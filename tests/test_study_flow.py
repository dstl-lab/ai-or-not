import csv
import io

from conftest import BACKGROUND, CLOSING, FOLLOWUP, FULL, MARKS, SITES, mark, start, survey


def assigned_sites(client, sid):
    return [s["id"] for s in client.get(f"/api/sessions/{sid}").json()["sites"]]


def answer(client, sid, site, answers):
    return client.put(f"/api/sessions/{sid}/sites/{site}/answers", json={"answers": answers})


def complete(client, sid, site):
    return client.post(f"/api/sessions/{sid}/sites/{site}/complete")


def finish_all_sites(client, sid):
    for site in assigned_sites(client, sid):
        assert answer(client, sid, site, FULL).status_code == 200
        assert complete(client, sid, site).status_code == 200


def finish_followup(client, sid):
    assert client.post(f"/api/sessions/{sid}/followup").status_code == 200
    data = client.get(f"/api/sessions/{sid}").json()
    assert data["phase"] == "followup"
    for site in data["followup_sites"]:
        assert answer(client, sid, site["id"], FOLLOWUP).status_code == 200
        assert complete(client, sid, site["id"]).status_code == 200


def test_pages_and_sites_are_served(client):
    assert client.get("/").status_code == 200
    assert client.get("/admin").status_code == 200
    assert "<h1>alpha</h1>" in client.get("/sites/alpha/").text


def test_session_starts_on_first_site_with_later_sites_locked(client):
    sid = start(client)
    data = client.get(f"/api/sessions/{sid}").json()
    assert {s["id"] for s in data["sites"]} == set(SITES)
    assert [s["unlocked"] for s in data["sites"]] == [True, False, False]
    assert data["sites"][0]["label"] == "Website 1 of 3"
    assert len(data["questions"]) == len(FULL)
    assert len(data["background"]) == len(BACKGROUND)
    assert len(data["closing"]) == len(CLOSING)


def test_websites_stay_locked_until_background_is_answered(client):
    sid = start(client, background=False)
    data = client.get(f"/api/sessions/{sid}").json()
    assert not data["sites"][0]["unlocked"]
    assert answer(client, sid, "alpha", FULL).status_code == 409
    partial = {k: v for k, v in BACKGROUND.items() if k != "phd_year"}
    assert survey(client, sid, "background", partial).json()["missing"] == ["phd_year"]
    assert survey(client, sid, "background", BACKGROUND).json()["missing"] == []
    first = assigned_sites(client, sid)[0]
    assert answer(client, sid, first, FULL).status_code == 200


def test_survey_answers_are_validated_per_section(client):
    sid = start(client, background=False)
    assert survey(client, sid, "background", {"polish": 3}).status_code == 422  # a site question
    assert survey(client, sid, "background", {"phd_year": "y9"}).status_code == 422
    assert survey(client, sid, "nonsense", {}).status_code == 404


def test_shared_feature_list_is_used_everywhere(client):
    sid = start(client)
    data = client.get(f"/api/sessions/{sid}").json()
    by_id = {q["id"]: q for q in data["questions"] + data["closing"]}
    rows = [r["value"] for r in by_id["feature_rating"]["rows"]]
    assert [o["value"] for o in by_id["top_ai_feature"]["options"]] == rows + ["none"]
    assert [o["value"] for o in by_id["reliable_signs"]["options"]] == rows


def test_participant_ids_are_validated_and_duplicates_need_confirmation(client):
    assert client.post("/api/sessions", json={"participant_id": "bad id!", "cohort": "dsc106"}).status_code == 422
    start(client, "P02")
    assert client.post("/api/sessions", json={"participant_id": "P02", "cohort": "dsc106"}).status_code == 409
    start(client, "P02", allow_duplicate=True)
    start(client, "P02", practice=True)  # practice runs never conflict


