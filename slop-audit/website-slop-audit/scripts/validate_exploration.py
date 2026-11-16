#!/usr/bin/env python3
"""Validate a live-exploration record (exploration.json and its screenshots), and optionally lock it.

    python scripts/validate_exploration.py EXPLORATION_DIR [--bundle BUNDLE] [--freeze] [--json]

Exit code 0 = valid, 1 = invalid, 2 = unusable input. The record is written by
scripts/explore.py finish. These checks are structural: ids in order, files
present with matching hashes, budgets respected, and the link to the frozen
bundle the tour stage judged. Once locked (exploration.lock.json), any change
to the record or its screenshots is reported.

Also home to the tour-stage lock used by explore.py start and validate_audit.py:
tour_commit(audit) is the hash of an audit without its exploration_stage.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

LOCK_NAME = "exploration.lock.json"
RECORD_NAME = "exploration.json"


class VxError(Exception):
    """A tour audit or bundle that cannot start an exploration; the message says why."""


def tour_commit(audit):
    """Hash of the tour stage: the whole audit except exploration_stage."""
    return _lib.sha256_bytes(_lib.canonical_json({k: v for k, v in audit.items() if k != "exploration_stage"}))


def validate_bundle_frozen(bundle_dir):
    import validate_bundle
    report, bundle = validate_bundle.validate(bundle_dir)
    if report.ok and not (Path(bundle_dir) / validate_bundle.LOCK_NAME).exists():
        report.error("not_frozen", "the bundle has no bundle.lock.json; freeze it before auditing")
    return report, bundle


def check_tour_audit(audit_path, bundle_dir):
    """The tour-stage audit must validate, carry the study answers, and have no exploration stage yet."""
    import validate_audit
    audit = _lib.load_json(audit_path)
    if "exploration_stage" in audit:
        raise VxError("the tour audit already has an exploration_stage; give the tour-stage file (audit.tour.json)")
    if "study_questionnaire" not in audit:
        raise VxError("the tour audit has no study_questionnaire; answer the study questions before exploring")
    report = validate_audit.validate(audit, bundle_dir)
    if not report.ok:
        report.print(sys.stderr)
        raise VxError("the tour audit does not validate; fix it before exploring (exploring locks it)")
    return audit


class Record:
    def __init__(self, folder):
        self.dir = Path(folder)
        if self.dir.is_file():
            self.dir = self.dir.parent
        self.data = _lib.load_json(self.dir / RECORD_NAME)
        acts = self.data.get("actions", [])
        self.actions = {a["action_id"]: a for a in acts}
        self.assets = {s["asset_id"]: (a, s) for a in acts for s in a.get("screenshots", [])}

    @property
    def exploration_id(self):
        return self.data.get("exploration_id")

    @property
    def hash(self):
        return _lib.sha256_bytes(_lib.canonical_json(self.data))

    def selectors(self):
        """Selectors of elements the model actually acted on."""
        return {a["target"]["selector"] for a in self.actions.values() if a["status"] == "completed" and a.get("target")}

    def routes(self):
        return {a["route"] for a in self.actions.values() if a["route"]}


def validate(folder, bundle_dir=None):
    folder = Path(folder)
    report = _lib.Report(str(folder))
    try:
        rec = Record(folder)
    except _lib.UsageError as err:
        report.error("unreadable", str(err))
        return report, None
    d = rec.data
    for msg in _lib.schema_errors(d, _lib.load_schema("exploration.schema.json")):
        report.error("schema", msg)
    if report.errors:
        return report, rec
    for i, a in enumerate(d["actions"], 1):
        where = f"action {a['action_id']}"
        if a["action_id"] != f"L{i:03d}":
            report.error("action_order", f"{where}: actions are numbered L001, L002, … in order; expected L{i:03d}")
        if a["status"] != "completed" and a["screenshots"]:
            report.error("malformed_action", f"{where}: a {a['status']} action cannot carry screenshots")
        for s in a["screenshots"]:
            if not s["asset_id"].startswith(a["action_id"]):
                report.error("malformed_action", f"{where}: screenshot {s['asset_id']} belongs to another action")
            path = rec.dir / s["path"]
            if not path.is_file():
                report.error("missing_file", f"{where}: {s['path']} not found")
                continue
            if _lib.sha256_file(path) != s["sha256"]:
                report.error("hash_mismatch", f"{where}: sha256 does not match {s['path']}")
            if _lib.image_size(path) != (s["pixel_width"], s["pixel_height"]):
                report.error("dimension_mismatch", f"{where}: {s['path']} size differs from the record")
    counted = sum(1 for a in d["actions"] if a["counted"])
    shots = sum(len(a["screenshots"]) for a in d["actions"])
    inspections = sum(1 for a in d["actions"] if a["command"] in ("find", "read"))
    actual = {"actions": counted, "screenshots": shots, "inspections": inspections,
              "refused": sum(1 for a in d["actions"] if a["status"] == "refused"),
              "failed": sum(1 for a in d["actions"] if a["status"] == "failed")}
    if actual != d["counts"]:
        report.error("counts_mismatch", f"counts {d['counts']} do not match the actions {actual}")
    lim = d["limits"]
    if counted > lim["max_actions"] or shots > lim["max_screenshots"] or inspections > lim["max_inspections"]:
        report.error("budget_exceeded", f"the record exceeds its budget {lim}: {actual}")
    if bundle_dir is not None:
        try:
            bundle = _lib.Bundle(bundle_dir)
            if bundle.bundle_id != d["bundle_id"] or bundle.hash != d["bundle_hash"]:
                report.error("bundle_mismatch", "the exploration was started from a different bundle (bundle_id or bundle_hash differ)")
        except _lib.UsageError as err:
            report.error("bundle_unreadable", str(err))
    lock = rec.dir / LOCK_NAME
    if lock.exists():
        locked = _lib.load_json(lock)
        if locked.get("exploration_hash") != rec.hash:
            report.error("changed_after_freeze", f"{LOCK_NAME} does not match exploration.json; the record changed after it was locked")
    return report, rec


def freeze(rec):
    lock = {"exploration_id": rec.exploration_id, "exploration_hash": rec.hash,
            "frozen_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "files": {s["path"]: s["sha256"] for a in rec.data["actions"] for s in a["screenshots"]}}
    (rec.dir / LOCK_NAME).write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    return lock


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("exploration", help="the exploration folder (or its exploration.json)")
    p.add_argument("--bundle", help="the frozen bundle the tour stage judged")
    p.add_argument("--freeze", action="store_true", help=f"write {LOCK_NAME} when valid")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    report, rec = validate(a.exploration, a.bundle)
    if a.freeze and report.ok:
        lock = freeze(rec)
        report.warnings.append(("frozen", f"wrote {LOCK_NAME} with exploration_hash {lock['exploration_hash']}"))
    print(json.dumps(report.as_dict(), indent=2)) if a.json else report.print()
    return 0 if report.ok else 1


if __name__ == "__main__":
    _lib.run_main(main)
