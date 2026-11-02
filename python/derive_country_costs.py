"""
derive_country_costs.py
-----------------------
Recompute country cost and wait-time ranges in data/country_comparison.json
from data/treatment_centers.csv, so the headline figures trace back to named
hospitals instead of standing alone.

Why this exists: the published USA range was $488K-$760K while no centre in
treatment_centers.csv charged more than $650K or less than $400K. Two
hand-maintained sources for the same quantity had drifted apart. Deriving one
from the other makes that impossible.

What this is NOT: automatic. No public source publishes CAR-T prices, and
treatment_centers.csv is itself researched by hand. This script only enforces
that the country table agrees with the centre data underneath it, and records
which countries that applies to.

Countries with no centre rows (currently Germany, UK, Japan, India) keep their
researched figures and are listed in `manual_countries` so the page can say so.
Centres with a non-numeric cost (e.g. "Covered (wait list)") contribute their
wait time but not their cost.
"""

import json
import os
import re

import pandas as pd

BASE       = os.path.join(os.path.dirname(__file__), "..")
CENTERS    = os.path.join(BASE, "data", "treatment_centers.csv")
COMPARISON = os.path.join(BASE, "data", "country_comparison.json")

COST_RE = re.compile(r"([\d,]+)\s*-\s*([\d,]+)")


def parse_cost(value):
    """'50,000-80,000' -> (50000, 80000). Returns None if not a numeric range."""
    m = COST_RE.search(str(value))
    if not m:
        return None
    return int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))


def derive(centers: pd.DataFrame) -> dict:
    out = {}
    for country, rows in centers.groupby("country"):
        costs, waits = [], []
        for _, r in rows.iterrows():
            parsed = parse_cost(r["est_cost_usd"])
            if parsed:
                costs.extend(parsed)
            if pd.notna(r["wait_weeks"]):
                waits.append(int(r["wait_weeks"]))
        entry = {"n_centers": int(len(rows)),
                 "centers": sorted(rows["hospital"].tolist())}
        if costs:
            entry["cost_low_usd"], entry["cost_high_usd"] = min(costs), max(costs)
        if waits:
            entry["wait_low_weeks"], entry["wait_high_weeks"] = min(waits), max(waits)
        out[country] = entry
    return out


def main():
    centers = pd.read_csv(CENTERS)
    derived = derive(centers)

    with open(COMPARISON, encoding="utf-8") as f:
        comparison = json.load(f)

    changes, centre_derived, manual = [], [], []
    for row in comparison["countries"]:
        name = row["country"]
        d = derived.get(name)
        if not d or "cost_low_usd" not in d:
            manual.append(name)
            row.pop("derived_from_centers", None)
            continue

        centre_derived.append(name)
        for field in ("cost_low_usd", "cost_high_usd",
                      "wait_low_weeks", "wait_high_weeks"):
            if field in d and row.get(field) != d[field]:
                changes.append(f"  {name} {field}: {row.get(field)} -> {d[field]}")
                row[field] = d[field]
        row["derived_from_centers"] = d["n_centers"]

    comparison["centre_derived_countries"] = sorted(centre_derived)
    comparison["manual_countries"] = sorted(manual)

    with open(COMPARISON, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Derived from {len(centers)} centres across "
          f"{len(centre_derived)} countries: {', '.join(sorted(centre_derived))}")
    print(f"Still researched (no centre data): {', '.join(sorted(manual)) or 'none'}")
    if changes:
        print("\nChanged:")
        print("\n".join(changes))
    else:
        print("\nNo changes — country table already matches the centre data.")


if __name__ == "__main__":
    main()
