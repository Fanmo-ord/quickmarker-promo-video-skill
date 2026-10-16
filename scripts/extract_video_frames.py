#!/usr/bin/env python3
"""Extract useful video frames and compare them with an existing image library."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageStat

from common import atomic_write_json, sha256_file, utc_now


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm"}


def dhash(path: Path, size: int = 16) -> int:
    """Return a compact perceptual difference hash."""
    with Image.open(path) as image:
        gray = image.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
        pixels = list(gray.getdata())
    bits = 0
    for row in range(size):
        offset = row * (size + 1)
        for column in range(size):
            bits = (bits << 1) | int(pixels[offset + column] > pixels[offset + column + 1])
    return bits


def distance(left: int, right: int) -> int:
    """Return Hamming distance between two hashes."""
    return (left ^ right).bit_count()


def visual_quality(path: Path) -> dict[str, float]:
    """Estimate entropy, brightness and contrast to reject blank transition frames."""
    with Image.open(path) as image:
        gray = image.convert("L").resize((256, 256), Image.Resampling.BILINEAR)
        stat = ImageStat.Stat(gray)
        return {
            "entropy": round(gray.entropy(), 3),
            "brightness": round(stat.mean[0], 3),
            "contrast": round(stat.stddev[0], 3),
        }


def extract_frames(video: Path, target: Path, interval: float) -> list[Path]:
    """Extract regular JPEG samples with ffmpeg."""
    target.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
        "-vf", f"fps=1/{interval}", "-q:v", "2", str(target / "%06d.jpg"),
    ]
    proc = subprocess.run(command, capture_output=True, text=True, check=False)
    if proc.returncode:
        raise RuntimeError(f"ffmpeg failed for {video.name}: {(proc.stderr or proc.stdout).strip()}")
    return sorted(target.glob("*.jpg"))


def load_library_hashes(library: Path) -> list[tuple[Path, int]]:
    """Hash every readable image in the reference library."""
    result: list[tuple[Path, int]] = []
    for path in sorted(library.rglob("*")):
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
            try:
                result.append((path, dhash(path)))
            except (OSError, ValueError):
                continue
    return result


def nearest_library_match(frame_hash: int, library: list[tuple[Path, int]]) -> tuple[str | None, int | None]:
    """Return the nearest known image and distance."""
    if not library:
        return None, None
    path, score = min(((path, distance(frame_hash, value)) for path, value in library), key=lambda item: item[1])
    return str(path), score


def evenly_limit(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """Keep temporal coverage when more useful frames exist than the requested limit."""
    if len(items) <= limit:
        return items
    indices = {round(index * (len(items) - 1) / (limit - 1)) for index in range(limit)}
    return [items[index] for index in sorted(indices)]


def contact_sheet(items: list[dict[str, Any]], output: Path, columns: int = 4) -> None:
    """Create a review sheet containing thumbnails and source timestamps."""
    if not items:
        return
    thumb_width, thumb_height, label_height = 260, 180, 28
    rows = math.ceil(len(items) / columns)
    sheet = Image.new("RGB", (columns * thumb_width, rows * (thumb_height + label_height)), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, item in enumerate(items):
        row, column = divmod(index, columns)
        x, y = column * thumb_width, row * (thumb_height + label_height)
        with Image.open(item["output_path"]) as source:
            image = source.convert("RGB")
            image.thumbnail((thumb_width, thumb_height), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (thumb_width, thumb_height), "#111827")
            canvas.paste(image, ((thumb_width - image.width) // 2, (thumb_height - image.height) // 2))
        sheet.paste(canvas, (x, y))
        label = f"{index + 1:02d}  {item['timestamp']}  Δlib={item['library_distance']}"
        draw.text((x + 6, y + thumb_height + 7), label, fill="black", font=font)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)


def process_video(
    video: Path,
    library: list[tuple[Path, int]],
    output: Path,
    interval: float,
    library_threshold: int,
    change_threshold: int,
    max_frames: int,
) -> dict[str, Any]:
    """Extract, deduplicate and save candidate frames for one video."""
    with tempfile.TemporaryDirectory(prefix=f"quickmarker-{video.stem}-") as temp:
        raw_frames = extract_frames(video, Path(temp), interval)
        candidates: list[dict[str, Any]] = []
        previous_hash: int | None = None
        for index, frame in enumerate(raw_frames):
            frame_hash = dhash(frame)
            quality = visual_quality(frame)
            timestamp_seconds = index * interval
            library_match, library_distance = nearest_library_match(frame_hash, library)
            if quality["entropy"] < 2.5 or quality["contrast"] < 12:
                continue
            if library_distance is not None and library_distance <= library_threshold:
                continue
            if previous_hash is not None and distance(frame_hash, previous_hash) < change_threshold:
                continue
            previous_hash = frame_hash
            candidates.append(
                {
                    "raw_path": str(frame),
                    "hash": str(frame_hash),
                    "timestamp_seconds": timestamp_seconds,
                    "timestamp": f"{int(timestamp_seconds // 60):02d}m{int(timestamp_seconds % 60):02d}s",
                    "library_match": library_match,
                    "library_distance": library_distance,
                    "quality": quality,
                }
            )
        selected = evenly_limit(candidates, max_frames)
        video_output = output / video.stem
        video_output.mkdir(parents=True, exist_ok=True)
        for sequence, item in enumerate(selected, start=1):
            filename = f"{date.today().isoformat()}_教学视频_{video.stem}_{item['timestamp']}_候选画面_v001.jpg"
            destination = video_output / filename
            shutil.copy2(item.pop("raw_path"), destination)
            item.update(sequence=sequence, output_path=str(destination), sha256=sha256_file(destination))
        sheet = output / f"{video.stem}_候选抽帧联系表.jpg"
        contact_sheet(selected, sheet)
        return {
            "video": str(video),
            "sampled": len(raw_frames),
            "change_candidates": len(candidates),
            "selected": selected,
            "contact_sheet": str(sheet) if selected else None,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--videos-dir", required=True)
    parser.add_argument("--library-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--library-threshold", type=int, default=10)
    parser.add_argument("--change-threshold", type=int, default=14)
    parser.add_argument("--max-per-video", type=int, default=20)
    args = parser.parse_args()
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is required")
    videos_dir, library_dir, output_dir = Path(args.videos_dir), Path(args.library_dir), Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    videos = [path for path in sorted(videos_dir.iterdir()) if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES]
    if not videos:
        raise SystemExit(f"No videos found in {videos_dir}")
    library = load_library_hashes(library_dir)
    reports = [
        process_video(
            video, library, output_dir, args.interval, args.library_threshold,
            args.change_threshold, args.max_per_video,
        )
        for video in videos
    ]
    report = {
        "generated_at": utc_now(),
        "videos_dir": str(videos_dir.resolve()),
        "library_dir": str(library_dir.resolve()),
        "library_image_count": len(library),
        "parameters": {
            "interval": args.interval,
            "library_threshold": args.library_threshold,
            "change_threshold": args.change_threshold,
            "max_per_video": args.max_per_video,
        },
        "videos": reports,
    }
    report_path = output_dir / "抽帧对比报告.json"
    atomic_write_json(report_path, report)
    print(json.dumps({"report": str(report_path), "videos": len(reports), "selected": sum(len(item["selected"]) for item in reports)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

