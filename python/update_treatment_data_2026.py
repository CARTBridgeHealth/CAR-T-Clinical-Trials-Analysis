"""
update_treatment_data_2026.py
------------------------------
Writes the manually researched treatment datasets to CSV.

NOTE ON WHAT THIS DOES NOT DO: despite the name, this script fetches nothing.
It serialises the hand-maintained Python literals below, so running it monthly
produces an identical file every time. Prices, wait times and approval counts
are a human research snapshot — to change them, edit the literals here.

The country comparison shown on index.html is NOT produced from here. It reads
data/country_comparison.json, which carries its own `as_of` date and is edited
by hand so the page can state honestly when a person last checked the figures.
Keep the two in sync when you revise either.
"""

import json
import pandas as pd
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── 1. Latest Approved Products (July 2026) ──────────────────────────────────
approved_products = [

    # USA — FDA Approved (7 products as of 2026)
    {"product": "Tisagenlecleucel (Kymriah)",              "company": "Novartis",                   "country": "USA", "approval_year": 2017, "target": "CD19",      "indications": "Pediatric ALL, DLBCL",         "us_price_usd": 475000, "cn_price_usd": None,   "solid_tumor": False, "source": ""},
    {"product": "Axicabtagene ciloleucel (Yescarta)",      "company": "Kite/Gilead",                "country": "USA", "approval_year": 2017, "target": "CD19",      "indications": "DLBCL, FL, PMBCL",            "us_price_usd": 373000, "cn_price_usd": 165000, "solid_tumor": False, "source": ""},
    {"product": "Brexucabtagene autoleucel (Tecartus)",    "company": "Kite/Gilead",                "country": "USA", "approval_year": 2020, "target": "CD19",      "indications": "MCL, B-ALL",                  "us_price_usd": 373000, "cn_price_usd": None,   "solid_tumor": False, "source": ""},
    {"product": "Lisocabtagene maraleucel (Breyanzi)",     "company": "Bristol Myers Squibb",       "country": "USA", "approval_year": 2021, "target": "CD19",      "indications": "DLBCL, CLL, MCL, FL",         "us_price_usd": 410300, "cn_price_usd": None,   "solid_tumor": False, "source": ""},
    {"product": "Idecabtagene vicleucel (Abecma)",         "company": "Bristol Myers Squibb",       "country": "USA", "approval_year": 2021, "target": "BCMA",      "indications": "Multiple Myeloma",            "us_price_usd": 419500, "cn_price_usd": None,   "solid_tumor": False, "source": ""},
    {"product": "Ciltacabtagene autoleucel (Carvykti)",    "company": "Janssen / Legend Biotech",   "country": "USA", "approval_year": 2022, "target": "BCMA",      "indications": "Multiple Myeloma",            "us_price_usd": 465000, "cn_price_usd": 158000, "solid_tumor": False, "source": ""},
    {"product": "Obe-cel (Aucatzyl)",                      "company": "Autolus",                    "country": "USA", "approval_year": 2024, "target": "CD19",      "indications": "Adult B-ALL",                 "us_price_usd": 450000, "cn_price_usd": None,   "solid_tumor": False, "source": ""},

    # China — NMPA Approved (9 products as of July 2026)
    # VERIFIED against the NMPA record. Marketing authorisation holder is
    # 复星凯瑞（上海）生物科技有限公司 (Shanghai Fosun Kairos) — the JV is widely
    # written "Fosun Kite", but the registry names Fosun Kairos as the holder.
    {"product": "Axicabtagene ciloleucel (Yescarta)",      "company": "Shanghai Fosun Kairos",      "country": "China", "approval_year": 2021, "target": "CD19",  "indications": "DLBCL, FL, MCL",              "us_price_usd": None,   "cn_price_usd": 165000, "solid_tumor": False, "cn_trade_name": "奕凯达", "nmpa_approval_no": "国药准字S20210019", "nmpa_approval_date": "2021-06-22", "source": "NMPA Certificate of a Pharmaceutical Product 沪20240406号, issued 2024-12-11 by Shanghai MPA"},
    {"product": "Relmacabtagene autoleucel (Relma-cel)",   "company": "JW Therapeutics (Shanghai)", "country": "China", "approval_year": 2021, "target": "CD19",  "indications": "DLBCL, B-ALL",               "us_price_usd": None,   "cn_price_usd": 177000, "solid_tumor": False, "cn_trade_name": "倍诺达", "nmpa_approval_no": "国药准字S20210035", "nmpa_approval_date": "2021-09-01", "source": "NMPA CPP 沪20250119号, Shanghai MPA, issued 2025-03-27, valid to 2027-03-26"},
    {"product": "Equecabtagene autoleucel (Fucaso)",       "company": "Nanjing IASO",               "country": "China", "approval_year": 2023, "target": "BCMA",  "indications": "Multiple Myeloma",            "us_price_usd": None,   "cn_price_usd": 160000, "solid_tumor": False, "cn_trade_name": "福可苏", "nmpa_approval_no": "国药准字S20230040", "nmpa_approval_date": "2023-06-30", "source": "NMPA CPP 苏20260406号, Jiangsu MPA, issued 2026-06-22, valid to 2029-06-21"},
    {"product": "Ciltacabtagene autoleucel (Carvykti)",    "company": "南京传奇生物 Nanjing Legend",  "country": "China", "approval_year": 2024, "target": "BCMA",  "indications": "r/r MM, >=3 prior lines (conditional approval)", "us_price_usd": None,   "cn_price_usd": 158000, "solid_tumor": False, "cn_trade_name": "卡卫荻", "nmpa_approval_no": "", "nmpa_approval_date": "2024-09-12", "source": "NMPA announcement 索引号 XZXK-2024-349, published 2024-09-12, 附条件批准. The announcement says 近期 (recently), so this is the announcement date; a 2025 NHSA submission dates the listing to 2024年8月. Exact approval date needs the 批准文号 record."},
    {"product": "Zevorcabtagene autoleucel (Zevor-cel)",   "company": "CARsgen Life Sciences",      "country": "China", "approval_year": 2024, "target": "BCMA",  "indications": "r/r MM, >=3 prior lines",     "us_price_usd": None,   "cn_price_usd": 158000, "solid_tumor": False, "cn_trade_name": "赛恺泽", "nmpa_approval_no": "国药准字S20240006", "nmpa_approval_date": "2024-02-23", "source": "NMPA 境内生产药品 record 国药准字S20240006, 批准日期 2024-02-23, 上市许可持有人 恺兴生命科技（上海）有限公司, 生产单位 上海科济制药有限公司, 药品本位码 86984167000014. Date corroborated by NHSA submission YPSW202500100."},
    {"product": "Inaticabtagene autoleucel (Yuanruida)",   "company": "Juventas Cell Therapy",      "country": "China", "approval_year": 2023, "target": "CD19",  "indications": "Adult r/r B-ALL",             "us_price_usd": None,   "cn_price_usd": None,   "solid_tumor": False, "cn_trade_name": "源瑞达", "nmpa_approval_no": "国药准字S20230065", "nmpa_approval_date": "2023-11-07", "source": "NMPA CPP 津20250029号, Tianjin MPA, issued 2025-02-21; that CPP lapsed 2026-06-28 (export certificate expiry, not a withdrawal of the marketing approval)"},
    {"product": "Satricabtagene autoleucel (Satri-cel)",   "company": "CARsgen Life Sciences",                    "country": "China", "approval_year": 2026, "target": "CLDN18.2", "indications": "Gastric/GEJ Cancer 🆕 World First Solid Tumor CAR-T", "us_price_usd": None, "cn_price_usd": None, "solid_tumor": True, "cn_trade_name": "恺力美", "nmpa_approval_no": "国药准字S20260044", "nmpa_approval_date": "2026-06-17", "source": "NMPA CPP 沪20260186号, Shanghai MPA, issued 2026-08-14, valid to 2029-08-13"},
]


