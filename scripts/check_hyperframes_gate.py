#!/usr/bin/env python3
"""Self-check for the Hyperframes-to-Remotion video contract."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import json
from pathlib import Path

from render_hyperframes_motion import validate_video
from run_pipeline import initialize_project_files, motion_plan_errors


def main() -> int:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required")
    with tempfile.TemporaryDirectory(prefix="quickmarker-hyperframes-gate-") as temp_dir:
        root = Path(temp_dir)
        silent = root / "silent.mp4"
        with_audio = root / "with-audio.mp4"
        subprocess.run(
            [ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=blue:s=1080x1920:r=30:d=0.2", "-an", str(silent)],
            capture_output=True,
            check=True,
        )
        result = validate_video(silent, 1080, 1920, 30)
        if result["audio_streams"] != 0:
            raise RuntimeError("silent fixture was not accepted")
        files = initialize_project_files(root, "2026-10-20-hyperframes-test-v1", "Hyperframes test", "douyin")
        motion_plan = Path(files["motion_plan"])
        if not motion_plan.is_file():
            raise RuntimeError("new project did not receive motion-plan.json")
        motion_plan.write_text(
            json.dumps(
                {
                    "engine": "hyperframes",
                    "version": "0.8.174",
                    "integration_mode": "rendered_clips",
                    "clips": [{"id": "hook", "output": str(silent)}],
                }
            ),
            encoding="utf-8",
        )
        if motion_plan_errors(motion_plan):
            raise RuntimeError("valid motion plan was rejected")
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=blue:s=1080x1920:r=30:d=0.2",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=48000:cl=stereo",
                "-shortest",
                str(with_audio),
            ],
            capture_output=True,
            check=True,
        )
        try:
            validate_video(with_audio, 1080, 1920, 30)
        except RuntimeError as exc:
            if "无音轨" not in str(exc):
                raise
        else:
            raise RuntimeError("audio fixture incorrectly passed")
    print("hyperframes motion gate OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
