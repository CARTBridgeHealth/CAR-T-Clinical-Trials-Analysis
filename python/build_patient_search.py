"""Build data/patient_search.json for the patient disease-search page.

Reads the existing clinical-trial and approved-product CSVs, tags each trial
and product with the disease topics it matches, and writes one JSON file the
static page (patient_search.html) loads. No network access.

Run from the repository root:
    python python/build_patient_search.py
"""
import csv
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRIALS_CSV = ROOT / "data" / "cart_trials_clean.csv"
PRODUCTS_CSV = ROOT / "data" / "approved_products.csv"
CENTERS_CSV = ROOT / "data" / "treatment_centers.csv"
OUT_JSON = ROOT / "data" / "patient_search.json"

# Each topic: bilingual label, regex terms matched against trial title +
# conditions, regex terms matched against approved-product name + indications,
# and the CAR target used to pick treatment centres.
TOPICS = [
    {
        "id": "sle",
        "name_en": "Systemic lupus erythematosus (SLE)",
        "name_cn": "系统性红斑狼疮 (SLE)",
        "trial_terms": [r"lupus", r"\bSLE\b"],
        "product_terms": [],
        "target": "CD19",
    },
    {
        "id": "myeloma",
        "name_en": "Multiple myeloma",
        "name_cn": "多发性骨髓瘤",
        "trial_terms": [r"myeloma"],
        "product_terms": [r"myeloma", r"\bMM\b"],
        "target": "BCMA",
    },
    {
        "id": "lymphoma",
        "name_en": "B-cell lymphoma",
        "name_cn": "B细胞淋巴瘤",
        "trial_terms": [r"lymphoma", r"\bDLBCL\b", r"\bLBCL\b", r"follicular", r"mantle cell", r"\bPMBCL\b"],
        "product_terms": [r"lymphoma", r"\bDLBCL\b", r"\bLBCL\b", r"\bFL\b", r"\bMCL\b", r"\bPMBCL\b", r"\bMZL\b"],
        "target": "CD19",
    },
    {
        "id": "all",
        "name_en": "B-cell acute lymphoblastic leukaemia (B-ALL)",
        "name_cn": "B细胞急性淋巴细胞白血病 (B-ALL)",
        "trial_terms": [r"lymphoblastic", r"\bB-?ALL\b"],
        "product_terms": [r"\bALL\b", r"lymphoblastic"],
        "target": "CD19",
    },
    {
        "id": "cll",
        "name_en": "Chronic lymphocytic leukaemia (CLL)",
        "name_cn": "慢性淋巴细胞白血病 (CLL)",
        "trial_terms": [r"chronic lymphocytic", r"\bCLL\b"],
        "product_terms": [r"\bCLL\b"],
        "target": "CD19",
    },
    {
        "id": "gastric",
        "name_en": "Gastric / gastro-oesophageal cancer (CLDN18.2)",
        "name_cn": "胃癌 / 食管胃结合部癌 (CLDN18.2)",
        "trial_terms": [r"gastric", r"gastroesophageal", r"oesophagogastric", r"stomach", r"claudin", r"CLDN18"],
        "product_terms": [r"satri", r"gastric", r"CLDN18"],
        "target": "CLDN18.2",
    },
]


def matches(text, patterns):
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)


def split_multi(value):
    return [v.strip() for v in re.split(r"[|;,]", value or "") if v.strip()]


def build_trials():
    trials = []
    with TRIALS_CSV.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            text = f"{row['title']} | {row['conditions']}"
            topics = [t["id"] for t in TOPICS if matches(text, t["trial_terms"])]
            if not topics:
                continue
            trials.append({
                "nct": row["trial_id"],
                "title": row["title"],
                "status": row["status"],
                "phase": row["phase"],
                "start_year": int(float(row["start_year"])) if row["start_year"] else None,
                "countries": split_multi(row["countries"]),
                "conditions": split_multi(row["conditions"]),
                "sponsor": row["sponsor"],
                "is_pediatric": row["is_pediatric"].strip().lower() in ("true", "1", "yes"),
                "topics": topics,
            })
    return trials


def build_products():
    products = []
    with PRODUCTS_CSV.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            text = f"{row['product']} | {row['indications']}"
            topics = [t["id"] for t in TOPICS if matches(text, t["product_terms"])]
            products.append({
                "product": row["product"],
                "company": row["company"],
                "country": row["country"],
                "approval_year": row["approval_year"],
                "target": row["target"],
                "indications": row["indications"],
                "cn_trade_name": row["cn_trade_name"],
                "nmpa_approval_no": row["nmpa_approval_no"],
                "topics": topics,
            })
    return products


def build_centers():
    centers = []
    with CENTERS_CSV.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            centers.append({
                "hospital": row["hospital"],
                "country": row["country"],
                "city": row["city"],
                "cart_products": row["cart_products"],
                "est_cost_usd": row["est_cost_usd"],
                "wait_weeks": row["wait_weeks"],
                "english_support": row["english_support"].strip().lower() in ("true", "1", "yes"),
                "targets": [t for t in ("CD19", "BCMA", "CLDN18.2") if t in row["cart_products"]],
            })
    return centers


def main():
    trials = build_trials()
    products = build_products()
    centers = build_centers()

    summary = {
        "generated": date.today().isoformat(),
        "disclaimer_version": 1,
        "topics": [
            {k: v for k, v in t.items() if k in ("id", "name_en", "name_cn", "target")}
            | {"trial_count": sum(1 for x in trials if t["id"] in x["topics"])}
            for t in TOPICS
        ],
        "trials": trials,
        "products": products,
        "centers": centers,
    }

    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wrote {OUT_JSON}")
    for t in summary["topics"]:
        n_prod = sum(1 for p in products if t["id"] in p["topics"])
        print(f"  {t['id']:8s} trials={t['trial_count']:4d}  approved_products={n_prod}")


if __name__ == "__main__":
    main()
