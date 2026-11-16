#!/usr/bin/env python3
"""Export an audit's answers to the human study's questions as CSV files in the study's own column layout.

    python scripts/export_study_csv.py AUDIT.json --bundle BUNDLE --out DIR
    python scripts/export_study_csv.py AUDIT.json --bundle BUNDLE --out DIR --append --site-id breathing-smoke --rater "anthropic/claude-opus-5-5"

Writes, in DIR:
  responses_wide.csv         one row per audited site and stage: `evidence_phase` is "tour" for the answers formed
                             from the frozen tour (identical evidence for every model) and "explored" for the answers
                             after the live exploration, when the audit has one. The answer columns use the study export's names and
                             cell formats (feature_rating__<feature> with NA, ai_marks summary and ai_marks__count,
                             stored option values), so the row can sit next to the participants' rows.
  marks.csv                  one row per marked spot, in the study's marks.csv columns.
  questionnaire_reasons.csv  every answer's reason and the evidence ids it rests on (not part of the study export).

Study columns the skill has no value for (timing, practice, award) are left blank; a few skill columns
(rater, audit_id, bundle_id, bundle_hash, analysis_profile, site_url, evidence_phase, exploration_id) are added at
the end, and marks.csv and questionnaire_reasons.csv end with evidence_phase. With --append, rows
are added to existing files with the same header, so several sites end up in one table. Only audits that pass
validate_audit.py are exported.
"""

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import questionnaire  # noqa: E402
import validate_audit  # noqa: E402

LEAD = ["participant_id", "session_id", "practice", "site_position", "site_id", "site_title", "site_award",
        "first_opened_at", "completed_at", "seconds_on_site"]
TRAIL = ["questions_version", "site_commit"]
SKILL_COLS = ["rater", "audit_id", "bundle_id", "bundle_hash", "analysis_profile", "site_url", "evidence_phase", "exploration_id"]
MARK_COLUMNS = ["participant_id", "session_id", "practice", "site_position", "site_id", "site_title", "question_id",
                "mark_number", "page", "kind", "tag", "text", "selector", "x", "y", "box_x", "box_y", "box_w", "box_h",
                "scroll_y", "viewport_w", "viewport_h", "created_at", "evidence_phase"]
REASON_COLUMNS = ["participant_id", "session_id", "site_id", "question_id", "item", "value", "reason", "rests_on", "evidence_phase"]


def wide_columns():
    return LEAD + questionnaire.answer_columns() + TRAIL + SKILL_COLS


def refs(items):
    return "; ".join(f"{r['kind']}:{r['id']}" for r in items)


def rows_for(audit, bundle, participant_id, site_id, site_title, rater, sq=None, phase="tour", exploration_id=""):
    sq = sq if sq is not None else audit["study_questionnaire"]
    answers = sq["answers"]
    m = bundle.manifest
    ident = {"participant_id": participant_id, "session_id": audit["audit_id"], "practice": "", "site_position": "",
             "site_id": site_id, "site_title": site_title}
    wide = {c: "" for c in wide_columns()}
    wide.update(ident)
    wide.update(questionnaire.answer_cells(answers))
    wide.update({"questions_version": sq["questionnaire_version"], "site_commit": m["capture"].get("snapshot_id") or "",
                 "rater": rater, "audit_id": audit["audit_id"], "bundle_id": audit["bundle_id"], "bundle_hash": audit["bundle_hash"],
                 "analysis_profile": audit["analysis_profile"], "site_url": m["capture"].get("target_locator") or "",
                 "evidence_phase": phase, "exploration_id": exploration_id})
    first_route = m["states"][0]["route"] if m["states"] else ""
    marks = answers["ai_marks"]["value"] if isinstance(answers["ai_marks"]["value"], list) else []
    mark_rows = [dict({c: "" for c in MARK_COLUMNS}, **{k: ident[k] for k in MARK_COLUMNS[:6]}, question_id="ai_marks",
                      mark_number=mk["mark_number"], page="" if mk["page"] == first_route else mk["page"],
                      kind=mk["kind"], tag=mk["tag"], text=mk["text"], selector=mk["selector"], evidence_phase=phase) for mk in marks]
    base = {"participant_id": participant_id, "session_id": audit["audit_id"], "site_id": site_id, "evidence_phase": phase}
    reasons = []
    for q in questionnaire.questions():
        a = answers[q["id"]]
        if q["type"] == "grid":
            shown = "; ".join(f"{r['value']}={questionnaire.grid_cell(a['value'].get(r['value']))}" for r in questionnaire.rows(q))
        else:
            shown = questionnaire.answer_cells({q["id"]: a})[q["id"]]
        reasons.append(dict(base, question_id=q["id"], item="", value=shown, reason=a["reason"], rests_on=refs(a["refs"])))
        if q["type"] == "grid":
            grid = a["value"]
            reasons += [dict(base, question_id=q["id"], item=r["feature"], value=questionnaire.grid_cell(grid[r["feature"]]),
                             reason=r["reason"], rests_on=refs(r["refs"])) for r in a["rows"]]
        if q["type"] == "marks":
            reasons += [dict(base, question_id=q["id"], item=mk["mark_number"], value=mk["selector"], reason=mk["reason"],
                             rests_on=refs(mk["refs"])) for mk in marks]
    return wide, mark_rows, reasons


