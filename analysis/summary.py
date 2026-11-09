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

    rated = [c for c in done.columns if c.startswith("feature_rating__")]
    done["n_marks"] = pd.to_numeric(done["ai_marks__count"], errors="coerce")
    done["mean_rating"] = done[rated].mean(axis=1)  # N/A rows are skipped

    per_site = done.groupby(["site_position", "site_title"]).agg(
        n=("participant_id", "count"),
        mean_spots_marked=("n_marks", "mean"),
        mean_feature_rating=("mean_rating", "mean"),
        mean_polish=("polish", "mean"),
        mean_quality=("quality", "mean"),
        mean_minutes=("seconds_on_site", lambda s: s.mean() / 60),
    ).round(2)
    with pd.option_context("display.width", 140, "display.max_colwidth", 45):
        print("Per website:")
        print(per_site.to_string(), "\n")

    features = pd.DataFrame({
        "mean rating 0-10": done[rated].mean().rename(lambda c: c.removeprefix("feature_rating__")),
        "% most AI-looking": 100 * done["top_ai_feature"].value_counts(normalize=True),
    }).round(1).fillna(0)
    print("Per feature:")
    print(features.sort_values("mean rating 0-10", ascending=False).to_string(), "\n")

    marks = data["marks"]
    if not marks.empty:
        print("What kind of element participants marked:")
        print(marks["kind"].value_counts().to_string(), "\n")

    r = done["n_marks"].corr(done["mean_rating"])
    print(f"Correlation between spots marked and mean feature rating: r = {r:.2f}")


if __name__ == "__main__":
    main()
