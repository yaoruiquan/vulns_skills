#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证码 OCR 识别脚本，支持单次识别和常驻服务快速识别。"""

import argparse
import json
import os
import time
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


def recognize_via_server(image_path: str, server_url: str) -> str:
    """调用本地 OCR 常驻服务识别，避免每次重新加载模型。"""
    if not os.path.exists(image_path):
        return f"ERROR: 图片不存在: {image_path}"

    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
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
    print(f"Captcha OCR server listening on http://{host}:{port}", flush=True)
    server.serve_forever()
    return 0


def parse_args():
    parser = argparse.ArgumentParser(description="验证码 OCR 识别")
    parser.add_argument("image_path", nargs="?", help="验证码图片路径")
    parser.add_argument("--server-url", default=os.environ.get("CAPTCHA_OCR_SERVER_URL", ""), help="本地 OCR 服务地址")
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
        result = recognize_via_server(args.image_path, args.server_url)
    else:
        result = recognize_captcha(args.image_path)
    print(result)

    if result.startswith("ERROR"):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
