#!/usr/bin/env python3
"""Shared, dependency-free helpers for the QuickMarker video workflow."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = SKILL_ROOT / "config" / "product.json"


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path, default: Any | None = None) -> Any:
    """Read UTF-8 JSON, optionally returning a default for a missing file."""
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def atomic_write_json(path: Path, data: Any) -> None:
    """Write JSON atomically so interrupted runs do not corrupt state."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file without loading it into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def slugify(value: str, fallback: str = "video") -> str:
    """Create a stable ASCII-ish project slug while retaining CJK text."""
    value = value.strip().lower()
    value = re.sub(r"[^\w\u4e00-\u9fff]+", "-", value, flags=re.UNICODE)
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:48] or fallback


def workspace_layout(workspace: Path) -> dict[str, Path]:
    """Return and create the persistent directory layout for a user workspace."""
    root = workspace.resolve()
    paths = {
        "root": root,
        "management": root / "00-项目管理",
        "product_docs": root / "01-产品资料",
        "library": root / "02-素材库",
        "screenshots": root / "02-素材库" / "01-产品截图",
        "videos": root / "02-素材库" / "02-教学视频",
        "samples": root / "02-素材库" / "03-作文样本",
        "brand": root / "02-素材库" / "05-品牌与导流",
        "incoming": root / "03-内容运营" / "01-素材收集" / "待整理",
        "topic_pool": root / "03-内容运营" / "02-选题池",
        "copywriting": root / "03-内容运营" / "03-文案脚本",
        "generated": root / "03-内容运营" / "04-视觉样帧",
        "publish_packages": root / "03-内容运营" / "05-发布包",
        "state": root / "03-内容运营" / "06-状态记录",
        "projects": root / "03-内容运营" / "06-状态记录" / "projects",
        "promo_projects": root / "04-视频项目" / "01-宣传片工程",
        "drafts": root / "04-视频项目" / "02-剪映草稿",
        "exports": root / "04-视频项目" / "03-成片",
        "automation": root / "05-自动化工具",
        "validation": root / "03-内容运营" / "06-状态记录" / "validation",
        "archive": root / "90-归档",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def load_config() -> dict[str, Any]:
    """Load the versioned product/workflow contract."""
    return load_json(CONFIG_PATH)

