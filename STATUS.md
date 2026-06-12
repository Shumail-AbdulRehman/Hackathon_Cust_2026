# TaxNet XAI — Implementation Status & Data Audit

Last updated: 2026-06-12 (server pipeline + backend features sprint complete)

---

## 1. Implemented

| Area | Status | Details |
|------|--------|---------|
| Python packaging | ✅ Done | `pyproject.toml` + `uv` + editable install; tests discoverable via `uv run pytest tests -q` |
| Synthetic data generator | ✅ Done | Seeded generation of FBR, property, vehicle, utility records |
| Data ingestion | ✅ Done | CSV/Excel upload path, column mapping, schema profiling |
| Normalization | ✅ Done | Phone, CNIC/NTN, name, address normalization; Pakistan formats prioritized |
| Entity resolution | ✅ Done | Blocking (phone, city+surname, address, initials), fuzzy pairwise scoring, union-find clustering; parallel `ProcessPoolExecutor` fast path; exact-match shortcuts for `national_id` / `phone`; optional ANN blocking via BlockingPy + FAISS-HNSW |
| ANN blocking | ✅ Done | `taxnet/ann_blocking.py` — optional BlockingPy/FAISS-HNSW shingle encoder for large-scale name/address blocking; falls back to traditional blocking if unavailable |
| NIC geocoding | ✅ Done | `taxnet/nic_geocode.py` — CNIC/NIC prefix → province/district; one-hot province flags in features |
| Benford's Law analysis | ✅ Done | `taxnet/benford.py` — first-digit MAD per numeric column; feeds rule + ML features |
| Living-Luxury-Income (LLI) metric | ✅ Done | `taxnet/features.py` + `taxnet/scoring.py` — headline `lli_ratio` and `lli_score` |
| Temporal graph analysis | ✅ Done | `taxnet/temporal_analysis.py` — asset-burst detection, peak asset year, event timelines |
| In-memory graph | ✅ Done | Property graph with Person, Vehicle, Property, Meter, TaxReturn nodes and ownership / shared-attribute edges |
| FalkorDB integration | ✅ Done | Container setup script, graph loader, PageRank, communities, degrees, shortest path; graceful fallback if unavailable |
| Feature engineering | ✅ Done | `taxnet/features.py` — graph + tabular features |
| ML scoring | ✅ Done | XGBoost regressor (CPU), trained on synthetic labels, 5-tier risk classification |
| XAI / SHAP | ✅ Done | Per-entity feature attributions returned in every score profile |
| Scoring blend | ✅ Done | Rule-based score + ML score blend; final score, tier, SHAP explanation |
| HTTP API | ✅ Done | `/api/health`, `/api/demo`, `/api/benchmark`, `/api/profile`, `/api/run` |
| Demo / Benchmark scripts | ✅ Done | `scripts/demo_backend.py`, `scripts/benchmark_suite.py`, `scripts/demo_icij.py` |
| ICIJ Offshore Leaks loader | ✅ Done | `taxnet/loaders/icij_loader.py` with Polars-based sampling |
| Tests | ✅ Done | 92 passing (`tests/test_*.py`) |

### Performance snapshot

- 500-citizen benchmark: ~20.8 s total, ~67 records/s on a typical laptop.
- Entity resolution is the dominant cost; blocking + parallelism keeps it sub-quadratic.

---

## 2. On Hold (preserved in repo, not wired in)

| Area | Status | Reason |
|------|--------|--------|
| GNN anomaly detection | ⏸️ On hold | User chose ML + SLM for the server run; GNN may be added later if time permits |
| UI/UX redesign | ⏸️ On hold | User will use the `impeccable` skill later; backend-only changes for now |

## 2.5 Server-side Model Training Pipeline (in progress)

A three-file server pipeline is being implemented to train models on real data and export CPU-runnable artifacts.

