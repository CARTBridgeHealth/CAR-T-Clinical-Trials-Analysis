"""
update_readme.py
----------------
Rewrite the generated blocks of README.md from the data files, so the README
tracks the monthly refresh instead of being hand-edited and drifting.

Two blocks, each delimited by HTML comment markers:

  TRIALS      — counted from data/trial_figures.json. Moves every month.
  COMPARISON  — from data/country_comparison.json, which is manually
                maintained. The numbers only change when a human edits that
                file; this script just keeps the README in step with it and
                prints its as_of date rather than inventing a fresh one.

Anything outside the markers is left exactly as written.
"""

import json
import os
import re

BASE       = os.path.join(os.path.dirname(__file__), "..")
README     = os.path.join(BASE, "README.md")
STATS      = os.path.join(BASE, "data", "trial_figures.json")
COMPARISON = os.path.join(BASE, "data", "country_comparison.json")

FLAGS = {"China": "🇨🇳", "USA": "🇺🇸", "Canada": "🇨🇦", "Germany": "🇩🇪",
         "UK": "🇬🇧", "Japan": "🇯🇵", "India": "🇮🇳"}
# Countries shown in the README table — a short list, not all of them.
README_ROWS = ["China", "USA", "Canada", "Germany"]


def block(name, body):
    return f"<!-- BEGIN:{name} -->\n{body}\n<!-- END:{name} -->"


def replace_block(text, name, body):
    pattern = re.compile(
        rf"<!-- BEGIN:{name} -->.*?<!-- END:{name} -->", re.DOTALL)
    if not pattern.search(text):
        raise SystemExit(
            f"README.md has no <!-- BEGIN:{name} --> ... <!-- END:{name} --> "
            f"markers. Add them around the block this script should own.")
    return pattern.sub(lambda _: block(name, body), text)


def trials_block(s):
    g = s["growth"]
    first_year, first = g["years"][0], g["trials"][0]
    # Last complete year: the current one is still filling up.
    idx = max(i for i, y in enumerate(g["years"]) if y < int(s["generated_utc"][:4]))
    peak_year, peak = g["years"][idx], g["trials"][idx]

    c = s["by_country"]
    pairs = sorted(zip(c["labels"], c["all"]), key=lambda p: -p[1])[:2]
    (top, top_n), (second, second_n) = pairs

    phases = dict(zip(s["phase"]["labels"], s["phase"]["counts"]))
    p1 = phases.get("Phase 1", 0)

    return (
        f"### Clinical Trials · {s['total_trials']:,} records · {s['data_month']}\n"
        f"\n"
        f"- CAR-T trial starts grew from {first} in {first_year} to "
        f"**{peak} in {peak_year}**\n"
        f"- **{top} leads globally** with {top_n:,} trials; "
        f"{second} follows with {second_n:,}\n"
        f"- Phase 1 trials dominate ({p1:,} trials) — field still largely "
        f"pre-commercial\n"
        f"- **{s['recruiting_pct']}% of trials actively recruiting** — "
        f"rapid expansion continuing\n"
        f"\n"
        f"> Counts above are regenerated from `data/trial_figures.json` on every "
        f"monthly refresh.\n"
        f"> {s['missing_country']} trials "
        f"({round(100 * s['missing_country'] / s['total_trials'])}%) list no "
        f"country, so country counts are a lower bound."
    )


def _list(names):
    if len(names) < 2:
        return names[0] if names else "none"
    return ", ".join(names[:-1]) + " and " + names[-1]


def _n_centers(c):
    return sum(r.get("derived_from_centers", 0) for r in c["countries"])


def _verification(c):
    v = c.get("verification")
    if not v:
        return ""
    done = v["centres_sourced"] + v["researched_sourced"]
    total = v["centres_total"] + v["researched_total"]
    if done == 0:
        return ("Figures are indicative estimates from our centre research — "
                "we are adding a citation to each one. Ask for the basis of any "
                "figure you need to rely on.")
    if done < total:
        return (f"{done} of {total} figures now cite a source; the remainder are "
                f"indicative estimates.")
    return f"All {total} figures cite a documented source."


def comparison_block(c):
    def money(n):
        return f"${round(n / 1000)}K"

    def weeks(lo, hi):
        return f"{lo} weeks" if lo == hi else f"{lo}–{hi} weeks"

    rows = []
    for name in README_ROWS:
        r = next((x for x in c["countries"] if x["country"] == name), None)
        if r is None:
            continue
        cost = f"{money(r['cost_low_usd'])}–{money(r['cost_high_usd'])}"
        wait = weeks(r["wait_low_weeks"], r["wait_high_weeks"])
        prod = str(r["approved_products"])
        if r.get("approved_products_note"):
            prod += f" ({r['approved_products_note']})"
        if r.get("highlight"):
            cost, wait, prod = f"**{cost}**", f"**{wait}**", f"**{prod}**"
        rows.append(f"| {FLAGS.get(name, '')} {name} | {cost} | {wait} | {prod} |")

    return (
        f"### Global Treatment Comparison · {c['as_of']}\n"
        f"\n"
        f"| Country | All-In Cost | Wait Time | Approved Products |\n"
        f"|---|---|---|---|\n"
        + "\n".join(rows) + "\n"
        f"\n"
        f"> Costs and wait times for {_list(c.get('centre_derived_countries', []))} "
        f"are the range across the {_n_centers(c)} named hospitals in "
        f"`data/treatment_centers.csv`. {_list(c.get('manual_countries', []))}, "
        f"and the approved-product, insurance and solid-tumour columns, are "
        f"researched estimates. Nothing here auto-updates — last reviewed "
        f"{c['as_of']}.\n"
        f">\n"
        f"> {_verification(c)}"
    )


def main():
    with open(STATS, encoding="utf-8") as f:
        stats = json.load(f)
    with open(COMPARISON, encoding="utf-8") as f:
        comparison = json.load(f)
    with open(README, encoding="utf-8") as f:
        text = f.read()

    updated = replace_block(text, "TRIALS", trials_block(stats))
    updated = replace_block(updated, "COMPARISON", comparison_block(comparison))

    # Two counts live in running prose rather than a block, so they are matched
    # by shape instead. Both must stay in step with the trial total.
    total = f"{stats['total_trials']:,}"
    for pattern, repl in [
        (r"\*\*[\d,]+ real-world CAR-T clinical trials\*\*",
         f"**{total} real-world CAR-T clinical trials**"),
        (r"\| [\d,]+ trial records \(auto-updated monthly\) \|",
         f"| {total} trial records (auto-updated monthly) |"),
    ]:
        if not re.search(pattern, updated):
            raise SystemExit(f"README.md: expected text matching {pattern!r}. "
                             "Update this script if the wording changed.")
        updated = re.sub(pattern, repl, updated)

    if updated == text:
        print("README.md already current — no change.")
        return
    with open(README, "w", encoding="utf-8") as f:
        f.write(updated)
    print(f"README.md updated → {stats['total_trials']:,} trials, "
          f"{stats['data_month']}; comparison as of {comparison['as_of']}")


if __name__ == "__main__":
    main()
