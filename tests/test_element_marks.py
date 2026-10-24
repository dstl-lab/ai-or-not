import csv
import io

from test_study_flow import start, answer, complete
from conftest import FULL, SITES


def mark(**changes):
    return {"page": "/sites/alpha/", "selector": "html > body > button", "tag": "button",
            "label": "button: Explore", "reason": "shape", "rect": [10, 20, 120, 40],
            "viewport": [1000, 800], "styles": {"border-radius": "24px"},
            "ai_judgment": True, **changes}


def test_marks_require_judgment_and_roundtrip_with_csv(client):
    sid = start(client)
    url = f"/api/sessions/{sid}/sites/alpha/marks"
    payload = {"marks": [mark()], "none": False}
    assert client.put(url, json=payload).status_code == 422
    answer(client, sid, 'alpha', FULL)
    assert client.put(url, json=payload).status_code == 200
    assert client.get(f'/api/sessions/{sid}').json()['marks']['alpha'] == payload
    rows = list(csv.DictReader(io.StringIO(client.get('/api/export/element_marks.csv').text)))
    assert rows[0]['reason'] == 'shape'
    assert rows[0]['ai_judgment'] == 'True'
    assert '24px' in rows[0]['styles']
    assert client.put(url, json={"marks": [], "none": True}).status_code == 200
    assert client.get(f'/api/sessions/{sid}').json()['marks']['alpha']['none'] is True


def test_marks_validate_limit_reason_scope_and_session_locks(client):
    sid = start(client)
    answer(client, sid, 'alpha', FULL)
    url = f'/api/sessions/{sid}/sites/alpha/marks'
    for payload in [
        {'marks': [mark()] * 4}, {'marks': [mark(reason='made_up')]},
        {'marks': [mark(page='/sites/beta/')]}, {'marks': [mark(rect=[-1, 0, 10, 10])]},
        {'marks': [mark()], 'none': True},
    ]:
        assert client.put(url, json=payload).status_code == 422
    assert client.put(f'/api/sessions/{sid}/sites/beta/marks', json={'marks': []}).status_code == 409
    for site in SITES:
        answer(client, sid, site, FULL)
        complete(client, sid, site)
    client.post(f'/api/sessions/{sid}/finish')
    assert client.put(url, json={'marks': [mark()]}).status_code == 409


def test_practice_mark_exports_are_opt_in(client):
    sid = start(client, practice=True)
    answer(client, sid, 'alpha', FULL)
    client.put(f'/api/sessions/{sid}/sites/alpha/marks', json={'marks': [mark()]})
    assert len(list(csv.DictReader(io.StringIO(client.get('/api/export/element_marks.csv').text)))) == 0
    assert len(list(csv.DictReader(io.StringIO(client.get('/api/export/element_marks.csv?practice=true').text)))) == 1