| File | Purpose | Outputs |
|------|---------|---------|
| `file1.py` | Download Pakistan tax laws + build a vectorless RAG index | `server_artifacts/law_rag/law_index.faiss`, `law_chunks.jsonl`, `law_metadata.jsonl` |
| `file2.py` | Download ICIJ/OpenSanctions/UK/Elliptic/IBM datasets, build entity graph, train XGBoost ML model | `server_artifacts/ml/ml_model.json`, `feature_columns.json`, `entity_profiles.jsonl`, `training_report.json` |
| `file3.py` | Download Qwen + SmolLM2-135M, generate SLM training data from entity profiles, fine-tune, export GGUF | `server_artifacts/slm/gguf/*.gguf` |

All three files are idempotent, lint-clean, and use `server_utils.py` for resume/retry-safe downloads and checkpoints. `file2.py` now runs OpenSanctions watchlist screening after entity resolution and stores matches in `entity_profiles.jsonl`.

## 2.6 Backend Features 1–4 (in progress)

These gaps from the original audit are being implemented in parallel with the server pipeline:

| # | Feature | Status | Notes |
|---|---------|--------|-------|
| 1 | OpenSanctions loader / watchlist screening | ✅ Done | Loader in `taxnet/loaders/open_sanctions_loader.py`; screening integrated into `file2.py` for server; local scoring deferred to avoid 458 MB load |
| 2 | Income–event alignment | ✅ Done | `taxnet/income_event_alignment.py` + features + scoring explanations |
| 3 | Direct `cust-csv/` demo | ✅ Done | `scripts/demo_cust_csv.py` runs local Pakistan CSVs end-to-end |
| 4 | District-level risk features | ✅ Done | Expanded `taxnet/nic_geocode.py` district mapping + `district_risk_score` feature |
| 5 | CNIC/NTN vs phone scoring weight | ✅ Done | `SHARES_NATIONAL_ID_WITH` edges weighted 1.6× vs 0.6× for phone sharing |

---

## 3. Not Implemented

These were discussed but are **not currently in the codebase** and remain out of scope for the current sprint.

| Area | Priority | Notes |
|------|----------|-------|
| Dataset-level Benford dashboard | Medium | Aggregate first-digit deviation across whole datasets, not just per entity |
| Airflow / proper data-engineering pipeline | Low-Medium | Overkill for a 48-hour demo; SQLite-backed ingestion is sufficient for now |
| PCA / dimensionality reduction | Low | Not needed for current feature set; XGBoost handles redundancy |
| Real public datasets | High | Searched; no individual-level Pakistan tax/property/vehicle data was found. Macro data exists (see audit below) |

**Moved to in-progress:** income-event alignment, district-level risk features, OpenSanctions watchlist screening, and ML retraining on real data are now covered by §2.5 and §2.6 above.

---

## 4. Dataset Audit

A quick header/row sample of every file under `data/` was generated with `scripts/sample_data.py`. Full raw output is at [`docs/data_sample_report.txt`](docs/data_sample_report.txt).

### 4.1 `cust-csv/` — ✅ Usable

| File | Type | Usability |
|------|------|-----------|
| `fbr_tax_records_complex.csv` | CSV | Directly usable. Columns: `fbr_id`, `full_name`, `declared_income_pkr`, `tax_paid_pkr`, `filer_status`, `reported_address`, `phone_number`, `ntn`, `source_note` |
| `property_transfers_complex.csv` | CSV | Directly usable. Columns: `registry_no`, `buyer_name`, `seller_name`, `property_address`, `property_value_pkr`, `transfer_date`, `area_marla`, `property_type`, `buyer_phone`, `source_note` |
| `excise_vehicles_complex.csv` | CSV | Directly usable. Columns: `vehicle_reg_no`, `owner_name`, `engine_capacity_cc`, `vehicle_make_model`, `registration_year`, `owner_address`, `owner_phone`, `chassis_no`, `source_note` |
| `disco_consumption_complex.csv` | CSV | Directly usable. Columns: `meter_ref_no`, `consumer_name`, `installation_address`, `avg_monthly_bill_pkr`, `connection_type`, `phone_number`, `division`, `source_note` |
| `README.md` | Doc | Context notes for the synthetic test set |

