"""The FastAPI app: study pages, the JSON API they call, CSV exports, and the
frozen website copies under /sites/<site-id>/."""

import mimetypes
import posixpath
import re
from urllib.parse import unquote, urlsplit
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import Paths, Site, load_sites
from .db import Database
from .export import TABLES, Exporter
from .mirror import is_mirrored
from .questions import AnswerError, check_answer, load_questions, missing_answers, parse_questions
from .sheets import SheetSync, run_gws

# Types Python doesn't know by default but D3 sites commonly load.
for ext, mime in {".mjs": "text/javascript", ".geojson": "application/geo+json",
                  ".topojson": "application/json", ".csv": "text/csv",
                  ".tsv": "text/tab-separated-values", ".wasm": "application/wasm",
                  ".webmanifest": "application/manifest+json"}.items():
    mimetypes.add_type(mime, ext)

PARTICIPANT_ID = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
COHORTS = [
    {"id": "lower_division", "label": "Lower-division data science", "description": "Has not taken DSC106; no regular hands-on agentic AI experience."},
    {"id": "dsc106", "label": "Completed DSC106", "description": "Has completed DSC106; no regular hands-on agentic AI experience."},
    {"id": "agentic_internship", "label": "Agentic AI internship experience", "description": "Hands-on agentic workflows during an internship; either DSC106 background."},
]


class NewSession(BaseModel):
    participant_id: str
    cohort: Literal["lower_division", "dsc106", "agentic_internship"]
    dsc106_completed: bool | None = None
    excluded_site_ids: list[str] = Field(default_factory=list, max_length=1000)
    practice: bool = False
    allow_duplicate: bool = False
    screen: str | None = Field(default=None, max_length=40)


class Answers(BaseModel):
    answers: dict[str, Any]


class TimeSpent(BaseModel):
    seconds: float = Field(allow_inf_nan=False)
    phase: Literal["review", "followup"] = "review"


class SessionPatch(BaseModel):
    practice: bool


