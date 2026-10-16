#!/usr/bin/env python3
"""Single stateful entry point for the interactive QuickMarker video pipeline."""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path
from typing import Any

from bootstrap import bootstrap
from check_assets import inventory
from common import atomic_write_json, load_config, load_json, slugify, utc_now, workspace_layout
from manage_topic_pool import add_topic, initialize as initialize_topic_pool, suggest_topic


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
    "delivery_validation",
    "complete",
)

REQUIRED_APPROVALS = {
    "creative_approval": ("visual_sample", "audio_direction"),
    "cover_approval": ("cover",),
}

NEXT_ACTIONS = {
    "topic": "读取选题池并提出具有明显差异的选题、角度和卖点。",
    "script": "撰写短视频脚本、镜头表、平台标题和发布文案。",
    "creative_brief": "调用 promo-video-maker 生成视觉方向和样帧，并推荐免费可商用 BGM/旁白方向。",
    "creative_approval": "向用户展示样帧、BGM 和声音推荐，等待 visual_sample 与 audio_direction 两项确认。",
    "promo_render_with_qr": "用 ai-promo-video-maker 生成主片，并在主片项目中加入至少 5 秒的二维码片尾。",
    "qr_validation": "截取主片片尾画面，验证二维码完整、无遮挡且可扫描，通过后进入剪映后期。",
    "jianying_post": "导入主片，用剪映加入自然旁白、单层底部字幕、混音和封面。",
    "cover_approval": "展示剪映生成的封面，等待用户确认或给出一次修改意见。",
    "export": "Windows 自动导出并验证；macOS 打开草稿并请用户手动点击导出。",
    "delivery_validation": "运行交付验证，生成 delivery-manifest.json，并进入用户发布确认阶段。",
    "complete": "汇总成片、封面、脚本、发布文案和验证报告，并等待用户决定是否发布。",
}


def state_path(workspace: Path, project_id: str) -> Path:
    return workspace_layout(workspace)["projects"] / f"{project_id}.json"


def latest_project(workspace: Path) -> dict[str, Any] | None:
    paths = sorted(workspace_layout(workspace)["projects"].glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    return load_json(paths[0]) if paths else None


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
        "history": [{"stage": "topic", "at": utc_now(), "note": "选题已通过去重检查"}],
        "contracts": {
            "qr_phase": config["qr_outro"]["phase"],
            "qr_minimum_seconds": config["qr_outro"]["minimum_duration_seconds"],
            "subtitle_position": config["subtitles"]["position"],
            "main_canvas_scaled": False,
            "auto_publish": False,
        },
    }
    atomic_write_json(path, project)
    return {"created": True, "project": project, "state_path": str(path), "next_action": NEXT_ACTIONS["script"]}


def approval_satisfied(project: dict[str, Any], stage: str) -> bool:
    required = REQUIRED_APPROVALS.get(stage, ())
    return all(project.get("approvals", {}).get(name, {}).get("approved") for name in required)


def advance_project(workspace: Path, project_id: str, artifact: str | None, note: str | None) -> dict[str, Any]:
    """Advance one stage while enforcing approvals and QR ordering."""
    path = state_path(workspace, project_id)
    project = load_json(path)
    current = project["stage"]
    if current == "complete":
        return {"project": project, "next_action": NEXT_ACTIONS[current]}
    if current in REQUIRED_APPROVALS and not approval_satisfied(project, current):
        missing = [name for name in REQUIRED_APPROVALS[current] if not project.get("approvals", {}).get(name, {}).get("approved")]
        return {"advanced": False, "needs_approval": missing, "project": project, "next_action": NEXT_ACTIONS[current]}
    if current == "qr_validation" and not project.get("artifacts", {}).get("qr_validation", {}).get("passed"):
        return {
            "advanced": False,
            "error": "二维码验证待完成。请在主片项目中更新二维码片尾并重新渲染。",
            "project": project,
            "next_action": NEXT_ACTIONS[current],
        }
    if artifact:
        project.setdefault("artifacts", {})[current] = {"path": artifact, "recorded_at": utc_now()}
    index = STAGES.index(current)
    next_stage = STAGES[index + 1]
    project["stage"] = next_stage
    project["updated_at"] = utc_now()
    project.setdefault("history", []).append({"stage": current, "at": utc_now(), "note": note or "阶段完成"})
    if next_stage == "complete":
        project["status"] = "complete"
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
    if current and current.get("status") == "active":
        next_action = f"继续项目 {current['project_id']}：{NEXT_ACTIONS[current['stage']]}"
    else:
        suggestion = suggest_topic(workspace)
        next_action = "根据建议选题创建新项目，并向用户简短说明推荐角度。"
        current = None
    return {
        "ready": boot["ready"] and assets["ready"],
        "platform": platform.system(),
        "bootstrap": boot,
        "assets": {key: value for key, value in assets.items() if key != "files"},
        "topic_count": len(pool.get("topics", [])),
        "active_project": current,
        "suggestion": None if current else suggest_topic(workspace),
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
        result = advance_project(workspace, args.project, args.artifact, args.note)
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

