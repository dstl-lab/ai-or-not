#!/usr/bin/env python3
"""Render a validated audit as a static HTML (or Markdown) report.

    python scripts/render_report.py AUDIT.json --bundle BUNDLE --out report.html
    python scripts/render_report.py AUDIT.json --bundle BUNDLE --out report.md

Everything shown is derived from the audit JSON: counts are computed from its
arrays, boxes are drawn from its locations, and all text (which may contain
page content or model prose) is HTML-escaped. Images are referenced by local
relative paths into the bundle; nothing is fetched. The audit is validated
first and the report states the result.
"""

import argparse
import html
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import validate_audit  # noqa: E402

E = html.escape

CSS = """
:root { color-scheme: light; --ink:#1f2328; --muted:#5b636e; --line:#d8dde3; --bg:#f6f7f9; --card:#fff; --accent:#2f5d8a; --warn:#9a3412; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
main { max-width:1100px; margin:0 auto; padding:24px 16px 64px; }
h1 { font-size:22px; margin:0 0 4px; } h2 { font-size:18px; margin:28px 0 10px; } h3 { font-size:15px; margin:0 0 6px; }
.meta { color:var(--muted); font-size:13px; }
.box { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px 16px; margin:12px 0; }
.scope { border-left:4px solid var(--accent); }
.invalid { border-left:4px solid var(--warn); }
.counts { display:flex; flex-wrap:wrap; gap:8px; margin-top:8px; }
.pill { font-size:12px; border:1px solid var(--line); border-radius:999px; padding:2px 10px; background:var(--bg); }
.grid { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:12px 20px; }
.grid dt { font-size:12px; text-transform:uppercase; letter-spacing:.03em; color:var(--muted); margin-top:6px; }
.grid dd { margin:0; }
ul.tight { margin:4px 0; padding-left:18px; }
q { quotes:"“" "”"; background:#fff6d6; }
table { width:100%; border-collapse:collapse; font-size:14px; }
th, td { text-align:left; vertical-align:top; padding:6px 8px; border-bottom:1px solid var(--line); }
.shot { position:relative; display:inline-block; max-width:100%; margin:6px 0; border:1px solid var(--line); }
.shot img { display:block; max-width:100%; height:auto; }
.mark { position:absolute; border:2px solid #d9480f; background:rgba(217,72,15,.08); }
.mark span { position:absolute; top:-1px; left:-1px; transform:translateY(-100%); background:#d9480f; color:#fff; font-size:11px; padding:0 4px; white-space:nowrap; }
.note { color:var(--muted); font-size:13px; }
@media (max-width:720px) { .grid { grid-template-columns:1fr; } }
"""


def level(obj):
    return f"<b>{E(obj['level'])}</b>: {E(obj['reason'])}"


def loc_text(loc, bundle):
    region = bundle.regions.get(loc["region_id"], {})
    bits = [f"{loc['region_id']} ({region.get('name', 'unknown region')})", f"state {loc['state_id']}"]
    if loc["asset_id"]:
        bits.append(f"image {loc['asset_id']}" + (" with box" if loc["box"] else ", region only (no box)"))
    if loc["selector"]:
        bits.append(f"selector {loc['selector']}")
    if loc["source_ref"]:
        s = loc["source_ref"]
        bits.append(f"source {s['excerpt_id']} lines {s['line_start']}-{s['line_end']}")
    return " · ".join(bits)


def evidence_list(items, fmt="html"):
    rows = []
    for ev in items:
        quote = ev["quote"]
        if fmt == "html":
            q = f' <q>{E(quote)}</q>' if quote else ""
            rows.append(f"<li><code>{E(ev['kind'])}:{E(ev['ref_id'])}</code> {E(ev['description'])}{q}</li>")
        else:
            q = f' "{quote}"' if quote else ""
            rows.append(f"  - `{ev['kind']}:{ev['ref_id']}` {ev['description']}{q}")
    return rows