def create_app(paths=None, runner=run_gws, start_sync=True):
    paths = paths or Paths.default()
    sites = load_sites(paths)
    questions = load_questions(paths)
    db = Database(paths.db_file)
    exporter = Exporter(db, sites, questions)
    sync = SheetSync(db, exporter, paths, runner)

    @asynccontextmanager
    async def lifespan(app):
        if start_sync:
            sync.start()
        yield

    app = FastAPI(title="AI or Not study", lifespan=lifespan, docs_url="/api/docs", redoc_url=None)
    app.state.db, app.state.sync, app.state.paths = db, sync, paths

    @app.middleware("http")
    async def no_cache_for_app_files(request, call_next):
        response = await call_next(request)
        if not request.url.path.startswith("/sites/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    # --- helpers ---------------------------------------------------------

    def load_session(session_id):
        session = db.get_session(session_id)
        if session is None:
            raise HTTPException(404, "No session with that id")
        snapshot = session.get("sites_snapshot")
        if snapshot and any(not is_mirrored(paths, Site(**snapshot[sid])) for sid in session["site_order"]):
            raise HTTPException(409, "The frozen project files for this session have changed or are missing. Restore the original mirror before resuming.")
        return session

    def session_questions(session):
        snapshot = session.get("questions_snapshot")
        if snapshot:
            return parse_questions(snapshot)
        if session["questions_version"] != questions.version:
            raise HTTPException(409, "This older session has no saved questionnaire. Restore its original questions configuration to resume it.")
        return questions

    def phase(session):
        return "followup" if session.get("followup_started_at") else "review"

    def site_states(session, stage="review"):
        """Each site in this session's order, with whether it's done or reachable yet."""
        visits = {v["site_id"]: v for v in db.visits(session["id"])}
        states, reachable = [], True
        order = session["followup_order"] if stage == "followup" else session["site_order"]
        total = len(order)
        for position, site_id in enumerate(order, start=1):
            site = (session.get("sites_snapshot") or {}).get(site_id)
            entry = site["entry"] if site else sites.pool[site_id].entry
            done = visits[site_id]["followup_completed_at" if stage == "followup" else "completed_at"] is not None
            states.append({
                "id": site_id,
                "position": position,
                "label": f"Website {position} of {total}",
                "src": f"/sites/{site_id}/{entry}",
                "home": f"/sites/{site_id}/",
                "completed": done,
                "unlocked": reachable,
            })
            # Participants must finish each site before the next one opens.
            reachable = reachable and done
        return states

    def require_site(session, site_id, editable=True, stage=None):
        state = next((s for s in site_states(session, stage or phase(session)) if s["id"] == site_id), None)
        if state is None:
            raise HTTPException(404, "That site is not part of this session")
        if not state["unlocked"]:
            raise HTTPException(409, "Finish the earlier websites first")
        if editable and session["finished_at"]:
            raise HTTPException(409, "This session is already finished")
        return state

    # --- pages -------------------------------------------------------------

    @app.get("/", include_in_schema=False)
    def start_page():
        return FileResponse(paths.web_dir / "index.html")

    @app.get("/study/{session_id}", include_in_schema=False)
    def study_page(session_id: str):
        return FileResponse(paths.web_dir / "study.html")

    @app.get("/admin", include_in_schema=False)
    def admin_page():
        return FileResponse(paths.web_dir / "admin.html")

    # --- participant API ---------------------------------------------------

    @app.get("/api/study")
    def study_setup():
        return {"cohorts": COHORTS, "sites_per_session": min(sites.sites_per_session, len(sites.study)),
                "sites": [{"id": s.id, "title": s.title} for s in sites.study],
                "instructions": "Browse each webpage using normal scrolling and interaction. We are interested in your impression of how AI-generated it appears, rather than determining how it was made. Allow about five minutes per webpage, including answers."}

    @app.post("/api/sessions", status_code=201)
    def create_session(body: NewSession, request: Request):
        pid = body.participant_id.strip()
        if not PARTICIPANT_ID.match(pid):
            raise HTTPException(422, "Participant ID: use letters, numbers, - or _ (up to 32)")
        background = {"lower_division": False, "dsc106": True}.get(body.cohort, body.dsc106_completed)
        if background is None:
            raise HTTPException(422, "Record whether this internship participant has completed DSC106")
        if body.cohort != "agentic_internship" and body.dsc106_completed is not None and body.dsc106_completed != background:
            raise HTTPException(422, "DSC106 background conflicts with the selected group")
        active_ids = [s.id for s in sites.study]
        if set(body.excluded_site_ids) - set(active_ids):
            raise HTTPException(422, "Excluded projects must come from the active study list")
        missing = [s.id for s in sites.study if not is_mirrored(paths, s)]
        if missing:
            raise HTTPException(
                503, f"Not downloaded yet: {', '.join(missing)}. Run `uv run aiornot mirror`."
            )
        if not body.practice and not body.allow_duplicate and db.participant_has_session(pid):
            raise HTTPException(409, f"{pid} already has a session")
        try:
            session_id = db.create_session(
                pid, body.practice, active_ids, questions.version, sites.version,
                request.headers.get("user-agent", "")[:300], body.screen,
                cohort=body.cohort, dsc106_completed=background,
                questions_snapshot={"version": questions.version, "questions": questions.to_client()},
                sites_snapshot={s.id: s.__dict__ for s in sites.study},
                sites_per_session=min(sites.sites_per_session, len(sites.study)),
                excluded_site_ids=body.excluded_site_ids,
                followup_count=2 if questions.for_phase("followup").questions else 0,
            )
        except ValueError as err:
            raise HTTPException(422, str(err)) from None
        return {"id": session_id}

    @app.get("/api/sessions/{session_id}")
    def get_session(session_id: str):
        session = load_session(session_id)
        qs = session_questions(session)
        stage = phase(session)
        return {
            "session": {key: value for key, value in session.items() if key not in {"questions_snapshot", "sites_snapshot"}},
            "sites": site_states(session),
            "answers": db.answers(session_id),
            "phase": "finished" if session["finished_at"] else stage,
            "questions": qs.for_phase(stage).to_client(),
            "review_questions": qs.for_phase("review").to_client(),
            "followup_questions": qs.for_phase("followup").to_client() if stage == "followup" else [],
            "followup_sites": site_states(session, "followup"),
            "config_changed": session["questions_version"] != questions.version,
        }

    @app.put("/api/sessions/{session_id}/sites/{site_id}/answers")
    def save_answers(session_id: str, site_id: str, body: Answers):
        session = load_session(session_id)
        qs = session_questions(session)
        active = qs.for_phase(phase(session))
        by_id = qs.by_id
        for qid, value in body.answers.items():
            if qid not in by_id:
                raise HTTPException(422, f"Unknown question {qid!r}")
            if qid not in active.by_id:
                raise HTTPException(409, "This question is not editable in the current study stage")
            if value not in (None, [], ""):
                try:
                    check_answer(by_id[qid], value, by_id)
                except AnswerError as err:
                    raise HTTPException(422, str(err)) from None
                if by_id[qid].type == "annotation":
                    home = f"/sites/{site_id}"
                    for entry in value:
                        path = urlsplit(entry["page_path"]).path
                        for _ in range(3):
                            path = unquote(path)
                        path = posixpath.normpath(path)
                        if "\\" in path or (path != home and not path.startswith(home + "/")):
                            raise HTTPException(422, "Annotations must refer to this project's webpage")
        state = require_site(session, site_id)
        changed = db.save_answers(session_id, site_id, body.answers)
        if changed and state["completed"]:
            sync.enqueue(session_id, site_id)  # keep the Sheet row current after edits
        current = db.answers(session_id).get(site_id, {})
        return {"changed": changed, "missing": missing_answers(active, current)}

    @app.post("/api/sessions/{session_id}/sites/{site_id}/open")
    def open_site(session_id: str, site_id: str):
        session = load_session(session_id)
        require_site(session, site_id, editable=False)
        db.mark_opened(session_id, site_id, phase(session))
        return {"ok": True}

    @app.post("/api/sessions/{session_id}/sites/{site_id}/time")
    def add_time(session_id: str, site_id: str, body: TimeSpent):
        session = load_session(session_id)
        if body.phase == "followup" and not session["followup_started_at"]:
            raise HTTPException(409, "Final questions have not started")
        require_site(session, site_id, editable=False, stage=body.phase)
        # One report covers one continuous stretch on a site; cap it to ignore sleeping laptops.
        db.add_time(session_id, site_id, min(max(body.seconds, 0.0), 1800.0), body.phase)
        return {"ok": True}

    @app.post("/api/sessions/{session_id}/sites/{site_id}/complete")
    def complete_site(session_id: str, site_id: str):
        session = load_session(session_id)
        require_site(session, site_id)
        missing = missing_answers(session_questions(session).for_phase(phase(session)), db.answers(session_id).get(site_id, {}))
        if missing:
            raise HTTPException(422, {"message": "Some questions are unanswered", "missing": missing})
        db.complete_site(session_id, site_id, phase(session))
        sync.enqueue(session_id, site_id)
        return {"sites": site_states(session, phase(session))}

    def require_primary_complete(session):
        qs = session_questions(session).for_phase("review")
        answers = db.answers(session["id"])
        if not all(s["completed"] for s in site_states(session)):
            raise HTTPException(409, "Every website must be completed first")
        if any(missing_answers(qs, answers.get(site_id, {})) for site_id in session["site_order"]):
            raise HTTPException(422, "Every website must have complete answers")

    @app.post("/api/sessions/{session_id}/followup")
    def start_followup(session_id: str):
        session = load_session(session_id)
        if session["finished_at"]:
            raise HTTPException(409, "This session is already finished")
        require_primary_complete(session)
        if not session["followup_order"]:
            raise HTTPException(409, "This session has no final questions")
        db.start_followup(session_id)
        return {"ok": True}

    @app.post("/api/sessions/{session_id}/finish")
    def finish_session(session_id: str):
        session = load_session(session_id)
        require_primary_complete(session)
        qs = session_questions(session)
        answers = db.answers(session_id)
        if session["followup_order"]:
            if not session["followup_started_at"]:
                raise HTTPException(409, "Complete the final questions before finishing")
            if not all(s["completed"] for s in site_states(session, "followup")) or any(
                missing_answers(qs.for_phase("followup"), answers.get(site_id, {})) for site_id in session["followup_order"]
            ):
                raise HTTPException(422, "Complete the final questions before finishing")
        db.finish_session(session_id)
        return {"ok": True}

    # --- researcher API ----------------------------------------------------

    @app.patch("/api/sessions/{session_id}")
    def patch_session(session_id: str, body: SessionPatch):
        load_session(session_id)
        db.set_practice(session_id, body.practice)
        sync.enqueue_pending()
        return db.get_session(session_id)

    @app.get("/api/admin/overview")
    def overview():
        return {
            "sessions": [{key: value for key, value in row.items() if key not in {"questions_snapshot", "sites_snapshot"}} for row in db.list_sessions()],
            "site_count": len(sites.study),
            "coverage": db.coverage([s.id for s in sites.study]),
            "cohorts": COHORTS,
            "sites": [
                {"position": i, "id": s.id, "title": s.title, "award": s.award, "url": s.url,
                 "commit": s.commit, "mirrored": is_mirrored(paths, s),
                 "preview": f"/sites/{s.id}/{s.entry}"}
                for i, s in enumerate(sites.study, start=1)
            ],
            "questions_version": questions.version,
            "sites_version": sites.version,
            "sheet": sync.status(),
        }

    @app.post("/api/admin/sheet/sync")
    def sync_now():
        sync.enqueue_pending()
        return sync.status()

    @app.get("/api/export/{name}.csv")
    def export_csv(name: str, practice: bool = False):
        if name not in TABLES:
            raise HTTPException(404, f"Unknown table; choose from {', '.join(TABLES)}")
        return Response(
            exporter.csv(name, include_practice=practice),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{name}.csv"'},
        )

    app.mount("/static", StaticFiles(directory=paths.web_dir), name="static")
    paths.mirror_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/sites", StaticFiles(directory=paths.mirror_dir, html=True), name="sites")
    return app
