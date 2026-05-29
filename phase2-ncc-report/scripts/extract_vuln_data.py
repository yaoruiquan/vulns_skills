#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从本地漏洞材料中提取 NCC 平台上报所需字段。"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Dict, Iterable, Optional

from docx import Document

from compress_upload_zip import compress_zip_if_needed


SKILL_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = SKILL_DIR / ".env"
DEFAULT_DATA_DIR = os.path.expanduser("~/vulns/date")
MATERIAL_PREFIXES = ("CNVD-", "CNNVD-", "NCC-")
DAS_ID_RE = re.compile(r"(DAS-T\d+)", re.IGNORECASE)
RISK_LEVEL_RE = re.compile(r"风险等级[:：]\s*([^\s]+)")
VERSION_RE = re.compile(r"\b(?:v(?:ersion)?\s*)?(\d+(?:\.\d+){1,4}(?:[-_][0-9A-Za-z.]+)?)\b", re.IGNORECASE)
CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
MARKDOWN_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
MARKDOWN_LIST_RE = re.compile(r"^\s*[-*+]\s+", re.MULTILINE)
GENERATOR_PREFIX_RE = re.compile(r"^\s*经恒脑AI代码审计智能体分析[:：]\s*")
GENERATOR_BOILERPLATE_RE = re.compile(r"此分析报告由恒脑AI代码审计智能体自动生成，并经过人工核验。?")
ZIP_SEARCH_DIRS = (
    "exp",
    "poc",
    "PoC",
    "EXP",
    "附件",
)
SCREENSHOT_DIRS = (
    "exp验证图片",
    "poc验证图片",
    "PoC验证图片",
    "验证图片",
    "screenshots",
    "screenshot",
    "images",
)
VIDEO_DIRS = (
    "exp验证视频",
    "poc验证视频",
    "PoC验证视频",
    "验证视频",
    "videos",
    "video",
)
SCREENSHOT_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
YES_VALUES = {"是", "yes", "y", "true", "1", "对", "有"}
NO_VALUES = {"否", "no", "n", "false", "0", "不", "无"}
NCC_BUSINESS_TYPE = "通用型漏洞"
NCC_TARGET_TYPE_OPTIONS = (
    "操作系统",
    "应用程序",
    "WEB应用",
    "数据库",
    "网络设备（交换机、路由器等网络端设备）",
    "安全产品",
    "智能设备（物联网终端设备）",
    "区块链公链",
    "区块链联盟链",
    "区块链外围系统",
    "车联网",
    "工业控制系统",
)
NCC_COUNTRY_OPTIONS = {
    "中国大陆",
    "中国香港特别行政区",
    "中国澳门特别行政区",
    "中国台湾",
    "美国",
    "德国",
    "法国",
    "英国",
    "日本",
    "韩国",
    "加拿大",
    "澳大利亚",
    "新加坡",
    "荷兰",
    "瑞士",
    "瑞典",
    "俄罗斯",
    "以色列",
    "印度",
}
VENDOR_COUNTRY_KEYWORDS = (
    ("中国台湾", ("d-link", "dlink")),
    ("美国", ("apache", "activemq", "apisix", "seatunnel", "dotcms", "freebsd", "microsoft", "oracle", "cisco", "google")),
    ("中国大陆", ("dataease", "datagear", "ujcms", "novel-plus", "rebuild", "杭州安恒", "安恒")),
)
NCC_DETAIL_CATEGORY_OPTIONS = (
    "SQL注入",
    "XML实体注入",
    "XSS",
    "SSRF",
    "CSRF",
    "弱口令",
    "文件上传",
    "信息泄露",
    "未授权访问",
    "逻辑缺陷",
    "文件包含",
    "命令执行",
    "目录遍历",
    "任意文件下载",
    "任意文件读取",
    "拒绝服务",
    "二进制",
    "工控设备",
    "服务参数注入",
    "点击劫持",
    "其他",
)
NCC_DETAIL_CATEGORY_KEYWORDS = (
    ("SQL注入", (r"SQL\s*注入", r"\bsqli\b", r"jdbc", r"查询.*注入")),
    ("XML实体注入", (r"XML\s*实体", r"\bXXE\b", r"外部实体")),
    ("XSS", (r"\bXSS\b", r"跨站脚本")),
    ("SSRF", (r"\bSSRF\b", r"服务器端请求伪造", r"服务端请求伪造")),
    ("CSRF", (r"\bCSRF\b", r"跨站请求伪造")),
    ("弱口令", (r"弱口令", r"默认口令", r"默认密码")),
    ("文件上传", (r"文件上传", r"上传绕过", r"任意上传")),
    ("信息泄露", (r"信息泄露", r"敏感信息", r"数据泄露")),
    ("未授权访问", (r"未授权", r"越权访问", r"认证绕过", r"权限绕过", r"身份伪造")),
    ("逻辑缺陷", (r"逻辑缺陷", r"业务逻辑", r"逻辑漏洞")),
    ("文件包含", (r"(?<!二进制)文件包含", r"\bLFI\b", r"\bRFI\b")),
    ("二进制", (r"二进制", r"越界", r"溢出", r"heap", r"buffer", r"asan", r"内存", r"反序列化", r"释放后使用", r"UAF")),
    ("命令执行", (r"命令执行", r"代码执行", r"远程执行", r"\bRCE\b")),
    ("目录遍历", (r"目录遍历", r"路径遍历", r"path traversal")),
    ("任意文件下载", (r"任意文件下载", r"文件下载")),
    ("任意文件读取", (r"任意文件读取", r"文件读取")),
    ("拒绝服务", (r"拒绝服务", r"\bDoS\b", r"\bDDoS\b", r"崩溃", r"死循环")),
    ("工控设备", (r"工控", r"工业控制", r"PLC", r"SCADA")),
    ("服务参数注入", (r"服务参数注入", r"参数注入")),
    ("点击劫持", (r"点击劫持", r"clickjacking")),
)


