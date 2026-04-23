#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 CNVD 浏览器填表阶段唯一使用的 form_context.json。"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from extract_vuln_data import DEFAULT_DATA_DIR, extract_cnvd_data, extract_fields_from_docx, find_docx_path


def extract_das_id_from_name(name: str) -> str:
    """从目录名或文件名中提取 DAS-ID。"""
    match = re.search(r"(DAS-[A-Z]?\d+)", name)
    return match.group(1) if match else name


def resolve_target(input_value: str, data_dir: str) -> Tuple[str, str, Optional[str]]:
    """兼容 DAS-ID、DAS 目录、CNVD 目录和 docx 路径。"""
    target = Path(input_value).expanduser()
    if not target.exists():
        return input_value, data_dir, None

    if target.is_file() and target.suffix.lower() == ".docx":
        das_id = extract_das_id_from_name(target.name) or extract_das_id_from_name(target.parent.name)
        return das_id, str(target.parent.parent), str(target)

    if target.is_dir():
        if target.name.startswith("CNVD-"):
            das_id = extract_das_id_from_name(target.parent.name)
            docx_paths = sorted(
                path for path in target.iterdir()
                if path.is_file() and path.suffix.lower() == ".docx" and not path.name.startswith(".")
            )
            return das_id, str(target.parent.parent), str(docx_paths[0]) if docx_paths else None

        das_id = extract_das_id_from_name(target.name)
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


def build_context(args: argparse.Namespace) -> dict:
    """构建完整 CNVD FormContext。"""
    das_id, resolved_data_dir, doc_path_override = resolve_target(args.target, args.data_dir)
    if doc_path_override:
        fields = extract_fields_from_docx(doc_path_override)
        platform_dir = str(Path(doc_path_override).parent)
        data = extract_cnvd_data(das_id, resolved_data_dir)
        if data.get("error"):
            # 允许直接传 docx/CNVD 目录时绕过 data_dir 扫描失败。
            from extract_vuln_data import clean_cnvd_description, find_attachment_zip_path, map_cnvd_vuln_type, map_soft_style

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
                "version": fields.get("影响版本", ""),
                "folder_path": platform_dir,
                "docx_path": doc_path_override,
                "attachment_zip_path": find_attachment_zip_path(platform_dir, "CNVD"),
            }
    else:
        data = extract_cnvd_data(das_id, resolved_data_dir)

    if data.get("error"):
        return data

    attachment_status = file_status(data.get("attachment_zip_path", ""))
    title_parts = split_cnvd_title(data.get("title", ""), data.get("vuln_type", ""))

    checks = {
        "title_input_ready": bool(title_parts["title_input"]),
        "title_final_expected_ready": bool(title_parts["title_final_expected"]),
        "attachment_exists": attachment_status["exists"],
        "attachment_is_file": attachment_status["is_file"],
        "attachment_is_zip": attachment_status["suffix"] == ".zip",
        "attachment_name_starts_with_cnvd": attachment_status["name_starts_with_cnvd"],
        "description_ready": bool(data.get("description", "")),
        "is_open_no": True,
        "no_browser_phase_extraction": True,
    }

    context = {
        **data,
        **title_parts,
        "schema": "cnvd_form_context_v1",
        "platform": "CNVD",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_target": args.target,
        "resolved_data_dir": resolved_data_dir,
        "is_open": "否",
        "temp_solution": "无",
        "formal_solution": "见附件",
        "submission_zip_path": data.get("attachment_zip_path", ""),
        "submission_zip_status": attachment_status,
        "attachment_status": attachment_status,
        "checks": checks,
        "ready": all(checks.values()),
        "browser_phase_rule": "浏览器阶段只能读取本 form_context.json；禁止重新压缩目录或重新判断标题。",
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="准备 CNVD 表单上下文 JSON")
    parser.add_argument("target", help="DAS-ID、DAS 目录、CNVD 目录或 CNVD docx 路径")
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR, help="漏洞数据根目录")
    parser.add_argument("--output", default="", help="输出 form_context.json 路径；默认写入 CNVD 材料目录")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    context = build_context(args)
    if context.get("error"):
        print(json.dumps(context, ensure_ascii=False, indent=2))
        return 1

    output = Path(args.output).expanduser() if args.output else Path(context["folder_path"]) / "form_context.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "output": str(output),
        "ready": context["ready"],
        "checks": context["checks"],
    }, ensure_ascii=False, indent=2))
    return 0 if context["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
