"""
plot_carnk_growth.py
--------------------
Chart CAR-NK trial starts per year (2017-2026) from carnk_trials_clean.csv.
Renders a LinkedIn-sized PNG (1200x1200, square crops well in-feed).

Colors are the validated reference categorical slot 1 (blue). Planned starts
reuse that same hue with a hatch texture rather than a second colour, so the
"started vs planned" split survives colour-vision deficiency and greyscale.
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BASE      = os.path.join(os.path.dirname(__file__), "..")
CLEAN_CSV = os.path.join(BASE, "data", "carnk_trials_clean.csv")
OUT_PNG   = os.path.join(BASE, "carnk_trial_growth.png")

BLUE   = "#2a78d6"   # categorical slot 1, light mode
INK    = "#0b0b0b"   # text-primary
MUTED  = "#52514e"   # text-secondary
GRID   = "#e3e2de"
SURF   = "#fcfcfb"   # surface-1


def load_counts():
    inc = pd.read_csv(CLEAN_CSV).query("included")
    inc = inc[inc["start_date"].notna()]
    d = pd.DataFrame({
        "year": inc["start_date"].astype(str).str.slice(0, 4).astype(int),
        "type": inc["start_date_type"].fillna("ACTUAL"),
    })
    d = d[(d.year >= 2017) & (d.year <= 2026)]
    actual  = d[d.type == "ACTUAL"].groupby("year").size()
    planned = d[d.type != "ACTUAL"].groupby("year").size()
    years = list(range(2017, 2027))
    return (years,
            [int(actual.get(y, 0)) for y in years],
            [int(planned.get(y, 0)) for y in years])


def main():
    years, actual, planned = load_counts()
    total = [a + p for a, p in zip(actual, planned)]

    fig, ax = plt.subplots(figsize=(10, 10), dpi=120)
    fig.patch.set_facecolor(SURF)
    ax.set_facecolor(SURF)

    # 2px surface gap between stacked segments: draw planned with a small offset
    ax.bar(years, actual, width=0.62, color=BLUE, zorder=3, label="Started")
    ax.bar(years, planned, width=0.62, bottom=[a + 0.35 for a in actual],
           facecolor=SURF, edgecolor=BLUE, linewidth=1.6, hatch="////",
           zorder=3, label="Start date not confirmed")

    for x, t in zip(years, total):
        ax.text(x, t + 1.6, str(t), ha="center", va="bottom",
                fontsize=15, fontweight="bold", color=INK, zorder=4)

    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=GRID, linewidth=1)
    ax.xaxis.grid(False)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)

    ax.set_xticks(years)
    ax.set_xticklabels(years, fontsize=14, color=MUTED)
    ax.tick_params(axis="y", labelsize=13, colors=MUTED, length=0)
    ax.set_ylim(0, max(total) * 1.18)
    ax.set_ylabel("CAR-NK trials starting", fontsize=14, color=MUTED, labelpad=12)

    # Title block lives in figure coords so it can never collide with the axes.
    fig.text(0.10, 0.945, "CAR-NK trial starts have\naccelerated sharply",
             fontsize=28, fontweight="bold", color=INK,
             va="top", linespacing=1.22)
    fig.text(0.10, 0.833,
             "179 interventional CAR-NK trials registered worldwide.\n"
             "93% are still phase 1 or earlier; none have reached phase 3.",
             fontsize=14.5, color=MUTED, va="top", linespacing=1.5)

    leg = ax.legend(loc="upper left", fontsize=13.5, frameon=False,
                    handlelength=1.5, borderpad=0.9)
    for t in leg.get_texts():
        t.set_color(MUTED)

    fig.text(0.072, 0.045,
             "Source: ClinicalTrials.gov, accessed 24 Sep 2026. Interventional "
             "studies only; excludes NK-92-derived,\nCAR-NKT and CAR-T-only "
             "studies. Hatched = registry start date never confirmed by the sponsor.",
             fontsize=11.5, color=MUTED, linespacing=1.5)

    fig.subplots_adjust(left=0.10, right=0.96, top=0.755, bottom=0.14)
    fig.savefig(OUT_PNG, facecolor=SURF)
    print(f"Saved → {OUT_PNG}")
    print(f"  years   {years}")
    print(f"  started {actual}")
    print(f"  planned {planned}")


if __name__ == "__main__":
    main()