def shot(bundle, out_dir, asset_id, marks):
    asset = bundle.assets.get(asset_id)
    if asset is None:
        return ""
    src = os.path.relpath(bundle.dir / asset["path"], out_dir)
    boxes = "".join(
        f'<div class="mark" style="left:{b["x"]*100:.2f}%;top:{b["y"]*100:.2f}%;width:{b["width"]*100:.2f}%;height:{b["height"]*100:.2f}%"><span>{E(label)}</span></div>'
        for label, b in marks)
    return f'<div class="shot"><img src="{E(src)}" alt="{E(asset_id)}" loading="lazy">{boxes}</div>'


def counts(audit):
    """Counts derived from the arrays, labeled singular or plural."""
    unassessed = [c for c in audit["coverage"]["features"] if c["status"] == "unassessed"]
    raw = [("finding", "findings", len(audit["findings"])),
           ("contextual exception", "contextual exceptions", len(audit["contextual_exceptions"])),
           ("quality observation", "quality observations", len(audit["quality_observations"])),
           ("exploratory candidate", "exploratory candidates", len(audit["exploratory_candidates"])),
           ("unassessed feature", "unassessed features", len(unassessed))]
    return {(one if n == 1 else many): n for one, many, n in raw}, unassessed


def render_html(audit, bundle, report, out_dir, features):
    c, unassessed = counts(audit)
    cov = audit["coverage"]
    title = f"Slop-feature audit {audit['audit_id']}"
    h = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>",
         f"<title>{E(title)}</title><style>{CSS}</style></head><body><main>",
         f"<h1>{E(title)}</h1>",
         f"<div class='meta'>bundle {E(audit['bundle_id'])} · profile {E(audit['analysis_profile'])} · rubric {E(audit['rubric_version'])} · status <b>{E(audit['status'])}</b></div>"]
    if not report.ok:
        errs = "".join(f"<li><code>{E(code)}</code> {E(msg)}</li>" for code, msg in report.errors)
        h.append(f"<div class='box invalid'><h3>Validation failed</h3><p>This audit has {len(report.errors)} integrity error(s); treat its claims as unverified.</p><ul class='tight'>{errs}</ul></div>")
    unmod = "".join(f"<li>{E(u['modality'])}: {E(u['reason'])}</li>" for u in cov["unassessed_modalities"]) or "<li>none</li>"
    limits = "".join(f"<li>{E(x)}</li>" for x in audit["summary"]["major_limitations"]) or "<li>none stated</li>"
    pills = "".join(f"<span class='pill'>{v} {E(k)}</span>" for k, v in c.items())
    h.append(f"""<div class='box scope'><h3>Scope and limits</h3>
<p>{E(audit['summary']['text'])}</p>
<div class='grid'><div><dt>Assessed modalities</dt><dd>{E(', '.join(cov['assessed_modalities']) or 'none')}</dd>
<dt>Not assessed</dt><dd><ul class='tight'>{unmod}</ul></dd></div>
<div><dt>Major limitations</dt><dd><ul class='tight'>{limits}</ul></dd></div></div>
<div class='counts'>{pills}</div>
<p class='note'>These findings identify features that may contribute to a perceived AI-slop impression. They do not establish who or what made the site, and the ratings are provisional research scales, not probabilities.</p></div>""")

    h.append("<h2>Findings</h2>")
    if not audit["findings"]:
        h.append("<div class='box'><p>No accepted findings in the assessed scope. See the scope, exceptions, and unassessed checks.</p></div>")
    for f in audit["findings"]:
        feat = features.get(f["feature_id"], {"title": "unknown feature"})
        locs = "".join(f"<li>{E(loc_text(l, bundle))}</li>" for l in f["locations"])
        alts = "".join(f"<li>{E(a)}</li>" for a in f["alternative_explanations"])
        lims = "".join(f"<li>{E(x)}</li>" for x in f["limitations"]) or "<li>none stated</li>"
        tags = f" · also {E(', '.join(f['secondary_tags']))}" if f["secondary_tags"] else ""
        shots = "".join(shot(bundle, out_dir, l["asset_id"], [(f["finding_id"], l["box"])] if l["box"] else [])
                        for l in f["locations"] if l["asset_id"])
        h.append(f"""<div class='box'><h3>{E(f['finding_id'])} · {E(f['feature_id'])} {E(feat['title'])}{tags}</h3>
<div class='grid'>
<div><dt>What</dt><dd>{E(f['observation'])}</dd>
<dt>Where ({E(f['scope'])})</dt><dd><ul class='tight'>{locs}</ul></dd>
<dt>Evidence</dt><dd><ul class='tight'>{''.join(evidence_list(f['evidence']))}</ul></dd></div>
<div><dt>Observation confidence</dt><dd>{level(f['observation_confidence'])}</dd>
<dt>Slop association (interpretation)</dt><dd>{level(f['slop_association'])}</dd>
<dt>Contextual fit</dt><dd>{level(f['contextual_fit'])}</dd>
<dt>Consequence</dt><dd>{level(f['communication_or_interaction_consequence'])}</dd>
<dt>Alternative explanations</dt><dd><ul class='tight'>{alts}</ul></dd>
<dt>Codebook evidence status</dt><dd><code>{E(f['codebook_evidence_status'])}</code></dd>
<dt>Limitations</dt><dd><ul class='tight'>{lims}</ul></dd></div></div>{shots}</div>""")

    def simple_table(title, rows, header, empty):
        h.append(f"<h2>{E(title)}</h2>")
        if not rows:
            h.append(f"<p class='note'>{E(empty)}</p>")
            return
        head = "".join(f"<th>{E(x)}</th>" for x in header)
        body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in r) + "</tr>" for r in rows)
        h.append(f"<div class='box'><table><tr>{head}</tr>{body}</table></div>")

    simple_table("Contextual exceptions (present, not counted)", [
        [E(x["exception_id"]), E(x["feature_id"]), E(x["observation"]), E(x["reason_not_counted"]) + "<br>" + E(x["rationale"]),
         "<br>".join(E(loc_text(l, bundle)) for l in x["locations"])] for x in audit["contextual_exceptions"]],
        ["id", "feature", "observation", "why not counted", "where"], "None recorded.")
    simple_table("Quality observations (not slop claims)", [
        [E(q["observation_id"]), E(q["category"]), E(q["observation"]), level(q["consequence"]),
         "<br>".join(E(loc_text(l, bundle)) for l in q["locations"])] for q in audit["quality_observations"]],
        ["id", "category", "observation", "consequence", "where"], "None recorded.")
    simple_table("Exploratory candidates (outside the codebook; not scored)", [
        [E(x["candidate_id"]), E(x["label"]), E(x["observation"]), E(x["why_outside_codebook"])] for x in audit["exploratory_candidates"]],
        ["id", "label", "observation", "why outside codebook"], "None recorded.")
    simple_table("Unassessed checks", [[E(u["feature_id"]), E(features.get(u["feature_id"], {}).get("title", "")), E(u["reason"])] for u in unassessed],
                 ["feature", "title", "reason"], "Every feature in the profile was assessed or not applicable.")
    if audit["untrusted_instructions_observed"]:
        simple_table("Page content addressed to the auditor (recorded, not followed)",
                     [[E(u["ref_kind"]), E(u["ref_id"]), E(u["description"])] for u in audit["untrusted_instructions_observed"]],
                     ["kind", "ref", "description"], "")

    marks = {}
    for group in ("findings", "contextual_exceptions", "quality_observations", "exploratory_candidates"):
        id_key = {"findings": "finding_id", "contextual_exceptions": "exception_id",
                  "quality_observations": "observation_id", "exploratory_candidates": "candidate_id"}[group]
        for item in audit[group]:
            for l in item["locations"]:
                if l["asset_id"] and l["box"]:
                    marks.setdefault(l["asset_id"], []).append((item[id_key], l["box"]))
    if marks:
        h.append("<h2>Annotated screenshots</h2><p class='note'>Boxes are drawn from the audit's normalized coordinates on each image.</p>")
        for asset_id in sorted(marks):
            a = bundle.assets.get(asset_id, {})
            h.append(f"<div class='box'><h3>{E(asset_id)} · state {E(a.get('state_id', '?'))} · scroll y {E(str(a.get('scroll_y', '?')))}</h3>{shot(bundle, out_dir, asset_id, marks[asset_id])}</div>")
    h.append("</main></body></html>")
    return "\n".join(h) + "\n"


