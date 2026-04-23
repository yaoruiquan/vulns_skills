#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""上传单个 CNNVD 原始 zip，并按需推送钉钉下载链接。"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote


SKILL_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = SKILL_ROOT / ".env"
PLATFORM = "CNNVD"
ZIP_PREFIX = "CNNVD"
DEFAULT_REMOTE_DIR = "/root/msrc-report-downloads/cnnvd-submissions"
DEFAULT_BASE_URL = "http://10.50.10.29:8080/download/msrc/cnnvd-submissions"
DAS_ID_PATTERN = re.compile(r"(DAS-[A-Z]?\d+)")
PLATFORM_ID_PATTERN = re.compile(r"(CNNVD-\d{4}-\d+)")


def load_env() -> None:
    """加载 skill 根目录下的 .env，不覆盖已存在环境变量。"""
    if not ENV_FILE.exists():
        return
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def env_bool(name: str, default: bool = True) -> bool:
    """读取布尔环境变量。"""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def safe_name(value: str, fallback: str) -> str:
    """生成远端目录安全名称。"""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", (value or "").strip()).strip("-")
    return cleaned or fallback


def file_size_mb(path: Path) -> float:
    """返回文件大小 MB。"""
    return round(path.stat().st_size / 1024 / 1024, 2)


def read_context(path: Path) -> dict:
    """读取 form_context.json。"""
    return json.loads(path.read_text(encoding="utf-8"))


def extract_das_id(*values: str) -> str:
    """从路径、目录名或文件名中提取 DAS-ID。"""
    for value in values:
        match = DAS_ID_PATTERN.search(value or "")
        if match:
            return match.group(1)
    return ""


def extract_platform_id(*values: str) -> str:
    """从路径、目录名或文件名中提取 CNNVD 编号。"""
    for value in values:
        match = PLATFORM_ID_PATTERN.search(value or "")
        if match:
            return match.group(1)
    return ""


def title_from_dir_name(name: str) -> str:
    """从 DAS/CNNVD 目录名推断漏洞名称。"""
    cleaned = re.sub(r"^DAS-[A-Z]?\d+-", "", name or "")
    cleaned = re.sub(r"^CNNVD-", "", cleaned)
    cleaned = re.sub(r"^CNNVD-\d{4}-\d+-DAS-[A-Z]?\d+-?", "", cleaned)
    return cleaned.strip("-") or name


def find_nearby_context(zip_path: Path) -> dict:
    """直接传 zip 时，尝试读取同一 DAS 目录下 CNNVD 子目录的 form_context.json。"""
    roots = [zip_path.parent]
    if zip_path.parent.parent not in roots:
        roots.append(zip_path.parent.parent)

    for root in roots:
        if not root.is_dir():
            continue
        direct = root / "form_context.json"
        if direct.is_file():
            try:
                context = read_context(direct)
                if context.get("platform") == PLATFORM or "CNNVD-" in direct.parent.name:
                    return context
            except (OSError, json.JSONDecodeError):
                pass

        for child in root.iterdir():
            if not child.is_dir() or not child.name.startswith("CNNVD-"):
                continue
            candidate = child / "form_context.json"
            if not candidate.is_file():
                continue
            try:
                return read_context(candidate)
            except (OSError, json.JSONDecodeError):
                continue
    return {}


def find_platform_zip(folder_path: str) -> str:
    """查找单个 CNNVD 原始整包 zip，优先查平台目录父级。"""
    folder = Path(folder_path).expanduser()
    roots = [folder.parent, folder]
    candidates = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.iterdir():
            if not path.is_file() or path.suffix.lower() != ".zip" or path.name.startswith("."):
                continue
            if path.name.upper().startswith(ZIP_PREFIX):
                candidates.append(path)
    if not candidates:
        return ""
    return str(max(candidates, key=lambda item: item.stat().st_size))


def resolve_zip_and_context(target: str, vuln_name: str = "") -> tuple[Path, dict]:
    """兼容 form_context.json 或 zip 路径。"""
    path = Path(target).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"输入路径不存在: {path}")

    if path.is_file() and path.suffix.lower() == ".json":
        context = read_context(path)
        zip_path = (
            context.get("submission_zip_path")
            or context.get("attachment_zip_path")
            or find_platform_zip(context.get("folder_path", ""))
        )
        if not zip_path:
            raise SystemExit("form_context.json 中未找到 CNNVD zip 路径，且材料目录未找到 CNNVD-*.zip")
        return Path(zip_path).expanduser().resolve(), context

    if path.is_file() and path.suffix.lower() == ".zip":
        context = find_nearby_context(path)
        if not context:
            context = {
                "das_id": extract_das_id(path.name, path.parent.name),
                "title": title_from_dir_name(path.parent.name),
                "folder_path": str(path.parent),
            }
        if vuln_name:
            context["title"] = vuln_name
        return path, context

    raise SystemExit("输入必须是 form_context.json 或 CNNVD-*.zip")


