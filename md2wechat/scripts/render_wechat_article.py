#!/usr/bin/env python3
"""Render vulnerability alert Markdown into deterministic WeChat article HTML."""

from __future__ import annotations

import argparse
import base64
import html
import os
import re
import urllib.request
import urllib.parse
import json as json_lib
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = SKILL_ROOT / "assets" / "wechat-alert-article-template.placeholders.html"
DEFAULT_MICROSOFT_TEMPLATE = SKILL_ROOT / "assets" / "wechat-microsoft-monthly-template.placeholders.html"
DEFAULT_HEADER_IMAGE = SKILL_ROOT / "assets" / "logo.png"

FORBIDDEN_OUTPUT = ("<style", "<script", "class=", "contenteditable=", "ProseMirror", "onclick=")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
SCREENSHOT_PATTERN = re.compile(r"复现|截图|reproduce|screenshot|poc|图\d+", re.I)
LOGO_PATTERN = re.compile(r"logo|封面|cover|header|banner", re.I)
CVE_PATTERN = re.compile(r"CVE-\d{4}-\d{4,}", re.I)
TITLE_PREFIX_PATTERN = re.compile(r"^(【[^】]*】)\s*")


def load_local_env() -> None:
    """Load the skill-local .env when WeChat credentials are not already set."""
    env_path = SKILL_ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key in os.environ:
            continue
        os.environ[key] = value.strip().strip('"').strip("'")


@dataclass
class AlertData:
    title: str = ""
    intro: list[str] = field(default_factory=list)
    reproduction_note: str = ""
    reproduction_images: list[Path] = field(default_factory=list)
    product_intro: str = ""
    description: list[str] = field(default_factory=list)
    impact: list[str] = field(default_factory=list)
    official_fix: list[str] = field(default_factory=list)
    temporary_fix: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    overview: dict[str, str] = field(default_factory=dict)
    product_coverage: list[list[str]] = field(default_factory=list)


@dataclass
class MicrosoftVulnerability:
    title: str = ""
    description: str = ""
    vuln_type: str = ""
    cve_id: str = ""
    cnvd_id: str = ""
    cnnvd_id: str = ""
    antian_cert_id: str = ""
    cvss_score: str = ""
    severity: str = ""
    cvss_vector: dict[str, str] = field(default_factory=dict)
    reference: str = ""


