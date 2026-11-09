#!/usr/bin/env python3
"""Capture a website URL into a frozen bundle by handing it to this environment's acquisition adapter.

    python3 scripts/acquire_url.py https://example.github.io/project/ [adapter options]

The audit instructions never depend on a particular browser. This script only
finds the acquisition adapter that ships next to the skill in this repository
(integrations/capture/site_capture.py) or the one named by the environment
variable WEBSITE_SLOP_AUDIT_ACQUIRE, and runs it with the same arguments.

Adapter contract (references/capture-protocol.md, "One-line acquisition"):
take a URL plus options, write RUN_DIR/bundle as a validated and frozen
bundle, and print RUN_DIR=..., BUNDLE=..., and SUGGESTED_PROFILE=... lines.
Useful options of the bundled adapter: --single-page, --max-pages N,
--max-controls N, --budget N (8 makes a bundle small enough for chat apps),
--withhold TERM (repeatable; masks names and blinds the bundle), --out DIR.
"""

import os
import subprocess
import sys
from pathlib import Path

ENV = "WEBSITE_SLOP_AUDIT_ACQUIRE"


def find_adapter():
    if os.environ.get(ENV):
        return Path(os.environ[ENV]).expanduser()
    here = Path(__file__).resolve()  # resolves the symlinks agents load the skill through
    candidate = here.parents[2] / "integrations" / "capture" / "site_capture.py"
    return candidate if candidate.is_file() else None


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if argv else 2
    adapter = find_adapter()
    if adapter is None or not adapter.is_file():
        print("No acquisition adapter is available in this environment, so a URL cannot be captured here.\n"
              f"Either run this skill from its repository (which ships integrations/capture/site_capture.py), set {ENV} "
              "to an adapter that follows references/capture-protocol.md, or supply a frozen capture bundle instead.",
              file=sys.stderr)
        return 2
    return subprocess.call([sys.executable, str(adapter), *argv])


if __name__ == "__main__":
    sys.exit(main())
