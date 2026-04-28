#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 CNNVD 浏览器填表阶段唯一使用的 form_context.json。"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from compress_zip import ensure_submission_zip
from extract_vuln_data import DEFAULT_DATA_DIR, extract_cnnvd_data, resolve_target


DEFAULT_FORM_CONTEXT_DIR = os.environ.get(
    "FORM_CONTEXT_DIR",
    "/tmp/vulns-skills/phase2-cnnvd-report/form-contexts",
)
DEFAULT_OCR_PORT = int(os.environ.get("CAPTCHA_OCR_PORT", "18766"))
DEFAULT_OCR_SERVER_URL = os.environ.get("CAPTCHA_OCR_SERVER_URL", f"http://127.0.0.1:{DEFAULT_OCR_PORT}")


def clip_text(text: str, max_length: int) -> str:
    """按字符数裁剪文本。"""
    cleaned = (text or "").strip()
    if len(cleaned) <= max_length:
        return cleaned
    return cleaned[:max_length].rstrip()


def infer_entity_description(product: str, category: str, title: str) -> tuple[str, str]:
    """为受影响实体描述提供兜底文本；优先用 --entity-description 覆盖。"""
    text = f"{product} {title}".lower()
    product_name = (product or title.split("存在", 1)[0]).strip() or "该产品"

    if "emlog" in text:
        return (
            "emlog 是一款基于 PHP 的开源博客和内容管理系统，常用于个人博客、轻量级网站和内容发布场景，支持模板、插件和后台管理功能。",
            "heuristic",
        )
    if "invoiceplane" in text:
        return (
            "InvoicePlane 是一款开源发票和客户管理系统，常用于小型企业的报价、发票、付款和客户信息管理场景。",
            "heuristic",
        )

    templates = {
        "建站系统": f"{product_name} 是一类网站建设或内容管理相关系统，常用于网站内容发布、模板管理、插件扩展和后台维护等场景。",
        "web应用": f"{product_name} 是一类 Web 应用系统，通常通过浏览器访问，用于业务管理、数据处理或在线服务等场景。",
        "中间件": f"{product_name} 是一类服务端中间件组件，通常用于承载 Web 服务、应用运行、请求转发或业务系统集成。",
        "数据库": f"{product_name} 是一类数据存储和管理系统，常用于业务数据的查询、写入、索引和权限管理等场景。",
        "操作系统": f"{product_name} 是一类操作系统或系统组件，负责提供基础运行环境、资源调度、文件管理和应用支撑能力。",
    }
    return templates.get(
        category,
        f"{product_name} 是相关业务系统或软件组件，常用于特定业务场景中的数据处理、功能配置和后台管理。",
    ), "heuristic"


