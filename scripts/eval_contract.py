#!/usr/bin/env python3
"""Small command grader for the bundled workflow contract fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", choices=("qr", "order", "platform", "safety"), required=True)
    parser.add_argument("output")
    args = parser.parse_args()
    data = json.loads(Path(args.output).read_text(encoding="utf-8"))
    if args.check == "qr":
        qr = data.get("qr_outro", {})
        ok = qr.get("phase") == "promo_render" and qr.get("minimum_duration_seconds", 0) >= 5 and qr.get("required") is True
    elif args.check == "order":
        order = data.get("workflow_order", [])
        ok = all(name in order for name in ("promo_render_with_qr", "jianying_post")) and order.index("promo_render_with_qr") < order.index("jianying_post")
    elif args.check == "platform":
        export = data.get("export", {})
        ok = (
            export.get("macos") == "manual"
            and export.get("windows") == "automatic"
            and export.get("final_review") == "user"
        )
    else:
        safety = data.get("safety", {})
        ok = safety.get("paid_services_allowed") is False and safety.get("auto_publish") is False and safety.get("privacy_review_required") is True
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

