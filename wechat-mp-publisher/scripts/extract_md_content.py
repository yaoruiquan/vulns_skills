#!/usr/bin/env python3
"""
从漏洞预警 .md 文件提取内容，用于微信公众号发布
"""

import re
import json
import sys
from pathlib import Path


def extract_md_content(md_path: str) -> dict:
    """从 .md 文件提取微信公众号发布所需的内容"""
    content = Path(md_path).read_text(encoding='utf-8')

    result = {
        'title': '',
        'intro': '',
        'vuln_table_html': '',
        'description': '',
        'attack_vector': '',
        'fix_official': '',
        'fix_temp': '',
        'references': '',
        'support': ''
    }

    # 1. 提取标题：从文件名或表格第一行
    filename = Path(md_path).stem
    result['title'] = filename.replace('漏洞预警报告', '漏洞预警')

    # 也可以从表格中提取更精确的标题
    title_match = re.search(r'<tr>\s*<th>漏洞标题</th>\s*<th>([^<]+)</th>\s*</tr>', content)
    if title_match:
        result['title'] = title_match.group(1).strip()

    # 2. 提取导语：开头的引用块（以 > 开头的段落）
    intro_lines = []
    in_intro = False
    for line in content.split('\n'):
        if line.startswith('>'):
            in_intro = True
            intro_lines.append(line[1:].strip())
        elif in_intro and line.strip() and not line.startswith('#') and not line.startswith('<'):
            intro_lines.append(line.strip())
        elif in_intro and (line.startswith('#') or line.startswith('<table')):
            break

    result['intro'] = ' '.join(intro_lines)

    # 3. 提取漏洞信息表格
    table_match = re.search(r'<table>.*?</table>', content, re.DOTALL)
    if table_match:
        result['vuln_table_html'] = table_match.group(0)

    # 4. 提取各章节内容

    # 漏洞描述
    desc_match = re.search(r'## 漏洞描述\s*\n(.*?)(?=## |\n# |$)', content, re.DOTALL)
    if desc_match:
        result['description'] = desc_match.group(1).strip()

    # 攻击向量（可选）
    attack_match = re.search(r'## 攻击向量\s*\n(.*?)(?=## |\n# |$)', content, re.DOTALL)
    if attack_match:
        result['attack_vector'] = attack_match.group(1).strip()

    # 修复方案
    fix_match = re.search(r'# 二、 修复方案\s*\n(.*?)(?=## 参考资料|\n# |$)', content, re.DOTALL)
    if fix_match:
        fix_content = fix_match.group(1).strip()

        # 分离官方修复和临时缓解
        official_match = re.search(r'官方修复方案[:\s]*\n(.*?)(?=临时缓解方案|$)', fix_content, re.DOTALL)
        if official_match:
            result['fix_official'] = official_match.group(1).strip()

        temp_match = re.search(r'临时缓解方案[:\s]*\n(.*?)(?=##|$)', fix_content, re.DOTALL)
        if temp_match:
            result['fix_temp'] = temp_match.group(1).strip()

    # 参考资料
    ref_match = re.search(r'## 参考资料\s*\n(.*?)(?=## 产品能力覆盖|\n# 四|$)', content, re.DOTALL)
    if ref_match:
        result['references'] = ref_match.group(1).strip()

    # 技术支持
    support_match = re.search(r'# 五、 技术支持\s*\n(.*?)(?=$)', content, re.DOTALL)
    if support_match:
        result['support'] = support_match.group(1).strip()

    return result