These four CSVs are the only Pakistan synthetic files that contain **entity-level** names, addresses, phones, and asset/income signals. They map cleanly to the existing pipeline.

### 4.2 `icij-offshore-leaks/` — ✅ Real global tax-evasion graph

| File | Type | Notes |
|------|------|-------|
| `nodes-addresses.csv` | Entity-level | 70 MB — addresses linked to offshore entities/officers |
| `nodes-entities.csv` | Entity-level | 190 MB — offshore companies, trusts, foundations |
| `nodes-intermediaries.csv` | Entity-level | 3.8 MB — law firms, agents, middlemen |
| `nodes-officers.csv` | Entity-level | 87 MB — beneficial owners, directors, shareholders |
| `nodes-others.csv` | Entity-level | 390 KB — miscellaneous nodes |
| `relationships.csv` | Entity-level | 248 MB — edges linking all node types |

**Verdict:** Real, global, graph-shaped tax-evasion / hidden-asset data. Perfect for entity resolution, graph analytics, and risk scoring. Use as the primary real-world benchmark. The full dataset (~600 MB CSV) is present locally.

**Integration status:** Loader implemented in `taxnet/loaders/icij_loader.py`, runs through the full pipeline, and exposes a demo script.

### 4.3 `open-sanctions/` — ✅ Real global watchlist graph

| File | Type | Notes |
|------|------|-------|
| `targets.simple.csv` | Entity-level | 458 MB — ~1.3M sanctioned/PEP/crime targets with identifiers, aliases, addresses, countries, relationships |

**Verdict:** Large real-world graph of high-risk individuals and entities. Excellent for watchlist screening and as a second real benchmark. The full dataset is present locally.

### 4.4 `energy-mining-data/` — ❌ Not entity-level

| File | Type | Notes |
|------|------|-------|
| `Mineral-Production-Data-*.pdf/xlsx` | Macro | Province × mineral × month production volumes (MT) |
| `detail-tables-*.xlsx/pdf` | Macro | Electricity generation (GWh) by establishment/fuel |

**Verdict:** Aggregate production statistics. No individual identifiers. Could support a macro "tax gap vs. sector output" narrative, but cannot drive entity resolution or individual risk scoring without heavy extraction and entity attribution.

### 4.5 `export-data/` — ❌ Not entity-level

| File | Type | Notes |
|------|------|-------|
| `D-10_Export/Import-*.pdf` | Macro | HS-code × country import/export values (thousands of PKR) |
| `*_imp/exp_*.pdf/txt` | Macro | Commodity/country trade tables by fiscal year |
| `Table-2-2009-10-Base-2005-06.pdf` | Macro | Large-scale manufacturing production index |
| `Final_POL_Data_2014-15_to_2016-17.pdf` | Macro | Petroleum product data |

**Verdict:** National trade and manufacturing statistics. No company-level identifiers. Useful for macro context (e.g., under-invoicing detection at country level), not for the individual taxpayer graph.

### 4.6 `hise-data/` — ❌ Aggregate household survey

| File | Type | Notes |
|------|------|-------|
| `TABLE_02-1.xlsx`, `TABLE_03-1.xlsx`, `TABLE_04-1.xlsx`, `TABLE_22.xlsx` | Aggregate | Employment, industry, occupation, consumption expenditure tables |
| `TABLE_*.xls` | Aggregate | Same, but require `xlrd` (not installed) to read |

**Verdict:** Pakistan Bureau of Statistics household survey tables. All percentages/aggregates; no individual records. The `.xls` files are currently unreadable without adding `xlrd` to dependencies.

### 4.7 `labor-data/` — ❌ Aggregate labor force survey

