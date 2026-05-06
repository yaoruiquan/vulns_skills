#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证码 OCR 识别脚本。"""

from __future__ import annotations

import argparse
import os
from io import BytesIO


_OCR = None


def get_ocr():
    """懒加载 OCR 模型。"""
    global _OCR
    if _OCR is None:
        import ddddocr
        _OCR = ddddocr.DdddOcr(show_ad=False)
    return _OCR


def parse_crop_box(crop_box: str, width: int, height: int) -> tuple[int, int, int, int] | None:
    """解析 x1,y1,x2,y2 裁剪框；小于等于 1 的值按比例处理。"""
    if not crop_box:
        return None
    parts = [item.strip() for item in crop_box.split(",")]
    if len(parts) != 4:
        raise ValueError("--crop-box 格式应为 x1,y1,x2,y2")
    values = [float(item) for item in parts]
    x1, y1, x2, y2 = values
    if all(0 <= item <= 1 for item in values):
        x1, x2 = x1 * width, x2 * width
        y1, y2 = y1 * height, y2 * height
    box = tuple(int(round(item)) for item in (x1, y1, x2, y2))
    if box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError("--crop-box 裁剪范围无效")
    return box


def preprocess_image_bytes(image_data: bytes, preprocess: str = "none", crop_box: str = "", scale: int = 1) -> bytes:
    """按 CNVD 验证码场景增强、放大图片；裁剪仅用于兼容旧页面截图排障。"""
    if preprocess == "none" and not crop_box and scale <= 1:
        return image_data

    try:
        from PIL import Image, ImageOps
    except Exception as exc:
        raise RuntimeError("图片预处理需要 Pillow，请先安装 pillow") from exc

    image = Image.open(BytesIO(image_data)).convert("RGB")
    width, height = image.size

    box = parse_crop_box(crop_box, width, height)
    if box:
        image = image.crop(box)
    elif preprocess == "cnvd" and width > height * 2.6:
        # 仅兼容旧截图：如果误截到右侧提示文字，裁掉非验证码区域。
        image = image.crop((0, 0, min(width, int(height * 2.4)), height))

    if preprocess == "cnvd":
        image = ImageOps.autocontrast(image)
        scale = max(scale, 3)

    if scale > 1:
        resampling = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
        image = image.resize((image.width * scale, image.height * scale), resampling)

    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def classify_image_bytes(image_data: bytes, preprocess: str = "none", crop_box: str = "", scale: int = 1) -> str:
    """识别图片二进制内容。"""
    image_data = preprocess_image_bytes(image_data, preprocess=preprocess, crop_box=crop_box, scale=scale)
    result = get_ocr().classification(image_data)
    return result.strip()


def recognize_captcha(image_path: str, preprocess: str = "none", crop_box: str = "", scale: int = 1) -> str:
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
        with open(image_path, "rb") as f:
            image_data = f.read()
        return classify_image_bytes(image_data, preprocess=preprocess, crop_box=crop_box, scale=scale)
    except Exception as e:
        return f"ERROR: 识别失败: {str(e)}"


def parse_args():
    parser = argparse.ArgumentParser(description="CNVD 验证码 OCR 识别")
    parser.add_argument("image_path", nargs="?", help="验证码图片路径")
    parser.add_argument("--preprocess", choices=["none", "cnvd"], default="none", help="图片预处理模式；cnvd 会裁掉右侧提示文字并放大")
    parser.add_argument("--crop-box", default="", help="旧截图排障裁剪框 x1,y1,x2,y2；支持像素或 0-1 比例")
    parser.add_argument("--scale", type=int, default=1, help="识别前放大倍数")
    return parser.parse_args()


def main():
    args = parse_args()

    if not args.image_path:
        print("用法: python3 captcha_ocr.py <图片路径>")
        return 1

    result = recognize_captcha(args.image_path, preprocess=args.preprocess, crop_box=args.crop_box, scale=args.scale)
    print(result)

    if result.startswith("ERROR"):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
