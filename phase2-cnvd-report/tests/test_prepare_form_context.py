#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from prepare_form_context import build_context


class PrepareFormContextTests(unittest.TestCase):
    def test_default_captcha_flow_uses_element_screenshot_local_ocr(self):
        args = argparse.Namespace(target="DAS-TEST-001", data_dir="/tmp", output=None)
        extracted = {
            "das_id": "DAS-TEST-001",
            "title": "Example 命令执行漏洞",
            "description": "Example description",
            "vuln_type": "命令执行",
            "vuln_type_raw": "命令执行",
            "url": "https://example.test",
            "unit_name": "Example Vendor",
            "is_event": "0",
            "soft_style_id": "29",
            "discoverer_name": "tester",
            "affected_product": "Example Product",
            "version": "1.0",
            "folder_path": "/tmp",
            "docx_path": "/tmp/example.docx",
            "attachment_zip_path": "/tmp/CNVD-example.zip",
        }

        with patch("prepare_form_context.resolve_target", return_value=("DAS-TEST-001", "/tmp", "")):
            with patch("prepare_form_context.extract_cnvd_data", return_value=extracted):
                with patch("prepare_form_context.file_status", return_value={
                    "path": "/tmp/CNVD-example.zip",
                    "exists": True,
                    "is_file": True,
                    "size_mb": 1,
                    "suffix": ".zip",
                    "name_starts_with_cnvd": True,
                }):
                    context = build_context(args)

        helpers = context["browser_helpers"]
        ocr = context["ocr"]
        self.assertEqual(helpers["open_captcha_tab_command"], "python3 scripts/browser_snippets.py captcha-tab")
        self.assertEqual(ocr["recognize_command"], "python3 scripts/captcha_ocr.py /tmp/captcha.png --preprocess cnvd")
        self.assertIn("/tmp/captcha.png", ocr["recognize_command"])
        self.assertNotIn("--server-url", ocr["recognize_command"])
        self.assertNotIn("start_command", ocr)
        self.assertNotIn("preferred_server_url", ocr)
        self.assertNotIn("captcha_image_data_command", helpers)
        self.assertNotIn("recognize_base64_command", ocr)
        self.assertIn("禁止默认改用后台 OCR 进程", ocr["submit_rule"])


if __name__ == "__main__":
    unittest.main()