| File | Type | Notes |
|------|------|-------|
| `Report-1.pdf` … `Report-15.pdf` | Aggregate | Population, labor force, migration, education, employment status tables (2024-25) |

**Verdict:** Aggregate demographic/labor statistics. No individual records or identifiers. Useful only as background context.

### 4.8 `pakistani-tax-data/` — ⚠️ Macro indicators only

| File | Type | Notes |
|------|------|-------|
| `API_PAK_*/` | Macro | World Bank tax-to-GDP, GDP, population CSVs for Pakistan |
| `UNUWIDERGRD_2025_Central.xlsx` | Macro | Government revenue dataset (central government, many countries, includes Pakistan rows) |
| `UNUWIDERGRD_2025_Full.xlsx` | Macro | Same, full documentation sheet |
| `*.xlsx.part` | Junk | Incomplete download remnant — safe to delete |

**Verdict:** Country-level fiscal indicators. Excellent for framing Pakistan's tax-gap narrative, but cannot be linked to individual taxpayers. Can be used in the pitch as macro motivation.

---

## 5. Current 48-Hour Sprint Plan

### 5.1 Server-side model training (priority)

1. Run `file1.py` on the A500 server to download Pakistan tax laws and build the vectorless RAG index.
2. Run `file2.py` on the server to train the XGBoost ML model on ICIJ + OpenSanctions + sampled UK/Elliptic/IBM data.
3. Run `file3.py` on the server to fine-tune SmolLM2-135M on entity-profile audit narratives and export a GGUF.
4. SCP `server_artifacts/` back to the local machine for CPU inference.

### 5.2 Backend features 1–4 (parallel)

1. **OpenSanctions loader** — finish `taxnet/loaders/open_sanctions_loader.py` and wire watchlist matches into scoring.
2. **Income–event alignment** — add `taxnet/income_event_alignment.py` + features + scoring explanations.
3. **`cust-csv/` demo** — add `scripts/demo_cust_csv.py` and README instructions.
4. **District-level risk features** — expand `taxnet/nic_geocode.py` mapping and add district risk score.

### 5.3 Demo / pitch polish

- Show the `cust-csv/` dataset running through the live pipeline (not just synthetic data).
- Highlight the macro tax-to-GDP context from `tax-data/` to justify the problem.
- Keep the UI on hold until the `impeccable` redesign.
- GNN remains on hold unless ML + SLM finish early.

---

## 6. Real-world datasets to consider (non-Pakistani)

Pakistan does not publish individual-level tax, property, or asset registers. The `cust-csv/` files are small and synthetic, so the ML model is at risk of overfitting. Below are publicly available, real, non-Pakistani datasets that map directly to the TaxNet XAI pipeline. Using one of them as a "global benchmark" also strengthens the "Pakistan-first but globally mappable" pitch.

### 6.1 ICIJ Offshore Leaks Database — **top recommendation**

- **What:** 810,000+ offshore entities from Panama Papers, Paradise Papers, Pandora Papers, Bahamas Leaks, and Offshore Leaks.
- **Why it fits:** Real-world tax-evasion / hidden-asset graph with persons, companies, addresses, officers, intermediaries, and relationships. Exactly the entity-resolution + graph-analytics + risk-scoring problem TaxNet solves.
- **Size:** ~73 MB ZIP (`full-oldb.LATEST.zip`).
- **License:** Open Database License / CC-BY-SA. Cite ICIJ.
- **Download:** `https://offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip`
- **Format:** CSVs: `nodes-*.csv` (Entity, Officer, Intermediary, Address, Other) + `relationships.csv`.
- **Notes:** The dataset is intentionally de-duplicated and includes name/address variations, making it a strong test for our entity-resolution blocking + fuzzy matching. **Full CSVs already present in `data/icij-offshore-leaks/`.**

### 6.2 OpenSanctions

