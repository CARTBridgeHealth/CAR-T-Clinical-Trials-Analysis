"""
fetch_cart_data.py
------------------
Step 1: Pull CAR-T clinical trial data from ClinicalTrials.gov API v2
Saves raw JSON and a cleaned CSV to the /data folder.

The registry search is full-text, so it also returns studies that only mention
CAR-T in passing. Each record is therefore classified (classify_cart_trials.py)
and only trials that actually administer a CAR-T product are written to
cart_trials_clean.csv. Everything else goes to cart_trials_excluded.csv with
the reason it was left out.

Run with --no-fetch to re-classify the saved raw JSON without calling the API,
e.g. after editing data/cart_scope_overrides.csv.
"""

import requests
import pandas as pd
import json
import sys
import time
import os

from classify_cart_trials import classify, load_overrides

# ── Config ──────────────────────────────────────────────────────────────────
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
RAW_JSON   = os.path.join(OUTPUT_DIR, "cart_trials_raw.json")
CLEAN_CSV  = os.path.join(OUTPUT_DIR, "cart_trials_clean.csv")
EXCLUDED_CSV = os.path.join(OUTPUT_DIR, "cart_trials_excluded.csv")

BASE_URL   = "https://clinicaltrials.gov/api/v2/studies"
SEARCH_TERM = "CAR-T OR CAR T-cell OR chimeric antigen receptor T-cell"

# Fields we want back from the API
FIELDS = [
    "NCTId",
    "BriefTitle",
    "OverallStatus",
    "Phase",
    "StartDate",
    "PrimaryCompletionDate",
    "CompletionDate",
    "EnrollmentCount",
    "Condition",
    "InterventionName",
    "InterventionType",
    "LeadSponsorName",
    "LeadSponsorClass",
    "LocationCountry",
    "MinimumAge",
    "MaximumAge",
    "Gender",
    "PrimaryOutcomeMeasure",
    "ResultsFirstSubmitDate",
    # Read only by the classifier, to see WHERE in a record CAR-T is named.
    "StudyType",
    "OfficialTitle",
    "BriefSummary",
    "DetailedDescription",
    "InterventionDescription",
    "InterventionOtherName",
    "ArmGroupLabel",
    "ArmGroupDescription",
    "Keyword",
    "PrimaryOutcomeDescription",
    "SecondaryOutcomeMeasure",
    "SecondaryOutcomeDescription",
]


# ── Step 1: Fetch raw data from API ─────────────────────────────────────────
def fetch_all_trials():
    """Page through the API and collect all CAR-T studies."""
    all_studies = []
    next_token  = None
    page        = 1

    print("Fetching CAR-T trials from ClinicalTrials.gov...")

    while True:
        params = {
            "query.term": SEARCH_TERM,
            "pageSize":   1000,
            "format":     "json",
            "fields":     ",".join(FIELDS),
        }
        if next_token:
            params["pageToken"] = next_token

        try:
            resp = requests.get(BASE_URL, params=params, timeout=180)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            # A partial fetch would silently shrink every count on the site,
            # so stop here and keep last month's files instead.
            sys.exit(f"  Request error on page {page}: {e}\n"
                     "  Aborting; existing data left untouched.")

        studies = data.get("studies", [])
        all_studies.extend(studies)
        print(f"  Page {page}: fetched {len(studies)} records "
              f"(total so far: {len(all_studies)})")

        next_token = data.get("nextPageToken")
        if not next_token:
            break

        page += 1
        time.sleep(0.5)   # be polite to the API

    print(f"\nDone. Total records fetched: {len(all_studies)}\n")
    return all_studies


