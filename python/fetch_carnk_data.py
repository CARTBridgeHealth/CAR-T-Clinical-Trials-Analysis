"""
fetch_carnk_data.py
-------------------
Pull interventional CAR-NK clinical trials from ClinicalTrials.gov API v2,
excluding NK-92-derived products and CAR-T-only studies, and print the
summary statistics used in the CAR-NK landscape paragraph.
Saves raw JSON and a cleaned CSV (with inclusion flags) to the /data folder.

Screening
  1. Two API searches (narrow CAR-NK phrases + broad CAR AND NK), unioned,
     restricted to interventional studies.
  2. Text screen: title, interventions, summary and detailed description
     must describe a CAR-engineered NK cell product.
  3. Exclude NK-92 / pNK / haNK-derived products, CAR-NKT, CAR-T-only
     studies, and non-NK platforms (ITNK, gamma-delta T, in vivo CAR).
  4. Manual adjudications below override the text screen where the
     registry wording is misleading.
"""

import requests
import pandas as pd
import json
import re
import time
import os
from datetime import date

# ── Config ──────────────────────────────────────────────────────────────────
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
RAW_JSON   = os.path.join(OUTPUT_DIR, "carnk_trials_raw.json")
CLEAN_CSV  = os.path.join(OUTPUT_DIR, "carnk_trials_clean.csv")

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
SEARCH_TERMS = [
    '"CAR-NK" OR "CAR NK" OR CARNK OR "chimeric antigen receptor natural killer" '
    'OR "chimeric antigen receptor NK" OR "CAR-engineered NK"',
    '("chimeric antigen receptor" OR CAR) AND '
    '("natural killer" OR NK OR "NK cell" OR "NK cells" OR iNK)',
    # Named CAR-NK products whose registry records never say "CAR" or "NK"
    # in the title, summary or interventions (e.g. the FT5xx series).
    'FT596 OR FT576 OR FT522 OR NKX019 OR NKX101 OR AB-201 OR "CNTY-101" '
    'OR TAK-007 OR QN-019a OR QN-023a OR "KN5501" OR SN301A',
]

CARNK_RE = re.compile(
    r"CAR[\s\-+/.]*(?:i|p|CB|u|ra)?NK"
    r"|chimeric antigen receptor.{0,100}?(?:natural[\s\-]killer|\bNK)"
    r"|\bCAR\b.{0,60}?(?:\bNK\b|\bNK[\s\-]cell|natural[\s\-]killer)",
    re.IGNORECASE | re.DOTALL,
)
NK92_RE = re.compile(r"NK[\s\-]?92|\bt?-?haNK\b|CAR[\s\-]?pNK", re.IGNORECASE)
NKT_RE  = re.compile(r"NK[\s\-]?T[\s\-]cell|\bNKT\b|\biNKT\b|natural killer T", re.IGNORECASE)
CART_RE = re.compile(r"CAR[\s\-]?T\b|CAR T[\s\-]cell", re.IGNORECASE)

