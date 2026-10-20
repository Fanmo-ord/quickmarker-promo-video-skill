#!/usr/bin/env python3
"""Render and validate a Hyperframes motion clip for the Remotion master film."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Any


DEFAULT_VERSION = "0.8.174"


def _run(command: list[str], *, cwd: Path | None = None, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _node_major() -> int:
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Hyperframes 需要 Node.js 22+，但未找到 node")
    result = _run([node, "--version"], timeout=10)
    if result.returncode != 0:
        raise RuntimeError("无法读取 Node.js 版本")
    try:
        return int(result.stdout.strip().lstrip("v").split(".", 1)[0])
    except ValueError as exc:
        raise RuntimeError(f"无法解析 Node.js 版本：{result.stdout.strip()}") from exc


def _probe_video(path: Path) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("未找到 ffprobe，无法校验动效片段")
    result = _run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe 校验失败：{result.stderr.strip()}")
    return json.loads(result.stdout)


def validate_video(path: Path, width: int, height: int, fps: float) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"动效片段不存在或为空：{path}")
    probe = _probe_video(path)
    streams = probe.get("streams", [])
    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    if len(video_streams) != 1:
        raise RuntimeError("动效片段必须且只能包含一个视频轨")
    if audio_streams:
        raise RuntimeError("Hyperframes 动效片段必须无音轨，声音统一留给剪映阶段")
    video = video_streams[0]
    actual_size = (int(video.get("width", 0)), int(video.get("height", 0)))
    if actual_size != (width, height):
        raise RuntimeError(f"动效片段尺寸必须是 {width}×{height}，实际为 {actual_size[0]}×{actual_size[1]}")
    rate_text = video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1"
    actual_fps = float(Fraction(rate_text))
    if abs(actual_fps - fps) > 0.01:
        raise RuntimeError(f"动效片段帧率必须是 {fps:g}fps，实际为 {actual_fps:g}fps")
    duration = float(video.get("duration") or probe.get("format", {}).get("duration") or 0)
    if duration <= 0:
        raise RuntimeError("动效片段时长无效")
    return {
        "width": actual_size[0],
        "height": actual_size[1],
        "fps": actual_fps,
        "duration_seconds": duration,
        "audio_streams": 0,
        "codec": video.get("codec_name"),
    }


def render_project(project: Path, output: Path, version: str) -> None:
    if _node_major() < 22:
        raise RuntimeError("Hyperframes 需要 Node.js 22+")
    if not shutil.which("npx"):
        raise RuntimeError("未找到 npx，无法运行 Hyperframes")
    if not (project / "hyperframes.json").is_file() or not (project / "index.html").is_file():
        raise RuntimeError("Hyperframes 项目必须包含 hyperframes.json 和 index.html")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "npx",
        "--yes",
        f"--package=hyperframes@{version}",
        "--",
        "hyperframes",
        "render",
        ".",
        "--skill=motion-graphics",
        "-q",
        "high",
        "-o",
        str(output.resolve()),
    ]
    result = _run(command, cwd=project, timeout=900)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()[-12:]
        raise RuntimeError("Hyperframes 渲染失败：\n" + "\n".join(detail))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, help="Hyperframes 项目目录；校验已有视频时可省略")
    parser.add_argument("--output", type=Path, required=True, help="输出或待校验的 MP4")
    parser.add_argument("--version", default=DEFAULT_VERSION)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--fps", type=float, default=30)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--json", action="store_true", help="输出机器可读结果")
    args = parser.parse_args()

    try:
        output = args.output.expanduser().resolve()
        if not args.validate_only:
            if not args.project:
                raise RuntimeError("渲染时必须提供 --project")
            render_project(args.project.expanduser().resolve(), output, args.version)
        video = validate_video(output, args.width, args.height, args.fps)
        report = {
            "passed": True,
            "engine": "hyperframes",
            "version": args.version,
            "integration_mode": "rendered_clips",
            "output": str(output),
            "video": video,
        }
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        report = {"passed": False, "error": str(exc)}

    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else ("PASS" if report["passed"] else f"FAIL: {report['error']}"))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
