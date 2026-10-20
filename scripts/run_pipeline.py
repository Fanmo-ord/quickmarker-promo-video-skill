#!/usr/bin/env python3
"""Single stateful entry point for the interactive QuickMarker video pipeline."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import unicodedata
from pathlib import Path
from typing import Any

from bootstrap import bootstrap
from check_assets import inventory
from check_visual_coverage import analyze_video
from common import atomic_write_json, load_config, load_json, slugify, utc_now, workspace_layout
from manage_topic_pool import add_topic, complete_topic, initialize as initialize_topic_pool, suggest_topics
from render_hyperframes_motion import validate_video as validate_motion_video


TEMPLATE_ROOT = Path(__file__).resolve().parent.parent / "assets" / "templates"


STAGES = (
    "topic",
    "script",
    "creative_brief",
    "creative_approval",
    "promo_render_with_qr",
    "qr_validation",
    "jianying_post",
    "cover_approval",
    "export",
    "delivery_handoff",
    "complete",
)

REQUIRED_APPROVALS = {
    "creative_approval": ("visual_sample", "audio_direction"),
    "cover_approval": ("cover",),
}

REQUIRED_EXECUTOR_SKILLS = {
    "creative_brief": "ai-promo-video-maker",
    "promo_render_with_qr": "ai-promo-video-maker",
    "jianying_post": "jianying-editor-skill",
}

NEXT_ACTIONS = {
    "topic": "读取选题池并提出具有明显差异的选题、角度和卖点。",
    "script": "撰写短视频脚本、镜头表、平台标题和发布文案；把最终口播按自然停顿切成短句，每个非空行一条，写入 files.narration。",
    "creative_brief": "加载并实际执行 ai-promo-video-maker，按无旁白、无新增运营文字模式生成 3 套差异化视觉方向；画面只组合背景、装饰视觉、真实产品截图和二维码；在 files.motion_plan 中为每套方向规划最多 3 个 Hyperframes 标志性动效，并各生成 3–5 秒动效预览；推荐免费可商用 BGM 与画面节奏，跳过 ElevenLabs 和旁白相关询问。",
    "creative_approval": "向用户展示 3 套视觉样帧、对应动效预览和 BGM 推荐，等待 visual_sample 与 audio_direction 两项确认。",
    "promo_render_with_qr": "继续执行 ai-promo-video-maker；用 scripts/render_hyperframes_motion.py 把已批准的 Hyperframes 动效渲染成 1080×1920、30fps、无音轨 MP4，由 Remotion 按时间轴合成无音轨、无新增运营文字的视觉主片，并加入至少 5 秒静止、可扫描的二维码片尾；把源码入口和抽帧证据登记到 files.visual_master_contract。",
    "qr_validation": "截取主片片尾画面，验证二维码完整、无遮挡且可扫描，通过后进入剪映后期。",
    "jianying_post": "加载并实际执行 jianying-editor-skill，在 files.jianying_script 创建 1080×1920 项目并铺满主视频轨；从 files.narration 读取全文，调用 add_narrated_subtitles 同步生成旁白与底部字幕，把实际逐句文本、TTS 素材和起止时间写入 files.narration_cues，再加入 BGM 和封面。",
    "cover_approval": "展示剪映生成的封面，等待用户确认或给出一次修改意见。",
    "export": "Windows 自动导出并返回文件位置；macOS 打开草稿并请用户手动点击导出。",
    "delivery_handoff": "生成 delivery-manifest.json，标记待人工验收，并进入用户发布确认阶段。",
    "complete": "汇总成片、封面、脚本、发布文案和交付清单，并等待用户人工验收和发布决定。",
}


def state_path(workspace: Path, project_id: str) -> Path:
    return workspace_layout(workspace)["projects"] / f"{project_id}.json"


def latest_project(workspace: Path) -> dict[str, Any] | None:
    paths = sorted(workspace_layout(workspace)["projects"].glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    return load_json(paths[0]) if paths else None


def initialize_project_files(workspace: Path, project_id: str, title: str, platform_name: str) -> dict[str, str]:
    """Create canonical project paths and seed machine-readable templates."""
    paths = workspace_layout(workspace)
    date = project_id[:10]
    topic = slugify(title)
    stem = f"{date}_英语批改助手_{{kind}}_{topic}_{platform_name}_9x16_v001"
    project_dir = paths["promo_projects"] / project_id
    export_dir = paths["exports"] / project_id
    sample_dir = paths["generated"] / project_id
    publish_dir = paths["publish_packages"] / project_id
    for directory in (project_dir, export_dir, sample_dir, publish_dir, project_dir / "tmp"):
        directory.mkdir(parents=True, exist_ok=True)

    files = {
        "script": paths["copywriting"] / f"{stem.format(kind='脚本')}.md",
        "narration": paths["copywriting"] / f"{stem.format(kind='旁白')}.txt",
        "narration_cues": project_dir / "narration-cues.json",
        "creative_brief": paths["copywriting"] / f"{stem.format(kind='创意方案')}.md",
        "storyboard": project_dir / "storyboard.json",
        "motion_plan": project_dir / "motion-plan.json",
        "visual_master_contract": project_dir / "visual-master-contract.json",
        "sample_dir": sample_dir,
        "project_dir": project_dir,
        "draft_dir": paths["drafts"] / project_id,
        "export_dir": export_dir,
        "video": export_dir / f"{stem.format(kind='成片')}.mp4",
        "cover": export_dir / f"{stem.format(kind='封面')}.png",
        "delivery_manifest": export_dir / "delivery-manifest.json",
        "publish_package": publish_dir,
        "tmp": project_dir / "tmp",
        "jianying_script": project_dir / "build_jianying_post.py",
    }

    shutil.copy2(TEMPLATE_ROOT / "creative-brief.md", files["creative_brief"])
    files["narration"].touch()
    narration_cues = load_json(TEMPLATE_ROOT / "narration-cues.json")
    narration_cues["narration_file"] = str(files["narration"])
    atomic_write_json(files["narration_cues"], narration_cues)
    storyboard = load_json(TEMPLATE_ROOT / "storyboard.json")
    storyboard["project_id"] = project_id
    atomic_write_json(files["storyboard"], storyboard)

    motion_plan = load_json(TEMPLATE_ROOT / "motion-plan.json")
    atomic_write_json(files["motion_plan"], motion_plan)
    visual_master_contract = load_json(TEMPLATE_ROOT / "visual-master-contract.json")
    atomic_write_json(files["visual_master_contract"], visual_master_contract)
    manifest = load_json(TEMPLATE_ROOT / "delivery-manifest.json")
    manifest.update(project_id=project_id, platform=platform_name)
    manifest["video_path"] = str(files["video"])
    manifest["cover"]["path"] = str(files["cover"])
    atomic_write_json(files["delivery_manifest"], manifest)
    return {name: str(path) for name, path in files.items()}


def artifact_errors(stage: str, artifact_path: Path | None) -> list[str]:
    """Validate the artifact contract for stages where a file type matters."""
    required = {
        "script": "markdown",
        "creative_brief": "markdown",
        "promo_render_with_qr": "video",
        "jianying_post": "draft",
        "cover_approval": "image",
        "export": "video",
        "delivery_handoff": "manifest",
    }
    kind = required.get(stage)
    if not kind:
        return []
    if not artifact_path or not artifact_path.exists():
        return [f"{stage} 阶段必须提供实际存在的 {kind} 产物"]
    if kind == "markdown" and (not artifact_path.is_file() or artifact_path.suffix.lower() != ".md"):
        return [f"{stage} 产物必须是 Markdown 文件"]
    if kind == "video" and (not artifact_path.is_file() or artifact_path.suffix.lower() != ".mp4"):
        return [f"{stage} 产物必须是 MP4 文件"]
    if stage == "promo_render_with_qr":
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            return ["主片音轨校验需要 ffprobe"]
        try:
            probe = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-select_streams",
                    "a",
                    "-show_entries",
                    "stream=index",
                    "-of",
                    "csv=p=0",
                    str(artifact_path),
                ],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return ["无法完成主片音轨校验"]
        if probe.returncode != 0:
            return ["主片文件无法通过 ffprobe 校验"]
        if probe.stdout.strip():
            return ["ai-promo-video-maker 主片必须保持无音轨，旁白与混音由剪映阶段完成"]
        coverage = load_config()["visual_coverage"]
        try:
            coverage_result = analyze_video(
                artifact_path,
                min_width_ratio=coverage["minimum_width_ratio"],
                min_height_ratio=coverage["minimum_height_ratio"],
                sample_count=coverage["sample_count"],
            )
        except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError):
            return ["无法完成主片画面占比校验"]
        if not coverage_result["passed"]:
            return [
                "主片主体画面占比过小："
                f"宽度中位数 {coverage_result.get('median_width_ratio', 0):.0%}，"
                f"高度中位数 {coverage_result.get('median_height_ratio', 0):.0%}"
            ]
    if kind == "image" and (not artifact_path.is_file() or artifact_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}):
        return ["封面产物必须是图片文件"]
    if kind == "draft":
        has_timeline = artifact_path.is_dir() and (
            (artifact_path / "draft_info.json").is_file()
            or any((artifact_path / "Timelines").glob("*/draft_info.json"))
        )
        if not has_timeline:
            return ["jianying_post 产物必须是包含 draft_info.json 的可编辑剪映草稿目录"]
    if kind == "manifest":
        try:
            manifest = load_json(artifact_path)
        except (OSError, json.JSONDecodeError):
            return ["delivery-manifest.json 必须是有效 JSON"]
        required_keys = {"project_id", "draft_path", "video_path", "cover", "qr_outro", "visual_master", "subtitles", "audio", "review", "publish_approved"}
        missing = sorted(required_keys - set(manifest))
        if missing:
            return [f"delivery-manifest.json 缺少字段：{', '.join(missing)}"]
        if manifest.get("review", {}).get("status") != "pending_manual_review":
            return ["交付清单必须标记 pending_manual_review，由用户人工验收"]
        visual_master = manifest.get("visual_master", {})
        if (
            visual_master.get("mode") != "text_free_visual_master"
            or visual_master.get("product_ui_text_allowed") is not True
            or visual_master.get("added_copy_layers") is not False
            or visual_master.get("verification_passed") is not True
            or not visual_master.get("proof_frames")
        ):
            return ["交付清单必须记录无新增运营文字视觉主片及其验证帧"]
        audio = manifest.get("audio", {})
        if audio.get("narration_subtitle_sync_method") != "add_narrated_subtitles":
            return ["交付清单必须记录剪映旁白字幕同步方法 add_narrated_subtitles"]
        if audio.get("narration_subtitle_sync_verified") is not True:
            return ["交付清单必须记录旁白字幕同步校验已通过"]
        subtitles = manifest.get("subtitles", {})
        subtitle_checks = {
            "source": "jianying_add_narrated_subtitles",
            "position": "bottom",
            "single_layer": True,
            "one_cue_per_utterance": True,
            "timing_from_tts_segments": True,
            "main_canvas_scaled": False,
            "overlap_check_passed": True,
        }
        if any(subtitles.get(key) != value for key, value in subtitle_checks.items()):
            return ["交付清单必须记录逐句字幕、真实 TTS 时间轴、底部安全区和重叠校验已通过"]
        if not subtitles.get("cues_path") or not subtitles.get("proof_frames"):
            return ["交付清单必须登记逐句时间轴文件和字幕验证帧"]
    return []


def motion_plan_errors(path: Path) -> list[str]:
    """Require validated Hyperframes clips before the Remotion master render."""
    if not path.is_file():
        return ["缺少 motion-plan.json"]
    try:
        plan = load_json(path)
    except (OSError, json.JSONDecodeError):
        return ["motion-plan.json 必须是有效 JSON"]
    if plan.get("engine") != "hyperframes" or plan.get("integration_mode") != "rendered_clips":
        return ["动效方案必须使用 Hyperframes rendered_clips 接入模式"]
    expected_version = load_config()["tools"]["hyperframes_package"].rsplit("@", 1)[-1]
    if plan.get("version") != expected_version:
        return [f"Hyperframes 动效版本必须锁定为 {expected_version}"]
    clips = plan.get("clips")
    if not isinstance(clips, list) or not 1 <= len(clips) <= 3:
        return ["动效方案必须包含 1 至 3 个已批准片段"]
    errors: list[str] = []
    for index, clip in enumerate(clips, start=1):
        output_value = clip.get("output") if isinstance(clip, dict) else None
        output = Path(output_value).expanduser() if output_value else None
        if output and not output.is_absolute():
            output = path.parent / output
        if not output:
            errors.append(f"第 {index} 个动效片段缺少 output")
            continue
        try:
            validate_motion_video(output, 1080, 1920, 30)
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"第 {index} 个动效片段未通过校验：{exc}")
    return errors


def contract_evidence_path(contract_path: Path, value: str) -> Path:
    evidence_path = Path(value)
    return evidence_path if evidence_path.is_absolute() else contract_path.parent / evidence_path


def visual_master_contract_errors(path: Path) -> list[str]:
    try:
        contract = load_json(path)
    except (OSError, json.JSONDecodeError):
        return ["visual-master-contract.json 必须是有效 JSON"]
    if contract.get("mode") != "text_free_visual_master":
        return ["视觉主片必须使用 text_free_visual_master 模式"]
    allowed_layers = {"background", "decorative_visual", "product_ui_screenshot", "qr_asset"}
    declared_layers = contract.get("allowed_visual_layers")
    if not isinstance(declared_layers, list) or set(declared_layers) != allowed_layers:
        return ["视觉主片只能使用背景、装饰视觉、产品界面截图和二维码图层"]
    if contract.get("product_ui_text_allowed") is not True or contract.get("added_copy_layers") != []:
        return ["产品截图自身 UI 文字可以保留，视觉主片不得新增运营文字图层"]

    source_entrypoints = contract.get("source_entrypoints")
    if not isinstance(source_entrypoints, list) or not source_entrypoints:
        return ["必须登记视觉主片的实际源码入口"]
    for source in source_entrypoints:
        source_path = contract_evidence_path(path, str(source))
        if not source_path.is_file():
            return [f"视觉主片源码入口不存在：{source_path}"]

    verification = contract.get("verification", {})
    if verification.get("source_review_passed") is not True or verification.get("added_text_detected") is not False:
        return ["必须确认视觉主片源码和抽帧中没有新增运营文字"]
    sample_frames = verification.get("sample_frames")
    if not isinstance(sample_frames, list) or len(sample_frames) < 3:
        return ["必须保存开场、主体和二维码片尾的视觉主片验证帧"]
    for sample_frame in sample_frames:
        sample_path = contract_evidence_path(path, str(sample_frame))
        if not sample_path.is_file():
            return [f"视觉主片验证帧不存在：{sample_path}"]
    return []


def subtitle_display_width(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(char) in {"W", "F", "A"} else 1 for char in text)


def narration_contract_errors(path: Path) -> list[str]:
    if not path.is_file():
        return ["缺少规范旁白文本文件"]
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return ["必须在规范旁白文本文件中保存最终口播内容"]
    oversized = [str(index) for index, line in enumerate(lines, start=1) if subtitle_display_width(line) > 44]
    if oversized:
        return [f"旁白第 {', '.join(oversized)} 行超过单行字幕可读宽度，请按自然停顿拆分"]
    return []


def normalize_caption_text(text: str) -> str:
    return "".join(text.split())


def narration_cues_errors(path: Path, narration_path: Path) -> list[str]:
    try:
        cues = load_json(path)
    except (OSError, json.JSONDecodeError):
        return ["narration-cues.json 必须是有效 JSON"]
    if cues.get("source") != "jianying_add_narrated_subtitles":
        return ["逐句时间轴必须来自剪映 add_narrated_subtitles"]

    narration_lines = [
        normalize_caption_text(line)
        for line in narration_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    segments = cues.get("segments")
    if not isinstance(segments, list) or not segments:
        return ["必须登记剪映实际生成的逐句字幕与 TTS 时间段"]

    segment_texts: list[str] = []
    previous_end = -1.0
    for index, segment in enumerate(segments, start=1):
        if not isinstance(segment, dict):
            return [f"第 {index} 条字幕时间段格式无效"]
        text = normalize_caption_text(str(segment.get("text", "")))
        tts_asset = str(segment.get("tts_asset", "")).strip()
        start_ms = segment.get("start_ms")
        end_ms = segment.get("end_ms")
        if not text or not tts_asset or not isinstance(start_ms, (int, float)) or not isinstance(end_ms, (int, float)):
            return [f"第 {index} 条字幕必须包含 text、tts_asset、start_ms 和 end_ms"]
        tts_path = Path(tts_asset)
        if not tts_path.is_absolute():
            tts_path = path.parent / tts_path
        if not tts_path.is_file():
            return [f"第 {index} 条字幕登记的 TTS 素材不存在：{tts_path}"]
        if start_ms < previous_end or end_ms <= start_ms:
            return [f"第 {index} 条字幕时间段必须按真实音频顺序连续递增"]
        previous_end = float(end_ms)
        segment_texts.append(text)
    if segment_texts != narration_lines:
        return ["逐句字幕文本顺序必须与旁白文件的非空行完全一致"]

    layout = cues.get("layout", {})
    if (
        layout.get("canvas_width") != 1080
        or layout.get("canvas_height") != 1920
        or layout.get("anchor") != "bottom"
        or layout.get("main_track_scale") != 1.0
        or layout.get("numeric_y_position") is not True
    ):
        return ["字幕必须使用 1080×1920 底部数值坐标，主视频轨保持 100% 比例"]

    verification = cues.get("verification", {})
    required_checks = ("text_sequence_matches_narration", "timing_from_tts_assets", "no_overlap")
    if any(verification.get(check) is not True for check in required_checks):
        return ["必须完成字幕文本、真实 TTS 时间段和画面重叠技术校验"]
    proof_frames = verification.get("proof_frames")
    if not isinstance(proof_frames, list) or not proof_frames:
        return ["必须保存逐句时间中点的字幕验证帧"]
    for proof_frame in proof_frames:
        proof_path = Path(str(proof_frame))
        if not proof_path.is_absolute():
            proof_path = path.parent / proof_path
        if not proof_path.is_file():
            return [f"字幕验证帧不存在：{proof_path}"]
    return []


def project_contract_errors(stage: str, project: dict[str, Any]) -> list[str]:
    """Validate project-owned files that make cross-stage contracts enforceable."""
    files = project.get("files", {})
    if stage == "promo_render_with_qr":
        motion_errors = motion_plan_errors(Path(files.get("motion_plan", "")))
        if motion_errors:
            return motion_errors
        visual_errors = visual_master_contract_errors(Path(files.get("visual_master_contract", "")))
        if visual_errors:
            return visual_errors
    if stage in {"script", "jianying_post"}:
        narration_path = Path(files.get("narration", ""))
        narration_errors = narration_contract_errors(narration_path)
        if narration_errors:
            return narration_errors
    if stage == "jianying_post":
        script_path = Path(files.get("jianying_script", ""))
        if not script_path.is_file() or script_path.suffix.lower() != ".py":
            return ["必须在规范路径保存剪映自动化执行脚本"]
        source = script_path.read_text(encoding="utf-8")
        required_markers = ("read_text(", "add_narrated_subtitles(")
        if any(marker not in source for marker in required_markers):
            return ["剪映脚本必须读取规范旁白文本并调用 add_narrated_subtitles 同步生成声音和字幕"]
        if "add_tts_intelligent(" in source or "import_srt(" in source:
            return ["剪映旁白与字幕必须统一通过 add_narrated_subtitles 生成"]
        cues_errors = narration_cues_errors(Path(files.get("narration_cues", "")), narration_path)
        if cues_errors:
            return cues_errors
    return []


def new_project(workspace: Path, title: str, angle: str, selling_point: str, platform_name: str) -> dict[str, Any]:
    """Create versioned project state only after topic deduplication."""
    added = add_topic(workspace, title, angle, selling_point, platform_name)
    if not added["accepted"]:
        return {"created": False, **added, "next_action": "调整受众痛点、使用场景或证据形式，形成差异化选题。"}
    topic = added["topic"]
    project_id = f"{utc_now()[:10]}-{slugify(title)}-v1"
    path = state_path(workspace, project_id)
    version = 2
    while path.exists():
        project_id = f"{utc_now()[:10]}-{slugify(title)}-v{version}"
        path = state_path(workspace, project_id)
        version += 1
    config = load_config()
    files = initialize_project_files(workspace, project_id, title, platform_name)
    project = {
        "project_id": project_id,
        "topic_id": topic["id"],
        "title": title,
        "angle": angle,
        "selling_point": selling_point,
        "platform": platform_name,
        "stage": "script",
        "status": "active",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "approvals": {},
        "artifacts": {},
        "files": files,
        "history": [{"stage": "topic", "at": utc_now(), "note": "选题已通过去重检查"}],
        "contracts": {
            "main_film_audio_mode": config["workflow"]["main_film_audio_mode"],
            "main_film_text_mode": config["workflow"]["main_film_text_mode"],
            "allowed_main_film_text_sources": config["workflow"]["allowed_main_film_text_sources"],
            "added_marketing_copy_allowed": config["workflow"]["added_marketing_copy_allowed"],
            "motion_engine": config["workflow"]["motion_engine"],
            "motion_integration_mode": config["workflow"]["motion_integration_mode"],
            "hyperframes_package": config["tools"]["hyperframes_package"],
            "narration_engine": config["workflow"]["narration_engine"],
            "narration_selection": config["workflow"]["narration_selection"],
            "narration_sync_method": config["workflow"]["narration_sync_method"],
            "qr_phase": config["qr_outro"]["phase"],
            "qr_minimum_seconds": config["qr_outro"]["minimum_duration_seconds"],
            "subtitle_position": config["subtitles"]["position"],
            "main_canvas_scaled": False,
            "main_track_scale": config["visual_coverage"]["main_track_scale"],
            "minimum_visual_width_ratio": config["visual_coverage"]["minimum_width_ratio"],
            "minimum_visual_height_ratio": config["visual_coverage"]["minimum_height_ratio"],
            "auto_publish": False,
        },
    }
    atomic_write_json(path, project)
    return {"created": True, "project": project, "state_path": str(path), "next_action": NEXT_ACTIONS["script"]}


def approval_satisfied(project: dict[str, Any], stage: str) -> bool:
    required = REQUIRED_APPROVALS.get(stage, ())
    return all(project.get("approvals", {}).get(name, {}).get("approved") for name in required)


def advance_project(
    workspace: Path,
    project_id: str,
    artifact: str | None,
    note: str | None,
    executor_skill: str | None = None,
    skill_entrypoint: str | None = None,
    samples: list[str] | None = None,
) -> dict[str, Any]:
    """Advance one stage while enforcing approvals and QR ordering."""
    path = state_path(workspace, project_id)
    project = load_json(path)
    current = project["stage"]
    artifact_path = Path(artifact).expanduser() if artifact else None
    if current == "complete":
        return {"project": project, "next_action": NEXT_ACTIONS[current]}
    if current in REQUIRED_APPROVALS and not approval_satisfied(project, current):
        missing = [name for name in REQUIRED_APPROVALS[current] if not project.get("approvals", {}).get(name, {}).get("approved")]
        return {"advanced": False, "needs_approval": missing, "project": project, "next_action": NEXT_ACTIONS[current]}
    errors = artifact_errors(current, artifact_path)
    errors.extend(project_contract_errors(current, project))
    required_skill = REQUIRED_EXECUTOR_SKILLS.get(current)
    if required_skill:
        entrypoint = Path(skill_entrypoint).expanduser() if skill_entrypoint else None
        sample_paths = [Path(item).expanduser() for item in (samples or [])]
        if executor_skill != required_skill:
            errors.append(f"executor_skill 必须是 {required_skill}")
        if not entrypoint or entrypoint.name != "SKILL.md" or not entrypoint.is_file():
            errors.append("必须提供实际加载过且存在的依赖 Skill SKILL.md 路径")
        if current == "creative_brief":
            if len(sample_paths) != 3 or len({str(path.resolve()) for path in sample_paths}) != 3:
                errors.append("视觉阶段必须登记 3 个不同样帧")
            elif any(not path.is_file() for path in sample_paths):
                errors.append("3 个样帧文件必须全部存在")
    if errors:
        return {
            "advanced": False,
            "error": "；".join(errors),
            "required_executor_skill": required_skill,
            "project": project,
            "next_action": NEXT_ACTIONS[current],
        }
    if current == "qr_validation" and not project.get("artifacts", {}).get("qr_validation", {}).get("passed"):
        return {
            "advanced": False,
            "error": "二维码验证待完成。请在主片项目中更新二维码片尾并重新渲染。",
            "project": project,
            "next_action": NEXT_ACTIONS[current],
        }
    if artifact:
        artifact_record = {"path": artifact, "recorded_at": utc_now()}
        if required_skill:
            artifact_record["executor_skill"] = required_skill
            artifact_record["skill_entrypoint"] = str(Path(skill_entrypoint).expanduser().resolve())
            if sample_paths:
                artifact_record["samples"] = [str(path.resolve()) for path in sample_paths]
        project.setdefault("artifacts", {})[current] = artifact_record
    index = STAGES.index(current)
    next_stage = STAGES[index + 1]
    project["stage"] = next_stage
    project["updated_at"] = utc_now()
    project.setdefault("history", []).append({"stage": current, "at": utc_now(), "note": note or "阶段完成"})
    if next_stage == "complete":
        project["status"] = "complete"
        video_path = project.get("artifacts", {}).get("export", {}).get("path")
        if video_path and project.get("topic_id"):
            complete_topic(workspace, project["topic_id"], video_path)
    atomic_write_json(path, project)
    return {"advanced": True, "project": project, "state_path": str(path), "next_action": NEXT_ACTIONS[next_stage]}


def record_approval(workspace: Path, project_id: str, gate: str, approved: bool, note: str) -> dict[str, Any]:
    allowed = {gate_name for gates in REQUIRED_APPROVALS.values() for gate_name in gates} | {"publish"}
    if gate not in allowed:
        raise ValueError(f"Unknown approval gate: {gate}. Allowed: {sorted(allowed)}")
    path = state_path(workspace, project_id)
    project = load_json(path)
    project.setdefault("approvals", {})[gate] = {"approved": approved, "note": note, "at": utc_now()}
    project["updated_at"] = utc_now()
    atomic_write_json(path, project)
    return project


def record_qr_validation(workspace: Path, project_id: str, passed: bool, proof_frame: str, duration: float) -> dict[str, Any]:
    config = load_config()["qr_outro"]
    final_passed = passed and duration >= float(config["minimum_duration_seconds"])
    path = state_path(workspace, project_id)
    project = load_json(path)
    if project.get("stage") != "qr_validation":
        raise ValueError("QR validation can only be recorded after the main film has been rendered with its QR outro.")
    project.setdefault("artifacts", {})["qr_validation"] = {
        "passed": final_passed,
        "reported_scannable": passed,
        "proof_frame": proof_frame,
        "duration_seconds": duration,
        "required_phase": "promo_render",
        "at": utc_now(),
    }
    project["updated_at"] = utc_now()
    atomic_write_json(path, project)
    return project


def start(workspace: Path, install: bool = False) -> dict[str, Any]:
    """Wire deterministic initialization steps and return the interactive next action."""
    boot = bootstrap(workspace, install=install)
    assets = inventory(workspace, seed=True)
    pool = initialize_topic_pool(workspace)
    current = latest_project(workspace)
    topic_selection = None
    if current and current.get("status") == "active":
        next_action = f"继续项目 {current['project_id']}：{NEXT_ACTIONS[current['stage']]}"
    else:
        topic_selection = suggest_topics(workspace, count=3)
        next_action = (
            "补足并展示 3 个差异明显的选题方向，分别说明标题、内容角度和核心卖点；"
            "等待用户选择后再创建项目。"
        )
        current = None
    return {
        "ready": boot["ready"] and assets["ready"],
        "platform": platform.system(),
        "bootstrap": boot,
        "assets": {key: value for key, value in assets.items() if key != "files"},
        "topic_count": len(pool.get("topics", [])),
        "active_project": current,
        "topic_selection": topic_selection,
        "next_action": next_action,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".")
    sub = parser.add_subparsers(dest="command", required=True)
    start_parser = sub.add_parser("start")
    start_parser.add_argument("--install", action="store_true")
    new_parser = sub.add_parser("new")
    new_parser.add_argument("--title", required=True)
    new_parser.add_argument("--angle", required=True)
    new_parser.add_argument("--selling-point", required=True)
    new_parser.add_argument("--platform", default="douyin")
    status_parser = sub.add_parser("status")
    status_parser.add_argument("--project")
    advance_parser = sub.add_parser("advance")
    advance_parser.add_argument("--project", required=True)
    advance_parser.add_argument("--artifact")
    advance_parser.add_argument("--note")
    advance_parser.add_argument("--executor-skill")
    advance_parser.add_argument("--skill-entrypoint")
    advance_parser.add_argument("--sample", action="append", default=[])
    approve_parser = sub.add_parser("approve")
    approve_parser.add_argument("--project", required=True)
    approve_parser.add_argument("--gate", required=True)
    approve_parser.add_argument("--approved", choices=("yes", "no"), required=True)
    approve_parser.add_argument("--note", default="")
    qr_parser = sub.add_parser("record-qr")
    qr_parser.add_argument("--project", required=True)
    qr_parser.add_argument("--passed", choices=("yes", "no"), required=True)
    qr_parser.add_argument("--proof-frame", required=True)
    qr_parser.add_argument("--duration", required=True, type=float)
    args = parser.parse_args()
    workspace = Path(args.workspace)
    if args.command == "start":
        result = start(workspace, install=args.install)
    elif args.command == "new":
        result = new_project(workspace, args.title, args.angle, args.selling_point, args.platform)
    elif args.command == "status":
        project = load_json(state_path(workspace, args.project)) if args.project else latest_project(workspace)
        result = {"project": project, "next_action": NEXT_ACTIONS[project["stage"]] if project else "创建新项目。"}
    elif args.command == "advance":
        result = advance_project(
            workspace,
            args.project,
            args.artifact,
            args.note,
            args.executor_skill,
            args.skill_entrypoint,
            args.sample,
        )
    elif args.command == "approve":
        result = record_approval(workspace, args.project, args.gate, args.approved == "yes", args.note)
    else:
        result = record_qr_validation(workspace, args.project, args.passed == "yes", args.proof_frame, args.duration)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.command == "new" and not result.get("created"):
        return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

