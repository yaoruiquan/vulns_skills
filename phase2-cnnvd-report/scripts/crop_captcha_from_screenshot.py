#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Crop a captcha image from a full-page screenshot using browser coordinates."""

import argparse
import os
from pathlib import Path

from PIL import Image


def parse_args():
    parser = argparse.ArgumentParser(description="Crop captcha from a full screenshot")
    parser.add_argument("--screenshot", required=True, help="Full-page screenshot path")
    parser.add_argument("--output", default="/tmp/captcha.png", help="Output captcha image path")
    parser.add_argument("--x", type=float, required=True, help="Captcha element x coordinate")
    parser.add_argument("--y", type=float, required=True, help="Captcha element y coordinate")
    parser.add_argument("--width", type=float, required=True, help="Captcha element width")
    parser.add_argument("--height", type=float, required=True, help="Captcha element height")
    parser.add_argument("--viewport-width", type=float, default=0, help="Browser viewport CSS width")
    parser.add_argument("--viewport-height", type=float, default=0, help="Browser viewport CSS height")
    parser.add_argument("--padding", type=float, default=2, help="Extra pixels around the crop")
    return parser.parse_args()


def clamp(value, low, high):
    return max(low, min(high, value))


def main():
    args = parse_args()
    screenshot = Path(args.screenshot)
    if not screenshot.exists():
        print(f"ERROR: screenshot not found: {screenshot}")
        return 1

    with Image.open(screenshot) as image:
        image.load()
        scale_x = image.width / args.viewport_width if args.viewport_width > 0 else 1
        scale_y = image.height / args.viewport_height if args.viewport_height > 0 else scale_x
        # DevTools reports CSS pixels. Most MCP screenshots already use the same
        # coordinate space, so do not infer a scale from a hardcoded viewport.
        x1 = int(clamp((args.x - args.padding) * scale_x, 0, image.width))
        y1 = int(clamp((args.y - args.padding) * scale_y, 0, image.height))
        x2 = int(clamp((args.x + args.width + args.padding) * scale_x, 0, image.width))
        y2 = int(clamp((args.y + args.height + args.padding) * scale_y, 0, image.height))
        if x2 <= x1 or y2 <= y1:
            print(f"ERROR: invalid crop box: {(x1, y1, x2, y2)}")
            return 1
        crop = image.crop((x1, y1, x2, y2))
        if crop.width < 80 or crop.height < 25:
            print(f"ERROR: crop too small: {crop.width}x{crop.height}; check viewport scaling or captcha element coordinates")
            return 1
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        crop.save(output)

    print(os.fspath(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
