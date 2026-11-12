"""
make_xhs_post03.py
------------------
Xiaohongshu post 03: CAR-T trials in autoimmune disease.

Same canvas, palette and panel grammar as posts 01 and 02. Three panels:

  ①  how fast the field grew
  ②  which diseases are being treated
  ③  how far along the trials are

Every trial figure is counted from cart_trials_clean.csv, using the same
"Autoimmune disease" group as generate_trial_figures.py, so the total here is
the number the website and post 01 show. The counted figures are also written
to data/post03_autoimmune.json so they can be checked without re-running.

Two things on the image are NOT counted from the registry and are stated in
RESEARCHED below with their source: that no CAR-T is approved for an
autoimmune disease, and that a first application has been filed.

Output: xhs_cards/post03_infographic.png, post03_infographic_en.png
"""

import json
import os

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from classify_cart_trials import zones
from generate_trial_figures import DISEASE_GROUPS
from make_xhs_infographic import (
    BG, DEEP, ROSE, ORANGE, PINK, PEACH, GREY, INK, BODY, WARN_BG, WARN_ED,
    OUT_DIR, SIZE_IN, DPI, rounded, panel, lift, month_zh)

BASE  = os.path.join(os.path.dirname(__file__), "..")
CLEAN = os.path.join(BASE, "data", "cart_trials_clean.csv")
RAW   = os.path.join(BASE, "data", "cart_trials_raw.json")
OUT_JSON = os.path.join(BASE, "data", "post03_autoimmune.json")

RESEARCHED = {
    "approved_for_autoimmune": 0,
    "first_filing": "Kyverna completed a BLA submission to the FDA for miv-cel "
                    "(KYV-101) in stiff person syndrome; no decision as of "
                    "2026-11-12 (company 8-K filings, BioSpace).",
}

# Sub-diseases, matched on title + conditions. A basket trial that enrols
# several diseases counts once under each, so these do not sum to the total.
DISEASES = [
    ("lupus",   "系统性红斑狼疮 / 狼疮肾炎", "Lupus (SLE / lupus nephritis)",
     r"lupus|\bSLE\b"),
    ("ssc",     "系统性硬化症", "Systemic sclerosis",
     r"systemic sclerosis|scleroderma|\bSSc\b"),
    ("myositis", "炎性肌病", "Inflammatory myopathy",
     r"myositis|myopath|dermatomyos|antisynthetase"),
    ("aav",     "ANCA 相关血管炎", "ANCA vasculitis", r"vasculitis|\bANCA\b"),
    ("mg",      "重症肌无力", "Myasthenia gravis", r"myasth"),
    ("ms",      "多发性硬化", "Multiple sclerosis", r"multiple sclerosis"),
    ("cytopenia", "免疫性血细胞减少", "Immune cytopenias",
     r"thrombocytopeni|hemolytic|haemolytic|\bITP\b|AIHA|immune cytopenia"),
    ("sjogren", "干燥综合征", "Sjögren's", r"sj[öo]gren"),
    ("ra",      "类风湿关节炎", "Rheumatoid arthritis", r"rheumatoid"),
    ("nmosd",   "视神经脊髓炎谱系病", "NMOSD", r"neuromyelitis|NMOSD"),
]
N_CHART = 6
FIRST_YEAR = 2019


def autoimmune_trials(df):
    """Same first-match grouping as generate_trial_figures.py."""
    cond = df["conditions"].fillna("")
    unassigned = pd.Series(True, index=df.index)
    for label, pattern in DISEASE_GROUPS:
        hit = unassigned & cond.str.contains(pattern, case=False, regex=True)
        if label == "Autoimmune disease":
            return df[hit].copy()
        unassigned &= ~hit
    raise KeyError("Autoimmune disease group not defined")


