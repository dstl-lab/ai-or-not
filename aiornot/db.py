"""SQLite storage. The database file is the source of truth for all study data.

Values are stored as JSON text so every question type (bool, int, str, list)
round-trips exactly. Each table is documented in docs/data-dictionary.md.
"""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from .questions import is_blank

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id                TEXT PRIMARY KEY,
    participant_id    TEXT NOT NULL,
    practice          INTEGER NOT NULL DEFAULT 0,
    started_at        TEXT NOT NULL,
    finished_at       TEXT,
    site_order        TEXT NOT NULL,
    questions_version TEXT NOT NULL,
    sites_version     TEXT NOT NULL,
    user_agent        TEXT,
    screen            TEXT
);
CREATE INDEX IF NOT EXISTS sessions_participant ON sessions(participant_id);

CREATE TABLE IF NOT EXISTS site_visits (
    session_id      TEXT NOT NULL REFERENCES sessions(id),
    site_id         TEXT NOT NULL,
    position        INTEGER NOT NULL,
    first_opened_at TEXT,
    completed_at    TEXT,
    seconds_on_site REAL NOT NULL DEFAULT 0,
    revision        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (session_id, site_id)
);

CREATE TABLE IF NOT EXISTS responses (
    session_id        TEXT NOT NULL REFERENCES sessions(id),
    site_id           TEXT NOT NULL,
    question_id       TEXT NOT NULL,
    value             TEXT NOT NULL,
    first_answered_at TEXT NOT NULL,
    updated_at        TEXT NOT NULL,
    times_changed     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (session_id, site_id, question_id)
);

