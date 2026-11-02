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
  3  solid-tumour trials
  4  autoimmune trials
  5  cost comparison by country

Card 5 reads from country_comparison.json, whose figures are researched
rather than counted, so it carries its own caveats on the image. XHS images
get screenshotted and reshared without the caption, so a cost claim has to
travel with its qualifiers attached.

Output: xhs_cards/card{1..5}_*.png
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

BASE       = os.path.join(os.path.dirname(__file__), "..")
FIGURES    = os.path.join(BASE, "data", "trial_figures.json")
COMPARISON = os.path.join(BASE, "data", "country_comparison.json")
OUT_DIR    = os.path.join(BASE, "xhs_cards")

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


MONTHS_ZH = {"January": 1, "February": 2, "March": 3, "April": 4, "May": 5,
             "June": 6, "July": 7, "August": 8, "September": 9,
             "October": 10, "November": 11, "December": 12}


def month_zh(text):
    """'July 2026' -> '2026年7月'. Returns the input unchanged if unparsable."""
    parts = str(text).split()
    if len(parts) == 2 and parts[0] in MONTHS_ZH:
        return f"{parts[1]}年{MONTHS_ZH[parts[0]]}月"
    return text


def new_canvas():
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=DPI)
    fig.patch.set_facecolor(BG)
    return fig


def footer(fig, text="数据来源 ClinicalTrials.gov · 仅供科普参考"):
    fig.text(0.5, 0.045, text, ha="center", va="center",
             fontsize=15, color=MUTED)


def card_total(s):
    """Card 1 — headline count, then the China/USA gap drawn as bars.

    Two numbers side by side made the reader do the arithmetic. Bars make the
    gap the thing you see first, which is the actual hook for this post.
    """
    labels = s["by_country"]["labels"]
    counts = s["by_country"]["all"]
    cn = counts[labels.index("China")]
    us = counts[labels.index("USA")]

    fig = new_canvas()

    # ── Headline ──
    fig.text(0.5, 0.925, "全球 CAR-T 临床试验", ha="center",
             fontsize=31, color=MUTED)

    fig.text(0.46, 0.800, f"{s['total_trials']:,}", ha="center", va="center",
             fontsize=152, fontweight="bold", color=ACCENT)
    # Unit tucked against the number rather than on its own line.
    fig.text(0.815, 0.762, "项", ha="center", va="center",
             fontsize=42, color=INK)

    fig.text(0.5, 0.675, f"其中 {s['recruiting']:,} 项正在招募"
                         f"（{s['recruiting_pct']}%）",
             ha="center", fontsize=26, color=INK)

    # ── Divider ──
    fig.add_artist(plt.Line2D([0.12, 0.88], [0.615, 0.615],
                              color="#2a3f3b", linewidth=2))

    # ── China vs USA, as bars ──
    bar_left, bar_max = 0.28, 0.41
    widest = max(cn, us)
    for i, (name, n, colour) in enumerate((("中国", cn, ACCENT),
                                           ("美国", us, BLUE))):
        y = 0.505 - i * 0.125
        fig.text(0.12, y, name, ha="left", va="center",
                 fontsize=34, color=INK)
        fig.patches.append(plt.Rectangle(
            (bar_left, y - 0.028), bar_max * n / widest, 0.056,
            transform=fig.transFigure, facecolor=colour, zorder=1))
        fig.text(bar_left + bar_max * n / widest + 0.018, y, f"{n:,}",
                 ha="left", va="center", fontsize=38,
                 fontweight="bold", color=colour)

    # ── The point of the card ──
    fig.text(0.5, 0.285, f"中国试验数量约为美国的 {cn / us:.1f} 倍",
             ha="center", fontsize=30, fontweight="bold", color=INK)

    fig.text(0.5, 0.205, "但试验数量 ≠ 疗效更好",
             ha="center", fontsize=24, color=MUTED)
    fig.text(0.5, 0.155, "也 ≠ 更容易参加 · 多数仍在一期",
             ha="center", fontsize=24, color=MUTED)

    footer(fig, f"ClinicalTrials.gov · {month_zh(s['data_month'])} · 仅供科普参考")
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

    footer(fig, f"ClinicalTrials.gov · {month_zh(s['data_month'])} · 仅供科普参考")
    path = os.path.join(OUT_DIR, "card2_disease.png")
    fig.savefig(path, facecolor=BG)
    plt.close(fig)
    return path


