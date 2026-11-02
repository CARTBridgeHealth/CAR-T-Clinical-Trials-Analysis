"""
make_xhs_cards.py
-----------------
Render Xiaohongshu cover cards from data/trial_figures.json.

Sized 1080x1440 (3:4), the ratio that fills a phone screen in the XHS feed.
Type is far larger than a desktop chart would use because these are read at
thumbnail size first — if a number isn't legible in the feed, the post doesn't
get opened.

Re-run after the monthly refresh and the cards update themselves, so the
numbers on social never drift from the site.

Cards:
  1  headline trial count + China/USA split
  2  disease breakdown bar chart

Output: xhs_cards/card1_total.png, card2_disease.png
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

BASE    = os.path.join(os.path.dirname(__file__), "..")
FIGURES = os.path.join(BASE, "data", "trial_figures.json")
OUT_DIR = os.path.join(BASE, "xhs_cards")

# XHS canvas: 1080x1440 at 120 dpi
W_IN, H_IN, DPI = 9, 12, 120

# Dark ground with one accent reads well in a busy feed.
BG     = "#0f1e1c"
INK    = "#ffffff"
MUTED  = "#8fa8a3"
ACCENT = "#2ec4a6"
RED    = "#e8614d"
BLUE   = "#4a9fe0"

CJK = next((n for n in ("Microsoft YaHei", "Microsoft JhengHei", "SimHei")
            if any(f.name == n for f in font_manager.fontManager.ttflist)), None)
if CJK:
    # The CJK face must come FIRST: matplotlib picks one font per text run
    # rather than falling back per glyph, so a Latin-first list renders every
    # Chinese character as a tofu box. YaHei carries Latin digits too.
    plt.rcParams["font.sans-serif"] = [CJK, "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def new_canvas():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=DPI)
    fig.patch.set_facecolor(BG)
    return fig


def footer(fig, text="数据来源 ClinicalTrials.gov · 仅供科普参考"):
    fig.text(0.5, 0.045, text, ha="center", va="center",
             fontsize=15, color=MUTED)


def card_total(s):
    """Card 1 — the headline number and the two-country split."""
    fig = new_canvas()

    fig.text(0.5, 0.88, "全球 CAR-T 临床试验", ha="center",
             fontsize=34, color=MUTED)

    fig.text(0.5, 0.715, f"{s['total_trials']:,}", ha="center", va="center",
             fontsize=175, fontweight="bold", color=ACCENT)
    fig.text(0.5, 0.565, "项试验登记在册", ha="center",
             fontsize=30, color=INK)

    labels = s["by_country"]["labels"]
    counts = s["by_country"]["all"]
    cn = counts[labels.index("China")]
    us = counts[labels.index("USA")]

    # Two-country split, drawn as plain text blocks rather than a chart —
    # at thumbnail size a two-bar chart reads as noise.
    for x, flag, name, n, colour in (
        (0.26, "🇨🇳", "中国",  cn, RED),
        (0.74, "🇺🇸", "美国",  us, BLUE),
    ):
        fig.text(x, 0.44, name, ha="center", fontsize=30, color=MUTED)
        fig.text(x, 0.355, f"{n:,}", ha="center", va="center",
                 fontsize=74, fontweight="bold", color=colour)

    fig.text(0.5, 0.245, f"其中 {s['recruiting']:,} 项正在招募"
                         f"（{s['recruiting_pct']}%）",
             ha="center", fontsize=27, color=INK)
    fig.text(0.5, 0.175,
             "试验数量 ≠ 疗效更好，也 ≠ 更容易参加",
             ha="center", fontsize=23, color=MUTED)

    footer(fig, f"ClinicalTrials.gov · {s['data_month']} · 仅供科普参考")
    path = os.path.join(OUT_DIR, "card1_total.png")
    fig.savefig(path, facecolor=BG)
    plt.close(fig)
    return path


def card_disease(s):
    """Card 2 — disease breakdown, biggest group first."""
    d = s["disease"]
    pairs = [(l, n) for l, n in zip(d["labels"], d["counts"])
             if not l.startswith("Other")]
    pairs.sort(key=lambda p: p[1])

    zh = {
        "Multiple myeloma":          "多发性骨髓瘤",
        "Leukaemia":                 "白血病",
        "Lymphoma":                  "淋巴瘤",
        "Autoimmune disease":        "自身免疫病",
        "Solid tumour":              "实体瘤",
        "Blood cancer, unspecified": "其他血液肿瘤",
    }
    names  = [zh.get(l, l) for l, _ in pairs]
    values = [n for _, n in pairs]
    colours = [ACCENT if n == max(values) else
               RED if names[i] in ("实体瘤", "自身免疫病") else "#4f6f6a"
               for i, n in enumerate(values)]

    fig = new_canvas()
    fig.text(0.5, 0.90, "CAR-T 都在治什么病？", ha="center",
             fontsize=44, fontweight="bold", color=INK)
    fig.text(0.5, 0.855, "按试验数量 · 每项试验只计入一类", ha="center",
             fontsize=21, color=MUTED)

    ax = fig.add_axes([0.34, 0.20, 0.56, 0.60])
    ax.set_facecolor(BG)
    ax.barh(names, values, color=colours, height=0.6)

    for i, v in enumerate(values):
        ax.text(v + max(values) * 0.025, i, f"{v}", va="center",
                fontsize=30, fontweight="bold", color=INK)

    ax.set_xlim(0, max(values) * 1.22)
    ax.tick_params(axis="y", labelsize=27, colors=INK, length=0)
    ax.set_xticks([])
    for side in ax.spines.values():
        side.set_visible(False)

    footer(fig, f"ClinicalTrials.gov · {s['data_month']} · 仅供科普参考")
    path = os.path.join(OUT_DIR, "card2_disease.png")
    fig.savefig(path, facecolor=BG)
    plt.close(fig)
    return path


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(FIGURES, encoding="utf-8") as f:
        stats = json.load(f)

    if not CJK:
        print("WARNING: no CJK font found — Chinese text will render as boxes.")

    for path in (card_total(stats), card_disease(stats)):
        print(f"Saved → {path}")
    print(f"\n{stats['total_trials']:,} trials · {stats['data_month']}")


if __name__ == "__main__":
    main()
