"""Download frozen copies of the study websites into mirror/<site-id>/.

Every DSC 106 final project is a "legacy" GitHub Pages site: GitHub serves the
files in one branch/folder of the repo as-is. Copying that folder at a fixed
commit therefore reproduces the deployed site exactly, and pinning the commit
in config/sites.json guarantees every participant sees the same version even
if the authors keep editing (or delete) their repos.
"""

import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

# References like src="/foo.js" resolve against the server root, which on
# GitHub Pages is <user>.github.io/ but on our server is the app itself.
ROOT_RELATIVE = re.compile(r"""(?:src|href)\s*=\s*["']/(?!/)""")
EXTERNAL_HOST = re.compile(r"""(?:src|href)\s*=\s*["']https?://([^/"']+)""")
STAMP = ".mirrored-commit"


def git(*args, cwd=None):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def latest_commit(repo, branch):
    out = git("ls-remote", f"https://github.com/{repo}.git", f"refs/heads/{branch}")
    if not out:
        raise RuntimeError(f"branch {branch!r} not found in {repo}")
    return out.split()[0]


def fetch_commit(repo, commit, dest, attempts=3):
    """Shallow-fetch a single commit into dest (no full history download).

    Big repos (100+ MB of data files) sometimes drop mid-download, so retry.
    """
    git("init", "-q", str(dest))
    git("remote", "add", "origin", f"https://github.com/{repo}.git", cwd=dest)
    for attempt in range(1, attempts + 1):
        try:
            git("fetch", "-q", "--depth", "1", "origin", commit, cwd=dest)
            break
        except subprocess.CalledProcessError:
            if attempt == attempts:
                raise
            time.sleep(5 * attempt)
    git("checkout", "-q", "FETCH_HEAD", cwd=dest)


def is_mirrored(paths, site):
    stamp = paths.mirror_dir / site.id / STAMP
    return site.commit is not None and stamp.exists() and stamp.read_text().strip() == site.commit


def inspect(site_dir, entry):
    """Things that may make the copy behave differently from the live site."""
    warnings, hosts = [], set()
    entry_file = site_dir / (entry.split("#")[0] or "index.html")
    if entry_file.is_dir():
        entry_file = entry_file / "index.html"
    if not entry_file.exists():
        warnings.append(f"entry page {entry_file.relative_to(site_dir)} does not exist")
    for page in site_dir.rglob("*.html"):
        text = page.read_text(errors="ignore")
        rel = page.relative_to(site_dir)
        if text.startswith("---"):
            warnings.append(f"{rel}: has Jekyll front matter (GitHub may render it differently)")
        if ROOT_RELATIVE.search(text):
            warnings.append(f"{rel}: has root-relative src/href (may 404 when mirrored)")
        hosts.update(EXTERNAL_HOST.findall(text))
    return warnings, sorted(hosts)


def mirror_site(paths, site, update=False):
    """Mirror one site; returns (commit, warnings, external hosts)."""
    commit = site.commit
    if commit is None or update:
        commit = latest_commit(site.repo, site.branch)
    dest = paths.mirror_dir / site.id
    stamp = dest / STAMP
    if not (stamp.exists() and stamp.read_text().strip() == commit):
        with tempfile.TemporaryDirectory() as tmp:
            checkout = Path(tmp) / "repo"
            fetch_commit(site.repo, commit, checkout)
            source = checkout / site.path.strip("/")
            if dest.exists():
                shutil.rmtree(dest)
            # Jekyll (which legacy Pages runs) never publishes dotfiles or _folders.
            shutil.copytree(source, dest, ignore=shutil.ignore_patterns(".*", "_*"))
        stamp.write_text(commit)
    warnings, hosts = inspect(dest, site.entry)
    return commit, warnings, hosts


def pin_commits(paths, commits):
    """Write pinned commits back into config/sites.json, keeping its layout."""
    sites_file = paths.config_dir / "sites.json"
    raw = json.loads(sites_file.read_text())
    for entry in raw["pool"]:
        if entry["id"] in commits:
            entry["commit"] = commits[entry["id"]]
    sites_file.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n")


def mirror_all(paths, sites, update=False, log=print):
    """Mirror the given sites, pin their commits, and return the number of failures."""
    paths.mirror_dir.mkdir(exist_ok=True)
    commits, failures = {}, 0
    for site in sites:
        try:
            commit, warnings, hosts = mirror_site(paths, site, update)
        except (subprocess.CalledProcessError, RuntimeError, OSError) as err:
            failures += 1
            detail = err.stderr.strip() if isinstance(err, subprocess.CalledProcessError) else err
            log(f"  {site.id}: FAILED ({detail})")
            continue
        commits[site.id] = commit
        log(f"  {site.id}: ok @ {commit[:7]}")
        for w in warnings:
            log(f"    warning: {w}")
        if hosts:
            log(f"    references other websites: {', '.join(hosts)}")
    pin_commits(paths, commits)
    return failures
