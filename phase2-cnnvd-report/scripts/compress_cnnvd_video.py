#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compress CNNVD verification videos to stay below the platform size limit."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path


DEFAULT_MAX_MB = 50.0
DEFAULT_TARGET_MB = 48.0
DEFAULT_AUDIO_KBPS = 96
DEFAULT_MAX_WIDTH = 1280


def file_size_mb(path: Path) -> float:
    return round(path.stat().st_size / 1024 / 1024, 2)


def require_binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"缺少依赖: {name}，请先安装 ffmpeg")
    return path


def probe_duration_seconds(input_path: Path) -> float:
    ffprobe = require_binary("ffprobe")
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(input_path),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    try:
        duration = float(result.stdout.strip())
    except ValueError as exc:
        raise SystemExit(f"无法读取视频时长: {input_path}") from exc
    if duration <= 0:
        raise SystemExit(f"视频时长无效: {input_path}")
    return duration


def default_output_path(input_path: Path, output_dir: str = "") -> Path:
    directory = Path(output_dir).expanduser() if output_dir else input_path.parent / "cnnvd-compressed"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{input_path.stem}-cnnvd-compressed.mp4"


def target_video_kbps(target_mb: float, duration_seconds: float, audio_kbps: int) -> int:
    target_bits = target_mb * 1024 * 1024 * 8 * 0.96
    total_kbps = math.floor(target_bits / duration_seconds / 1000)
    return max(220, total_kbps - audio_kbps)


def ffmpeg_command(input_path: Path, output_path: Path, video_kbps: int, audio_kbps: int, max_width: int) -> list[str]:
    ffmpeg = require_binary("ffmpeg")
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-i",
        str(input_path),
    ]
    if max_width > 0:
        command.extend(["-vf", f"scale=trunc(min({max_width}\\,iw)/2)*2:-2"])
    command.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-b:v",
            f"{video_kbps}k",
            "-maxrate",
            f"{video_kbps}k",
            "-bufsize",
            f"{video_kbps * 2}k",
            "-c:a",
            "aac",
            "-b:a",
            f"{audio_kbps}k",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
    return command


def compress_video(
    input_path: str,
    *,
    max_mb: float = DEFAULT_MAX_MB,
    target_mb: float = DEFAULT_TARGET_MB,
    output: str = "",
    output_dir: str = "",
    audio_kbps: int = DEFAULT_AUDIO_KBPS,
    max_width: int = DEFAULT_MAX_WIDTH,
    force: bool = False,
    dry_run: bool = False,
) -> dict:
    source = Path(input_path).expanduser().resolve()
    if not source.is_file():
        raise SystemExit(f"视频文件不存在: {source}")

    original_mb = file_size_mb(source)
    if original_mb <= max_mb and not force:
        return {
            "compressed": False,
            "reason": "within_limit",
            "input_path": str(source),
            "output_path": str(source),
            "original_size_mb": original_mb,
            "output_size_mb": original_mb,
            "max_mb": max_mb,
        }

    if target_mb >= max_mb:
        target_mb = max_mb * 0.96

    duration = probe_duration_seconds(source)
    destination = Path(output).expanduser().resolve() if output else default_output_path(source, output_dir).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    initial_video_kbps = target_video_kbps(target_mb, duration, audio_kbps)
    attempts = []
    current_kbps = initial_video_kbps
    command = []
    for attempt in range(1, 4):
        command = ffmpeg_command(source, destination, current_kbps, audio_kbps, max_width)
        attempts.append({"attempt": attempt, "video_kbps": current_kbps, "command": command})
        if dry_run:
            break
        subprocess.run(command, check=True)
        output_mb = file_size_mb(destination)
        attempts[-1]["output_size_mb"] = output_mb
        if output_mb <= max_mb:
            return {
                "compressed": True,
                "input_path": str(source),
                "output_path": str(destination),
                "original_size_mb": original_mb,
                "output_size_mb": output_mb,
                "duration_seconds": round(duration, 2),
                "video_kbps": current_kbps,
                "audio_kbps": audio_kbps,
                "max_mb": max_mb,
                "target_mb": target_mb,
                "attempts": attempts,
            }
        current_kbps = max(180, int(current_kbps * 0.82))

    if dry_run:
        return {
            "compressed": True,
            "dry_run": True,
            "input_path": str(source),
            "output_path": str(destination),
            "original_size_mb": original_mb,
            "duration_seconds": round(duration, 2),
            "video_kbps": current_kbps,
            "audio_kbps": audio_kbps,
            "max_mb": max_mb,
            "target_mb": target_mb,
            "command": command,
            "attempts": attempts,
        }

    final_mb = file_size_mb(destination) if destination.is_file() else 0
    raise SystemExit(f"压缩后仍超过限制: {destination} {final_mb} MB > {max_mb} MB")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="压缩 CNNVD 验证视频到 50MB 限制以内")
    parser.add_argument("input", help="原始视频路径")
    parser.add_argument("--output", default="", help="输出视频路径；默认写入原目录 cnnvd-compressed/")
    parser.add_argument("--output-dir", default="", help="默认输出目录；指定 --output 时忽略")
    parser.add_argument("--max-mb", type=float, default=DEFAULT_MAX_MB, help="平台最大限制，默认 50")
    parser.add_argument("--target-mb", type=float, default=DEFAULT_TARGET_MB, help="压缩目标大小，默认 48")
    parser.add_argument("--audio-kbps", type=int, default=DEFAULT_AUDIO_KBPS, help="音频码率，默认 96")
    parser.add_argument("--max-width", type=int, default=DEFAULT_MAX_WIDTH, help="最大宽度，默认 1280；0 表示不缩放")
    parser.add_argument("--force", action="store_true", help="即使原视频未超限也重新压缩")
    parser.add_argument("--dry-run", action="store_true", help="只输出计划，不执行 ffmpeg")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = compress_video(
        args.input,
        max_mb=args.max_mb,
        target_mb=args.target_mb,
        output=args.output,
        output_dir=args.output_dir,
        audio_kbps=args.audio_kbps,
        max_width=args.max_width,
        force=args.force,
        dry_run=args.dry_run,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"input={result['input_path']}")
        print(f"output={result['output_path']}")
        print(f"compressed={result['compressed']}")
        print(f"size={result.get('original_size_mb')}MB -> {result.get('output_size_mb', 'dry-run')}MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