def validate_zip(zip_path: Path, *, allow_non_prefixed: bool = False) -> None:
    """校验上传文件必须是单个 CNNVD zip。"""
    if not zip_path.is_file():
        raise SystemExit(f"zip 文件不存在: {zip_path}")
    if zip_path.suffix.lower() != ".zip":
        raise SystemExit(f"上传文件必须是 .zip: {zip_path}")
    if not allow_non_prefixed and not zip_path.name.upper().startswith(ZIP_PREFIX):
        raise SystemExit(f"上传文件名必须以 {ZIP_PREFIX} 开头: {zip_path.name}")


def build_ssh_prefix(password: str, *, require_binary: bool = True) -> tuple[list[str], dict[str, str]]:
    """如果配置了密码则使用 sshpass，否则使用 SSH key。"""
    if not password:
        return [], {}
    if require_binary and not shutil.which("sshpass"):
        raise SystemExit("已配置 REPORT_UPLOAD_PASSWORD，但未安装 sshpass；建议使用 SSH key 免密")
    return ["sshpass", "-e"], {"SSHPASS": password}


def run_command(command: list[str], *, dry_run: bool = False, env_overlay: Optional[dict[str, str]] = None) -> None:
    """执行外部命令。"""
    printable = " ".join(shlex.quote(part) for part in command)
    if dry_run:
        print(f"[dry-run] {printable}", file=sys.stderr)
        return
    env = os.environ.copy()
    if env_overlay:
        env.update(env_overlay)
    subprocess.run(command, check=True, env=env)


def build_download_url(base_url: str, relative_dir: str, filename: str) -> str:
    """按 URL path 规则生成下载链接。"""
    parts = [part for part in relative_dir.strip("/").split("/") if part]
    encoded = [quote(part) for part in parts]
    encoded.append(quote(filename))
    return "/".join([base_url.rstrip("/"), *encoded])


def publish(args: argparse.Namespace) -> dict:
    """上传 zip 并返回结果。"""
    load_env()

    if not env_bool("REPORT_UPLOAD_ENABLED", True) and not args.force:
        return {"enabled": False}

    zip_path, context = resolve_zip_and_context(args.target, args.vuln_name)
    validate_zip(zip_path, allow_non_prefixed=args.allow_non_prefixed)

    host = args.host or os.environ.get("REPORT_UPLOAD_HOST", "10.50.10.29")
    user = args.user or os.environ.get("REPORT_UPLOAD_USER", "root")
    port = str(args.port or os.environ.get("REPORT_UPLOAD_PORT", "22"))
    remote_root = args.remote_dir or os.environ.get("REPORT_UPLOAD_REMOTE_DIR", DEFAULT_REMOTE_DIR)
    base_url = args.base_url or os.environ.get("REPORT_DOWNLOAD_BASE_URL", DEFAULT_BASE_URL)
    password = args.password or os.environ.get("REPORT_UPLOAD_PASSWORD", "")

    if not host or not remote_root or not base_url:
        raise SystemExit("缺少上传配置：REPORT_UPLOAD_HOST、REPORT_UPLOAD_REMOTE_DIR 或 REPORT_DOWNLOAD_BASE_URL")

    das_id = args.das_id or context.get("das_id") or extract_das_id(zip_path.name, str(zip_path.parent)) or "unknown"
    vuln_name = args.vuln_name or context.get("title_final_expected") or context.get("title") or zip_path.stem
    platform_id = args.platform_id or extract_platform_id(zip_path.name)
    month = args.batch_month or datetime.now().strftime("%Y-%m")
    relative_dir = args.batch or f"{safe_name(month, 'batch')}/{safe_name(das_id, 'unknown')}"
    remote_batch_dir = f"{remote_root.rstrip('/')}/{relative_dir.strip('/')}"
    ssh_target = f"{user}@{host}"
    prefix, ssh_env = build_ssh_prefix(password, require_binary=not args.dry_run)

    run_command(
        prefix + ["ssh", "-p", port, ssh_target, f"mkdir -p {shlex.quote(remote_batch_dir)}"],
        dry_run=args.dry_run,
        env_overlay=ssh_env,
    )
    run_command(
        prefix + ["scp", "-P", port, str(zip_path), f"{ssh_target}:{remote_batch_dir}/"],
        dry_run=args.dry_run,
        env_overlay=ssh_env,
    )

    download_url = build_download_url(base_url, relative_dir, zip_path.name)
    return {
        "enabled": True,
        "platform": PLATFORM,
        "das_id": das_id,
        "platform_id": platform_id,
        "vuln_name": vuln_name,
        "zip_path": str(zip_path),
        "zip_name": zip_path.name,
        "zip_size_mb": file_size_mb(zip_path),
        "remote_dir": remote_batch_dir,
        "download_url": download_url,
    }


