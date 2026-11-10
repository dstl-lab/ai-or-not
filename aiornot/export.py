"""Turn the database into analysis-ready tables (CSV) and Google Sheet rows.

Five tables, all documented in docs/data-dictionary.md:

    responses_long   one row per participant x site x question
    responses_wide   one row per participant x site, one column per question
                     (a grid gets one column per row), plus 0/1 columns for
                     every multi-select option
    sessions         one row per session, with the background and closing answers
    marks            one row per spot a participant clicked on a website
    site_visits      one row per participant x site (timing only)
    projects         project versions, for joining an external creator survey
"""

import csv
import io
import json

from .questions import NA, SURVEY_KEYS, parse_questions

TABLES = ("responses_long", "responses_wide", "sessions", "site_visits", "projects", "marks")
SESSION_METADATA = ["cohort", "dsc106_completed", "questions_version", "sites_version"]
FOLLOWUP_TIMING = ["followup_opened_at", "followup_completed_at", "followup_seconds_on_site"]

MARK_COLUMNS = ["participant_id", "session_id", "practice", "site_position", "site_id",
                "site_title", "question_id", "mark_number", "page", "kind", "tag", "text",
                "selector", "x", "y", "box_x", "box_y", "box_w", "box_h", "scroll_y",
                "viewport_w", "viewport_h", "created_at"]

VISIT_QUERY = """
SELECT s.participant_id, v.session_id, s.practice, v.position AS site_position, v.site_id,
       v.first_opened_at, v.completed_at, ROUND(v.seconds_on_site, 1) AS seconds_on_site,
       v.followup_opened_at, v.followup_completed_at,
       ROUND(v.followup_seconds_on_site, 1) AS followup_seconds_on_site,
       v.revision
FROM site_visits v JOIN sessions s ON s.id = v.session_id
WHERE v.first_opened_at IS NOT NULL  -- sites the participant never reached aren't data
  AND (? OR s.practice = 0) AND (? IS NULL OR v.session_id = ?) AND (? IS NULL OR v.site_id = ?)
ORDER BY s.started_at, v.position
"""

RESPONSE_QUERY = """
SELECT r.session_id, r.site_id, r.question_id, r.value, r.first_answered_at, r.updated_at,
       r.times_changed
FROM responses r JOIN sessions s ON s.id = r.session_id
WHERE (? OR s.practice = 0) AND (? IS NULL OR r.session_id = ?) AND (? IS NULL OR r.site_id = ?)
"""


def display(question, value):
    """A flat, spreadsheet-friendly rendering of one answer."""
    if value is None:
        return ""
    if question is not None and question.type == "boolean":
        return "TRUE" if value else "FALSE"
    if question is not None and question.type == "annotation":
        return json.dumps(value)
    if question is not None and question.type == "marks":
        return marks_summary(value)
    if isinstance(value, list):
        return "; ".join(value) if all(isinstance(item, str) for item in value) else json.dumps(value)
    if isinstance(value, dict):
        return "; ".join(f"{k}={grid_cell(v)}" for k, v in value.items())
    return value


def grid_cell(value):
    """One grid row's answer: the number, NA for "not applicable", blank if unanswered."""
    if value is None:
        return ""
    return "NA" if value == NA else value


def marks_summary(value):
    """'none', or a short readable list like '1. Heading: Breathing Smoke | 2. Chart or graphic'."""
    if not isinstance(value, list):
        return value
    return " | ".join(
        f"{i}. {m.get('kind') or m.get('tag', '')}" + (f": {m['text'][:40]}" if m.get("text") else "")
        for i, m in enumerate(value, start=1)
    )


def marks_count(value):
    return len(value) if isinstance(value, list) else 0 if value is not None else ""


def answer_columns(questions):
    """Column names for a list of questions: grids expand to one column per row."""
    cols = []
    for q in questions:
        if q.type == "grid":
            cols += [f"{q.id}__{r.value}" for r in q.rows]
        elif q.type == "marks":
            cols += [q.id, f"{q.id}__count"]
        else:
            cols.append(q.id)
    return cols