def load_env() -> None:
    """加载 skill 根目录下的 .env。"""
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


load_env()

PYTHON_PROJECT_PATH = os.environ.get("PYTHON_PROJECT_PATH", "")
if PYTHON_PROJECT_PATH and os.path.isdir(PYTHON_PROJECT_PATH):
    sys.path.insert(0, PYTHON_PROJECT_PATH)

DEFAULT_DATA_DIR = os.environ.get("VULN_DATA_DIR", DEFAULT_DATA_DIR)


def normalize_text(value: str) -> str:
    """清理首尾空白，保留正文换行。"""
    return html.unescape(value or "").strip()


def upload_work_dir() -> Path:
    """读取运行时 zip 副本目录。"""
    base = Path(os.environ.get("NCC_UPLOAD_WORK_DIR", "/tmp")).expanduser()
    return base / "vulns-skills" / "phase2-ncc-report" / "upload-zips"


def clean_text_for_textarea(value: str, max_chars: int = 0) -> str:
    """把 Markdown/代码块清成适合 NCC textarea 的纯文本。"""
    text = normalize_text(value)
    if not text:
        return ""

    text = GENERATOR_PREFIX_RE.sub("", text)
    text = GENERATOR_BOILERPLATE_RE.sub("", text)
    text = CODE_BLOCK_RE.sub("", text)
    text = INLINE_CODE_RE.sub(r"\1", text)
    text = MARKDOWN_LINK_RE.sub(r"\1", text)
    text = MARKDOWN_HEADING_RE.sub("", text)
    text = MARKDOWN_LIST_RE.sub("", text)
    text = text.replace("\\\n", "\n")

    cleaned_lines = []
    blank_seen = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if not blank_seen and cleaned_lines:
                cleaned_lines.append("")
            blank_seen = True
            continue
        cleaned_lines.append(line)
        blank_seen = False

    text = "\n".join(cleaned_lines).strip()
    if max_chars and len(text) > max_chars:
        cut = text[:max_chars].rstrip()
        sentence_end = max(cut.rfind("。"), cut.rfind("\n"), cut.rfind("；"))
        if sentence_end > max_chars * 0.55:
            cut = cut[: sentence_end + 1].rstrip()
        text = f"{cut}\n\n详见附件中的完整验证材料。"
    return text


def first_value(fields: Dict[str, str], *keys: str, default: str = "") -> str:
    """按候选字段名取第一个非空值。"""
    for key in keys:
        value = normalize_text(fields.get(key, ""))
        if value:
            return value
    return default


def normalize_yes_no(value: str, default: str = "") -> str:
    """把是/否、yes/no、true/false 等提示统一成 NCC 页面值。"""
    text = normalize_text(value)
    if not text:
        return default
    lowered = text.lower()
    if lowered in YES_VALUES:
        return "是"
    if lowered in NO_VALUES:
        return "否"
    compact = re.sub(r"\s+", "", lowered)
    if compact in YES_VALUES:
        return "是"
    if compact in NO_VALUES:
        return "否"
    if "是" in text and "否" not in text:
        return "是"
    if "否" in text and "是" not in text:
        return "否"
    return default or text


def is_empty_material_value(value: str) -> bool:
    """识别 Word 中的占位空值。"""
    text = normalize_text(value)
    return not text or text in {"无", "暂无", "N/A", "n/a", "none", "None", "-", "--"}


def dedupe_paths(paths: Iterable[Path]) -> list[Path]:
    """按真实路径去重并保留顺序。"""
    result = []
    seen = set()
    for path in paths:
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path.absolute()
        key = str(resolved)
        if key in seen or not path.is_file():
            continue
        seen.add(key)
        result.append(path)
    return result


def detect_material_source(path: Path) -> str:
    """根据目录前缀识别材料来源。"""
    upper_name = path.name.upper()
    for prefix in MATERIAL_PREFIXES:
        if upper_name.startswith(prefix):
            return prefix[:-1]
    return "UNKNOWN"


def extract_das_id(path: Path) -> str:
    """从路径各级目录中提取 DAS-ID。"""
    for part in [path.name, *[parent.name for parent in path.parents]]:
        match = DAS_ID_RE.search(part)
        if match:
            return match.group(1).upper()
    return ""


def is_valid_docx(path: Path) -> bool:
    """过滤掉临时 docx 文件。"""
    if path.suffix.lower() != ".docx":
        return False
    if path.name.startswith("."):
        return False
    if path.name.startswith("~$") or path.name.startswith(".~"):
        return False
    return path.is_file()


