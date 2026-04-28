#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import batch_report


def quiet_call(func, *args, **kwargs):
    with redirect_stdout(StringIO()):
        return func(*args, **kwargs)


class BatchReportTests(unittest.TestCase):
    def make_batch(self, root: Path, platform: str) -> Path:
        batch_dir = root / "杭州安恒信息原创漏洞报送2个-2026-04-28-094514"
        batch_dir.mkdir()
        for das_id, title in [
            ("DAS-T106035", "RestartServer 路径遍历漏洞"),
            ("DAS-T106034", "HttpRestartServer 反序列化漏洞"),
        ]:
            das_dir = batch_dir / f"{das_id}-{title}"
            platform_dir = das_dir / f"{platform}-{title}"
            platform_dir.mkdir(parents=True)
            (platform_dir / f"{title}.docx").write_text("placeholder", encoding="utf-8")
        return batch_dir

    def test_scan_batch_orders_das_directories_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            batch_dir = self.make_batch(Path(tmp), batch_report.PLATFORM)

            items, skipped = batch_report.scan_batch(batch_dir, batch_report.PLATFORM)

        self.assertEqual([], skipped)
        self.assertEqual(["DAS-T106034", "DAS-T106035"], [item["das_id"] for item in items])
        self.assertTrue(all(batch_report.PLATFORM in item["platform_dir"] for item in items))

    def test_init_start_and_record_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            batch_dir = self.make_batch(root, batch_report.PLATFORM)
            state_path = root / "batch_state.json"

            quiet_call(batch_report.command_init, SimpleNamespace(batch_dir=str(batch_dir), output=str(state_path), force=False))
            state = batch_report.read_state(state_path)
            self.assertEqual(batch_report.PLATFORM, state["platform"])
            self.assertEqual(2, len(state["items"]))

            quiet_call(batch_report.command_start_next, SimpleNamespace(state=str(state_path), skip_env_check=False))
            state = batch_report.read_state(state_path)
            first = state["items"][0]
            self.assertEqual("in_progress", first["status"])
            self.assertIn("contexts", first["context_file"])
            self.assertNotIn("--skip-env-check", batch_report.start_next_command(state))

            quiet_call(batch_report.command_mark_env, SimpleNamespace(state=str(state_path)))
            state = batch_report.read_state(state_path)
            self.assertIn("--skip-env-check", batch_report.start_next_command(state, skip_env_check=state["env_checked"]))

            quiet_call(batch_report.command_record, SimpleNamespace(
                state=str(state_path),
                das_id=first["das_id"],
                index=0,
                platform_id=f"{batch_report.PLATFORM}-TEST-1",
                context=first["context_file"],
                status="submitted",
                error="",
            ))
            state = batch_report.read_state(state_path)
            self.assertEqual("submitted", state["items"][0]["status"])
            self.assertEqual(f"{batch_report.PLATFORM}-TEST-1", state["items"][0]["platform_id"])

    def test_build_notify_text_uses_one_link_per_result(self):
        state = {
            "platform": batch_report.PLATFORM,
            "batch_name": "batch",
            "items": [{"status": "submitted"}, {"status": "submitted"}],
        }
        results = [
            {"das_id": "DAS-T1", "platform_id": "ID-1", "vuln_name": "漏洞1", "zip_name": "a.zip", "zip_size_mb": 1, "download_url": "http://x/a.zip"},
            {"das_id": "DAS-T2", "platform_id": "ID-2", "vuln_name": "漏洞2", "zip_name": "b.zip", "zip_size_mb": 2, "download_url": "http://x/b.zip"},
        ]

        text, links = batch_report.build_notify_text(state, results)

        self.assertIn("总数：2", text)
        self.assertEqual(2, len(links))
        self.assertIn("DAS-T1", links[0])


if __name__ == "__main__":
    unittest.main()
