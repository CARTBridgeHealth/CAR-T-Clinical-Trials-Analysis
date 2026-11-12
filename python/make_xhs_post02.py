"""
make_xhs_post02.py
------------------
Xiaohongshu post 02: what the approved CAR-T products treat, and how well.

Same canvas, palette and panel grammar as post 01 (make_xhs_infographic.py),
so the two read as one series. Three panels:

  ①  how many products, and the four disease groups they fall into
  ②  response rates from the pivotal registration trials, as ranges
  ③  how long responses last

The figures are researched rather than counted, so they live in
data/post02_efficacy.json with a source beside each one. Response rates are
drawn as a low-high range across products instead of one bar per product:
these are separate single-arm trials, and a ranked bar chart would invite
exactly the cross-trial comparison the caution box warns against.

Output: xhs_cards/post02_infographic.png, post02_infographic_en.png
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from make_xhs_infographic import (
    BG, DEEP, ROSE, ORANGE, PINK, PEACH, GREY, INK, BODY, WARN_BG, WARN_ED,
    OUT_DIR, SIZE_IN, DPI, FIGURES, rounded, panel, lift)

BASE = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(BASE, "data", "post02_efficacy.json")

# One colour per disease group, used for both the tile in ① and the row in ②.
COLOURS = {"lymphoma": DEEP, "ball": ROSE, "myeloma": ORANGE, "gastric": PINK}


def build(lang="zh"):
    EN = lang == "en"
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(DATA, encoding="utf-8") as f:
        d = json.load(f)
    with open(FIGURES, encoding="utf-8") as f:
        total_trials = json.load(f)["total_trials"]

    groups = d["groups"]
    products = {p for g in groups for p in g["usa"] + g["china"]}
    n_us = len({p for g in groups for p in g["usa"]})
    n_cn = len({p for g in groups for p in g["china"]})
    n_prod = len(products)
    year, month = d["as_of"].split("-")
    asof = (f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][int(month)-1]} {year}"
            if EN else f"{year}年{int(month)}月")

    fig = plt.figure(figsize=(SIZE_IN, SIZE_IN), dpi=DPI)
    fig.patch.set_facecolor(BG)

    # ── Title banner ──
    rounded(fig, 0.040, 0.905, 0.920, 0.062, DEEP, z=2)
    fig.text(0.5, 0.936,
             ("Approved CAR-T: what it treats, how well it works" if EN
              else "已上市的CAR-T：治什么病，疗效如何"),
             ha="center", va="center", fontsize=20 if EN else 27,
             fontweight="bold", color="#ffffff", zorder=3)

    # ── Panel ① what they treat ──
    px, py, pw, ph = panel(
        fig, 0.040, 0.690, 0.920, 0.185, "①",
        (f"{n_prod} approved (USA {n_us}, China {n_cn}) — four disease groups" if EN
         else f"中美已上市 {n_prod} 款（美国{n_us} · 中国{n_cn}），集中在4类疾病"),
        DEEP)
    tile_w = pw / 4
    for i, g in enumerate(groups):
        cx = px + tile_w * (i + 0.5)
        n = len(g["usa"]) + len(g["china"])
        fig.text(cx, py + 0.093, f"{n}", ha="center", va="center",
                 fontsize=34, fontweight="bold", color=COLOURS[g["key"]],
                 zorder=4)
        fig.text(cx, py + 0.055, g["en"] if EN else g["zh"],
                 ha="center", va="center", fontsize=12.5 if EN else 13.5,
                 fontweight="bold", color=INK, zorder=4)
        fig.text(cx, py + 0.033,
                 (f"Target: {g['target']}" if EN else f"靶点 {g['target']}"),
                 ha="center", va="center", fontsize=11, color=BODY, zorder=4)
        split = (f"USA {len(g['usa'])} · China {len(g['china'])}" if EN
                 else f"美国 {len(g['usa'])} · 中国 {len(g['china'])}")
        if g["key"] == "gastric":
            split = ("First for a solid tumour" if EN else "全球首款实体瘤CAR-T")
        fig.text(cx, py + 0.010, split, ha="center", va="center",
                 fontsize=10.5, color=GREY if g["key"] != "gastric" else ROSE,
                 zorder=4)

    # ── Panel ② response rates ──
    px, py, pw, ph = panel(
        fig, 0.040, 0.385, 0.920, 0.285, "②",
        ("Response rates in the pivotal trials" if EN
         else "关键注册研究里，有多少人出现缓解"),
        ROSE)
    ax_rect = [px + 0.275, py + 0.052, 0.400, 0.164]
    ax = lift(fig.add_axes(ax_rect))
    n_rows = len(groups)
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.6, n_rows - 0.4)
    for gx in (0, 50, 100):
        ax.axvline(gx, color=PEACH, lw=1, zorder=0)
    for i, g in enumerate(groups):
        row = n_rows - 1 - i
        colour = COLOURS[g["key"]]
        ax.barh([row], [100], color="#faf1ec", height=0.46, zorder=1)
        if g["low"] == g["high"]:
            ax.plot([g["high"]], [row], "o", ms=11, color=colour, zorder=3)
            ax.plot([g["control"]], [row], "o", ms=8, mfc="#ffffff",
                    mec=GREY, mew=1.6, zorder=3)
            label = (f"{g['high']}%  (control {g['control']}%)" if EN
                     else f"{g['high']}%（对照组 {g['control']}%）")
            ax.text(g["high"] + 5, row, label, ha="left", va="center",
                    fontsize=11, fontweight="bold", color=INK, zorder=4)
        else:
            ax.barh([row], [g["high"] - g["low"]], left=g["low"],
                    color=colour, height=0.46, zorder=2)
            ax.text(g["low"] - 3, row, f"{g['low']}–{g['high']}%",
                    ha="right", va="center", fontsize=11.5,
                    fontweight="bold", color=INK, zorder=4)
        # Row label and right-hand note sit outside the axes, in figure space.
        fy = ax_rect[1] + ax_rect[3] * (row + 0.6) / n_rows
        fig.text(px + 0.016, fy + 0.008, g["chart_en"] if EN else g["chart_zh"],
                 ha="left", va="center", fontsize=11 if EN else 12,
                 fontweight="bold", color=INK, zorder=4)
        fig.text(px + 0.016, fy - 0.011, g["metric_en"] if EN else g["metric_zh"],
                 ha="left", va="center", fontsize=9, color=GREY, zorder=4)
        if "cr_low" in g:
            note = (f"Complete response {g['cr_low']}–{g['cr_high']}%" if EN
                    else f"其中完全缓解 {g['cr_low']}–{g['cr_high']}%")
        elif g["key"] == "ball":
            note = ("Most are MRD-negative" if EN else "多数达到MRD阴性")
        else:
            note = ("Solid tumour: far lower" if EN else "实体瘤，缓解率低得多")
        fig.text(px + 0.700, fy, note, ha="left", va="center",
                 fontsize=10 if EN else 11, color=BODY, zorder=4)
    ax.set_xticks([0, 50, 100])
    ax.set_xticklabels(["0", "50%", "100%"], fontsize=9, color=GREY)
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(length=0, pad=1)
    fig.text(px + 0.016, py + 0.014,
             ("Bars span the lowest to highest rate across each group's products. "
              "Mostly single-arm trials — not comparable head to head." if EN else
              "色条为该类疾病各产品缓解率的最低到最高值。多为单臂试验、患者已历经多线治疗，不同试验不能直接比较。"),
             ha="left", va="center", fontsize=9.6 if EN else 10.5, color=GREY,
             zorder=4)

    # ── Panel ③ durability ──
    px, py, pw, ph = panel(
        fig, 0.040, 0.215, 0.920, 0.150, "③",
        ("After the response: how long does it last?" if EN
         else "缓解之后，能维持多久"),
        DEEP)
    dur = {x["key"]: x for x in d["durability"]}
    tiles = [
        (DEEP,
         f"{round(dur['lbcl']['value'])}%",
         ("Large B-cell lymphoma" if EN else "大B细胞淋巴瘤"),
         ("alive at 5 years (ZUMA-1)" if EN else "输注5年后仍存活（ZUMA-1）")),
        (ORANGE,
         ("1 in 3" if EN else "约1/3"),
         ("Multiple myeloma" if EN else "多发性骨髓瘤"),
         ("progression-free ≥5 yrs (CARTITUDE-1)" if EN
          else "5年以上未进展（CARTITUDE-1）")),
        (PINK,
         (f"{dur['gastric']['value']} vs {dur['gastric']['control']} mo" if EN
          else f"{dur['gastric']['value']} 对 {dur['gastric']['control']} 个月"),
         ("Gastric cancer" if EN else "胃癌"),
         ("median PFS vs standard care" if EN else "中位无进展生存，对比常规治疗")),
    ]
    tile_w = pw / 3
    for i, (colour, big, name, sub) in enumerate(tiles):
        cx = px + tile_w * (i + 0.5)
        fig.text(cx, py + 0.066, big, ha="center", va="center",
                 fontsize=24 if i < 2 else (18 if EN else 19),
                 fontweight="bold", color=colour, zorder=4)
        fig.text(cx, py + 0.034, name, ha="center", va="center",
                 fontsize=12.5, fontweight="bold", color=INK, zorder=4)
        fig.text(cx, py + 0.011, sub, ha="center", va="center",
                 fontsize=9.8 if EN else 10.5, color=BODY, zorder=4)

    # ── Caution box ──
    rounded(fig, 0.040, 0.108, 0.920, 0.082, WARN_BG, edge=WARN_ED, lw=1.6, z=2)
    fig.text(0.060, 0.166, "※", ha="left", va="center",
             fontsize=15, fontweight="bold", color=WARN_ED, zorder=4)
    caution = ([
        "Response is not cure. Trial patients are carefully selected, and CAR-T carries real risks",
        "(cytokine release syndrome, neurotoxicity). Whether it fits you is a question for your oncologist."]
        if EN else [
        "缓解 ≠ 治愈。试验人群经过严格筛选，个体差异很大；CAR-T 也有细胞因子释放综合征、",
        "神经毒性等风险。是否适合、选哪一款，请和主治医生讨论。"])
    for i, line in enumerate(caution):
        fig.text(0.086, 0.166 - i * 0.033, line, ha="left", va="center",
                 fontsize=10.6 if EN else 12.2, color=BODY, zorder=4,
                 fontweight="normal")

    # ── Footer ──
    fig.text(0.040, 0.080,
             (f"Sources: FDA and NMPA approvals; published pivotal trials (NEJM, Lancet, JCO, Blood, ASH). As of {asof}."
              if EN else
              f"数据来源：FDA / NMPA 批准信息；各产品关键注册研究（NEJM、Lancet、JCO、Blood、ASH）。截至{asof}"),
             ha="left", va="center", fontsize=9.6 if EN else 10.5, color=BODY)
    fig.text(0.040, 0.048,
             ("Educational information only. Not medical advice." if EN
              else "本内容仅供科普参考，不构成医疗建议。"),
             ha="left", va="center", fontsize=10.5, color=GREY)
    fig.text(0.960, 0.048,
             (f"Next: where are the {total_trials:,} trials heading? →" if EN
              else f"下一期聊：{total_trials}项试验，正在攻哪些新病种？→"),
             ha="right", va="center", fontsize=12, fontweight="bold",
             color=DEEP)

    suffix = "_en" if EN else ""
    path = os.path.join(OUT_DIR, f"post02_infographic{suffix}.png")
    fig.savefig(path, facecolor=BG)
    plt.close(fig)
    print(f"Saved -> {path}")
    return path


def main():
    for lang in ("zh", "en"):
        build(lang)


if __name__ == "__main__":
    main()
