#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate and print the exact NCC upload zip path from form_context.json."""

from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path


def load_context(path: str) -> dict:
    return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))


def file_summary(path: Path) -> dict:
    exists = path.is_file()
    size = path.stat().st_size if exists else 0
    return {
        "path": str(path),
        "name": path.name,
        "dir": str(path.parent),
        "exists": exists,
        "size_bytes": size,
        "size_mb": round(size / 1024 / 1024, 3) if size else 0.0,
    }


def similar_files(path: Path) -> list[str]:
    folder = path.parent
    if not folder.is_dir():
        return []
    files = [item.name for item in folder.iterdir() if item.is_file()]
    close = difflib.get_close_matches(path.name, files, n=8, cutoff=0.45)
    if close:
        return [str(folder / name) for name in close]
    return [str(item) for item in sorted(folder.glob("*.zip"))[:8] if item.is_file()]


def build_result(context_path: str, candidate_path: str = "") -> dict:
    context = load_context(context_path)
    expected_raw = str(context.get("upload_zip_path") or "")
    if not expected_raw:
        return {
            "ok": False,
            "reason": "form_context.json missing upload_zip_path",
            "context": str(Path(context_path).expanduser()),
        }

    expected = Path(expected_raw).expanduser()
    expected_summary = file_summary(expected)
    result = {
        "ok": expected_summary["exists"] and expected_summary["size_bytes"] > 0,
        "context": str(Path(context_path).expanduser()),
        "filePath": str(expected),
        "upload_zip_path": str(expected),
        "expected": expected_summary,
        "mcp_upload_file": {
            "filePath": str(expected),
        },
    }
    if not result["ok"]:
        result["reason"] = "upload_zip_path does not exist or is empty"
        result["suggestions"] = similar_files(expected)

    if candidate_path:
        candidate = Path(candidate_path).expanduser()
        candidate_summary = file_summary(candidate)
        candidate_matches_expected = (
            candidate.resolve() == expected.resolve()
            if candidate.exists() and expected.exists()
            else str(candidate) == str(expected)
        )
        result["candidate"] = candidate_summary
        result["candidate_matches_expected"] = candidate_matches_expected
        if not candidate_summary["exists"]:
            result["candidate_ok"] = False
            result["candidate_reason"] = "candidate path does not exist; use filePath from this output instead of manually typed filename"
            result["candidate_suggestions"] = similar_files(candidate)
        elif not candidate_matches_expected:
            result["candidate_ok"] = False
            result["candidate_reason"] = "candidate path exists but is not the upload_zip_path recorded in form_context.json"
            result["candidate_suggestions"] = [str(expected)]
        else:
            result["candidate_ok"] = candidate_summary["size_bytes"] > 0
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate NCC upload zip path from form_context.json")
    parser.add_argument("--context", default="", help="form_context.json path")
    parser.add_argument("--batch-root", default="", help="scan all **/form_context.json files under this directory")
    parser.add_argument("--candidate", default="", help="optional manually typed path to compare and diagnose")
    parser.add_argument("--plain", action="store_true", help="print only the exact upload file path")
    parser.add_argument("--verbose", action="store_true", help="include full per-context details in --batch-root output")
    return parser


def build_batch_result(root: str, verbose: bool = False) -> dict:
    root_path = Path(root).expanduser()
    contexts = sorted(root_path.rglob("form_context.json")) if root_path.is_dir() else []
    results = [build_result(str(context_path)) for context_path in contexts]
    failed = [item for item in results if not item.get("ok")]
    checked = [
        {
            "context": item.get("context", ""),
            "filePath": item.get("filePath", ""),
            "size_mb": item.get("expected", {}).get("size_mb", 0),
        }
        for item in results
        if item.get("ok")
    ]
    result = {
        "ok": bool(contexts) and not failed,
        "root": str(root_path),
        "count": len(contexts),
        "failed_count": len(failed),
        "failed": failed,
        "checked": checked,
    }
    if verbose:
        result["results"] = results
    return result


def main() -> int:
    args = build_parser().parse_args()
    if args.batch_root:
        if args.candidate:
            raise SystemExit("--candidate can only be used with --context")
        result = build_batch_result(args.batch_root, verbose=args.verbose)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1
    if not args.context:
        raise SystemExit("missing --context or --batch-root")
    result = build_result(args.context, args.candidate)
    if args.plain:
        print(result.get("filePath") or "")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("ok"):
        return 1
    if args.candidate and not result.get("candidate_ok", False):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
