"""The human study's per-website questions, as the skill answers them (standard library only).

The wording lives in assets/study-questions.json, a frozen copy of the study
platform's questions (regenerate it with scripts/sync_study_questions.py).
This module loads it, renders it for the prompt and the report, and turns an
audit's `study_questionnaire` into the study export's cell format, so the
skill's answers can be read next to the participants' answers.
"""

import json

import _lib

ASSET = _lib.ASSET_DIR / "study-questions.json"
NA = "na"
# The answer object of every question carries these; the value shape depends on the question type.
SCALE_TYPES = {"scale"}


def load():
    return _lib.load_json(ASSET)


def features(study=None):
    return (study or load())["features"]


def questions(study=None):
    return (study or load())["questions"]


def question_ids(study=None):
    return [q["id"] for q in questions(study)]


def options(q, study=None):
    """The options of a single-choice question, with named option lists resolved."""
    study = study or load()
    opts = q.get("options", [])
    if isinstance(opts, str):
        opts = study[opts] if opts in study else study["option_lists"][opts]
    return list(opts) + list(q.get("extra_options", []))


def rows(q, study=None):
    study = study or load()
    r = q.get("rows", [])
    return study[r] if isinstance(r, str) and r in study else r


def label(q, value, study=None):
    """A human-readable rendering of one answer value, using the study's own labels."""
    if value is None:
        return "unassessed"
    if q["type"] == "scale":
        return f"{value} (of {q['min']}–{q['max']}: {q['min']} = {q['min_label']}, {q['max']} = {q['max_label']})"
    if q["type"] == "single":
        return next((o["label"] for o in options(q, study) if o["value"] == value), str(value))
    if q["type"] == "grid":
        return "; ".join(f"{f['label']}: {grid_cell(value.get(f['value']))}" for f in rows(q, study))
    if q["type"] == "marks":
        return marks_summary(value)
    return str(value)


def grid_cell(value):
    """The study export's grid cell: the number, NA for not applicable, blank if unanswered."""
    if value is None:
        return ""
    return "NA" if value == NA else value


def marks_summary(value):
    """'none', or '1. Heading: Breathing Smoke | 2. Chart or graphic' as in the study export."""
    if not isinstance(value, list):
        return value
    return " | ".join(f"{i}. {m.get('kind') or m.get('tag', '')}" + (f": {m['text'][:40]}" if m.get("text") else "")
                      for i, m in enumerate(value, start=1))


def marks_count(value):
    return len(value) if isinstance(value, list) else 0 if value is not None else ""


def answer_columns(study=None):
    """Wide-table answer columns in the study's order: grids expand per row, marks add a count."""
    study = study or load()
    cols = []
    for q in questions(study):
        if q["type"] == "grid":
            cols += [f"{q['id']}__{r['value']}" for r in rows(q, study)]
        elif q["type"] == "marks":
            cols += [q["id"], f"{q['id']}__count"]
        else:
            cols.append(q["id"])
    return cols


def answer_cells(answers, study=None):
    """Flatten an audit's answers into the study export's cells."""
    study = study or load()
    out = {}
    for q in questions(study):
        value = answers.get(q["id"], {}).get("value")
        if q["type"] == "grid":
            grid = value or {}
            for r in rows(q, study):
                out[f"{q['id']}__{r['value']}"] = grid_cell(grid.get(r["value"]))
        elif q["type"] == "marks":
            out[q["id"]] = "" if value is None else marks_summary(value)
            out[f"{q['id']}__count"] = marks_count(value)
        else:
            out[q["id"]] = "" if value is None else value
    return out


def render_for_prompt(study=None):
    """The questions as the auditor sees them: exact study wording, then the answer format."""
    study = study or load()
    feats = ", ".join(f"`{f['value']}` ({f['label']})" for f in features(study))
    lines = [f"Questionnaire `{study['questionnaire_version']}` (copied verbatim from the human study; "
             f"{study['source']['description']}). The feature list used by the grid and the single-choice feature "
             f"question: {feats}.", ""]
    for i, q in enumerate(questions(study), 1):
        lines.append(f"{i}. `{q['id']}` ({q['type']}): \"{q['prompt']}\"")
        if q.get("help"):
            lines.append(f"   Help shown to participants: \"{q['help']}\"")
        if q["type"] == "scale":
            lines.append(f"   Scale {q['min']}–{q['max']}: {q['min']} = \"{q['min_label']}\", {q['max']} = \"{q['max_label']}\".")
        elif q["type"] == "grid":
            lines.append(f"   One rating per feature, {q['min']}–{q['max']}: {q['min']} = \"{q['min_label']}\", {q['max']} = \"{q['max_label']}\""
                         + ("; `na` when the site does not have that feature." if q.get("allow_na") else "."))
        elif q["type"] == "single":
            lines.append("   Options: " + ", ".join(f"`{o['value']}` (\"{o['label']}\")" for o in options(q, study)) + ".")
        elif q["type"] == "marks":
            lines.append(f"   Or \"{q['none_label']}\" (value `none`). Mark kinds: " + ", ".join(study["mark_kinds"]) + ".")
    lines += ["", "Not asked of the auditor: " + "; ".join(f"`{x['id']}` ({x['reason']})" for x in study["not_answered"]) + "."]
    return "\n".join(lines)


def source_summary(study=None):
    s = (study or load())["source"]
    return json.dumps({k: s[k] for k in ("repository", "pull_request", "branch", "commit", "path")}, ensure_ascii=False)
