# TaxNet XAI — Hackathon Winning Design

**Date:** 2026-06-12  
**Approach:** A — ML + XAI Powerhouse (non-GNN priority, GNN as stretch)  
**Context:** CUST Hackathon 2026, Round 1 rubric weights Technical Implementation 30%, Innovation & Differentiation 20%, Solution Relevance 20%, Validation & Reliability 15%, Feasibility & Scalability 15%.

---

## 1. Goals & Non-Goals

### Goals
- Add real graph-analytics features that feed into risk scoring (rubric: graph relationship depth).
- Replace the heuristic scorer with an interpretable ML model (XGBoost/LightGBM) trained on synthetic data, with SHAP-style attribution (rubric: real anomaly model).
- Implement a 5-tier risk classification mapped to the dashboard.
- Persist the knowledge graph in FalkorDB with real Cypher analytics.
- Strengthen validation: more tests, edge cases, and scalability benchmarks.
- Build backend foundations so UI can be redesigned later without rework.

### Non-Goals
- Small LLM / SLM audit narrative: on hold for this implementation phase.
- GNN anomaly model: on hold for this implementation phase.
- Airflow data pipeline: overkill for a 48-hour demo.
- PCA in the scoring path: hurts interpretability; avoided.
- PEP cross-reference: no real data source available.
- Real-time streaming ingestion.
- UI/UX redesign: will be handled separately using the impeccable skill.

---

## 2. High-Level Architecture

```
CSV Upload / Synthetic Data
        ↓
[Ingestion + Normalization]   (keep, minor polish)
        ↓
[Entity Resolution]           (upgrade: NIC/CNIC, asset-range blocking)
        ↓
[FalkorDB Knowledge Graph]    (new: persistent graph + Cypher analytics)
        ↓
[Feature Engineering]         (new: graph + tabular interpretable features)
        ↓
[XGBoost Scoring Model]       (new: trained ML + SHAP attribution)
        ↓
[JSON API + Explanations]     (keep template-based; SLM on hold)
        ↓
[Web Dashboard]               (UI redesign on hold — impeccable skill later)
```

---

## 3. Module 1 — Entity Resolution Upgrades

### What to polish
- Correct documentation wording: `normalize_address()` **compresses** common address words to abbreviations (`House` → `h`, `Street` → `st`, `Phase` → `ph`, `Block` → `blk`), it does not expand them.
- Add NIC/CNIC field support:
  - `FIELD_SYNONYMS` entries: `cnic`, `nic`, `national_id`, `ntn` mapped to a canonical `national_id` field.
  - `normalize_national_id()` strips dashes/spaces and validates 13-digit CNIC format.
  - Blocking key: `cnic:{normalized_id}` with very high confidence match.
- Add **asset-range blocking**: if two records share same city and have similar vehicle engine CC + similar property value, compare them even if name/address are noisy.
- Add benchmark test for larger synthetic datasets (100, 500, 1000, 5000 citizens) capturing blocking reduction and runtime.

### Acceptance criteria
- Complex CSV blocking reduction is reproducibly reported (currently ~93%).
- CNIC matches get a dedicated high-confidence decision path.
- All existing tests still pass.

---

## 4. Module 2 — Graph Engine: FalkorDB + Analytics

### FalkorDB deployment
The team has deployed FalkorDB as a rootless Podman container:

```bash
podman volume create falkordb_data
podman run -d \
  --name falkordb \
  -v falkordb_data:/var/lib/falkordb/data \
  -p 6379:6379 \
  docker.io/falkordb/falkordb
```

Connection: `redis://localhost:6379` (FalkorDB speaks the Redis protocol and Cypher).

### What to implement
- `taxnet/falkor_engine.py` — graph loader and query client.
- Push nodes: `Person`, `Vehicle`, `Property`, `Meter`, `Address`, `PhoneNumber`, `TaxReturn`.
- Push edges with confidence weights: `OWNS_VEHICLE`, `BOUGHT_PROPERTY`, `HAS_UTILITY_METER`, `USES_ADDRESS`, `USES_PHONE`, `SAME_ADDRESS_AS`, `SHARES_PHONE_WITH`.
- Cypher analytics:
  - PageRank over person-to-person shared-asset/address/phone subgraph.
  - Community detection via weakly connected components (or Louvain if FalkorDB supports it).
  - Shortest path between two flagged persons.
  - Ego network (1-hop and 2-hop neighbors) for dashboard graph view.

### Graph-derived scoring features
- `pagerank_score`
- `community_size`
- `shared_address_count`
- `shared_phone_count`
- `degree_centrality`
- `path_distance_to_nearest_high_risk_node`

### Acceptance criteria
- Graph can be loaded from synthetic and complex CSV data.
- Cypher queries return PageRank and community IDs.
- Dashboard can render an ego-network graph for any selected entity.

---

## 5. Module 3 — ML Scoring (XGBoost + SHAP)

