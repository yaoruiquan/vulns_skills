#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 NCC 浏览器填表阶段唯一使用的 form_context.json。"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from extract_vuln_data import DEFAULT_DATA_DIR, extract_ncc_data, resolve_input


DEFAULT_FORM_CONTEXT_DIR = os.environ.get(
    "FORM_CONTEXT_DIR",
    "/tmp/vulns-skills/phase2-ncc-report/form-contexts",
)


def safe_name(value: str, fallback: str = "unknown") -> str:
    """生成适合路径使用的名称。"""
    cleaned = "".join(char if char.isalnum() or char in "._-" else "-" for char in (value or "").strip())
    cleaned = cleaned.strip("-")
    return cleaned or fallback


def default_context_output(context: dict) -> Path:
    """根据生成时间和 DAS-ID 生成默认输出路径。"""
    generated_at = context.get("generated_at") or datetime.now().isoformat(timespec="seconds")
    month = generated_at[:7]
    das_id = safe_name(str(context.get("das_id") or "unknown"))
    return Path(DEFAULT_FORM_CONTEXT_DIR).expanduser() / month / das_id / "form_context.json"


def build_context(args: argparse.Namespace) -> dict:
    """一次性整理浏览器填表所需的 NCC FormContext。"""
    material_dir, docx_path, error = resolve_input(args)
    if error:
        raise SystemExit(error)

    assert material_dir is not None
    assert docx_path is not None
    context = extract_ncc_data(material_dir, docx_path)
    context.update(
        {
            "form_context_version": 1,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "source_docx_path": str(docx_path),
            "browser_phase_rule": "浏览器阶段只能读取本 form_context.json；禁止重新运行 Word 提取脚本。",
        }
    )
    return context


def build_parser() -> argparse.ArgumentParser:
    """构造命令行参数解析器。"""
    parser = argparse.ArgumentParser(description="生成 NCC 浏览器填表 FormContext")
    parser.add_argument("das_id", nargs="?", help="DAS-ID，兼容旧用法")
    parser.add_argument("--platform", default="NCC", help="保留兼容参数，当前仅支持 NCC")
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR, help="漏洞数据根目录")
    parser.add_argument("--input-path", default="", help="具体 DAS 目录或材料目录")
    parser.add_argument("--docx-path", default="", help="直接指定 docx 文件路径")
    parser.add_argument(
        "--prefer-source",
        default="CNVD",
        choices=["CNVD", "CNNVD", "NCC"],
        help="同一 DAS 目录下优先选择哪类材料目录，默认 CNVD",
    )
    parser.add_argument(
        "--output",
        default="",
        help="输出 form_context.json 路径；默认写入 /tmp/vulns-skills/phase2-ncc-report/form-contexts/YYYY-MM/DAS-ID/",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    context = build_context(args)

    output = Path(args.output).expanduser() if args.output else default_context_output(context)
    output.parent.mkdir(parents=True, exist_ok=True)
    context["context_file_path"] = str(output)
    output.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"ok": True, "output": str(output), "context": context}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
