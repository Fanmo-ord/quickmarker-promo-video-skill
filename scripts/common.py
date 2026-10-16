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
    base = root / "quickmarker-video-workspace"
    paths = {
        "root": base,
        "incoming": base / "素材库" / "incoming",
        "library": base / "素材库" / "product-library",
        "generated": base / "generated",
        "drafts": base / "drafts",
        "exports": base / "exports",
        "state": base / "state",
        "projects": base / "state" / "projects",
        "validation": base / "validation",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def load_config() -> dict[str, Any]:
    """Load the versioned product/workflow contract."""
    return load_json(CONFIG_PATH)