def iter_docx_files(folder: Path) -> Iterable[Path]:
    """递归遍历目录中的有效 docx 文件。"""
    for docx_path in sorted(folder.rglob("*.docx")):
        if is_valid_docx(docx_path):
            yield docx_path


def preference_rank(path: Path, prefer_source: str) -> tuple[int, str]:
    """为材料目录或文件计算优先级。"""
    upper_name = path.name.upper()
    prefer_prefix = f"{prefer_source.upper()}-"
    if upper_name.startswith(prefer_prefix):
        return (0, upper_name)
    for index, prefix in enumerate(MATERIAL_PREFIXES, start=1):
        if upper_name.startswith(prefix):
            return (index, upper_name)
    return (len(MATERIAL_PREFIXES) + 1, upper_name)


def find_matching_das_root(das_id: str, data_dir: str) -> Optional[Path]:
    """在漏洞数据根目录下查找匹配 DAS-ID 的目录。"""
    root = Path(data_dir).expanduser()
    if not root.exists():
        return None

    das_id = das_id.upper()
    for item in sorted(root.iterdir()):
        if item.is_dir() and item.name.upper().startswith(das_id):
            return item
    return None


def find_material_dir(root: Path, prefer_source: str) -> Optional[Path]:
    """在输入目录下挑选最合适的材料目录。"""
    if not root.exists():
        return None

    if root.is_file():
        return root.parent if is_valid_docx(root) else None

    if any(is_valid_docx(path) for path in root.glob("*.docx")):
        return root

    candidates = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        if any(is_valid_docx(path) for path in child.glob("*.docx")):
            candidates.append(child)

    if not candidates:
        for docx_path in iter_docx_files(root):
            return docx_path.parent
        return None

    candidates.sort(key=lambda item: preference_rank(item, prefer_source))
    return candidates[0]


def find_preferred_docx(folder: Path) -> Optional[Path]:
    """优先取材料目录根下 docx；没有则递归取第一个。"""
    direct = [path for path in sorted(folder.glob("*.docx")) if is_valid_docx(path)]
    if direct:
        return direct[0]

    for docx_path in iter_docx_files(folder):
        return docx_path
    return None


def list_files(folder: Path, pattern: str) -> list[str]:
    """按 glob 规则列出文件路径。"""
    if not folder.exists():
        return []
    return [str(path) for path in sorted(folder.glob(pattern)) if path.is_file()]


def iter_named_dir_files(material_dir: Path, names: Iterable[str], suffixes: Optional[set[str]] = None) -> Iterable[Path]:
    """递归扫描指定名称目录中的文件。"""
    wanted = {name.lower() for name in names}
    for folder in sorted(path for path in material_dir.rglob("*") if path.is_dir() and path.name.lower() in wanted):
        for file_path in sorted(path for path in folder.rglob("*") if path.is_file()):
            if suffixes and file_path.suffix.lower() not in suffixes:
                continue
            yield file_path


def iter_zip_candidates(material_dir: Path) -> list[Path]:
    """优先从 exp/poc 等目录查找 zip，找不到再退回材料目录递归。"""
    candidates = list(iter_named_dir_files(material_dir, ZIP_SEARCH_DIRS, {".zip"}))
    if not candidates:
        candidates = [path for path in sorted(material_dir.rglob("*.zip")) if path.is_file()]
    return dedupe_paths(candidates)


def sanitize_filename(value: str, fallback: str) -> str:
    """生成保留中文但避开路径危险字符的文件名片段。"""
    cleaned = re.sub(r'[\\/:*?"<>|\r\n\t]+', "-", normalize_text(value))
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .-_")
    return cleaned or fallback


def material_stem_from_dir(material_dir: Path) -> str:
    """从 CNVD/CNNVD/NCC 材料目录名推导漏洞材料名。"""
    name = material_dir.name
    for prefix in MATERIAL_PREFIXES:
        if name.upper().startswith(prefix):
            return name[len(prefix) :]
    return name


def ncc_zip_name(material_dir: Path, title: str, source_zip: Path) -> str:
    """将 CNVD/CNNVD zip 名规范成 NCC-漏洞名.zip。"""
    source_name = source_zip.name
    upper_name = source_name.upper()
    for prefix in MATERIAL_PREFIXES:
        if upper_name.startswith(prefix):
            return "NCC-" + source_name[len(prefix) :]

    base = material_stem_from_dir(material_dir) or title or source_zip.stem
    if base.upper().startswith("NCC-"):
        stem = base[4:]
    else:
        for prefix in ("CNVD-", "CNNVD-"):
            if base.upper().startswith(prefix):
                base = base[len(prefix) :]
                break
        stem = base
    return f"NCC-{sanitize_filename(stem, source_zip.stem)}.zip"


def prepare_ncc_zip_copy(source_zip: Path, material_dir: Path, title: str, das_id: str) -> Path:
    """复制原始 zip 到运行时目录，并使用 NCC 前缀文件名。"""
    target_dir = upload_work_dir() / sanitize_filename(das_id or extract_das_id(material_dir) or "unknown", "unknown")
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / ncc_zip_name(material_dir, title, source_zip)
    if not target.exists() or source_zip.stat().st_size != target.stat().st_size:
        shutil.copy2(source_zip, target)
    return target


