# QuickMarker Promo Video Skill

## Purpose

This repository is an installable Agent Skill for producing daily QuickMarker/英语批改助手 promotional videos. Read [SKILL.md](SKILL.md) before acting.

## Activation

Activate when the user asks for QuickMarker marketing videos, daily short-video topics, product promo scripts, automated editing, or to continue a saved video project.

## Operating rules

- The AI performs technical setup and production. The user approves creative decisions, manually exports on macOS, and decides whether to publish.
- Use only free/open-source or already licensed tools and assets by default.
- Main picture production uses `ai-promo-video-maker`; final narration, one bottom subtitle layer, mix, and cover use `jianying-editor-skill`.
- The QR outro is rendered into the main film before JianYing post-production. Never defer it to the JianYing stage and never add it twice.
- Never shrink the main picture to make room for subtitles.
- Do not expose student or teacher personal information. Do not publish or push sensitive assets to a public repository.
- Preserve checkpoints and versioned outputs. Never overwrite an approved result.
- Follow `references/file-management.md` before creating or moving any workspace file; never scatter generated files in the workspace root.
- Do not auto-publish to social platforms.

## First command

Run this yourself; do not turn it into a manual tutorial for the user:

```bash
python3 scripts/run_pipeline.py --workspace "<workspace>" start --install
```

Follow the returned `next_action`. Read the detailed references only when the relevant phase is reached.

