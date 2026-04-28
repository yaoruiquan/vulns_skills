#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CNVD/CNNVD 批量上报状态管理与统一通知。"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = SKILL_ROOT.name
PLATFORM = "CNNVD" if "cnnvd" in SKILL_NAME.lower() else "CNVD"
STATE_SCHEMA = "regulatory_batch_state_v1"
DAS_ID_PATTERN = re.compile(r"(DAS-[A-Z]?\d+)")


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_name(value: str, fallback: str = "batch") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", (value or "").strip()).strip("-")
    return cleaned or fallback


def extract_das_id(value: str) -> str:
    match = DAS_ID_PATTERN.search(value or "")
    return match.group(1) if match else ""


def default_state_path(batch_dir: Path) -> Path:
    batch_name = safe_name(batch_dir.name, "batch")
    return Path("/tmp/vulns-skills") / SKILL_NAME / "batches" / batch_name / "batch_state.json"


def state_dir_for(state_path: Path) -> Path:
    return state_path.expanduser().resolve().parent


def read_state(path: str | Path) -> dict:
    state_path = Path(path).expanduser().resolve()
    if not state_path.is_file():
        raise SystemExit(f"批量状态文件不存在: {state_path}")
    return json.loads(state_path.read_text(encoding="utf-8"))


def write_state(state: dict, path: str | Path | None = None) -> Path:
    state_path = Path(path or state["state_path"]).expanduser().resolve()
    state["state_path"] = str(state_path)
    state["updated_at"] = now()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state_path


def find_platform_dir(das_dir: Path, platform: str) -> Path | None:
    candidates = [
        path for path in das_dir.iterdir()
        if path.is_dir() and not path.name.startswith(".") and path.name.upper().startswith(f"{platform}-")
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item.name)[0]


def find_docx(platform_dir: Path) -> Path | None:
    candidates = [
        path for path in platform_dir.iterdir()
        if path.is_file() and path.suffix.lower() == ".docx" and not path.name.startswith(".")
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item.name)[0]


def context_path_for(state: dict, item: dict) -> str:
    base = state_dir_for(Path(state["state_path"])) / "contexts" / state["platform"] / item["das_id"]
    return str(base / "form_context.json")


def scan_batch(batch_dir: Path, platform: str) -> tuple[list[dict], list[dict]]:
    items = []
    skipped = []
    order = 1
    for das_dir in sorted(batch_dir.iterdir(), key=lambda item: item.name):
        if not das_dir.is_dir() or das_dir.name.startswith("."):
            continue
        das_id = extract_das_id(das_dir.name)
        if not das_id:
            skipped.append({"path": str(das_dir), "reason": "目录名未识别到 DAS-ID"})
            continue
        platform_dir = find_platform_dir(das_dir, platform)
        if not platform_dir:
            skipped.append({"path": str(das_dir), "das_id": das_id, "reason": f"未找到 {platform}-* 目录"})
            continue
        docx_path = find_docx(platform_dir)
        item = {
            "order": order,
            "status": "pending",
            "das_id": das_id,
            "title": docx_path.stem if docx_path else platform_dir.name.removeprefix(f"{platform}-"),
            "vuln_dir": str(das_dir),
            "platform_dir": str(platform_dir),
            "docx_path": str(docx_path) if docx_path else "",
            "context_file": "",
            "platform_id": "",
            "started_at": "",
            "submitted_at": "",
            "error": "",
            "publish_result": {},
        }
        items.append(item)
        order += 1
    return items, skipped


def summarize_state(state: dict) -> dict:
    counts = {}
    for item in state.get("items", []):
        counts[item.get("status", "unknown")] = counts.get(item.get("status", "unknown"), 0) + 1
    return {
        "platform": state.get("platform"),
        "batch_name": state.get("batch_name"),
        "state_path": state.get("state_path"),
        "env_checked": state.get("env_checked", False),
        "total": len(state.get("items", [])),
        "counts": counts,
        "skipped": len(state.get("skipped", [])),
        "final_notified": state.get("final_notified", False),
    }


def next_item(state: dict) -> dict | None:
    for item in state.get("items", []):
        if item.get("status") == "in_progress":
            return item
    for item in state.get("items", []):
        if item.get("status") == "pending":
            return item
    return None


def find_item(state: dict, das_id: str = "", index: int = 0) -> dict:
    if index:
        for item in state.get("items", []):
            if item.get("order") == index:
                return item
        raise SystemExit(f"未找到序号: {index}")
    if das_id:
        for item in state.get("items", []):
            if item.get("das_id") == das_id:
                return item
        raise SystemExit(f"未找到 DAS-ID: {das_id}")
    item = next_item(state)
    if not item:
        raise SystemExit("没有可操作的批量条目")
    return item


def prepare_command(item: dict) -> str:
    return "python3 scripts/prepare_form_context.py {} --output {}".format(
        shlex.quote(item["platform_dir"]),
        shlex.quote(item["context_file"]),
    )


