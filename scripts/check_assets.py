#!/usr/bin/env python3
"""Seed, inventory, and safety-check the QuickMarker product asset library."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any

from common import SKILL_ROOT, atomic_write_json, sha256_file, utc_now, workspace_layout


ASSET_SOURCE = SKILL_ROOT / "assets"
MEDIA_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".m4v", ".wav", ".mp3", ".m4a"}
SENSITIVE_PATTERNS = {
    "mobile_phone": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "id_card": re.compile(r"(?<!\d)\d{17}[0-9Xx](?!\d)"),
}


def seed_assets(paths: dict[str, Path]) -> list[str]:
    """Copy bundled reference assets without overwriting user changes."""
    copied: list[str] = []
    destinations = {
        "screenshots": paths["screenshots"],
        "videos": paths["videos"],
        "brand": paths["brand"],
        "knowledge": paths["product_docs"] / "01-产品定位",
        "examples": paths["exports"] / "参考成片",
    }
    for category in ("screenshots", "videos", "brand", "knowledge", "examples"):
        source_dir = ASSET_SOURCE / category
        target_dir = destinations[category]
        target_dir.mkdir(parents=True, exist_ok=True)
        if not source_dir.exists():
            continue
        for source in source_dir.rglob("*"):
            if not source.is_file():
                continue
            relative = source.relative_to(source_dir)
            target = target_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                shutil.copy2(source, target)
                copied.append(str(target))
    return copied


def scan_text(path: Path) -> list[str]:
    """Flag obvious personal identifiers in readable text files."""
    if path.suffix.lower() not in {".md", ".txt", ".json", ".csv", ".srt"}:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ["unreadable"]
    return [name for name, pattern in SENSITIVE_PATTERNS.items() if pattern.search(text)]


def inventory(workspace: Path, seed: bool = False) -> dict[str, Any]:
    """Return a manifest with hashes and explicit visual privacy review flags."""
    paths = workspace_layout(workspace)
    copied = seed_assets(paths) if seed else []
    roots = [paths["library"], paths["incoming"], paths["product_docs"]]
    files: list[dict[str, Any]] = []
    sensitive: list[dict[str, Any]] = []
    for root in roots:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.name.startswith("."):
                continue
            flags = scan_text(path)
            item = {
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "kind": "media" if path.suffix.lower() in MEDIA_SUFFIXES else "document",
                "text_sensitive_flags": flags,
                "visual_privacy_review_required": path.suffix.lower() in MEDIA_SUFFIXES,
            }
            files.append(item)
            if flags:
                sensitive.append(item)
    qr_files = [item for item in files if "二维码" in Path(item["path"]).name or "qr" in Path(item["path"]).stem.lower()]
    report = {
        "generated_at": utc_now(),
        "workspace": str(workspace.resolve()),
        "copied": copied,
        "file_count": len(files),
        "files": files,
        "qr_assets": qr_files,
        "text_sensitive_findings": sensitive,
        "visual_privacy_review_required": any(item["visual_privacy_review_required"] for item in files),
        "ready": bool(files) and bool(qr_files) and not sensitive,
        "notice": "图片和视频必须由 AI 逐帧/逐图检查真实姓名、成绩、学校等信息；本脚本不能仅凭文件名判定安全。",
    }
    manifest_path = paths["state"] / "asset-manifest.json"
    atomic_write_json(manifest_path, report)
    report["manifest_path"] = str(manifest_path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--seed", action="store_true", help="Copy bundled assets into the workspace library.")
    args = parser.parse_args()
    report = inventory(Path(args.workspace), seed=args.seed)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 4


if __name__ == "__main__":
    raise SystemExit(main())

