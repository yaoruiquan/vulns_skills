#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 docx 提取漏洞数据，供 CNVD/CNNVD 上报使用"""

import sys
import os
import json
import re
from pathlib import Path

from docx import Document
from typing import Dict, Optional

# 导入配置模块
try:
    from config import get_company_name, get_data_dir, get_default_phone
    DEFAULT_DATA_DIR = get_data_dir()
except ImportError:
    DEFAULT_DATA_DIR = "/Users/yao/LLM/vulns/date"

    def get_company_name() -> str:
        return "杭州安恒信息技术股份有限公司"

    def get_default_phone() -> str:
        return "15700082275"


def find_docx_path(das_id: str, platform: str, data_dir: str = DEFAULT_DATA_DIR) -> Optional[str]:
    """查找漏洞 docx 文件路径"""
    for item in os.listdir(data_dir):
        item_path = os.path.join(data_dir, item)
        if item.startswith(das_id) and os.path.isdir(item_path):
            vuln_folder = item_path
            # 查找平台子目录
            for sub in os.listdir(vuln_folder):
                sub_path = os.path.join(vuln_folder, sub)
                if sub.startswith(f"{platform}-") and os.path.isdir(sub_path):
                    platform_folder = sub_path
                    for f in os.listdir(platform_folder):
                        f_path = os.path.join(platform_folder, f)
                        if f.endswith('.docx') and not f.startswith('.') and os.path.isfile(f_path):
                            return f_path
    return None


def extract_das_id_from_name(name: str) -> str:
    """从 DAS 目录名或文件名中提取 DAS-ID"""
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


def resolve_target(input_value: str, platform: str, data_dir: str) -> tuple[str, str, Optional[str]]:
    """兼容 DAS-ID、DAS 目录路径和 docx 路径三种输入形式"""
    target = Path(input_value).expanduser()
    if not target.exists():
        return input_value, data_dir, None

    if target.is_file() and target.suffix.lower() == ".docx":
        das_id = extract_das_id_from_path(target) or input_value
        return das_id, str(target.parent.parent), str(target)

    if target.is_dir():
        das_id = extract_das_id_from_path(target) or target.name
        # 如果传入的是平台子目录（如 CNNVD-xxx 或 CNVD-xxx），直接在其中查找 docx
        if target.name.startswith(f"{platform}-"):
            docx_files = [
                path for path in target.iterdir()
                if path.is_file() and path.suffix.lower() == ".docx" and not path.name.startswith(".")
            ]
            if docx_files:
                doc_path = str(sorted(docx_files, key=lambda p: p.name)[0])
                return das_id, str(target.parent), doc_path
            return das_id, str(target.parent), None
        # 如果传入的是 DAS 根目录（以 DAS- 开头）
        if target.name.startswith("DAS-"):
            doc_path = find_docx_path(das_id, platform, str(target.parent))
            return das_id, str(target.parent), doc_path
        # 其他情况：传入的是批次目录，在其中查找 DAS 目录
        doc_path = find_docx_path(das_id, platform, str(target))
        return das_id, str(target), doc_path

    return input_value, data_dir, None


def extract_fields_from_docx(doc_path: str) -> Dict[str, str]:
    """从 docx 的所有表格中提取字段"""
    doc = Document(doc_path)
    fields = {}
    for table in doc.tables:
        for row in table.rows:
            cells = row.cells
            if len(cells) >= 2:
                key = cells[0].text.strip()
                val = cells[1].text.strip()
                if key and val:
                    fields[key] = val
    return fields


def clean_ai_prefix(text: str) -> str:
    """去掉简介中不应填写到平台的固定分析前缀"""
    cleaned = (text or "").strip()
    cleaned = re.sub(
        r"^\s*经恒脑\s*AI\s*代码审计智能体分析[:：]\s*",
        "",
        cleaned,
        count=1,
    )
    return cleaned.strip()


def limit_text(text: str, max_length: int) -> str:
    """限制平台字段长度，避免页面校验失败"""
    cleaned = (text or "").strip()
    if len(cleaned) <= max_length:
        return cleaned
    return cleaned[:max_length].rstrip()


