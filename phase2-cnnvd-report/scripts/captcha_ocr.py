#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证码 OCR 识别脚本
使用 ddddocr 识别验证码图片

用法：
    python captcha_ocr.py <图片路径>
    python captcha_ocr.py /tmp/captcha.png
"""

import sys
import os


def recognize_captcha(image_path: str) -> str:
    """
    识别验证码图片

    Args:
        image_path: 验证码图片路径

    Returns:
        识别出的验证码文字
    """
    if not os.path.exists(image_path):
        return f"ERROR: 图片不存在: {image_path}"

    try:
        import ddddocr
        ocr = ddddocr.DdddOcr(show_ad=False)
        with open(image_path, 'rb') as f:
            image_data = f.read()
        result = ocr.classification(image_data)
        return result.strip()
    except Exception as e:
        return f"ERROR: 识别失败: {str(e)}"


def main():
    if len(sys.argv) < 2:
        print("用法: python captcha_ocr.py <图片路径>")
        sys.exit(1)

    result = recognize_captcha(sys.argv[1])
    print(result)

    if result.startswith("ERROR"):
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()