#!/usr/bin/env python3
"""Import one model response (from any provider or a manual chat session) as a benchmark run.

    python scripts/import_run.py --raw response.txt --package RUN_PKG --bundle BUNDLE \\
        --condition frozen-skill --provider example --model-id example-model-2026-10 \\
        --access-path "manual chat, prompt pasted, images attached in order" --out RUNS_DIR

This is the provider-neutral adapter contract: anything that can produce the
raw text a model returned for RUN_PKG/prompt.md (plus attachments in
attachments.json order) can be scored. The raw text is always preserved. JSON
is extracted if the model wrapped it in prose or a code fence (recorded as
json_extracted); nothing is repaired, retried, or re-asked here.
"""

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import validate_audit  # noqa: E402


def extract_json(raw):
    """Return (obj or None, parse_status, errors)."""
    text = raw.strip()
    if not text:
        return None, "empty", ["empty response"]
    try:
        return json.loads(text), "ok", []
    except json.JSONDecodeError:
        pass
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    candidates = [fence.group(1)] if fence else []
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start:end + 1])
    for c in candidates:
        try:
            return json.loads(c), "json_extracted", []
        except json.JSONDecodeError as err:
            last = str(err)
    return None, "invalid_json", [f"no parseable JSON object ({last if candidates else 'no braces found'})"]


def safe_id(text):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-")[:64] or "run"


def import_run(raw_path, package_dir, bundle_dir, out_dir, condition, provider, model_id, access_path,
               run_index=1, run_id=None, snapshot_date=None, envelope="", system_sha=None, temperature=None,
               max_output_tokens=None, reasoning=None, unavailable=(), retries=0, latency_ms=None,
               input_tokens=None, output_tokens=None, notes=()):
    lock = _lib.load_json(Path(package_dir) / "prompt.lock.json")
    attachments = _lib.load_json(Path(package_dir) / "attachments.json")
    bundle = _lib.Bundle(bundle_dir)
    if lock["bundle_hash"] != bundle.hash:
        raise _lib.UsageError("the prompt package was built from a different version of this bundle")
    raw = Path(raw_path).read_text(encoding="utf-8", errors="replace")
    run_id = safe_id(run_id or f"{condition}-{model_id}-{lock['bundle_id']}-r{run_index}")
    run_dir = Path(out_dir) / run_id
    if run_dir.exists():
        raise _lib.UsageError(f"{run_dir} already exists; runs are never overwritten")
    run_dir.mkdir(parents=True)
    shutil.copyfile(raw_path, run_dir / "raw_output.txt")

    audit, status, errors = extract_json(raw)
    audit_rel = None
    if audit is not None:
        audit_rel = "audit.json"
        (run_dir / audit_rel).write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        report = validate_audit.validate(audit, bundle.dir)
        if any(code == "schema" for code, _ in report.errors):
            status = "schema_invalid"
        elif not report.ok:
            status = "integrity_invalid"
        errors += [f"[{code}] {msg}" for code, msg in report.errors][:50]
    record = {
        "schema_version": "website-slop-audit/run-record/0.1",
        "run_id": run_id,
        "condition_id": condition,
        "model": {"provider": provider, "model_id": model_id, "snapshot_date": snapshot_date, "access_path": access_path},
        "run_index": run_index,
        "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prompt_lock": {
            "prompt_sha256": lock["prompt_sha256"],
            "package_sha256": lock["package_sha256"],
            "bundle_id": lock["bundle_id"],
            "bundle_hash": lock["bundle_hash"],
            "analysis_profile": lock["analysis_profile"],
            "rubric_version": lock["rubric_version"],
            "condition_template": lock["condition"],
        },
        "envelope": {"description": envelope, "system_instructions_sha256": system_sha,
                     "attachment_order": [a["asset_id"] for a in attachments]},
        "settings": {"temperature": temperature, "max_output_tokens": max_output_tokens, "reasoning": reasoning, "other": {}},
        "unavailable_parameters": list(unavailable),
        "retries": retries,
        "parse_status": status,
        "parse_errors": [e[:500] for e in errors],
        "raw_output_path": "raw_output.txt",
        "audit_path": audit_rel,
        "latency_ms": latency_ms,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens,
                  "images": len(attachments), "unit_note": "as reported by the provider, if at all"},
        "notes": list(notes),
    }
    schema_errs = _lib.schema_errors(record, _lib.load_schema("run-record.schema.json"))
    if schema_errs:
        raise _lib.UsageError(f"could not build a valid run record: {schema_errs[0]}")
    (run_dir / "run.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record, run_dir


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--raw", required=True, help="the model's raw response text")
    p.add_argument("--package", required=True, help="directory written by expand_prompt.py (or a baseline expander)")
    p.add_argument("--bundle", required=True)
    p.add_argument("--out", required=True, help="runs directory")
    p.add_argument("--condition", required=True, choices=["generic-prompt", "frozen-skill", "critique-baseline",
                                                          "deterministic-baseline", "native-workflow", "live-agent", "no-skill-dev"])
    p.add_argument("--provider", required=True)
    p.add_argument("--model-id", required=True, help="exact identifier the endpoint reported")
    p.add_argument("--access-path", required=True)
    p.add_argument("--run-index", type=int, default=1)
    p.add_argument("--run-id")
    p.add_argument("--snapshot-date")
    p.add_argument("--envelope", default="", help="how the host wrapped the prompt")
    p.add_argument("--system-sha256")
    p.add_argument("--temperature", type=float)
    p.add_argument("--max-output-tokens", type=int)
    p.add_argument("--reasoning")
    p.add_argument("--unavailable", action="append", default=[], help="a parameter the host did not expose (repeatable)")
    p.add_argument("--retries", type=int, default=0)
    p.add_argument("--latency-ms", type=float)
    p.add_argument("--input-tokens", type=int)
    p.add_argument("--output-tokens", type=int)
    p.add_argument("--note", action="append", default=[])
    a = p.parse_args(argv)
    record, run_dir = import_run(a.raw, a.package, a.bundle, a.out, a.condition, a.provider, a.model_id, a.access_path,
                                 a.run_index, a.run_id, a.snapshot_date, a.envelope, a.system_sha256, a.temperature,
                                 a.max_output_tokens, a.reasoning, a.unavailable, a.retries, a.latency_ms,
                                 a.input_tokens, a.output_tokens, a.note)
    print(f"{record['parse_status']}: {run_dir}")
    for e in record["parse_errors"][:10]:
        print(f"  {e}")
    return 0 if record["parse_status"] in ("ok", "json_extracted") else 1


if __name__ == "__main__":
    _lib.run_main(main)
