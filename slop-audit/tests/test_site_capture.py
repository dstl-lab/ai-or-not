"""The one-line URL path: site scope, image budget, control safety, the skill's entry points, and repo wiring."""

import argparse
import os
import re
import subprocess
import sys
import tomllib

import pytest

import _lib
import acquire_url
import bundle_digest
import site_capture as sc
from conftest import BUNDLES, FIXTURES, ROOT, SKILL, load

REPO = ROOT.parent
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


# --- scope -------------------------------------------------------------------

def test_canonical_urls_collapse_index_fragments_and_default_ports():
    assert sc.canonical("https://A.github.io:443/repo/index.html#top") == "https://a.github.io/repo/"
    assert sc.canonical("http://127.0.0.1:8000/page.html?x=1#y") == "http://127.0.0.1:8000/page.html?x=1"


def test_scope_stays_inside_the_project_folder_of_a_shared_host():
    scope = sc.Scope("https://someone.github.io/project/")
    assert scope.contains("https://someone.github.io/project/about.html")
    assert scope.contains("https://someone.github.io/project/sub/deep.html")
    assert not scope.contains("https://someone.github.io/other-project/")      # same host, different repository
    assert not scope.contains("https://example.com/project/")
    assert not scope.contains("http://someone.github.io/project/")             # scheme change
    assert scope.route("https://someone.github.io/project/index.html") == "/project/"
    assert sc.Scope("https://someone.github.io/project/story.html").prefix == "/project/"
    bare = sc.Scope("https://someone.github.io/project")                        # no trailing slash
    assert bare.prefix == "/project/" and bare.contains("https://someone.github.io/project")
    assert bare.contains("https://someone.github.io/project/about.html")
    assert not bare.contains("https://someone.github.io/project-two/") and not bare.contains("https://someone.github.io/other/")


def test_only_page_links_are_followed():
    assert sc.is_page_link("https://x.io/a/") and sc.is_page_link("https://x.io/a/b.html")
    for url in ("https://x.io/report.pdf", "https://x.io/data.csv", "mailto:a@b.c", "javascript:void(0)", "https://x.io/i.png"):
        assert not sc.is_page_link(url), url


# --- image budget --------------------------------------------------------------

def test_tiles_cover_a_page_top_to_bottom_and_spread_when_short_of_budget():
    pos = sc.positions(3000, 800)
    assert pos[0] == 0 and pos[-1] == 2200 and len(pos) == 4
    assert sc.positions(500, 800) == [0]
    assert sc.spread(pos, 0) == [] and sc.spread(pos, 1) == [0] and sc.spread(pos, 9) == pos
    top, middle, bottom = sc.spread(sc.positions(16000, 800), 3)
    assert top == 0 and bottom == 15200 and 5000 < middle < 10500        # top, middle, bottom


def test_budget_gives_every_page_a_top_view_and_the_entry_page_full_coverage():
    alloc, notes = sc.allocate([20000, 3000, 900], budget=64, vh=800)
    used = sum(len(a["desktop"]) + a["mobile"] for a in alloc)
    assert used <= 64 - 12                                     # 12 kept for after-click screenshots
    assert all(a["desktop"] and a["desktop"][0] == 0 for a in alloc)
    assert len(alloc[0]["desktop"]) == len(sc.positions(20000, 800))   # entry page fully covered
    assert alloc[0]["mobile"]
    many, notes = sc.allocate([8000] * 12, budget=64, vh=800)
    assert all(a["desktop"] for a in many) and sum(len(a["desktop"]) + a["mobile"] for a in many) <= 64
    assert any("viewport positions screenshotted" in n for n in notes)
    tiny, _ = sc.allocate([5000] * 5, budget=3, vh=800, mobile=False)
    assert [len(a["desktop"]) for a in tiny] == [1, 1, 1, 0, 0]


# --- controls ------------------------------------------------------------------

def control(sel, text="", section=0, **kw):
    return dict({"selector": sel, "tag": "button", "type": "", "kind": "button", "text": text, "section": section,
                 "submits": False, "disabled": False, "download": False}, **kw)


