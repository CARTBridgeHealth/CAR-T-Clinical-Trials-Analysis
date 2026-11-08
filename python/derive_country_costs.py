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
PRODUCTS   = os.path.join(BASE, "data", "approved_products.csv")
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
        sourced = rows["source"].fillna("").str.strip().ne("") \
            if "source" in rows else pd.Series(False, index=rows.index)
        entry = {"n_centers": int(len(rows)),
                 "n_sourced": int(sourced.sum()),
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

    # Approved-product counts are counted from approved_products.csv, not typed
    # into the JSON. China carried a hand-entered 9 against a six-row list for
    # months, and it reached the website and the investor deck unchallenged.
    products = pd.read_csv(PRODUCTS)
    product_counts = products["country"].value_counts().to_dict()

    with open(COMPARISON, encoding="utf-8") as f:
        comparison = json.load(f)

    changes, centre_derived, manual = [], [], []
    for row in comparison["countries"]:
        name = row["country"]

        counted = product_counts.get(name)
        if counted is not None and row.get("approved_products") != counted:
            changes.append(
                f"  {name} approved_products: {row.get('approved_products')} "
                f"-> {counted}")
            row["approved_products"] = counted
        # "most globally" only holds while China leads outright.
        if name == "China" and counted is not None:
            top = max(product_counts.values())
            if counted < top or list(product_counts.values()).count(top) > 1:
                row.pop("approved_products_note", None)

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
        row["centers_with_source"] = d["n_sourced"]

    comparison["centre_derived_countries"] = sorted(centre_derived)
    comparison["manual_countries"] = sorted(manual)

    # Verification tally, so the page can state how much of this table has a
    # documented source rather than leaving the reader to assume.
    total_centres = int(len(centers))
    sourced_centres = int(centers["source"].fillna("").str.strip().ne("").sum()) \
        if "source" in centers else 0
    researched_total = len(manual)
    researched_sourced = sum(
        1 for r in comparison["countries"]
        if r["country"] in manual and str(r.get("source", "")).strip()
    )
    comparison["verification"] = {
        "centres_total":      total_centres,
        "centres_sourced":    sourced_centres,
        "researched_total":   researched_total,
        "researched_sourced": researched_sourced,
    }

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
