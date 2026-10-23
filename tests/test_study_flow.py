import csv
import io

from conftest import FULL, SITES


def start(client, pid="P01", **extra):
    res = client.post("/api/sessions", json={"participant_id": pid, **extra})
    assert res.status_code == 201, res.text
    return res.json()["id"]


def answer(client, sid, site, answers):
    return client.put(f"/api/sessions/{sid}/sites/{site}/answers", json={"answers": answers})


def complete(client, sid, site):
    return client.post(f"/api/sessions/{sid}/sites/{site}/complete")


def test_pages_and_sites_are_served(client):
    assert client.get("/").status_code == 200
    assert client.get("/admin").status_code == 200
    assert "<h1>alpha</h1>" in client.get("/sites/alpha/").text


def test_session_starts_on_first_site_with_later_sites_locked(client):
    sid = start(client)
    data = client.get(f"/api/sessions/{sid}").json()
    assert [s["id"] for s in data["sites"]] == SITES
    assert [s["unlocked"] for s in data["sites"]] == [True, False, False]
    assert data["sites"][0]["label"] == "Website 1 of 3"
    assert len(data["questions"]) == 9


def test_participant_ids_are_validated_and_duplicates_need_confirmation(client):
    assert client.post("/api/sessions", json={"participant_id": "bad id!"}).status_code == 422
    start(client, "P02")
    assert client.post("/api/sessions", json={"participant_id": "P02"}).status_code == 409
    start(client, "P02", allow_duplicate=True)
    start(client, "P02", practice=True)  # practice runs never conflict


def test_cannot_complete_a_site_with_missing_answers(client):
    sid = start(client)
    res = answer(client, sid, "alpha", {"ai_generated": True})
    assert "confidence" in res.json()["missing"]
    res = complete(client, sid, "alpha")
    assert res.status_code == 422
    assert "confidence" in res.json()["detail"]["missing"]


def test_later_sites_unlock_only_after_completion(client):
    sid = start(client)
    assert answer(client, sid, "beta", FULL).status_code == 409
    assert answer(client, sid, "alpha", FULL).json()["missing"] == []
    assert complete(client, sid, "alpha").status_code == 200
    assert answer(client, sid, "beta", FULL).status_code == 200


def test_invalid_answers_are_rejected(client):
    sid = start(client)
    for bad in ({"confidence": 9}, {"ai_generated": "yes"}, {"cues": ["not_an_option"]},
                {"ai_extent": "lots"}, {"made_up_question": 1}):
        assert answer(client, sid, "alpha", bad).status_code == 422, bad


def test_strongest_cue_must_be_one_of_the_selected_cues(client):
    sid = start(client)
    answers = {**FULL, "strongest_cue": "typography"}  # valid option, but not ticked in cues
    assert "strongest_cue" in answer(client, sid, "alpha", answers).json()["missing"]


def test_editing_a_completed_site_keeps_history(client):
    sid = start(client)
    answer(client, sid, "alpha", FULL)
    complete(client, sid, "alpha")
    answer(client, sid, "alpha", {**FULL, "confidence": 2})
    db = client.app_state.db
    assert db.answers(sid)["alpha"]["confidence"] == 2
    history = db.export_rows(
        "SELECT value FROM response_history WHERE session_id = ? AND question_id = 'confidence'", (sid,))
    assert [h["value"] for h in history] == ["4", "2"]


def test_full_session_and_exports(client):
    sid = start(client)
    for site in SITES:
        answer(client, sid, site, FULL)
        client.post(f"/api/sessions/{sid}/sites/{site}/time", json={"seconds": 240})
        assert complete(client, sid, site).status_code == 200
    assert client.post(f"/api/sessions/{sid}/finish").status_code == 200
    assert answer(client, sid, "alpha", FULL).status_code == 409  # finished sessions are locked

    wide = list(csv.DictReader(io.StringIO(client.get("/api/export/responses_wide.csv").text)))
    assert len(wide) == 3
    row = wide[0]
    assert row["participant_id"] == "P01"
    assert row["ai_generated"] == "TRUE"
    assert row["cues"] == "gradients; emoji_icons"
    assert row["cues__gradients"] == "1" and row["cues__color_scheme"] == "0"
    assert float(row["seconds_on_site"]) == 240

    long = list(csv.DictReader(io.StringIO(client.get("/api/export/responses_long.csv").text)))
    assert len(long) == 3 * len(FULL)

    sessions = list(csv.DictReader(io.StringIO(client.get("/api/export/sessions.csv").text)))
    assert sessions[0]["sites_completed"] == "3" and sessions[0]["finished_at"]


def test_practice_sessions_are_excluded_from_exports_by_default(client):
    sid = start(client, "PRACTICE", practice=True)
    answer(client, sid, "alpha", FULL)
    complete(client, sid, "alpha")
    assert len(client.get("/api/export/responses_wide.csv").text.strip().splitlines()) == 1
    assert len(client.get("/api/export/responses_wide.csv?practice=true").text.strip().splitlines()) == 2


def test_finish_revalidates_previously_completed_answers(client):
    sid = start(client)
    for site in SITES:
        answer(client, sid, site, FULL)
        complete(client, sid, site)
    answer(client, sid, "alpha", {"confidence": None})
    assert client.post(f"/api/sessions/{sid}/finish").status_code == 422
    assert client.app_state.db.get_session(sid)["finished_at"] is None
    answer(client, sid, "alpha", {"confidence": 4})
    assert client.post(f"/api/sessions/{sid}/finish").status_code == 200
