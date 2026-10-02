# CAR-T Clinical Trials & Treatment Analysis Pipeline

[![Monthly Data Update](https://github.com/CARTBridgeHealth/CAR-T-Clinical-Trials-Analysis/actions/workflows/monthly_update.yml/badge.svg)](https://github.com/CARTBridgeHealth/CAR-T-Clinical-Trials-Analysis/actions/workflows/monthly_update.yml)
[![Deploy to Pages](https://github.com/CARTBridgeHealth/CAR-T-Clinical-Trials-Analysis/actions/workflows/static.yml/badge.svg)](https://github.com/CARTBridgeHealth/CAR-T-Clinical-Trials-Analysis/actions/workflows/static.yml)

An end-to-end data pipeline analyzing **2,944 real-world CAR-T clinical trials** and **global treatment availability** across 7 countries — combining SQL database design, Python data engineering, Power BI visualization, and interactive web publishing. Data is refreshed automatically every month via GitHub Actions.

---

## 🌐 Live Websites

| | Site | Description |
|---|---|---|
| 📊 | [Data Analysis](https://cartbridgehealth.github.io/CAR-T-Clinical-Trials-Analysis/) | Interactive clinical trial charts — growth trends, country breakdown, phase analysis |
| 💼 | [Investor Presentation](https://cartbridgehealth.github.io/CAR-T-Clinical-Trials-Analysis/investor.html) | Full business case — problem, service model, product strategy, data, team · Bilingual EN/CN · Mobile responsive |
| 🏥 | [Patient Guide](https://cartbridgehealth.github.io/CAR-T-Clinical-Trials-Analysis/patient_guide.html) | One-page product guides for all 5 Priority 1–3 CAR-T products · Bilingual EN/CN · Mobile responsive |

---

## 🔄 Automated Monthly Updates

GitHub Actions runs on the **1st of every month** and automatically:

1. Fetches the latest CAR-T trials from ClinicalTrials.gov API
2. Standardizes phase labels and cleans the dataset
3. Updates treatment cost and approved product comparison data
4. Commits and pushes updated CSV files to this repository
5. Regenerates `data/site_stats.json`, which the websites read on load
6. GitHub Pages websites refresh automatically

No manual steps required.

---

## Key Findings

### Clinical Trials · 2,944 records · October 2026

- CAR-T trial starts grew from 5 in 2010 to **430 in 2025**
- **China leads globally** with 1,441 trials; USA follows with 930
- Phase 1 trials dominate (1,134 trials) — field still largely pre-commercial
- **34% of trials actively recruiting** — rapid expansion continuing

> Counts come from `data/site_stats.json`, regenerated on every monthly refresh.
> 204 trials (7%) list no country, so country counts are a lower bound.

### Global Treatment Comparison · July 2026

| Country | All-In Cost | Wait Time | Approved Products |
|---|---|---|---|
| 🇨🇳 China | **$50K–$80K** | **2–3 weeks** | **9 (most globally)** |
| 🇺🇸 USA | $488K–$760K | 8–12 weeks | 7 |
| 🇨🇦 Canada | $250K–$350K | 16–20 weeks | 4 |
| 🇩🇪 Germany | $320K–$360K | 8 weeks | 6 |

🚨 **June 22, 2026**: China approved **Satri-cel / 恺力美®** — the world's first CAR-T therapy for solid tumors (gastric cancer). Not yet available in the USA, Canada, or Europe.

---

## CAR-T Product Strategy

Five products organized into four priority tiers for patient coordination:

| Priority | Product | Target | Indication | China Price | ORR |
|---|---|---|---|---|---|
| 🟢 P1 | 奕凯达® (Yescarta) | CD19 | B-cell Lymphoma, FL, MCL | ¥1.2M (~$165K) | 83% |
| 🟢 P1 | 倍诺达® (Relma-cel) | CD19 | DLBCL, MCL post-BTKi | ¥1.29M (~$177K) | 80% |
| 🟡 P2 | 卡卫荻® (Carvykti) | BCMA | Multiple Myeloma (3L+) | ¥1.15M (~$158K) | 98% |
| 🟡 P2 | 福可苏® (Fucaso) | BCMA | Multiple Myeloma (3L+) | ¥1.17M (~$160K) | 96% |
| 🔴 P3 | 恺力美® (Satri-cel) | CLDN18.2 | Gastric/GEJ Cancer 🌍 World First | TBD | — |
| ⚪ P4 | FDA products (USA) | — | Pediatric ALL, CLL, special cases | $373K–$475K | — |

→ Full bilingual patient guide: [patient_guide.html](https://cartbridgehealth.github.io/CAR-T-Clinical-Trials-Analysis/patient_guide.html)

---

## Tech Stack

| Layer | Tools |
|---|---|
| Database | PostgreSQL (5-table normalized schema) |
| SQL | Joins, aggregations, window functions, ETL pipeline |
| Data pipeline | Python, Pandas, Requests (ClinicalTrials.gov API v2) |
| Visualization | Power BI Desktop (2-page dashboard) |
| Web | HTML, CSS, Chart.js — interactive, bilingual, mobile-responsive |
| Automation | GitHub Actions (monthly cron schedule) |
| Version control | Git / GitHub |

---

## Project Structure

```
CAR-T-Clinical-Trials-Analysis/
│
├── .github/workflows/
│   ├── static.yml                    # Auto-deploy to GitHub Pages on push
│   └── monthly_update.yml            # Monthly data refresh — runs 1st of each month
│
├── data/
│   ├── cart_trials_raw.json          # Raw API response (2,944 records)
│   ├── cart_trials_clean.csv         # Cleaned, flattened dataset — auto-updated
│   ├── approved_products.csv         # FDA & NMPA approved products (2026)
│   ├── cost_comparison.csv           # Treatment costs by country (2026)
│   └── treatment_centers.csv         # Top CAR-T hospitals worldwide
│
├── sql/
│   └── queries.sql                   # 6 analysis queries (joins, aggregations, window functions)
│
├── python/
│   ├── fetch_cart_data.py            # Pull from ClinicalTrials.gov API
│   ├── generate_mock_data.py         # 500-record mock dataset for local dev
│   ├── fix_phase_labels.py           # Standardize phase label formats
│   ├── collect_treatment_data.py     # Build treatment comparison datasets
│   └── update_treatment_data_2026.py # Refresh with latest 2026 data
│
├── dashboard/
│   └── cart_trials_dashboard.pbix    # Power BI — 2 pages (trials + treatment comparison)
│
├── index.html                        # Data analysis site (Chart.js interactive charts)
├── investor.html                     # Investor presentation — bilingual EN/CN, mobile-responsive
│                                     #   Sections: problem · service · products · data · team · contact
├── patient_guide.html                # Patient education — bilingual EN/CN, mobile-responsive
│                                     #   Products: 奕凯达® · 倍诺达® · 卡卫荻® · 福可苏® · 恺力美®
└── README.md
```

---

## SQL Analysis Queries

| # | Query | Technique | Key Finding |
|---|---|---|---|
| 1 | Trial growth by year | GROUP BY, SUM | 20× growth 2010–2025 |
| 2 | Trials by cancer type | JOIN, AVG | B-cell malignancies most studied |
| 3 | Completion rate by phase | CASE WHEN, percentage | Phase 2 highest completion (34%) |
| 4 | Geographic distribution | JOIN, COUNT DISTINCT | China #1, USA #2 |
| 5 | CAR-T product analysis | JOIN, ORDER BY | 14 major products compared |
| 6 | Pediatric vs adult | Window function, PARTITION BY | Phase 3 highest avg enrollment |

---

## How to Run Locally

```bash
# 1. Install dependencies
pip install requests pandas

# 2. Fetch real data from ClinicalTrials.gov
python python/fetch_cart_data.py
python python/fix_phase_labels.py

# 3. Update treatment comparison data
python python/update_treatment_data_2026.py

# 4. Set up PostgreSQL database
psql -U postgres -c "CREATE DATABASE cart_trials;"
psql -U postgres -d cart_trials -f sql/queries.sql

# 5. Trigger monthly update manually (GitHub)
# Actions → Monthly CAR-T Data Update → Run workflow
```

---

## Data Sources

| Source | Data | URL |
|---|---|---|
| ClinicalTrials.gov | 2,944 trial records (auto-updated monthly) | clinicaltrials.gov |
| U.S. FDA | Approved CAR-T products | fda.gov |
| China NMPA | Approved CAR-T products | nmpa.gov.cn |
| Medical literature | Treatment costs, outcomes | Published 2024–2026 |
| CARsgen | Satri-cel / 恺力美® approval | Press release, June 22, 2026 |

---

## Business Application

This project underpins **CARTBridge Health** — a cross-border CAR-T medical coordination service connecting North American cancer patients with top treatment centers in China, and Chinese patients seeking FDA-approved therapies in North America.

> *"China now has more approved CAR-T products than any other country, at one-seventh the cost, with one-sixth the wait time."*

| Resource | Link |
|---|---|
| 💼 Investor Presentation | [investor.html](https://cartbridgehealth.github.io/CAR-T-Clinical-Trials-Analysis/investor.html) |
| 🏥 Patient Guide | [patient_guide.html](https://cartbridgehealth.github.io/CAR-T-Clinical-Trials-Analysis/patient_guide.html) |

---

## Author

**Yang Liu** · Research Associate, University of Manitoba

Biomedical researcher with expertise in microfluidics, point-of-care diagnostics, and data analysis. Bridging clinical research with data engineering and cross-border healthcare access.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-yang--liu--6093-blue?logo=linkedin)](https://www.linkedin.com/in/yang-liu-6093/)
[![GitHub](https://img.shields.io/badge/GitHub-CARTBridgeHealth-black?logo=github)](https://github.com/CARTBridgeHealth)
📧 liuyang6093@gmail.com · 📞 +1 (431) 554-0238
