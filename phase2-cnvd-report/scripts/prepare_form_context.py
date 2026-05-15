#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 CNVD 浏览器填表阶段唯一使用的 form_context.json。"""

from __future__ import annotations

import argparse
import shutil
import json
import os
import re
import shlex
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from browser_snippets import shell_command_for_select2
from extract_vuln_data import DEFAULT_DATA_DIR, extract_cnvd_data, extract_fields_from_docx, find_docx_path


DEFAULT_FORM_CONTEXT_DIR = os.environ.get(
    "FORM_CONTEXT_DIR",
    "/tmp/vulns-skills/phase2-cnvd-report/form-contexts",
)


def shell_command_for_attachment(command: str, attachment_path: str) -> str:
    return "python3 scripts/browser_snippets.py {} --attachment-path {}".format(
        command,
        shlex.quote(attachment_path),
    )


def browser_upload_alias_path(attachment_path: str, output_path: str) -> str:
    """Create an ASCII-named browser-readable copy for Chrome DevTools upload.

    Docker Chrome can read /data/work, but CDP upload is unreliable with long
    non-ASCII paths. Keep the original CNVD zip as source of truth and upload
    this same-content alias from logs/.
    """
    source = Path(attachment_path) if attachment_path else None
    if not source or not source.is_file():
        return attachment_path

    output = Path(output_path).expanduser()
    if output.name:
        job_root = output.parent.parent
    else:
        job_root = output.parent
    alias_dir = job_root / "logs" / "browser-upload"
    alias_dir.mkdir(parents=True, exist_ok=True)
    alias = alias_dir / "cnvd-attachment-upload.zip"
    if not alias.exists() or alias.stat().st_size != source.stat().st_size:
        shutil.copy2(source, alias)
    return str(alias)


def extract_das_id_from_name(name: str) -> str:
    """从目录名或文件名中提取 DAS-ID。"""
    match = re.search(r"(DAS-[A-Z]?\d+)", name)
    return match.group(1) if match else ""


def extract_das_id_from_path(path: Path) -> str:
    """从文件或目录路径各级名称中提取 DAS-ID。"""
    candidates = [path.name, *[parent.name for parent in path.parents]]
    for name in candidates:
        das_id = extract_das_id_from_name(name)
        if das_id:
            return das_id
    return ""


def resolve_target(input_value: str, data_dir: str) -> Tuple[str, str, Optional[str]]:
    """兼容 DAS-ID、DAS 目录、CNVD 目录和 docx 路径。"""
    target = Path(input_value).expanduser()
    if not target.exists():
        return input_value, data_dir, None

    if target.is_file() and target.suffix.lower() == ".docx":
        das_id = extract_das_id_from_path(target) or input_value
        return das_id, str(target.parent.parent), str(target)

    if target.is_dir():
        if target.name.startswith("CNVD-"):
            das_id = extract_das_id_from_path(target) or target.parent.name
            docx_paths = sorted(
                path for path in target.iterdir()
                if path.is_file() and path.suffix.lower() == ".docx" and not path.name.startswith(".")
            )
            return das_id, str(target.parent.parent), str(docx_paths[0]) if docx_paths else None

        das_id = extract_das_id_from_path(target) or target.name
        if target.name.startswith("DAS-"):
            doc_path = find_docx_path(das_id, "CNVD", str(target.parent))
            return das_id, str(target.parent), doc_path

        doc_path = find_docx_path(das_id, "CNVD", str(target))
        return das_id, str(target), doc_path

    return input_value, data_dir, None


def split_cnvd_title(title: str, vuln_type: str) -> dict:
    """拆分 CNVD 页面标题输入框与最终预期标题。"""
    cleaned = (title or "").strip()
    if "存在" in cleaned and cleaned.endswith("漏洞"):
        title_input, suffix = cleaned.split("存在", 1)
        vuln_phrase = suffix[:-2] if suffix.endswith("漏洞") else suffix
    else:
        title_input = cleaned[:-2].strip() if cleaned.endswith("漏洞") else cleaned.strip()
        vuln_phrase = vuln_type or ""

    title_input = title_input.strip()
    vuln_phrase = vuln_phrase.strip()
    title_final_expected = cleaned or (
        f"{title_input}存在{vuln_phrase}漏洞" if title_input and vuln_phrase else title_input
    )
    return {
        "title_original": cleaned,
        "title_input": title_input,
        "title_vuln_phrase": vuln_phrase,
        "title_final_expected": title_final_expected,
    }