def test_cannot_complete_a_site_with_missing_answers(client):
    sid = start(client)
    first = assigned_sites(client, sid)[0]
    res = answer(client, sid, first, {"ai_marks": MARKS})
    assert "feature_rating" in res.json()["missing"]
    res = complete(client, sid, first)
    assert res.status_code == 422
    assert "feature_rating" in res.json()["detail"]["missing"]


def test_grid_needs_every_row_and_accepts_na(client):
    sid = start(client)
    first = assigned_sites(client, sid)[0]
    partial = {k: v for k, v in FULL["feature_rating"].items() if k != "writing"}
    res = answer(client, sid, first, {**FULL, "feature_rating": partial})
    assert res.json()["missing"] == ["feature_rating"]
    assert answer(client, sid, first, FULL).json()["missing"] == []
    assert client.app_state.db.answers(sid)[first]["feature_rating"]["charts"] == "na"


def test_later_sites_unlock_only_after_completion(client):
    sid = start(client)
    first, second, _ = assigned_sites(client, sid)
    assert answer(client, sid, second, FULL).status_code == 409
    assert answer(client, sid, first, FULL).json()["missing"] == []
    assert complete(client, sid, first).status_code == 200
    assert answer(client, sid, second, FULL).status_code == 200


def test_invalid_answers_are_rejected(client):
    sid = start(client)
    first = assigned_sites(client, sid)[0]
    for bad in ({"ai_appearance": 9}, {"polish": 9},
                {"top_ai_feature": "not_an_option"}, {"ai_extent": "lots"},
                {"made_up_question": 1}, {"field": "cs"},  # background question on a site
                {"feature_rating": {"gradients": 11}}, {"feature_rating": {"gradients": True}},
                {"feature_rating": {"not_a_feature": 3}}, {"feature_rating": [3]}):
        expected = {409, 422} if "field" in bad else {422}
        assert answer(client, sid, first, bad).status_code in expected, bad


def test_marks_accept_any_number_of_clicks_or_none(client):
    sid = start(client)
    first = assigned_sites(client, sid)[0]
    many = [mark(f"m{i}") for i in range(25)]
    assert answer(client, sid, first, {**FULL, "ai_marks": many}).json()["missing"] == []
    assert answer(client, sid, first, {**FULL, "ai_marks": "none"}).json()["missing"] == []
    res = answer(client, sid, first, {"ai_marks": None})
    assert res.json()["missing"] == ["ai_marks"]


def test_malformed_marks_are_rejected(client):
    sid = start(client)
    first = assigned_sites(client, sid)[0]
    for bad in ("nothing", [{"id": "a1"}],                       # no selector
                [mark("a1"), mark("a1")],                        # repeated id
                [mark("a1", x="far left")],                      # wrong type
                [mark("a1", secret="extra field")],              # unknown field
                [mark("a1", box={"x": 1})],                      # incomplete box
                [mark(str(i)) for i in range(201)]):             # unreasonably many
        assert answer(client, sid, first, {"ai_marks": bad}).status_code == 422, bad


def test_editing_a_completed_site_keeps_history(client):
    sid = start(client)
    first = assigned_sites(client, sid)[0]
    answer(client, sid, first, FULL)
    complete(client, sid, first)
    answer(client, sid, first, {**FULL, "polish": 2})
    db = client.app_state.db
    assert db.answers(sid)[first]["polish"] == 2
    history = db.export_rows(
        "SELECT value FROM response_history WHERE session_id = ? AND question_id = 'polish'", (sid,))
    assert [h["value"] for h in history] == ["4", "2"]