def ncc_zip_name_from_material(material_dir: Path, title: str) -> str:
    """从材料目录或标题生成 NCC zip 文件名。"""
    base = material_stem_from_dir(material_dir) or title or "attachment"
    for prefix in ("CNVD-", "CNNVD-", "NCC-"):
        if base.upper().startswith(prefix):
            base = base[len(prefix) :]
            break
    return f"NCC-{sanitize_filename(base, 'attachment')}.zip"


def create_ncc_zip_from_material(material_dir: Path, title: str, das_id: str) -> tuple[str, list[str]]:
    """没有现成 zip 时，把 CNVD/CNNVD/NCC 材料目录打包为 NCC-*.zip。"""
    files: list[Path] = []
    for file_path in sorted(path for path in material_dir.rglob("*") if path.is_file()):
        if file_path.suffix.lower() == ".zip":
            continue
        if file_path.name.startswith(".") or file_path.name.startswith("~$"):
            continue
        files.append(file_path)

    files = dedupe_paths(files)
    if not files:
        return "", []

    target_dir = upload_work_dir() / sanitize_filename(das_id or extract_das_id(material_dir) or "unknown", "unknown")
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / ncc_zip_name_from_material(material_dir, title)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zip_handle:
        for file_path in files:
            zip_handle.write(file_path, arcname=str(file_path.relative_to(material_dir)))
    return str(target), [str(material_dir)]


def path_size_mb(path_value: str) -> float:
    """读取文件大小，单位 MiB。"""
    if not path_value:
        return 0.0
    path = Path(path_value)
    if not path.exists():
        return 0.0
    return round(path.stat().st_size / 1024 / 1024, 3)


def upload_limit_mb() -> float:
    """读取 NCC 上传大小限制。"""
    try:
        return float(os.environ.get("NCC_UPLOAD_MAX_MB", 50) or 50)
    except ValueError:
        return 50.0


def infer_product_from_title(title: str) -> str:
    """从“xxx系统...”标题中提取产品/项目名。"""
    cleaned = normalize_text(title)
    match = re.search(r"(.+?)系统", cleaned)
    if match:
        return match.group(1).strip(" -_")
    return ""


def infer_vendor(fields: Dict[str, str], title: str, affected_product: str) -> str:
    """修正“其他”等无效厂商，优先用产品名/标题推导。"""
    raw_vendor = first_value(fields, "漏洞厂商", "影响厂商", "厂商名称")
    if raw_vendor and raw_vendor not in {"其他", "未知", "无", "N/A", "n/a"}:
        return raw_vendor

    product = infer_product_from_title(title) or re.split(r"\s+", affected_product.strip())[0]
    return product or raw_vendor


def extract_version(value: str) -> str:
    """从带描述的版本字段中提取纯版本号。"""
    text = normalize_text(value)
    if not text:
        return ""
    match = VERSION_RE.search(text)
    return match.group(1) if match else text


def normalize_product_version(fields: Dict[str, str], title: str) -> tuple[str, str]:
    """清洗 affected_product/version，避免混入“已复现”等验证描述。"""
    raw_product = first_value(fields, "影响产品", "受影响实体", "产品名称")
    raw_version = first_value(fields, "影响版本", "受影响实体版本号", "版本号")
    inferred_product = infer_product_from_title(title)
    version = extract_version(raw_version or raw_product)

    polluted_product = bool(re.search(r"已在|版本复现|复现|验证|影响版本", raw_product))
    product = raw_product
    if polluted_product or not product:
        product = " ".join(part for part in (inferred_product, version) if part).strip()
    elif version and version not in product and not re.search(r"[<>=≤≥]", product):
        product = f"{product} {version}".strip()

    return product, version or raw_version


def infer_target_type(fields: Dict[str, str], title: str, affected_product: str, detail_category: str = "") -> str:
    """把材料里的影响对象归一到 NCC 页面允许选项。"""
    explicit = first_value(fields, "影响对象类型", "影响对象", "受影响实体分类")
    if explicit in NCC_TARGET_TYPE_OPTIONS:
        return explicit

    text = "\n".join([explicit, title, affected_product, detail_category, first_value(fields, "漏洞类型")]).lower()
    if re.search(r"windows|linux|ubuntu|centos|debian|freebsd|android|ios|操作系统|\bos\b", text, re.IGNORECASE):
        return "操作系统"
    if re.search(r"mysql|postgres|postgresql|oracle|sql server|sqlite|redis|mongodb|数据库", text, re.IGNORECASE):
        return "数据库"
    if re.search(r"router|switch|交换机|路由器|网关|d-link|tplink|tp-link|di-\d|网络设备", text, re.IGNORECASE):
        return "网络设备（交换机、路由器等网络端设备）"
    if re.search(r"防火墙|waf|ids|ips|堡垒机|安全产品", text, re.IGNORECASE):
        return "安全产品"
    if re.search(r"iot|摄像头|智能设备|物联网", text, re.IGNORECASE):
        return "智能设备（物联网终端设备）"
    if re.search(r"工控|plc|scada|工业控制", text, re.IGNORECASE):
        return "工业控制系统"
    if re.search(r"车联网|汽车|车载", text, re.IGNORECASE):
        return "车联网"
    if re.search(r"区块链|公链", text, re.IGNORECASE):
        return "区块链公链"
    if re.search(r"联盟链", text, re.IGNORECASE):
        return "区块链联盟链"
    if re.search(r"钱包|交易所|区块链外围", text, re.IGNORECASE):
        return "区块链外围系统"
    if re.search(r"web|http|cms|servlet|controller|接口|网站|平台|网关|api", text, re.IGNORECASE):
        return "WEB应用"
    return "应用程序"


