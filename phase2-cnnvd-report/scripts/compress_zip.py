#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""压缩附件文件夹为 zip 文件"""

import zipfile
import os
import sys

def compress_folder(folder_path: str) -> str:
    """将文件夹压缩为 zip 文件，返回 zip 文件路径

    Args:
        folder_path: 要压缩的文件夹路径

    Returns:
        zip 文件路径
    """
    if not os.path.isdir(folder_path):
        raise ValueError(f"文件夹不存在: {folder_path}")

    zip_path = folder_path.rstrip('/') + ".zip"

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(folder_path):
            for f in files:
                # 跳过隐藏文件
                if f.startswith('.'):
                    continue
                fp = os.path.join(root, f)
                # 使用相对路径作为 zip 内路径
                arcname = os.path.relpath(fp, folder_path)
                zf.write(fp, arcname)

    print(f"压缩完成: {zip_path}")
    return zip_path

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 compress_zip.py <folder_path>")
        sys.exit(1)

    folder = sys.argv[1]
    compress_folder(folder)
