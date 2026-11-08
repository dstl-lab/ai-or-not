#!/usr/bin/env python3
"""Build the generic-prompt baseline package (condition 1 of the benchmark protocol).

    python integrations/baselines/expand_generic.py --bundle BUNDLE --profile multimodal-datastory --out RUN_DIR

Same task, same frozen evidence, same image order, same output schema, and the
same response block as the frozen-skill condition, so outputs are scored the
same way. What it leaves out is the skill: no construct definition, no
codebook definitions, inclusion or exclusion rules, anchors, or evidence and
location rules. Feature codes appear only as names, so findings stay
scorable. This is a design choice; a fully free-form baseline would need the
human-mapped relaxed scoring path instead (see critique_mapping.py).
"""

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "website-slop-audit" / "scripts"))
import _lib  # noqa: E402
import expand_prompt  # noqa: E402

TEMPLATE = HERE / "generic-identification.md"


def instructions(profile_id):
    feats = _lib.profile_features(profile_id)
    listing = "\n".join(f"- {f['id']}: {f['title']}" for f in feats)
    return TEMPLATE.read_text(encoding="utf-8").replace("FEATURE_LIST", listing).rstrip()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--bundle", required=True)
    p.add_argument("--profile", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--max-chars", type=int)
    a = p.parse_args(argv)
    lock = expand_prompt.build_package(a.bundle, a.profile, a.out, a.max_chars, condition="generic-prompt",
                                       instructions=instructions(a.profile), template_files=[TEMPLATE, Path(__file__)])
    print(f"prompt_sha256  {lock['prompt_sha256']}\npackage_sha256 {lock['package_sha256']}\n{lock['prompt_chars']} characters, {lock['image_count']} image(s)")
    return 0


if __name__ == "__main__":
    _lib.run_main(main)
