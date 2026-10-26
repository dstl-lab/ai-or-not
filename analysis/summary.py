"""First-look summary of the study data.

    uv run --group analysis python -m analysis.summary [--practice]
"""

import argparse

import pandas as pd

from analysis.load import load


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--practice", action="store_true", help="include practice sessions")
    args = parser.parse_args()

    data = load(include_practice=args.practice)
    wide = data["responses_wide"]
    done = wide[wide["completed_at"].astype(bool)].copy()
    sessions = data["sessions"]
    print(f"Participants: {sessions['participant_id'].nunique()}  "
          f"(finished sessions: {sessions['finished_at'].astype(bool).sum()})")
    print(f"Completed site judgments: {len(done)}\n")
    if done.empty:
        print("No completed judgments yet.")
        return

    aggregates = {"n": ("participant_id", "count"),
                  "mean_minutes": ("seconds_on_site", lambda s: s.mean() / 60)}
    for question in ("ai_appearance", "confidence", "polish"):
        if question in done:
            done[question] = pd.to_numeric(done[question], errors="coerce")
            if question == "ai_appearance" and "technical_issue" in done:
                done.loc[done["technical_issue"] == "unable", question] = float("nan")
            aggregates[f"mean_{question}"] = (question, "mean")
    if "ai_generated" in done:
        done["ai_generated"] = done["ai_generated"].map({True: 1, False: 0, "TRUE": 1, "FALSE": 0})
        aggregates["pct_judged_ai"] = ("ai_generated", lambda s: 100 * s.mean())
    if "cohort" not in done:
        done["cohort"] = "unclassified"
    groups = ["cohort", "site_id", "site_title"]
    if "site_commit" in done:
        groups.append("site_commit")
    per_site = done.groupby(groups, dropna=False).agg(**aggregates).round(2)
    with pd.option_context("display.width", 140, "display.max_colwidth", 45):
        print("Per website:")
        print(per_site.to_string(), "\n")

    cue_cols = [c for c in done.columns if c.startswith("cues__")]
    if not cue_cols:
        return
    done[cue_cols] = done[cue_cols].apply(pd.to_numeric, errors="coerce")
    if "ai_generated" in done and "ai_appearance" not in done:
        cues = pd.DataFrame({
            "judged AI": done.loc[done["ai_generated"] == 1, cue_cols].mean(),
            "judged human": done.loc[done["ai_generated"] == 0, cue_cols].mean(),
        })
    else:
        cues = pd.DataFrame({"selected": done[cue_cols].mean()})
    cues = cues.rename(index=lambda c: c.removeprefix("cues__"))
    print("Share of judgments citing each feature:")
    print((100 * cues).round(0).sort_values(cues.columns[0], ascending=False).to_string())


if __name__ == "__main__":
    main()
