#!/usr/bin/env python3
"""Generate references/feature-codebook.md and references/evidence-sources.md
from assets/codebook.json (the single source of truth).

    python scripts/build_codebook.py          # rewrite both files
    python scripts/build_codebook.py --check  # exit 1 if either file is stale
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

REF_DIR = _lib.SKILL_ROOT / "references"
HEADER = "<!-- GENERATED from assets/codebook.json by scripts/build_codebook.py. Edit the JSON, then rebuild. -->\n\n"


def anchor(f):
    """GitHub-style heading anchor for '### VIS-01: Default aesthetic package'."""
    text = f"{f['id']}: {f['title']}".lower()
    return "".join(c for c in text.replace(" ", "-") if c.isalnum() or c in "-_")


def feature_block(f):
    alt = "; ".join(f["alternative_explanations"])
    mods = " or ".join("+".join(s) for s in f["modality_sets"])
    extra = []
    if f.get("requires_completed_interaction"):
        extra.append("requires a completed recorded interaction")
    if f.get("min_regions", 1) > 1:
        extra.append(f"at least {f['min_regions']} regions")
    rules = f" ({'; '.join(extra)})" if extra else ""
    return "\n".join([
        f"### {f['id']}: {f['title']}",
        "",
        f"*Module:* `{f['module']}` · *Unit:* {f['unit_of_observation']} · *Judgment:* {f['judgment']} · "
        f"*Evidence status:* `{f['evidence_status']}` · *Consequence required:* {'yes' if f['consequence_required'] else 'no'}",
        "",
        f"- **Definition.** {f['definition']}",
        f"- **Include when.** {f['inclusion']}",
        f"- **Exclude.** {f['exclusion']}",
        f"- **Minimum evidence.** {f['minimum_evidence']}{rules}",
        f"- **Modalities.** {mods}",
        f"- **Positive example.** {f['positive_example']}",
        f"- **Legitimate counterexample.** {f['counterexample']}",
        f"- **Alternative explanations.** {alt}",
        f"- **Boundary.** {f['boundaries']}",
        f"- **Sources.** {', '.join(f['sources'])}",
        "",
    ])


def render_codebook(cb, features=None, modules=None, for_prompt=False):
    """Full reference file, or (for_prompt) the subset a profile's prompt needs."""
    features = cb["features"] if features is None else features
    toc = [f"- [{f['id']}: {f['title']}](#{anchor(f)})" for f in features]
    out = [HEADER, f"# Feature codebook (rubric {cb['rubric_version']})", "",
           f"Status: {cb['status']}.", "",
           "Contents: definition, dimensions, prohibited inferences, ordinal anchors, evidence-status levels, "
           "modules, then one entry per feature:", ""] + toc + ["",
           "## Definition", "", f"> {cb['definition']['text']}", "",
           f"*{cb['definition']['attribution']}*", "",
           "## Four dimensions, kept separate", ""]
    out += [f"{i}. **{d['id'].replace('_', ' ')}**: {d['text']}" for i, d in enumerate(cb["dimensions"], 1)]
    out += ["", "## Never infer", ""] + [f"- {p}" for p in cb["prohibited_inferences"]]
    out += ["", "## Ordinal anchors", "", cb["anchors"]["note"], ""]
    for scale in ("slop_association", "observation_confidence", "contextual_fit", "consequence"):
        out.append(f"**{scale}**")
        out.append("")
        out += [f"- `{k}`: {v}" for k, v in cb["anchors"][scale].items()]
        out.append("")
    out += ["## Evidence-status levels", "", "The auditor copies a feature's status from this codebook and never changes it.", ""]
    out += [f"- `{k}`: {v}" for k, v in cb["evidence_status_levels"].items()]
    out += ["", "## Modules", ""] + [f"- `{k}`: {v}" for k, v in cb["modules"].items()
                                       if modules is None or k in modules]
    out += ["", "## Features", ""]
    family = None
    for f in features:
        if f["family"] != family:
            family = f["family"]
            out += [f"## Family {family}: {f['family_title']}", ""]
        out.append(feature_block(f))
    oc = cb["other_candidate"]
    out += [f"## {oc['id']}: {oc['title']}", "", oc["text"], ""]
    if not for_prompt:
        out += ["## Changelog", ""] + [f"- **{c['version']}** ({c['date']}): {c['change']}" for c in cb["changelog"]]
    if for_prompt:
        out = out[1:]  # drop the generated-file banner
    return "\n".join(out).rstrip() + "\n"


def render_sources(cb):
    out = [HEADER, f"# Evidence sources ledger (rubric {cb['rubric_version']})", "",
           "Each entry records what was read, at what access level, what it supports, and its limits. "
           "None of these sources validates an authorship detector. Practitioner guidance, empirical findings, "
           "and this project's own hypotheses are labeled separately (`kind`). Benchmark judgments must not do "
           "fresh web research; this ledger is fixed per rubric version.", ""]
    used = {}
    for f in cb["features"]:
        for s in f["sources"]:
            used.setdefault(s, []).append(f["id"])
    for s in cb["sources"]:
        out += [f"## {s['id']}", "",
                f"- **Citation.** {s['citation']}",
                f"- **URL.** {s['url'] or 'none (internal)'}",
                f"- **Kind.** `{s['kind']}` · **Access level.** `{s['access_level']}`",
                f"- **Section read.** {s['section']}",
                f"- **Version / date.** {s['version_or_date']}",
                f"- **Supported proposition.** {s['supported_proposition']}",
                f"- **Limitation.** {s['limitation']}",
                f"- **Cited by features.** {', '.join(used.get(s['id'], [])) or 'definition and protocol only'}",
                ""]
    return "\n".join(out).rstrip() + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    cb = _lib.load_codebook()
    ids = {s["id"] for s in cb["sources"]}
    missing = sorted({s for f in cb["features"] for s in f["sources"]} - ids)
    if missing:
        raise _lib.UsageError(f"features cite unknown sources: {missing}")
    targets = {REF_DIR / "feature-codebook.md": render_codebook(cb), REF_DIR / "evidence-sources.md": render_sources(cb)}
    stale = [p for p, text in targets.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
    if args.check:
        for p in stale:
            print(f"stale: {p.relative_to(_lib.SKILL_ROOT)} (run scripts/build_codebook.py)")
        return 1 if stale else 0
    for p, text in targets.items():
        p.write_text(text, encoding="utf-8")
        print(f"wrote {p.relative_to(_lib.SKILL_ROOT)}")
    return 0


if __name__ == "__main__":
    _lib.run_main(main)