# Manual adjudication: True = include, False = exclude
MANUAL = {
    # CAR-NK products whose registry text never spells out "CAR-NK"
    "NCT05336409": (True,  "CNTY-101, CD19 CAR iPSC-NK"),
    "NCT06255028": (True,  "CNTY-101, CD19 CAR iPSC-NK"),
    "NCT05020015": (True,  "TAK-007, CD19 CAR cord-blood NK"),
    "NCT06342986": (True,  "FT536, MICA/B CAR iPSC-NK"),
    "NCT07560865": (True,  "FT536, MICA/B CAR iPSC-NK"),
    "NCT05137275": (True,  "5T4 CAR-raNK (primary NK)"),
    "NCT07211737": (True,  "NKG2D.zeta CAR-NK + GD2 CAR-T combination"),
    "NCT04245722": (True,  "FT596, CD19 CAR iPSC-NK"),
    "NCT04555811": (True,  "FT596, CD19 CAR iPSC-NK"),
    "NCT05934097": (True,  "FT596, CD19 CAR iPSC-NK"),
    "NCT05950334": (True,  "FT522, CD19 CAR iPSC-NK with ADR"),
    "NCT05678205": (True,  "AB-201, HER2 CAR-NK"),
    "NCT06341647": (True,  "AB-201, HER2 CAR-NK"),
    # Registry wording suggests CAR-NK but the product is not
    "NCT05248048": (False, "NKG2D CAR-T (CAR-NK text is a registry typo)"),
    "NCT03882840": (False, "ITNK: reprogrammed T cells, not NK"),
    "NCT04747093": (False, "CAR-ITNK: reprogrammed T cells, not NK"),
    "NCT04107142": (False, "CAR gamma-delta T cells"),
    "NCT05976906": (False, "NKG2D/NKp44 CAR-T"),
    "NCT06539338": (False, "INT2104, in vivo lentiviral CAR"),
    "NCT06434363": (False, "AD-PluReceptor NK, no CAR"),
    "NCT03692429": (False, "CYAD-101, NKG2D CAR-T"),
    "NCT05296525": (False, "GDA-201, nicotinamide-expanded NK, no CAR"),
}


