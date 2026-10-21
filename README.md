# AI or Not: website perception study

A study platform for the Data Science teaching & learning lab. Participants (students who have
taken DSC 106) explore real DSC 106 final-project websites and answer closed-ended questions
about whether each one looks AI-generated, and why.

The website is on the left and fully interactive. The questions sit in a panel on the right.

## Setup (first time on a computer)

**1. Install the tools.** You need git and [uv](https://docs.astral.sh/uv/). uv installs the
right Python version by itself.

- macOS / Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh` (on a Mac, run
  `xcode-select --install` first if `git --version` says git is missing)
- Windows: install [Git for Windows](https://git-scm.com/download/win), then in PowerShell:
  `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

Open a new terminal afterwards so the `uv` command is found.

**2. Get the code and start the app.**

```bash
git clone https://github.com/dstl-lab/ai-or-not.git
cd ai-or-not
uv run aiornot serve
```

The first run installs dependencies, then downloads the 10 study websites (~1.6 GB; allow
10–20 minutes). Every computer gets byte-identical copies, because the exact version
(git commit) of every site is pinned in `config/sites.json`. The app then opens
http://localhost:8000.

**3. Check it.** `uv run aiornot check` should list all 10 sites as `ok`. Then run a practice
session (see below) before the first real participant.

Answers are stored on this computer in `data/study.db`. To also mirror them to the lab's Google
Sheet, see [Google Sheet](#google-sheet-optional).

## Running a session

1. Start the server (`uv run aiornot serve`) and check that the laptop is online. The sites load
   D3 and fonts from the internet.
2. **Do a practice run first:** enter any ID, tick *Practice run*, and click through a site or two.
   Practice sessions are flagged and left out of exports.
3. Enter the participant's ID (e.g. `P01`; no names) and click **Start session**. Hand over the laptop.
4. The participant explores each site for about 4–5 minutes and answers the questions. **Next** unlocks
   once every question for that site is answered. They can go back to earlier sites and change
   answers until they click **Finish** on the last site.
5. Open **Researcher dashboard** (http://localhost:8000/admin) to watch progress, check the Google
   Sheet sync, and download CSVs.

If the browser is closed mid-session, reopen the session from the dashboard (**Resume**). Every
answer is saved the moment it's clicked.

## Google Sheet (optional)

SQLite is the main store; the Sheet is a live, shared copy for the team. Each completed site
becomes one row. If a participant edits answers later, that row is updated in place. Sync
failures (e.g. offline) are retried automatically; the dashboard shows the status.

**One-time setup per computer:**

1. Install the Google Workspace CLI (`gws`): `brew install googleworkspace-cli`.
   Watch out: `brew install gws` installs an unrelated tool with the same command name.
2. Sign in: `gws auth login`. If it asks for an OAuth client, run `gws auth setup` first;
   that step needs a Google Cloud project, as described in the CLI's own documentation.
3. Link a spreadsheet, then restart the server:
   - **The lab's existing Sheet:** ask its owner to share it with your Google account as
     *Editor* and send you the link, then run `uv run aiornot sheet connect "<sheet link>"`.
   - **A new Sheet of your own:** `uv run aiornot sheet create` makes
     "AI or Not: study responses" in your Drive.

The link is saved per computer in `data/sheets.json` (not in git, like all study data), which is
why each computer links once. `uv run aiornot check` shows which Sheet is linked.

## Using more than one laptop

Each laptop keeps its own `data/study.db`. To keep things combined:

- Link every laptop to the **same** Google Sheet (above). Rows from all laptops land there
  together, each tagged with its participant and session id.
- Give participants IDs that are unique across laptops (e.g. `A01…` on one, `B01…` on the other).
- For the full data (including answer-change history), export CSVs from each laptop
  (`uv run aiornot export`) or collect each `data/study.db`.

## Backing up the websites

The sites are downloaded from their authors' GitHub repos. If an author deletes a repo, it can't
be downloaded again. Once all 10 are downloaded, zip the `mirror/` folder and keep it with the
lab's files. Unzipping it into a fresh checkout skips the download, and `uv run aiornot check`
confirms the copies match the pinned versions.

## Changing the study

| To change… | Edit | Then |
|---|---|---|
| The questions | `config/questions.json` | restart the server |
| Which sites, or their order | `study_sites` in `config/sites.json` (ids from its `pool`) | `uv run aiornot mirror`, restart |
| Refresh sites to their authors' latest version | — | `uv run aiornot mirror --update` |

Question types: `boolean`, `single` (multiple choice), `multi` (multi-select), `scale` (e.g. 1–5).
Each session records the question and site versions it used, so changes mid-study stay traceable.
Avoid renaming option `value`s after data collection starts. Labels are safe to reword.

## Data and analysis

- **Dashboard → Download data**, or `uv run aiornot export`, writes four CSV tables
  (described in [docs/data-dictionary.md](docs/data-dictionary.md)).
- For pandas: `uv run --group analysis python -m analysis.summary` prints a first-look summary,
  and `analysis/load.py` loads every table as a DataFrame.
- Back up `data/study.db` after each session day. It's the complete record, including every answer change.

## Commands

| Command | What it does |
|---|---|
| `uv run aiornot serve` | Run the study app (add `--no-browser`, `--port 8001`) |
| `uv run aiornot check` | Validate config; show which sites are downloaded |
| `uv run aiornot mirror` | Download/refresh the study sites (`--all` for the full pool) |
| `uv run aiornot export` | Write all CSVs to `data/exports/<date>/` |
| `uv run aiornot sheet create\|connect\|sync\|status` | Manage the Google Sheet link |
| `uv run pytest` | Run the tests |

## How it works

- **Sites are frozen copies.** Every DSC 106 project is a static GitHub Pages site served straight
  from its repo, so the app downloads each repo at a pinned commit (`config/sites.json`) and serves
  it from `/sites/<id>/`. Every participant sees exactly the same version, even if authors change
  or delete their repos. Because the copies come from the app's own origin, a future version can
  also observe in-site navigation (for page-triggered questions).
- **Site identity is hidden.** Participants see "Website 3 of 10", never the project title or URL.
  Links that leave a site open in a new tab so the study page stays put.
- **Code layout:** `aiornot/` (Python: `app.py` API, `db.py` SQLite, `sheets.py` sync,
  `export.py` CSV tables, `mirror.py` site copies), `web/` (plain HTML/CSS/JS, no build step),
  `config/` (sites and questions), `analysis/` (pandas helpers), `docs/PLAN.md` (design decisions).