# ── Step 2: Flatten nested JSON into a flat dict ─────────────────────────────
def extract_fields(study: dict) -> dict:
    """Pull the fields we need out of one study's nested JSON."""
    proto  = study.get("protocolSection", {})
    id_mod = proto.get("identificationModule", {})
    stat   = proto.get("statusModule", {})
    design = proto.get("designModule", {})
    desc   = proto.get("descriptionModule", {})
    elig   = proto.get("eligibilityModule", {})
    arms   = proto.get("armsInterventionsModule", {})
    spons  = proto.get("sponsorCollaboratorsModule", {})
    locs   = proto.get("contactsLocationsModule", {})
    res    = study.get("resultsSection", {})

    # Interventions — join multiple names with a pipe
    interventions = arms.get("interventions", [])
    intervention_names = " | ".join(
        i.get("name", "") for i in interventions
    )
    intervention_types = " | ".join(
        i.get("type", "") for i in interventions
    )

    # Conditions — join multiples with a pipe.
    # These live in conditionsModule, not identificationModule; reading the
    # wrong module silently produced an empty column for every trial.
    conditions = " | ".join(
        proto.get("conditionsModule", {}).get("conditions", [])
    )

    # Countries — join multiples with a pipe
    locations  = locs.get("locations", [])
    countries  = " | ".join(
        set(l.get("country", "") for l in locations if l.get("country"))
    )

    # Primary outcomes
    outcomes = proto.get("outcomesModule", {})
    primary  = outcomes.get("primaryOutcomes", [])
    primary_outcome = primary[0].get("measure", "") if primary else ""

    return {
        "trial_id":           id_mod.get("nctId", ""),
        "title":              id_mod.get("briefTitle", ""),
        "status":             stat.get("overallStatus", ""),
        "phase":              " | ".join(design.get("phases", [])),
        "start_date":         stat.get("startDateStruct", {}).get("date", ""),
        "completion_date":    stat.get("completionDateStruct", {}).get("date", ""),
        "primary_completion": stat.get("primaryCompletionDateStruct", {}).get("date", ""),
        "enrollment":         design.get("enrollmentInfo", {}).get("count", None),
        "enrollment_type":    design.get("enrollmentInfo", {}).get("type", ""),
        "conditions":         conditions,
        "intervention_names": intervention_names,
        "intervention_types": intervention_types,
        "sponsor":            spons.get("leadSponsor", {}).get("name", ""),
        "sponsor_class":      spons.get("leadSponsor", {}).get("class", ""),
        "countries":          countries,
        "min_age":            elig.get("minimumAge", ""),
        "max_age":            elig.get("maximumAge", ""),
        "gender":             elig.get("sex", ""),
        "std_ages":           " | ".join(elig.get("stdAges", [])),
        "primary_outcome":    primary_outcome,
        "results_posted":     bool(res),
        "is_pediatric":       "CHILD" in elig.get("stdAges", []),
    }


# ── Step 3: Save raw JSON ────────────────────────────────────────────────────
def save_raw(studies: list):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(RAW_JSON, "w", encoding="utf-8") as f:
        json.dump(studies, f, indent=2)
    print(f"Raw JSON saved → {RAW_JSON}")


# ── Step 4: Build and save clean CSV ────────────────────────────────────────
def save_clean(studies: list):
    overrides = load_overrides()
    rows, excluded = [], []
    for s in studies:
        scope, basis = classify(s, overrides)
        row = extract_fields(s)
        if scope == "product":
            rows.append(row)
        else:
            excluded.append({"trial_id": row["trial_id"], "scope": scope,
                             "basis": basis, "title": row["title"],
                             "status": row["status"]})
    df   = pd.DataFrame(rows)

    ex = pd.DataFrame(excluded).sort_values(["scope", "trial_id"])
    ex.to_csv(EXCLUDED_CSV, index=False, encoding="utf-8")
    print(f"Search returned {len(studies)} studies: {len(rows)} administer a "
          f"CAR-T product, {len(excluded)} excluded")
    print(ex["scope"].value_counts().to_string())
    print(f"Excluded list saved → {EXCLUDED_CSV}\n")

    # Basic cleaning
    df["enrollment"]  = pd.to_numeric(df["enrollment"], errors="coerce")
    df["start_date"]  = pd.to_datetime(df["start_date"], errors="coerce")
    df["completion_date"] = pd.to_datetime(df["completion_date"], errors="coerce")
    df["start_year"]  = df["start_date"].dt.year
    df["is_pediatric"] = df["is_pediatric"].fillna(False).astype(bool)

    # Normalize phase labels  (API returns "PHASE1", "PHASE2", etc.)
    phase_map = {
        "PHASE1": "Phase 1",
        "PHASE2": "Phase 2",
        "PHASE3": "Phase 3",
        "PHASE4": "Phase 4",
        "NA":     "N/A",
    }
    df["phase"] = df["phase"].replace(phase_map)

    df.to_csv(CLEAN_CSV, index=False, encoding="utf-8")
    print(f"Clean CSV saved  → {CLEAN_CSV}")
    print(f"\nShape: {df.shape[0]} rows × {df.shape[1]} columns")
    print("\nColumn overview:")
    print(df.dtypes)
    print("\nStatus breakdown:")
    print(df["status"].value_counts().head(10))
    print("\nPhase breakdown:")
    print(df["phase"].value_counts())
    return df


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if "--no-fetch" in sys.argv:
        with open(RAW_JSON, encoding="utf-8") as f:
            studies = json.load(f)
        print(f"Re-classifying {len(studies)} saved records (no API call)\n")
    else:
        studies = fetch_all_trials()
        if not studies:
            sys.exit("No studies fetched; leaving existing data untouched.")
        save_raw(studies)
    df = save_clean(studies)
    print("\nStep 1 complete. Check /data folder for:")
    print("  cart_trials_raw.json  — original API response")
    print("  cart_trials_clean.csv — flattened, ready for SQL import")
