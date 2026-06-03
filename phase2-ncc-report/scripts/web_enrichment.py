#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NCC 信息收集阶段的漏洞危害和修复方案补全。"""

from __future__ import annotations

import html
import os
import re
import urllib.parse
import urllib.request
from typing import Dict, Iterable


EMPTY_VALUES = {"", "无", "暂无", "N/A", "n/a", "none", "None", "-", "--", "见附件"}
ATTACHMENT_NOTE_RE = re.compile(r"(详见|见)附件[^。；\n]*(?:[。；])?")
TAG_RE = re.compile(r"<[^>]+>")

CATEGORY_IMPACTS = {
    "SQL注入": "攻击者可能通过构造恶意 SQL 参数绕过业务查询逻辑，读取、篡改或删除数据库中的敏感数据，严重时可进一步获取系统权限或影响业务连续性。",
    "XML实体注入": "攻击者可能通过恶意 XML 外部实体读取服务器本地文件、探测内网资源或造成服务端请求异常，导致敏感信息泄露和系统可用性下降。",
    "XSS": "攻击者可能诱导用户访问携带恶意脚本的页面，窃取会话凭证、篡改页面内容或执行未授权操作，影响用户数据和业务可信度。",
    "SSRF": "攻击者可能利用服务端代发请求访问内网地址、云元数据接口或受限服务，造成敏感信息泄露、内网探测或进一步攻击。",
    "CSRF": "攻击者可能诱导已登录用户在不知情的情况下执行敏感操作，造成账号配置被修改、业务数据被篡改或权限被滥用。",
    "弱口令": "攻击者可能使用默认或弱密码直接登录系统，获取管理权限、访问敏感数据或进一步控制受影响服务。",
    "文件上传": "攻击者可能上传恶意文件或脚本并在服务端触发执行，造成 WebShell 写入、权限提升或服务器被控制。",
    "信息泄露": "攻击者可能获取系统配置、账号凭证、接口数据或内部路径等敏感信息，为后续攻击提供条件。",
    "未授权访问": "攻击者可能在未通过身份认证或权限校验的情况下访问敏感接口、读取业务数据或执行管理操作。",
    "逻辑缺陷": "攻击者可能绕过正常业务流程和权限限制，造成越权操作、数据篡改、资源滥用或其他业务安全影响。",
    "文件包含": "攻击者可能通过可控路径包含本地或远程文件，读取敏感文件、执行恶意代码或导致服务异常。",
    "命令执行": "攻击者可能在目标系统上执行任意系统命令，读取或篡改服务器数据，严重时可接管服务器并横向移动。",
    "目录遍历": "攻击者可能通过路径穿越访问预期目录外的文件，读取配置、源码、日志或其他敏感信息。",
    "任意文件下载": "攻击者可能下载服务器上的敏感文件、配置文件、源码或业务数据，造成信息泄露。",
    "任意文件读取": "攻击者可能读取服务器本地敏感文件、配置文件或业务数据，进一步获取账号凭证和系统结构信息。",
    "拒绝服务": "攻击者可能构造异常请求触发进程崩溃、资源耗尽或服务不可用，影响业务连续性。",
    "二进制": "攻击者可能触发内存破坏、越界访问或进程崩溃，造成拒绝服务；在特定条件下可能进一步实现代码执行或权限提升。",
    "工控设备": "攻击者可能影响工业控制设备的正常运行、配置完整性或远程管理能力，造成生产控制风险和业务中断。",
    "服务参数注入": "攻击者可能通过可控服务参数改变后端执行逻辑，造成权限绕过、命令执行、数据泄露或服务异常。",
    "点击劫持": "攻击者可能诱导用户在伪装页面中点击敏感按钮，造成未授权操作、配置变更或账号安全风险。",
    "其他": "攻击者可能利用该漏洞破坏受影响系统的机密性、完整性或可用性，并对相关业务造成安全影响。",
}