def format_for_wechat(data: dict) -> str:
    """格式化为微信公众号 HTML 内容"""
    html_parts = []

    # 导语（引用样式）
    if data['intro']:
        html_parts.append(f'<blockquote style="background:#f5f5f5;padding:10px;border-left:4px solid #ccc;">{data["intro"]}</blockquote>')
        html_parts.append('<p></p>')

    # 一、漏洞信息
    html_parts.append('<h2 style="color:#333;border-bottom:1px solid #ccc;">一、漏洞信息</h2>')
    if data['vuln_table_html']:
        # 添加表格样式
        table_html = data['vuln_table_html'].replace(
            '<table>',
            '<table style="width:100%;border-collapse:collapse;margin:10px 0;">'
        ).replace(
            '<th>',
            '<th style="background:#f0f0f0;padding:8px;border:1px solid #ddd;text-align:left;">'
        ).replace(
            '<td>',
            '<td style="padding:8px;border:1px solid #ddd;">'
        )
        html_parts.append(table_html)

    # 二、漏洞描述
    if data['description']:
        html_parts.append('<h2 style="color:#333;border-bottom:1px solid #ccc;">二、漏洞描述</h2>')
        # Markdown 转 HTML
        desc_html = markdown_to_html(data['description'])
        html_parts.append(desc_html)

    # 三、攻击向量（可选）
    if data['attack_vector']:
        html_parts.append('<h2 style="color:#333;border-bottom:1px solid #ccc;">三、攻击向量</h2>')
        attack_html = markdown_to_html(data['attack_vector'])
        html_parts.append(attack_html)

    # 四、修复方案
    if data['fix_official'] or data['fix_temp']:
        html_parts.append('<h2 style="color:#333;border-bottom:1px solid #ccc;">四、修复方案</h2>')

        if data['fix_official']:
            html_parts.append('<h3 style="color:#666;">官方修复方案</h3>')
            fix_official_html = markdown_to_html(data['fix_official'])
            html_parts.append(fix_official_html)

        if data['fix_temp']:
            html_parts.append('<h3 style="color:#666;">临时缓解方案</h3>')
            fix_temp_html = markdown_to_html(data['fix_temp'])
            html_parts.append(fix_temp_html)

    # 五、参考资料
    if data['references']:
        html_parts.append('<h2 style="color:#333;border-bottom:1px solid #ccc;">五、参考资料</h2>')
        ref_html = markdown_to_html(data['references'])
        html_parts.append(ref_html)

    # 六、技术支持
    if data['support']:
        html_parts.append('<h2 style="color:#333;border-bottom:1px solid #ccc;">六、技术支持</h2>')
        support_html = markdown_to_html(data['support'])
        html_parts.append(support_html)

    return '\n'.join(html_parts)


def markdown_to_html(md_text: str) -> str:
    """简单的 Markdown 转 HTML"""
    html = md_text

    # 代码块
    html = re.sub(r'```(\w*)\n(.*?)```', r'<pre style="background:#f5f5f5;padding:10px;overflow-x:auto;"><code>\2</code></pre>', html, flags=re.DOTALL)

    # 行内代码
    html = re.sub(r'`([^`]+)`', r'<code style="background:#f5f5f5;padding:2px 4px;">\1</code>', html)

    # 加粗
    html = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', html)

    # 链接
    html = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2" style="color:#06c;">\1</a>', html)

    # 列表项
    html = re.sub(r'^-\s+(.+)$', r'<li style="margin-left:20px;">\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li.*</li>\n)+', r'<ul style="padding-left:0;">\g<0></ul>', html)

    # 段落
    lines = html.split('\n')
    paragraphs = []
    for line in lines:
        if line.strip() and not line.startswith('<'):
            paragraphs.append(f'<p style="margin:10px 0;">{line}</p>')
        else:
            paragraphs.append(line)
    html = '\n'.join(paragraphs)

    return html


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 extract_md_content.py <md文件路径>")
        sys.exit(1)

    md_path = sys.argv[1]

    if not Path(md_path).exists():
        print(f"Error: 文件不存在 - {md_path}")
        sys.exit(1)

    data = extract_md_content(md_path)
    html = format_for_wechat(data)

    # 输出 JSON 格式数据
    output = {
        'raw_data': data,
        'wechat_html': html,
        'title': data['title']
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()