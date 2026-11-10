from conftest import FULL

from aiornot.sheets import parse_spreadsheet_id, row_from_range, save_link
from aiornot.sheets import GwsError
import pytest


def finish_site(client, sid, answers=FULL):
    site = client.get(f"/api/sessions/{sid}").json()["sites"][0]["id"]
    assert client.put(f"/api/sessions/{sid}/sites/{site}/answers", json={"answers": answers}).status_code == 200
    assert client.post(f"/api/sessions/{sid}/sites/{site}/complete").status_code == 200
    return site


def new_session(client, pid="P01"):
    res = client.post("/api/sessions", json={"participant_id": pid, "cohort": "dsc106"})
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_nothing_syncs_until_a_sheet_is_linked(client, gws):
    sid = new_session(client)
    site = finish_site(client, sid)
    sync = client.app_state.sync
    sync.sync_one(sid, site)
    assert gws.calls == []
    assert client.app_state.db.unsynced_visits() == [(sid, site)]


def test_completed_site_is_appended_then_updated_in_place(client, gws, paths):
    save_link(paths, "sheet123", "https://docs.google.com/spreadsheets/d/sheet123", "Test")
    sid = new_session(client)
    site = finish_site(client, sid)
    sync, db = client.app_state.sync, client.app_state.db

    sync.sync_one(sid, site)
    kinds = [c[0] for c in gws.calls]
    assert kinds == ["get", "update", "append"]  # inspect before writing the header or data
    header = gws.calls[1][2]["values"][0]
    row = gws.calls[2][2]["values"][0]
    assert header[:3] == ["synced_at", "participant_id", "session_id"]
    assert row[header.index("participant_id")] == "P01"
    assert row[header.index("cues")] == "gradients; emoji_icons"
    assert db.unsynced_visits() == []

    # An edit after completion rewrites the same row rather than adding a new one.
    client.put(f"/api/sessions/{sid}/sites/{site}/answers", json={"answers": {"confidence": 1}})
    assert db.unsynced_visits() == [(sid, site)]
    sync.sync_one(sid, site)
    last = gws.calls[-1]
    assert last[0] == "update" and last[1]["range"] == "responses!A2"
    assert last[2]["values"][0][header.index("confidence")] == 1


def test_failures_are_recorded_and_left_pending(client, gws, paths):
    save_link(paths, "sheet123", "https://example", "Test")
    sid = new_session(client)
    site = finish_site(client, sid)
    gws.fail = True
    sync = client.app_state.sync
    try:
        sync.sync_one(sid, site)
    except Exception as err:
        client.app_state.db.record_sheet_error(sid, site, str(err))
    status = sync.status()
    assert status["pending"] == 1 and "network down" in status["last_error"]


def test_helpers():
    assert row_from_range("responses!A12:T12") == 12
    url = "https://docs.google.com/spreadsheets/d/1AbC-d_9/edit#gid=0"
    assert parse_spreadsheet_id(url) == "1AbC-d_9"
    assert parse_spreadsheet_id("1AbC-d_9") == "1AbC-d_9"


def test_sync_finds_row_after_rows_move(client, gws, paths):
    save_link(paths, "sheet123", "https://example", "Test")
    sid = new_session(client)
    site = finish_site(client, sid)
    sync = client.app_state.sync
    sync.sync_one(sid, site)
    other = list(gws.values[1])
    other[2] = "another-session"
    gws.values.insert(1, other)
    client.put(f"/api/sessions/{sid}/sites/{site}/answers", json={"answers": {"confidence": 1}})
    sync.sync_one(sid, site)
    assert gws.calls[-1][1]["range"] == "responses!A3"
    assert gws.values[1] == other
    assert client.app_state.db.sheet_row(sid, site)["row_number"] == 3


def test_sync_to_new_sheet_does_not_reuse_old_row(client, gws, paths):
    save_link(paths, "old", "https://example", "Old")
    sid = new_session(client)
    site = finish_site(client, sid)
    sync = client.app_state.sync
    sync.sync_one(sid, site)
    save_link(paths, "new", "https://example", "New")
    gws.values = []
    sync.sync_one(sid, site)
    assert gws.calls[-1][0] == "append"


def test_incompatible_sheet_header_is_not_overwritten(client, gws, paths):
    save_link(paths, "sheet123", "https://example", "Test")
    sid = new_session(client)
    site = finish_site(client, sid)
    gws.values = [["old_question", "participant_id"], ["saved answer", "P99"]]
    original = [row[:] for row in gws.values]
    with pytest.raises(GwsError, match="columns"):
        client.app_state.sync.sync_one(sid, site)
    assert gws.values == original