CATEGORY_SOLUTIONS = {
    "SQL注入": "对所有数据库查询参数使用参数化查询或预编译语句，禁止拼接 SQL；对输入进行白名单校验，并为数据库账号配置最小权限；同步升级受影响组件到官方修复版本。",
    "XML实体注入": "关闭 XML 解析器的外部实体和 DTD 解析能力；对上传或接口接收的 XML 内容进行严格校验；升级相关 XML 解析库和业务组件到安全版本。",
    "XSS": "对用户输入进行白名单校验，对输出到 HTML、属性、脚本上下文的内容分别做安全编码；启用 HttpOnly/SameSite Cookie 和 CSP；升级受影响组件。",
    "SSRF": "对服务端请求目标做白名单限制，禁止访问内网地址、环回地址和云元数据地址；限制协议类型和重定向；升级受影响组件并增加出网访问控制。",
    "CSRF": "为敏感操作增加 CSRF Token、SameSite Cookie 和二次校验；校验 Referer/Origin；对关键接口增加权限和操作确认。",
    "弱口令": "禁用默认账号和弱密码，强制修改初始密码；启用复杂度、锁定策略和多因素认证；排查是否存在异常登录和配置变更。",
    "文件上传": "限制上传文件类型、扩展名、MIME 和文件内容，上传目录禁止脚本执行；对文件重命名并隔离存储；升级受影响组件并补充恶意文件检测。",
    "信息泄露": "关闭调试接口和目录浏览，限制敏感文件访问；移除泄露的密钥、账号和配置并完成轮换；升级受影响组件并增加访问控制。",
    "未授权访问": "为受影响接口补充身份认证和权限校验，默认拒绝匿名访问；检查会话和访问控制逻辑；升级受影响组件并审计历史访问记录。",
    "逻辑缺陷": "修正业务流程中的权限、状态和边界校验，关键操作增加服务端校验和审计；补充自动化测试覆盖异常流程。",
    "文件包含": "禁止用户输入直接参与文件包含路径，使用白名单映射固定资源；关闭远程包含能力；限制应用运行权限并升级相关组件。",
    "命令执行": "禁止用户输入直接拼接系统命令，改用安全 API 或参数白名单；限制进程权限和可执行命令范围；升级受影响版本并排查入侵痕迹。",
    "目录遍历": "对路径参数进行规范化和白名单校验，禁止 `../` 等穿越序列；限制文件访问根目录；升级受影响组件并检查敏感文件访问日志。",
    "任意文件下载": "对下载文件使用 ID 到白名单路径的映射，禁止直接传入文件路径；增加身份认证和权限校验；升级受影响组件。",
    "任意文件读取": "对文件读取接口增加白名单、路径规范化和权限校验；限制应用账号文件系统权限；升级受影响组件并检查敏感文件是否泄露。",
    "拒绝服务": "升级到官方修复版本，限制异常请求频率和请求体大小；增加输入边界校验、超时控制和服务守护；必要时在网关层阻断触发特征。",
    "二进制": "升级到包含内存安全修复的官方版本；对触发入口增加长度、边界和格式校验；启用 ASLR、栈保护、FORTIFY、沙箱或最小权限运行。",
    "工控设备": "升级设备固件或厂商补丁，限制管理接口暴露范围；通过 VPN、ACL 和工业防火墙隔离访问；加强账号、日志和变更审计。",
    "服务参数注入": "对服务参数使用白名单和类型校验，禁止危险参数透传到底层服务；限制后端服务权限；升级受影响组件并增加审计。",
    "点击劫持": "配置 `X-Frame-Options` 或 CSP `frame-ancestors` 限制页面被嵌入；关键操作增加二次确认；升级受影响组件。",
    "其他": "优先升级到官方修复版本；如暂无补丁，应限制受影响入口访问、增加输入校验和权限控制，并通过网关或安全设备临时阻断触发特征。",
}


def normalize_text(value: str) -> str:
    return html.unescape(value or "").strip()


def valid_value(value: str) -> bool:
    text = normalize_text(value)
    compact = re.sub(r"\s+", "", text).strip(":：。；")
    return bool(text) and text not in EMPTY_VALUES and compact not in EMPTY_VALUES


def clean_snippet(value: str, max_chars: int = 260) -> str:
    text = TAG_RE.sub("", value or "")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars].rstrip()


def env_bool(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on", "是"}


def search_timeout() -> float:
    try:
        return float(os.environ.get("NCC_WEBSEARCH_TIMEOUT", "8") or "8")
    except ValueError:
        return 8.0


def search_limit() -> int:
    try:
        return max(1, min(8, int(os.environ.get("NCC_WEBSEARCH_LIMIT", "3") or "3")))
    except ValueError:
        return 3


def build_queries(title: str, product: str, vendor: str, category: str) -> list[str]:
    title = normalize_text(title)
    product = normalize_text(product)
    vendor = normalize_text(vendor)
    category = normalize_text(category)
    base = product or vendor or title
    queries = []
    if title:
        queries.append(f'"{title}" 漏洞 危害 修复')
    if base and category:
        queries.append(f'"{base}" "{category}" 漏洞 修复 影响')
    if base:
        queries.append(f'"{base}" security advisory mitigation')
    deduped = []
    seen = set()
    for query in queries:
        if query and query not in seen:
            deduped.append(query)
            seen.add(query)
    return deduped


def duckduckgo_search(query: str, limit: int, timeout: float) -> list[dict[str, str]]:
    url = "https://duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; NCC report enrichment)",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="ignore")

    results: list[dict[str, str]] = []
    blocks = re.findall(r'<div class="result(?: results_links)?[^"]*".*?</div>\s*</div>', body, flags=re.S)
    if not blocks:
        blocks = re.findall(r'<a rel="nofollow" class="result__a".*?</a>.*?(?:result__snippet.*?</a>|</div>)', body, flags=re.S)
    for block in blocks:
        title_match = re.search(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, flags=re.S)
        if not title_match:
            continue
        href = html.unescape(title_match.group(1))
        parsed_href = urllib.parse.urlparse(href)
        if parsed_href.path == "/l/":
            target = urllib.parse.parse_qs(parsed_href.query).get("uddg", [""])[0]
            if target:
                href = target
        snippet_match = re.search(r'class="result__snippet"[^>]*>(.*?)</(?:a|div)>', block, flags=re.S)
        results.append(
            {
                "title": clean_snippet(title_match.group(2), 160),
                "url": href,
                "snippet": clean_snippet(snippet_match.group(1) if snippet_match else "", 300),
            }
        )
        if len(results) >= limit:
            break
    return results


