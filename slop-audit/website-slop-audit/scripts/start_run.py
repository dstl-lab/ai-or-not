#!/usr/bin/env python3
"""Make a fresh folder for one auditor's run on a frozen bundle, so several models can audit the same capture.

    python3 scripts/start_run.py --bundle BUNDLE --rater "anthropic/claude-opus-5-5"

Prints AUDIT_DIR=<capture folder>/runs/<UTC time>-<rater>/ and writes run.json
there (rater, bundle id and hash, start time). Write audit.tour.json,
audit.json, the exploration folder, the reports, and the CSV files into it.
Nothing is ever overwritten: every call makes a new folder.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402


def slug(text, limit=48):
    s = re.sub(r"[^A-Za-z0-9.]+", "-", text).strip("-").lower()
    return (s or "rater")[:limit].strip("-")


def start(bundle_dir, rater, root=None):
    bundle = _lib.Bundle(bundle_dir)
    capture = Path(root) if root else bundle.dir.resolve().parent
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = capture / "runs" / f"{stamp}-{slug(rater)}"
    run, n = base, 1
    while run.exists():
        n += 1
        run = base.with_name(f"{base.name}-{n}")
    run.mkdir(parents=True)
    info = {"rater": rater, "bundle": str(bundle.dir.resolve()), "bundle_id": bundle.bundle_id, "bundle_hash": bundle.hash,
            "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    (run / "run.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    return run


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--bundle", required=True, help="the frozen capture bundle")
    p.add_argument("--rater", required=True, help="the model doing the audit, as provider/model, e.g. openai/gpt-5-codex")
    p.add_argument("--root", help="folder to put runs/ in (default: the folder that holds the bundle)")
    a = p.parse_args(argv)
    print(f"AUDIT_DIR={start(a.bundle, a.rater, a.root)}")
    return 0


if __name__ == "__main__":
    _lib.run_main(main)
