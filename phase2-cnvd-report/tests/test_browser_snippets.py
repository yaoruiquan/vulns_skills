#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from browser_snippets import captcha_tab_script, captcha_preview_script, submit_captcha_script


class BrowserSnippetTests(unittest.TestCase):
    def test_captcha_tab_opens_current_cnvd_captcha_url_in_new_tab(self):
        script = captcha_tab_script()

        self.assertIn("#codeSpan1 img", script)
        self.assertIn("currentSrc", script)
        self.assertIn("common\\/myCodeNew", script)
        self.assertIn("window.open(src, '_blank')", script)
        self.assertIn("openedNewTab", script)
        self.assertNotIn("image.click", script)
        self.assertNotIn("document.write", script)

    def test_captcha_preview_is_compatibility_alias(self):
        self.assertEqual(captcha_tab_script(), captcha_preview_script())

    def test_submit_captcha_fills_input_and_clicks_submit(self):
        script = submit_captcha_script("ab12")

        self.assertIn("#myCode1", script)
        self.assertIn("#subForm", script)
        self.assertIn('"ab12"', script)


if __name__ == "__main__":
    unittest.main()
