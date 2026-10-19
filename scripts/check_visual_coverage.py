#!/usr/bin/env python3
"""Detect videos whose visible content occupies only a small part of the canvas."""

from __future__ import annotations

import argparse
import json
import shutil
import statistics
import subprocess
from pathlib import Path
from typing import Any


def probe_video(path: Path) -> dict[str, float]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe is required")
    proc = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height:format=duration",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError("video metadata probe failed")
    data = json.loads(proc.stdout)
    stream = data["streams"][0]
    return {
        "width": float(stream["width"]),
        "height": float(stream["height"]),
        "duration": float(data["format"]["duration"]),
    }


def extract_gray_frame(path: Path, second: float, width: int = 180, height: int = 320) -> bytes:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required")
    proc = subprocess.run(
        [
            ffmpeg,
            "-v",
            "error",
            "-ss",
            f"{second:.3f}",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-vf",
            f"scale={width}:{height},format=gray",
            "-f",
            "rawvideo",
            "-",
        ],
        capture_output=True,
        timeout=30,
        check=False,
    )
    if proc.returncode != 0 or len(proc.stdout) != width * height:
        raise RuntimeError("video frame extraction failed")
    return proc.stdout


def visible_bounds(frame: bytes, width: int, height: int, threshold: int = 18) -> dict[str, float]:
    points = [(index % width, index // width) for index, value in enumerate(frame) if value > threshold]
    if not points:
        return {"width_ratio": 0.0, "height_ratio": 0.0, "active_ratio": 0.0}
    xs, ys = zip(*points)
    return {
        "width_ratio": (max(xs) - min(xs) + 1) / width,
        "height_ratio": (max(ys) - min(ys) + 1) / height,
        "active_ratio": len(points) / (width * height),
    }


def analyze_video(
    path: Path,
    min_width_ratio: float = 0.65,
    min_height_ratio: float = 0.55,
    sample_count: int = 9,
) -> dict[str, Any]:
    metadata = probe_video(path)
    duration = metadata["duration"]
    times = [duration * (index + 1) / (sample_count + 1) for index in range(sample_count)]
    frames = [visible_bounds(extract_gray_frame(path, second), 180, 320) for second in times]
    usable = [frame for frame in frames if frame["active_ratio"] >= 0.01]
    if not usable:
        return {"passed": False, "reason": "未检测到有效画面内容", "frames": frames}
    median_width = statistics.median(frame["width_ratio"] for frame in usable)
    median_height = statistics.median(frame["height_ratio"] for frame in usable)
    passed = median_width >= min_width_ratio and median_height >= min_height_ratio
    return {
        "passed": passed,
        "reason": "画面内容占比符合要求" if passed else "主体画面占比过小或存在大面积黑边",
        "median_width_ratio": round(median_width, 4),
        "median_height_ratio": round(median_height, 4),
        "minimum_width_ratio": min_width_ratio,
        "minimum_height_ratio": min_height_ratio,
        "sample_count": len(usable),
        "frames": frames,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--min-width", type=float, default=0.65)
    parser.add_argument("--min-height", type=float, default=0.55)
    parser.add_argument("--samples", type=int, default=9)
    args = parser.parse_args()
    result = analyze_video(args.video, args.min_width, args.min_height, max(3, args.samples))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