# ── 2. Cost Comparison (2026 updated) ────────────────────────────────────────
# Derived from data/country_comparison.json — the single hand-maintained source
# for country cost figures, and what index.html renders. Previously these were
# separate literals holding single values, which disagreed with the ranges shown
# on the page for all seven countries. Edit the JSON, not this.
with open(os.path.join(OUTPUT_DIR, "country_comparison.json"), encoding="utf-8") as f:
    _comparison = json.load(f)

cost_comparison = [
    {
        "country":            r["country"],
        "cost_low_usd":       r["cost_low_usd"],
        "cost_high_usd":      r["cost_high_usd"],
        "wait_low_weeks":     r["wait_low_weeks"],
        "wait_high_weeks":    r["wait_high_weeks"],
        "approved_products":  r["approved_products"],
        "solid_tumor_cart":   r["solid_tumor_cart"],
        "insurance":          r["insurance"],
        "as_of":              _comparison["as_of"],
    }
    for r in _comparison["countries"]
]


# Approved-product counts are COUNTED from the list above, never typed.
# A hand-entered "9" for China sat in this file from the first commit while the
# list held six entries, and propagated to the website, the investor deck and
# the patient guide before anyone compared the two.
approved_by_country = {}
for _p in approved_products:
    approved_by_country[_p["country"]] = approved_by_country.get(_p["country"], 0) + 1


