#!/usr/bin/env python3
"""Score saved model runs against human reference annotations. No model APIs.

    python scripts/score_benchmark.py --runs RUNS --annotations ANNOTATIONS --bundles BUNDLES --out OUT_DIR
    python scripts/score_benchmark.py ... --compare frozen-skill/model-a generic-prompt/model-a
    python scripts/score_benchmark.py ... --human-sets PRE_ADJUDICATION_DIR --price-table prices.json

Inputs
  RUNS/<run_id>/run.json (+ audit.json, raw_output.txt)   written by import_run.py
  ANNOTATIONS/*.json   reference sets (stage adjudicated or synthetic_development), one per bundle
  BUNDLES/**/manifest.json   the frozen bundles, found by bundle_id

The matching and metric definitions are documented in
references/benchmark-protocol.md; this file implements exactly those rules.
"""

import argparse
import json
import math
import os
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import validate_audit  # noqa: E402

PRIMARY_METRIC = "strict accepted-finding micro F1 on fully annotated assessable scopes"
DEFAULT_IOU = 0.5  # pre-registered pilot threshold, not an established standard
ORD = {"none": 0, "weak": 1, "moderate": 2, "strong": 3}
WIDE_SCOPES = {"page-pattern"}
NARROW_REF_SCOPES = {"region"}


# --- small metric helpers ----------------------------------------------------

def ratio(num, den):
    return None if den == 0 else num / den


def prf(tp, fp, fn):
    p, r = ratio(tp, tp + fp), ratio(tp, tp + fn)
    if p is None or r is None:
        f1 = None
    elif p + r == 0:
        f1 = 0.0
    else:
        f1 = 2 * p * r / (p + r)
    return {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r, "f1": f1,
            "undefined": [n for n, v in (("precision", p), ("recall", r)) if v is None]}


def macro(values):
    defined = [v for v in values if v is not None]
    return {"mean": statistics.mean(defined) if defined else None, "n_defined": len(defined), "n_total": len(values)}


def jaccard(a, b):
    return len(a & b) / len(a | b) if a | b else 0.0


def iou(a, b):
    ix = max(0.0, min(a["x"] + a["width"], b["x"] + b["width"]) - max(a["x"], b["x"]))
    iy = max(0.0, min(a["y"] + a["height"], b["y"] + b["height"]) - max(a["y"], b["y"]))
    inter = ix * iy
    union = a["width"] * a["height"] + b["width"] * b["height"] - inter
    return inter / union if union > 0 else 0.0


def spearman(pairs):
    if len(pairs) < 3:
        return None
    xs, ys = zip(*pairs)

    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r

    rx, ry = ranks(xs), ranks(ys)
    if len(set(rx)) < 2 or len(set(ry)) < 2:
        return None
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else None


# --- loading -------------------------------------------------------------------

def find_bundles(root):
    """bundle_id -> Bundle for every manifest.json under root (symlinked folders included)."""
    out = {}
    for dirpath, _, files in sorted(os.walk(root, followlinks=True)):
        if "manifest.json" not in files:
            continue
        try:
            b = _lib.Bundle(Path(dirpath))
            out[b.bundle_id] = b
        except _lib.UsageError:
            continue
    return out


def load_references(directory, accept_stages=("adjudicated", "synthetic_development")):
    refs = {}
    for path in sorted(Path(directory).glob("*.json")):
        data = _lib.load_json(path)
        errors = _lib.schema_errors(data, _lib.load_schema("annotation.schema.json"))
        if errors:
            raise _lib.UsageError(f"{path}: invalid annotation set: {errors[0]}")
        if data["stage"] in accept_stages:
            if data["bundle_id"] in refs:
                raise _lib.UsageError(f"two reference sets for bundle {data['bundle_id']}; keep one adjudicated set")
            refs[data["bundle_id"]] = data
    return refs


