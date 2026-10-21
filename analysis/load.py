"""Load the study database into pandas DataFrames.

    from analysis.load import load
    data = load()                 # dict of DataFrames, practice sessions excluded
    wide = data["responses_wide"] # one row per participant x site

Run from the repo root with the analysis dependencies:
    uv run --group analysis python -i -c "from analysis.load import load; data = load()"
"""

import pandas as pd

from aiornot.config import Paths, load_sites
from aiornot.db import Database
from aiornot.export import TABLES, Exporter
from aiornot.questions import load_questions


def load(include_practice=False, paths=None):
    paths = paths or Paths.default()
    questions = load_questions(paths)
    exporter = Exporter(Database(paths.db_file), load_sites(paths), questions)
    frames = {}
    for name in TABLES:
        columns, rows = exporter.table(name, include_practice)
        frames[name] = pd.DataFrame(rows, columns=columns)

    # Give answer columns real dtypes: booleans as bool, scales as numbers.
    wide = frames["responses_wide"]
    for q in questions.questions:
        if q.id not in wide:
            continue
        if q.type == "boolean":
            wide[q.id] = wide[q.id].map({"TRUE": True, "FALSE": False})
        elif q.type == "scale":
            wide[q.id] = pd.to_numeric(wide[q.id], errors="coerce")
        elif q.type == "multi":
            onehot = [c for c in wide.columns if c.startswith(f"{q.id}__")]
            wide[onehot] = wide[onehot].apply(pd.to_numeric, errors="coerce")
    return frames
