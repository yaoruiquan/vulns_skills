#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compress oversized NCC upload zips by transcoding bundled videos with ffmpeg."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any


VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
DEFAULT_MAX_MB = 50.0
COMPRESSION_PROFILES = (
    {"max_width": 854, "max_height": 480, "crf": 32, "audio_bitrate": "64k", "label": "480p-crf32"},
    {"max_width": 640, "max_height": 360, "crf": 34, "audio_bitrate": "48k", "label": "360p-crf34"},
    {"max_width": 480, "max_height": 270, "crf": 36, "audio_bitrate": "48k", "label": "270p-crf36"},
)


def env_bool(name: str, default: bool) -> bool:
    """Read a permissive boolean from env."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on", "是"}


def env_float(name: str, default: float) -> float:
    """Read a float from env with fallback."""
    value = os.environ.get(name, "").strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def size_mb(path: Path) -> float:
    """Return file size in MiB."""
    return round(path.stat().st_size / 1024 / 1024, 3)


def safe_extract(zip_path: Path, target_dir: Path) -> None:
    """Extract zip without allowing paths to escape target_dir."""
    target_root = target_dir.resolve()
    with zipfile.ZipFile(zip_path, "r") as zip_handle:
        for member in zip_handle.infolist():
            member_path = (target_root / member.filename).resolve()
            if target_root != member_path and target_root not in member_path.parents:
                raise ValueError(f"zip member escapes target dir: {member.filename}")
        zip_handle.extractall(target_root)


def iter_video_files(root: Path) -> list[Path]:
    """Find videos under an extracted upload package."""
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES)


def ffmpeg_command(ffmpeg_bin: str, input_path: Path, output_path: Path, profile: dict[str, Any]) -> list[str]:
    """Build one ffmpeg transcode command."""
    video_filter = (
        f"scale=w='min({profile['max_width']},iw)':"
        f"h='min({profile['max_height']},ih)':"
        "force_original_aspect_ratio=decrease:force_divisible_by=2,format=yuv420p"
    )
    return [
        ffmpeg_bin,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(input_path),
        "-vf",
        video_filter,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        str(profile["crf"]),
        "-c:a",
        "aac",
        "-b:a",
        str(profile["audio_bitrate"]),
        "-movflags",
        "+faststart",
        str(output_path),
    ]


def transcode_videos(root: Path, ffmpeg_bin: str, profile: dict[str, Any]) -> dict[str, Any]:
    """Compress videos in place, replacing only when the transcoded file is smaller."""
    videos = iter_video_files(root)
    compressed = 0
    warnings: list[str] = []
    details: list[dict[str, Any]] = []
    for video_path in videos:
        before_mb = size_mb(video_path)
        tmp_output = video_path.with_name(f"{video_path.stem}.ncc-compressed.mp4")
        command = ffmpeg_command(ffmpeg_bin, video_path, tmp_output, profile)
        try:
            completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=900)
        except subprocess.TimeoutExpired:
            warnings.append(f"ffmpeg timeout: {video_path.name}")
            continue
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}"
            warnings.append(f"ffmpeg failed for {video_path.name}: {message[:240]}")
            tmp_output.unlink(missing_ok=True)
            continue
        if not tmp_output.exists() or tmp_output.stat().st_size <= 0:
            warnings.append(f"ffmpeg produced empty output: {video_path.name}")
            tmp_output.unlink(missing_ok=True)
            continue

        after_mb = size_mb(tmp_output)
        if tmp_output.stat().st_size >= video_path.stat().st_size:
            warnings.append(f"compressed video not smaller, kept original: {video_path.name}")
            tmp_output.unlink(missing_ok=True)
            continue

        if video_path.suffix.lower() == ".mp4":
            target_path = video_path
        else:
            target_path = video_path.with_suffix(".mp4")
            video_path.unlink()
        shutil.move(str(tmp_output), target_path)
        compressed += 1
        details.append(
            {
                "path": str(target_path.relative_to(root)),
                "before_mb": before_mb,
                "after_mb": after_mb,
                "profile": profile["label"],
            }
        )
    return {"video_count": len(videos), "compressed_video_count": compressed, "warnings": warnings, "details": details}


def repack_zip(source_dir: Path, output_zip: Path) -> None:
    """Write a zip from an extracted directory."""
    tmp_zip = output_zip.with_suffix(output_zip.suffix + ".tmp")
    tmp_zip.unlink(missing_ok=True)
    with zipfile.ZipFile(tmp_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zip_handle:
        for file_path in sorted(path for path in source_dir.rglob("*") if path.is_file()):
            if file_path.name.startswith(".DS_Store") or "__MACOSX" in file_path.parts:
                continue
            zip_handle.write(file_path, arcname=str(file_path.relative_to(source_dir)))
    tmp_zip.replace(output_zip)


def compressed_zip_path(zip_path: Path) -> Path:
    """Return the sibling output path for a compressed runtime zip."""
    if zip_path.stem.endswith("-compressed"):
        return zip_path
    return zip_path.with_name(f"{zip_path.stem}-compressed{zip_path.suffix}")


def compress_zip_if_needed(
    zip_path: Path,
    max_mb: float | None = None,
    enabled: bool | None = None,
    ffmpeg_bin: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Compress videos inside zip when it exceeds the NCC upload limit."""
    max_size_mb = max_mb if max_mb is not None else env_float("NCC_UPLOAD_MAX_MB", DEFAULT_MAX_MB)
    compression_enabled = enabled if enabled is not None else env_bool("NCC_VIDEO_COMPRESS_ENABLED", True)
    ffmpeg = ffmpeg_bin or os.environ.get("NCC_FFMPEG_BIN") or shutil.which("ffmpeg") or "ffmpeg"

    result: dict[str, Any] = {
        "path": str(zip_path),
        "original_path": str(zip_path),
        "original_size_mb": 0,
        "size_mb": 0,
        "limit_mb": max_size_mb,
        "compressed": False,
        "attempted": False,
        "ok": False,
        "video_count": 0,
        "compressed_video_count": 0,
        "profile": "",
        "warnings": [],
        "details": [],
    }

    if not zip_path.exists():
        result["warnings"].append(f"zip not found: {zip_path}")
        return result

    result["original_size_mb"] = size_mb(zip_path)
    result["size_mb"] = result["original_size_mb"]
    result["ok"] = result["size_mb"] <= max_size_mb
    if result["ok"] and not force:
        return result
    if not compression_enabled:
        result["warnings"].append("NCC_VIDEO_COMPRESS_ENABLED is disabled")
        return result
    if not shutil.which(ffmpeg) and not Path(ffmpeg).exists():
        result["warnings"].append(f"ffmpeg not found: {ffmpeg}")
        return result

    result["attempted"] = True
    output_zip = compressed_zip_path(zip_path)
    best_zip = ""
    best_size = result["original_size_mb"]
    best_profile = ""
    all_warnings: list[str] = []
    all_details: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="ncc-video-compress-") as tmp_dir:
        tmp_root = Path(tmp_dir)
        original_extract = tmp_root / "original"
        original_extract.mkdir()
        safe_extract(zip_path, original_extract)
        result["video_count"] = len(iter_video_files(original_extract))
        if result["video_count"] == 0:
            result["warnings"].append("no video files found in zip")
            return result

        for profile in COMPRESSION_PROFILES:
            work_dir = tmp_root / f"work-{profile['label']}"
            shutil.copytree(original_extract, work_dir)
            transcode_result = transcode_videos(work_dir, ffmpeg, profile)
            all_warnings.extend(transcode_result["warnings"])
            all_details.extend(transcode_result["details"])
            candidate_zip = tmp_root / f"candidate-{profile['label']}.zip"
            repack_zip(work_dir, candidate_zip)
            candidate_size = size_mb(candidate_zip)
            if candidate_size < best_size:
                best_size = candidate_size
                best_profile = profile["label"]
                shutil.copy2(candidate_zip, output_zip)
                best_zip = str(output_zip)
                result["compressed_video_count"] = transcode_result["compressed_video_count"]
            if candidate_size <= max_size_mb:
                break

    if best_zip:
        result["path"] = best_zip
        result["size_mb"] = best_size
        result["compressed"] = True
        result["profile"] = best_profile
        result["ok"] = best_size <= max_size_mb
    else:
        result["ok"] = result["original_size_mb"] <= max_size_mb
        all_warnings.append("video compression did not reduce zip size")

    if not result["ok"]:
        all_warnings.append(f"zip still exceeds NCC limit: {result['size_mb']} MB > {max_size_mb} MB")
    result["warnings"] = all_warnings
    result["details"] = all_details
    return result


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(description="Compress oversized NCC upload zip videos with ffmpeg")
    parser.add_argument("zip_path", help="NCC upload zip path")
    parser.add_argument("--max-mb", type=float, default=None, help="Upload limit in MiB, default NCC_UPLOAD_MAX_MB or 50")
    parser.add_argument("--ffmpeg-bin", default="", help="ffmpeg binary path, default NCC_FFMPEG_BIN or PATH lookup")
    parser.add_argument("--force", action="store_true", help="Compress even when zip is already under the limit")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    result = compress_zip_if_needed(
        Path(args.zip_path).expanduser(),
        max_mb=args.max_mb,
        ffmpeg_bin=args.ffmpeg_bin or None,
        force=args.force,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
