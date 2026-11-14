#!/usr/bin/env python3
"""Freeze the human study's per-website questions into assets/study-questions.json.

    python scripts/sync_study_questions.py SOURCE_questions.json --repository dstl-lab/ai-or-not \\
        --pull-request 6 --branch codex/merge-reviewer-phd --commit b02e48d... --path config/questions.json
    python scripts/sync_study_questions.py SOURCE_questions.json ... --check   # exit 1 if the frozen copy differs

The study platform's config/questions.json is the source of truth for the
wording the participants see. This copies the per-website questions the skill
answers, word for word, together with the shared feature list and where the
copy came from, so any model given the skill receives the participants' exact
wording. Run it again whenever the study's questions change; the version id
(`questionnaire_version`) comes from the source file.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

TARGET = _lib.ASSET_DIR / "study-questions.json"
ANSWERED = ["ai_appearance", "ai_marks", "feature_rating", "top_ai_feature", "ai_extent",
            "design_generic", "writing_ai", "polish", "quality", "technical_issue"]
NOT_ANSWERED = {
    "ai_changes_view": "asks about the rater's own values, not the site",
    "seen_before": "not meaningful for a model",
    "annotations": "follow-up item asked of participants on two sites; not part of the skill's answers",
    "cues": "follow-up item asked of participants on two sites; not part of the skill's answers",
}
# The plain-language element kinds of the study's marks.csv export (docs/data-dictionary.md).
MARK_KINDS = ["Heading", "Text", "Chart or graphic", "Button", "Link", "Image", "Navigation", "Section", "Whole page"]


def build(source_path, meta):
    src = _lib.load_json(source_path)
    by_id = {q["id"]: q for q in src["questions"]}
    missing = [qid for qid in ANSWERED + list(NOT_ANSWERED) if qid not in by_id]
    if missing:
        raise _lib.UsageError(f"{source_path}: per-website questions missing from the source: {missing}")
    extra = sorted(set(by_id) - set(ANSWERED) - set(NOT_ANSWERED))
    if extra:
        raise _lib.UsageError(f"{source_path}: new per-website questions {extra}; decide whether the skill answers them "
                              "(add them to ANSWERED or NOT_ANSWERED in this script) before syncing")
    return {
        "questionnaire_version": src["version"],
        "source": dict(meta, sha256=_lib.sha256_file(source_path),
                       description=f"{meta['repository']} pull request #{meta['pull_request']}, {meta['path']} at {meta['commit'][:7]}"),
        "_about": ("Frozen copy of the human study's per-website questions that the skill answers, copied word for word "
                   "from the study platform's questions file (see source). Do not edit by hand: rerun "
                   "scripts/sync_study_questions.py when the study changes. `options` or `rows` naming `features` refer "
                   "to the feature list below."),
        "features": src["option_lists"]["features"],
        "questions": [by_id[qid] for qid in ANSWERED],
        "not_answered": [{"id": qid, "prompt": by_id[qid]["prompt"], "reason": why} for qid, why in NOT_ANSWERED.items()],
        "mark_kinds": MARK_KINDS,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("source", help="the study platform's config/questions.json")
    for name in ("repository", "branch", "commit", "path"):
        p.add_argument(f"--{name}", required=True)
    p.add_argument("--pull-request", type=int, required=True)
    p.add_argument("--check", action="store_true", help="only compare with the frozen copy")
    a = p.parse_args(argv)
    meta = {"repository": a.repository, "pull_request": a.pull_request, "branch": a.branch, "commit": a.commit, "path": a.path}
    data = build(a.source, meta)
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if a.check:
        same = TARGET.exists() and TARGET.read_text(encoding="utf-8") == text
        print("study-questions.json matches the source" if same else "study-questions.json differs from the source; rerun without --check")
        return 0 if same else 1
    TARGET.write_text(text, encoding="utf-8")
    print(f"wrote {TARGET} ({data['questionnaire_version']}, {len(data['questions'])} questions)")
    return 0


if __name__ == "__main__":
    _lib.run_main(main)