def resolve_form_type(is_event: str) -> dict:
    """将 is_event 统一成页面使用的漏洞所属类型。"""
    value = str(is_event or "0").strip()
    is_event_flag = value in {"1", "true", "True", "事件型漏洞", "事件型"}
    return {
        "form_type_value": "1" if is_event_flag else "0",
        "form_type_label": "事件型漏洞" if is_event_flag else "通用型漏洞",
    }


def file_status(path_value: str) -> dict:
    """返回文件存在性和大小信息。"""
    path = Path(path_value) if path_value else None
    if not path:
        return {
            "exists": False,
            "is_file": False,
            "size_mb": 0,
            "suffix": "",
            "name_starts_with_cnvd": False,
        }

    exists = path.exists()
    is_file = path.is_file()
    return {
        "exists": exists,
        "is_file": is_file,
        "size_mb": round(path.stat().st_size / 1024 / 1024, 2) if exists and is_file else 0,
        "suffix": path.suffix.lower(),
        "name_starts_with_cnvd": path.name.upper().startswith("CNVD"),
    }


def soft_style_label(soft_style_id: str) -> str:
    """将影响对象类型编码映射回页面下拉框中文。"""
    mapping = {
        "27": "操作系统",
        "28": "应用程序",
        "29": "WEB应用",
        "30": "数据库",
        "31": "网络设备",
        "32": "安全产品",
        "33": "智能设备",
        "38": "工业控制",
    }
    return mapping.get(str(soft_style_id or "").strip(), "应用程序")