def record_command(state: dict, item: dict) -> str:
    return "python3 scripts/batch_report.py record {} --das-id {} --platform-id '<{}编号>' --context {} --status submitted".format(
        shlex.quote(state["state_path"]),
        shlex.quote(item["das_id"]),
        state["platform"],
        shlex.quote(item["context_file"]),
    )


def start_next_command(state: dict, *, skip_env_check: bool = False) -> str:
    command = f"python3 scripts/batch_report.py start-next {shlex.quote(state['state_path'])}"
    if skip_env_check:
        command += " --skip-env-check"
    return command


def command_init(args: argparse.Namespace) -> int:
    batch_dir = Path(args.batch_dir).expanduser().resolve()
    if not batch_dir.is_dir():
        raise SystemExit(f"批次目录不存在: {batch_dir}")
    state_path = Path(args.output).expanduser().resolve() if args.output else default_state_path(batch_dir)
    if state_path.exists() and not args.force:
        raise SystemExit(f"状态文件已存在，如需重建请加 --force: {state_path}")

    items, skipped = scan_batch(batch_dir, PLATFORM)
    state = {
        "schema": STATE_SCHEMA,
        "platform": PLATFORM,
        "skill_name": SKILL_NAME,
        "batch_dir": str(batch_dir),
        "batch_name": batch_dir.name,
        "state_path": str(state_path),
        "created_at": now(),
        "updated_at": now(),
        "env_checked": False,
        "final_notified": False,
        "items": items,
        "skipped": skipped,
    }
    for item in state["items"]:
        item["context_file"] = context_path_for(state, item)
    write_state(state, state_path)
    print(json.dumps({
        "state_path": str(state_path),
        "summary": summarize_state(state),
        "next_command": start_next_command(state),
    }, ensure_ascii=False, indent=2))
    return 0 if items else 2


def command_status(args: argparse.Namespace) -> int:
    state = read_state(args.state)
    print(json.dumps(summarize_state(state), ensure_ascii=False, indent=2))
    return 0


def command_mark_env(args: argparse.Namespace) -> int:
    state = read_state(args.state)
    state["env_checked"] = True
    write_state(state)
    print(json.dumps({"state_path": state["state_path"], "env_checked": True}, ensure_ascii=False, indent=2))
    return 0


def command_start_next(args: argparse.Namespace) -> int:
    state = read_state(args.state)
    item = next_item(state)
    if not item:
        print(json.dumps({
            "done": True,
            "summary": summarize_state(state),
            "notify_command": f"python3 scripts/batch_report.py notify {shlex.quote(state['state_path'])}",
        }, ensure_ascii=False, indent=2))
        return 0
    if item["status"] == "pending":
        item["status"] = "in_progress"
        item["started_at"] = now()
        item["context_file"] = item.get("context_file") or context_path_for(state, item)
        write_state(state)

    print(json.dumps({
        "done": False,
        "platform": state["platform"],
        "env_checked": state.get("env_checked", False),
        "skip_environment_check": bool(state.get("env_checked")) or args.skip_env_check,
        "item": item,
        "prepare_context_command": prepare_command(item),
        "single_report_target": item["platform_dir"],
        "after_submit_record_command": record_command(state, item),
        "continue_rule": "本条提交后执行 after_submit_record_command；record 输出 next_command 后直接继续下一条，不需要清理上下文。",
    }, ensure_ascii=False, indent=2))
    return 0


def command_record(args: argparse.Namespace) -> int:
    state = read_state(args.state)
    item = find_item(state, args.das_id, args.index)
    item["status"] = args.status
    item["platform_id"] = args.platform_id.strip()
    item["context_file"] = args.context or item.get("context_file") or context_path_for(state, item)
    item["error"] = args.error
    if args.status == "submitted":
        item["submitted_at"] = now()
    write_state(state)
    print(json.dumps({
        "recorded": True,
        "item": item,
        "summary": summarize_state(state),
        "next_command": start_next_command(state, skip_env_check=bool(state.get("env_checked"))),
    }, ensure_ascii=False, indent=2))
    return 0


def run_json(command: list[str]) -> dict:
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"命令未返回 JSON: {' '.join(command)}\n{result.stdout}\n{result.stderr}") from exc


def publish_item(state: dict, item: dict, dry_run: bool) -> dict:
    context_file = Path(item.get("context_file") or context_path_for(state, item)).expanduser()
    if not context_file.is_file():
        raise SystemExit(f"缺少 form_context.json，无法统一上传: {context_file}")
    publish_script = SKILL_ROOT / "scripts" / "publish_submission_zip.py"
    relative_batch = f"{safe_name(state['batch_name'])}/{state['platform']}/{safe_name(item['das_id'], 'unknown')}"
    command = [
        sys.executable,
        str(publish_script),
        str(context_file),
        "--platform-id",
        item.get("platform_id", ""),
        "--batch",
        relative_batch,
        "--json",
    ]
    if dry_run:
        command.append("--dry-run")
    return run_json(command)


