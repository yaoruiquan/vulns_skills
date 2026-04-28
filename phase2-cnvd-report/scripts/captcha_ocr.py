#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证码 OCR 识别脚本，支持单次识别和常驻服务快速识别。"""

from __future__ import annotations

import argparse
import json
import sys
import os
import time
from io import BytesIO
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib import request


_OCR = None


def get_ocr():
    """懒加载 OCR 模型；常驻服务模式下只加载一次。"""
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


def recognize_via_server(image_path: str, server_url: str, preprocess: str = "none", crop_box: str = "", scale: int = 1) -> str:
    """调用本地 OCR 常驻服务识别，避免每次重新加载模型。"""
    if not os.path.exists(image_path):
        return f"ERROR: 图片不存在: {image_path}"

    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
        image_data = preprocess_image_bytes(image_data, preprocess=preprocess, crop_box=crop_box, scale=scale)
        req = request.Request(
            server_url.rstrip("/") + "/ocr",
            data=image_data,
            headers={"Content-Type": "application/octet-stream"},
            method="POST",
        )
        with request.urlopen(req, timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if not payload.get("ok"):
            return f"ERROR: 识别失败: {payload.get('error', 'unknown')}"
        return str(payload.get("result", "")).strip()
    except Exception as e:
        return f"ERROR: 服务识别失败: {str(e)}"


class OcrHandler(BaseHTTPRequestHandler):
    """极简本地 HTTP OCR 服务。"""

    def do_POST(self):
        if self.path != "/ocr":
            self.send_error(404)
            return

        content_length = int(self.headers.get("Content-Length", "0") or "0")
        image_data = self.rfile.read(content_length)
        start = time.time()
        try:
            result = classify_image_bytes(image_data)
            payload = {
                "ok": True,
                "result": result,
                "elapsed_ms": round((time.time() - start) * 1000, 2),
            }
            status = 200
        except Exception as e:
            payload = {"ok": False, "error": str(e)}
            status = 500

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


def serve(host: str, port: int) -> int:
    """启动本地 OCR 服务。"""
    get_ocr()
    server = HTTPServer((host, port), OcrHandler)
    print(f"CNVD captcha OCR server listening on http://{host}:{port}", flush=True)
    server.serve_forever()
    return 0


def parse_args():
    parser = argparse.ArgumentParser(description="CNVD 验证码 OCR 识别")
    parser.add_argument("image_path", nargs="?", help="验证码图片路径")
    parser.add_argument("--server-url", default=os.environ.get("CAPTCHA_OCR_SERVER_URL", ""), help="本地 OCR 服务地址")
    parser.add_argument("--preprocess", choices=["none", "cnvd"], default="none", help="图片预处理模式；cnvd 会裁掉右侧提示文字并放大")
    parser.add_argument("--crop-box", default="", help="旧截图排障裁剪框 x1,y1,x2,y2；支持像素或 0-1 比例")
    parser.add_argument("--scale", type=int, default=1, help="识别前放大倍数")
    parser.add_argument("--serve", action="store_true", help="启动常驻 OCR 服务")
    parser.add_argument("--host", default="127.0.0.1", help="OCR 服务监听地址")
    parser.add_argument("--port", type=int, default=18765, help="OCR 服务监听端口")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.serve:
        return serve(args.host, args.port)

    if not args.image_path:
        print("用法: python3 captcha_ocr.py <图片路径>")
        return 1

    if args.server_url:
        result = recognize_via_server(args.image_path, args.server_url, preprocess=args.preprocess, crop_box=args.crop_box, scale=args.scale)
    else:
        result = recognize_captcha(args.image_path, preprocess=args.preprocess, crop_box=args.crop_box, scale=args.scale)
    print(result)

    if result.startswith("ERROR"):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