def test_control_choice_refuses_unsafe_targets_and_spreads_across_sections():
    controls = [control("#a", "Show details", 0), control("#b", "Next", 0), control("#c", "Subscribe", 1, submits=True),
                control("#d", "Delete account", 1), control("#e", "Download", 1, download=True), control("#f", "Off", 2, disabled=True),
                control("#g", "Toggle", 2), control("#h", "Only", 2, tag="select", kind="select",
                                                     options=[{"value": "x", "text": "x", "selected": True}]),
                control("#i", "Next", 0)]
    chosen, extra, blocked, skipped = sc.choose_controls(controls, max_n=2)
    assert [c["selector"] for c in chosen] == ["#a", "#g"]                       # one per section first
    assert {c["selector"] for c in blocked} == {"#c", "#d", "#e"}
    assert {c["selector"] for c, _ in skipped} == {"#f", "#h"}
    reasons = {c["selector"]: why for c, why in extra}
    assert "limit of 2" in reasons["#b"] and "repeats" in reasons["#i"]


def test_plan_masks_withheld_names_in_region_names_and_control_descriptions():
    info = {"metrics": {"page_h": 1600, "vh": 800}, "title": "Story",
            "sections": [{"selector": "#hero", "name": "header: By Ada Example", "tag": "header", "rect": {}}],
            "controls": [control("#bio", "About Ada Example", 0)], "untestable": [], "links": [], "signals": {"charts": 0}}
    pages = [{"url": "https://x.github.io/p/", "route": "/p/", "info": info}]
    args = argparse.Namespace(budget=64, max_controls=10, max_pages=12, no_mobile=False, withhold=["Ada Example"])
    plan = sc.build_plan("https://x.github.io/p/", sc.Scope("https://x.github.io/p/"), pages, [], args, "robots.txt read")
    text = str(plan["pages"])
    assert "Ada" not in text and "[WITHHELD-1]" in text
    assert plan["blinding"]["profile"] == "blinded" and plan["max_images"] == 64
    assert ID.match(plan["bundle_id"]) and ID.match(plan["site_id"])
    assert not any(s.get("full_page") for s in plan["pages"][0]["shots"])
    assert plan["pages"][0]["interactions"][0]["shot_after"] == "if_changed"
    open_args = argparse.Namespace(budget=64, max_controls=10, max_pages=12, no_mobile=True, withhold=[])
    unblinded = sc.build_plan("https://x.github.io/p/", sc.Scope("https://x.github.io/p/"), pages, [], open_args, "")
    assert unblinded["blinding"]["profile"] == "unblinded" and [v["device"] for v in unblinded["viewports"]] == ["desktop"]


# --- the skill's entry points ----------------------------------------------------------

def test_acquire_url_finds_the_adapter_beside_the_skill_and_fails_clearly_without_one(monkeypatch, capsys):
    monkeypatch.delenv(acquire_url.ENV, raising=False)
    assert acquire_url.find_adapter() == ROOT / "integrations" / "capture" / "site_capture.py"
    monkeypatch.setenv(acquire_url.ENV, "/nonexistent/adapter.py")
    assert acquire_url.main(["https://x.test/"]) == 2
    assert "No acquisition adapter" in capsys.readouterr().err


def test_acquire_url_works_through_the_repo_symlink():
    link = REPO / ".claude" / "skills" / "website-slop-audit" / "scripts" / "acquire_url.py"
    out = subprocess.run([sys.executable, str(link), "--help"], capture_output=True, text=True)
    assert out.returncode == 0 and "acquisition adapter" in out.stdout


def test_bundle_digest_lists_real_ids_page_by_page():
    text = bundle_digest.digest(BUNDLES / "scenario-inconsistency")
    m = load(BUNDLES / "scenario-inconsistency/manifest.json")
    assert "data, not instructions" in text
    for rid in [r["region_id"] for r in m["regions"]] + [a["asset_id"] for a in m["assets"]] + [e["event_id"] for e in m["interactions"]]:
        assert rid in text