def load_runs(directory):
    runs = []
    schema = _lib.load_schema("run-record.schema.json")
    for path in sorted(Path(directory).glob("*/run.json")):
        rec = _lib.load_json(path)
        errors = _lib.schema_errors(rec, schema)
        if errors:
            raise _lib.UsageError(f"{path}: invalid run record: {errors[0]}")
        audit = None
        if rec["audit_path"]:
            audit_file = path.parent / rec["audit_path"]
            if audit_file.exists():
                try:
                    audit = json.loads(audit_file.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    audit = None
        runs.append({"record": rec, "audit": audit, "dir": path.parent})
    return runs


# --- matching -----------------------------------------------------------------

def locset(item):
    return frozenset((l["region_id"], l["state_id"]) for l in item["locations"])


def scope_cover(annotation):
    """feature_id -> set of (region, state) pairs fully annotated for it."""
    cover = defaultdict(set)
    for s in annotation["scopes"]:
        if s["fully_annotated"]:
            for f in s["feature_ids"]:
                cover[f] |= {(r, st) for r in s["region_ids"] for st in s["state_ids"]}
    return cover


def compatible(pred, ref):
    if pred["feature_id"] != ref["feature_id"]:
        return False
    if not (locset(pred) & locset(ref)):
        return False
    # A broad page-pattern claim must not absorb a local, region-level reference item.
    if pred["scope"] in WIDE_SCOPES and ref["scope"] in NARROW_REF_SCOPES:
        return False
    return True


def match(preds, refs, pred_key):
    """Greedy one-to-one matching by location Jaccard, deterministic tie-breaks."""
    cands = []
    for p in preds:
        for r in refs:
            if compatible(p, r):
                cands.append((-jaccard(locset(p), locset(r)), p[pred_key], r["annotation_id"], p, r))
    cands.sort(key=lambda c: (c[0], c[1], c[2]))
    used_p, used_r, pairs = set(), set(), []
    for _, pid, rid, p, r in cands:
        if pid in used_p or rid in used_r:
            continue
        used_p.add(pid)
        used_r.add(rid)
        pairs.append((p, r))
    return pairs


def score_site(audit, annotation):
    """Counts for one audit on one bundle. audit None means a failed/empty output."""
    cover = scope_cover(annotation)
    refs = [r for r in annotation["items"] if r["disposition"] != "unassessed"]
    preds = audit["findings"] if audit else []
    in_scope = [p for p in preds if locset(p) <= cover.get(p["feature_id"], set())]
    unreviewed = [p for p in preds if p not in in_scope]
    pairs = match(in_scope, refs, "finding_id")
    matched = {p["finding_id"]: r for p, r in pairs}
    positives = [r for r in refs if r["disposition"] == "accepted_slop_candidate"]
    matched_pos_ids = {r["annotation_id"] for _, r in pairs if r["disposition"] == "accepted_slop_candidate"}

    per_code = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    fp_kinds = defaultdict(int)
    tp_pairs = []
    for p in in_scope:
        r = matched.get(p["finding_id"])
        if r is not None and r["disposition"] == "accepted_slop_candidate":
            per_code[p["feature_id"]]["tp"] += 1
            tp_pairs.append((p, r))
        else:
            per_code[p["feature_id"]]["fp"] += 1
            kind = {"contextual_exception": "contextual_false_alarm", "quality_only": "quality_as_slop",
                    "feature_absent": "absent_false_alarm"}.get(r["disposition"] if r else None, "unsupported_in_annotated_scope")
            fp_kinds[kind] += 1
    for r in positives:
        if r["annotation_id"] not in matched_pos_ids:
            per_code[r["feature_id"]]["fn"] += 1

    # Presence recognition: findings and contextual exceptions both assert presence.
    present_preds = list(preds) + (audit["contextual_exceptions"] if audit else [])
    present_preds = [dict(p, _pid=p.get("finding_id") or p.get("exception_id"), scope=p.get("scope", "region"))
                     for p in present_preds if locset(p) <= cover.get(p["feature_id"], set())]
    present_refs = [r for r in refs if r["disposition"] in ("accepted_slop_candidate", "contextual_exception", "quality_only")]
    ppairs = match(present_preds, present_refs, "_pid")
    presence = {"tp": len(ppairs), "fp": len(present_preds) - len(ppairs), "fn": len(present_refs) - len(ppairs)}

    # Localization on true positives.
    region_j, exact, ious, null_box = [], 0, [], 0
    for p, r in tp_pairs:
        j = jaccard(locset(p), locset(r))
        region_j.append(j)
        exact += int(locset(p) == locset(r))
        for pl in p["locations"]:
            ref_boxes = [rl["box"] for rl in r["locations"] if rl["box"] and rl["asset_id"] == pl["asset_id"]]
            if not ref_boxes:
                continue
            if pl["box"] is None:
                null_box += 1
            else:
                ious.append(max(iou(pl["box"], b) for b in ref_boxes))

    # Ordinal agreement on matched pairs (true positives and contextual false alarms).
    ordinal = [(ORD[p["slop_association"]["level"]], ORD[r["slop_association"]])
               for p in in_scope if (r := matched.get(p["finding_id"])) is not None
               and p["slop_association"]["level"] in ORD and r["slop_association"] in ORD]

    # Abstention: features in fully annotated scopes that the audit left unassessed.
    cov = {c["feature_id"]: c["status"] for c in (audit["coverage"]["features"] if audit else [])}
    scope_feats = sorted(cover)
    abstained = [f for f in scope_feats if cov.get(f) == "unassessed"]
    missing_cov = [f for f in scope_feats if f not in cov]
    return {
        "per_code": dict(per_code), "fp_kinds": dict(fp_kinds), "presence": presence,
        "n_predictions": len(preds), "n_in_scope": len(in_scope), "n_unreviewed": len(unreviewed),
        "n_positives": len(positives), "n_exploratory": len(audit["exploratory_candidates"]) if audit else 0,
        "localization": {"region_jaccard": region_j, "exact_region_state": exact, "ious": ious, "null_box_where_ref_box": null_box},
        "ordinal": ordinal, "abstained": abstained, "scope_features": scope_feats, "coverage_missing": missing_cov,
        "finding_keys": sorted((p["feature_id"], tuple(sorted(r for r, _ in locset(p)))) for p in preds),
    }


# --- aggregation ---------------------------------------------------------------

def system_key(rec):
    return f"{rec['condition_id']}/{rec['model']['model_id']}"


def capability(rec):
    try:
        return _lib.profile(rec["prompt_lock"]["analysis_profile"])["capability"]
    except _lib.UsageError:
        return "unknown"


def summarize_system(site_scores, iou_threshold=DEFAULT_IOU):
    """site_scores: {bundle_id: [score per run]}. Repeated runs average within a site."""
    totals = defaultdict(lambda: {"tp": 0.0, "fp": 0.0, "fn": 0.0})
    per_site, presence = {}, {"tp": 0.0, "fp": 0.0, "fn": 0.0}
    fp_kinds = defaultdict(float)
    loc = {"region_jaccard": [], "exact": 0.0, "n_tp": 0.0, "ious": [], "null_box": 0.0}
    ordinal, abst_num, abst_den, unreviewed, exploratory = [], 0.0, 0, 0.0, 0.0
    for bundle_id, runs in sorted(site_scores.items()):
        n = len(runs)
        site = {"tp": 0.0, "fp": 0.0, "fn": 0.0}
        for s in runs:
            for code, c in s["per_code"].items():
                for k in ("tp", "fp", "fn"):
                    totals[code][k] += c[k] / n
                    site[k] += c[k] / n
            for k in presence:
                presence[k] += s["presence"][k] / n
            for k, v in s["fp_kinds"].items():
                fp_kinds[k] += v / n
            loc["region_jaccard"] += s["localization"]["region_jaccard"]
            loc["exact"] += s["localization"]["exact_region_state"] / n
            loc["n_tp"] += len(s["localization"]["region_jaccard"]) / n
            loc["ious"] += s["localization"]["ious"]
            loc["null_box"] += s["localization"]["null_box_where_ref_box"] / n
            ordinal += s["ordinal"]
            abst_num += len(s["abstained"]) / n
            unreviewed += s["n_unreviewed"] / n
            exploratory += s["n_exploratory"] / n
        abst_den += len(runs[0]["scope_features"])
        per_site[bundle_id] = dict(prf(site["tp"], site["fp"], site["fn"]), n_runs=n)
    micro = {k: sum(c[k] for c in totals.values()) for k in ("tp", "fp", "fn")}
    per_code = {code: prf(c["tp"], c["fp"], c["fn"]) for code, c in sorted(totals.items())}
    return {
        "primary": prf(micro["tp"], micro["fp"], micro["fn"]),
        "macro_by_code": {m: macro([v[m] for v in per_code.values()]) for m in ("precision", "recall", "f1")},
        "macro_by_site": {m: macro([v[m] for v in per_site.values()]) for m in ("precision", "recall", "f1")},
        "per_code": per_code,
        "per_site": per_site,
        "false_alarm_breakdown": dict(fp_kinds),
        "presence_recognition": prf(presence["tp"], presence["fp"], presence["fn"]),
        "localization": {
            "matched_findings": loc["n_tp"],
            "mean_region_state_jaccard": statistics.mean(loc["region_jaccard"]) if loc["region_jaccard"] else None,
            "exact_region_state_rate": ratio(loc["exact"], loc["n_tp"]),
            "box_pairs": len(loc["ious"]),
            "mean_box_iou": statistics.mean(loc["ious"]) if loc["ious"] else None,
            "box_iou_at_threshold_rate": ratio(sum(1 for v in loc["ious"] if v >= iou_threshold), len(loc["ious"])),
            "null_box_where_reference_has_box": loc["null_box"],
        },
        "ordinal_agreement": {
            "pairs": len(ordinal),
            "exact": ratio(sum(1 for a, b in ordinal if a == b), len(ordinal)),
            "within_one": ratio(sum(1 for a, b in ordinal if abs(a - b) <= 1), len(ordinal)),
            "spearman": spearman(ordinal),
        },
        "abstention_rate_in_annotated_scope": ratio(abst_num, abst_den),
        "unreviewed_findings": unreviewed,
        "exploratory_candidates_reported_separately": exploratory,
        "n_sites": len(site_scores),
    }



def bootstrap_diff(scores_a, scores_b, n, seed):
    """Paired site-level bootstrap of micro-F1 difference (A minus B)."""
    sites = sorted(set(scores_a) & set(scores_b))
    if len(sites) < 2:
        return {"sites": len(sites), "note": "need at least two shared sites"}

    def site_counts(runs):
        out = {"tp": 0.0, "fp": 0.0, "fn": 0.0}
        for s in runs:
            for c in s["per_code"].values():
                for k in out:
                    out[k] += c[k] / len(runs)
        return out

    ca = {s: site_counts(scores_a[s]) for s in sites}
    cb = {s: site_counts(scores_b[s]) for s in sites}

    def f1(counts, sample):
        t = {k: sum(counts[s][k] for s in sample) for k in ("tp", "fp", "fn")}
        return prf(t["tp"], t["fp"], t["fn"])["f1"]

    observed_a, observed_b = f1(ca, sites), f1(cb, sites)
    rng = random.Random(seed)
    diffs = []
    for _ in range(n):
        sample = [rng.choice(sites) for _ in sites]
        fa, fb = f1(ca, sample), f1(cb, sample)
        if fa is not None and fb is not None:
            diffs.append(fa - fb)
    diffs.sort()
    lo = diffs[int(0.025 * len(diffs))] if diffs else None
    hi = diffs[min(len(diffs) - 1, int(0.975 * len(diffs)))] if diffs else None
    return {"sites": len(sites), "f1_a": observed_a, "f1_b": observed_b,
            "difference": None if observed_a is None or observed_b is None else observed_a - observed_b,
            "ci95": [lo, hi], "resamples_defined": len(diffs), "resamples": n, "seed": seed}


def stability(by_system_bundle):
    out = {}
    for sys_key, bundles in by_system_bundle.items():
        vals = []
        for runs in bundles.values():
            keys = [set(map(tuple, r["finding_keys"])) for r in runs]
            for i in range(len(keys)):
                for j in range(i + 1, len(keys)):
                    vals.append(jaccard(keys[i], keys[j]) if keys[i] | keys[j] else 1.0)
        out[sys_key] = {"pairs": len(vals), "mean_finding_set_jaccard": statistics.mean(vals) if vals else None}
    return out


def human_variability(directory):
    """Pairwise agreement between pre-adjudication sets on the same bundle."""
    sets = defaultdict(list)
    for path in sorted(Path(directory).glob("*.json")):
        data = _lib.load_json(path)
        if data["stage"] == "pre_adjudication":
            sets[data["bundle_id"]].append(data)
    pairs_out = []
    for bundle_id, group in sorted(sets.items()):
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a = [dict(x, finding_id=x["annotation_id"]) for x in group[i]["items"] if x["disposition"] != "unassessed"]
                b = [x for x in group[j]["items"] if x["disposition"] != "unassessed"]
                pairs = match(a, b, "finding_id")
                ordinal = [(ORD[x["slop_association"]], ORD[y["slop_association"]]) for x, y in pairs
                           if x["slop_association"] in ORD and y["slop_association"] in ORD]
                pairs_out.append({
                    "bundle_id": bundle_id,
                    "sets": [group[i]["annotation_set_id"], group[j]["annotation_set_id"]],
                    "items_a": len(a), "items_b": len(b), "matched": len(pairs),
                    "disposition_agreement": ratio(sum(1 for x, y in pairs if x["disposition"] == y["disposition"]), len(pairs)),
                    "association_exact": ratio(sum(1 for x, y in ordinal if x == y), len(ordinal)),
                    "association_spearman": spearman(ordinal),
                })
    return pairs_out


def operational(runs, prices):
    groups = defaultdict(list)
    for run in runs:
        groups[system_key(run["record"])].append(run)
    out = {}
    for key, group in sorted(groups.items()):
        recs = [g["record"] for g in group]
        lat = [r["latency_ms"] for r in recs if r["latency_ms"] is not None]
        inp = [r["usage"]["input_tokens"] for r in recs if r["usage"]["input_tokens"] is not None]
        outp = [r["usage"]["output_tokens"] for r in recs if r["usage"]["output_tokens"] is not None]
        model_id = recs[0]["model"]["model_id"]
        cost = None
        if prices and model_id in prices.get("models", {}) and len(inp) == len(recs) and len(outp) == len(recs):
            p = prices["models"][model_id]
            cost = {"total": sum(inp) / 1e6 * p["input_per_mtok"] + sum(outp) / 1e6 * p["output_per_mtok"],
                    "currency": prices.get("currency"), "price_table_date": prices.get("date")}
        out[key] = {
            "runs": len(recs),
            "schema_valid_rate": ratio(sum(1 for g in group if g["schema_ok"]), len(group)),
            "integrity_valid_rate": ratio(sum(1 for g in group if g["integrity_ok"]), len(group)),
            "parse_failures": sum(1 for r in recs if r["parse_status"] in ("invalid_json", "empty", "schema_invalid")),
            "retries_total": sum(r["retries"] for r in recs),
            "median_latency_ms": statistics.median(lat) if lat else None,
            "mean_input_tokens": statistics.mean(inp) if inp else None,
            "mean_output_tokens": statistics.mean(outp) if outp else None,
            "cost": cost,
            "note": "Token units are provider-specific and not comparable as computational effort.",
        }
    return out


# --- report --------------------------------------------------------------------

def fmt(v):
    if v is None:
        return "undefined"
    return f"{v:.3f}" if isinstance(v, float) else str(v)


def write_markdown(result, path):
    lines = ["# Benchmark scores", "", f"Primary metric: **{PRIMARY_METRIC}**. "
             "Undefined values are shown as 'undefined', never as 0 or 1.", ""]
    for cap, systems in result["systems_by_capability"].items():
        lines += [f"## {cap} runs", "", "| system | sites | TP | FP | FN | precision | recall | F1 | contextual false alarms | presence F1 | unreviewed | abstention |",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for key, s in systems.items():
            p = s["primary"]
            lines.append(f"| {key} | {s['n_sites']} | {fmt(p['tp'])} | {fmt(p['fp'])} | {fmt(p['fn'])} | {fmt(p['precision'])} | "
                         f"{fmt(p['recall'])} | {fmt(p['f1'])} | {fmt(s['false_alarm_breakdown'].get('contextual_false_alarm', 0.0))} | "
                         f"{fmt(s['presence_recognition']['f1'])} | {fmt(s['unreviewed_findings'])} | {fmt(s['abstention_rate_in_annotated_scope'])} |")
        lines.append("")
    lines += ["## Evidence validity (integrity error counts by code)", ""]
    for key, counts in result["evidence_validity"].items():
        lines.append(f"- {key}: " + (", ".join(f"{c} {k}" for k, c in sorted(counts.items())) or "no errors"))
    lines += ["", "## Operational", ""]
    for key, o in result["operational"].items():
        lines.append(f"- {key}: {o['runs']} runs, schema-valid {fmt(o['schema_valid_rate'])}, integrity-valid {fmt(o['integrity_valid_rate'])}, "
                     f"parse failures {o['parse_failures']}, median latency {fmt(o['median_latency_ms'])} ms")
    if result.get("comparison"):
        c = result["comparison"]
        lines += ["", "## Paired comparison", "", "```", json.dumps(c, indent=2), "```"]
    lines += ["", "No weighted 'best model' score is computed. Report the tradeoffs.", ""]
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def score(runs_dir, annotations_dir, bundles_dir, compare=None, bootstrap=2000, seed=0,
          human_sets=None, price_table=None, iou_threshold=DEFAULT_IOU):
    bundles = find_bundles(bundles_dir)
    refs = load_references(annotations_dir)
    runs = load_runs(runs_dir)
    by_sys = defaultdict(lambda: defaultdict(list))
    validity = defaultdict(lambda: defaultdict(int))
    unscored = []
    for run in runs:
        rec, audit = run["record"], run["audit"]
        key = system_key(rec)
        bundle = bundles.get(rec["prompt_lock"]["bundle_id"])
        run["schema_ok"] = run["integrity_ok"] = False
        if audit is not None and bundle is not None:
            report = validate_audit.validate(audit, bundle.dir)
            run["schema_ok"] = not any(c == "schema" for c, _ in report.errors)
            run["integrity_ok"] = report.ok
            for code, _ in report.errors:
                validity[key][code] += 1
            if not run["schema_ok"]:
                audit = None  # schema-invalid output scores as an empty, failed output
        ann = refs.get(rec["prompt_lock"]["bundle_id"])
        if ann is None or bundle is None:
            unscored.append({"run_id": rec["run_id"], "reason": "no reference annotation" if bundle else "bundle not found"})
            continue
        if ann["bundle_hash"] != bundle.hash:
            raise _lib.UsageError(f"annotation for {ann['bundle_id']} was made on a different bundle version")
        by_sys[key][rec["prompt_lock"]["bundle_id"]].append(dict(score_site(audit, ann), capability=capability(rec)))
    systems_by_cap = defaultdict(dict)
    for key, sites in sorted(by_sys.items()):
        caps = {r["capability"] for runs_ in sites.values() for r in runs_}
        cap = caps.pop() if len(caps) == 1 else "mixed"
        systems_by_cap[cap][key] = summarize_system(sites, iou_threshold)
    result = {
        "primary_metric": PRIMARY_METRIC,
        "iou_threshold": iou_threshold,
        "systems_by_capability": dict(systems_by_cap),
        "evidence_validity": {k: dict(v) for k, v in validity.items()},
        "stability": stability(by_sys),
        "operational": operational(runs, _lib.load_json(price_table) if price_table else None),
        "unscored_runs": unscored,
    }
    if human_sets:
        result["human_variability"] = human_variability(human_sets)
    if compare:
        a, b = compare
        if a not in by_sys or b not in by_sys:
            raise _lib.UsageError(f"--compare systems must be among: {sorted(by_sys)}")
        result["comparison"] = dict(bootstrap_diff(by_sys[a], by_sys[b], bootstrap, seed), a=a, b=b,
                                    note="Paired over sites, not findings or runs. Repeated runs are averaged within a site first.")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", required=True)
    parser.add_argument("--annotations", required=True)
    parser.add_argument("--bundles", required=True)
    parser.add_argument("--out", default=None, help="directory for metrics.json and metrics.md")
    parser.add_argument("--compare", nargs=2, metavar=("SYSTEM_A", "SYSTEM_B"), help="condition/model keys")
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--human-sets", default=None, help="directory of pre_adjudication annotation sets")
    parser.add_argument("--price-table", default=None, help="dated JSON price table supplied by the researcher")
    parser.add_argument("--iou-threshold", type=float, default=DEFAULT_IOU)
    args = parser.parse_args(argv)
    result = score(args.runs, args.annotations, args.bundles, args.compare, args.bootstrap, args.seed,
                   args.human_sets, args.price_table, args.iou_threshold)
    text = json.dumps(result, indent=2, default=list)
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "metrics.json").write_text(text + "\n", encoding="utf-8")
        write_markdown(result, out / "metrics.md")
        print(f"wrote {out / 'metrics.json'} and {out / 'metrics.md'}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    _lib.run_main(main)
