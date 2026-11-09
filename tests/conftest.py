import json
import shutil

import pytest
from fastapi.testclient import TestClient

from aiornot.app import create_app
from aiornot.config import ROOT, Paths

SITES = ["alpha", "beta", "gamma"]


class FakeGws:
    """Stands in for the gws CLI: records calls and fakes Sheets API replies."""

    def __init__(self):
        self.calls = []
        self.rows = 1  # row 1 is the header
        self.fail = False
        self.values = []

    def __call__(self, args, params=None, body=None):
        if self.fail:
            from aiornot.sheets import GwsError
            raise GwsError("network down")
        self.calls.append((args[-1], params, body))
        if args[-1] == "get":
            return {"values": self.values}
        if args[-1] == "update":
            row = int(params["range"].split("!A")[1])
            while len(self.values) < row:
                self.values.append([])
            self.values[row - 1] = body["values"][0]
        if args[-1] == "append":
            self.values.append(body["values"][0])
            self.rows = len(self.values)
            return {"updates": {"updatedRange": f"responses!A{self.rows}:Z{self.rows}"}}
        return {}


@pytest.fixture
def paths(tmp_path):
    config = tmp_path / "config"
    config.mkdir()
    shutil.copy(ROOT / "config" / "questions.json", config / "questions.json")
    pool = [
        {"id": sid, "title": f"Site {sid}", "url": f"https://example.github.io/{sid}/",
         "repo": f"example/{sid}", "branch": "main", "path": "/", "entry": "",
         "award": None, "commit": "abc1234"}
        for sid in SITES
    ]
    (config / "sites.json").write_text(json.dumps({"study_sites": SITES, "pool": pool}))
    mirror = tmp_path / "mirror"
    for sid in SITES:
        (mirror / sid).mkdir(parents=True)
        (mirror / sid / "index.html").write_text(f"<h1>{sid}</h1>")
        (mirror / sid / ".mirrored-commit").write_text("abc1234")
    return Paths(config_dir=config, data_dir=tmp_path / "data", mirror_dir=mirror, web_dir=ROOT / "web")


@pytest.fixture
def gws():
    return FakeGws()


@pytest.fixture
def client(paths, gws):
    app = create_app(paths, runner=gws, start_sync=False)
    with TestClient(app) as c:
        c.app_state = app.state
        yield c


# A complete, valid set of answers for one site.
FEATURES = ["color_scheme", "gradients", "typography", "emoji_icons", "buttons", "layout",
            "animations", "charts", "writing", "navigation"]
def mark(mark_id, selector="main > h1", kind="Heading", text="Breathing Smoke", **extra):
    """One clicked spot, shaped like what the study page sends."""
    return {"id": mark_id, "page": "", "selector": selector, "tag": selector.split()[-1],
            "kind": kind, "text": text, "x": 410, "y": 220,
            "box": {"x": 120, "y": 180, "w": 640, "h": 80},
            "scroll_y": 0, "viewport_w": 1060, "viewport_h": 800,
            "created_at": "2026-11-08T19:30:00.000Z", **extra}


MARKS = [mark("a1"), mark("b2", selector="#chart > svg > rect:nth-of-type(3)",
                         kind="Chart or graphic", text="", page="story.html")]

FULL = {
    "ai_marks": MARKS,
    "feature_rating": {**{f: 3 for f in FEATURES}, "gradients": 9, "emoji_icons": 8, "charts": "na"},
    "top_ai_feature": "gradients",
    "ai_extent": "most",
    "design_generic": 5,
    "writing_ai": 3,
    "polish": 4,
    "quality": 4,
    "ai_changes_view": "no_change",
    "seen_before": "no",
}

# Complete answers to the once-per-session questions.
BACKGROUND = {
    "field": "data_science",
    "phd_year": "y2",
    "build_experience": "moderate",
    "taught_course": True,
    "ai_use_code": "daily",
    "ai_use_design": "weekly",
    "can_tell_pre": 4,
    "ai_acceptable": 3,
    "ai_less_valuable": 2,
}
CLOSING = {
    "can_tell_post": 2,
    "reliable_signs": ["gradients", "writing"],
    "difficulty": 4,
    "ai_vs_human": "not_sure",
}


def survey(client, sid, part, answers):
    return client.put(f"/api/sessions/{sid}/survey/{part}/answers", json={"answers": answers})


def start(client, pid="P01", background=True, **extra):
    """Create a session; by default also answer the background questions so site 1 opens."""
    res = client.post("/api/sessions", json={"participant_id": pid, **extra})
    assert res.status_code == 201, res.text
    sid = res.json()["id"]
    if background:
        assert survey(client, sid, "background", BACKGROUND).json()["missing"] == []
    return sid