def notify(result: dict, args: argparse.Namespace) -> None:
    """调用 dingtalk_notify.py 推送下载链接和重要字段。"""
    if not result.get("enabled"):
        return

    text_lines = [
        f"漏洞名称：{result['vuln_name']}",
        f"DAS-ID：{result['das_id']}",
    ]
    if result.get("platform_id"):
        text_lines.append(f"{PLATFORM} 编号：{result['platform_id']}")
    text_lines.extend([
        f"附件：{result['zip_name']}",
        f"大小：{result['zip_size_mb']} MB",
    ])
    if args.text:
        text_lines.append(args.text)

    notify_script = SKILL_ROOT / "scripts" / "dingtalk_notify.py"
    command = [
        sys.executable,
        str(notify_script),
        "--title",
        args.title,
        "--status",
        args.status,
        "--text",
        "\n".join(text_lines),
        "--link",
        f"{PLATFORM}附件下载={result['download_url']}",
    ]
    if args.at_all:
        command.append("--at-all")
    run_command(command, dry_run=args.dry_run)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="上传单个 CNNVD 原始 zip，并可推送钉钉下载链接")
    parser.add_argument("target", help="CNNVD form_context.json 或 CNNVD-*.zip 路径")
    parser.add_argument("--platform-id", default="", help="提交成功后的 CNNVD 编号")
    parser.add_argument("--das-id", default="", help="DAS-ID；默认从 form_context.json 读取")
    parser.add_argument("--vuln-name", default="", help="漏洞名称；默认从 form_context.json 读取")
    parser.add_argument("--batch", default="", help="远端相对目录；默认 YYYY-MM/DAS-ID")
    parser.add_argument("--batch-month", default="", help="批次月份；默认当前 YYYY-MM")
    parser.add_argument("--host", default="", help="上传服务器；默认读取 REPORT_UPLOAD_HOST")
    parser.add_argument("--user", default="", help="上传用户；默认读取 REPORT_UPLOAD_USER/root")
    parser.add_argument("--port", default="", help="SSH 端口；默认读取 REPORT_UPLOAD_PORT/22")
    parser.add_argument("--remote-dir", default="", help="远程根目录；默认读取 REPORT_UPLOAD_REMOTE_DIR")
    parser.add_argument("--base-url", default="", help="下载 URL 根路径；默认读取 REPORT_DOWNLOAD_BASE_URL")
    parser.add_argument("--password", default="", help="SSH 密码；默认读取 REPORT_UPLOAD_PASSWORD，不建议命令行传入")
    parser.add_argument("--allow-non-prefixed", action="store_true", help="允许上传文件名不是 CNNVD 开头的 zip")
    parser.add_argument("--force", action="store_true", help="忽略 REPORT_UPLOAD_ENABLED=false，强制上传")
    parser.add_argument("--dry-run", action="store_true", help="只打印 ssh/scp/通知命令，不执行")
    parser.add_argument("--notify", action="store_true", help="上传成功后推送钉钉 Markdown 下载链接")
    parser.add_argument("--title", default="监管上报 CNNVD 附件已上传", help="钉钉消息标题")
    parser.add_argument("--status", choices=["success", "failed", "running", "info"], default="success", help="钉钉消息状态")
    parser.add_argument("--text", default="", help="钉钉消息附加说明")
    parser.add_argument("--at-all", action="store_true", help="钉钉消息 @所有人")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = publish(args)
    if args.notify:
        notify(result, args)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if not result.get("enabled"):
        print("附件上传未启用，跳过")
        return 0

    print(f"platform={result['platform']}")
    print(f"das_id={result['das_id']}")
    print(f"zip={result['zip_path']}")
    print(f"download={result['download_url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
