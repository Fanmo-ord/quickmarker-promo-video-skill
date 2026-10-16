#!/usr/bin/env python3
"""Validate a final MP4 and its delivery manifest with explicit manual checks."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from common import atomic_write_json, load_config, load_json, utc_now


def probe_video(path: Path) -> dict[str, Any]:
    """Read duration, dimensions and audio streams with ffprobe."""
    if not shutil.which("ffprobe"):
        return {"passed": False, "error": "ffprobe not found"}
    proc = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-show_entries", "stream=index,codec_type,width,height", "-of", "json", str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return {"passed": False, "error": proc.stderr.strip()}
    data = json.loads(proc.stdout)
    video_stream = next((item for item in data.get("streams", []) if item.get("codec_type") == "video"), {})
    audio_streams = [item for item in data.get("streams", []) if item.get("codec_type") == "audio"]
    width, height = video_stream.get("width"), video_stream.get("height")
    return {
        "passed": bool(width and height),
        "duration_seconds": float(data.get("format", {}).get("duration", 0)),
        "width": width,
        "height": height,
        "is_vertical": bool(width and height and height > width),
        "audio_stream_count": len(audio_streams),
    }


def validate_manifest(manifest: dict[str, Any], draft_only: bool = False) -> list[str]:
    """Return contract violations that cannot be waived silently."""
    config = load_config()
    errors: list[str] = []
    qr = manifest.get("qr_outro", {})
    if not qr.get("included_in_main_film"):
        errors.append("二维码未在主片生成阶段加入")
    if float(qr.get("duration_seconds", 0)) < float(config["qr_outro"]["minimum_duration_seconds"]):
        errors.append("二维码片尾不足 5 秒")
    if not qr.get("verified_scan"):
        errors.append("二维码尚未验证可扫描")
    subtitles = manifest.get("subtitles", {})
    if subtitles.get("position") != "bottom" or not subtitles.get("single_layer"):
        errors.append("字幕必须为单层底部字幕")
    if subtitles.get("main_canvas_scaled"):
        errors.append("主画面因字幕被缩小")
    audio = manifest.get("audio", {})
    if not audio.get("narration_present") or not audio.get("bgm_ducked"):
        errors.append("旁白或混音验收未完成")
    if not manifest.get("cover", {}).get("approved"):
        errors.append("封面尚未获用户确认")
    if not manifest.get("privacy_review", {}).get("passed"):
        errors.append("隐私检查未通过")
    if not manifest.get("copyright_review", {}).get("passed"):
        errors.append("素材版权检查未通过")
    if draft_only and not manifest.get("draft_path"):
        errors.append("macOS 草稿路径缺失")
    return errors


def validate(path: Path, draft_only: bool = False) -> dict[str, Any]:
    manifest = load_json(path)
    errors = validate_manifest(manifest, draft_only=draft_only)
    video_probe: dict[str, Any] | None = None
    video_value = manifest.get("video_path")
    if not draft_only:
        if not video_value:
            errors.append("最终视频路径缺失")
        else:
            video_path = Path(video_value).expanduser()
            if not video_path.is_file():
                errors.append(f"最终视频不存在：{video_path}")
            else:
                video_probe = probe_video(video_path)
                if not video_probe.get("passed"):
                    errors.append(f"视频探测失败：{video_probe.get('error', 'unknown')}")
                elif not video_probe.get("is_vertical"):
                    errors.append("最终视频不是竖屏")
                if video_probe and video_probe.get("audio_stream_count", 0) < 1:
                    errors.append("最终视频没有音轨")
    manual_checks = [
        "无黑帧、无离线素材、无错误裁切",
        "旁白与字幕同步，BGM 不压旁白",
        "字幕只在底部且未缩小主画面",
        "封面标题位于安全区且清晰可读",
        "二维码片尾完整、无遮挡、实际扫码成功",
    ]
    result = {
        "checked_at": utc_now(),
        "passed": not errors,
        "errors": errors,
        "video_probe": video_probe,
        "manual_checks": manual_checks,
        "mode": "draft" if draft_only else "final",
    }
    manifest["validation"] = result
    atomic_write_json(path, manifest)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--draft-only", action="store_true", help="Validate a macOS draft before manual MP4 export.")
    args = parser.parse_args()
    result = validate(Path(args.manifest), draft_only=args.draft_only)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 6


if __name__ == "__main__":
    raise SystemExit(main())

