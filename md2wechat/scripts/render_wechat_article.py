#!/usr/bin/env python3
"""Render vulnerability alert Markdown into deterministic WeChat article HTML."""

from __future__ import annotations

import argparse
import html
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = SKILL_ROOT / "assets" / "wechat-alert-article-template.placeholders.html"

FORBIDDEN_OUTPUT = ("<style", "<script", "class=", "contenteditable=", "ProseMirror", "onclick=")


@dataclass
class AlertData:
    title: str = ""
    intro: list[str] = field(default_factory=list)
    reproduction_note: str = ""
    product_intro: str = ""
    description: list[str] = field(default_factory=list)
    impact: list[str] = field(default_factory=list)
    official_fix: list[str] = field(default_factory=list)
    temporary_fix: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    overview: dict[str, str] = field(default_factory=dict)
    product_coverage: list[list[str]] = field(default_factory=list)


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


def extract_tables(markdown: str) -> list[list[list[str]]]:
    regex_tables = extract_tables_lenient(markdown)
    if regex_tables:
        return regex_tables
    parser = TableParser()
    parser.feed(markdown)
    return parser.tables


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


def extract_title(markdown: str, overview: dict[str, str], source: Path) -> str:
    if overview.get("漏洞标题") or overview.get("漏洞名称"):
        return overview.get("漏洞标题") or overview.get("漏洞名称") or source.stem
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
                return title
    return overview.get("漏洞标题") or overview.get("漏洞名称") or source.stem


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


def split_fix_section(text: str) -> tuple[list[str], list[str]]:
    official: list[str] = []
    temporary: list[str] = []
    current = "official"
    for block in markdown_blocks(text):
        label = strip_markdown(block)
        if "临时缓解" in label:
            current = "temporary"
            remainder = re.sub(r"^#+\s*临时缓解方案\s*[:：]?", "", block).strip()
            if remainder and remainder != block:
                temporary.append(remainder)
            continue
        if "官方修复" in label or label.startswith("安全版本"):
            current = "official"
            remainder = re.sub(r"^#+\s*官方修复方案\s*[:：]?", "", block).strip()
            if remainder and remainder != block:
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

    preface = plain_paragraphs(sections.get("__preface__", ""))
    notice = plain_paragraphs(find_section(sections, "安全通告"))
    data.intro = preface + notice
    if not data.intro:
        data.intro = [overview.get("危害描述", "")]
    data.intro = [item for item in data.intro if item]

    for paragraph in data.intro:
        if "已复现" in paragraph or "完成技术分析" in paragraph or "卫兵实验室" in paragraph:
            data.reproduction_note = paragraph
            break

    vuln_info = find_section(sections, "漏洞信息")
    vuln_paragraphs = plain_paragraphs(vuln_info)
    if vuln_paragraphs:
        data.product_intro = vuln_paragraphs[0]
    explicit_description = plain_paragraphs(find_section(sections, "漏洞描述"))
    data.description = explicit_description or vuln_paragraphs[:2]
    if not data.description and overview.get("危害描述"):
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