def infer_vendor_country(fields: Dict[str, str], unit_name: str, affected_product: str, title: str) -> str:
    """根据厂商/产品常见归属推断 NCC 国家/地区下拉值。"""
    explicit = first_value(fields, "厂商所属国家", "产品厂商国家", "所属国家", "国家", "国家地区", "国家/地区")
    if explicit in NCC_COUNTRY_OPTIONS:
        return explicit

    text = "\n".join([unit_name, affected_product, title]).lower()
    for country, keywords in VENDOR_COUNTRY_KEYWORDS:
        if any(keyword.lower() in text for keyword in keywords):
            return country
    return "中国大陆"


def classify_detail(fields: Dict[str, str], title: str, description: str) -> str:
    """给 NCC 漏洞详细分类提供可直接选择的候选值。"""
    explicit = first_value(fields, "漏洞详细分类", "详细分类", "漏洞类型")
    if explicit in NCC_DETAIL_CATEGORY_OPTIONS:
        return explicit

    text = "\n".join(
        [
            explicit,
            title,
            description,
            first_value(fields, "漏洞危害", "漏洞分析"),
        ]
    )
    for category, patterns in NCC_DETAIL_CATEGORY_KEYWORDS:
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
            return category
    return "其他"


def extract_http_request_block(text: str) -> str:
    """从材料文本中提取原始 HTTP 请求块。"""
    raw = normalize_text(text)
    if not raw:
        return ""
    lines = raw.splitlines()
    start_index = -1
    request_line_re = re.compile(r"^\s*(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+.+\s+HTTP/\d(?:\.\d)?\s*$", re.I)
    for index, line in enumerate(lines):
        if request_line_re.match(line):
            start_index = index
            break
    if start_index < 0:
        return ""

    collected: list[str] = []
    for offset, line in enumerate(lines[start_index:]):
        stripped = line.strip()
        if collected and not stripped:
            remaining = lines[start_index + offset + 1 :]
            next_text = next((candidate.strip() for candidate in remaining if candidate.strip()), "")
            if not next_text or re.match(r"^[\u4e00-\u9fff].{0,30}$", next_text):
                break
            collected.append("")
            continue
        if collected and re.match(r"^(漏洞|修复|影响|危害|复现|分析|证明|备注|解决方案|步骤)\S{0,12}[:：]?$", stripped):
            break
        if collected and stripped.startswith(("###", "## ", "# ")):
            break
        collected.append(line.rstrip())
        if len("\n".join(collected)) > 5000:
            break
    return "\n".join(collected).strip()


def extract_curl_command_block(text: str) -> str:
    """从材料文本中提取已有 curl PoC 命令。"""
    raw = normalize_text(text)
    if not raw:
        return ""
    lines = raw.splitlines()
    start_index = -1
    for index, line in enumerate(lines):
        if re.match(r"^\s*curl\s+", line):
            start_index = index
            break
    if start_index < 0:
        return ""

    collected: list[str] = []
    for line in lines[start_index:]:
        stripped = line.strip()
        if collected and not stripped:
            break
        if collected and re.match(r"^(漏洞|修复|影响|危害|复现|分析|证明|备注|解决方案|步骤)\S{0,12}[:：]?$", stripped):
            break
        if collected and not collected[-1].rstrip().endswith("\\"):
            break
        collected.append(line.rstrip())
        if len("\n".join(collected)) > 5000:
            break
    return "\n".join(collected).strip()


def extract_poc_text(fields: Dict[str, str], url: str, request_method: str, detail_category: str = "") -> str:
    """从 Word 中提取 NCC 动态 PoC 字段文本；仅 SQL 注入需要已有真实 PoC。"""
    if detail_category != "SQL注入":
        return "见附件"

    candidate_values = [
        first_value(fields, "SQL注入Poc", "SQL注入POC", "SQL注入PoC", "POC", "PoC", "poc", "完整PoC描述"),
        first_value(fields, "漏洞验证过程", "验证过程", "漏洞验证", "漏洞分析"),
    ]
    for value in candidate_values:
        request_block = extract_http_request_block(value)
        if request_block:
            return request_block
        curl_block = extract_curl_command_block(value)
        if curl_block:
            return curl_block

    return "见附件"


def extract_poc_text_legacy(fields: Dict[str, str], url: str, request_method: str) -> str:
    """保留旧 PoC 提取逻辑，必要时可用于人工复核。"""
    parts: list[str] = []
    for label, keys in (
        ("触发条件", ("漏洞触发条件", "触发条件")),
        ("请求方式", ("请求方式",)),
        ("漏洞URL", ("漏洞URL", "漏洞定位")),
        ("利用工具", ("利用工具",)),
        ("工具指令", ("工具指令",)),
        ("弱口令账号/密码", ("弱口令账号\\密码", "弱口令账号/密码")),
        ("XSS payload", ("触发XSS payload", "XSS payload")),
        ("验证过程", ("漏洞验证过程", "验证过程", "漏洞验证")),
    ):
        value = first_value(fields, *keys)
        if label == "请求方式" and not value:
            value = request_method
        if label == "漏洞URL" and not value:
            value = url
        if is_empty_material_value(value):
            continue
        cleaned = clean_text_for_textarea(value, max_chars=360)
        if cleaned:
            parts.append(f"{label}：{cleaned}")

    if parts:
        return "\n".join(parts)
    return "PoC、验证截图和验证视频见附件压缩包。"