def render_md(audit, bundle, report, features):
    c, unassessed = counts(audit)
    lines = [f"# Slop-feature audit {audit['audit_id']}", "",
             f"bundle `{audit['bundle_id']}` · profile `{audit['analysis_profile']}` · rubric {audit['rubric_version']} · status **{audit['status']}**", ""]
    if not report.ok:
        lines += [f"> **Validation failed** ({len(report.errors)} integrity errors); claims are unverified.", ""]
        lines += [f"> - `{code}` {msg}" for code, msg in report.errors] + [""]
    lines += ["## Scope and limits", "", audit["summary"]["text"], "",
              f"- Assessed modalities: {', '.join(audit['coverage']['assessed_modalities']) or 'none'}"]
    lines += [f"- Not assessed: {u['modality']} ({u['reason']})" for u in audit["coverage"]["unassessed_modalities"]]
    lines += [f"- Limitation: {x}" for x in audit["summary"]["major_limitations"]]
    lines += ["- Counts: " + ", ".join(f"{v} {k}" for k, v in c.items()), "",
              "These findings identify features that may contribute to a perceived AI-slop impression; they do not establish who or what made the site.", "",
              "## Findings", ""]
    if not audit["findings"]:
        lines += ["No accepted findings in the assessed scope.", ""]
    for f in audit["findings"]:
        feat = features.get(f["feature_id"], {"title": "unknown feature"})
        lines += [f"### {f['finding_id']} · {f['feature_id']} {feat['title']}", "",
                  f"- **What:** {f['observation']}",
                  f"- **Where ({f['scope']}):** " + "; ".join(loc_text(l, bundle) for l in f["locations"]),
                  "- **Evidence:**", *evidence_list(f["evidence"], "md"),
                  f"- **Interpretation:** slop association {f['slop_association']['level']} ({f['slop_association']['reason']}); "
                  f"fit {f['contextual_fit']['level']} ({f['contextual_fit']['reason']}); "
                  f"consequence {f['communication_or_interaction_consequence']['level']} ({f['communication_or_interaction_consequence']['reason']})",
                  f"- **Alternative explanations:** " + "; ".join(f["alternative_explanations"]),
                  f"- **Observation confidence:** {f['observation_confidence']['level']} ({f['observation_confidence']['reason']}) · evidence status `{f['codebook_evidence_status']}`", ""]
    for title, key, fmt in [("Contextual exceptions", "contextual_exceptions", lambda x: f"- {x['exception_id']} {x['feature_id']}: {x['observation']} ({x['reason_not_counted']}: {x['rationale']})"),
                            ("Quality observations", "quality_observations", lambda x: f"- {x['observation_id']} [{x['category']}]: {x['observation']}"),
                            ("Exploratory candidates (not scored)", "exploratory_candidates", lambda x: f"- {x['candidate_id']} {x['label']}: {x['observation']}")]:
        lines += [f"## {title}", ""] + ([fmt(x) for x in audit[key]] or ["None recorded."]) + [""]
    lines += ["## Unassessed checks", ""] + ([f"- {u['feature_id']}: {u['reason']}" for u in unassessed] or ["None."]) + [""]
    if audit["untrusted_instructions_observed"]:
        lines += ["## Page content addressed to the auditor (recorded, not followed)", ""]
        lines += [f"- {u['ref_kind']} {u['ref_id']}: {u['description']}" for u in audit["untrusted_instructions_observed"]] + [""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("audit")
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--out", required=True, help="report path ending in .html or .md")
    args = parser.parse_args(argv)
    report = validate_audit.validate(args.audit, args.bundle)
    if any(code in ("schema", "invalid_json", "bundle_unreadable") for code, _ in report.errors):
        report.print(sys.stderr)
        raise _lib.UsageError("cannot render an audit that fails schema validation")
    audit = _lib.load_json(args.audit)
    bundle = _lib.Bundle(args.bundle)
    features = _lib.features_by_id()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix == ".md":
        out.write_text(render_md(audit, bundle, report, features), encoding="utf-8")
    else:
        out.write_text(render_html(audit, bundle, report, out.parent.resolve(), features), encoding="utf-8")
    print(f"wrote {out} ({'valid' if report.ok else 'INVALID: ' + str(len(report.errors)) + ' error(s)'})")
    return 0 if report.ok else 1


if __name__ == "__main__":
    _lib.run_main(main)