# ── 3. Top Treatment Centers (2026) ──────────────────────────────────────────
treatment_centers = [

    # China — Top centers accepting international patients
    {"hospital": "Chinese PLA General Hospital (301)",       "country": "China",  "city": "Beijing",   "tier": "Top",      "intl_patients": True,  "cart_products": "CD19, BCMA, CLDN18.2",  "est_cost_usd": "50,000-80,000",  "wait_weeks": 2,  "english_support": True, "source": ""},
    {"hospital": "Peking University Cancer Hospital",        "country": "China",  "city": "Beijing",   "tier": "Top",      "intl_patients": True,  "cart_products": "Multiple CD19/BCMA","est_cost_usd": "55,000-85,000",  "wait_weeks": 3,  "english_support": True, "source": ""},
    {"hospital": "Fudan University Cancer Hospital",         "country": "China",  "city": "Shanghai",  "tier": "Top",      "intl_patients": True,  "cart_products": "CD19, BCMA, CLDN18.2","est_cost_usd": "60,000-90,000","wait_weeks": 3,  "english_support": True, "source": ""},
    {"hospital": "Zhejiang University First Hospital",       "country": "China",  "city": "Hangzhou",  "tier": "Top",      "intl_patients": True,  "cart_products": "CD19, CD22, BCMA", "est_cost_usd": "50,000-75,000",  "wait_weeks": 2,  "english_support": True, "source": ""},
    {"hospital": "Shanghai Ruijin Hospital",                 "country": "China",  "city": "Shanghai",  "tier": "Top",      "intl_patients": True,  "cart_products": "CD19, trials",     "est_cost_usd": "50,000-80,000",  "wait_weeks": 3,  "english_support": True, "source": ""},

    # USA
    {"hospital": "MD Anderson Cancer Center",                "country": "USA",    "city": "Houston TX","tier": "Top",      "intl_patients": True,  "cart_products": "All 7 FDA-approved","est_cost_usd": "450,000-650,000","wait_weeks": 12, "english_support": True, "source": ""},
    {"hospital": "Memorial Sloan Kettering",                 "country": "USA",    "city": "New York NY","tier": "Top",     "intl_patients": True,  "cart_products": "All 7 FDA-approved","est_cost_usd": "430,000-620,000","wait_weeks": 10, "english_support": True, "source": ""},
    {"hospital": "Fred Hutchinson Cancer Center",            "country": "USA",    "city": "Seattle WA","tier": "Top",      "intl_patients": True,  "cart_products": "All 7 FDA-approved","est_cost_usd": "400,000-580,000","wait_weeks": 8,  "english_support": True, "source": ""},

    # Canada
    {"hospital": "Princess Margaret Cancer Centre",          "country": "Canada", "city": "Toronto ON","tier": "Top",      "intl_patients": True,  "cart_products": "Health Canada approved","est_cost_usd": "250,000-350,000","wait_weeks": 16, "english_support": True, "source": ""},
    {"hospital": "CancerCare Manitoba",                      "country": "Canada", "city": "Winnipeg MB","tier": "Regional","intl_patients": False, "cart_products": "Referral to Toronto","est_cost_usd": "Covered (wait list)","wait_weeks": 20, "english_support": True, "source": ""},
]


# ── Save ──────────────────────────────────────────────────────────────────────
pd.DataFrame(approved_products).to_csv(os.path.join(OUTPUT_DIR, "approved_products.csv"), index=False)
pd.DataFrame(cost_comparison).to_csv(os.path.join(OUTPUT_DIR, "cost_comparison.csv"), index=False)
pd.DataFrame(treatment_centers).to_csv(os.path.join(OUTPUT_DIR, "treatment_centers.csv"), index=False)

print("Updated 3 datasets:")
print(f"   approved_products.csv  — {len(approved_products)} products "
      f"({', '.join(f'{k}: {v}' for k, v in sorted(approved_by_country.items()))})")
print(f"   cost_comparison.csv    — {len(cost_comparison)} countries")
print(f"   treatment_centers.csv  — {len(treatment_centers)} hospitals")
print()
print("Notes:")
print(f"   - China {approved_by_country.get('China', 0)} approved products, "
      f"USA {approved_by_country.get('USA', 0)}")
print("   - Satri-cel (CLDN18.2, gastric/GEJ) approved in China 2026-06-17 —")
print("     the first approved CAR-T for a solid tumour anywhere")
print("   - Country cost figures come from country_comparison.json; see")
print("     derive_country_costs.py for how they are built")
