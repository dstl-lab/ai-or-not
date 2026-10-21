"""Mirror survey answers into a Google Sheet, using the `gws` CLI's saved login.

SQLite stays the source of truth. The Sheet gets one row per participant x
site, written when the participant finishes that site. If they go back and
edit, the same row is overwritten (its row number is remembered in the
sheet_rows table), so the Sheet always shows the latest answers.

Sync runs on a background thread so a slow or offline network never blocks
the participant. Failures are recorded and retried; anything still pending
is picked up again the next time the server starts.
"""

import json
import queue
import re
import subprocess
import threading

from .db import now

TAB = "responses"
RETRY_SECONDS = 30


class GwsError(Exception):
    pass


def run_gws(args, params=None, body=None, timeout=60):
    """Run one `gws` command and return its parsed JSON output."""
    cmd = ["gws", *args]
    if params is not None:
        cmd += ["--params", json.dumps(params)]
    if body is not None:
        cmd += ["--json", json.dumps(body)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise GwsError("the gws CLI is not installed or not on PATH") from None
    except subprocess.TimeoutExpired:
        raise GwsError(f"gws timed out after {timeout}s") from None
    if proc.returncode != 0:
        raise GwsError((proc.stderr or proc.stdout).strip()[-500:] or "gws failed")
    out = proc.stdout.strip()
    if not out:
        return {}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        # Some gws builds print a status line before the JSON body.
        start, end = out.find("{"), out.rfind("}")
        if start == -1:
            raise GwsError(f"unexpected gws output: {out[:200]}") from None
        return json.loads(out[start : end + 1])


def parse_spreadsheet_id(id_or_url):
    match = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)", id_or_url)
    return match.group(1) if match else id_or_url.strip()


def load_link(paths):
    try:
        return json.loads(paths.sheets_file.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_link(paths, spreadsheet_id, url, title):
    paths.sheets_file.parent.mkdir(parents=True, exist_ok=True)
    link = {"spreadsheet_id": spreadsheet_id, "url": url, "title": title}
    paths.sheets_file.write_text(json.dumps(link, indent=2) + "\n")
    return link


def create_sheet(paths, title, runner=run_gws):
    """Create a new spreadsheet with a frozen header row and link it to this study."""
    resp = runner(
        ["sheets", "spreadsheets", "create"],
        body={
            "properties": {"title": title},
            "sheets": [{"properties": {"title": TAB, "gridProperties": {"frozenRowCount": 1}}}],
        },
    )
    return save_link(paths, resp["spreadsheetId"], resp["spreadsheetUrl"], title)


def connect_sheet(paths, id_or_url, runner=run_gws):
    """Link an existing spreadsheet, adding the responses tab if it's missing."""
    spreadsheet_id = parse_spreadsheet_id(id_or_url)
    info = runner(
        ["sheets", "spreadsheets", "get"],
        params={"spreadsheetId": spreadsheet_id, "fields": "spreadsheetUrl,properties.title,sheets.properties.title"},
    )
    tabs = {s["properties"]["title"] for s in info.get("sheets", [])}
    if TAB not in tabs:
        runner(
            ["sheets", "spreadsheets", "batchUpdate"],
            params={"spreadsheetId": spreadsheet_id},
            body={"requests": [{"addSheet": {"properties": {
                "title": TAB, "gridProperties": {"frozenRowCount": 1}}}}]},
        )
    return save_link(paths, spreadsheet_id, info["spreadsheetUrl"], info["properties"]["title"])


def row_from_range(updated_range):
    """'responses!A5:T5' -> 5"""
    match = re.search(r"![A-Z]+(\d+)", updated_range or "")
    if not match:
        raise GwsError(f"could not read row number from {updated_range!r}")
    return int(match.group(1))


class SheetSync:
    def __init__(self, db, exporter, paths, runner=run_gws):
        self.db = db
        self.exporter = exporter
        self.paths = paths
        self.runner = runner
        self.queue = queue.Queue()
        self.queued = set()
        self.lock = threading.Lock()
        self.header_written_for = None
        self.thread = None

    @property
    def link(self):
        return load_link(self.paths)

    def start(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self._work, name="sheet-sync", daemon=True)
            self.thread.start()
        self.enqueue_pending()

    def enqueue(self, session_id, site_id):
        key = (session_id, site_id)
        with self.lock:
            if key in self.queued:
                return
            self.queued.add(key)
        self.queue.put(key)

    def enqueue_pending(self):
        for key in self.db.unsynced_visits():
            self.enqueue(*key)

    def _work(self):
        while True:
            key = self.queue.get()
            with self.lock:
                self.queued.discard(key)
            try:
                self.sync_one(*key)
            except Exception as err:  # keep the worker alive no matter what
                self.db.record_sheet_error(*key, str(err)[:500])
                timer = threading.Timer(RETRY_SECONDS, self.enqueue, args=key)
                timer.daemon = True
                timer.start()

    def sync_one(self, session_id, site_id):
        link = self.link
        if not link:
            return  # not configured yet; stays pending until a Sheet is linked
        sid = link["spreadsheet_id"]
        columns = self.exporter.sheet_columns()
        if self.header_written_for != (sid, columns):
            self.runner(
                ["sheets", "spreadsheets", "values", "update"],
                params={"spreadsheetId": sid, "range": f"{TAB}!A1", "valueInputOption": "RAW"},
                body={"values": [columns]},
            )
            self.header_written_for = (sid, columns)

        values, revision = self.exporter.sheet_row(session_id, site_id, now())
        if values is None:
            return
        existing = self.db.sheet_row(session_id, site_id)
        if existing and existing.get("row_number"):
            row = existing["row_number"]
            self.runner(
                ["sheets", "spreadsheets", "values", "update"],
                params={"spreadsheetId": sid, "range": f"{TAB}!A{row}", "valueInputOption": "RAW"},
                body={"values": [values]},
            )
        else:
            resp = self.runner(
                ["sheets", "spreadsheets", "values", "append"],
                params={"spreadsheetId": sid, "range": f"{TAB}!A1", "valueInputOption": "RAW",
                        "insertDataOption": "INSERT_ROWS"},
                body={"values": [values]},
            )
            row = row_from_range(resp.get("updates", {}).get("updatedRange"))
        self.db.record_sheet_sync(session_id, site_id, row, revision)

    def status(self):
        link = self.link
        return {"configured": bool(link), "link": link, **self.db.sheet_summary()}
