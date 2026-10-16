#!/usr/bin/env python3
"""Install this repository into native and universal Agent Skill locations."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from common import SKILL_ROOT


SKILL_NAME = "quickmarker-promo-video-skill"


def detected_targets(platform_name: str) -> list[Path]:
    """Return requested platform path plus the universal path."""
    home = Path.home()
    universal = home / ".agents" / "skills" / SKILL_NAME
    mapping = {
        "codex": home / ".codex" / "skills" / SKILL_NAME,
        "claude": home / ".claude" / "skills" / SKILL_NAME,
        "copilot": home / ".copilot" / "skills" / SKILL_NAME,
        "gemini": home / ".gemini" / "skills" / SKILL_NAME,
        "cline": home / ".cline" / "skills" / SKILL_NAME,
        "roo-code": home / ".roo" / "skills" / SKILL_NAME,
        "goose": home / ".config" / "goose" / "skills" / SKILL_NAME,
        "opencode": home / ".config" / "opencode" / "skills" / SKILL_NAME,
    }
    if platform_name != "auto":
        if platform_name not in mapping and platform_name != "universal":
            raise ValueError(f"Unsupported platform: {platform_name}")
        return [universal] if platform_name == "universal" else [universal, mapping[platform_name]]
    targets = [universal]
    markers = {
        "codex": home / ".codex",
        "claude": home / ".claude",
        "copilot": home / ".copilot",
        "gemini": home / ".gemini",
        "cline": home / ".cline",
        "roo-code": home / ".roo",
        "goose": home / ".config" / "goose",
        "opencode": home / ".config" / "opencode",
    }
    for name, marker in markers.items():
        if marker.exists():
            targets.append(mapping[name])
    return list(dict.fromkeys(targets))


def install(target: Path, force: bool) -> str:
    """Copy the skill without runtime outputs; refuse accidental overwrite by default."""
    if target.resolve() == SKILL_ROOT.resolve():
        return f"already-installed:{target}"
    if target.exists():
        if not force:
            return f"skipped-existing:{target}"
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        SKILL_ROOT,
        target,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".DS_Store", "node_modules", ".quickmarker-runtime"),
    )
    return f"installed:{target}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", default="auto", help="auto, codex, claude, copilot, gemini, cline, roo-code, goose, opencode, universal")
    parser.add_argument("--force", action="store_true", help="Replace an existing installed copy.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    targets = detected_targets(args.platform)
    if args.dry_run:
        for target in targets:
            print(f"would-install:{target}")
    else:
        for target in targets:
            print(install(target, args.force))
        print("next:/quickmarker-promo-video-skill 做今天的英语批改助手宣传视频")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

