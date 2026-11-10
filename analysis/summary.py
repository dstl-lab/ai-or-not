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
    for question in ("ai_appearance", "confidence", "polish", "quality"):
        if question in done:
            done[question] = pd.to_numeric(done[question], errors="coerce")
            if question == "ai_appearance" and "technical_issue" in done:
                done.loc[done["technical_issue"] == "unable", question] = float("nan")
            aggregates[f"mean_{question}"] = (question, "mean")
    if "ai_generated" in done:
        done["ai_generated"] = done["ai_generated"].map({True: 1, False: 0, "TRUE": 1, "FALSE": 0})
        aggregates["pct_judged_ai"] = ("ai_generated", lambda s: 100 * s.mean())
    rated = [c for c in done.columns if c.startswith("feature_rating__")]
    if rated:
        done[rated] = done[rated].apply(pd.to_numeric, errors="coerce")
        done["mean_rating"] = done[rated].mean(axis=1)
        aggregates["mean_feature_rating"] = ("mean_rating", "mean")
    if "ai_marks__count" in done:
        done["n_marks"] = pd.to_numeric(done["ai_marks__count"], errors="coerce")
        aggregates["mean_spots_marked"] = ("n_marks", "mean")
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
    if cue_cols:
        done[cue_cols] = done[cue_cols].apply(pd.to_numeric, errors="coerce")
        cues = pd.DataFrame({"selected": done[cue_cols].mean()})
        cues = cues.rename(index=lambda c: c.removeprefix("cues__"))
        print("Share of follow-up judgments citing each cue:")
        print((100 * cues).round(0).sort_values("selected", ascending=False).to_string(), "\n")

    if rated:
        features = pd.DataFrame({
            "mean rating 0-10": done[rated].mean().rename(
                lambda c: c.removeprefix("feature_rating__")),
            "% most AI-looking": 100 * done["top_ai_feature"].value_counts(normalize=True),
        }).round(1).fillna(0)
        print("Per feature:")
        print(features.sort_values("mean rating 0-10", ascending=False).to_string(), "\n")

    marks = data["marks"]
    if not marks.empty:
        print("What kind of element participants marked:")
        print(marks["kind"].value_counts().to_string(), "\n")

    if "n_marks" in done and "mean_rating" in done:
        r = done["n_marks"].corr(done["mean_rating"])
        print(f"Correlation between spots marked and mean feature rating: r = {r:.2f}")


if __name__ == "__main__":
    main()
