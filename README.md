# TaxNet XAI

Pakistan-first, globally mappable tax fraud detection prototype.

TaxNet XAI links fragmented civic records (tax, property, vehicles, utilities) into a single entity graph, scores every taxpayer for hidden-asset / under-reporting risk, and explains each score with SHAP-backed feature attributions.

---

## What it does

- **Ingests messy civic datasets** — FBR tax returns, excise vehicle registrations, property transfers, DISCO utility bills — and canonicalizes names, phone numbers, CNIC/NTN, and addresses.
- **Resolves identities** across sources with blocking + fuzzy matching + union-find clustering. Exact-match fast paths make common cases cheap; parallel comparison handles larger volumes.
- **Builds a knowledge graph** in memory and optionally loads it into **FalkorDB** for graph analytics (PageRank, communities, degrees, shortest paths).
- **Scores risk** with a blend of interpretable rule-based signals and an XGBoost model trained on synthetic labels.
- **Explains scores** with SHAP so every high-risk flag has a human-readable reason.
- **Exposes a small HTTP API** for health checks, dataset profiling, pipeline runs, demos, and benchmarks.

---

## Quick start

Requires **Python 3.11** and **uv**. FalkorDB runs inside Podman or Docker.

```bash
# Install dependencies and the package in editable mode
uv sync --extra dev
uv pip install -e .

# Start FalkorDB (rootless Podman, falls back to Docker)
uv run python scripts/setup_falkordb.py

# Run tests
uv run pytest tests -q

# Run a small synthetic demo
uv run python scripts/demo_backend.py

# Build the React frontend
npm install
cd web && npm install && npm run build && cd ..

# Run the HTTP server
uv run python run.py
```

Then open `http://127.0.0.1:8000/`.

For frontend development with hot reload and API proxy:

```bash
# Terminal 1: start the Python API server
uv run python run.py

# Terminal 2: start the Vite dev server
npm install
cd web && npm run dev
```

Then open `http://127.0.0.1:5173/`.

---

## HTTP API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Service + FalkorDB health |
| `/api/demo` | GET | Run the default synthetic pipeline |
| `/api/benchmark?citizens=500&seed=42` | GET | Synthetic scalability benchmark |
| `/api/profile` | POST | Profile uploaded datasets without scoring |
| `/api/run` | POST | Ingest, resolve, graph, score uploaded datasets |

---

## Project layout

```
taxnet/
  ingestion.py          # Load + canonicalize + profile datasets
  normalization.py      # Phone, CNIC/NTN, name, address normalization
  entity_resolution.py  # Blocking, fuzzy matching, union-find clustering
  ann_blocking.py       # Optional BlockingPy/FAISS-HNSW ANN blocking
  types.py              # Shared dataclasses (e.g., RecordFingerprint)
  nic_geocode.py        # CNIC/NIC prefix → province/district
  benford.py            # First-digit Benford's Law analysis
  temporal_analysis.py  # Asset-burst and timing anomaly detection
  graph_engine.py       # In-memory property graph builder
  falkor_engine.py      # FalkorDB loader + Cypher analytics
  features.py           # Interpretable feature engineering
  ml_scorer.py          # XGBoost training + SHAP explanations
  scoring.py            # Rule + ML blend, 5-tier risk buckets
  pipeline.py           # End-to-end orchestration
  app.py                # HTTP server
  synthetic.py          # Synthetic dataset generator (seeded)
  loaders/              # Real-world dataset loaders
    icij_loader.py      # ICIJ Offshore Leaks loader (Polars)

scripts/
  setup_falkordb.py     # One-command FalkorDB container setup
  demo_backend.py       # CLI demo of the full pipeline (synthetic)
  demo_icij.py          # CLI demo on ICIJ Offshore Leaks
  benchmark_suite.py    # Scalability benchmark
  sample_data.py        # Quick data header/row sampler

data/
  cust-csv/             # Pakistan synthetic CSV test data
  icij-offshore-leaks/  # Real global tax-evasion graph
  open-sanctions/       # Real global watchlist graph
  energy-mining-data/   # Macro mineral/energy production (not entity-level)
  export-data/          # Macro trade statistics (not entity-level)
  hise-data/            # Household survey aggregates (not entity-level)
  labor-data/           # Labor force survey aggregates (not entity-level)
  pakistani-tax-data/   # Macro tax/GDP indicators (context only)
```

---

## Notes

- **Data mix:** `cust-csv/` is synthetic Pakistan test data. `icij-offshore-leaks/` and `open-sanctions/` are real global datasets now integrated into the pipeline.
- **Frontend is a React + Vite app.** Source lives in `web/src/` and builds to `web/dist/`, which the Python server serves.
- **SLM (small LLM) narrative generation and GNN anomaly detection are on hold** per the user's request. The modules are not removed, just not wired into the pipeline.
- **FalkorDB is optional.** The pipeline degrades gracefully if the container is not running; graph scoring continues with the in-memory graph.
- **ANN blocking is optional.** Set `use_ann_blocking=True` in `run_pipeline` or `resolve_entities` to use BlockingPy/FAISS-HNSW instead of key-based blocking. Useful for large datasets; for small synthetic samples traditional blocking is faster.
- **New interpretability features.** NIC geocoding, Benford's Law analysis, the Living-Luxury-Income (LLI) ratio, and temporal asset-burst detection are computed per entity and exposed in every profile.

## Daily development commands

```bash
# Install dependencies and the package in editable mode
uv sync --extra dev
uv pip install -e .

# Start FalkorDB (rootless Podman, falls back to Docker)
uv run python scripts/setup_falkordb.py

# Run the full test suite
uv run pytest tests -q

# Run the synthetic demo
uv run python scripts/demo_backend.py

# Run the ICIJ Offshore Leaks demo (real global tax-evasion data)
uv run python scripts/demo_icij.py --max-entities 1000 --seed 42

# Run a scalability benchmark
uv run python run.py --benchmark --citizens 500 --seed 42

# Build the React frontend for production
npm install
cd web && npm install && npm run build && cd ..

# Run the full stack (backend + built frontend)
uv run python run.py

# Re-audit dataset headers/rows
uv run python scripts/sample_data.py > docs/data_sample_report.txt
```

See [`STATUS.md`](STATUS.md) for a detailed implementation checklist and dataset audit.