# ── Step 1: Fetch raw data from API ─────────────────────────────────────────
def fetch_search(term):
    studies, next_token = [], None
    while True:
        params = {
            "query.term":      term,
            "filter.advanced": "AREA[StudyType]INTERVENTIONAL",
            "pageSize":        1000,
            "format":          "json",
        }
        if next_token:
            params["pageToken"] = next_token
        resp = requests.get(BASE_URL, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        studies.extend(data.get("studies", []))
        next_token = data.get("nextPageToken")
        if not next_token:
            return studies
        time.sleep(0.5)


def fetch_all_trials():
    print("Fetching CAR-NK trials from ClinicalTrials.gov...")
    by_id = {}
    for term in SEARCH_TERMS:
        studies = fetch_search(term)
        print(f"  Search returned {len(studies)} interventional records")
        for s in studies:
            by_id[s["protocolSection"]["identificationModule"]["nctId"]] = s
    print(f"  Unique records: {len(by_id)}")
    return list(by_id.values())


# ── Step 2: Flatten + classify ───────────────────────────────────────────────
def extract_fields(study: dict) -> dict:
    proto  = study.get("protocolSection", {})
    id_mod = proto.get("identificationModule", {})
    stat   = proto.get("statusModule", {})
    design = proto.get("designModule", {})
    desc   = proto.get("descriptionModule", {})
    arms   = proto.get("armsInterventionsModule", {})
    spons  = proto.get("sponsorCollaboratorsModule", {})
    locs   = proto.get("contactsLocationsModule", {})
    nct    = id_mod.get("nctId", "")

    interventions = arms.get("interventions", [])
    iv_text = " | ".join(
        f"{i.get('name', '')} {i.get('description', '')} "
        f"{' '.join(i.get('otherNames', []))}" for i in interventions
    )
    title = f"{id_mod.get('briefTitle', '')} {id_mod.get('officialTitle', '')}"
    core_text = f"{title} {iv_text}"
    full_text = (f"{core_text} {desc.get('briefSummary', '')} "
                 f"{desc.get('detailedDescription', '')}")

    is_carnk = bool(CARNK_RE.search(full_text))
    is_nk92  = bool(NK92_RE.search(full_text))
    is_nkt   = bool(NKT_RE.search(core_text))
    # CAR-T in title/interventions with no CAR-NK there → CAR-T study
    is_cart  = bool(CART_RE.search(core_text)) and not CARNK_RE.search(core_text)
    included = is_carnk and not (is_nk92 or is_nkt or is_cart)
    reason   = ""
    if nct in MANUAL:
        included, reason = MANUAL[nct]

    countries = " | ".join(sorted(
        {l.get("country", "") for l in locs.get("locations", []) if l.get("country")}
    ))

    return {
        "trial_id":           nct,
        "title":              id_mod.get("briefTitle", ""),
        "status":             stat.get("overallStatus", ""),
        "phase":              " | ".join(design.get("phases", [])),
        "start_date":         stat.get("startDateStruct", {}).get("date", ""),
        # ACTUAL = sponsor confirmed the start; ESTIMATED = never confirmed.
        # Kept in the CSV so the chart script doesn't need the raw JSON.
        "start_date_type":    stat.get("startDateStruct", {}).get("type", ""),
        "first_posted":       stat.get("studyFirstPostDateStruct", {}).get("date", ""),
        "enrollment":         design.get("enrollmentInfo", {}).get("count", None),
        "conditions":         " | ".join(proto.get("conditionsModule", {}).get("conditions", [])),
        "intervention_names": " | ".join(i.get("name", "") for i in interventions),
        "sponsor":            spons.get("leadSponsor", {}).get("name", ""),
        "sponsor_class":      spons.get("leadSponsor", {}).get("class", ""),
        "countries":          countries,
        "results_posted":     bool(study.get("hasResults")) or "resultsSection" in study,
        "is_carnk":           is_carnk,
        "is_nk92":            is_nk92,
        "is_nkt":             is_nkt,
        "is_cart":            is_cart,
        "combo_with_cart":    bool(CART_RE.search(core_text)),
        "manual_note":        reason,
        "included":           included,
    }


# ── Step 3: Save + summarize ────────────────────────────────────────────────
def main():
    studies = fetch_all_trials()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(RAW_JSON, "w", encoding="utf-8") as f:
        json.dump(studies, f, indent=2)

    df = pd.DataFrame([extract_fields(s) for s in studies]).sort_values("trial_id")
    df["start_year"] = pd.to_datetime(df["start_date"], errors="coerce", format="mixed").dt.year
    df["first_posted_year"] = pd.to_datetime(df["first_posted"], errors="coerce", format="mixed").dt.year
    df.to_csv(CLEAN_CSV, index=False, encoding="utf-8")

    inc = df[df["included"]]
    n = len(inc)
    withdrawn = (inc["status"] == "WITHDRAWN").sum()
    auto = ~df["trial_id"].isin(MANUAL)

    print(f"\n── Screening (search date {date.today()}) ──")
    print(f"  Interventional records screened:   {len(df)}")
    print(f"  No CAR-NK product described:       {(auto & ~df['is_carnk']).sum()}")
    print(f"  Excluded NK-92-derived:            {(auto & df['is_carnk'] & df['is_nk92']).sum()}")
    print(f"  Excluded CAR-NKT:                  {(auto & df['is_carnk'] & ~df['is_nk92'] & df['is_nkt']).sum()}")
    print(f"  Excluded CAR-T only:               {(auto & df['is_carnk'] & ~df['is_nk92'] & ~df['is_nkt'] & df['is_cart']).sum()}")
    print(f"  Manual include / exclude:          "
          f"{sum(v[0] for v in MANUAL.values())} / {sum(not v[0] for v in MANUAL.values())}")
    print(f"  Included CAR-NK trials:            {n}")
    print(f"    of which combined with CAR-T:    {inc['combo_with_cart'].sum()}")

    print(f"\n── Key numbers ──")
    print(f"  Withdrawn:        {withdrawn} ({withdrawn / n:.1%})")
    print(f"  Results posted:   {inc['results_posted'].sum()}")
    for y in (2024, 2025, 2026):
        s = (inc["start_year"] == y).sum()
        p = (inc["first_posted_year"] == y).sum()
        print(f"  {y}: started {s} ({s / n:.1%}) | first registered {p} ({p / n:.1%})")
    print("\n  Status breakdown:")
    print(inc["status"].value_counts().to_string())
    print("\n  Start year | first-registered year:")
    yrs = pd.concat([inc["start_year"].value_counts().rename("started"),
                     inc["first_posted_year"].value_counts().rename("registered")],
                    axis=1).fillna(0).astype(int).sort_index()
    print(yrs.to_string())
    print(f"\nSaved → {RAW_JSON}\n        {CLEAN_CSV}")


if __name__ == "__main__":
    main()
