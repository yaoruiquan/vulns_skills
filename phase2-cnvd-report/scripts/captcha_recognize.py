#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证码识别包装脚本，支持 OCR 失败后回退到人工识别。"""

import argparse
import json
import os
import sys
from pathlib import Path


def recognize_with_fallback(image_path, context="login", preprocess="cnvd",
                            max_ocr_attempts=2, state_file=None):
    """
    验证码识别，支持 OCR 失败后回退到人工识别。

    Args:
        image_path: 验证码图片路径
        context: 上下文（login/submit）
        preprocess: OCR 预处理模式
        max_ocr_attempts: OCR 最大尝试次数
        state_file: 状态文件路径（用于跨调用计数）

    Returns:
        包含识别结果的字典
    """
    if not os.path.exists(image_path):
        return {"ok": False, "error": "图片不存在: {}".format(image_path)}

    # 读取或初始化状态
    state = {"ocr_attempts": 0, "context": context}
    if state_file and os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                state = json.load(f)
        except:
            pass

    # 检查是否已超过 OCR 尝试次数
    if state["ocr_attempts"] >= max_ocr_attempts:
        sys.stderr.write("OCR 已失败 {} 次，切换到人工识别\n".format(state["ocr_attempts"]))
        return request_manual_input(image_path, context)

    # 尝试 OCR 识别
    state["ocr_attempts"] += 1
    if state_file:
        state_file_path = Path(state_file)
        state_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, "w") as f:
            json.dump(state, f)

    sys.stderr.write("尝试 OCR 识别（第 {}/{} 次）\n".format(
        state["ocr_attempts"], max_ocr_attempts))

    # 调用 OCR
    from captcha_ocr import recognize_captcha
    result = recognize_captcha(image_path, preprocess=preprocess)

    if result.startswith("ERROR"):
        return {
            "ok": False,
            "error": result,
            "method": "ocr",
            "attempts": state["ocr_attempts"]
        }

    return {
        "ok": True,
        "code": result,
        "method": "ocr",
        "attempts": state["ocr_attempts"],
        "note": "如果此验证码识别错误，将在第 {} 次失败后切换到人工识别".format(max_ocr_attempts)
    }


def request_manual_input(image_path, context):
    """请求外部人工输入验证码。

    服务化任务没有可交互 stdin。这里输出明确标记并用退出码 2
    通知上层流程把截图和验证码请求转交给前端处理。
    """
    abs_path = os.path.abspath(image_path)

    request = {
        "type": "manual_captcha_request",
        "context": context,
        "image_path": abs_path,
        "message": "OCR 识别失败，需要人工识别验证码",
        "status": "MANUAL_INPUT_REQUIRED",
        "instructions": [
            "1. 将图片返回给前端或人工处理通道: {}".format(abs_path),
            "2. 等待人工输入验证码",
            "3. 上层流程拿到验证码后重新填入页面"
        ]
    }

    sys.stderr.write(json.dumps(request, ensure_ascii=False, indent=2) + "\n")
    return {
        "ok": False,
        "error": "MANUAL_INPUT_REQUIRED",
        "method": "manual",
        "image_path": abs_path,
        "context": context,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="验证码识别（OCR + 人工回退）")
    parser.add_argument("image_path", help="验证码图片路径")
    parser.add_argument("--context", default="login", choices=["portal", "login", "submit"],
                        help="验证码上下文")
    parser.add_argument("--preprocess", default="cnvd", choices=["none", "cnvd"],
                        help="OCR 预处理模式")
    parser.add_argument("--max-ocr-attempts", type=int, default=2,
                        help="OCR 最大尝试次数，超过后切换到人工识别")
    parser.add_argument("--state-file", default=None,
                        help="状态文件路径（用于跨调用计数）")
    return parser.parse_args()


def main():
    args = parse_args()
    result = recognize_with_fallback(
        args.image_path,
        context=args.context,
        preprocess=args.preprocess,
        max_ocr_attempts=args.max_ocr_attempts,
        state_file=args.state_file
    )

    if result["ok"]:
        # 只输出验证码到 stdout
        print(result["code"])
        return 0
    else:
        error = result.get("error", "Unknown error")
        if error == "MANUAL_INPUT_REQUIRED":
            print("MANUAL_INPUT_REQUIRED")
            return 2
        sys.stderr.write("ERROR: {}\n".format(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