def compute():
    df = pd.read_csv(CLEAN, low_memory=False)
    ai = autoimmune_trials(df)
    n = len(ai)

    this_year = pd.Timestamp.now("UTC").year
    last_full = this_year - 1
    years = list(range(FIRST_YEAR, last_full + 1))
    by_year = ai["start_year"].value_counts()
    all_by_year = df["start_year"].value_counts()
    per_year = [int(by_year.get(y, 0)) for y in years]

    text = ai["title"].fillna("") + " | " + ai["conditions"].fillna("")
    flags = pd.DataFrame({k: text.str.contains(p, case=False, regex=True)
                          for k, _, _, p in DISEASES})
    diseases = [{"key": k, "zh": zh, "en": en, "trials": int(flags[k].sum())}
                for k, zh, en, _ in DISEASES]
    diseases.sort(key=lambda d: -d["trials"])

    early = ai["phase"].isin(["Early Phase 1", "Phase 1", "Phase 1/2"]).sum()
    later = ai["phase"].isin(["Phase 2", "Phase 2/3", "Phase 3"]).sum()
    countries = ai["countries"].fillna("")

    # Product design, read from the full protocol text of each trial.
    with open(RAW, encoding="utf-8") as f:
        raw = {s["protocolSection"]["identificationModule"]["nctId"]: s
               for s in json.load(f)}
    deep = ai["trial_id"].map(
        lambda i: " | ".join(v for k, v in zones(raw[i]).items()
                             if k != "study_type") if i in raw else "")
    cd19 = deep.str.contains("CD19", case=False)
    bcma = deep.str.contains("BCMA", case=False)

    stats = {
        "generated_utc": pd.Timestamp.now("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_month": pd.Timestamp.now("UTC").strftime("%B %Y"),
        "total": n,
        "all_cart_trials": int(len(df)),
        "years": years,
        "per_year": per_year,
        "current_year": this_year,
        "current_year_so_far": int(by_year.get(this_year, 0)),
        "share_of_new_trials_last_full_year_pct":
            round(100 * by_year.get(last_full, 0) / all_by_year.get(last_full, 1)),
        "diseases": diseases,
        "basket_trials": int((flags.sum(axis=1) >= 2).sum()),
        "early_phase": int(early),
        "early_phase_pct": round(100 * early / n),
        "phase2_or_later": int(later),
        "phase3": int((ai["phase"] == "Phase 3").sum()),
        "median_enrollment": int(ai["enrollment"].median()),
        "completed": int((ai["status"] == "COMPLETED").sum()),
        "recruiting": int((ai["status"] == "RECRUITING").sum()),
        "results_posted": int(ai["results_posted"].sum()),
        "china": int(countries.str.contains("China", regex=False).sum()),
        "usa": int(countries.str.contains("United States", regex=False).sum()),
        "cd19": int(cd19.sum()),
        "cd19_bcma_dual": int((cd19 & bcma).sum()),
        "researched": RESEARCHED,
    }
    stats["china_pct"] = round(100 * stats["china"] / n)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return stats


def build(s, lang="zh"):
    EN = lang == "en"
    os.makedirs(OUT_DIR, exist_ok=True)
    n, years, per_year = s["total"], s["years"], s["per_year"]
    month = s["data_month"] if EN else month_zh(s["data_month"])

    fig = plt.figure(figsize=(SIZE_IN, SIZE_IN), dpi=DPI)
    fig.patch.set_facecolor(BG)

    # ── Title banner ──
    rounded(fig, 0.040, 0.905, 0.920, 0.062, DEEP, z=2)
    fig.text(0.5, 0.936,
             ("CAR-T in autoimmune disease: the trial landscape" if EN
              else "CAR-T 治疗自身免疫病：临床试验全景"),
             ha="center", va="center", fontsize=20 if EN else 27,
             fontweight="bold", color="#ffffff", zorder=3)

    # ── Panel ① growth ──
    px, py, pw, ph = panel(
        fig, 0.040, 0.675, 0.920, 0.200, "①",
        (f"{n} registered trials, most started since {years[-2]}" if EN
         else f"注册试验 {n} 项，绝大多数始于 {years[-2]} 年之后"), DEEP)
    ax = lift(fig.add_axes([px + 0.030, py + 0.030, 0.400, 0.100]))
    ax.bar(years, per_year, width=0.72,
           color=[PEACH] * (len(years) - 1) + [DEEP])
    for y, v in zip(years, per_year):
        ax.text(y, v + max(per_year) * 0.04, str(v), ha="center", va="bottom",
                fontsize=10 if y != years[-1] else 11.5,
                fontweight="bold" if y == years[-1] else "normal",
                color=DEEP if y == years[-1] else BODY)
    ax.set_ylim(0, max(per_year) * 1.28)
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], fontsize=9.5, color=GREY)
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(length=0, pad=2)

    tx = px + 0.475
    grow = [f"{years[-3]}: {per_year[-3]}  →  {years[-1]}: {per_year[-1]}" if EN
            else f"{years[-3]} 年 {per_year[-3]} 项  →  {years[-1]} 年 {per_year[-1]} 项"]
    fig.text(tx, py + 0.118, grow[0], ha="left", va="center",
             fontsize=14.5 if EN else 15.5, fontweight="bold", color=INK,
             zorder=4)
    lines = ([f"In {years[-1]}, about 1 in {round(100 / s['share_of_new_trials_last_full_year_pct'])} "
              f"new CAR-T trials",
              "was in autoimmune disease.",
              f"{s['current_year']} so far: {s['current_year_so_far']} more registered.",
              "Chart: trials by start year."]
             if EN else
             [f"{years[-1]} 年新启动的 CAR-T 试验中，约每 "
              f"{round(100 / s['share_of_new_trials_last_full_year_pct'])} 项",
              "就有 1 项针对自身免疫病。",
              f"{s['current_year']} 年至今已再登记 {s['current_year_so_far']} 项。",
              "柱状图：按启动年份统计的试验数。"])
    for i, line in enumerate(lines):
        fig.text(tx, py + 0.086 - i * 0.024, line, ha="left", va="center",
                 fontsize=10.6 if EN else 11.5,
                 color=BODY if i < 3 else GREY, zorder=4)

    # ── Panel ② diseases ──
    px, py, pw, ph = panel(
        fig, 0.040, 0.385, 0.920, 0.270, "②",
        ("Which diseases: lupus leads" if EN else "在治什么病：红斑狼疮领跑"),
        ROSE)
    top = s["diseases"][:N_CHART]
    ax_rect = [px + 0.300, py + 0.040, 0.520, 0.156]
    ax = lift(fig.add_axes(ax_rect))
    vmax = top[0]["trials"]
    ax.set_xlim(0, vmax * 1.12)
    ax.set_ylim(-0.6, len(top) - 0.4)
    for i, d in enumerate(top):
        row = len(top) - 1 - i
        ax.barh([row], [d["trials"]], height=0.58,
                color=ROSE if i == 0 else PINK if i < 3 else PEACH, zorder=2)
        ax.text(d["trials"] + vmax * 0.015, row, str(d["trials"]),
                ha="left", va="center", fontsize=11.5, fontweight="bold",
                color=INK, zorder=3)
        fy = ax_rect[1] + ax_rect[3] * (row + 0.6) / len(top)
        fig.text(px + 0.288, fy, d["en"] if EN else d["zh"], ha="right",
                 va="center", fontsize=10.8 if EN else 12, color=INK, zorder=4)
    ax.axis("off")
    rest = "、".join(d["zh"] for d in s["diseases"][N_CHART:N_CHART + 3])
    rest_en = ", ".join(d["en"] for d in s["diseases"][N_CHART:N_CHART + 3])
    fig.text(px + 0.016, py + 0.016,
             (f"{s['basket_trials']} basket trials enrol several diseases and count under each. "
              f"Also: {rest_en}." if EN else
              f"其中 {s['basket_trials']} 项为同时纳入多个病种的篮子试验，在各病种下重复计数。"
              f"此外还有{rest}等。"),
             ha="left", va="center", fontsize=9.6 if EN else 10.5, color=GREY,
             zorder=4)

    # ── Panel ③ maturity ──
    px, py, pw, ph = panel(
        fig, 0.040, 0.215, 0.920, 0.150, "③",
        ("How far along: still early" if EN else "走到哪一步：仍处于早期"),
        DEEP)
    tiles = [
        (DEEP, f"{s['early_phase_pct']}%",
         ("Phase 1/2 or earlier" if EN else "处于 I/II 期或更早"),
         (f"only {s['phase3']} Phase 3 trials" if EN
          else f"III 期试验仅 {s['phase3']} 项")),
        (ORANGE, (f"{s['median_enrollment']} people" if EN
                  else f"{s['median_enrollment']} 人"),
         ("median planned enrolment" if EN else "每项试验计划入组中位数"),
         (f"{s['completed']} completed, {s['results_posted']} with posted results" if EN
          else f"已完成 {s['completed']} 项，登记库公布结果 {s['results_posted']} 项")),
        (ROSE, (f"{s['researched']['approved_for_autoimmune']} approved" if EN
                else f"{s['researched']['approved_for_autoimmune']} 款获批"),
         ("for any autoimmune disease" if EN else "全球尚无用于自身免疫病的产品"),
         ("first FDA application submitted" if EN
          else "首个上市申请已递交美国 FDA")),
    ]
    tile_w = pw / 3
    for i, (colour, big, name, sub) in enumerate(tiles):
        cx = px + tile_w * (i + 0.5)
        fig.text(cx, py + 0.066, big, ha="center", va="center",
                 fontsize=22 if EN else 24, fontweight="bold", color=colour,
                 zorder=4)
        fig.text(cx, py + 0.034, name, ha="center", va="center",
                 fontsize=11.5 if EN else 12.5, fontweight="bold", color=INK,
                 zorder=4)
        fig.text(cx, py + 0.011, sub, ha="center", va="center",
                 fontsize=9.8 if EN else 10.5, color=BODY, zorder=4)

    # ── Caution box ──
    rounded(fig, 0.040, 0.108, 0.920, 0.082, WARN_BG, edge=WARN_ED, lw=1.6, z=2)
    fig.text(0.060, 0.166, "※", ha="left", va="center",
             fontsize=15, fontweight="bold", color=WARN_ED, zorder=4)
    caution = ([
        "Early case reports are striking, but this remains experimental: samples are small, and",
        "long-term safety and relapse are unknown. Ask your rheumatologist or neurologist first."]
        if EN else [
        "早期个案报道令人鼓舞，但目前仍属试验性治疗：样本量小，长期安全性与复发情况尚不明确。",
        "是否适合参加试验，请先咨询风湿免疫科或神经内科主治医生。"])
    for i, line in enumerate(caution):
        fig.text(0.086, 0.166 - i * 0.033, line, ha="left", va="center",
                 fontsize=10.6 if EN else 11.8, color=BODY, zorder=4)

    # ── Footer ──
    fig.text(0.040, 0.080,
             (f"Source: ClinicalTrials.gov, {month}. Counts trials that administer a CAR-T product; "
              f"{s['china_pct']}% have sites in China." if EN else
              f"数据来源：ClinicalTrials.gov，{month}。仅统计给受试者输注 CAR-T 产品的试验；"
              f"其中 {s['china_pct']}% 有中国中心参与。"),
             ha="left", va="center", fontsize=9.6 if EN else 10.5, color=BODY)
    fig.text(0.040, 0.048,
             ("For educational purposes only; not medical advice." if EN
              else "本内容仅供医学科普，不构成诊疗建议。"),
             ha="left", va="center", fontsize=10.5, color=GREY)
    fig.text(0.960, 0.048,
             ("Next: CAR-T for solid tumours — where it stands →" if EN
              else "下期：CAR-T 治疗实体瘤，进展到哪了 →"),
             ha="right", va="center", fontsize=12, fontweight="bold",
             color=DEEP)

    suffix = "_en" if EN else ""
    path = os.path.join(OUT_DIR, f"post03_infographic{suffix}.png")
    fig.savefig(path, facecolor=BG)
    plt.close(fig)
    print(f"Saved -> {path}")
    return path


def main():
    stats = compute()
    print(json.dumps({k: v for k, v in stats.items()
                      if k not in ("researched",)}, ensure_ascii=False))
    for lang in ("zh", "en"):
        build(stats, lang)


if __name__ == "__main__":
    main()