- **What:** 4.9M+ entities combining sanctions lists, PEP registries, crime/wanted lists, and debarment registers.
- **Why it fits:** Pre-built graph of high-risk individuals and companies with addresses, identifiers, aliases, and relationships.
- **Size:** `targets.simple.csv` is ~300 MB; full `statements.csv` is ~13 GB.
- **License:** Free for non-commercial use; commercial use requires a license.
- **Download:** `https://data.opensanctions.org/datasets/latest/default/targets.simple.csv`
- **Notes:** Great for a "screen against global watchlists" feature, but less about tax evasion specifically. **`targets.simple.csv` already present in `data/open-sanctions/`.**

### 6.3 UK Companies House

- **What:** Official UK register of ~5 million companies, officers, and Persons with Significant Control (PSC).
- **Why it fits:** Real beneficial-ownership graph; publicly available; includes company → officer / shareholder links and registered addresses.
- **License:** UK Open Government Licence.
- **Download:**
  - Basic company data snapshot (~5 GB): `https://download.companieshouse.gov.uk/BasicCompanyDataAsOneFile-2026-06-01.zip`
  - PSC snapshot: `https://download.companieshouse.gov.uk/persons-with-significant-control-snapshot-2026-06-12.zip`
- **Notes:** Large, clean, and authoritative. The PSC data is a free bulk JSON snapshot. Best for demonstrating scale and real-world entity linking. **Too large to use whole locally — shard/sample (see §8).**

### 6.4 Open Ownership Register

- **What:** Consolidated beneficial-ownership data from multiple countries.
- **Why it fits:** Directly models person/company ownership/control relationships.
- **License:** Open Ownership terms / source-dependent.
- **Download:** `https://oo-bodsdata.s3.amazonaws.com/data/gleif_version_0_4/csv.zip`
- **Notes:** Focused specifically on beneficial ownership.

### 6.5 Elliptic++ Data Set (Bitcoin AML)

- **What:** Bitcoin transaction graph with illicit/licit labels (enhanced Elliptic dataset).
- **Why it fits:** Graph-based financial fraud detection benchmark; useful if you re-enable the GNN module.
- **License:** Academic / research use.
- **Access:** `https://github.com/git-disl/EllipticPlusPlus`
- **Notes:** Not tax fraud, but transaction-graph anomaly detection is directly transferable.

### 6.6 IBM / Kaggle AML Transaction Data

- **What:** Synthetic financial transactions for anti-money-laundering (HI/LI variants, small/medium/large).
- **Why it fits:** Large labeled transaction graph; good for benchmarking GNNs.
- **License:** Kaggle dataset terms.
- **Download:**
  ```bash
  curl -L -o ~/Downloads/ibm-transactions-for-anti-money-laundering-aml.zip \
    https://www.kaggle.com/api/v1/datasets/download/ealtman2019/ibm-transactions-for-anti-money-laundering-aml
  ```
- **Notes:** Synthetic, ~8 GB. Too large to use whole locally — shard/sample (see §8).

---

## 7. Exact commands used for verification

```bash
# One-time setup
uv sync --extra dev
uv pip install -e .
uv run python scripts/setup_falkordb.py

# Test suite (92 tests)
uv run pytest tests -q

# End-to-end demo (synthetic Pakistan data)
uv run python scripts/demo_backend.py

# Pakistan-shaped CSV demo
uv run python scripts/demo_cust_csv.py --no-server

# ICIJ Offshore Leaks demo (real global tax-evasion data)
# This demo uses ANN blocking and disables ML because the model is trained only on synthetic Pakistan data.
uv run python scripts/demo_icij.py --max-entities 1000 --seed 42

# ICIJ demo with traditional blocking instead of ANN blocking
uv run python scripts/demo_icij.py --max-entities 1000 --seed 42 --no-ann

# Scalability benchmark
uv run python run.py --benchmark --citizens 500 --seed 42

# Re-generate this dataset audit
uv run python scripts/sample_data.py > docs/data_sample_report.txt
```

