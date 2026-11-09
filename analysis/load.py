"""Load the study database into pandas DataFrames.

    from analysis.load import load
    data = load()                 # dict of DataFrames, practice sessions excluded
    wide = data["responses_wide"] # one row per participant x site
    people = data["sessions"]     # one row per session, with background + closing answers

Run from the repo root with the analysis dependencies:
    uv run --group analysis python -i -c "from analysis.load import load; data = load()"
"""

import pandas as pd

from aiornot.config import Paths, load_sites
from aiornot.db import Database
from aiornot.export import TABLES, Exporter
from aiornot.questions import load_questions


def typed(frame, questions):
    """Give answer columns real dtypes: booleans as bool, scales and grids as numbers."""
    for q in questions:
        if q.type == "grid":
            # "NA" (not applicable) becomes NaN, so means skip it.
            cols = [f"{q.id}__{r.value}" for r in q.rows if f"{q.id}__{r.value}" in frame]
            frame[cols] = frame[cols].apply(pd.to_numeric, errors="coerce")
        elif q.id not in frame:
            continue
        elif q.type == "boolean":
            frame[q.id] = frame[q.id].map({"TRUE": True, "FALSE": False})
        elif q.type == "scale":
            frame[q.id] = pd.to_numeric(frame[q.id], errors="coerce")
        elif q.type == "multi":
            onehot = [c for c in frame.columns if c.startswith(f"{q.id}__")]
            frame[onehot] = frame[onehot].apply(pd.to_numeric, errors="coerce")


def load(include_practice=False, paths=None):
    paths = paths or Paths.default()
    questions = load_questions(paths)
    exporter = Exporter(Database(paths.db_file), load_sites(paths), questions)
    frames = {}
    for name in TABLES:
        columns, rows = exporter.table(name, include_practice)
        frames[name] = pd.DataFrame(rows, columns=columns)
    typed(frames["responses_wide"], questions.questions)
    typed(frames["sessions"], questions.background + questions.closing)
    return frames