def build_context(args: argparse.Namespace) -> dict:
    """构建完整 CNVD FormContext。"""
    das_id, resolved_data_dir, doc_path_override = resolve_target(args.target, args.data_dir)
    if doc_path_override:
        fields = extract_fields_from_docx(doc_path_override)
        platform_dir = str(Path(doc_path_override).parent)
        data = extract_cnvd_data(das_id, resolved_data_dir)
        if data.get("error"):
            # 允许直接传 docx/CNVD 目录时绕过 data_dir 扫描失败。
            from extract_vuln_data import clean_cnvd_description, find_attachment_zip_path, first_non_empty, map_cnvd_vuln_type, map_soft_style

            data = {
                "das_id": das_id,
                "title": fields.get("漏洞名称", ""),
                "description": clean_cnvd_description(fields.get("漏洞描述", "")),
                "vuln_type": map_cnvd_vuln_type(fields.get("漏洞类型", "")),
                "vuln_type_raw": fields.get("漏洞类型", ""),
                "url": fields.get("漏洞URL", ""),
                "unit_name": fields.get("漏洞厂商", ""),
                "is_event": "0",
                "soft_style_id": map_soft_style(fields.get("影响对象类型", "")),
                "discoverer_name": fields.get("提交人员", ""),
                "affected_product": fields.get("影响产品", ""),
                "version": first_non_empty(fields, "受影响实体版本号", "影响版本", "版本号"),
                "folder_path": platform_dir,
                "docx_path": doc_path_override,
                "attachment_zip_path": find_attachment_zip_path(platform_dir, "CNVD"),
            }
    else:
        data = extract_cnvd_data(das_id, resolved_data_dir)

    if data.get("error"):
        return data

    attachment_path = data.get("attachment_zip_path", "")
    browser_upload_path = browser_upload_alias_path(attachment_path, args.output)
    browser_upload_status = file_status(browser_upload_path)
    attachment_status = file_status(attachment_path)
    title_parts = split_cnvd_title(data.get("title", ""), data.get("vuln_type", ""))
    form_type = resolve_form_type(data.get("is_event", "0"))
    object_type_label = soft_style_label(data.get("soft_style_id", ""))

    checks = {
        "form_type_ready": bool(form_type["form_type_label"]),
        "object_type_ready": bool(object_type_label),
        "title_input_ready": bool(title_parts["title_input"]),
        "title_final_expected_ready": bool(title_parts["title_final_expected"]),
        "attachment_exists": attachment_status["exists"],
        "attachment_is_file": attachment_status["is_file"],
        "attachment_is_zip": attachment_status["suffix"] == ".zip",
        "attachment_name_starts_with_cnvd": attachment_status["name_starts_with_cnvd"],
        "description_ready": bool(data.get("description", "")),
        "detail_url_ready": True,
        "is_open_no": True,
        "no_browser_phase_extraction": True,
    }

    context = {
        **data,
        **title_parts,
        **form_type,
        "schema": "cnvd_form_context_v1",
        "platform": "CNVD",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_target": args.target,
        "resolved_data_dir": resolved_data_dir,
        "is_open": "否",
        "detail_url": "http://test.com",
        "detail_unknown_value": "见附件",
        "temp_solution": "无",
        "formal_solution": "见附件",
        "detail_phase": {
            "description": data.get("description", ""),
            "url": "http://test.com",
            "temp_solution": "无",
            "formal_solution": "见附件",
            "other_required_default": "见附件",
        },
        "dropdown_phase": {
            "form_type_label": form_type["form_type_label"],
            "vuln_type": data.get("vuln_type", ""),
            "object_type_label": object_type_label,
        },
        "page_payloads": {
            "select_first": {
                "form_type_label": form_type["form_type_label"],
                "vuln_type": data.get("vuln_type", ""),
                "object_type_label": object_type_label,
            },
            "base_info": {
                "is_open": "否",
            },
            "vendor_info": {
                "unit_name": data.get("unit_name", ""),
                "url": data.get("url", ""),
                "affected_product": data.get("affected_product", ""),
                "version": data.get("version", ""),
            },
            "detail_info": {
                "title_input": title_parts["title_input"],
                "description": data.get("description", ""),
                "detail_url": "http://test.com",
                "temp_solution": "无",
                "formal_solution": "见附件",
                "other_required_default": "见附件",
            },
            "attachments": {
                "attachment_zip_path": attachment_path,
                "browser_upload_path": browser_upload_path,
            },
        },
        "fill_order": [
            "1. 先执行 browser_helpers.select2_command，同步 漏洞所属类型(form_type_label)、漏洞类型(vuln_type)、影响对象类型(object_type_label)",
            "2. Select2 返回 ok=true 后，一次性填写 base_info/vendor_info/detail_info",
            "3. 不要在 fill_form 中重复填写 Select2 下拉框",
            "4. 最后上传 attachment_zip_path 并处理验证码",
        ],
        "interaction_rules": {
            "snapshot_budget": "除导航、下拉联动确认、提交结果确认外，不要为单个字段重复 take_snapshot。",
            "fill_rule": "页面联动完成后，优先一次性 fill_form 完成整组字段，不要填一个字段就重新检查一次。",
            "browser_phase_source": "浏览器阶段只读取 page_payloads 和 dropdown_phase，不重新读取 Word。",
            "login_guard_rule": "进入 /flaw/create 后必须先执行 browser_helpers.login_guard_command 生成的脚本；如检测到 Cloudflare 或登录页，先恢复登录态，不要继续填表。",
            "select2_rule": "CNVD 下拉框是 Select2 自定义组件，优先执行 browser_helpers.select2_command 生成的脚本，不要依赖 a11y 树点击选项。",
            "runtime_evaluate_rule": "browser_helpers 输出的是可直接执行的 IIFE 表达式，必须原样传给 Runtime.evaluate/evaluate_script，不要改回 async () => {...} 函数定义。",
        },
        "browser_helpers": {
            "is_open_command": "python3 scripts/browser_snippets.py is-open",
            "login_guard_command": "python3 scripts/browser_snippets.py login-guard",
            "select2_command": shell_command_for_select2(
                form_type["form_type_label"],
                data.get("vuln_type", ""),
                object_type_label,
            ),
            "attachment_prepare_command": shell_command_for_attachment(
                "attachment-prepare",
                browser_upload_path,
            ),
            "attachment_verify_command": shell_command_for_attachment(
                "attachment-verify",
                browser_upload_path,
            ),
            "open_captcha_tab_command": "python3 scripts/browser_snippets.py captcha-tab",
            "captcha_preview_command": "python3 scripts/browser_snippets.py captcha-tab",
            "submit_captcha_command_template": "python3 scripts/browser_snippets.py submit-captcha '<OCR识别结果>'",
        },
        "ocr": {
            "recognize_command": "python3 scripts/captcha_ocr.py /tmp/captcha.png --preprocess cnvd",
            "submit_rule": "提交前不要点击刷新；固定执行 browser_helpers.open_captcha_tab_command。若返回 ok=true，打开的是已加载的真实验证码图片，再只用 MCP 对验证码 img 元素截图到 /tmp/captcha.png 并执行 recognize_command 单次本地识别；识别结果返回后用 browser_helpers.submit_captcha_command_template 生成脚本直接填入并提交。若返回 code=CNVD_CAPTCHA_IMAGE_BROKEN，说明 /common/myCodeNew 触发 CNVD 防火墙或图片加载失败，禁止 OCR 页面占位文字，必须保存防火墙截图到 logs/human-cnvd-firewall.png，截取防火墙页真实验证码 img 元素并调用 captcha_ocr.py --preprocess cnvd 最多尝试 3 次；3 次仍未通过再写 progress warning 并等待前端人工验证码后继续。禁止整页/视口截图用于普通提交验证码，禁止提交包含“看不清/点击更换/存在/二进制/验证码”等页面文字的 OCR 结果。",
        },
        "browser_upload_path": browser_upload_path,
        "submission_zip_path": attachment_path,
        "submission_zip_status": attachment_status,
        "attachment_status": attachment_status,
        "browser_upload_status": browser_upload_status,
        "checks": checks,
        "ready": all(checks.values()),
        "browser_phase_rule": "浏览器阶段只能读取本 form_context.json；必须先执行 browser_helpers.select2_command 同步 Select2 下拉框，待页面联动完成后使用 page_payloads 一次性填写其余非 Select2 字段；第二阶段禁止重新读取 Word、重新提取描述、重新压缩目录或重新判断标题。",
        "dingtalk": {
            "success_title": "监管上报 CNVD 上报完成",
            "success_text_template": (
                f"漏洞名称：{title_parts['title_final_expected']}\\n"
                f"DAS-ID：{data.get('das_id', '')}\\n"
                "CNVD 编号：{cnvd_id}"
            ),
            "failed_title": "监管上报 CNVD 上报失败",
        },
    }
    return context