def websearch(queries: Iterable[str]) -> tuple[list[dict[str, str]], list[str]]:
    warnings: list[str] = []
    if not env_bool("NCC_WEBSEARCH_ENABLED", True):
        return [], ["NCC_WEBSEARCH_ENABLED=false，跳过联网检索"]

    limit = search_limit()
    timeout = search_timeout()
    collected: list[dict[str, str]] = []
    seen_urls = set()
    for query in queries:
        try:
            for item in duckduckgo_search(query, limit=limit, timeout=timeout):
                url = item.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                item["query"] = query
                collected.append(item)
                if len(collected) >= limit:
                    return collected, warnings
        except Exception as exc:  # pragma: no cover - network-dependent
            warnings.append(f"{query}: {exc}")
    return collected, warnings


def joined_snippets(results: list[dict[str, str]], max_chars: int = 220) -> str:
    snippets = [item.get("snippet", "") for item in results if item.get("snippet")]
    text = "；".join(snippets)
    return clean_snippet(text, max_chars)


def pick_direct(fields: Dict[str, str], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = normalize_text(fields.get(key, ""))
        if valid_value(value):
            return value
    return ""


def compose_impact(category: str, product: str, description: str, results: list[dict[str, str]]) -> str:
    base = CATEGORY_IMPACTS.get(category) or CATEGORY_IMPACTS["其他"]
    product_name = normalize_text(product)
    prefix = f"该漏洞影响 {product_name}。" if product_name else ""
    snippet = joined_snippets(results)
    if snippet:
        return f"{prefix}{base} 公开检索信息显示：{snippet}"
    desc = ATTACHMENT_NOTE_RE.sub("", normalize_text(description)).strip()
    if desc and len(desc) <= 220:
        return f"{prefix}{base} 漏洞描述摘要：{desc}"
    return f"{prefix}{base}"


def compose_solution(category: str, product: str, results: list[dict[str, str]]) -> str:
    base = CATEGORY_SOLUTIONS.get(category) or CATEGORY_SOLUTIONS["其他"]
    product_name = normalize_text(product)
    prefix = f"针对 {product_name}，" if product_name else ""
    source_urls = [item.get("url", "") for item in results if item.get("url")]
    source_hint = ""
    if source_urls:
        source_hint = f" 同时关注厂商公告、代码仓库 Release 或安全通告中的修复版本，已检索到的参考地址包括：{source_urls[0]}"
    return f"{prefix}{base}{source_hint}"


def build_security_guidance(
    fields: Dict[str, str],
    title: str,
    product: str,
    vendor: str,
    category: str,
    description: str,
) -> Dict[str, object]:
    """返回可直接写入 JSON/Word 的漏洞危害和修复方案。"""
    direct_impact = pick_direct(fields, ("漏洞危害", "危害说明", "影响说明"))
    direct_solution = pick_direct(fields, ("修复方案", "临时解决方案", "正式解决方案", "修复建议", "解决方案"))
    queries = build_queries(title, product, vendor, category)
    results: list[dict[str, str]] = []
    warnings: list[str] = []
    used_web = False
    if not direct_impact or not direct_solution:
        results, warnings = websearch(queries)
        used_web = bool(results)

    impact = direct_impact or compose_impact(category, product, description, results)
    solution = direct_solution or compose_solution(category, product, results)
    return {
        "impact": impact,
        "solution": solution,
        "solution_type": "临时方案",
        "queries": queries,
        "results": results,
        "warnings": warnings,
        "impact_source": "word" if direct_impact else "websearch" if used_web else "category_strategy",
        "solution_source": "word" if direct_solution else "websearch" if used_web else "category_strategy",
        "websearch_enabled": env_bool("NCC_WEBSEARCH_ENABLED", True),
    }