def paragraph(text: str) -> str:
    return (
        '<p style="-webkit-tap-highlight-color:transparent;letter-spacing:0.544px;'
        'font-size:15px;word-break:break-all;line-height:2;margin:0 0 15px 0;">'
        f'<span style="font-size:15px;letter-spacing:0.544px;color:#3e3e3e;">{escape(text)}</span></p>'
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
  <section style="-webkit-tap-highlight-color:transparent;margin-right:4px;display:inline-block;vertical-align:bottom;width:auto;flex:0 0 0%;height:auto;align-self:flex-end;">
    <section style="-webkit-tap-highlight-color:transparent;display:inline-block;width:3px;height:10px;vertical-align:top;overflow:hidden;background-color:#4577da;"></section>
  </section>
  <section style="-webkit-tap-highlight-color:transparent;padding:0px 12px;display:inline-block;vertical-align:bottom;width:auto;flex:0 0 auto;align-self:flex-end;min-width:10%;height:auto;box-sizing:border-box;">
    <section style="-webkit-tap-highlight-color:transparent;text-align:justify;font-size:17px;"><p style="-webkit-tap-highlight-color:transparent;margin:0;"><strong>{escape(title)}</strong></p></section>
    <section style="-webkit-tap-highlight-color:transparent;margin-top:2px;"><section style="-webkit-tap-highlight-color:transparent;background-color:#4577da;height:1px;"></section></section>
  </section>
  <section style="-webkit-tap-highlight-color:transparent;margin-left:4px;display:inline-block;vertical-align:bottom;width:auto;flex:0 0 0%;height:auto;align-self:flex-end;">
    <section style="-webkit-tap-highlight-color:transparent;display:inline-block;width:3px;height:16px;vertical-align:top;overflow:hidden;background-color:#4577da;"></section>
  </section>
</section>'''


def sub_title(title: str) -> str:
    return (
        '<section style="margin:20px 0 10px 0;">'
        '<span style="display:inline-block;width:8px;height:8px;margin-right:8px;background:#f8c025;transform:rotate(45deg);vertical-align:middle;"></span>'
        '<span style="display:inline-block;width:8px;height:8px;margin-right:8px;background:#4577da;transform:rotate(45deg);vertical-align:middle;"></span>'
        f'<span style="color:#666666;font-size:15px;font-weight:800;vertical-align:middle;">{escape(title)}</span>'
        '</section>'
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
        f"<tr>{label_cell('危害描述')}{cell(first_matching_value(o, '危害描述', default=(data.description[0] if data.description else '待确认')), colspan=3)}</tr>",
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
        '<section style="margin:14px 0;padding:10px 12px;border-left:4px solid #f8c025;background:#fff8df;">'
        f'<p style="margin:0;color:#3e3e3e;font-size:15px;line-height:1.9;"><strong>{escape(note)}</strong></p>'
        "</section>"
    )


def render_description(data: AlertData) -> str:
    parts = []
    if data.product_intro:
        parts.append(paragraph(data.product_intro))
    parts.append(blocks_html(data.description))
    return section_title("漏洞描述") + "\n" + "\n".join(part for part in parts if part)


def render_impact(data: AlertData) -> str:
    if not data.impact:
        return ""
    return section_title("影响范围") + "\n" + unordered_list(data.impact)


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
    for index, url in enumerate(urls, 1):
        safe_url = escape(url)
        rows.append(
            '<p style="margin:0 0 8px 0;color:#888888;font-size:12px;letter-spacing:0.57834px;word-break:break-all;">'
            f'[{index}] <a href="{safe_url}" style="color:#4577da;text-decoration:none;word-break:break-all;">{safe_url}</a></p>'
        )
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


def render_support() -> str:
    return section_title("技术支持") + "\n" + paragraph("如有漏洞相关需求支持请联系400-6059-110获取相关能力支撑。")


def validate_html(output: str) -> None:
    lower = output.lower()
    for forbidden in FORBIDDEN_OUTPUT:
        if forbidden.lower() in lower:
            raise ValueError(f"forbidden output marker found: {forbidden}")


def render(data: AlertData, template: Path) -> str:
    html_template = template.read_text(encoding="utf-8")
    values = {
        "overview_table": render_overview(data),
        "intro_html": "\n".join(paragraph(item) for item in data.intro if item != data.reproduction_note),
        "reproduction_html": render_reproduction(data.reproduction_note),
        "description_section": render_description(data),
        "impact_section": render_impact(data),
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Render WeChat alert article HTML from Markdown")
    parser.add_argument("markdown_file", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--json", action="store_true", help="Print machine-readable summary")
    args = parser.parse_args()

    markdown = args.markdown_file.read_text(encoding="utf-8")
    data = parse_alert(markdown, args.markdown_file)
    output = render(data, args.template)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output, encoding="utf-8")

    if args.json:
        import json

        print(
            json.dumps(
                {
                    "success": True,
                    "output": str(args.output),
                    "title": data.title,
                    "references": len(data.references),
                    "product_coverage_rows": max(0, len(data.product_coverage) - 1),
                },
                ensure_ascii=False,
            )
        )
    else:
        print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