def test_closing_opens_after_last_site_and_is_needed_to_finish(client):
    sid = start(client)
    assert survey(client, sid, "closing", CLOSING).status_code == 409  # websites not done
    finish_all_sites(client, sid)
    assert survey(client, sid, "closing", CLOSING).status_code == 409  # follow-up not done
    finish_followup(client, sid)
    assert client.post(f"/api/sessions/{sid}/finish").status_code == 422  # closing not done
    too_many = {**CLOSING, "reliable_signs": ["gradients", "writing", "layout", "charts"]}
    assert survey(client, sid, "closing", too_many).status_code == 422  # up to 3
    assert survey(client, sid, "closing", CLOSING).json()["missing"] == []
    assert client.post(f"/api/sessions/{sid}/finish").status_code == 200
    assert survey(client, sid, "closing", CLOSING).status_code == 409  # finished sessions are locked


def test_full_session_and_exports(client):
    sid = start(client)
    assigned = assigned_sites(client, sid)
    for site in assigned:
        answer(client, sid, site, FULL)
        client.post(f"/api/sessions/{sid}/sites/{site}/time", json={"seconds": 240})
        assert complete(client, sid, site).status_code == 200
    finish_followup(client, sid)
    survey(client, sid, "closing", CLOSING)
    assert client.post(f"/api/sessions/{sid}/finish").status_code == 200
    assert answer(client, sid, assigned[0], FULL).status_code == 409  # finished sessions are locked

    wide = list(csv.DictReader(io.StringIO(client.get("/api/export/responses_wide.csv").text)))
    assert len(wide) == 3
    row = wide[0]
    assert row["participant_id"] == "P01"
    assert row["ai_marks__count"] == "2"
    assert row["ai_marks"] == "1. Heading: Breathing Smoke | 2. Chart or graphic"
    assert row["feature_rating__gradients"] == "9" and row["feature_rating__charts"] == "NA"
    assert "feature_rating" not in row  # the grid is only exported one column per feature
    assert float(row["seconds_on_site"]) == 240

    long = list(csv.DictReader(io.StringIO(client.get("/api/export/responses_long.csv").text)))
    assert len(long) == 3 * len(FULL) + 2 * len(FOLLOWUP)

    marks = list(csv.DictReader(io.StringIO(client.get("/api/export/marks.csv").text)))
    assert len(marks) == 3 * len(MARKS)
    assert [m["mark_number"] for m in marks[:2]] == ["1", "2"]
    assert marks[1]["selector"] == "#chart > svg > rect:nth-of-type(3)"
    assert marks[1]["page"] == "story.html" and marks[1]["box_w"] == "640"
    assert marks[0]["participant_id"] == "P01" and marks[0]["site_id"] == assigned[0]

    sessions = list(csv.DictReader(io.StringIO(client.get("/api/export/sessions.csv").text)))
    assert sessions[0]["sites_completed"] == "3" and sessions[0]["finished_at"]
    assert sessions[0]["phd_year"] == "y2" and sessions[0]["taught_course"] == "TRUE"
    assert sessions[0]["can_tell_pre"] == "4" and sessions[0]["can_tell_post"] == "2"
    assert sessions[0]["reliable_signs"] == "gradients; writing"


def test_practice_sessions_are_excluded_from_exports_by_default(client):
    sid = start(client, "PRACTICE", practice=True)
    site = assigned_sites(client, sid)[0]
    answer(client, sid, site, FULL)
    complete(client, sid, site)
    assert len(client.get("/api/export/responses_wide.csv").text.strip().splitlines()) == 1
    assert len(client.get("/api/export/responses_wide.csv?practice=true").text.strip().splitlines()) == 2


def test_finish_revalidates_previously_completed_answers(client):
    sid = start(client)
    finish_all_sites(client, sid)
    first = assigned_sites(client, sid)[0]
    answer(client, sid, first, {"polish": None})
    assert client.post(f"/api/sessions/{sid}/followup").status_code == 422
    assert client.app_state.db.get_session(sid)["finished_at"] is None
    answer(client, sid, first, {"polish": 4})
    finish_followup(client, sid)
    survey(client, sid, "closing", CLOSING)
    assert client.post(f"/api/sessions/{sid}/finish").status_code == 200
