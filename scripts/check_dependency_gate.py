#!/usr/bin/env python3
"""Verify that dependency-owned stages require real Skill execution evidence."""

from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from bootstrap import bootstrap
from common import atomic_write_json, load_json, workspace_layout
from manage_topic_pool import suggest_topics
from run_pipeline import advance_project, artifact_errors, new_project, project_contract_errors, state_path


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="quickmarker-dependency-gate-") as temp_dir:
        workspace = Path(temp_dir)

        bootstrap(workspace, install=False)
        selection = suggest_topics(workspace, count=3)
        options = selection.get("suggestions", [])
        if len(options) != 3 or selection.get("generation_needed") != 0:
            raise RuntimeError(f"topic selection did not return three options: {selection}")
        directions = {(item["title"], item["angle"], item["selling_point"]) for item in options}
        if len(directions) != 3:
            raise RuntimeError("topic selection returned duplicate directions")

        created = new_project(
            workspace,
            "批改后自动生成班级学情",
            "从逐份统计到一眼定位共性错题",
            "批次成绩统计与错题分析",
            "douyin",
        )
        if not created.get("created"):
            raise RuntimeError(f"new project was not created: {created}")
        files = created["project"].get("files", {})
        for key in ("creative_brief", "storyboard", "delivery_manifest", "narration"):
            path = Path(files.get(key, ""))
            if not path.is_file():
                raise RuntimeError(f"new project did not seed {key}: {path}")

        narration_path = Path(files["narration"])
        narration_path.write_text("拍照上传作业，英语批改助手自动完成批改。", encoding="utf-8")
        jianying_script = Path(files["jianying_script"])
        jianying_script.write_text(
            "from pathlib import Path\n"
            "text = Path('narration.txt').read_text(encoding='utf-8')\n"
            "project.add_narrated_subtitles(text, speaker='zh_female_xiaopengyou')\n",
            encoding="utf-8",
        )
        if project_contract_errors("jianying_post", created["project"]):
            raise RuntimeError("valid narrated-subtitle contract was rejected")
        jianying_script.write_text(
            "project.add_tts_intelligent('voice')\nproject.import_srt('subtitle.srt')\n",
            encoding="utf-8",
        )
        if not project_contract_errors("jianying_post", created["project"]):
            raise RuntimeError("separate narration and subtitle generation passed the contract gate")
        jianying_script.write_text(
            "from pathlib import Path\n"
            "text = Path('narration.txt').read_text(encoding='utf-8')\n"
            "project.add_narrated_subtitles(text, speaker='zh_female_xiaopengyou')\n",
            encoding="utf-8",
        )

        contracts = created["project"].get("contracts", {})
        if contracts.get("main_film_audio_mode") != "silent":
            raise RuntimeError("main film must use the silent handoff contract")
        if contracts.get("narration_engine") != "jianying-editor-skill":
            raise RuntimeError("narration must be owned by jianying-editor-skill")
        if contracts.get("narration_selection") != "automatic_recommended":
            raise RuntimeError("Jianying narration must use automatic recommended settings")

        fake_main_film = workspace / "main-film.mp4"
        fake_main_film.write_bytes(b"mp4")
        with patch("run_pipeline.shutil.which", return_value="/usr/bin/ffprobe"), patch(
            "run_pipeline.subprocess.run",
            return_value=SimpleNamespace(returncode=0, stdout="0\n", stderr=""),
        ), patch(
            "run_pipeline.analyze_video",
            return_value={"passed": True},
        ):
            if not artifact_errors("promo_render_with_qr", fake_main_film):
                raise RuntimeError("main film with an audio stream passed the silent handoff gate")
        with patch("run_pipeline.shutil.which", return_value="/usr/bin/ffprobe"), patch(
            "run_pipeline.subprocess.run",
            return_value=SimpleNamespace(returncode=0, stdout="", stderr=""),
        ), patch(
            "run_pipeline.analyze_video",
            return_value={"passed": True},
        ):
            if artifact_errors("promo_render_with_qr", fake_main_film):
                raise RuntimeError("silent main film was rejected by the handoff gate")
        with patch("run_pipeline.shutil.which", return_value="/usr/bin/ffprobe"), patch(
            "run_pipeline.subprocess.run",
            return_value=SimpleNamespace(returncode=0, stdout="", stderr=""),
        ), patch(
            "run_pipeline.analyze_video",
            return_value={"passed": False, "median_width_ratio": 0.31, "median_height_ratio": 0.42},
        ):
            if not artifact_errors("promo_render_with_qr", fake_main_film):
                raise RuntimeError("undersized main visual passed the coverage gate")

        created_state_path = Path(created["state_path"])
        created_state = load_json(created_state_path)
        export_path = Path(files["video"])
        export_path.write_bytes(b"mp4")
        created_state["stage"] = "delivery_handoff"
        created_state["artifacts"]["export"] = {"path": str(export_path)}
        atomic_write_json(created_state_path, created_state)
        manifest_path = Path(files["delivery_manifest"])
        manifest = load_json(manifest_path)
        manifest["audio"]["narration_subtitle_sync_method"] = "add_narrated_subtitles"
        manifest["audio"]["narration_subtitle_sync_verified"] = True
        atomic_write_json(manifest_path, manifest)
        completed = advance_project(
            workspace,
            created_state["project_id"],
            files["delivery_manifest"],
            "delivery handoff ready for manual review",
        )
        if completed.get("project", {}).get("status") != "complete":
            raise RuntimeError(f"delivery handoff did not complete project: {completed}")
        topic_pool = load_json(workspace_layout(workspace)["state"] / "topic-pool.json")
        completed_topic = next(
            (item for item in topic_pool["topics"] if item["id"] == created_state["topic_id"]),
            None,
        )
        if not completed_topic or completed_topic.get("status") != "complete":
            raise RuntimeError("completed project did not close its topic-pool record")

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

        draft_project_id = "jianying-artifact-check"
        draft_project_path = state_path(workspace, draft_project_id)
        atomic_write_json(
            draft_project_path,
            {
                "project_id": draft_project_id,
                "stage": "jianying_post",
                "status": "active",
                "approvals": {},
                "artifacts": {},
                "history": [],
            },
        )
        fake_video = workspace / "not-a-jianying-draft.mp4"
        fake_video.write_bytes(b"mp4")
        rejected = advance_project(
            workspace,
            draft_project_id,
            str(fake_video),
            "must reject mp4 as a Jianying draft",
            "jianying-editor-skill",
            str(entrypoint),
        )
        if rejected.get("advanced") is not False:
            raise RuntimeError("jianying_post accepted an MP4 instead of an editable draft")

        print("dependency execution gate OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
