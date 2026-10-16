#!/usr/bin/env python3
"""Inspect the free local toolchain needed by the video workflow."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def command_info(name: str, args: list[str] | None = None) -> dict[str, Any]:
    """Return path and a compact version string for a command."""
    path = shutil.which(name)
    result: dict[str, Any] = {"name": name, "found": bool(path), "path": path, "version": None}
    if not path:
        return result
    try:
        proc = subprocess.run(
            [path, *(args or ["--version"])],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        output = (proc.stdout or proc.stderr).strip().splitlines()
        result["version"] = output[0][:240] if output else None
    except (OSError, subprocess.SubprocessError) as exc:
        result["version_error"] = str(exc)
    return result


def detect_jianying() -> dict[str, Any]:
    """Detect common JianYing/CapCut desktop locations without modifying them."""
    system = platform.system().lower()
    candidates: list[Path] = []
    if system == "darwin":
        candidates = [
            Path("/Applications/剪映专业版.app"),
            Path.home() / "Applications" / "剪映专业版.app",
            Path("/Applications/CapCut.app"),
        ]
    elif system == "windows":
        for env_name in ("LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)"):
            value = os.environ.get(env_name)
            if value:
                base = Path(value)
                candidates.extend([base / "JianyingPro", base / "CapCut"])
    found = next((str(path) for path in candidates if path.exists()), None)
    return {"found": bool(found), "path": found, "checked": [str(path) for path in candidates]}


def inspect_environment() -> dict[str, Any]:
    """Build a machine-readable environment report."""
    commands = {
        "git": command_info("git"),
        "python": command_info(sys.executable, ["--version"]),
        "node": command_info("node"),
        "npm": command_info("npm"),
        "ffmpeg": command_info("ffmpeg", ["-version"]),
        "ffprobe": command_info("ffprobe", ["-version"]),
    }
    required = ("git", "python", "node", "npm", "ffmpeg", "ffprobe")
    missing = [name for name in required if not commands[name]["found"]]
    python_supported = sys.version_info >= (3, 10)
    if not python_supported:
        missing.append("python>=3.10")
    return {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "architecture": platform.machine(),
        "commands": commands,
        "python_supported": python_supported,
        "jianying": detect_jianying(),
        "missing_required": missing,
        "ready": not missing,
        "notes": [
            "剪映桌面端缺失时，AI 可以完成主片，但不能完成剪映草稿。"
            if not detect_jianying()["found"]
            else "已检测到剪映/CapCut 桌面端。"
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when required tools are missing.")
    args = parser.parse_args()
    report = inspect_environment()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"platform={report['platform']} architecture={report['architecture']}")
        for name, item in report["commands"].items():
            print(f"{name}: {'OK' if item['found'] else 'MISSING'} {item.get('version') or ''}".rstrip())
        print(f"jianying: {'OK' if report['jianying']['found'] else 'NOT_FOUND'}")
        print(f"ready={str(report['ready']).lower()}")
    return 2 if args.strict and not report["ready"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