def build_notify_text(state: dict, results: list[dict]) -> tuple[str, list[str]]:
    lines = [
        f"批次：{state['batch_name']}",
        f"平台：{state['platform']}",
        f"总数：{len(state.get('items', []))}",
    ]
    links = []

    name_lines = []
    id_lines = []
    attach_lines = []
    for index, result in enumerate(results, start=1):
        name_lines.append(f"{index}. {result.get('vuln_name', '')}")
        id_lines.append(f"{index}. {result.get('platform_id', '未记录')}")
        zip_name = result.get('zip_name', '')
        zip_size = result.get('zip_size_mb', 0)
        attach_lines.append(f"{index}. {zip_name}（{zip_size} MB）")
        if result.get("download_url"):
            label = f"{result.get('das_id', index)}-{state['platform']}附件"
            links.append(f"{label}={result['download_url']}")

    lines.extend([
        "",
        "漏洞名称：",
        *name_lines,
        "",
        "CNNVD 编号：",
        *id_lines,
        "",
        "附件：",
        *attach_lines,
    ])
    return "\n".join(lines), links


def command_notify(args: argparse.Namespace) -> int:
    state = read_state(args.state)
    submitted = [item for item in state.get("items", []) if item.get("status") == "submitted"]
    if len(submitted) != len(state.get("items", [])) and not args.allow_incomplete:
        raise SystemExit("批次尚未全部 submitted；如需强制通知请加 --allow-incomplete")
    if not submitted:
        raise SystemExit("没有已提交条目，不能发送统一通知")

    results = []
    for item in submitted:
        result = publish_item(state, item, args.dry_run)
        item["publish_result"] = result
        results.append(result)

    text, links = build_notify_text(state, results)
    notify_script = SKILL_ROOT / "scripts" / "dingtalk_notify.py"
    command = [
        sys.executable,
        str(notify_script),
        "--title",
        args.title or f"监管上报 {state['platform']} 批量上报完成",
        "--status",
        "success",
        "--text",
        text,
    ]
    for link in links:
        command.extend(["--link", link])
    if args.at_all:
        command.append("--at-all")

    if args.dry_run:
        print(json.dumps({
            "dry_run": True,
            "publish_results": results,
            "notify_command": command,
            "text": text,
            "links": links,
        }, ensure_ascii=False, indent=2))
        return 0

    subprocess.run(command, check=True)
    state["final_notified"] = True
    write_state(state)
    print(json.dumps({"notified": True, "summary": summarize_state(state)}, ensure_ascii=False, indent=2))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"{PLATFORM} 批量上报状态管理")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="扫描批次目录并创建状态文件")
    init.add_argument("batch_dir", help="批次根目录，内部包含 DAS-* 目录")
    init.add_argument("--output", default="", help="状态文件输出路径")
    init.add_argument("--force", action="store_true", help="覆盖已有状态文件")
    init.set_defaults(func=command_init)

    status = sub.add_parser("status", help="查看批次状态")
    status.add_argument("state", help="batch_state.json 路径")
    status.set_defaults(func=command_status)

    mark_env = sub.add_parser("mark-env", help="标记首个漏洞已完成环境检查")
    mark_env.add_argument("state", help="batch_state.json 路径")
    mark_env.set_defaults(func=command_mark_env)

    start_next = sub.add_parser("start-next", help="取出并锁定下一条待上报漏洞")
    start_next.add_argument("state", help="batch_state.json 路径")
    start_next.add_argument("--skip-env-check", action="store_true", help="继续批量时跳过环境检查")
    start_next.set_defaults(func=command_start_next)

    record = sub.add_parser("record", help="记录单个漏洞上报结果")
    record.add_argument("state", help="batch_state.json 路径")
    record.add_argument("--das-id", default="", help="DAS-ID")
    record.add_argument("--index", type=int, default=0, help="批次序号")
    record.add_argument("--platform-id", default="", help=f"{PLATFORM} 编号")
    record.add_argument("--context", default="", help="本条 form_context.json 路径")
    record.add_argument("--status", choices=["pending", "in_progress", "submitted", "failed"], default="submitted")
    record.add_argument("--error", default="", help="失败原因")
    record.set_defaults(func=command_record)

    notify = sub.add_parser("notify", help="统一上传附件并发送一条钉钉通知")
    notify.add_argument("state", help="batch_state.json 路径")
    notify.add_argument("--title", default="", help="钉钉标题")
    notify.add_argument("--allow-incomplete", action="store_true", help="允许批次未全部完成时通知")
    notify.add_argument("--dry-run", action="store_true", help="只生成上传/通知结果，不执行 ssh/scp/钉钉发送")
    notify.add_argument("--at-all", action="store_true", help="钉钉 @所有人")
    notify.set_defaults(func=command_notify)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