def normalize_one_paragraph(text: str) -> str:
    """将 Word 中的多段验证过程清理为一段纯文本，供后续总结压缩使用"""
    cleaned = (text or "").strip()
    markers = [
        "此分析报告由VF自动生成，并经过人工核验。",
        "此分析报告由恒脑AI代码审计智能体自动生成，并经过人工核验。",
        "（更多成果请查看VF官网：https://v.das-ai.com/）",
        "（查看恒脑AI代码审计智能体官网: https://www.dbappsecurity.com.cn/）",
        "（查看恒脑AI代码审计智能体官网：https://www.dbappsecurity.com.cn/）",
    ]
    for marker in markers:
        cleaned = cleaned.replace(marker, " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def normalize_risk_level(value: str) -> str:
    """CNNVD 漏洞自评级必填，Word 为空时使用高危兜底"""
    text = (value or "").strip()
    for level in ("超危", "高危", "中危", "低危"):
        if level in text:
            return level
    return "高危"


def infer_entity_category(fields: Dict[str, str]) -> str:
    """受影响实体分类为必填下拉框，优先使用 Word 字段，否则根据 URL/名称保守推断"""
    explicit = (fields.get("受影响实体分类", "") or fields.get("影响对象类型", "")).strip()
    options = (
        "浏览器", "办公软件", "数据库", "web应用", "建站系统", "操作系统", "图像处理软件",
        "OA系统", "PDF编辑、阅读器", "主流电子邮件网站", "电子邮件服务器", "电子邮件客户端",
        "压缩软件", "视频播放软件", "网页插件", "杀毒软件", "驱动程序", "工控设备",
        "打印机", "社交软件", "工控软件", "网络设备", "安全设备", "运营商核心网元设备",
        "APP", "虚拟化平台", "安防系统", "系统工具", "其他软件", "中间件", "其他",
    )
    for option in options:
        if option in explicit:
            return option

    title = fields.get("漏洞名称", "")
    title_lower = title.lower()
    location = fields.get("漏洞定位", "")

    if any(word in title_lower for word in ("emlog", "wordpress", "drupal", "discuz", "dedecms", "pbootcms", "thinkcmf", "joomla", "cms")):
        return "建站系统"
    if any(word in title for word in ("通达", "泛微", "致远", "蓝凌", "OA", "协同办公")):
        return "OA系统"
    if any(word in title_lower for word in ("tomcat", "weblogic", "websphere", "jboss", "jetty", "nginx", "apache", "iis", "php-fpm")):
        return "中间件"
    if any(word in title_lower for word in ("mysql", "postgresql", "oracle", "sql server", "redis", "mongodb", "mariadb")) or "数据库" in title:
        return "数据库"
    if any(word in title_lower for word in ("chrome", "edge", "firefox", "safari")):
        return "浏览器"
    if any(word in title for word in ("内核", "Linux", "Windows", "macOS", "操作系统", "Ubuntu", "CentOS", "Debian", "麒麟", "UOS")):
        return "操作系统"
    if any(word in title for word in ("防火墙", "WAF", "网闸", "堡垒机", "安全")):
        return "安全设备"
    if any(word in title for word in ("路由器", "交换机", "网关", "AP", "控制器")):
        return "网络设备"
    if any(word in title for word in ("APP", "Android", "iOS", "小程序")):
        return "APP"
    if location.startswith(("http://", "https://")):
        return "web应用"
    if any(word in title for word in ("系统", "平台", "网站", "Web", "web")):
        return "web应用"
    return "其他软件"


def find_first_file(folder_path: str, subdir_names: tuple, extensions: tuple) -> str:
    """在指定子目录中查找第一个匹配附件"""
    folder = Path(folder_path)
    for subdir_name in subdir_names:
        subdir = folder / subdir_name
        if not subdir.is_dir():
            continue
        files = [
            path for path in subdir.rglob("*")
            if path.is_file()
            and not path.name.startswith(".")
            and path.suffix.lower() in extensions
        ]
        if files:
            return str(sorted(files, key=lambda path: path.name)[0])
    return ""


def map_cnvd_vuln_type(vuln_type_text: str) -> str:
    """将漏洞类型文本映射为 CNVD 表单值"""
    mapping = {
        "SQL注入": "sql注入",
        "XSS": "跨站脚本",
        "SSRF": "其他",
        "弱口令": "其他",
        "文件上传": "文件上传",
        "信息泄露": "信息泄露",
        "未授权访问": "其他",
        "逻辑缺陷": "其他",
        "文件包含": "其他",
        "命令执行": "其他",
        "代码执行": "其他",
        "反序列化": "其他",
        "目录遍历": "其他",
        "越界": "其他",
        "溢出": "其他",
        "内存": "其他",
    }
    for key, val in mapping.items():
        if key in vuln_type_text:
            return val
    return "其他"


def map_soft_style(obj_type_text: str) -> str:
    """将影响对象类型映射为 CNVD 表单值"""
    mapping = {
        "WEB应用": "29",
        "操作系统": "27",
        "应用程序": "28",
        "数据库": "30",
        "网络设备": "31",
        "安全产品": "32",
        "智能设备": "33",
        "工业控制": "38",
    }
    for key, val in mapping.items():
        if key in obj_type_text:
            return val
    return "28"


def extract_cnvd_data(das_id: str, data_dir: str = DEFAULT_DATA_DIR, doc_path_override: Optional[str] = None) -> Dict[str, str]:
    """提取 CNVD 上报所需数据"""
    doc_path = doc_path_override or find_docx_path(das_id, "CNVD", data_dir)
    if not doc_path:
        return {"error": f"未找到 CNVD docx: {das_id}"}

    fields = extract_fields_from_docx(doc_path)
    folder_path = os.path.dirname(doc_path)

    return {
        "das_id": das_id,
        "title": fields.get("漏洞名称", ""),
        "description": fields.get("漏洞描述", ""),
        "vuln_type": map_cnvd_vuln_type(fields.get("漏洞类型", "")),
        "vuln_type_raw": fields.get("漏洞类型", ""),
        "url": fields.get("漏洞URL", ""),
        "unit_name": fields.get("漏洞厂商", ""),
        "is_event": "0",  # 默认通用型
        "soft_style_id": map_soft_style(fields.get("影响对象类型", "")),
        "discoverer_name": fields.get("提交人员", ""),
        "affected_product": fields.get("影响产品", ""),
        "version": fields.get("影响版本", ""),
        "folder_path": folder_path,
        "docx_path": doc_path,
    }


def extract_cnnvd_data(das_id: str, data_dir: str = DEFAULT_DATA_DIR, doc_path_override: Optional[str] = None) -> Dict[str, str]:
    """提取 CNNVD 上报所需数据"""
    doc_path = doc_path_override or find_docx_path(das_id, "CNNVD", data_dir)
    if not doc_path:
        return {"error": f"未找到 CNNVD docx: {das_id}"}

    fields = extract_fields_from_docx(doc_path)
    folder_path = os.path.dirname(doc_path)
    description_full = clean_ai_prefix(fields.get("漏洞简介", "") or fields.get("漏洞描述", ""))
    description = limit_text(description_full, 255)
    verification_source = normalize_one_paragraph(fields.get("漏洞验证过程", ""))
    contact = fields.get("联系方式", "").strip() or get_default_phone()
    affected_product = (
        fields.get("受影响实体名称", "").strip()
        or fields.get("影响产品", "").strip()
        or fields.get("漏洞名称", "").split("存在", 1)[0].strip()
    )
    version = fields.get("受影响实体版本号", "").strip() or fields.get("影响版本", "").strip()
    unit_name = fields.get("受影响实体厂商名称", "").strip() or fields.get("漏洞厂商", "").strip()
    verification_video_path = find_first_file(
        folder_path,
        ("exp验证视频", "poc验证视频", "验证视频", "视频", "video"),
        (".mp4", ".mov", ".avi", ".mkv", ".webm"),
    )
    poc_file_path = find_first_file(
        folder_path,
        ("exp", "poc", "POC", "PoC"),
        (".zip", ".rar", ".7z", ".tar", ".gz", ".py", ".txt", ".md"),
    )

    return {
        "das_id": das_id,
        "title": fields.get("漏洞名称", ""),
        "description": description,
        "description_full": description_full,
        "description_max_length": 255,
        "description_truncated": description != description_full,
        "vuln_type": fields.get("漏洞类型", ""),
        "risk_level": normalize_risk_level(fields.get("危害等级", "")),
        "affected_entity_category": infer_entity_category(fields),
        "url": fields.get("漏洞定位", ""),
        "unit_name": unit_name,
        "affected_product": affected_product,
        "version": version,
        "entity_description": fields.get("受影响实体描述", "").strip(),
        "entity_description_required": True,
        "entity_description_source": "websearch",
        "discoverer_name": fields.get("提交人员", ""),
        "technical_support": get_company_name(),
        "contact": contact,
        "verification": "",
        "verification_source": verification_source,
        "verification_summary_required": True,
        "verification_video_path": verification_video_path,
        "poc_file_path": poc_file_path,
        "folder_path": folder_path,
        "docx_path": doc_path,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 extract_vuln_data.py <das_id|das_dir|docx_path> [--platform CNVD|CNNVD] [--data-dir <path>]")
        print("  默认平台: CNVD")
        sys.exit(1)

    target_input = sys.argv[1]
    platform = "CNVD"
    data_dir = DEFAULT_DATA_DIR

    # 解析参数
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--platform" and i + 1 < len(sys.argv):
            platform = sys.argv[i + 1].upper()
            i += 2
        elif sys.argv[i] == "--data-dir" and i + 1 < len(sys.argv):
            data_dir = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    # 提取数据
    das_id, resolved_data_dir, doc_path_override = resolve_target(target_input, platform, data_dir)

    if platform == "CNNVD":
        data = extract_cnnvd_data(das_id, resolved_data_dir, doc_path_override)
    else:
        data = extract_cnvd_data(das_id, resolved_data_dir, doc_path_override)

    # 输出 JSON
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
