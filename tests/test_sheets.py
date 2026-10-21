from conftest import FULL

from aiornot.sheets import parse_spreadsheet_id, row_from_range, save_link


def finish_site(client, sid, site="alpha", answers=FULL):
    client.put(f"/api/sessions/{sid}/sites/{site}/answers", json={"answers": answers})
    client.post(f"/api/sessions/{sid}/sites/{site}/complete")


def new_session(client, pid="P01"):
    return client.post("/api/sessions", json={"participant_id": pid}).json()["id"]


def test_nothing_syncs_until_a_sheet_is_linked(client, gws):
    sid = new_session(client)
    finish_site(client, sid)
    sync = client.app_state.sync
    sync.sync_one(sid, "alpha")
    assert gws.calls == []
    assert client.app_state.db.unsynced_visits() == [(sid, "alpha")]


def test_completed_site_is_appended_then_updated_in_place(client, gws, paths):
    save_link(paths, "sheet123", "https://docs.google.com/spreadsheets/d/sheet123", "Test")
    sid = new_session(client)
    finish_site(client, sid)
    sync, db = client.app_state.sync, client.app_state.db

    sync.sync_one(sid, "alpha")
    kinds = [c[0] for c in gws.calls]
    assert kinds == ["update", "append"]  # header row, then the data row
    header = gws.calls[0][2]["values"][0]
    row = gws.calls[1][2]["values"][0]
    assert header[:3] == ["synced_at", "participant_id", "session_id"]
    assert row[header.index("participant_id")] == "P01"
    assert row[header.index("cues")] == "gradients; emoji_icons"
    assert db.unsynced_visits() == []

    # An edit after completion rewrites the same row rather than adding a new one.
    client.put(f"/api/sessions/{sid}/sites/alpha/answers", json={"answers": {"confidence": 1}})
    assert db.unsynced_visits() == [(sid, "alpha")]
    sync.sync_one(sid, "alpha")
    last = gws.calls[-1]
    assert last[0] == "update" and last[1]["range"] == "responses!A2"
    assert last[2]["values"][0][header.index("confidence")] == 1


def test_failures_are_recorded_and_left_pending(client, gws, paths):
    save_link(paths, "sheet123", "https://example", "Test")
    sid = new_session(client)
    finish_site(client, sid)
    gws.fail = True
    sync = client.app_state.sync
    try:
        sync.sync_one(sid, "alpha")
    except Exception as err:
        client.app_state.db.record_sheet_error(sid, "alpha", str(err))
    status = sync.status()
    assert status["pending"] == 1 and "network down" in status["last_error"]


def test_helpers():
    assert row_from_range("responses!A12:T12") == 12
    url = "https://docs.google.com/spreadsheets/d/1AbC-d_9/edit#gid=0"
    assert parse_spreadsheet_id(url) == "1AbC-d_9"
    assert parse_spreadsheet_id("1AbC-d_9") == "1AbC-d_9"
