#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from render_wechat_article import parse_alert, render, DEFAULT_TEMPLATE


SAMPLE = """![](./logo.JPG)

> 近日安恒信息CERT监测到测试组件存在远程代码执行漏洞。

# 一、 漏洞信息

测试组件是测试产品。

<table>
  <tr><th>漏洞标题</th><th>测试组件存在远程代码执行漏洞</th></tr>
  <tr><td>漏洞处置等级</td><td>1级</td></tr>
  <tr><td>CVSS3.1评分</td><td>9.8</td></tr>
  <tr><td>CVE编号</td><td>CVE-2026-0001</td></tr>
  <tr><td>CNVD编号</td><td>未分配</td></tr>
  <tr><td>CNNVD编号</td><td>未分配</td></tr>
  <tr><td>安恒CERT编号</td><td>DM-202604-000001</td></tr>
  <tr><td>Poc情况</td><td>已发现</td></tr>
  <tr><td>Exp情况</td><td>未发现</td></tr>
  <tr><td>在野利用</td><td>未发现</td></tr>
  <tr><td>研究情况</td><td>已复现</td></tr>
  <tr><td>危害描述</td><td>攻击者可远程执行代码。</td></tr>
</table>

## 漏洞描述

该漏洞源于输入校验不当。

```bash
# 这不是标题
echo test
```

# 二、 修复方案

官方修复方案:

升级至 2.0.1。

临时缓解方案:

- 限制公网访问。
- 启用 WAF 规则。

# 三、 参考资料

1. 厂商安全公告
2. https://example.com/advisory

# 四、 产品能力覆盖

<table>
  <tr><th>产品名称</th><th>覆盖补丁包</th></tr>
  <tr><td>WAF</td><td>已支持</td>
  <tr><td>玄武盾</td><td>已支持</td>
</table>
"""


class RenderWechatArticleTests(unittest.TestCase):
    def test_render_is_deterministic_and_uses_table_title(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "sample.md"
            source.write_text(SAMPLE, encoding="utf-8")
            data = parse_alert(SAMPLE, source)
            first = render(data, DEFAULT_TEMPLATE)
            second = render(data, DEFAULT_TEMPLATE)

        self.assertEqual(data.title, "测试组件存在远程代码执行漏洞")
        self.assertEqual(hashlib.sha256(first.encode()).hexdigest(), hashlib.sha256(second.encode()).hexdigest())
        self.assertIn("漏洞概述", first)
        self.assertIn("产品能力覆盖", first)
        self.assertIn("WAF", first)
        self.assertNotIn("这不是标题", data.title)

    def test_output_has_no_editor_or_page_shell_markers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "sample.md"
            source.write_text(SAMPLE, encoding="utf-8")
            data = parse_alert(SAMPLE, source)
            output = render(data, DEFAULT_TEMPLATE)

        forbidden = ["<style", "<script", "class=", "contenteditable=", "ProseMirror", "onclick="]
        for marker in forbidden:
            self.assertNotIn(marker, output)


if __name__ == "__main__":
    unittest.main()
