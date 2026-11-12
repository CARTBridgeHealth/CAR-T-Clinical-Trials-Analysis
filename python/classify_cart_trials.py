"""
classify_cart_trials.py
-----------------------
Decide, for each study the registry search returns, whether it is actually a
CAR-T trial.

Why this exists: fetch_cart_data.py uses ClinicalTrials.gov's full-text search,
which matches "CAR-T" anywhere in a record — including eligibility criteria
("no prior CAR-T therapy") and background paragraphs. A November 2026 audit
found the 2,982 rows it returned included knee-osteoarthritis analgesics,
autism rTMS, a fluoride caries model and several hundred lymphoma drug trials
that merely mention CAR-T. Every headline count on the site was inflated.

Scope definition (the thing the headline number counts):

  product         A CAR-engineered T-cell product is given to participants
                  under the study protocol. Includes CAR-T variants on a
                  T-lineage cell (gamma-delta, NKT/iNKT, Treg, CAAR-T, STAR-T,
                  in vivo CAR-T) and trials that combine CAR-T with other drugs.
  related         About CAR-T patients or care, but no CAR-T is given by the
                  study: long-term follow-up, toxicity management, imaging,
                  supportive care, drugs for relapse after CAR-T, observational
                  cohorts. Also records that only mention CAR-T in passing.
  other_modality  A different engineered-cell therapy: CAR-NK, CAR-macrophage,
                  CAR-DC, TCR-T, TIL, CIK.
  unrelated       Nothing to do with CAR-T.

Only `product` rows go into cart_trials_clean.csv. The rest are written to
cart_trials_excluded.csv with the reason, so the cut can be audited.

How a study is classified:
  1. data/cart_scope_overrides.csv, if the trial is listed. These are decisions
     from reading the record by hand, and they always win.
  2. Otherwise the rules in classify_by_rule(), which look at WHERE in the
     record CAR-T is named. The intervention fields are trusted; the summary
     and eligibility text are not.

The rules are deliberately conservative about what they promote to `product`.
A new trial they get wrong is fixed by adding one line to the overrides file.
"""

import csv
import os
import re

OVERRIDES_CSV = os.path.join(os.path.dirname(__file__), "..", "data",
                             "cart_scope_overrides.csv")

SCOPES = ("product", "related", "other_modality", "unrelated")

# CAR-T product language. The bare token "CAR" is matched case-sensitively:
# lower-case "car" is a vehicle, and "Ride-On Car Training" was in the data.
CAR = re.compile(
    r"(?i:chimeric antigen receptor|chimeric auto-?antibody receptor"
    r"|CAR[- ]?T\b|CAR[- ]?T[- ]cell|\bCART\b|CART[- ]?\d|\bCAAR|\bU?CAR-?T"
    r"|\w*leucel\b|CAR[- ]modified|CAR[- ]engineered|CAR[- ]transduced|CAR\+)"
    r"|\bCARs?\b|CAR\d|\d+CAR\b|CAR-[A-Z0-9]")

# Title wording that signals the study is ABOUT CAR-T care rather than a test
# of a CAR-T product. Only consulted when the intervention fields do not name
# a CAR-T product themselves.
CONTEXT_TITLE = re.compile(
    r"\bafter\b|\bpost\b|post-|following|fail|associated|related|induced"
    r"|prophyla|prevent|toxicit|cytokine release|neurotox|ICANS|\bCRS\b"
    r"|caregiver|quality of life|exercise|rehabilit|vaccin|monitor|imaging"
    r"|\bPET\b|follow[- ]?up|long[- ]term|bridging|maintenance|salvage"
    r"|microbio|cognitive|registry|biomarker|predict|cytopenia|infection"
    r"|immunoglobulin|telemedicine|telehealth|wearable|nursing|psycholog"
    r"|sample|specimen|collection|survey|questionnaire|education|palliative"
    r"|nutrition|diet|bispecific antibod|digital|outpatient|remote|symptom",
    re.I)