**Dependency note:** `xgboost-cpu` is pinned to `<3.0` because XGBoost 3.x encodes `base_score` in a way that SHAP 0.49 cannot parse. The pin is in `pyproject.toml`.

---

## 8. Strategy for large datasets, SLM, and GNN

You already have the two most important real datasets locally: **ICIJ Offshore Leaks** (~600 MB CSV) and **OpenSanctions** (~458 MB CSV). The others (UK Companies House ~5 GB, IBM AML ~8 GB) are too large for fast local iteration and would take days to train on even with the A500. Below is a practical split.

### 8.1 Use fully (no sharding needed)

| Dataset | Size | Use case |
|---|---|---|
| ICIJ Offshore Leaks | ~600 MB | Main real-world benchmark for entity resolution + graph scoring |
| OpenSanctions | ~458 MB | Watchlist screening + second benchmark |
| Elliptic++ | < 1 GB | GNN benchmark / transaction-graph anomaly detection |
| Pakistan Tax Act / tax law book | varies | SLM fine-tuning / RAG corpus for audit narrative |

### 8.2 Shard / sample for local development

| Dataset | Size | Sampling strategy |
|---|---|---|
| UK Companies House basic | ~5 GB | Sample by company status (active only), by SIC sector, or random 5–10% sample; use PSC snapshot as the relationship backbone |
| IBM AML | ~8 GB | Take one variant (e.g., `LI-Small_Trans` if available), or randomly sample accounts/transactions while preserving fraud-class balance |
| OpenSanctions statements | ~13 GB | Use `targets.simple.csv` (already local, 458 MB) instead of the full statements file |

**Practical sampling rules:**
1. **Preserve connected components** — when sampling a graph, keep whole components or ego networks so relationships remain meaningful.
2. **Preserve rare classes** — keep all positive (fraud/sanctioned/offshore) labels and down-sample negatives.
3. **Seed everything** — every sample command should take `--seed` so the demo is reproducible across laptops.
4. **Cache samples** — write sampled subsets to `data/samples/` so you do not re-process 8 GB on every run.

### 8.3 SLM (small LLM) plan

When the SLM comes off hold, the best training corpus is:
- **Pakistan Tax Act / tax law book** — domain knowledge for audit narrative.
- **ICIJ + OpenSanctions relationship descriptions** — examples of how to describe risky networks in natural language.
- **SHAP explanations from the current pipeline** — paired "feature attribution → narrative" examples.

A 7–8B parameter model (Qwen2.5-7B, Llama-3.1-8B, or Mistral-7B) fits comfortably on the A500 48 GB. Use LoRA/QLoRA for fast fine-tuning, or simple distillation if you have a larger teacher model available via API credits.

### 8.4 GNN plan

When the GNN comes off hold:
- **ICIJ Offshore Leaks** is the ideal heterogeneous graph: nodes = Entity, Officer, Intermediary, Address; edges = `relationships.csv`.
- **Elliptic++** is the ideal transaction-graph benchmark for binary classification.
- **OpenSanctions** can be used as a multi-relational graph for link-prediction / node-classification pre-training.

A PyTorch Geometric or DGL model trained on the A500 can handle the full ICIJ graph in memory. For UK Companies House or IBM AML, sample first.

### 8.5 Recommended next step

**Do not download the 5 GB / 8 GB files on your slow connection right now.** Instead:
1. Write a loader for the **ICIJ Offshore Leaks** CSVs that already sit in `data/icij-offshore-leaks/`.
2. Run the TaxNet pipeline on a 10K–100K node sample of ICIJ.
3. That immediately proves the system works on real, global tax-evasion data and gives the ML model enough variety to stop overfitting on the tiny `cust-csv/` synthetic set.
4. Only after that works, decide whether to shard UK Companies House / IBM AML for the server-side GNN/SLM training.
