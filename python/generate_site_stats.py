"""
generate_site_stats.py
----------------------
Compute every figure the public pages display from cart_trials_clean.csv and
write them to data/site_stats.json. The pages read that file at load, so the
websites track the monthly data refresh instead of drifting out of date.

Every value here is counted from the CSV. Nothing is estimated. Trials with no
country listed are counted nowhere, so country counts are a lower bound; the
JSON records how many those are in `missing_country` so the pages can say so.
"""

import json
import os

import pandas as pd

BASE      = os.path.join(os.path.dirname(__file__), "..")
CLEAN_CSV = os.path.join(BASE, "data", "cart_trials_clean.csv")
OUT_JSON  = os.path.join(BASE, "data", "site_stats.json")

# Chart label order, mirrored exactly by the arrays the pages consume.
STATUS_LABELS = ["Recruiting", "Unknown", "Not Yet Recruiting", "Completed",
                 "Active (not recruiting)", "Terminated", "Other"]
STATUS_KEYS   = ["RECRUITING", "UNKNOWN", "NOT_YET_RECRUITING", "COMPLETED",
                 "ACTIVE_NOT_RECRUITING", "TERMINATED"]

PHASE_LABELS  = ["Early Phase 1", "Phase 1", "Phase 1/2", "Phase 2",
                 "Phase 2/3", "Phase 3", "Phase 4"]

# Display name -> substring matched against the pipe-joined countries column.
COUNTRIES = [("China", "China"), ("USA", "United States"),
             ("UK", "United Kingdom"), ("France", "France"),
             ("Germany", "Germany"), ("Canada", "Canada"),
             ("Australia", "Australia"), ("Japan", "Japan"),
             ("Israel", "Israel"), ("S.Korea", "Korea")]

FIRST_YEAR, LAST_YEAR = 2010, 2026


def build(df: pd.DataFrame) -> dict:
    total = len(df)
    countries_col = df["countries"].fillna("")
    missing_country = int((countries_col.str.strip() == "").sum())

    # ── Status: fixed label order, everything else folded into "Other" ──
    counts = df["status"].value_counts()
    status = [int(counts.get(k, 0)) for k in STATUS_KEYS]
    status.append(total - sum(status))

    # ── Phase: trial counts and mean enrolment ──
    phase_counts, phase_enrol = [], []
    for label in PHASE_LABELS:
        rows = df[df["phase"] == label]
        enrol = rows["enrollment"].dropna()
        phase_counts.append(int(len(rows)))
        phase_enrol.append(int(round(enrol.mean())) if len(enrol) else 0)

    # ── Country: counted per status, never scaled from the total ──
    by_country = {"labels": [], "all": [], "recruiting": [], "completed": []}
    for label, needle in COUNTRIES:
        rows = df[countries_col.str.contains(needle, regex=False)]
        by_country["labels"].append(label)
        by_country["all"].append(int(len(rows)))
        by_country["recruiting"].append(int((rows["status"] == "RECRUITING").sum()))
        by_country["completed"].append(int((rows["status"] == "COMPLETED").sum()))

    # ── Growth by start year, split the same three ways as the page filter ──
    years = list(range(FIRST_YEAR, LAST_YEAR + 1))
    in_range = df[df["start_year"].between(FIRST_YEAR, LAST_YEAR)]

    def per_year(rows):
        counts_by_year = rows["start_year"].value_counts()
        return [int(counts_by_year.get(y, 0)) for y in years]

    growth = {
        "years":      years,
        "trials":     per_year(in_range),
        "recruiting": per_year(in_range[in_range["status"] == "RECRUITING"]),
        "completed":  per_year(in_range[in_range["status"] == "COMPLETED"]),
    }

    recruiting = int(counts.get("RECRUITING", 0))
    return {
        "generated_utc":   pd.Timestamp.now("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_month":      pd.Timestamp.now("UTC").strftime("%B %Y"),
        "total_trials":    total,
        "recruiting":      recruiting,
        "recruiting_pct":  round(100 * recruiting / total),
        "missing_country": missing_country,
        "status":          {"labels": STATUS_LABELS, "data": status},
        "phase":           {"labels": PHASE_LABELS,
                            "counts": phase_counts,
                            "avg_enrollment": phase_enrol},
        "by_country":      by_country,
        "growth":          growth,
    }


def main():
    df = pd.read_csv(CLEAN_CSV, low_memory=False)
    stats = build(df)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
        f.write("\n")

    print(f"Saved → {OUT_JSON}")
    print(f"  {stats['total_trials']} trials, {stats['recruiting_pct']}% recruiting")
    print(f"  {stats['missing_country']} trials list no country (counted nowhere)")
    print(f"  top countries: "
          + ", ".join(f"{l} {n}" for l, n in
                      zip(stats['by_country']['labels'][:3],
                          stats['by_country']['all'][:3])))


if __name__ == "__main__":
    main()
