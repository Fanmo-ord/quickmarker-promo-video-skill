#!/usr/bin/env python3
"""Verify that dependency-owned stages require real Skill execution evidence."""

from __future__ import annotations

import tempfile
from pathlib import Path

from common import atomic_write_json
from run_pipeline import advance_project, state_path


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="quickmarker-dependency-gate-") as temp_dir:
        workspace = Path(temp_dir)
        project_id = "dependency-gate-check"
        project_path = state_path(workspace, project_id)
        project_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(
            project_path,
            {
                "project_id": project_id,
                "stage": "creative_brief",
                "status": "active",
                "approvals": {},
                "artifacts": {},
                "history": [],
            },
        )

        blocked = advance_project(workspace, project_id, None, None)
        if blocked.get("advanced") is not False:
            raise RuntimeError("creative_brief advanced without dependency evidence")

        entrypoint = workspace / "SKILL.md"
        artifact = workspace / "visual-directions.md"
        entrypoint.write_text("dependency entrypoint", encoding="utf-8")
        artifact.write_text("visual directions", encoding="utf-8")
        samples = []
        for index in range(1, 4):
            sample = workspace / f"sample-{index}.png"
            sample.write_bytes(b"sample")
            samples.append(str(sample))

        advanced = advance_project(
            workspace,
            project_id,
            str(artifact),
            "dependency gate check",
            "ai-promo-video-maker",
            str(entrypoint),
            samples,
        )
        if advanced.get("advanced") is not True:
            raise RuntimeError(f"valid dependency evidence was rejected: {advanced}")

    print("dependency execution gate OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
