#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from extract_vuln_data import CNVD_VULN_TYPE_OPTIONS, map_cnvd_vuln_type


class VulnTypeMappingTests(unittest.TestCase):
    def test_all_cnvd_page_options_are_preserved(self):
        for option in CNVD_VULN_TYPE_OPTIONS:
            with self.subTest(option=option):
                self.assertEqual(map_cnvd_vuln_type(option), option)

    def test_command_execution_does_not_fallback_to_other(self):
        self.assertEqual(map_cnvd_vuln_type("命令执行"), "命令执行")
        self.assertEqual(map_cnvd_vuln_type("远程代码执行"), "命令执行")
        self.assertEqual(map_cnvd_vuln_type("反序列化远程代码执行"), "命令执行")

    def test_common_aliases_map_to_page_options(self):
        cases = {
            "跨站脚本": "XSS",
            "XXE": "XML实体注入",
            "服务端请求伪造": "SSRF",
            "路径遍历": "目录遍历",
            "DoS": "拒绝服务",
            "文件读取": "任意文件读取",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(map_cnvd_vuln_type(raw), expected)


if __name__ == "__main__":
    unittest.main()