def card_big_number(s, group, filename, heading, lead_zh, body_lines, caveat):
    """Cards 3 and 4 — one group's count, with context and a caveat.

    Both follow the same shape, so they share a builder rather than being
    copy-pasted: the only things that differ are the group looked up and the
    surrounding words.
    """
    d = s["disease"]
    n = d["counts"][d["labels"].index(group)]
    share = n / sum(d["counts"])

    fig = new_canvas()
    fig.text(0.5, 0.885, heading, ha="center", fontsize=34, color=MUTED)

    fig.text(0.5, 0.715, f"{n}", ha="center", va="center",
             fontsize=215, fontweight="bold", color=RED)
    fig.text(0.5, 0.565, lead_zh, ha="center", fontsize=31, color=INK)
    fig.text(0.5, 0.505, f"占全部 CAR-T 试验的 {share:.0%}",
             ha="center", fontsize=26, color=ACCENT)

    y = 0.395
    for line in body_lines:
        fig.text(0.5, y, line, ha="center", fontsize=25, color=INK)
        y -= 0.058

    fig.text(0.5, y - 0.03, caveat, ha="center", fontsize=22, color=MUTED)

    footer(fig, f"ClinicalTrials.gov · {month_zh(s['data_month'])} · 仅供科普参考")
    path = os.path.join(OUT_DIR, filename)
    fig.savefig(path, facecolor=BG)
    plt.close(fig)
    return path


def card_cost(c):
    """Card 5 — cost by country.

    The most commercially useful card and the most sensitive. Figures are
    researched, not counted, so the review date and the main caveats sit on
    the image itself.
    """
    wanted = ["China", "USA", "Canada", "Germany"]
    zh = {"China": "中国", "USA": "美国", "Canada": "加拿大", "Germany": "德国"}
    rows = [r for name in wanted
            for r in c["countries"] if r["country"] == name]

    fig = new_canvas()
    fig.text(0.5, 0.905, "CAR-T 全包费用对比", ha="center",
             fontsize=46, fontweight="bold", color=INK)
    fig.text(0.5, 0.858, "各国区间估算 · 美元", ha="center",
             fontsize=23, color=MUTED)

    y = 0.735
    for r in rows:
        low, high = r["cost_low_usd"] // 1000, r["cost_high_usd"] // 1000
        is_cn = r["country"] == "China"
        colour = ACCENT if is_cn else INK
        wait = (f"{r['wait_low_weeks']} 周" if r["wait_low_weeks"] == r["wait_high_weeks"]
                else f"{r['wait_low_weeks']}–{r['wait_high_weeks']} 周")

        fig.text(0.10, y, zh[r["country"]], ha="left", va="center",
                 fontsize=36, fontweight="bold" if is_cn else "normal",
                 color=colour)
        fig.text(0.90, y, f"${low}–{high}K", ha="right", va="center",
                 fontsize=44, fontweight="bold", color=colour)
        fig.text(0.90, y - 0.045, f"等待 {wait} · {r['approved_products']} 个获批产品",
                 ha="right", va="center", fontsize=21, color=MUTED)
        y -= 0.135

    # Caveats ride on the image: screenshots travel without the caption.
    fig.text(0.5, 0.165, "※ 区间估算，实际费用因医院、病情、并发症而异",
             ha="center", fontsize=21, color=INK)
    fig.text(0.5, 0.122, "不含机票、住宿、陪护、翻译等费用",
             ha="center", fontsize=21, color=MUTED)
    fig.text(0.5, 0.079, "费用差异源于定价机制，不代表治疗质量差异",
             ha="center", fontsize=21, color=MUTED)

    footer(fig, f"治疗中心调研 · {month_zh(c['as_of'])}复核 · 不构成医疗建议")
    path = os.path.join(OUT_DIR, "card5_cost.png")
    fig.savefig(path, facecolor=BG)
    plt.close(fig)
    return path


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(FIGURES, encoding="utf-8") as f:
        stats = json.load(f)
    with open(COMPARISON, encoding="utf-8") as f:
        comparison = json.load(f)

    if not CJK:
        print("WARNING: no CJK font found — Chinese text will render as boxes.")

    paths = [
        card_total(stats),
        card_disease(stats),
        card_big_number(
            stats, "Solid tumour", "card3_solid.png",
            heading="实体瘤 CAR-T 试验",
            lead_zh="项实体瘤试验登记在册",
            body_lines=["涵盖胰腺癌、卵巢癌、结直肠癌、胶质瘤等",
                        "2026年6月 中国批准全球首个实体瘤 CAR-T"],
            caveat="新获批产品的长期与真实世界数据仍然有限"),
        card_big_number(
            stats, "Autoimmune disease", "card4_autoimmune.png",
            heading="自身免疫病 CAR-T 试验",
            lead_zh="项自身免疫病试验登记在册",
            body_lines=["系统性红斑狼疮 · 系统性硬化症",
                        "狼疮性肾炎 · 肌炎"],
            caveat="均处于早期临床阶段，远未成为标准治疗"),
        card_cost(comparison),
    ]
    for path in paths:
        print(f"Saved → {path}")
    print(f"\n{stats['total_trials']:,} trials · {stats['data_month']}")


if __name__ == "__main__":
    main()
