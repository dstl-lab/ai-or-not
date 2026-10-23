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
FULL = {
    "ai_generated": True,
    "confidence": 4,
    "ai_extent": "most",
    "cues": ["gradients", "emoji_icons"],
    "strongest_cue": "gradients",
    "design_generic": 5,
    "writing_ai": 3,
    "polish": 4,
    "seen_before": "no",
}
