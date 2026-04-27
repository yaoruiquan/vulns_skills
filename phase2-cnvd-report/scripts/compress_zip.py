#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 CNVD 单漏洞整包 zip。"""

from __future__ import annotations

import argparse
import os
import zipfile
from pathlib import Path


def default_zip_output(folder_path: str, prefix: str = "CNVD") -> Path:
    """生成默认 zip 输出路径，输出到材料目录父级。"""
    folder = Path(folder_path).expanduser().resolve()
    name = folder.name
    if not name.upper().startswith(prefix.upper()):
        name = f"{prefix}-{name}"
    return folder.parent / f"{name}.zip"


def compress_folder(folder_path: str, output_path: str = "", include_root: bool = True) -> str:
    """将文件夹压缩为 zip 文件，返回 zip 文件路径。"""
    folder = Path(folder_path).expanduser().resolve()
    if not folder.is_dir():
        raise ValueError(f"文件夹不存在: {folder}")

    zip_path = Path(output_path).expanduser().resolve() if output_path else default_zip_output(str(folder))
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(folder):
            for name in sorted(files):
                if name.startswith("."):
                    continue
                file_path = Path(root) / name
                if file_path.resolve() == zip_path:
                    continue
                if include_root:
                    arcname = file_path.relative_to(folder.parent)
                else:
                    arcname = file_path.relative_to(folder)
                zf.write(file_path, str(arcname))

    return str(zip_path)


def ensure_submission_zip(folder_path: str, output_path: str = "", prefix: str = "CNVD") -> str:
    """若默认位置已有 zip 则直接返回，否则创建。"""
    folder = Path(folder_path).expanduser().resolve()
    if not folder.is_dir():
        return ""

    candidate = Path(output_path).expanduser().resolve() if output_path else default_zip_output(str(folder), prefix=prefix)
    if candidate.is_file():
        return str(candidate)
    return compress_folder(str(folder), str(candidate), include_root=True)


def build_parser() -> argparse.ArgumentParser:
    """构造命令行参数解析器。"""
    parser = argparse.ArgumentParser(description="压缩 CNVD 材料目录为单漏洞整包 zip")
    parser.add_argument("folder_path", help="CNVD 材料目录路径")
    parser.add_argument("--output", default="", help="输出 zip 路径；默认写到材料目录父级")
    parser.add_argument(
        "--without-root",
        action="store_true",
        help="zip 内不包含最外层目录名；默认保留最外层 CNVD 目录",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    zip_path = compress_folder(args.folder_path, args.output, include_root=not args.without_root)
    print(f"压缩完成: {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