### What to implement
- `taxnet/features.py` — engineered feature vectors from aggregated entity records + graph features.
- Interpretable features:
  - `income_lifestyle_ratio`
  - `vehicle_value_to_income_ratio`
  - `property_value_to_income_ratio`
  - `utility_to_income_ratio`
  - `tax_paid_to_income_ratio`
  - `max_engine_cc`
  - `asset_count`
  - `source_count`
  - `filer_status_encoded`
  - Graph features from Module 2
- `taxnet/ml_scorer.py`:
  - Train XGBoost regressor on synthetic data with injected fraud labels derived from `_truth_scenario`.
  - Predict deviation score 0–100.
  - Compute SHAP values per profile.
  - Map scores to 5-tier risk:
    - 0–20 Green (compliant)
    - 21–40 Yellow (monitor)
    - 41–60 Orange (review)
    - 61–80 Red (audit)
    - 81–100 Critical (immediate investigation)

### Why not PCA
PCA merges interpretable features into abstract components, making explanations like "PC2 contributed +18" useless to auditors. Tree-based models handle multicollinearity naturally, so we train XGBoost directly on the original engineered features and explain with SHAP.

### Acceptance criteria
- Model trains without errors on synthetic data.
- SHAP values sum to the predicted score.
- 5-tier classification is visible in dashboard and JSON export.
- Existing rule-based scorer remains available as a fallback/baseline.

---

## 6. Module 4 — LLM Audit Narrative (ON HOLD)

> **Status:** On hold. Detailed design kept for context.

### What to implement (when revisited)
- `taxnet/llm_narrative.py`:
  - Synthetic training dataset: 500+ examples of `(profile features + top SHAP features) → human-readable audit narrative`.
  - Fine-tune Qwen2.5-1.5B-Instruct or Llama-3.2-1B using LoRA on the A500 48GB GPU.
  - Inference endpoint takes a profile dictionary and returns a generated narrative.
- Keep the existing template-based `build_explanation()` as a fallback if the LLM service is unavailable.

### Acceptance criteria (when revisited)
- Fine-tuning completes on the A500.
- Generated narratives mention concrete features (income gap, vehicle CC, shared address, utility bill).
- Inference latency < 2 seconds per profile.

---

## 7. Module 5 — Visualizations (ON HOLD)

> **Status:** On hold. Detailed design kept for context. UI/UX redesign will be handled separately using the impeccable skill.

### Add/improve (when revisited)
- **Risk-tier matrix / heatmap**: grid of all entities colored by 5-tier risk.
- **Iceberg chart**: reported monthly income vs. imputed lifestyle cost.
- **Network graph**: force-directed D3.js graph with node size by risk score and PageRank.
- **Temporal timeline**: asset acquisitions and tax filings plotted over time.
- **SHAP waterfall chart**: per-profile feature contributions.
- **Benchmark dashboard**: live throughput, blocking reduction, F1 score.

### Polish (when revisited)
- Color coding by 5-tier risk throughout UI.
- Loading states for long operations (FalkorDB load, LLM inference).
- Responsive layout for live demo on projector.

---

## 8. Module 6 — Validation & Reliability

### What to implement
- Unit tests for every new module.
- Integration test for full pipeline with FalkorDB (skip if FalkorDB unavailable).
- Edge-case tests:
  - Urdu names
  - Missing phones
  - Proxy assets under associate names
  - Zero-income filers with luxury assets
  - Shared household addresses that should NOT merge
- Benchmark tests for 100, 500, 1000, 5000 citizens.
- Health-check endpoint `/api/health` reports FalkorDB and LLM status.

### Acceptance criteria
- `uv run python -m unittest discover` passes.
- Demo script can run end-to-end without manual intervention.

---

## 9. Implementation Order

1. **FalkorDB setup + graph loader** — backend foundation.
2. **Graph analytics features** — PageRank, community, degrees.
3. **Entity resolution upgrades** — NIC/CNIC, asset-range blocking.
4. **XGBoost scoring + 5-tier classification**.
5. **SHAP explanations**.
6. ~~LLM fine-tuning + narrative endpoint~~ — on hold.
7. ~~Frontend visualizations~~ — on hold; will be handled by impeccable skill.
8. **Tests, benchmarks, demo script**.

---

## 10. Stretch Goal — GNN Anomaly Model (ON HOLD)

> **Status:** On hold. Detailed design kept for context.

### What to implement (when revisited)
- Implement a lightweight GNN anomaly model using PyTorch Geometric or DGL on the FalkorDB graph, trained on synthetic labels derived from `_truth_scenario`.
- Use the GNN output as an additional risk signal or as a comparison baseline against the XGBoost model.

### Why on hold
- GNN training on synthetic data is risky for live-demo generalization.
- The rubric mentions GNNs as "academic complexity," but Technical Implementation and Innovation can be satisfied first with interpretable ML + graph analytics.
- Revisit only if Modules 1–5 and Module 8 are complete and stable.
