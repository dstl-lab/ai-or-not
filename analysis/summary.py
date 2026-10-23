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
    done = wide[wide["completed_at"].astype(bool)]
    sessions = data["sessions"]
    print(f"Participants: {sessions['participant_id'].nunique()}  "
          f"(finished sessions: {sessions['finished_at'].astype(bool).sum()})")
    print(f"Completed site judgments: {len(done)}\n")
    if done.empty:
        print("No completed judgments yet.")
        return

    per_site = done.groupby(["site_position", "site_title"]).agg(
        n=("participant_id", "count"),
        pct_judged_ai=("ai_generated", lambda s: round(100 * s.mean())),
        mean_confidence=("confidence", "mean"),
        mean_polish=("polish", "mean"),
        mean_minutes=("seconds_on_site", lambda s: s.mean() / 60),
    ).round(2)
    with pd.option_context("display.width", 140, "display.max_colwidth", 45):
        print("Per website:")
        print(per_site.to_string(), "\n")

    cue_cols = [c for c in done.columns if c.startswith("cues__")]
    cues = pd.DataFrame({
        "judged AI": done.loc[done["ai_generated"] == True, cue_cols].mean(),  # noqa: E712
        "judged human": done.loc[done["ai_generated"] == False, cue_cols].mean(),  # noqa: E712
    }).rename(index=lambda c: c.removeprefix("cues__"))
    print("Share of judgments citing each feature:")
    print((100 * cues).round(0).sort_values("judged AI", ascending=False).to_string())


if __name__ == "__main__":
    main()