def write(path, columns, rows, append):
    exists = path.exists() and path.stat().st_size > 0
    if append and exists:
        with path.open(newline="", encoding="utf-8") as fh:
            header = next(csv.reader(fh), [])
        if header != columns:
            raise _lib.UsageError(f"{path} has a different header; write to a new folder instead of appending")
    with path.open("a" if append and exists else "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=columns)
        if not (append and exists):
            w.writeheader()
        w.writerows(rows)


def export(audit_path, bundle_dir, out_dir, participant_id=None, site_id=None, site_title="", rater="", append=False, exploration_dir=None):
    report = validate_audit.validate(audit_path, bundle_dir, exploration_dir)
    if not report.ok:
        report.print(sys.stderr)
        raise _lib.UsageError("the audit does not validate; fix it before exporting")
    audit = _lib.load_json(audit_path)
    if "study_questionnaire" not in audit:
        raise _lib.UsageError("the audit has no study_questionnaire to export")
    bundle = _lib.Bundle(bundle_dir)
    participant_id = participant_id or ("website-slop-audit" + (f":{rater}" if rater else ""))
    site = site_id or bundle.manifest["site_id"]
    wide, marks, reasons = rows_for(audit, bundle, participant_id, site, site_title, rater)
    wides = [wide]
    st = audit.get("exploration_stage")
    if st and st["status"] == "completed" and st.get("study_questionnaire"):
        w2, m2, r2 = rows_for(audit, bundle, participant_id, site, site_title, rater, st["study_questionnaire"], "explored", st["exploration_id"] or "")
        wides.append(w2)
        marks, reasons = marks + m2, reasons + r2
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write(out / "responses_wide.csv", wide_columns(), wides, append)
    write(out / "marks.csv", MARK_COLUMNS, marks, append)
    write(out / "questionnaire_reasons.csv", REASON_COLUMNS, reasons, append)
    return out, wides, marks, reasons


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("audit")
    p.add_argument("--bundle", required=True)
    p.add_argument("--out", required=True, help="folder for the CSV files")
    p.add_argument("--participant-id", help="the rater's id in the participant_id column (default website-slop-audit[:RATER])")
    p.add_argument("--site-id", help="the study's project id for this site (default: the bundle's site_id)")
    p.add_argument("--site-title", default="")
    p.add_argument("--rater", default="", help="model or system that wrote the audit, e.g. anthropic/claude-opus-5-5")
    p.add_argument("--append", action="store_true", help="add rows to existing files instead of replacing them")
    p.add_argument("--exploration", help="the exploration folder (default: 'exploration' next to the audit)")
    a = p.parse_args(argv)
    out, wides, marks, reasons = export(a.audit, a.bundle, a.out, a.participant_id, a.site_id, a.site_title, a.rater, a.append, a.exploration)
    phases = ", ".join(w["evidence_phase"] for w in wides)
    print(f"wrote {out}/responses_wide.csv ({len(wides)} row(s): {phases}), marks.csv ({len(marks)} mark(s)), questionnaire_reasons.csv ({len(reasons)} rows)")
    return 0


if __name__ == "__main__":
    _lib.run_main(main)