CREATE TABLE IF NOT EXISTS response_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    site_id     TEXT NOT NULL,
    question_id TEXT NOT NULL,
    value       TEXT,
    recorded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sheet_rows (
    session_id      TEXT NOT NULL REFERENCES sessions(id),
    site_id         TEXT NOT NULL,
    row_number      INTEGER,
    synced_revision INTEGER,
    synced_at       TEXT,
    last_error      TEXT,
    last_attempt_at TEXT,
    PRIMARY KEY (session_id, site_id)
);
"""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class Database:
    def __init__(self, path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            with conn:  # commits on success, rolls back on error
                yield conn
        finally:
            conn.close()

    # --- sessions -------------------------------------------------------

    def create_session(self, participant_id, practice, site_ids, questions_version,
                       sites_version, user_agent=None, screen=None):
        session_id = uuid.uuid4().hex[:12]
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO sessions (id, participant_id, practice, started_at, site_order,"
                " questions_version, sites_version, user_agent, screen)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (session_id, participant_id, int(practice), now(), json.dumps(site_ids),
                 questions_version, sites_version, user_agent, screen),
            )
            conn.executemany(
                "INSERT INTO site_visits (session_id, site_id, position) VALUES (?, ?, ?)",
                [(session_id, sid, i) for i, sid in enumerate(site_ids, start=1)],
            )
        return session_id

    def participant_has_session(self, participant_id):
        with self.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM sessions WHERE participant_id = ? AND practice = 0 LIMIT 1",
                (participant_id,),
            ).fetchone()
        return row is not None

    def get_session(self, session_id):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return session_dict(row) if row else None

    def list_sessions(self):
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT s.*,"
                " (SELECT COUNT(*) FROM site_visits v WHERE v.session_id = s.id"
                "   AND v.completed_at IS NOT NULL) AS sites_completed,"
                " (SELECT COALESCE(SUM(seconds_on_site), 0) FROM site_visits v"
                "   WHERE v.session_id = s.id) AS total_seconds"
                " FROM sessions s ORDER BY s.started_at DESC"
            ).fetchall()
        return [session_dict(r) for r in rows]

    def set_practice(self, session_id, practice):
        with self.connect() as conn:
            conn.execute("UPDATE sessions SET practice = ? WHERE id = ?", (int(practice), session_id))
            # Synced Sheet rows carry the practice flag, so mark them for re-sync.
            conn.execute("UPDATE site_visits SET revision = revision + 1 WHERE session_id = ?",
                         (session_id,))

    def finish_session(self, session_id):
        with self.connect() as conn:
            conn.execute(
                "UPDATE sessions SET finished_at = COALESCE(finished_at, ?) WHERE id = ?",
                (now(), session_id),
            )

    # --- site visits ----------------------------------------------------

    def visits(self, session_id):
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM site_visits WHERE session_id = ? ORDER BY position", (session_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def mark_opened(self, session_id, site_id):
        with self.connect() as conn:
            conn.execute(
                "UPDATE site_visits SET first_opened_at = COALESCE(first_opened_at, ?)"
                " WHERE session_id = ? AND site_id = ?",
                (now(), session_id, site_id),
            )

    def add_time(self, session_id, site_id, seconds):
        with self.connect() as conn:
            conn.execute(
                "UPDATE site_visits SET seconds_on_site = seconds_on_site + ?"
                " WHERE session_id = ? AND site_id = ?",
                (seconds, session_id, site_id),
            )

    def complete_site(self, session_id, site_id):
        with self.connect() as conn:
            conn.execute(
                "UPDATE site_visits SET completed_at = COALESCE(completed_at, ?)"
                " WHERE session_id = ? AND site_id = ?",
                (now(), session_id, site_id),
            )

    # --- answers --------------------------------------------------------

    def answers(self, session_id):
        """{site_id: {question_id: value}} with the latest value of every answer."""
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT site_id, question_id, value FROM responses WHERE session_id = ?",
                (session_id,),
            ).fetchall()
        out = {}
        for r in rows:
            out.setdefault(r["site_id"], {})[r["question_id"]] = json.loads(r["value"])
        return out

    def save_answers(self, session_id, site_id, answers):
        """Upsert the given answers (None/[] clears one). Returns True if anything changed."""
        stamp = now()
        changed = False
        with self.connect() as conn:
            existing = {
                r["question_id"]: json.loads(r["value"])
                for r in conn.execute(
                    "SELECT question_id, value FROM responses WHERE session_id = ? AND site_id = ?",
                    (session_id, site_id),
                )
            }
            for qid, value in answers.items():
                old = existing.get(qid)
                if is_blank(value):
                    if qid not in existing:
                        continue
                    conn.execute(
                        "DELETE FROM responses WHERE session_id = ? AND site_id = ? AND question_id = ?",
                        (session_id, site_id, qid),
                    )
                    encoded = None
                elif qid in existing and old == value:
                    continue
                else:
                    encoded = json.dumps(value)
                    conn.execute(
                        "INSERT INTO responses (session_id, site_id, question_id, value,"
                        " first_answered_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)"
                        " ON CONFLICT (session_id, site_id, question_id) DO UPDATE SET"
                        " value = excluded.value, updated_at = excluded.updated_at,"
                        " times_changed = times_changed + 1",
                        (session_id, site_id, qid, encoded, stamp, stamp),
                    )
                conn.execute(
                    "INSERT INTO response_history (session_id, site_id, question_id, value, recorded_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (session_id, site_id, qid, encoded, stamp),
                )
                changed = True
            if changed:
                conn.execute(
                    "UPDATE site_visits SET revision = revision + 1,"
                    " first_opened_at = COALESCE(first_opened_at, ?)"
                    " WHERE session_id = ? AND site_id = ?",
                    (stamp, session_id, site_id),
                )
        return changed

    # --- Google Sheet sync bookkeeping ---------------------------------

    def unsynced_visits(self):
        """Completed site visits whose latest answers are not yet in the Sheet."""
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT v.session_id, v.site_id FROM site_visits v"
                " LEFT JOIN sheet_rows r ON r.session_id = v.session_id AND r.site_id = v.site_id"
                " WHERE v.completed_at IS NOT NULL"
                " AND (r.synced_revision IS NULL OR r.synced_revision < v.revision)"
                " ORDER BY v.session_id, v.position"
            ).fetchall()
        return [(r["session_id"], r["site_id"]) for r in rows]

    def sheet_row(self, session_id, site_id):
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM sheet_rows WHERE session_id = ? AND site_id = ?",
                (session_id, site_id),
            ).fetchone()
        return dict(row) if row else None

    def record_sheet_sync(self, session_id, site_id, row_number, revision):
        stamp = now()
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO sheet_rows (session_id, site_id, row_number, synced_revision,"
                " synced_at, last_error, last_attempt_at) VALUES (?, ?, ?, ?, ?, NULL, ?)"
                " ON CONFLICT (session_id, site_id) DO UPDATE SET row_number = excluded.row_number,"
                " synced_revision = excluded.synced_revision, synced_at = excluded.synced_at,"
                " last_error = NULL, last_attempt_at = excluded.last_attempt_at",
                (session_id, site_id, row_number, revision, stamp, stamp),
            )

    def record_sheet_error(self, session_id, site_id, error):
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO sheet_rows (session_id, site_id, last_error, last_attempt_at)"
                " VALUES (?, ?, ?, ?) ON CONFLICT (session_id, site_id) DO UPDATE SET"
                " last_error = excluded.last_error, last_attempt_at = excluded.last_attempt_at",
                (session_id, site_id, error, now()),
            )

    def sheet_summary(self):
        with self.connect() as conn:
            synced = conn.execute(
                "SELECT COUNT(*) AS n, MAX(synced_at) AS last FROM sheet_rows"
                " WHERE synced_revision IS NOT NULL"
            ).fetchone()
            error = conn.execute(
                "SELECT last_error, last_attempt_at FROM sheet_rows WHERE last_error IS NOT NULL"
                " ORDER BY last_attempt_at DESC LIMIT 1"
            ).fetchone()
        return {
            "rows_synced": synced["n"],
            "last_synced_at": synced["last"],
            "pending": len(self.unsynced_visits()),
            "last_error": error["last_error"] if error else None,
            "last_error_at": error["last_attempt_at"] if error else None,
        }

    # --- exports --------------------------------------------------------

    def export_rows(self, query, params=()):
        with self.connect() as conn:
            return [dict(r) for r in conn.execute(query, params).fetchall()]


def session_dict(row):
    data = dict(row)
    data["practice"] = bool(data["practice"])
    data["site_order"] = json.loads(data["site_order"])
    return data
