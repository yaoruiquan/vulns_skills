#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证码 OCR 识别脚本。"""

import argparse
import os


_OCR = None


def get_ocr():
    """懒加载 OCR 模型。"""
    global _OCR
    if _OCR is None:
        import ddddocr
        _OCR = ddddocr.DdddOcr(show_ad=False)
    return _OCR


def classify_image_bytes(image_data: bytes) -> str:
    """识别图片二进制内容。"""
    result = get_ocr().classification(image_data)
    return result.strip()


def recognize_captcha(image_path: str) -> str:
    """识别验证码图片。"""
    if not os.path.exists(image_path):
        return f"ERROR: 图片不存在: {image_path}"

    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
        return classify_image_bytes(image_data)
    except Exception as e:
        return f"ERROR: 识别失败: {str(e)}"


def parse_args():
    parser = argparse.ArgumentParser(description="验证码 OCR 识别")
    parser.add_argument("image_path", help="验证码图片路径")
    return parser.parse_args()


def main():
    args = parse_args()
    result = recognize_captcha(args.image_path)
    print(result)
    return 1 if result.startswith("ERROR") else 0


if __name__ == "__main__":
    raise SystemExit(main())
