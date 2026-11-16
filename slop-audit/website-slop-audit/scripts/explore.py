#!/usr/bin/env python3
"""Explore the audited site live, one logged action at a time, by handing commands to this environment's exploration adapter.

    python3 scripts/explore.py start --bundle BUNDLE --tour-audit RUN/audit.tour.json --out RUN/exploration
    python3 scripts/explore.py look --session RUN/exploration
    python3 scripts/explore.py scroll --session RUN/exploration --by 800
    python3 scripts/explore.py hover --session RUN/exploration "#chart circle" --nth 3
    python3 scripts/explore.py finish --session RUN/exploration

Commands: start, look, scroll (--by PX | --to Y | --to-element SEL | --top | --bottom, optional --frames),
hover (SEL [--nth N] | --at X Y), click SEL, select SEL VALUE, slide SEL VALUE, goto ROUTE, back,
wait MS [--shot], find (charts | controls | marks SEL), read [SEL], status, finish [--note TEXT].
Run with --help after a command for its options.

The audit instructions never depend on a particular browser. This script only
finds the exploration adapter that ships next to the skill in this repository
(integrations/capture/explore_session.py) or the one named by the environment
variable WEBSITE_SLOP_AUDIT_EXPLORE, and runs it with the same arguments.

Adapter contract (references/exploration-protocol.md): enforce the site's
scope and the safety rules, log every action with an id (L001, ...), keep a
fixed budget, and on finish write exploration.json that passes
scripts/validate_exploration.py, locked with exploration.lock.json.
"""

import os
import subprocess
import sys
from pathlib import Path

ENV = "WEBSITE_SLOP_AUDIT_EXPLORE"


def find_adapter():
    if os.environ.get(ENV):
        return Path(os.environ[ENV]).expanduser()
    here = Path(__file__).resolve()  # resolves the symlinks agents load the skill through
    candidate = here.parents[2] / "integrations" / "capture" / "explore_session.py"
    return candidate if candidate.is_file() else None


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if argv else 2
    adapter = find_adapter()
    if adapter is None or not adapter.is_file():
        print("No exploration adapter is available in this environment, so the live site cannot be explored here.\n"
              f"Either run this skill from its repository (which ships integrations/capture/explore_session.py), set {ENV} "
              "to an adapter that follows references/exploration-protocol.md, or skip the exploration stage and record "
              "exploration_stage with status not_done and the reason.", file=sys.stderr)
        return 2
    return subprocess.call([sys.executable, str(adapter), *argv])


if __name__ == "__main__":
    sys.exit(main())