@dataclass
class MicrosoftMonthlyReport:
    title: str = ""
    notice: list[str] = field(default_factory=list)
    product_intro: list[str] = field(default_factory=list)
    zero_day_note: str = ""
    highlighted_vulns: list[str] = field(default_factory=list)
    critical_vulns: list[str] = field(default_factory=list)
    vulnerabilities: list[MicrosoftVulnerability] = field(default_factory=list)
    official_fix: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._current_table: list[list[str]] | None = None
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "table":
            self._current_table = []
        elif tag == "tr" and self._current_table is not None:
            self._current_row = []
        elif tag in {"td", "th"} and self._current_row is not None:
            self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"td", "th"} and self._current_cell is not None and self._current_row is not None:
            value = normalize_space("".join(self._current_cell))
            self._current_row.append(value)
            self._current_cell = None
        elif tag == "tr" and self._current_row is not None and self._current_table is not None:
            if any(cell.strip() for cell in self._current_row):
                self._current_table.append(self._current_row)
            self._current_row = None
        elif tag == "table" and self._current_table is not None:
            self.tables.append(self._current_table)
            self._current_table = None

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._current_cell.append(data)


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def strip_markdown(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    text = re.sub(r"(?m)^\s{0,3}>\s?", "", text)
    text = re.sub(r"[*_`#]+", "", text)
    return normalize_space(text)


def escape(text: str) -> str:
    return html.escape(text or "", quote=True)


def extract_cve(markdown: str) -> str:
    match = CVE_PATTERN.search(markdown)
    return match.group(0).upper() if match else ""


def strip_title_prefix(title: str) -> str:
    return TITLE_PREFIX_PATTERN.sub("", title or "").strip()


def title_has_cve(title: str) -> bool:
    return bool(CVE_PATTERN.search(title or ""))


def append_cve_to_title(title: str, cve: str) -> str:
    title = normalize_space(title)
    if cve and not title_has_cve(title):
        title = f"{title}（{cve}）"
    return title


def infer_article_prefix(markdown: str, source: Path, title: str = "") -> str:
    for candidate in (source.stem, title):
        match = TITLE_PREFIX_PATTERN.match(candidate or "")
        if match:
            return match.group(1)

    for line in markdown.splitlines():
        match = re.match(r"^\s{0,3}#\s+(.+?)\s*$", line)
        if not match:
            continue
        heading = strip_markdown(match.group(1))
        prefix_match = TITLE_PREFIX_PATTERN.match(heading)
        if prefix_match:
            return prefix_match.group(1)

    if re.search(r"已复现|复现截图|复现结果|复现成功", markdown, re.I):
        return "【已复现】"
    for image in source.parent.iterdir() if source.parent.is_dir() else []:
        if image.is_file() and image.suffix.lower() in IMAGE_EXTENSIONS and SCREENSHOT_PATTERN.search(image.name):
            return "【已复现】"
    return "【风险通告】"


def format_article_title(markdown: str, source: Path, raw_title: str) -> str:
    cve = extract_cve(markdown)
    prefix = infer_article_prefix(markdown, source, raw_title)
    base_title = append_cve_to_title(strip_title_prefix(raw_title), cve)
    return f"{prefix}{base_title}" if prefix and not base_title.startswith("【") else base_title


def extract_tables(markdown: str) -> list[list[list[str]]]:
    pipe_tables = extract_pipe_tables(markdown)
    if pipe_tables:
        return pipe_tables
    regex_tables = extract_tables_lenient(markdown)
    if regex_tables:
        return regex_tables
    parser = TableParser()
    parser.feed(markdown)
    return parser.tables


def extract_pipe_tables(markdown: str) -> list[list[list[str]]]:
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [normalize_space(cell) for cell in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", cell.strip()) for cell in cells if cell.strip()):
                continue
            current.append(cells)
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    return tables


def extract_tables_lenient(markdown: str) -> list[list[list[str]]]:
    """Extract HTML tables from imperfect Markdown-exported HTML."""
    tables: list[list[list[str]]] = []
    for table_html in re.findall(r"<table\b.*?</table>", markdown, flags=re.I | re.S):
        rows: list[list[str]] = []
        for row_match in re.finditer(r"<tr\b[^>]*>(.*?)(?=<tr\b|</table>)", table_html, flags=re.I | re.S):
            row_html = row_match.group(1)
            cells = []
            for cell_html in re.findall(r"<t[dh]\b[^>]*>(.*?)(?=<t[dh]\b|</tr>|$)", row_html, flags=re.I | re.S):
                text = re.sub(r"<br\s*/?>", " ", cell_html, flags=re.I)
                text = re.sub(r"<[^>]+>", "", text)
                value = normalize_space(text)
                if value:
                    cells.append(value)
            if not cells:
                text = re.sub(r"<br\s*/?>", " ", row_html, flags=re.I)
                text = re.sub(r"<[^>]+>", "", text)
                value = normalize_space(text)
                if value:
                    cells.append(value)
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables


def remove_html_tables(markdown: str) -> str:
    return re.sub(r"<table\b.*?</table>", "", markdown, flags=re.I | re.S)


def split_sections(markdown: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {"__preface__": []}
    current = "__preface__"
    for line in markdown.splitlines():
        heading = parse_section_heading(line)
        if heading:
            if is_fix_subheading(heading) and current in {"修复方案", "修复建议"}:
                sections.setdefault(current, []).append(line)
                continue
            current = heading
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return {key: "\n".join(value).strip() for key, value in sections.items()}


def parse_section_heading(line: str) -> str:
    markdown_match = re.match(r"^\s{0,3}#{1,6}\s*(.+?)\s*$", line)
    if markdown_match:
        return normalize_heading(markdown_match.group(1))

    text = strip_markdown(line)
    if not re.match(r"^(?:第?[一二三四五六七八九十]+|[0-9]+)[、.．]\s*", text):
        return ""
    heading = normalize_heading(text)
    known_sections = ("安全通告", "漏洞信息", "漏洞描述", "影响范围", "修复方案", "修复建议", "参考资料", "产品能力覆盖")
    if any(section in heading for section in known_sections):
        return heading
    return ""


def is_fix_subheading(heading: str) -> bool:
    return heading in {"官方修复方案", "临时缓解方案", "官方修复建议", "临时缓解建议"}


def normalize_heading(text: str) -> str:
    text = strip_markdown(text)
    text = re.sub(r"^(?:第?[一二三四五六七八九十]+|[0-9]+)[、.．]\s*", "", text)
    return text.replace(" ", "")


def markdown_image_references(markdown: str, source: Path) -> list[tuple[str, Path]]:
    """Return local Markdown image references as (alt, path) pairs."""
    directory = source.parent
    refs: list[tuple[str, Path]] = []
    for match in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", markdown):
        alt = normalize_space(match.group(1))
        raw_target = match.group(2).strip()
        raw_target = raw_target.split(None, 1)[0].strip("<>")
        if not raw_target or re.match(r"^(?:https?:|data:)", raw_target, re.I):
            continue
        parsed = urllib.parse.urlparse(raw_target)
        if parsed.scheme:
            continue
        local_path = directory / urllib.parse.unquote(parsed.path)
        if local_path.is_file() and local_path.suffix.lower() in IMAGE_EXTENSIONS:
            refs.append((alt, local_path.resolve()))
    return refs


def missing_markdown_images(markdown: str, source: Path) -> list[str]:
    """Return missing local Markdown image targets for summary/reporting."""
    directory = source.parent
    missing: list[str] = []
    for match in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", markdown):
        alt = normalize_space(match.group(1))
        raw_target = match.group(2).strip()
        raw_target = raw_target.split(None, 1)[0].strip("<>")
        if not raw_target or re.match(r"^(?:https?:|data:)", raw_target, re.I):
            continue
        parsed = urllib.parse.urlparse(raw_target)
        if parsed.scheme:
            continue
        local_path = directory / urllib.parse.unquote(parsed.path)
        marker = f"{alt} {Path(parsed.path).name}"
        if local_path.is_file():
            continue
        if SCREENSHOT_PATTERN.search(marker) and not LOGO_PATTERN.search(marker):
            missing.append(raw_target)
    return list(dict.fromkeys(missing))


def find_reproduction_screenshots(source: Path, title: str, markdown: str = "") -> list[Path]:
    """Find reproduction screenshots in the same directory as the markdown file.

    Matches are determined by extracting identifiers from the title (CVE ID,
    product name keywords) and looking for image files in the source directory
    that match those identifiers or common screenshot naming patterns.
    """
    directory = source.parent
    if not directory.is_dir():
        return []

    referenced: list[Path] = []
    referenced_fallback: list[Path] = []
    for alt, image_path in markdown_image_references(markdown, source):
        marker = f"{alt} {image_path.name}"
        if LOGO_PATTERN.search(marker):
            continue
        if SCREENSHOT_PATTERN.search(marker):
            referenced.append(image_path)
        else:
            referenced_fallback.append(image_path)
    if referenced:
        return list(dict.fromkeys(referenced))

    cve_match = re.search(r"CVE-\d{4}-\d{4,}", title, re.I)
    cve_id = cve_match.group(0) if cve_match else None
    source_stem = source.stem

    image_files = sorted(
        f for f in directory.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    )

    if not image_files:
        return list(dict.fromkeys(referenced_fallback))

    matched: list[Path] = []
    unmatched: list[Path] = []

    for f in image_files:
        name_lower = f.stem.lower()
        if LOGO_PATTERN.search(f.name):
            continue
        if cve_id and cve_id.lower() in name_lower:
            matched.append(f)
        elif source_stem.lower() in name_lower and source_stem.lower():
            matched.append(f)
        elif SCREENSHOT_PATTERN.search(name_lower):
            matched.append(f)
        else:
            unmatched.append(f)

    result = sorted(matched, key=lambda p: p.stem)
    if not result:
        result = referenced_fallback or sorted(unmatched, key=lambda p: p.stem)
    return result


def find_section(sections: dict[str, str], *keywords: str) -> str:
    for heading, body in sections.items():
        if all(keyword in heading for keyword in keywords):
            return body
    return ""


def markdown_blocks(text: str) -> list[str]:
    text = remove_html_tables(text)
    blocks: list[str] = []
    current: list[str] = []
    in_code = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.strip().startswith("```"):
            in_code = not in_code
            current.append(line)
            continue
        if in_code:
            current.append(line)
            continue
        if not line.strip():
            if current:
                blocks.append("\n".join(current).strip())
                current = []
            continue
        current.append(line)
    if current:
        blocks.append("\n".join(current).strip())
    return blocks


def plain_paragraphs(text: str) -> list[str]:
    result: list[str] = []
    for block in markdown_blocks(text):
        if not block or re.fullmatch(r"!\[[^\]]*\]\([^)]+\)", block.strip()):
            continue
        if block.lstrip().startswith("|"):
            continue
        if block.startswith("```"):
            continue
        lines = [line.strip() for line in block.splitlines()]
        cleaned = strip_markdown(" ".join(lines))
        if cleaned:
            result.append(cleaned)
    return result


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？!?])\s*", strip_markdown(text))
    return [part.strip() for part in parts if part.strip()]


def infer_hazard_description(paragraphs: Iterable[str]) -> str:
    marker_re = re.compile(r"危害|高危|严重|权限提升|远程代码执行|任意代码|命令执行|信息泄露|拒绝服务|绕过|接管")
    fallback = ""
    for paragraph_text in paragraphs:
        for sentence in split_sentences(paragraph_text):
            if not marker_re.search(sentence):
                continue
            sentence = re.sub(r"^(?:近日|近期|目前)[，,]?", "", sentence).strip()
            sentence = re.sub(r"^安恒CERT(?:监测到|发现|关注到)[，,]?", "", sentence).strip()
            if "危害" in sentence or "高危" in sentence or "严重" in sentence:
                return sentence[:180]
            fallback = fallback or sentence[:180]
    return fallback


def extract_title(markdown: str, overview: dict[str, str], source: Path) -> str:
    stem = source.stem

    if overview.get("漏洞标题") or overview.get("漏洞名称"):
        raw_title = overview.get("漏洞标题") or overview.get("漏洞名称") or stem
        return format_article_title(markdown, source, raw_title)
    in_code = False
    for line in markdown.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        match = re.match(r"^\s{0,3}#\s+(.+?)\s*$", line)
        if match:
            title = strip_markdown(match.group(1))
            if not re.match(r"^[一二三四五六七八九十0-9]+[、.．]", title):
                return format_article_title(markdown, source, title)
    raw_title = overview.get("漏洞标题") or overview.get("漏洞名称") or stem
    return format_article_title(markdown, source, raw_title)


def table_to_key_values(table: list[list[str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in table:
        cells = [cell for cell in row if cell]
        if len(cells) == 2:
            key, value = cells
            if key not in result:
                result[key] = value
        elif len(cells) >= 4:
            for index in range(0, len(cells) - 1, 2):
                key = cells[index]
                value = cells[index + 1]
                if key and value and key not in result:
                    result[key] = value
    return result


def first_matching_value(data: dict[str, str], *keys: str, default: str = "未分配") -> str:
    for key in keys:
        if key in data and data[key]:
            return data[key]
    return default


def extract_references(text: str) -> list[str]:
    urls = re.findall(r"https?://[^\s<>\])\"']+", text)
    cleaned: list[str] = []
    for url in urls:
        url = url.rstrip("。；;，,")
        if url not in cleaned:
            cleaned.append(url)
    if cleaned:
        return cleaned
    for line in text.splitlines():
        item = strip_markdown(line)
        item = re.sub(r"^\d+[.、]\s*", "", item).strip()
        if item and item not in cleaned and not item.startswith("|"):
            cleaned.append(item)
    if cleaned:
        return cleaned
    for block in plain_paragraphs(text):
        item = re.sub(r"^\d+[.、]\s*", "", block).strip()
        if item and item not in cleaned:
            cleaned.append(item)
    return cleaned


def parse_fix_heading(block: str) -> tuple[str, str] | None:
    lines = block.strip().splitlines()
    if not lines:
        return None
    first = lines[0].strip()
    rest = "\n".join(lines[1:]).strip()

    heading_text = ""
    heading_match = re.match(r"^\s{0,3}#{1,6}\s*(.+?)\s*$", first)
    if heading_match:
        heading_text = strip_markdown(heading_match.group(1))
    else:
        first_label = strip_markdown(first)
        if re.fullmatch(r"(?:官方修复|临时缓解)(?:方案|建议)?\s*[:：]?", first_label):
            heading_text = first_label
        else:
            inline_label = re.match(r"^((?:官方修复|临时缓解)(?:方案|建议)?)\s*[:：]\s*(.+)$", first_label)
            if inline_label:
                heading_text = f"{inline_label.group(1)}：{inline_label.group(2)}"

    if not heading_text:
        return None

    match = re.match(r"^(官方修复|临时缓解)(?:方案|建议)?\s*[:：]?\s*(.*)$", heading_text)
    if not match:
        return None
    kind = "temporary" if match.group(1) == "临时缓解" else "official"
    inline_remainder = match.group(2).strip()
    remainder = "\n".join(item for item in (inline_remainder, rest) if item).strip()
    return kind, remainder


def split_fix_section(text: str) -> tuple[list[str], list[str]]:
    official: list[str] = []
    temporary: list[str] = []
    current = "official"
    for block in markdown_blocks(text):
        heading = parse_fix_heading(block)
        if heading:
            current, remainder = heading
            if remainder:
                if current == "temporary":
                    temporary.append(remainder)
                else:
                    official.append(remainder)
            continue
        if current == "temporary":
            temporary.append(block)
        else:
            official.append(block)
    return clean_blocks(official), clean_blocks(temporary)


def clean_blocks(blocks: Iterable[str]) -> list[str]:
    result: list[str] = []
    for block in blocks:
        cleaned = block.strip()
        if not cleaned:
            continue
        if cleaned in {"官方修复方案:", "官方修复方案：", "临时缓解方案:", "临时缓解方案："}:
            continue
        result.append(cleaned)
    return result


def parse_alert(markdown: str, source: Path) -> AlertData:
    tables = extract_tables(markdown)
    overview = table_to_key_values(tables[0]) if tables else {}
    sections = split_sections(markdown)
    data = AlertData(overview=overview)
    data.title = extract_title(markdown, overview, source)
    data.reproduction_images = find_reproduction_screenshots(source, data.title, markdown)

    preface = plain_paragraphs(sections.get("__preface__", ""))
    notice = plain_paragraphs(find_section(sections, "安全通告"))
    raw_intro = preface + notice
    data.intro = raw_intro
    if not data.intro:
        data.intro = [overview.get("危害描述", "")]
    data.intro = [item for item in data.intro if item]

    for paragraph in data.intro:
        if "已复现" in paragraph or "完成技术分析" in paragraph or "卫兵实验室" in paragraph:
            data.reproduction_note = paragraph
            break

    vuln_info = find_section(sections, "漏洞信息")
    vuln_paragraphs = plain_paragraphs(vuln_info)

    if (not overview.get("危害描述")) or overview.get("危害描述") in ("", "待确认"):
        inferred = infer_hazard_description(raw_intro + vuln_paragraphs)
        if inferred:
            overview["危害描述"] = inferred

    # 从正文intro中提取漏洞描述作为危害描述（去掉"近日..."监测类前缀）
    if ((not overview.get("危害描述")) or overview.get("危害描述") in ("", "待确认")) and raw_intro:
        for p in raw_intro:
            # 提取 "技术细节及PoC已公开，" 之后的版本和影响描述
            for sep in ("技术细节及PoC已公开，", "技术细节已公开，"):
                if sep in p:
                    desc = p.split(sep, 1)[1].strip()
                    if desc:
                        overview["危害描述"] = desc
                        break
            if overview.get("危害描述"):
                break

    data.intro = [item for item in data.intro if not item.startswith("近日") and not item.startswith("近期")]
    if vuln_paragraphs:
        data.product_intro = vuln_paragraphs[0]
    explicit_description = plain_paragraphs(find_section(sections, "漏洞描述"))
    if explicit_description:
        data.description = explicit_description
    elif not data.description and overview.get("危害描述"):
        data.description = [overview["危害描述"]]

    impact_lines = []
    for label in ("影响主体", "影响厂商", "影响产品", "影响版本", "安全版本"):
        value = overview.get(label)
        if value:
            impact_lines.append(f"{label}：{value}")
    data.impact = impact_lines

    fix_body = find_section(sections, "修复方案") or find_section(sections, "修复建议")
    data.official_fix, data.temporary_fix = split_fix_section(fix_body)

    ref_body = find_section(sections, "参考资料")
    data.references = extract_references(ref_body) or extract_references(markdown)

    coverage_body = find_section(sections, "产品能力覆盖")
    if coverage_body and len(tables) >= 2:
        data.product_coverage = tables[-1]

    return data


def is_microsoft_monthly_report(markdown: str, source: Path) -> bool:
    markers = ("微软", "漏洞速览表", "漏洞详情")
    if all(marker in markdown for marker in markers):
        return True
    return "微软漏洞通报" in str(source) or "微软" in source.stem


def table_items(table: list[list[str]]) -> list[str]:
    items: list[str] = []
    for row in table:
        text = strip_markdown(" ".join(cell for cell in row if cell))
        if text and text not in items:
            items.append(text)
    return items


def clean_vuln_type(value: str) -> str:
    return re.sub(r"^\s*\d+[.、]\s*", "", value).strip()


def clean_notice_text(value: str) -> str:
    value = strip_markdown(value)
    value = re.sub(r"\s*>\s*", " ", value)
    value = normalize_space(value)
    value = re.sub(r"^安全通告\s*", "", value)
    return value.strip()


def parse_microsoft_vulnerability(table: list[list[str]]) -> MicrosoftVulnerability | None:
    values = table_to_key_values(table)
    title = values.get("漏洞标题") or values.get("漏洞名称") or ""
    if not title:
        return None

    vector_keys = (
        "访问途径（AV）",
        "攻击复杂度（AC）",
        "所需权限（PR）",
        "用户交互（UI）",
        "影响范围（S）",
        "机密性影响（C）",
        "完整性影响（I）",
        "可用性影响（A）",
    )
    reference = ""
    for row in table:
        for item in row:
            match = re.search(r"https?://[^\s<>\])\"']+", item)
            if match:
                reference = match.group(0).rstrip("。；;，,")
                break
        if reference:
            break

    return MicrosoftVulnerability(
        title=title,
        description=values.get("漏洞描述", ""),
        vuln_type=clean_vuln_type(values.get("漏洞类型", "")),
        cve_id=values.get("CVE编号", ""),
        cnvd_id=values.get("CNVD编号", ""),
        cnnvd_id=values.get("CNNVD编号", ""),
        antian_cert_id=values.get("安恒CERT编号", ""),
        cvss_score=values.get("CVSS3.1评分", ""),
        severity=values.get("危害等级", "") or values.get("漏洞危害等级", ""),
        cvss_vector={key: values[key] for key in vector_keys if values.get(key)},
        reference=reference,
    )


def parse_microsoft_report(markdown: str, source: Path) -> MicrosoftMonthlyReport:
    tables = extract_tables(markdown)
    sections = split_sections(markdown)
    data = MicrosoftMonthlyReport(title=extract_title(markdown, {}, source))

    preface_items = [clean_notice_text(item) for item in plain_paragraphs(sections.get("__preface__", ""))]
    preface_items = [item for item in preface_items if item and item != "安全通告"]
    data.notice = preface_items

    vuln_info = find_section(sections, "漏洞信息")
    intro_part = vuln_info.split("**漏洞速览表**", 1)[0]
    data.product_intro = plain_paragraphs(intro_part)

    zero_day = re.search(r"(?:^|\n)\s*1[.、]?\s*(本月.*?0day.*?漏洞。?)", vuln_info, flags=re.I | re.S)
    if zero_day:
        data.zero_day_note = normalize_space(zero_day.group(1))

    summary_tables = [table for table in tables if table and all(len(row) == 1 for row in table)]
    if summary_tables:
        data.highlighted_vulns = table_items(summary_tables[0])
    if len(summary_tables) >= 2:
        data.critical_vulns = table_items(summary_tables[1])

    for table in tables:
        vuln = parse_microsoft_vulnerability(table)
        if vuln:
            data.vulnerabilities.append(vuln)

    fix_body = find_section(sections, "修复方案") or find_section(sections, "修复建议")
    data.official_fix, _ = split_fix_section(fix_body)
    if not data.official_fix:
        data.official_fix = clean_blocks(markdown_blocks(fix_body))

    ref_body = find_section(sections, "参考资料")
    data.references = extract_references(ref_body) or extract_references(markdown)
    return data


def paragraph(text: str) -> str:
    return (
        '<section style="-webkit-tap-highlight-color:transparent;padding:0px 15px;'
        'letter-spacing:0.544px;line-height:2;box-sizing:border-box;">'
        '<p style="-webkit-tap-highlight-color:transparent;margin-bottom:15px;word-break:break-all;">'
        f'<span style="font-size:15px;">{escape(text)}</span></p></section>'
    )


def block_to_html(block: str) -> str:
    block = block.strip()
    if not block:
        return ""
    if "```" in block:
        return mixed_block_to_html(block)
    return text_block_to_html(block)


def text_block_to_html(block: str) -> str:
    lines = block.splitlines()
    if all(re.match(r"^\s*[-*]\s+", line) for line in lines if line.strip()):
        items = [re.sub(r"^\s*[-*]\s+", "", line).strip() for line in lines if line.strip()]
        return unordered_list(items)
    if all(re.match(r"^\s*\d+\.\s+", line) for line in lines if line.strip()):
        items = [re.sub(r"^\s*\d+\.\s+", "", line).strip() for line in lines if line.strip()]
        return ordered_list(items)
    return paragraph(strip_markdown(block))


def mixed_block_to_html(block: str) -> str:
    parts: list[str] = []
    text_lines: list[str] = []
    code_lines: list[str] = []
    in_code = False

    def flush_text() -> None:
        if text_lines:
            rendered = text_block_to_html("\n".join(text_lines).strip())
            if rendered:
                parts.append(rendered)
            text_lines.clear()

    def flush_code() -> None:
        if code_lines:
            parts.append(code_block_html("\n".join(code_lines).strip()))
            code_lines.clear()

    for line in block.splitlines():
        if line.strip().startswith("```"):
            if in_code:
                flush_code()
                in_code = False
            else:
                flush_text()
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
        else:
            text_lines.append(line)
    flush_code()
    flush_text()
    return "\n".join(parts)


def code_block_html(code: str) -> str:
    return (
        '<pre style="margin:12px 0;padding:12px;border-radius:4px;background:#f8f8f8;'
        'border:1px solid #d9d9d9;color:#3e3e3e;font-size:13px;line-height:1.7;'
        f'white-space:pre-wrap;word-break:break-all;"><code>{escape(code)}</code></pre>'
    )


def blocks_html(blocks: Iterable[str]) -> str:
    return "\n".join(part for part in (block_to_html(block) for block in blocks) if part)


def unordered_list(items: Iterable[str]) -> str:
    lis = "\n".join(
        f'<li style="margin:0 0 6px 0;color:#3e3e3e;">{escape(strip_markdown(item))}</li>' for item in items if strip_markdown(item)
    )
    return f'<ul style="margin:8px 0 14px 0;padding-left:20px;color:#3e3e3e;font-size:15px;line-height:1.9;">{lis}</ul>'


def ordered_list(items: Iterable[str]) -> str:
    lis = "\n".join(
        f'<li style="margin:0 0 6px 0;color:#3e3e3e;">{escape(strip_markdown(item))}</li>' for item in items if strip_markdown(item)
    )
    return f'<ol style="margin:8px 0 14px 0;padding-left:20px;color:#3e3e3e;font-size:15px;line-height:1.9;">{lis}</ol>'


def section_title(title: str) -> str:
    return f'''<section style="-webkit-tap-highlight-color:transparent;margin:20px 0px 15px;letter-spacing:0.544px;display:flex;flex-flow:row;text-align:center;justify-content:center;">
  <section style="-webkit-tap-highlight-color:transparent;margin-top:0px;margin-right:4px;margin-bottom:unset;margin-left:0px;display:inline-block;vertical-align:bottom;width:auto;flex:0 0 0%;height:auto;align-self:flex-end;">
    <section style="-webkit-tap-highlight-color:transparent;margin-top:0px;margin-right:0px;margin-bottom:unset;margin-left:0px;transform-style:flat;transform:perspective(0px);-webkit-transform:perspective(0px);">
    <section style="-webkit-tap-highlight-color:transparent;margin-top:0px;margin-right:0px;margin-bottom:unset;margin-left:0px;transform:rotateX(180deg);-webkit-transform:rotateX(180deg);">
    <section style="-webkit-tap-highlight-color:transparent;display:inline-block;width:3px;height:16px;vertical-align:top;overflow:hidden;background-color:#4577da;box-sizing:border-box;">
    <svg viewBox="0 0 1 1" style="float:left;line-height:0;width:0;vertical-align:top;" role="img" aria-label="插图"></svg></section></section></section>
  </section>
  <section style="-webkit-tap-highlight-color:transparent;padding:0px 12px;display:inline-block;vertical-align:bottom;width:auto;flex:0 0 auto;align-self:flex-end;min-width:10%;height:auto;box-sizing:border-box;">
    <section style="-webkit-tap-highlight-color:transparent;text-align:justify;font-size:17px;"><p style="-webkit-tap-highlight-color:transparent;margin:0;"><strong style="-webkit-tap-highlight-color:transparent;"><span style="-webkit-tap-highlight-color:transparent;">{escape(title)}</span></strong></p></section>
    <section style="-webkit-tap-highlight-color:transparent;margin-top:2px;"><section style="-webkit-tap-highlight-color:transparent;background-color:#4577da;height:1px;box-sizing:border-box;"><svg viewBox="0 0 1 1" style="float:left;line-height:0;width:0;vertical-align:top;" role="img" aria-label="插图"></svg></section></section>
  </section>
  <section style="-webkit-tap-highlight-color:transparent;margin-top:0px;margin-right:0px;margin-bottom:unset;margin-left:4px;display:inline-block;vertical-align:bottom;width:auto;flex:0 0 0%;height:auto;align-self:flex-end;">
    <section style="-webkit-tap-highlight-color:transparent;margin-top:0px;margin-right:0px;margin-bottom:unset;margin-left:0px;transform-style:flat;transform:perspective(0px);-webkit-transform:perspective(0px);">
    <section style="-webkit-tap-highlight-color:transparent;margin-top:0px;margin-right:0px;margin-bottom:unset;margin-left:0px;transform:rotateX(180deg);-webkit-transform:rotateX(180deg);">
    <section style="-webkit-tap-highlight-color:transparent;display:inline-block;width:3px;height:10px;vertical-align:top;overflow:hidden;background-color:#4577da;box-sizing:border-box;">
    <svg viewBox="0 0 1 1" style="float:left;line-height:0;width:0;vertical-align:top;" role="img" aria-label="插图"></svg></section></section></section>
  </section>
</section>'''


def sub_title(title: str) -> str:
    return (
        '<section style="-webkit-tap-highlight-color:transparent;margin:10px 0px;'
        'letter-spacing:0.544px;text-align:left;justify-content:flex-start;display:flex;flex-flow:row;">'
        '<section style="-webkit-tap-highlight-color:transparent;display:inline-block;vertical-align:middle;'
        'width:auto;min-width:10%;flex:0 0 auto;height:auto;align-self:center;">'
        '<section style="-webkit-tap-highlight-color:transparent;font-size:15px;text-align:justify;'
        f'color:#3e3e3e;line-height:2;"><p style="-webkit-tap-highlight-color:transparent;margin:0;"><strong>{escape(title)}</strong></p></section></section></section>'
    )


def cell(text: str, *, header: bool = False, colspan: int = 1) -> str:
    attrs = f' colspan="{colspan}"' if colspan > 1 else ""
    if header:
        style = "word-break:break-all;border:1px solid #4577da;background-color:#4577da;padding:5px;color:#ffffff;font-size:14px;text-align:center;"
        return f'<td{attrs} style="{style}"><strong>{escape(text)}</strong></td>'
    style = "word-break:break-all;border:1px solid #4577da;padding:5px;font-size:14px;color:#3e3e3e;"
    return f'<td{attrs} style="{style}">{escape(text)}</td>'


def label_cell(text: str) -> str:
    style = "word-break:break-all;border:1px solid #4577da;padding:5px;font-size:14px;color:#3e3e3e;"
    return f'<td style="{style}"><strong>{escape(text)}</strong></td>'


def render_overview(data: AlertData) -> str:
    o = data.overview
    title = o.get("漏洞标题") or o.get("漏洞名称") or data.title
    rows = [
        f"<tr>{cell('漏洞概述', header=True, colspan=4)}</tr>",
        f"<tr>{label_cell('漏洞名称')}{cell(title, colspan=3)}</tr>",
        f"<tr>{label_cell('安恒CERT评级')}{cell(first_matching_value(o, '漏洞处置等级', default='待确认'))}{label_cell('CVSS3.1评分')}{cell(first_matching_value(o, 'CVSS3.1评分', default='待确认'))}</tr>",
        f"<tr>{label_cell('CVE编号')}{cell(first_matching_value(o, 'CVE编号'))}{label_cell('CNVD编号')}{cell(first_matching_value(o, 'CNVD编号'))}</tr>",
        f"<tr>{label_cell('CNNVD编号')}{cell(first_matching_value(o, 'CNNVD编号'))}{label_cell('安恒CERT编号')}{cell(first_matching_value(o, '安恒CERT编号'))}</tr>",
        f"<tr>{label_cell('POC情况')}{cell(first_matching_value(o, 'Poc情况', 'POC情况', default='待确认'))}{label_cell('EXP情况')}{cell(first_matching_value(o, 'Exp情况', 'EXP情况', default='待确认'))}</tr>",
        f"<tr>{label_cell('在野利用')}{cell(first_matching_value(o, '在野利用', default='待确认'))}{label_cell('研究情况')}{cell(first_matching_value(o, '研究情况', default='待确认'))}</tr>",
        f"<tr>{label_cell('危害描述')}{cell(first_matching_value(o, '危害描述', default='待确认'), colspan=3)}</tr>",
    ]
    return (
        '<section style="-webkit-tap-highlight-color:transparent;margin:10px 0px;min-height:40px;">'
        '<table style="min-width:100px;width:100%;border-collapse:collapse;table-layout:fixed;"><tbody>'
        + "\n".join(rows)
        + "</tbody></table></section>"
    )


def render_reproduction(note: str) -> str:
    if not note:
        return ""
    return (
        '<section style="-webkit-tap-highlight-color:transparent;padding:0px 15px;'
        'letter-spacing:0.544px;line-height:2;box-sizing:border-box;">'
        '<p style="-webkit-tap-highlight-color:transparent;margin-bottom:15px;word-break:break-all;">'
        f'<span style="font-size:15px;"><strong>{escape(note)}</strong></span></p></section>'
    )


def image_to_base64_html(image_path: Path) -> str:
    """Convert an image file to a base64-encoded HTML img tag for WeChat.

    Images are resized to max 578px width and compressed to JPEG quality 80
    to stay within WeChat's content size limit.
    """
    from PIL import Image as PILImage
    import io

    try:
        img = PILImage.open(image_path)
        orig_w, orig_h = img.size
        max_w = 578
        if orig_w > max_w:
            ratio = max_w / orig_w
            new_w = max_w
            new_h = int(orig_h * ratio)
            img = img.resize((new_w, new_h), PILImage.LANCZOS)

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80, optimize=True)
        encoded = base64.b64encode(buf.getvalue()).decode()
        mime = "image/jpeg"
    except ImportError:
        with open(image_path, "rb") as fh:
            encoded = base64.b64encode(fh.read()).decode()
        ext = image_path.suffix.lower().lstrip(".")
        mime_map = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                    "webp": "image/webp", "gif": "image/gif", "bmp": "image/bmp"}
        mime = mime_map.get(ext, "image/png")

    alt = escape(image_path.stem)
    return (
        '<section style="-webkit-tap-highlight-color:transparent;margin:10px 0px;'
        'letter-spacing:0.544px;text-align:center;line-height:0;">'
        '<section style="-webkit-tap-highlight-color:transparent;margin:0;vertical-align:middle;'
        'display:inline-block;line-height:0;">'
        f'<img src="data:{mime};base64,{encoded}" alt="{alt}" '
        'style="-webkit-tap-highlight-color:transparent;border-radius:initial;'
        'background-color:transparent !important;background-size:0px !important;'
        'vertical-align:bottom;width:100%;max-width:578px;height:auto;display:block;margin:0 auto;" />'
        '</section></section>'
    )


def render_reproduction_images(images: list[Path]) -> str:
    """Render reproduction screenshots as inline base64 images."""
    if not images:
        return ""
    parts = []
    for img in images:
        try:
            parts.append(image_to_base64_html(img))
        except (OSError, ValueError):
            continue
    if not parts:
        return ""
    return "\n".join(parts)


def render_description(data: AlertData) -> str:
    parts = []
    if data.product_intro:
        parts.append(paragraph(data.product_intro))
    for desc in data.description:
        parts.append(paragraph(desc))
    return section_title("漏洞描述") + "\n" + "\n".join(part for part in parts if part)


def render_impact(data: AlertData) -> str:
    if not data.impact:
        return ""
    items = "\n".join(paragraph(item) for item in data.impact)
    return section_title("影响范围") + "\n" + items


def render_fix(data: AlertData) -> str:
    if not data.official_fix and not data.temporary_fix:
        return ""
    parts = [section_title("修复方案")]
    if data.official_fix:
        parts.append(sub_title("官方修复方案"))
        parts.append(blocks_html(data.official_fix))
    if data.temporary_fix:
        parts.append(sub_title("临时缓解方案"))
        parts.append(blocks_html(data.temporary_fix))
    return "\n".join(parts)


def render_references(urls: list[str]) -> str:
    if not urls:
        return ""
    rows = [section_title("参考资料")]
    items_html = ""
    for url in urls:
        safe_url = escape(url)
        items_html += (
            '<section><span leaf="" style="color:rgb(136,136,136);font-size:12px;'
            'letter-spacing:0.57834px;font-family:&quot;PingFang SC&quot;, system-ui, -apple-system, '
            '&quot;system-ui&quot;, &quot;Helvetica Neue&quot;, &quot;Hiragino Sans GB&quot;, '
            '&quot;Microsoft YaHei UI&quot;, &quot;Microsoft YaHei&quot;, Arial, sans-serif;">'
            f'{safe_url}</span></section>\n'
        )
    rows.append(items_html.rstrip())
    return "\n".join(rows)


def render_product_coverage(rows: list[list[str]]) -> str:
    if len(rows) < 2:
        return ""
    rendered = [section_title("产品能力覆盖")]
    table_rows = []
    for row_index, row in enumerate(rows):
        if len(row) < 2:
            continue
        left, right = row[0], row[1]
        if row_index == 0:
            table_rows.append(f"<tr>{cell(left, header=True)}{cell(right, header=True)}</tr>")
        else:
            table_rows.append(f"<tr>{cell(left)}{cell(right)}</tr>")
    if not table_rows:
        return ""
    rendered.append(
        '<table style="min-width:50px;width:100%;border-collapse:collapse;table-layout:fixed;"><tbody>'
        + "\n".join(table_rows)
        + "</tbody></table>"
    )
    return "\n".join(rendered)


def render_header(data: AlertData) -> str:
    if not DEFAULT_HEADER_IMAGE.is_file():
        return ""
    encoded = base64.b64encode(DEFAULT_HEADER_IMAGE.read_bytes()).decode()
    return (
        '<section dir="ltr" style="-webkit-tap-highlight-color:transparent;margin:10px 0px;'
        'letter-spacing:0.544px;text-align:center;line-height:0;">'
        '<section style="-webkit-tap-highlight-color:transparent;margin:0;vertical-align:middle;'
        'display:inline-block;line-height:0;">'
        f'<img src="data:image/png;base64,{encoded}" alt="安恒信息安全通告" '
        'style="-webkit-tap-highlight-color:transparent;border-radius:initial;'
        'background-color:transparent !important;background-size:0px !important;'
        'vertical-align:bottom;width:100%;max-width:578px;height:auto;display:block;margin:0 auto;" />'
        '</section></section>'
    )


def render_support() -> str:
    items = paragraph("如有漏洞相关需求支持请联系400-6059-110获取相关能力支撑。")
    # Wrap the phone number in a section matching reference style
    return section_title("技术支持") + "\n" + items


def render_disclaimer() -> str:
    return (
        '<section style="margin:26px 0 0 0;padding:12px 14px;border-radius:10px;'
        'background:#f8fafc;border:1px solid #e5e7eb;">'
        '<p style="margin:0;color:#8a8f99;font-size:13px;line-height:1.8;text-align:justify;word-break:break-all;">'
        '<span>本文由产品安全研究部根据公开信息整理，仅供安全加固和风险排查参考。'
        '请结合实际业务环境评估影响范围并及时完成修复。</span></p></section>'
    )


def validate_html(output: str) -> None:
    lower = output.lower()
    for forbidden in FORBIDDEN_OUTPUT:
        if forbidden.lower() in lower:
            raise ValueError(f"forbidden output marker found: {forbidden}")


def vuln_sub_title(title: str) -> str:
    return (
        '<section style="-webkit-tap-highlight-color:transparent;margin:10px 0px;'
        'letter-spacing:0.544px;text-align:left;justify-content:flex-start;display:flex;flex-flow:row;">'
        '<section style="-webkit-tap-highlight-color:transparent;display:inline-block;vertical-align:middle;'
        'width:auto;line-height:0;min-width:10%;flex:0 0 auto;height:auto;align-self:center;">'
        '<section style="-webkit-tap-highlight-color:transparent;transform:rotateZ(45deg);'
        '-webkit-transform:rotateZ(45deg);"><section style="-webkit-tap-highlight-color:transparent;text-align:center;">'
        '<section style="display:inline-block;width:15px;height:4px;vertical-align:top;overflow:hidden;'
        'background-color:#f8c025;border-width:0px;border-radius:10px;border-style:none;'
        'border-color:rgb(62,62,62);box-shadow:rgb(0,0,0)0px 0px 0px;box-sizing:border-box;">'
        '<svg viewBox="0 0 1 1" style="letter-spacing:0.544px;font-size:15px;word-break:break-all;"'
        ' role="img" aria-label="插图"></svg></section></section></section>'
        '<section style="-webkit-tap-highlight-color:transparent;transform:rotateZ(315deg);'
        '-webkit-transform:rotateZ(315deg);"><section style="-webkit-tap-highlight-color:transparent;'
        'margin:4px 0px 5px;text-align:center;">'
        '<section style="display:inline-block;width:14px;height:4px;vertical-align:top;overflow:hidden;'
        'background-color:#4577da;border-width:0px;border-radius:10px;border-style:none;'
        'border-color:rgb(62,62,62);box-sizing:border-box;">'
        '<svg viewBox="0 0 1 1" style="letter-spacing:0.544px;font-size:15px;word-break:break-all;"'
        ' role="img" aria-label="插图"></svg></section></section></section></section>'
        '<section style="-webkit-tap-highlight-color:transparent;display:inline-block;vertical-align:middle;'
        'width:auto;min-width:10%;flex:0 0 auto;height:auto;align-self:center;">'
        '<section style="-webkit-tap-highlight-color:transparent;">'
        '<section style="-webkit-tap-highlight-color:transparent;font-size:15px;text-align:justify;'
        f'color:#666666;line-height:2;"><p style="-webkit-tap-highlight-color:transparent;margin:0;">'
        f'<strong style="-webkit-tap-highlight-color:transparent;"><span>{escape(title)}</span></strong>'
        "</p></section></section></section></section>"
    )




def render_vuln_info(data: AlertData) -> str:
    parts = []

    # product intro paragraph
    if data.product_intro:
        parts.append(paragraph(data.product_intro))

    # 漏洞描述 sub-section
    o = data.overview
    severity = first_matching_value(o, "漏洞危害等级", "漏洞处置等级", default="")
    vuln_type = o.get("漏洞类型", "")
    if severity or vuln_type:
        parts.append(vuln_sub_title("漏洞描述"))
        desc_lines = ""
        if severity:
            desc_lines += f'<p style="-webkit-tap-highlight-color:transparent;margin-bottom:15px;word-break:break-all;"><span style="font-size:15px;"><strong>漏洞危害等级：</strong>{escape(severity)}</span></p>\n'
        if vuln_type:
            desc_lines += f'<p style="-webkit-tap-highlight-color:transparent;margin-bottom:15px;word-break:break-all;"><span style="font-size:15px;"><strong>漏洞类型：</strong>{escape(vuln_type)}</span></p>\n'
        if desc_lines:
            parts.append(
                '<section style="-webkit-tap-highlight-color:transparent;padding:0px 15px;'
                'letter-spacing:0.544px;line-height:2;box-sizing:border-box;">\n'
                + desc_lines.rstrip()
                + '</section>'
            )

    # 影响范围 sub-section
    version = o.get("影响版本", "")
    if version:
        parts.append(vuln_sub_title("影响范围"))
        parts.append(
            '<section style="-webkit-tap-highlight-color:transparent;padding:0px 15px;'
            'letter-spacing:0.544px;line-height:2;box-sizing:border-box;">'
            f'<p style="-webkit-tap-highlight-color:transparent;margin-bottom:15px;word-break:break-all;">'
            f'<span style="font-size:15px;"><strong>影响版本：</strong>{escape(version)}</span></p></section>'
        )

    # CVSS向量 sub-section
    cvss_keys = [
        ("访问途径（AV）", "访问途径（AV）"),
        ("攻击复杂度（AC）", "攻击复杂度（AC）"),
        ("所需权限（PR）", "所需权限（PR）"),
        ("用户交互（UI）", "用户交互（UI）"),
        ("影响范围（S）", "影响范围（S）"),
        ("机密性影响（C）", "机密性影响（C）"),
        ("完整性影响（I）", "完整性影响（I）"),
        ("可用性影响（A）", "可用性影响（A）"),
    ]
    cvss_lines = ""
    for key, label in cvss_keys:
        value = o.get(key, "")
        if value:
            cvss_lines += f'<p style="-webkit-tap-highlight-color:transparent;margin-bottom:15px;word-break:break-all;"><span style="font-size:15px;">{escape(label)}：{escape(value)}</span></p>\n'
    if cvss_lines:
        parts.append(vuln_sub_title("CVSS向量"))
        parts.append(
            '<section style="-webkit-tap-highlight-color:transparent;padding:0px 15px;'
            'letter-spacing:0.544px;line-height:2;box-sizing:border-box;">\n'
            + cvss_lines.rstrip()
            + '\n</section>'
        )

    return section_title("漏洞信息") + "\n" + "\n".join(parts)


def link_html(url: str) -> str:
    safe_url = escape(url)
    return f'<a href="{safe_url}" style="color:#4577da;text-decoration:none;word-break:break-all;">{safe_url}</a>'


def raw_cell(content: str, *, header: bool = False, colspan: int = 1) -> str:
    attrs = f' colspan="{colspan}"' if colspan > 1 else ""
    if header:
        style = "word-break:break-all;border:1px solid #4577da;background-color:#4577da;padding:5px;color:#ffffff;font-size:14px;text-align:center;"
        return f'<td{attrs} style="{style}"><strong>{content}</strong></td>'
    style = "word-break:break-all;border:1px solid #4577da;padding:5px;font-size:14px;color:#3e3e3e;"
    return f'<td{attrs} style="{style}">{content}</td>'


def severity_color(severity: str) -> str:
    if any(word in severity for word in ("严重", "危急", "超危")):
        return "#b42318"
    if "高危" in severity:
        return "#d93026"
    if "中危" in severity:
        return "#f29900"
    if "低危" in severity:
        return "#2e7d32"
    return "#3e3e3e"


def render_microsoft_notice(data: MicrosoftMonthlyReport) -> str:
    parts = [section_title("安全通告")]
    parts.extend(paragraph(item) for item in data.notice)
    parts.extend(paragraph(item) for item in data.product_intro)
    return "\n".join(part for part in parts if part)


def render_microsoft_list_table(title: str, items: list[str]) -> str:
    if not items:
        return ""
    rows = [f"<tr>{cell(title, header=True, colspan=2)}</tr>"]
    for index, item in enumerate(items, start=1):
        rows.append(f"<tr>{label_cell(str(index))}{cell(item)}</tr>")
    return (
        '<section style="-webkit-tap-highlight-color:transparent;margin:10px 0px;min-height:40px;">'
        '<table style="min-width:100px;width:100%;border-collapse:collapse;table-layout:fixed;"><tbody>'
        + "\n".join(rows)
        + "</tbody></table></section>"
    )


def render_microsoft_summary(data: MicrosoftMonthlyReport) -> str:
    parts = [section_title("漏洞速览")]
    if data.zero_day_note:
        parts.append(
            '<section style="margin:14px 0;padding:12px 14px;border-left:5px solid #f8c025;'
            'background:#fff8df;border-radius:4px;">'
            f'<p style="margin:0;color:#3e3e3e;font-size:15px;line-height:1.9;text-align:justify;">{escape(data.zero_day_note)}</p>'
            '</section>'
        )
    parts.append(render_microsoft_list_table("重点关注漏洞", data.highlighted_vulns))
    parts.append(render_microsoft_list_table("严重漏洞", data.critical_vulns))
    return "\n".join(part for part in parts if part)


def render_microsoft_vulnerability(index: int, vuln: MicrosoftVulnerability) -> str:
    rows = [f"<tr>{cell('漏洞详情', header=True, colspan=4)}</tr>"]
    rows.append(f"<tr>{label_cell('漏洞标题')}{cell(vuln.title, colspan=3)}</tr>")
    if vuln.description:
        rows.append(f"<tr>{label_cell('漏洞描述')}{cell(vuln.description, colspan=3)}</tr>")
    severity_text = escape(vuln.severity or "待确认")
    severity_html = f'<span style="color:{severity_color(vuln.severity)};font-weight:700;">{severity_text}</span>'
    rows.append(
        f"<tr>{label_cell('漏洞类型')}{cell(vuln.vuln_type or '待确认')}"
        f"{label_cell('危害等级')}{raw_cell(severity_html)}</tr>"
    )
    rows.append(
        f"<tr>{label_cell('CVE编号')}{cell(vuln.cve_id or '未分配')}"
        f"{label_cell('CVSS3.1评分')}{cell(vuln.cvss_score or '待确认')}</tr>"
    )
    rows.append(
        f"<tr>{label_cell('CNVD编号')}{cell(vuln.cnvd_id or '未分配')}"
        f"{label_cell('CNNVD编号')}{cell(vuln.cnnvd_id or '未分配')}</tr>"
    )
    if vuln.antian_cert_id:
        rows.append(f"<tr>{label_cell('安恒CERT编号')}{cell(vuln.antian_cert_id, colspan=3)}</tr>")
    if vuln.cvss_vector:
        vector = "；".join(f"{key}：{value}" for key, value in vuln.cvss_vector.items())
        rows.append(f"<tr>{label_cell('CVSS向量')}{cell(vector, colspan=3)}</tr>")
    if vuln.reference:
        rows.append(f"<tr>{label_cell('参考链接')}{raw_cell(link_html(vuln.reference), colspan=3)}</tr>")

    return (
        vuln_sub_title(f"{index}.{vuln.title}")
        + "\n"
        + '<section style="-webkit-tap-highlight-color:transparent;margin:10px 0px;min-height:40px;">'
        + '<table style="min-width:100px;width:100%;border-collapse:collapse;table-layout:fixed;"><tbody>'
        + "\n".join(rows)
        + "</tbody></table></section>"
    )


def render_microsoft_details(vulnerabilities: list[MicrosoftVulnerability]) -> str:
    if not vulnerabilities:
        return ""
    parts = [section_title("漏洞详情")]
    for index, vuln in enumerate(vulnerabilities, start=1):
        parts.append(render_microsoft_vulnerability(index, vuln))
    return "\n".join(parts)


def render_microsoft_fix(blocks: list[str]) -> str:
    if not blocks:
        return ""
    return section_title("修复方案") + "\n" + blocks_html(blocks)


def render_microsoft_report(data: MicrosoftMonthlyReport, template: Path) -> str:
    html_template = template.read_text(encoding="utf-8")
    values = {
        "header_html": render_header(AlertData(title=data.title)),
        "notice_section": render_microsoft_notice(data),
        "summary_section": render_microsoft_summary(data),
        "vulnerability_details_section": render_microsoft_details(data.vulnerabilities),
        "fix_section": render_microsoft_fix(data.official_fix),
        "references_section": render_references(data.references),
        "technical_support_section": render_support(),
    }
    output = html_template
    for key, value in values.items():
        output = output.replace("{{" + key + "}}", value)
    validate_html(output)
    return output


def upload_base64_images_to_wechat(html_content: str) -> str:
    """Upload base64 images in HTML to WeChat article image CDN."""
    appid = os.environ.get("WECHAT_APPID", "")
    secret = os.environ.get("WECHAT_SECRET", "")
    if not appid or not secret:
        return html_content

    try:
        resp = urllib.request.urlopen(
            f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appid}&secret={secret}"
        )
        token_data = json_lib.loads(resp.read())
        token = token_data.get("access_token", "")
        if not token:
            return html_content
    except Exception:
        return html_content

    def _upload(data: bytes, filename: str, mime: str) -> str:
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="media"; filename="{filename}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode("utf-8") + data + f"\r\n--{boundary}--\r\n".encode("utf-8")
        req = urllib.request.Request(
            f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={token}",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        result = json_lib.loads(urllib.request.urlopen(req).read())
        return result.get("url", "")

    def _replace(m: re.Match) -> str:
        fmt = m.group(1)
        b64 = m.group(2)
        try:
            img_data = base64.b64decode(b64)
            url = _upload(img_data, f"image.{fmt}", f"image/{fmt}")
            return url if url else m.group(0)
        except Exception:
            return m.group(0)

    return re.sub(r'data:image/(\w+);base64,([A-Za-z0-9+/=]+)', _replace, html_content)


def render(data: AlertData, template: Path) -> str:
    html_template = template.read_text(encoding="utf-8")
    values = {
        "header_html": render_header(data),
        "overview_table": render_overview(data),
        "intro_html": "\n".join(paragraph(item) for item in data.intro if item != data.reproduction_note) + "\n" + render_reproduction(data.reproduction_note),
        "reproduction_images_html": render_reproduction_images(data.reproduction_images),
        "vuln_info_section": render_vuln_info(data),
        "fix_section": render_fix(data),
        "references_section": render_references(data.references),
        "product_coverage_section": render_product_coverage(data.product_coverage),
        "technical_support_section": render_support(),
    }
    output = html_template
    for key, value in values.items():
        output = output.replace("{{" + key + "}}", value)
    validate_html(output)
    return output


def digest_from_report(data: MicrosoftMonthlyReport) -> str:
    source = data.notice or data.product_intro or [data.title]
    return strip_markdown(source[0])[:120] if source else data.title[:120]


def main() -> int:
    parser = argparse.ArgumentParser(description="Render WeChat alert article HTML from Markdown")
    parser.add_argument("markdown_file", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--template", type=Path, default=None)
    parser.add_argument("--article-type", choices=("auto", "alert", "microsoft-monthly"), default="auto")
    parser.add_argument("--json", action="store_true", help="Print machine-readable summary")
    parser.add_argument("--no-upload-images", action="store_true", help="Keep local images as data URIs")
    args = parser.parse_args()

    load_local_env()
    markdown = args.markdown_file.read_text(encoding="utf-8")
    article_type = args.article_type
    if article_type == "auto":
        article_type = "microsoft-monthly" if is_microsoft_monthly_report(markdown, args.markdown_file) else "alert"

    if article_type == "microsoft-monthly":
        data = parse_microsoft_report(markdown, args.markdown_file)
        template = args.template or DEFAULT_MICROSOFT_TEMPLATE
        output = render_microsoft_report(data, template)
        digest = digest_from_report(data)
        meta = {
            "success": True,
            "output": str(args.output),
            "title": data.title,
            "author": os.environ.get("WECHAT_AUTHOR", "安恒CERT"),
            "digest": digest,
            "article_type": article_type,
            "references": len(data.references),
            "highlighted_vulnerabilities": len(data.highlighted_vulns),
            "critical_vulnerabilities": len(data.critical_vulns),
            "vulnerability_details": len(data.vulnerabilities),
            "reproduction_images": [],
        }
    else:
        data = parse_alert(markdown, args.markdown_file)
        template = args.template or DEFAULT_TEMPLATE
        output = render(data, template)
        meta = {
            "success": True,
            "output": str(args.output),
            "title": data.title,
            "author": os.environ.get("WECHAT_AUTHOR", "安恒CERT"),
            "digest": (data.overview.get("危害描述") or data.title)[:120],
            "article_type": article_type,
            "references": len(data.references),
            "product_coverage_rows": max(0, len(data.product_coverage) - 1),
            "reproduction_images": [str(path) for path in data.reproduction_images],
            "missing_reproduction_images": missing_markdown_images(markdown, args.markdown_file),
        }

    # Optional: upload base64 images to WeChat CDN when credentials are available
    if not args.no_upload_images and os.environ.get("WECHAT_APPID") and os.environ.get("WECHAT_SECRET"):
        output = upload_base64_images_to_wechat(output)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output, encoding="utf-8")
    meta_path = args.output.with_suffix(args.output.suffix + ".meta.json")
    meta_path.write_text(json_lib.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json_lib.dumps(meta | {"metadata": str(meta_path)}, ensure_ascii=False))
    else:
        print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