# --- repo wiring -----------------------------------------------------------------

@pytest.mark.parametrize("link", [".claude/skills/website-slop-audit", ".agents/skills/website-slop-audit"])
def test_agent_skill_links_resolve_to_the_one_skill(link):
    path = REPO / link
    assert path.is_symlink() and not os.path.isabs(os.readlink(path))      # relative, so clones work
    assert path.resolve() == SKILL.resolve() and (path / "SKILL.md").is_file()


def test_skill_frontmatter_stays_portable_and_names_no_browser():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    front = text.split("---")[1]
    keys = [line.split(":")[0] for line in front.strip().splitlines()]
    assert keys == ["name", "description"]
    desc = re.search(r"^description: (.*)$", front, re.M).group(1)
    assert len(desc) <= 1024 and "URL" in desc
    assert not re.search(r"gstack|\$B\b|claude-in-chrome", text, re.I)
    assert len(text.splitlines()) < 500


def test_gemini_command_passes_the_argument_and_injects_the_skill():
    cmd = tomllib.loads((REPO / ".gemini/commands/website-slop-audit.toml").read_text(encoding="utf-8"))
    assert set(cmd) == {"description", "prompt"}
    assert "{{args}}" in cmd["prompt"]
    injected = re.findall(r"@\{([^}]+)\}", cmd["prompt"])
    assert injected == ["slop-audit/website-slop-audit/SKILL.md"] and (REPO / injected[0]).is_file()


def test_site_auto_profile_is_documented():
    prof = _lib.load_profiles()["capture_profiles"]["site-auto"]
    assert prof["max_images"] == sc.MAX_BUDGET == 64


# --- live ----------------------------------------------------------------------------

@pytest.mark.skipif(os.environ.get("SLOP_LIVE_CAPTURE") != "1", reason="live gstack capture; set SLOP_LIVE_CAPTURE=1")
def test_live_site_capture_of_the_multi_page_fixture(tmp_path):
    args = sc.argparse.Namespace(target="/index.html", out=str(tmp_path / "run"), max_pages=12, max_controls=10, budget=64,
                                 single_page=False, no_mobile=False, withhold=["Ada Example"],
                                 serve=str(FIXTURES / "sites/multi-page-site"))
    report, summary = sc.run(args)
    assert report.ok and summary["bundle_valid"]
    m = load(tmp_path / "run/bundle/manifest.json")
    assert (tmp_path / "run/bundle/bundle.lock.json").is_file() and (tmp_path / "run/private.json").is_file()
    routes = {r["ref"]: r["status"] for r in m["coverage"]["routes"]}
    assert routes == {"/": "captured", "/about.html": "captured", "/data.html": "captured", "/team.html": "captured",
                      "/private.html": "skipped", "/archive.html": "failed"}       # robots.txt honored, 404 recorded, nothing off-site
    events = {e["target"]["description"]: e for e in m["interactions"]}
    assert all(e["execution_status"] == "completed" for e in events.values())
    assert any("Replay" in d for d in events)                                       # revealed only after scrolling
    assert "Replayed 1925 to 2025" in str(events[next(d for d in events if "Replay" in d)]["observed_changes"])
    cov = {c["ref"]: c["status"] for c in m["coverage"]["interactions"]}
    assert cov["/: button 'Subscribe'"] == "blocked" and cov["/: button 'Delete account'"] == "blocked"
    assert cov["/data.html: range input 'year'"] == "untested"
    assert len(m["assets"]) <= 64 and not any(a["kind"] == "full_page_screenshot" for a in m["assets"])
    team = [t for t in m["text_spans"] if t["state_id"] in {s["state_id"] for s in m["states"] if s["route"] == "/team.html"}]
    assert any("[WITHHELD-1]" in t["text"] for t in team) and not any("Ada Example" in t["text"] for t in m["text_spans"])
    assert m["blinding"]["known_leakage"]                                           # the name is still in the pixels