def default_context_output(context: dict) -> Path:
    """默认将运行时 JSON 写入 /tmp，避免污染 CNVD 提交材料目录。"""
    generated_at = context.get("generated_at") or datetime.now().isoformat(timespec="seconds")
    month = generated_at[:7]
    das_id = context.get("das_id") or "unknown-das"
    return Path(DEFAULT_FORM_CONTEXT_DIR).expanduser() / month / das_id / "form_context.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="准备 CNVD 表单上下文 JSON")
    parser.add_argument("target", help="DAS-ID、DAS 目录、CNVD 目录或 CNVD docx 路径")
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR, help="漏洞数据根目录")
    parser.add_argument("--output", default="", help="输出 form_context.json 路径；默认写入 /tmp/vulns-skills/phase2-cnvd-report/form-contexts/YYYY-MM/DAS-ID/")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    context = build_context(args)
    if context.get("error"):
        print(json.dumps(context, ensure_ascii=False, indent=2))
        return 1

    output = Path(args.output).expanduser() if args.output else default_context_output(context)
    output.parent.mkdir(parents=True, exist_ok=True)
    context["context_file_path"] = str(output)
    output.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "output": str(output),
        "ready": context["ready"],
        "checks": context["checks"],
    }, ensure_ascii=False, indent=2))
    return 0 if context["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
