#!/usr/bin/env python3
"""Map Impeccable detector JSON findings onto the codebook (source-scan comparison only).

    python integrations/baselines/impeccable_import.py findings.json [--out summary.json]

Impeccable (pinned: pbakaus/impeccable 687bc381, package 4.8.0, engine 0.1.18)
prints a JSON array of findings with the keys antipattern, name, description,
severity, category, file, line, snippet (and optionally advisory, ignoreValue);
the format is taken from crates/foundation/src/findings.rs in that commit.

UNTESTED INTEGRATION: the detector itself was not run here (it needs a compiled
engine). This importer is tested only against findings in that documented
shape. Its output is a per-code count of source-scan hits. It is not a
region-level audit: Impeccable reports files and lines, not bundle regions, so
it is never scored against rendered-region annotations, and rendered (URL)
scans and source scans are kept apart. It is not an origin detector.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

PINNED = {"repo": "pbakaus/impeccable", "commit": "687bc381bc9091bf252c0a05303640561014a425", "package": "4.8.0", "engine": "0.1.18"}

# Comparable rules only. Everything else is reported as unmatched, never forced into a code.
MAPPING = {
    "ai-color-palette": "VIS-01", "cream-palette": "VIS-01", "dark-glow": "VIS-01",
    "gradient-text": "VIS-02", "kicker-above-heading": "VIS-02", "hero-eyebrow-chip": "VIS-02",
    "numbered-section-labels": "VIS-02", "italic-serif-display": "VIS-02",
    "nested-cards": "LAY-01", "icon-tile-stack": "VIS-03", "radial-halo": "VIS-03", "radial-spotlight-glow": "VIS-03",
    "repeating-stripes-gradient": "VIS-03", "shape-assembled-illustration": "VIS-03",
    "bounce-easing": "MOT-01", "pulsing-dot": "MOT-01", "marquee": "MOT-01", "blinking-cursor": "MOT-01",
    "marketing-buzzword": "TXT-01", "theater-slop-phrase": "TXT-01", "aphoristic-cadence": "TXT-02",
    "broken-image": "QLT-01", "low-contrast": "QLT-01", "text-overflow": "QLT-01", "tiny-text": "QLT-01",
    "content-hidden-at-rest": "QLT-01", "text-occlusion": "QLT-01",
}
# Rules this rubric deliberately does not adopt as stand-alone cues.
EXCLUDED = {
    "overused-font": "a font family alone is excluded as a stand-alone cue (codebook prohibited inferences)",
    "em-dash-overuse": "punctuation alone is excluded as a stand-alone cue",
    "gpt-thin-border-wide-shadow": "rule name implies a generator identity; generator inference is prohibited",
    "codex-grid-background": "rule name implies a generator identity; generator inference is prohibited",
}


def summarize(findings):
    by_code, unmatched, excluded = Counter(), Counter(), Counter()
    for f in findings:
        rule = f.get("antipattern")
        if rule in MAPPING:
            by_code[MAPPING[rule]] += 1
        elif rule in EXCLUDED:
            excluded[rule] += 1
        else:
            unmatched[rule] += 1
    return {
        "baseline": "impeccable-detector", "pinned": PINNED, "scan_kind": "source",
        "hits_by_codebook_feature": dict(sorted(by_code.items())),
        "excluded_rule_hits": dict(sorted(excluded.items())),
        "unmatched_rule_hits": dict(sorted(unmatched.items())),
        "files": sorted({f.get("file", "") for f in findings}),
        "note": "Source-scan presence counts only; not comparable to region-level human annotations.",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("findings")
    p.add_argument("--out")
    a = p.parse_args(argv)
    data = json.loads(Path(a.findings).read_text(encoding="utf-8"))
    findings = data if isinstance(data, list) else data.get("findings", [])
    out = json.dumps(summarize(findings), indent=2)
    if a.out:
        Path(a.out).write_text(out + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