def find_context_window(source: str, keywords: tuple[str, ...], window: int = 90) -> str:
    """从长文本中截取包含关键词的一小段。"""
    for keyword in keywords:
        index = source.find(keyword)
        if index >= 0:
            start = max(0, index - window // 3)
            end = min(len(source), index + window)
            return source[start:end].strip()
    return ""


def summarize_verification(source: str, title: str, vuln_type: str) -> tuple[str, str]:
    """将 verification_source 压缩为第三页可填写的一段话。"""
    source = (source or "").strip()
    if not source:
        return "", "missing"

    product = (title or "目标系统").split("存在", 1)[0].strip() or "目标系统"
    source_lower = source.lower()

    if "zip" in source_lower and "上传" in source and "路径遍历" in source:
        return (
            f"验证过程显示，{product}的压缩包上传或解压流程存在路径校验不足问题。测试中构造包含合法文件和路径遍历文件名的 ZIP 包并通过后台上传，服务端校验通过后直接解压压缩包内容，导致恶意文件可被写入预期目录之外的可访问位置。随后访问写入文件可触发服务端代码执行，证明该文件上传链路可被实际利用。",
            "auto_summary",
        )

    if ("文件包含" in title or "include" in source_lower) and "上传" in source:
        return (
            f"验证过程显示，{product}的相关功能会将用户可控路径传入文件加载或包含逻辑。测试中先上传可控文件，再通过受影响入口构造请求触发包含流程，服务端未对最终包含路径进行有效限制，导致上传文件内容被加载执行。该过程证明漏洞可造成任意文件包含，并可能进一步导致代码执行。",
            "auto_summary",
        )

    if any(keyword in source for keyword in ("命令执行", "代码执行", "RCE")):
        return (
            f"验证过程显示，{product}的受影响入口会处理用户可控参数。测试中构造恶意输入并触发相关功能后，服务端未对参数进行充分校验或隔离，导致攻击载荷进入危险执行逻辑。通过观察命令执行结果、文件写入或页面回显，可证明该漏洞具备实际利用条件。",
            "auto_summary",
        )

    entry = find_context_window(source, ("入口", "Source", "访问路径", "上传功能", "函数"))
    exploit = find_context_window(source, ("构造", "上传", "触发", "路径遍历", "注入", "解压", "token"))
    result = find_context_window(source, ("成功", "执行", "返回", "写入", "RCE", "证明", "回显"))

    parts = []
    if entry:
        parts.append(f"验证过程显示，漏洞入口位于{entry}。")
    else:
        parts.append(f"验证过程显示，{title} 可通过相关功能入口触发。")
    if exploit and exploit not in entry:
        parts.append(f"测试中通过{exploit}完成漏洞触发。")
    if result:
        parts.append(f"最终观察到{result}，证明该{vuln_type or '漏洞'}可被实际利用。")

    summary = clip_text("".join(parts), 300)
    return summary, "auto_summary"


def file_status(path_value: str) -> dict:
    """返回文件存在性和大小信息。"""
    path = Path(path_value) if path_value else None
    if not path:
        return {
            "exists": False,
            "is_file": False,
            "size_mb": 0,
            "suffix": "",
            "name_starts_with_cnnvd": False,
        }
    exists = path.exists()
    is_file = path.is_file()
    size_mb = round(path.stat().st_size / 1024 / 1024, 2) if exists else 0
    return {
        "exists": exists,
        "is_file": is_file,
        "size_mb": size_mb if is_file else 0,
        "suffix": path.suffix.lower(),
        "name_starts_with_cnnvd": path.name.upper().startswith("CNNVD"),
    }


def find_submission_zip_path(folder_path: str) -> str:
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
            if path.name.upper().startswith("CNNVD"):
                candidates.append(path)
    if not candidates:
        return ""
    return str(max(candidates, key=lambda item: item.stat().st_size))


def resolve_vuln_type_path(vuln_type: str) -> list[str]:
    """将漏洞类型映射成 CNNVD 级联下拉路径。"""
    text = (vuln_type or "").strip()
    mapping = [
        (("命令执行", "命令注入"), ["代码问题", "输入验证错误", "注入", "命令注入"]),
        (("SQL注入", "sql注入"), ["代码问题", "输入验证错误", "注入", "SQL注入"]),
        (("XSS", "跨站脚本"), ["代码问题", "输入验证错误", "注入", "跨站脚本"]),
        (("代码执行", "代码注入"), ["代码问题", "输入验证错误", "注入", "代码注入"]),
        (("文件包含", "路径遍历", "目录遍历"), ["代码问题", "输入验证错误", "路径遍历"]),
        (("文件上传",), ["代码问题", "输入验证错误", "后置链接"]),
        (("CSRF", "跨站请求伪造"), ["代码问题", "输入验证错误", "跨站请求伪造"]),
        (("越界", "溢出", "缓冲区", "二进制", "UAF", "uaf"), ["代码问题", "输入验证错误", "缓冲区错误"]),
        (("格式化字符串",), ["代码问题", "输入验证错误", "注入", "格式化字符串错误"]),
        (("权限绕过", "未授权访问", "访问控制"), ["代码问题", "授权问题", "权限许可和访问控制问题"]),
        (("信任边界",), ["代码问题", "授权问题", "信任管理问题"]),
    ]
    for keywords, path in mapping:
        if any(keyword in text for keyword in keywords):
            return path
    return ["其他"]


def build_context(args: argparse.Namespace) -> dict:
    """构建完整 FormContext。"""
    das_id, data_dir, doc_path_override = resolve_target(args.target, "CNNVD", args.data_dir)
    context = extract_cnnvd_data(das_id, data_dir, doc_path_override)
    if context.get("error"):
        return context

    entity_description = (args.entity_description or context.get("entity_description") or "").strip()
    entity_description_source = context.get("entity_description_source", "websearch")
    if entity_description:
        entity_description_source = "manual" if args.entity_description else entity_description_source
    else:
        entity_description, entity_description_source = infer_entity_description(
            context.get("affected_product", ""),
            context.get("affected_entity_category", ""),
            context.get("title", ""),
        )

    verification = (args.verification or "").strip()
    verification_source_type = "manual" if verification else ""
    if not verification:
        verification, verification_source_type = summarize_verification(
            context.get("verification_source", ""),
            context.get("title", ""),
            context.get("vuln_type", ""),
        )

    context["schema"] = "cnnvd_form_context_v1"
    context["platform"] = "CNNVD"
    context["generated_at"] = datetime.now().isoformat(timespec="seconds")
    context["source_target"] = args.target
    context["resolved_data_dir"] = data_dir
    context["entity_description"] = clip_text(entity_description, 120)
    context["entity_description_source"] = entity_description_source
    context["verification"] = clip_text(verification, 300)
    context["verification_source_type"] = verification_source_type
    context["dropdown_plan"] = {
        "vuln_type_path": resolve_vuln_type_path(context.get("vuln_type", "")),
        "risk_level": context.get("risk_level", ""),
        "affected_entity_category": context.get("affected_entity_category", ""),
    }
    context["page_payloads"] = {
        "page1_dropdowns": {
            "vuln_type_path": resolve_vuln_type_path(context.get("vuln_type", "")),
            "risk_level": context.get("risk_level", ""),
            "affected_entity_category": context.get("affected_entity_category", ""),
        },
        "page1_text": {
            "title": context.get("title", ""),
            "affected_product": context.get("affected_product", ""),
            "version": context.get("version", ""),
            "entity_description": clip_text(entity_description, 120),
        },
        "page2_text": {
            "description": clip_text(context.get("description", ""), 255),
            "technical_support": context.get("technical_support", ""),
            "contact": context.get("contact", ""),
        },
        "page3_text": {
            "verification": clip_text(verification, 300),
        },
        "page3_uploads": {
            "verification_video_path": context.get("verification_video_path", ""),
            "poc_file_path": context.get("poc_file_path", ""),
        },
    }
    context["interaction_rules"] = {
        "snapshot_budget": "每页仅在进入页面、下拉联动确认、提交结果确认时 take_snapshot；不要为单个字段反复截图。",
        "fill_rule": "每页按 page_payloads 一次性填写，不要在第 2 页和第 3 页重新提取或总结。",
        "dropdown_rule": "优先按 dropdown_plan 直接选择；级联下拉点击最终叶子项前面的圆圈/单选按钮，不要按 Escape。",
    }
    context["ocr"] = {
        "preferred_server_url": DEFAULT_OCR_SERVER_URL,
        "start_command": f"python3 scripts/captcha_ocr.py --serve --port {DEFAULT_OCR_PORT}",
        "recognize_command": f"python3 scripts/captcha_ocr.py /tmp/captcha.png --server-url {DEFAULT_OCR_SERVER_URL}",
        "submit_rule": "如遇验证码，优先走常驻 OCR 服务；识别后直接填入并提交，不要再 take_snapshot。",
    }

    video_status = file_status(context.get("verification_video_path", ""))
    poc_status = file_status(context.get("poc_file_path", ""))
    submission_zip_path = find_submission_zip_path(context.get("folder_path", ""))
    if not submission_zip_path:
        submission_zip_path = ensure_submission_zip(context.get("folder_path", ""))
    submission_zip_status = file_status(submission_zip_path)

    checks = {
        "description_len_ok": len(context.get("description", "")) <= 255,
        "entity_description_ready": bool(context.get("entity_description")),
        "verification_ready": bool(context.get("verification")),
        "video_exists": video_status["exists"],
        "poc_exists": poc_status["exists"],
        "no_browser_phase_extraction": True,
    }
    context["file_checks"] = {
        "verification_video": video_status,
        "poc_file": poc_status,
    }
    context["submission_zip_path"] = submission_zip_path
    context["submission_zip_status"] = submission_zip_status
    context["publish_checks"] = {
        "submission_zip_exists": submission_zip_status["exists"],
        "submission_zip_is_file": submission_zip_status["is_file"],
        "submission_zip_is_zip": submission_zip_status["suffix"] == ".zip",
        "submission_zip_name_starts_with_cnnvd": submission_zip_status["name_starts_with_cnnvd"],
    }
    context["publish_ready"] = all(context["publish_checks"].values())
    context["checks"] = checks
    context["ready"] = all(checks.values())
    context["browser_phase_rule"] = (
        "浏览器阶段只能读取本 form_context.json；按 dropdown_plan 和 page_payloads 分页填写；第 2 页和第 3 页禁止重新运行提取脚本或重新总结。"
    )
    context["dingtalk"] = {
        "success_title": "监管上报 CNNVD 上报完成",
        "success_text_template": (
            f"漏洞名称：{context.get('title', '')}\\n"
            f"DAS-ID：{context.get('das_id', '')}\\n"
            "CNNVD 编号：{cnnvd_id}"
        ),
        "failed_title": "监管上报 CNNVD 上报失败",
    }

    return context


def default_context_output(context: dict) -> Path:
    """默认将运行时 JSON 写入 /tmp，避免污染 CNNVD 提交材料目录。"""
    generated_at = context.get("generated_at") or datetime.now().isoformat(timespec="seconds")
    month = generated_at[:7]
    das_id = context.get("das_id") or "unknown-das"
    return Path(DEFAULT_FORM_CONTEXT_DIR).expanduser() / month / das_id / "form_context.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="准备 CNNVD 表单上下文 JSON")
    parser.add_argument("target", help="DAS-ID、DAS 目录路径或 CNNVD docx 路径")
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR, help="漏洞数据根目录")
    parser.add_argument("--output", default="", help="输出 form_context.json 路径；默认写入 /tmp/vulns-skills/phase2-cnnvd-report/form-contexts/YYYY-MM/DAS-ID/")
    parser.add_argument("--entity-description", default="", help="websearch 后整理的受影响实体描述")
    parser.add_argument("--verification", default="", help="根据 verification_source 总结压缩后的验证过程")
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
