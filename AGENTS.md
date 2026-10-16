# QuickMarker Agent Guide

Use [SKILL.md](SKILL.md) as the workflow entrypoint.

## Operating principles

- Execute the automation directly and present user decisions at the visual, audio, cover, export, and publish gates.
- Use free/open-source tools and assets with clear commercial-use rights.
- Build the main film with a scannable QR outro before JianYing post-production.
- Preserve a full-size 9:16 picture with one synchronized bottom subtitle layer.
- Apply privacy review to names, grades, schools, phone numbers, handwriting, and student records.
- Store work according to `references/file-management.md` and keep versioned project outputs.
- Treat publishing as a user-approved action.

## Start

```bash
python3 scripts/run_pipeline.py --workspace "<workspace>" start --install
```

Follow the returned `next_action` and load the referenced guide for the active phase.