def collect_attachments(material_dir: Path, title: str = "", das_id: str = "") -> Dict[str, object]:
    """收集材料目录中的附件。"""
    docx_path = find_preferred_docx(material_dir)

    source_zip_paths = iter_zip_candidates(material_dir)
    ncc_zip_path = ""
    created_from_dirs: list[str] = []
    compression_result: Dict[str, object] = {}
    if source_zip_paths:
        ncc_zip_path = str(prepare_ncc_zip_copy(source_zip_paths[0], material_dir, title, das_id))
    else:
        ncc_zip_path, created_from_dirs = create_ncc_zip_from_material(material_dir, title, das_id)
    prepared_zip_path = ncc_zip_path
    if ncc_zip_path:
        try:
            compression_result = compress_zip_if_needed(Path(ncc_zip_path))
            ncc_zip_path = str(compression_result.get("path") or ncc_zip_path)
        except Exception as exc:  # pragma: no cover - defensive guard for corrupt zips/runtime ffmpeg issues
            compression_result = {
                "path": ncc_zip_path,
                "original_path": prepared_zip_path,
                "original_size_mb": path_size_mb(prepared_zip_path),
                "size_mb": path_size_mb(ncc_zip_path),
                "limit_mb": upload_limit_mb(),
                "compressed": False,
                "attempted": True,
                "ok": path_size_mb(ncc_zip_path) <= upload_limit_mb(),
                "warnings": [f"upload zip video compression failed: {exc}"],
            }

    screenshot_paths = [str(path) for path in dedupe_paths(iter_named_dir_files(material_dir, SCREENSHOT_DIRS, SCREENSHOT_SUFFIXES))]

    video_paths = [str(path) for path in dedupe_paths(iter_named_dir_files(material_dir, VIDEO_DIRS, VIDEO_SUFFIXES))]

    upload_files = []
    if ncc_zip_path:
        upload_files.append(ncc_zip_path)
    upload_zip_path_obj = Path(ncc_zip_path) if ncc_zip_path else Path()
    upload_zip_exists = bool(ncc_zip_path and upload_zip_path_obj.is_file() and upload_zip_path_obj.stat().st_size > 0)

    return {
        "docx_path": str(docx_path) if docx_path else "",
        "upload_zip_path": ncc_zip_path,
        "upload_zip_basename": upload_zip_path_obj.name if ncc_zip_path else "",
        "upload_zip_dir": str(upload_zip_path_obj.parent) if ncc_zip_path else "",
        "upload_zip_exists": upload_zip_exists,
        "upload_zip_prepared_path": prepared_zip_path,
        "upload_zip_source_path": str(source_zip_paths[0]) if source_zip_paths else "",
        "upload_zip_created": bool(ncc_zip_path and not source_zip_paths),
        "upload_zip_created_from_dirs": created_from_dirs,
        "upload_zip_size_mb": compression_result.get("size_mb", path_size_mb(ncc_zip_path)),
        "upload_zip_original_size_mb": compression_result.get("original_size_mb", path_size_mb(prepared_zip_path)),
        "upload_zip_limit_mb": compression_result.get("limit_mb", upload_limit_mb()),
        "upload_zip_within_limit": compression_result.get("ok", path_size_mb(ncc_zip_path) <= upload_limit_mb()),
        "upload_zip_compressed": compression_result.get("compressed", False),
        "upload_zip_compression": compression_result,
        "zip_paths": [ncc_zip_path] if ncc_zip_path else [],
        "source_zip_paths": [str(path) for path in source_zip_paths],
        "screenshot_paths": screenshot_paths,
        "video_paths": video_paths,
        "all_upload_files": upload_files,
    }


