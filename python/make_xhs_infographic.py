"""
make_xhs_infographic.py
-----------------------
Render the dense four-panel Xiaohongshu infographic from data/trial_figures.json.

A different format from make_xhs_cards.py: square (1080x1080), light ground,
panel grid, with a chart inside each panel. It carries roughly five times the
text of a cover card, so it works as the post's main image where the reader has
already tapped in — rather than as the thumbnail that earns the tap.

Every number and every chart comes from the figures file, so re-running after
the monthly refresh updates the whole graphic.

Output: xhs_cards/post01_infographic.png
"""

import json
import os

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, Polygon

BASE    = os.path.join(os.path.dirname(__file__), "..")
FIGURES = os.path.join(BASE, "data", "trial_figures.json")
PRODUCTS = os.path.join(BASE, "data", "approved_products.csv")
OUT_DIR = os.path.join(BASE, "xhs_cards")

SIZE_IN, DPI = 9, 120          # 1080 x 1080

# Warm palette — orange through rose, read as forward-looking rather than
# clinical. Deep shades carry white header text; lighter ones are series fills.
BG      = "#fdf4ee"            # page, warm off-white
PANEL   = "#ffffff"
DEEP    = "#9e3b2e"            # primary headers, primary series
ROSE    = "#b94a6e"            # secondary headers
ORANGE  = "#ef7f45"            # accent series
PINK    = "#e8718f"            # second accent — hue-separated from ORANGE
PEACH   = "#f7cdb4"            # muted series fill
GREY    = "#b0a09a"            # warm grey, de-emphasised text
INK     = "#2e211d"
BODY    = "#4a3a35"
ROSE_LT = "#cf87a1"            # ~75% strength ROSE on white
WARN_BG = "#fff3e4"
WARN_ED = "#e09a4e"

CJK = next((n for n in ("Microsoft YaHei", "Microsoft JhengHei", "SimHei")
            if any(f.name == n for f in font_manager.fontManager.ttflist)), None)
