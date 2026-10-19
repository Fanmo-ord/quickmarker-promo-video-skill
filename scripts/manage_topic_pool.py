#!/usr/bin/env python3
"""Persist promotional topics and reject repeated angles, not only repeated titles."""

from __future__ import annotations

import argparse
import json
import random
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from common import SKILL_ROOT, atomic_write_json, load_json, slugify, utc_now, workspace_layout


def normalize(text: str) -> str:
    """Normalize Chinese/English topic text for deterministic comparison."""
    return re.sub(r"[^\w\u4e00-\u9fff]", "", text.lower())


def ngrams(text: str, size: int = 2) -> set[str]:
    """Return character n-grams suitable for short Chinese phrases."""
    clean = normalize(text)
    if len(clean) <= size:
        return {clean} if clean else set()
    return {clean[index : index + size] for index in range(len(clean) - size + 1)}


def similarity(left: str, right: str) -> float:
    """Blend sequence and bigram Jaccard similarity."""
    left_n, right_n = normalize(left), normalize(right)
    sequence = SequenceMatcher(None, left_n, right_n).ratio()
    left_g, right_g = ngrams(left_n), ngrams(right_n)
    union = left_g | right_g
    jaccard = len(left_g & right_g) / len(union) if union else 0.0
    return round(max(sequence, jaccard), 4)


def pool_path(workspace: Path) -> Path:
    return workspace_layout(workspace)["state"] / "topic-pool.json"


def initialize(workspace: Path) -> dict[str, Any]:
    """Create a pool from the bundled template when absent."""
    path = pool_path(workspace)
    if not path.exists():
        template = load_json(SKILL_ROOT / "assets" / "templates" / "topic-pool.json")
        atomic_write_json(path, template)
    return load_json(path)


def find_duplicate(pool: dict[str, Any], title: str, angle: str, threshold: float) -> dict[str, Any] | None:
    """Return the closest used/planned topic when similarity crosses threshold."""
    candidate = f"{title} {angle}"
    best: dict[str, Any] | None = None
    for topic in pool.get("topics", []):
        score = similarity(candidate, f"{topic.get('title', '')} {topic.get('angle', '')}")
        if best is None or score > best["score"]:
            best = {"score": score, "topic": topic}
    return best if best and best["score"] >= threshold else None


def add_topic(
    workspace: Path,
    title: str,
    angle: str,
    selling_point: str,
    platform: str,
    threshold: float = 0.72,
) -> dict[str, Any]:
    """Add a planned topic or return a duplicate rejection."""
    pool = initialize(workspace)
    duplicate = find_duplicate(pool, title, angle, threshold)
    if duplicate:
        return {"accepted": False, "reason": "duplicate", "duplicate": duplicate}
    topic_id = f"{utc_now()[:10]}-{slugify(title)}"
    existing_ids = {item.get("id") for item in pool.get("topics", [])}
    suffix = 2
    base_id = topic_id
    while topic_id in existing_ids:
        topic_id = f"{base_id}-{suffix}"
        suffix += 1
    item = {
        "id": topic_id,
        "title": title.strip(),
        "angle": angle.strip(),
        "selling_point": selling_point.strip(),
        "platform": platform,
        "status": "planned",
        "created_at": utc_now(),
        "completed_at": None,
        "video_path": None,
    }
    pool.setdefault("topics", []).append(item)
    atomic_write_json(pool_path(workspace), pool)
    return {"accepted": True, "topic": item}


def complete_topic(workspace: Path, topic_id: str, video_path: str) -> dict[str, Any]:
    """Mark a topic complete and retain its final artifact for future dedupe."""
    pool = initialize(workspace)
    for topic in pool.get("topics", []):
        if topic.get("id") == topic_id:
            topic.update(status="complete", completed_at=utc_now(), video_path=video_path)
            atomic_write_json(pool_path(workspace), pool)
            return topic
    raise KeyError(f"Unknown topic id: {topic_id}")


def suggest_topics(workspace: Path, count: int = 3, threshold: float = 0.72) -> dict[str, Any]:
    """Return distinct bundled ideas whose angles have not already been used."""
    pool = initialize(workspace)
    candidates = [
        idea
        for idea in pool.get("ideas", [])
        if not find_duplicate(pool, idea["title"], idea["angle"], threshold)
    ]
    random.shuffle(candidates)
    suggestions: list[dict[str, Any]] = []
    for candidate in candidates:
        if any(
            similarity(
                f"{candidate['title']} {candidate['angle']}",
                f"{selected['title']} {selected['angle']}",
            )
            >= threshold
            for selected in suggestions
        ):
            continue
        suggestions.append(candidate)
        if len(suggestions) == count:
            break
    return {
        "suggestions": suggestions,
        "required_count": count,
        "generation_needed": max(0, count - len(suggestions)),
        "reason": "候选来自未使用的预置选题；不足部分由 AI 生成并通过重复度检查后补齐。",
    }


def suggest_topic(workspace: Path, threshold: float = 0.72) -> dict[str, Any]:
    """Return the first bundled idea whose angle is not already used."""
    pool = initialize(workspace)
    candidates = [
        idea
        for idea in pool.get("ideas", [])
        if not find_duplicate(pool, idea["title"], idea["angle"], threshold)
    ]
    if candidates:
        return {"suggestion": random.choice(candidates), "reason": "从未使用的预置选题中随机生成"}
    return {
        "suggestion": None,
        "reason": "预置选题已用完；AI 应从新受众痛点、使用场景或证据形式生成新角度。",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("list")
    suggest = sub.add_parser("suggest")
    suggest.add_argument("--count", type=int, default=3)
    check = sub.add_parser("check")
    add = sub.add_parser("add")
    complete = sub.add_parser("complete")
    for cmd in (check, add):
        cmd.add_argument("--title", required=True)
        cmd.add_argument("--angle", required=True)
        cmd.add_argument("--threshold", type=float, default=0.72)
    add.add_argument("--selling-point", required=True)
    add.add_argument("--platform", default="douyin")
    complete.add_argument("--id", required=True)
    complete.add_argument("--video", required=True)
    args = parser.parse_args()
    workspace = Path(args.workspace)
    pool = initialize(workspace)
    if args.command in {"init", "list"}:
        result: Any = pool
    elif args.command == "suggest":
        result = suggest_topics(workspace, count=max(1, args.count))
    elif args.command == "check":
        duplicate = find_duplicate(pool, args.title, args.angle, args.threshold)
        result = {"duplicate": bool(duplicate), "match": duplicate}
    elif args.command == "add":
        result = add_topic(workspace, args.title, args.angle, args.selling_point, args.platform, args.threshold)
    else:
        result = complete_topic(workspace, args.id, args.video)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 5 if args.command == "add" and not result.get("accepted") else 0


if __name__ == "__main__":
    raise SystemExit(main())

