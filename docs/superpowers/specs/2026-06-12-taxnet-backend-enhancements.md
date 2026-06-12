# TaxNet Backend Enhancements — Design Spec

**Date:** 2026-06-12  
**Scope:** Items 1–4 from the post-exploration gap list. ML model generalization (item 5) and macro-data integration (item 6) are explicitly out of scope.  
**Goal:** Improve the hackathon demo by wiring OpenSanctions, aligning income with asset events, adding a live `cust-csv/` demo, and expanding district-level NIC features.

---

## 1. OpenSanctions Watchlist Screening

### Purpose
Make the prototype screen resolved taxpayers/entities against the locally-available OpenSanctions dataset and surface any hits as an interpretable risk signal.

### Data
`data/open-sanctions/targets.simple.csv` (~458 MB). Header columns: `id`, `schema`, `name`, `aliases`, `birth_date`, `countries`, `addresses`, `identifiers`, `sanctions`, `phones`, `emails`, `program_ids`, `dataset`, `first_seen`, `last_seen`, `last_change`.

### Design
1. **Loader** — `taxnet/loaders/open_sanctions_loader.py`
   - Use Polars (already a dependency) to stream/read the CSV.
   - Normalize each target: canonical name, list of aliases, country codes, entity type/schema.
   - Return an in-memory list/dict of sanitized targets.
2. **Matching** — `taxnet/watchlist_screening.py`
   - After entity resolution, iterate over resolved entity clusters.
   - For each cluster, compare the canonical name (and optionally aliases from member records) against every OpenSanctions target name/alias.
   - Use the existing `taxnet/normalization.py` helpers plus token/Jaccard similarity (or rapidfuzz if available; fallback to existing functions).
   - A match is flagged when similarity >= `OPEN_SANCTIONS_MATCH_THRESHOLD` (default 0.85).
   - Preserve the best-scoring match per entity.
3. **Graph integration**
   - Add a `SanctionedMatch` edge or node attribute linking the resolved entity to the matched target ID.
   - Gracefully degrade if the OpenSanctions file is missing.
4. **Scoring**
   - In `taxnet/scoring.py`, add a rule-based watchlist boost.
   - Any flagged entity receives a fixed raw-score increment (e.g., +0.3) capped at the tier boundary.
   - Explanation: *"Name closely matches sanctioned entity '<target_name>' (similarity X.Y)."*
5. **API**
   - Extend `/api/profile/<entity_id>` to include `watchlist_matches`.
   - Optionally add `/api/screen` to run screening on demand.

### Alternatives considered
- **Exact matching only** — rejected: too brittle for transliterated Pakistani names.
- **Multi-field matching** (address, DOB, country) — deferred: higher precision but requires more normalization and is not critical for the first pass.

---

## 2. Income–Event Alignment

### Purpose
Detect asset acquisitions or lifestyle events that are inconsistent with the income declared on tax returns.

### Data
- `TaxReturn` records: `tax_year`, `declared_income`.
- `Property` records: `transaction_date`, `value`.
- `Vehicle` records: `registration_date`, `value` (or inferred value).
- `Utility` records: `billing_date`, `amount` (treated as lifestyle proxy where relevant).

### Design
1. **Module** — `taxnet/income_event_alignment.py`
   - `align_income_and_events(entity_records)` returns a dict of per-entity metrics.
2. **Metrics**
   - `max_asset_to_income_ratio`: max total asset value in any tax year / declared income for that year.
   - `unreported_asset_years`: count of years with asset value > 0 but no tax return.
   - `asset_burst_count`: number of 90/180/365-day windows with >= N high-value acquisitions.
   - `total_unexplained_value`: sum of asset values in years where declared income is zero or missing.
3. **Integration**
   - Add the metrics to `taxnet/features.py` under clear column names.
   - In `taxnet/scoring.py`, add a rule component for income-event misalignment.
   - Explanation: *"Acquired assets worth PKR X in 20YY but declared income was PKR Y."*
4. **Edge cases**
   - Missing income or missing asset value → metric is 0 or NaN; scoring ignores it.
   - Multiple tax returns for the same year → sum income.

### Alternatives considered
- **Time-series forecasting** — rejected as overkill for a prototype.
- **Sliding-window-only rules** — partially included via `asset_burst_count`; can be expanded later.

---

## 3. Live `cust-csv/` Demo

### Purpose
Show the system working on the real Pakistan-shaped CSVs already in `data/cust-csv/` instead of only on freshly-generated synthetic data.

### Design
1. **Script** — `scripts/demo_cust_csv.py`
   - Discover CSVs in `data/cust-csv/`.
   - Call `taxnet.pipeline.run_pipeline(input_dir, ...)`.
   - Write `demo_cust_csv_report.json` using the same schema as `demo_backend_report.json`.
   - Print a short summary to stdout.
   - Optionally start the web server (`python run.py`) so the user can browse results.
2. **Documentation**
   - Add the command to `README.md`.
3. **Test**
   - Add `tests/test_demo_cust_csv.py` that runs the script with a minimal fixture and asserts the report is created and valid JSON.

### Alternatives considered
- **Extend `demo_backend.py`** — rejected because that script explicitly generates synthetic data; mixing concerns would confuse users.
- **Jupyter notebook** — rejected because it is harder to run and test in this repo.

---

## 4. District-Level Risk Features

### Purpose
Expand NIC/CNIC prefix geocoding to cover more districts and add simple district-level risk features.

### Design
1. **Extend `taxnet/nic_geocode.py`**
   - Add a comprehensive CNIC prefix → district/province mapping.
   - Add `extract_prefix(cnic: str) -> str` helper.
   - Add `lookup_district(cnic: str) -> dict` returning province and district.
2. **Features in `taxnet/features.py`**
   - `province_onehot`: one-hot encoded province.
   - `district_risk_score`: a small integer score (0–3) based on a static lookup of districts flagged as higher-risk in public reporting/FBR patterns.
   - `district_known`: binary flag for whether the prefix is in the mapping.
3. **Scoring explanations**
   - *"CNIC prefix indicates district X, which has elevated reported risk."*
4. **Data source**
   - Use a hand-curated static table checked into the repo.
   - No external macro data (out of scope per user request).

### Alternatives considered
- **External district-level economic indicators** — rejected because macro-data integration is out of scope.
- **Learned district risk** — rejected because it requires server-side ML retraining.

---

## Common Implementation Notes

- Each new module receives focused unit tests.
- Existing tests must continue to pass.
- No ML model training is performed in this scope.
- New features feed into `taxnet/scoring.py` explanations so they appear in the web dashboard.
- Code must follow the existing style (ruff formatting) and use existing normalization utilities where possible.

## Acceptance Criteria

- [ ] `scripts/demo_cust_csv.py` runs end-to-end on `data/cust-csv/` and produces a valid report.
- [ ] OpenSanctions screening flags at least one test fixture with a synthetic sanctioned name match.
- [ ] Income-event alignment features are computed for entities with both tax and asset records.
- [ ] District features are computed for CNIC prefixes in the expanded mapping.
- [ ] All existing tests pass; new tests are added for each enhancement.