def extract_fields_from_docx(doc_path: Path) -> Dict[str, str]:
    """从 docx 提取键值字段，兼容 CNVD/CNNVD 表格和 NCC 段落模板。"""
    doc = Document(str(doc_path))
    table = doc.tables[0] if doc.tables else None
    fields: Dict[str, str] = {}
    if table:
        for row in table.rows:
            cells = row.cells
            if len(cells) < 2:
                continue
            key = normalize_text(cells[0].text)
            value = normalize_text(cells[1].text)
            if key and value:
                fields[key] = value
        if fields:
            return fields

    paragraphs = [normalize_text(paragraph.text) for paragraph in doc.paragraphs]
    paragraphs = [text for text in paragraphs if text]

    def value_after_prefix(prefixes: tuple[str, ...]) -> str:
        for text in paragraphs:
            compact = text.replace("：", ":")
            for prefix in prefixes:
                if compact.startswith(prefix):
                    return normalize_text(compact.split(":", 1)[1] if ":" in compact else "")
        return ""

    def collect_between(start_prefixes: tuple[str, ...], end_prefixes: tuple[str, ...]) -> str:
        collecting = False
        values: list[str] = []
        for text in paragraphs:
            if not collecting and any(text.startswith(prefix) for prefix in start_prefixes):
                collecting = True
                suffix = text.split("：", 1)[1] if "：" in text else text.split(":", 1)[1] if ":" in text else ""
                if suffix.strip():
                    values.append(suffix.strip())
                continue
            if collecting and any(text.startswith(prefix) for prefix in end_prefixes):
                break
            if collecting:
                values.append(text)
        return "\n".join(value for value in values if value).strip()

    fields.update(
        {
            "漏洞名称": value_after_prefix(("漏洞报告标题",)),
            "提交日期": value_after_prefix(("漏洞发现时间",)),
            "漏洞类型": value_after_prefix(("漏洞技术类型",)),
            "漏洞厂商": value_after_prefix(("漏洞厂商全称",)),
            "影响产品": value_after_prefix(("已知受影响产品及版本",)),
            "影响版本": extract_version(value_after_prefix(("已知受影响产品及版本",))),
            "漏洞描述": collect_between(("漏洞描述",), ("漏洞危害",)),
            "漏洞危害": collect_between(("漏洞危害",), ("漏洞厂商全称",)),
            "漏洞触发条件": value_after_prefix(("2）触发条件",)),
            "漏洞验证过程": "\n".join(
                value
                for value in [
                    collect_between(("1）完整PoC描述",), ("2）触发条件",)),
                    collect_between(("1）基础环境搭建",), ("2）漏洞触发操作",)),
                    collect_between(("2）漏洞触发操作",), ("3）复现注意事项",)),
                ]
                if value
            ),
            "临时解决方案": collect_between(("3、修复方案",), ("4、备注",)),
        }
    )
    fields = {key: value for key, value in fields.items() if normalize_text(value)}
    return fields


def extract_risk_level(fields: Dict[str, str]) -> str:
    """尝试从材料文本中提取风险等级。"""
    for key in ("漏洞危害", "漏洞分析", "漏洞描述"):
        match = RISK_LEVEL_RE.search(fields.get(key, ""))
        if match:
            return match.group(1)
    return ""


def impact_from_description(description: str) -> str:
    """从已清洗描述中提炼 NCC 可读的危害摘要。"""
    text = clean_text_for_textarea(description, max_chars=520)
    if not text:
        return ""
    if "导致" in text or "造成" in text or "攻击者" in text:
        return text
    return f"{text}\n\n可能造成系统异常、服务不可用或进一步安全影响，详见附件验证材料。"


def extract_impact(fields: Dict[str, str], description: str = "") -> str:
    """优先返回可直接填表的危害摘要。"""
    return "见附件"


def extract_impact_legacy(fields: Dict[str, str], description: str = "") -> str:
    """保留旧危害摘要逻辑，必要时可用于人工复核。"""
    direct = first_value(fields, "漏洞危害")
    if direct and not is_empty_material_value(direct):
        if (len(direct) > 700 or "环境搭建" in direct or "EXP 实际运行结果" in direct) and description:
            return impact_from_description(description)
        return clean_text_for_textarea(direct, max_chars=700)

    analysis = first_value(fields, "漏洞分析")
    if not analysis or is_empty_material_value(analysis):
        return impact_from_description(description)

    summary = clean_text_for_textarea(analysis, max_chars=700)
    for marker in ("源码证据", "利用链", "验证过程", "EXP 实际运行结果", "EXP使用说明", "EXP 使用说明"):
        if marker in summary:
            summary = summary.split(marker, 1)[0].strip()
    summary = summary.replace("此分析报告由恒脑AI代码审计智能体自动生成，并经过人工核验。", "").strip()
    if not summary:
        return impact_from_description(description)
    if (len(summary) > 700 or "环境搭建" in summary or "EXP 实际运行结果" in summary) and description:
        return impact_from_description(description)
    return summary


def resolve_input(args: argparse.Namespace) -> tuple[Optional[Path], Optional[Path], str]:
    """解析脚本输入，得到材料目录和 docx 文件。"""
    prefer_source = args.prefer_source.upper()

    if args.docx_path:
        docx_path = Path(args.docx_path).expanduser()
        if not is_valid_docx(docx_path):
            return None, None, f"无效的 docx 文件: {docx_path}"
        return docx_path.parent, docx_path, ""

    if args.input_path:
        input_path = Path(args.input_path).expanduser()
        if not input_path.exists():
            return None, None, f"输入路径不存在: {input_path}"
        material_dir = find_material_dir(input_path, prefer_source)
        if not material_dir:
            return None, None, f"未在输入路径中找到材料目录: {input_path}"
        docx_path = find_preferred_docx(material_dir)
        if not docx_path:
            return None, None, f"材料目录中未找到 docx: {material_dir}"
        return material_dir, docx_path, ""

    if args.das_id:
        das_root = find_matching_das_root(args.das_id, args.data_dir)
        if not das_root:
            return None, None, f"未找到 DAS 目录: {args.das_id}"
        material_dir = find_material_dir(das_root, prefer_source)
        if not material_dir:
            return None, None, f"未在 DAS 目录中找到材料目录: {das_root}"
        docx_path = find_preferred_docx(material_dir)
        if not docx_path:
            return None, None, f"材料目录中未找到 docx: {material_dir}"
        return material_dir, docx_path, ""

    return None, None, "缺少输入参数，请提供 DAS-ID、--input-path 或 --docx-path"


