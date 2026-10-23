"""Command line: `uv run aiornot <command>`. Run with --help for the list."""

import argparse
import sys
import threading
import webbrowser
from pathlib import Path

from .config import ConfigError, Paths, load_sites
from .db import Database, now
from .export import TABLES, Exporter
from .mirror import is_mirrored, mirror_all
from .questions import load_questions
from .sheets import GwsError, SheetSync, connect_sheet, create_sheet, load_link


def cmd_serve(args, paths):
    sites = load_sites(paths)
    missing = [s for s in sites.study if not is_mirrored(paths, s)]
    if missing:
        print(f"Downloading {len(missing)} study site(s) first...")
        if mirror_all(paths, missing):
            print("Some sites failed to download; re-run `uv run aiornot mirror`.", file=sys.stderr)
            return 1

    import uvicorn

    from .app import create_app

    app = create_app(paths)
    url = f"http://{'localhost' if args.host in ('127.0.0.1', '0.0.0.0') else args.host}:{args.port}"
    if args.host == "0.0.0.0":
        print("Warning: the researcher dashboard has no password; anyone on this network can open it.")
    print(f"\n  Study:      {url}/\n  Dashboard:  {url}/admin\n")
    if not args.no_browser:
        threading.Timer(1.5, webbrowser.open, args=(url,)).start()
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


def cmd_mirror(args, paths):
    sites = load_sites(paths)
    targets = list(sites.pool.values()) if args.all else sites.study
    print(f"Mirroring {len(targets)} site(s) into {paths.mirror_dir}")
    failures = mirror_all(paths, targets, update=args.update)
    print("Pinned commits saved to config/sites.json" + (f"; {failures} failed" if failures else ""))
    return 1 if failures else 0


def cmd_export(args, paths):
    sites, questions = load_sites(paths), load_questions(paths)
    exporter = Exporter(Database(paths.db_file), sites, questions)
    out = Path(args.out) if args.out else paths.data_dir / "exports" / now()[:10]
    out.mkdir(parents=True, exist_ok=True)
    for name in TABLES:
        target = out / f"{name}.csv"
        target.write_text(exporter.csv(name, include_practice=args.practice))
        print(f"  wrote {target}")
    return 0


def cmd_sheet(args, paths):
    try:
        if args.action == "create":
            link = create_sheet(paths, args.title)
            print(f"Created and linked: {link['url']}")
        elif args.action == "connect":
            link = connect_sheet(paths, args.spreadsheet)
            print(f"Linked: {link['title']} ({link['url']})")
        elif args.action == "sync":
            sites, questions = load_sites(paths), load_questions(paths)
            db = Database(paths.db_file)
            sync = SheetSync(db, Exporter(db, sites, questions), paths)
            pending = db.unsynced_visits()
            for key in pending:
                sync.sync_one(*key)
            print(f"Synced {len(pending)} row(s).")
        link = load_link(paths)
        if link:
            print(f"Sheet: {link['title']}\n  {link['url']}")
        else:
            print("No Google Sheet linked. Run `uv run aiornot sheet create`.")
    except GwsError as err:
        print(f"Google Sheets error: {err}", file=sys.stderr)
        return 1
    return 0


def cmd_check(args, paths):
    sites, questions = load_sites(paths), load_questions(paths)
    print(f"Questions: {len(questions.questions)} per site (version {questions.version})")
    print(f"Study sites (version {sites.version}):")
    ok = True
    for i, s in enumerate(sites.study, start=1):
        mirrored = is_mirrored(paths, s)
        ok &= mirrored
        mark = "ok " if mirrored else "MISSING"
        print(f"  {i:>2}. [{mark}] {s.title}  ({s.commit[:7] if s.commit else 'not pinned'})")
    link = load_link(paths)
    print(f"Google Sheet: {link['url'] if link else 'not linked'}")
    return 0 if ok else 1


def main(argv=None):
    parser = argparse.ArgumentParser(prog="aiornot", description="AI-or-not study platform")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("serve", help="run the study app (downloads missing sites first)")
    p.add_argument("--host", default="127.0.0.1", help="use 0.0.0.0 to allow other devices on the network")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("mirror", help="download frozen copies of the study websites")
    p.add_argument("--all", action="store_true", help="mirror the whole pool, not just study sites")
    p.add_argument("--update", action="store_true", help="re-pin each site to its latest commit")
    p.set_defaults(func=cmd_mirror)

    p = sub.add_parser("export", help="write all data tables as CSV files")
    p.add_argument("--out", help="output folder (default: data/exports/<today>)")
    p.add_argument("--practice", action="store_true", help="include practice sessions")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("sheet", help="link or sync the Google Sheet (uses your gws login)")
    sheet_sub = p.add_subparsers(dest="action", required=True)
    s = sheet_sub.add_parser("create", help="create a new spreadsheet and link it")
    s.add_argument("--title", default="AI or Not: study responses")
    s = sheet_sub.add_parser("connect", help="link an existing spreadsheet")
    s.add_argument("spreadsheet", help="spreadsheet URL or id")
    sheet_sub.add_parser("sync", help="push any unsynced answers now")
    sheet_sub.add_parser("status", help="show the linked spreadsheet")
    p.set_defaults(func=cmd_sheet)

    p = sub.add_parser("check", help="validate config and show which sites are downloaded")
    p.set_defaults(func=cmd_check)

    args = parser.parse_args(argv)
    try:
        return args.func(args, Paths.default())
    except ConfigError as err:
        print(f"Config problem: {err}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