# Other engineered-cell modalities, read from the title.
OTHER_CELL = re.compile(
    r"CAR[- ]?NK|\bNK cells?\b|natural killer|CAR[- ]?M\b|macrophage"
    r"|CAR[- ]?DC\b|TCR[- ]?T\b|T[- ]cell receptor gene|\bTILs?\b"
    r"|tumor infiltrating lymphocyte|\bCIK\b", re.I)
T_CELL_PRODUCT = re.compile(r"CAR[- ]?T\b|CAR[- ]?T[- ]cell|\bCART\b|NK/T|NKT",
                            re.I)


def zones(study: dict) -> dict:
    """Split a study record into the text zones the rules weigh differently."""
    p = study.get("protocolSection", {})
    idm = p.get("identificationModule", {})
    desc = p.get("descriptionModule", {})
    arms = p.get("armsInterventionsModule", {})
    out = p.get("outcomesModule", {})
    ivs = arms.get("interventions", [])
    outcomes = out.get("primaryOutcomes", []) + out.get("secondaryOutcomes", [])
    return {
        "study_type": p.get("designModule", {}).get("studyType", ""),
        "brief_title": idm.get("briefTitle", ""),
        "title": " | ".join([idm.get("briefTitle", ""),
                             idm.get("officialTitle", "")]),
        "names": " | ".join(i.get("name", "") + " "
                            + " ".join(i.get("otherNames", [])) for i in ivs),
        "own": " | ".join(i.get("description", "") for i in ivs),
        "arm": " | ".join(a.get("label", "") + " " + a.get("description", "")
                          for a in arms.get("armGroups", [])),
        "keywords": " | ".join(p.get("conditionsModule", {}).get("keywords", [])),
        "summary": desc.get("briefSummary", "") + " | "
                   + desc.get("detailedDescription", ""),
        "outcomes": " | ".join(o.get("measure", "") + " "
                               + o.get("description", "") for o in outcomes),
    }


def classify_by_rule(study: dict):
    """Return (scope, basis) from the record's own text."""
    z = zones(study)
    hit = {k: bool(CAR.search(z[k])) for k in
           ("names", "own", "arm", "title", "keywords", "summary", "outcomes")}
    title = z["brief_title"]

    if z["study_type"] == "OBSERVATIONAL":
        # Nothing is administered by an observational study.
        if hit["title"] or hit["names"] or hit["keywords"] or hit["arm"]:
            return "related", "rule: observational study of CAR-T"
        return "unrelated", "rule: observational, CAR-T not its subject"

    if OTHER_CELL.search(title) and not T_CELL_PRODUCT.search(title):
        return "other_modality", "rule: title names another cell therapy"

    if hit["names"]:
        return "product", "rule: CAR-T named as an intervention"
    if hit["own"]:
        return "product", "rule: an intervention is described as CAR-T"

    flagged = bool(CONTEXT_TITLE.search(title))
    if (hit["title"] or hit["keywords"]) and not flagged:
        return "product", "rule: CAR-T in title or keywords"
    if hit["outcomes"] and not flagged and not hit["arm"]:
        # Product-code trials ("GT802 Injection") often name CAR-T only in
        # their kinetics outcomes ("Cmax of circulating CAR-T cells").
        return "product", "rule: CAR-T kinetics are an outcome measure"

    if any(hit.values()):
        return "related", "rule: CAR-T mentioned, not an intervention"
    return "unrelated", "rule: CAR-T only in eligibility or not at all"


def load_overrides(path: str = OVERRIDES_CSV) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8", newline="") as f:
        rows = {r["trial_id"]: (r["scope"], r.get("note", ""))
                for r in csv.DictReader(f)}
    bad = {v[0] for v in rows.values()} - set(SCOPES)
    if bad:
        raise ValueError(f"Unknown scope in {path}: {sorted(bad)}")
    return rows


def classify(study: dict, overrides: dict):
    """Return (scope, basis). A hand-made decision beats the rules."""
    nct = study.get("protocolSection", {}).get(
        "identificationModule", {}).get("nctId", "")
    if nct in overrides:
        scope, note = overrides[nct]
        return scope, "manual: " + note if note else "manual"
    return classify_by_rule(study)