def extract_ncc_data(material_dir: Path, docx_path: Path) -> Dict[str, object]:
    """提取 NCC 平台上报所需的统一数据。"""
    fields = extract_fields_from_docx(docx_path)
    das_root = material_dir.parent if material_dir.parent != material_dir else material_dir
    das_id = extract_das_id(material_dir) or extract_das_id(docx_path)
    title = clean_text_for_textarea(first_value(fields, "漏洞名称"), max_chars=180)
    description = clean_text_for_textarea(first_value(fields, "漏洞描述", "漏洞简介"), max_chars=900)
    affected_product, version = normalize_product_version(fields, title)
    unit_name = infer_vendor(fields, title, affected_product)
    attachments = collect_attachments(material_dir, title=title, das_id=das_id)
    detail_category = classify_detail(fields, title, description)
    target_type = infer_target_type(fields, title, affected_product, detail_category)
    vendor_country = infer_vendor_country(fields, unit_name, affected_product, title)
    url = first_value(fields, "漏洞URL", "漏洞定位")
    request_method = first_value(fields, "请求方式")
    poc_text = extract_poc_text(fields, url, request_method, detail_category)
    is_original = normalize_yes_no(first_value(fields, "是否为原创漏洞", "是否原创漏洞", "是否原创"), default="")
    is_0day = normalize_yes_no(
        first_value(fields, "是否0Day漏洞", "是否0day漏洞", "是否 0Day 漏洞", "0Day漏洞", "零日漏洞"),
        default="",
    )

    data: Dict[str, object] = {
        "platform": "NCC",
        "das_id": das_id,
        "input_root": str(das_root),
        "material_dir": str(material_dir),
        "material_source": detect_material_source(material_dir),
        "docx_path": attachments["docx_path"],
        "upload_zip_path": attachments["upload_zip_path"],
        "upload_zip_basename": attachments["upload_zip_basename"],
        "upload_zip_dir": attachments["upload_zip_dir"],
        "upload_zip_exists": attachments["upload_zip_exists"],
        "upload_zip_prepared_path": attachments["upload_zip_prepared_path"],
        "upload_zip_source_path": attachments["upload_zip_source_path"],
        "upload_zip_created": attachments["upload_zip_created"],
        "upload_zip_created_from_dirs": attachments["upload_zip_created_from_dirs"],
        "upload_zip_size_mb": attachments["upload_zip_size_mb"],
        "upload_zip_original_size_mb": attachments["upload_zip_original_size_mb"],
        "upload_zip_limit_mb": attachments["upload_zip_limit_mb"],
        "upload_zip_within_limit": attachments["upload_zip_within_limit"],
        "upload_zip_compressed": attachments["upload_zip_compressed"],
        "upload_zip_compression": attachments["upload_zip_compression"],
        "zip_paths": attachments["zip_paths"],
        "source_zip_paths": attachments["source_zip_paths"],
        "screenshot_paths": attachments["screenshot_paths"],
        "video_paths": attachments["video_paths"],
        "all_upload_files": attachments["all_upload_files"],
        "title": title,
        "description": description,
        "impact": extract_impact(fields, description),
        "vuln_type": first_value(fields, "漏洞类型"),
        "business_type": NCC_BUSINESS_TYPE,
        "detail_category": detail_category,
        "target_type": target_type,
        "vendor_country": vendor_country,
        "url": url,
        "unit_name": unit_name,
        "vendor_website": first_value(fields, "厂商官网"),
        "affected_product": affected_product,
        "version": version,
        "request_method": request_method,
        "discoverer_name": first_value(fields, "提交人员", "发现者"),
        "contact": first_value(fields, "联系方式", "联系电话"),
        "submit_org": first_value(fields, "提交机构"),
        "submit_date": first_value(fields, "提交日期"),
        "verification": clean_text_for_textarea(first_value(fields, "漏洞验证过程", "验证过程", "漏洞验证"), max_chars=800),
        "temporary_solution": "见附件",
        "formal_solution": "见附件",
        "risk_level": extract_risk_level(fields),
        "is_0day": is_0day,
        "is_original": is_original,
        "poc_text": poc_text,
        "trigger_location": first_value(fields, "漏洞定位", "漏洞URL", default="见附件"),
        "browser_defaults": {
            "is_0day": is_0day,
            "is_original": is_original,
            "business_type": NCC_BUSINESS_TYPE,
            "detail_category": detail_category,
            "target_type": target_type,
            "vendor_country": vendor_country,
            "binary_required_fields": {
                "版本号": version or "见附件",
                "触发位置": first_value(fields, "漏洞定位", "漏洞URL", default="见附件"),
                "PoC": poc_text,
            },
            "attachment_policy": "NCC 页面可能是单文件上传；默认只上传 upload_zip_path，不再补传 docx/截图/视频，避免替换 zip。",
        },
    }

    return data


def build_parser() -> argparse.ArgumentParser:
    """构造命令行参数解析器。"""
    parser = argparse.ArgumentParser(description="提取 NCC 平台上报字段")
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
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    material_dir, docx_path, error = resolve_input(args)
    if error:
        print(json.dumps({"error": error}, ensure_ascii=False, indent=2))
        return 1

    assert material_dir is not None
    assert docx_path is not None
    data = extract_ncc_data(material_dir, docx_path)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