if CJK:
    # CJK face first: matplotlib picks one font per text run, so a Latin-first
    # list renders every Chinese character as a tofu box.
    plt.rcParams["font.sans-serif"] = [CJK, "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

MONTHS_ZH = {"January": 1, "February": 2, "March": 3, "April": 4, "May": 5,
             "June": 6, "July": 7, "August": 8, "September": 9,
             "October": 10, "November": 11, "December": 12}


def month_zh(text):
    parts = str(text).split()
    if len(parts) == 2 and parts[0] in MONTHS_ZH:
        return f"{parts[1]}年{MONTHS_ZH[parts[0]]}月"
    return text


def lift(ax):
    """Axes default to zorder 0 at figure level, below the panel patches."""
    ax.set_zorder(6)
    ax.patch.set_alpha(0)
    return ax


def rounded(fig, x, y, w, h, face, edge="none", lw=0, z=1, pad=0.008):
    fig.patches.append(FancyBboxPatch(
        (x, y), w, h, transform=fig.transFigure,
        boxstyle=f"round,pad={pad},rounding_size=0.014",
        facecolor=face, edgecolor=edge, linewidth=lw, zorder=z))


def panel(fig, x, y, w, h, number, title, header_colour):
    """White card with a coloured header strip. Returns the body rect."""
    rounded(fig, x, y, w, h, PANEL, z=2)
    bar_h = 0.050
    rounded(fig, x, y + h - bar_h, w, bar_h, header_colour, z=3)
    fig.text(x + 0.016, y + h - bar_h / 2, f"{number} {title}",
             ha="left", va="center", fontsize=15.5, fontweight="bold",
             color="#ffffff", zorder=4)
    return x, y, w, h - bar_h


def body_text(fig, x, y, w, lines, size=11.5):
    """Wrapped explanation under a panel's chart."""
    ty = y
    for line in lines:
        fig.text(x + 0.016, ty, line, ha="left", va="top",
                 fontsize=size, color=BODY, zorder=4, linespacing=1.5)
        ty -= 0.026
    return ty


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(FIGURES, encoding="utf-8") as f:
        s = json.load(f)

    total   = s["total_trials"]
    recruit = s["recruiting"]
    pct     = s["recruiting_pct"]
    phases  = dict(zip(s["phase"]["labels"], s["phase"]["counts"]))
    early   = (phases.get("Early Phase 1", 0) + phases.get("Phase 1", 0)
               + phases.get("Phase 1/2", 0))
    early_pct = round(100 * early / total)
    dis     = dict(zip(s["disease"]["labels"], s["disease"]["counts"]))
    blood   = (dis.get("Leukaemia", 0) + dis.get("Lymphoma", 0)
               + dis.get("Multiple myeloma", 0)
               + dis.get("Blood cancer, unspecified", 0))
    blood_pct = round(100 * blood / total)
    solid, auto = dis.get("Solid tumour", 0), dis.get("Autoimmune disease", 0)
    cn_us     = s.get("in_china_or_usa", 0)
    cn_us_pct = s.get("in_china_or_usa_pct", 0)
    month = month_zh(s["data_month"])

    # Approved products are counted from approved_products.csv — the same
    # source the website uses, so the card cannot disagree with the site.
    prods = pd.read_csv(PRODUCTS)
    n_prod = int(len(prods))
    n_cn   = int((prods["country"] == "China").sum())
    n_us   = int((prods["country"] == "USA").sum())

    fig = plt.figure(figsize=(SIZE_IN, SIZE_IN), dpi=DPI)
    fig.patch.set_facecolor(BG)

    # ── Title banner ──
    rounded(fig, 0.040, 0.905, 0.920, 0.062, DEEP, z=2)
    fig.text(0.5, 0.936, f"全球{total}项CAR-T试验，说明了什么",
             ha="center", va="center", fontsize=27, fontweight="bold",
             color="#ffffff", zorder=3)

    col_w, row_h = 0.445, 0.253
    left, right = 0.040, 0.515

    # ── Panel ① scale and concentration ──
    px, py, pw, ph = panel(fig, left, 0.598, col_w, row_h,
                           "①", f"{total}项试验登记在册", DEEP)
    ax = lift(fig.add_axes([px + 0.028, py + 0.112, pw - 0.056, 0.082]))
    this_year = int(s["generated_utc"][:4])
    pairs = [(y, v) for y, v in zip(s["growth"]["years"],
                                    s["growth"]["trials"]) if y < this_year]
    yrs, vals = [q[0] for q in pairs], [q[1] for q in pairs]
    ax.bar(yrs, vals, color=[PEACH] * (len(yrs) - 1) + [DEEP], width=0.75)
    ax.annotate(f"{vals[-1]}", (yrs[-1], vals[-1]), textcoords="offset points",
                xytext=(0, 4), ha="center", fontsize=10.5,
                fontweight="bold", color=DEEP)
    ax.set_ylim(0, max(vals) * 1.30)
    ax.set_xticks([yrs[0], yrs[-1]])
    ax.set_xticklabels([str(yrs[0]), f"{yrs[-1]}年"], fontsize=9.5, color=GREY)
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(length=0)
    body_text(fig, px, py + 0.092, pw,
              [f"研究规模很大，且高度集中：约 {cn_us_pct}%",
               f"（{cn_us}项）在中国和美国开展。",
               f"图为各年新启动试验数（至{yrs[-1]}年）。"])

    # ── Panel ② approved, mature in blood cancers ──
    px, py, pw, ph = panel(fig, right, 0.598, col_w, row_h,
                           "②", f"{n_prod}款已获批上市", ROSE)
    fig.text(px + pw / 2, py + 0.148, f"{n_prod}", ha="center", va="center",
             fontsize=52, fontweight="bold", color=ROSE_LT, zorder=4)
    fig.text(px + pw / 2, py + 0.112, f"中国 {n_cn} 款 · 美国 {n_us} 款",
             ha="center", va="center", fontsize=15, color=INK, zorder=4)
    body_text(fig, px, py + 0.084, pw,
              ["在血液肿瘤领域，CAR-T 已是获批的",
               "成熟疗法，不是实验性治疗——覆盖",
               "白血病、淋巴瘤、多发性骨髓瘤。"])

    # ── Panel ③ expanding, recruiting (full width) ──
    px, py, pw, ph = panel(fig, left, 0.330, 0.920, row_h,
                           "③", "正在扩展到血液肿瘤以外，并大量招募", DEEP)
    ax = lift(fig.add_axes([px + 0.030, py + 0.148, pw - 0.060, 0.044]))
    ax.set_xlim(0, total); ax.set_ylim(0, 1); ax.axis("off")
    ax.barh([0.5], [blood], color=DEEP, height=1.0)
    ax.barh([0.5], [solid], left=blood, color=ORANGE, height=1.0)
    ax.barh([0.5], [auto], left=blood + solid, color=PINK, height=1.0)
    ax.barh([0.5], [total - blood - solid - auto], left=blood + solid + auto,
            color=PEACH, height=1.0)
    ax.text(blood / 2, 0.5, f"血液肿瘤 {blood}项 · {blood_pct}%",
            ha="center", va="center", fontsize=11,
            fontweight="bold", color="#ffffff")

    lx = px + 0.032
    for colour, label in ((ORANGE, f"实体瘤 {solid}项"),
                          (PINK, f"自身免疫病 {auto}项"),
                          (PEACH, "其他 / 未分类")):
        fig.patches.append(FancyBboxPatch(
            (lx, py + 0.116), 0.013, 0.013, transform=fig.transFigure,
            boxstyle="round,pad=0.002,rounding_size=0.004",
            facecolor=colour, edgecolor="none", zorder=4))
        fig.text(lx + 0.021, py + 0.122, label, ha="left", va="center",
                 fontsize=11.5, color=BODY, zorder=4)
        lx += 0.235
    body_text(fig, px, py + 0.090, pw,
              [f"实体瘤已有 {solid} 项、自身免疫病 {auto} 项，这两个方向增长很快。"
               f"全球 {recruit} 项（{pct}%）正在招募，",
               f"其中新方向多数仍处于早期阶段——{early_pct}% 的试验在一期或更早，"
               "以探索安全性与适应症边界为主。"])

    # ── Caution box ──
    rounded(fig, 0.040, 0.128, 0.920, 0.168, WARN_BG, edge=WARN_ED, lw=1.6, z=2)
    fig.text(0.064, 0.272, "※", ha="left", va="center",
             fontsize=17, fontweight="bold", color=WARN_ED, zorder=4)
    fig.text(0.092, 0.272, "想特别说一句", ha="left", va="center",
             fontsize=15.5, fontweight="bold", color=INK, zorder=4)
    for i, line in enumerate([
            "试验数量 ≠ 可及性。临床试验的入组条件通常很严格（分期、既往治疗线数、",
            "器官功能等），不是想参加就能参加。如果你或家人正考虑这个方向，",
            "请先和主治医生讨论，由医生判断是否符合条件。"]):
        fig.text(0.064, 0.232 - i * 0.030, line, ha="left", va="center",
                 fontsize=12.5, color=BODY, zorder=4)

    # ── Footer ──
    fig.text(0.040, 0.082, f"数据来源：ClinicalTrials.gov，{month}",
             ha="left", va="center", fontsize=11, color=BODY)
    fig.text(0.040, 0.052, "本内容仅供科普参考，不构成医疗建议。",
             ha="left", va="center", fontsize=11, color=GREY)
    fig.text(0.960, 0.066, f"下一期聊：这{total}项试验，具体都在治什么病？→",
             ha="right", va="center", fontsize=12, fontweight="bold",
             color=DEEP)

    path = os.path.join(OUT_DIR, "post01_infographic.png")
    fig.savefig(path, facecolor=BG)
    plt.close(fig)
    print(f"Saved → {path}")
    print(f"  {total} trials · {month} · recruiting {recruit} ({pct}%) · "
          f"early {early_pct}% · blood {blood} ({blood_pct}%)")


if __name__ == "__main__":
    main()