def answer_cells(questions, values):
    row = {}
    for q in questions:
        if q.type == "grid":
            grid = values.get(q.id) or {}
            for r in q.rows:
                row[f"{q.id}__{r.value}"] = grid_cell(grid.get(r.value))
        elif q.type == "marks":
            row[q.id] = display(q, values.get(q.id))
            row[f"{q.id}__count"] = marks_count(values.get(q.id))
        else:
            row[q.id] = display(q, values.get(q.id))
    return row


class Exporter:
    def __init__(self, db, sites, questions):
        self.db = db
        self.sites = sites
        self.questions = questions

    def _snapshot(self, session, name):
        value = session.get(name)
        return json.loads(value) if isinstance(value, str) else value

    def _questions(self, session):
        snapshot = self._snapshot(session, "questions_snapshot")
        return parse_questions(snapshot) if snapshot else self.questions

    def _site(self, session, site_id):
        snapshot = self._snapshot(session, "sites_snapshot") or {}
        if site_id in snapshot:
            return snapshot[site_id]
        site = self.sites.pool.get(site_id)
        return site.__dict__ if site else {}

    def _visits(self, include_practice, session_id=None, site_id=None):
        params = (int(include_practice), session_id, session_id, site_id, site_id)
        visits = self.db.export_rows(VISIT_QUERY, params)
        answers = {}
        for r in self.db.export_rows(RESPONSE_QUERY, params):
            r["value"] = json.loads(r["value"])
            answers.setdefault((r["session_id"], r["site_id"]), {})[r["question_id"]] = r
        sessions = {s["id"]: s for s in self.db.list_sessions()}
        for v in visits:
            v["practice"] = bool(v["practice"])
            session = sessions[v["session_id"]]
            v.update({key: session.get(key) for key in SESSION_METADATA})
            v["questions"] = self._questions(session)
            followup_order = session.get("followup_order") or []
            v["followup_position"] = (followup_order.index(v["site_id"]) + 1
                                      if v["site_id"] in followup_order else None)
            site = self._site(session, v["site_id"])
            v["site_title"] = site.get("title", "")
            v["site_award"] = site.get("award") or ""
            v["site_commit"] = site.get("commit") or ""
            v["answers"] = answers.get((v["session_id"], v["site_id"]), {})
        return visits

    def wide_columns(self):
        cols = ["participant_id", "session_id", "practice", "site_position", "site_id",
                "site_title", "site_award", "first_opened_at", "completed_at", "seconds_on_site"]
        cols += answer_columns(self.questions.questions)
        cols += self.onehot_columns()
        return cols + SESSION_METADATA + ["site_commit", "followup_position"] + FOLLOWUP_TIMING

    def onehot_columns(self):
        return [f"{q.id}__{o.value}" for q in self.questions.questions
                if q.type == "multi" for o in q.options]

    def wide_row(self, visit):
        row = {k: visit[k] for k in self.wide_columns() if k in visit}
        questions = visit["questions"]
        by_id = questions.by_id
        values = {qid: a["value"] for qid, a in visit["answers"].items()}
        row.update(answer_cells(questions.questions, values))
        for q in questions.questions:
            if q.type == "multi":
                picked = values.get(q.id)
                for o in q.options:
                    row[f"{q.id}__{o.value}"] = "" if picked is None else int(o.value in picked)
        # Answers to questions that were later removed from the config still export.
        for qid, value in values.items():
            if qid not in by_id:
                row[qid] = display(None, value)
        return row

    def table(self, name, include_practice=False):
        """(columns, rows) for one export table."""
        if name == "sessions":
            rows = self.db.list_sessions()
            if not include_practice:
                rows = [r for r in rows if not r["practice"]]
            cols = ["session_id", "participant_id", "practice", "started_at", "finished_at",
                    "sites_completed", "total_seconds", "questions_version", "sites_version",
                    "user_agent", "screen", "cohort", "dsc106_completed", "sites_assigned",
                    "followup_order", "followup_started_at"]
            survey = self.questions.background + self.questions.closing
            cols += answer_columns(survey)
            for r in rows:
                r["session_id"] = r.pop("id")
                r["total_seconds"] = round(r["total_seconds"], 1)
                r["followup_order"] = json.dumps(r.get("followup_order") or [])
                answers = self.db.answers(r["session_id"])
                values = {**answers.get(SURVEY_KEYS["background"], {}),
                          **answers.get(SURVEY_KEYS["closing"], {})}
                r.update(answer_cells(survey, values))
            return cols, rows

        if name == "projects":
            cols = ["site_id", "site_title", "site_commit", "repo", "url", "sites_version"]
            projects = {(s.id, s.commit): {
                "site_id": s.id, "site_title": s.title, "site_commit": s.commit or "",
                "repo": s.repo, "url": s.url, "sites_version": self.sites.version,
            } for s in self.sites.study}
            for session in self.db.list_sessions():
                if session["practice"] and not include_practice:
                    continue
                for sid, site in (self._snapshot(session, "sites_snapshot") or {}).items():
                    projects.setdefault((sid, site.get("commit")), {
                        "site_id": sid, "site_title": site.get("title", ""),
                        "site_commit": site.get("commit") or "", "repo": site.get("repo", ""),
                        "url": site.get("url", ""), "sites_version": session["sites_version"],
                    })
            return cols, list(projects.values())

        visits = self._visits(include_practice)
        if name == "marks":
            return MARK_COLUMNS, self.mark_rows(visits)
        if name == "site_visits":
            cols = ["participant_id", "session_id", "practice", "site_position", "site_id",
                    "site_title", "site_award", "first_opened_at", "completed_at",
                    "seconds_on_site", "revision"] + SESSION_METADATA + ["site_commit", "followup_position"] + FOLLOWUP_TIMING
            return cols, visits
        if name == "responses_wide":
            rows = [self.wide_row(v) for v in visits]
            extra = sorted({k for r in rows for k in r} - set(self.wide_columns()))
            return self.wide_columns() + extra, rows
        if name == "responses_long":
            cols = ["participant_id", "session_id", "practice", "site_position", "site_id",
                    "site_title", "question_id", "question_type", "value", "value_json",
                    "first_answered_at", "updated_at", "times_changed"] + SESSION_METADATA + ["site_commit", "followup_position"]
            rows = []
            for v in visits:
                by_id = v["questions"].by_id
                order = {q.id: i for i, q in enumerate(v["questions"].questions)}
                for qid in sorted(v["answers"], key=lambda k: order.get(k, len(order))):
                    a = v["answers"][qid]
                    q = by_id.get(qid)
                    rows.append({
                        **{k: v[k] for k in cols if k in v},
                        "question_id": qid,
                        "question_type": q.type if q else "",
                        "value": display(q, a["value"]),
                        "value_json": json.dumps(a["value"]),
                        "first_answered_at": a["first_answered_at"],
                        "updated_at": a["updated_at"],
                        "times_changed": a["times_changed"],
                    })
            return cols, rows
        raise KeyError(name)

    def mark_rows(self, visits):
        marks_questions = [q for q in self.questions.questions if q.type == "marks"]
        rows = []
        for v in visits:
            for q in marks_questions:
                value = v["answers"].get(q.id, {}).get("value")
                if not isinstance(value, list):
                    continue
                for number, m in enumerate(value, start=1):
                    box = m.get("box") or {}
                    rows.append({
                        **{k: v[k] for k in MARK_COLUMNS[:6]},
                        "question_id": q.id,
                        "mark_number": number,
                        **{k: m.get(k, "") for k in ("page", "kind", "tag", "text", "selector", "x", "y",
                                                   "scroll_y", "viewport_w", "viewport_h", "created_at")},
                        **{f"box_{k}": box.get(k, "") for k in ("x", "y", "w", "h")},
                    })
        return rows

    def csv(self, name, include_practice=False):
        cols, rows = self.table(name, include_practice)
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()

    # --- Google Sheet ----------------------------------------------------

    def sheet_columns(self):
        onehot = set(self.onehot_columns())
        return ["synced_at"] + [c for c in self.wide_columns() if c not in onehot] + ["revision"]

    def sheet_row(self, session_id, site_id, synced_at):
        """(values, revision) for one participant x site, in sheet_columns() order."""
        visits = self._visits(True, session_id, site_id)
        if not visits:
            return None, None
        visit = visits[0]
        row = self.wide_row(visit)
        row["synced_at"] = synced_at
        row["practice"] = "TRUE" if visit["practice"] else "FALSE"
        row["revision"] = visit["revision"]
        values = ["" if row.get(c) is None else row.get(c, "") for c in self.sheet_columns()]
        return values, visit["revision"]
