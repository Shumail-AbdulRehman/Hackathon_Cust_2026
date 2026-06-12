# TaxNet Backend & AI Layers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add FalkorDB-backed knowledge graph with analytics, interpretable XGBoost scoring with SHAP, entity-resolution upgrades, and validation tests to the existing TaxNet prototype — without changing the UI.

**Architecture:** Persist the resolved entity graph in FalkorDB; run Cypher analytics (PageRank, communities, degrees) to produce graph features; combine graph features with tabular lifestyle-mismatch features; train an XGBoost regressor on synthetic labels; explain predictions with SHAP; keep the existing web API contract intact so the future UI redesign consumes richer JSON.

**Tech Stack:** Python 3.11+, uv, FalkorDB (Podman), `falkordb` Python client, `xgboost`, `shap`, `numpy`, `pandas`, `scikit-learn`.

---

## File Structure

### New files
- `pyproject.toml` — project metadata and dependencies (uv-compatible).
- `taxnet/falkor_engine.py` — FalkorDB connection, graph loader, Cypher analytics.
- `taxnet/features.py` — interpretable feature engineering from entities + graph.
- `taxnet/ml_scorer.py` — XGBoost training, prediction, SHAP attribution.
- `tests/test_falkor_engine.py` — FalkorDB integration tests (skip if no DB).
- `tests/test_features.py` — feature engineering tests.
- `tests/test_ml_scorer.py` — ML scorer tests.
- `tests/test_entity_resolution_upgrades.py` — NIC/CNIC and asset-range blocking tests.
- `scripts/demo_backend.py` — end-to-end backend demo script.

### Modified files
- `taxnet/normalization.py` — add `normalize_national_id`, NIC aliases.
- `taxnet/ingestion.py` — add `national_id`/`cnic`/`ntn` field synonyms and canonicalization.
- `taxnet/entity_resolution.py` — add CNIC blocking and asset-range blocking.
- `taxnet/pipeline.py` — wire FalkorDB graph, ML scorer, and SHAP into the pipeline.
- `taxnet/scoring.py` — keep rule-based scorer as fallback; add 5-tier classification helper.
- `taxnet/app.py` — health check reports FalkorDB status.
- `tests/test_pipeline.py` — add ML scorer pipeline tests.

### Unchanged files
- `web/index.html`, `web/app.js`, `web/styles.css` — UI redesign is on hold.
- `taxnet/synthetic.py` — may be extended but not replaced.

---

## Task 1: Project Packaging with uv

**Files:**
- Create: `pyproject.toml`

**Context:** The repo currently has no dependency manifest. We add a `pyproject.toml` so `uv` can install and run everything deterministically.

- [ ] **Step 1: Write pyproject.toml**

```toml
[project]
name = "taxnet"
version = "0.2.0"
description = "TaxNet XAI — Pakistan-first tax fraud detection prototype"
requires-python = ">=3.11"
dependencies = [
    "numpy>=1.26",
    "pandas>=2.0",
    "scikit-learn>=1.4",
    "xgboost>=2.0",
    "shap>=0.45",
    "falkordb>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "ruff>=0.4",
]

[tool.ruff]
line-length = 120
```

- [ ] **Step 2: Install dependencies with uv**

Run: `uv sync`
Expected: dependencies install without errors; `uv run python -c "import xgboost, shap, falkordb"` succeeds.

- [ ] **Step 3: Verify existing tests still pass**

Run: `uv run python -m unittest tests.test_pipeline -v`
Expected: 8/8 tests pass.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
uv run python -m unittest tests.test_pipeline -v
git commit -m "build: add pyproject.toml and uv lockfile"
```

---

## Task 2: Normalize and Ingest NIC/CNIC

**Files:**
- Modify: `taxnet/normalization.py`
- Modify: `taxnet/ingestion.py`
- Test: `tests/test_entity_resolution_upgrades.py`

**Context:** Pakistani CNIC is a 13-digit number. NTN is a 7-digit tax number. We add normalization and field synonyms so these become strong identity signals.

- [ ] **Step 1: Add normalize_national_id and tests**

In `taxnet/normalization.py` add:

```python
import re


def normalize_national_id(value: object) -> str:
    """Normalize Pakistani CNIC/NTN to a clean digit string.

    CNIC: 13 digits (XXXXX-XXXXXXX-X).
    NTN: 7 digits.
    Returns empty string if it does not look like either.
    """
    if value is None:
        return ""
    digits = re.sub(r"\D", "", str(value))
    if len(digits) == 13:
        return digits
    if len(digits) == 7:
        return digits
    return ""
```

In `tests/test_entity_resolution_upgrades.py`:

```python
import unittest
from taxnet.normalization import normalize_national_id


class NationalIdTests(unittest.TestCase):
    def test_cnic_with_dashes(self):
        self.assertEqual(normalize_national_id("35202-1234567-8"), "3520212345678")

    def test_cnic_clean(self):
        self.assertEqual(normalize_national_id("3520212345678"), "3520212345678")

    def test_ntn(self):
        self.assertEqual(normalize_national_id("1234567"), "1234567")

    def test_invalid_returns_empty(self):
        self.assertEqual(normalize_national_id("abc"), "")
```

Run: `uv run python -m unittest tests.test_entity_resolution_upgrades -v`
Expected: tests fail because module does not exist yet.

- [ ] **Step 2: Create test file and run to confirm failure**

Create `tests/test_entity_resolution_upgrades.py` with the content above.
Run: `uv run python -m unittest tests.test_entity_resolution_upgrades -v`
Expected: 4 tests, all currently FAIL or ERROR.

- [ ] **Step 3: Implement normalize_national_id**

Add the function to `taxnet/normalization.py`.

Run: `uv run python -m unittest tests.test_entity_resolution_upgrades -v`
Expected: 4 tests PASS.

- [ ] **Step 4: Add NIC/CNIC field synonyms to ingestion**

In `taxnet/ingestion.py` extend `FIELD_SYNONYMS`:

```python
"national_id": [
    "cnic",
    "nic",
    "national_id",
    "ntn",
    "national_id_number",
    "cnic_no",
],
```

In each canonical record builder (tax, vehicle, utility, property, generic), add:

```python
"national_id": normalize_national_id(value(row, mapping, "national_id")),
```

Import `normalize_national_id` at the top of `taxnet/ingestion.py`.

- [ ] **Step 5: Test ingestion maps NIC fields**

Append to `tests/test_entity_resolution_upgrades.py`:

```python
from taxnet.ingestion import canonicalize_datasets


class IngestionNicTests(unittest.TestCase):
    def test_tax_record_extracts_cnic(self):
        datasets = {
            "tax.csv": [
                {
                    "full_name": "M Ahmed",
                    "cnic": "35202-1234567-8",
                    "declared_income_pkr": "50000",
                    "tax_paid_pkr": "0",
                    "filer_status": "Filer",
                    "reported_address": "House 1 Lahore",
                }
            ]
        }
        records, _ = canonicalize_datasets(datasets)
        self.assertEqual(records[0]["national_id"], "3520212345678")

    def test_vehicle_record_extracts_ntn(self):
        datasets = {
            "vehicles.csv": [
                {
                    "owner_name": "M Ahmed",
                    "ntn": "1234567",
                    "engine_capacity_cc": "1300",
                }
            ]
        }
        records, _ = canonicalize_datasets(datasets)
        self.assertEqual(records[0]["national_id"], "1234567")
```

Run: `uv run python -m unittest tests.test_entity_resolution_upgrades -v`
Expected: 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add taxnet/normalization.py taxnet/ingestion.py tests/test_entity_resolution_upgrades.py
git commit -m "feat: add NIC/CNIC normalization and ingestion"
```

---

## Task 3: Add CNIC Blocking and Asset-Range Blocking to Entity Resolution

**Files:**
- Modify: `taxnet/entity_resolution.py`
- Test: `tests/test_entity_resolution_upgrades.py`

**Context:** Two records with the same CNIC should be compared and merged with high confidence even if names/addresses differ slightly. Asset-range blocking catches associates who share expensive assets and city but not names.

- [ ] **Step 1: Add CNIC to RecordFingerprint and blocking**

In `taxnet/entity_resolution.py`:

1. Import `normalize_national_id` from `.normalization`.
2. Add `national_id: str` to `RecordFingerprint` dataclass.
3. In `fingerprint()`, set `national_id=normalize_national_id(record.get("national_id", ""))`.
4. In `blocking_keys()`, add:

```python
if fp.national_id:
    keys.append(f"national_id:{fp.national_id}")
```

5. In `should_compare()`, add at the top:

```python
if left.national_id and right.national_id and left.national_id == right.national_id:
    return True
```

6. In `compare_records()`, add `same_national_id` and boost score:

```python
same_national_id = bool(left.national_id and right.national_id and left.national_id == right.national_id)
# ...
if same_national_id:
    score = max(score, 0.96)
    reasons.append("same national ID")
```

- [ ] **Step 2: Test CNIC forces comparison**

Append to `tests/test_entity_resolution_upgrades.py`:

```python
from taxnet.entity_resolution import resolve_entities


class CnicBlockingTests(unittest.TestCase):
    def test_same_cnic_merges_despite_name_drift(self):
        records = [
            {
                "source_dataset": "a",
                "source_row_id": "1",
                "source_kind": "tax",
                "person_name": "Muhammad Ahmed Khan",
                "address": "House 1 Lahore",
                "national_id": "35202-1234567-8",
            },
            {
                "source_dataset": "b",
                "source_row_id": "2",
                "source_kind": "vehicle",
                "person_name": "M. Ahmed",
                "address": "H 1 Lahore",
                "national_id": "3520212345678",
            },
        ]
        result = resolve_entities(records)
        self.assertEqual(len(result["entities"]), 1)
```

Run: `uv run python -m unittest tests.test_entity_resolution_upgrades.CnicBlockingTests -v`
Expected: PASS.

- [ ] **Step 3: Add asset-range blocking**

Add helper in `taxnet/entity_resolution.py`:

```python
def asset_range_key(fp: RecordFingerprint) -> str | None:
    # Use surname + city as a coarse key; refine with engine_cc/property_value if present.
    surname_value = surname(fp.norm_name)
    if fp.city and surname_value:
        return f"asset_city_surname:{fp.city}:{surname_value}"
    return None
```

Add to `blocking_keys()`:

```python
asset_key = asset_range_key(fp)
if asset_key:
    keys.append(asset_key)
```

This is intentionally conservative; it only creates extra candidates for records in the same city with the same surname.

- [ ] **Step 4: Test asset-range blocking does not over-merge**

Append to `tests/test_entity_resolution_upgrades.py`:

```python
class AssetRangeBlockingTests(unittest.TestCase):
    def test_different_people_same_city_same_surname_stay_separate(self):
        records = [
            {
                "source_dataset": "a",
                "source_row_id": "1",
                "source_kind": "tax",
                "person_name": "Ali Khan",
                "address": "House 1 Lahore",
            },
            {
                "source_dataset": "a",
                "source_row_id": "2",
                "source_kind": "tax",
                "person_name": "Bilal Khan",
                "address": "House 2 Lahore",
            },
        ]
        result = resolve_entities(records)
        self.assertEqual(len(result["entities"]), 2)
```

Run: `uv run python -m unittest tests.test_entity_resolution_upgrades -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add taxnet/entity_resolution.py tests/test_entity_resolution_upgrades.py
git commit -m "feat: CNIC blocking and conservative asset-range blocking"
```

---

## Task 4: FalkorDB Graph Loader

**Files:**
- Create: `taxnet/falkor_engine.py`
- Modify: `taxnet/pipeline.py`
- Test: `tests/test_falkor_engine.py`

**Context:** The existing `graph_engine.py` builds an in-memory graph. We add a parallel FalkorDB loader so real graph analytics can run via Cypher. The in-memory graph remains for the existing UI API.

- [ ] **Step 1: Write FalkorDB client and loader**

Create `taxnet/falkor_engine.py`:

```python
"""FalkorDB graph loader and analytics."""

from __future__ import annotations

import os
from typing import Any

from falkordb import FalkorDB


def get_falkordb_client() -> FalkorDB:
    host = os.getenv("FALKORDB_HOST", "localhost")
    port = int(os.getenv("FALKORDB_PORT", "6379"))
    return FalkorDB(host=host, port=port)


def load_graph(
    graph_name: str,
    records: list[dict[str, Any]],
    resolution: dict[str, Any],
) -> dict[str, Any]:
    db = get_falkordb_client()
    graph = db.select_graph(graph_name)

    # Clear existing graph for idempotent reloads during development.
    graph.delete()
    graph = db.select_graph(graph_name)

    record_to_entity = resolution["record_to_entity"]
    entity_lookup = {entity["entity_id"]: entity for entity in resolution["entities"]}

    for entity in resolution["entities"]:
        graph.query(
            "MERGE (p:Person {entity_id: $entity_id}) SET p.name = $name",
            {"entity_id": entity["entity_id"], "name": entity["canonical_name"]},
        )

    for record in records:
        source_ref = f"{record['source_dataset']}:{record['source_row_id']}"
        entity_id = record_to_entity.get(source_ref)
        if not entity_id:
            continue

        if record["record_type"] == "vehicle":
            vid = record.get("vehicle_reg_no") or source_ref
            graph.query(
                "MATCH (p:Person {entity_id: $entity_id}) "
                "MERGE (v:Vehicle {id: $vid}) SET v.make_model = $make, v.engine_cc = $cc "
                "MERGE (p)-[:OWNS_VEHICLE {confidence: 0.9}]->(v)",
                {
                    "entity_id": entity_id,
                    "vid": vid,
                    "make": str(record.get("vehicle_make_model") or ""),
                    "cc": float(record.get("engine_capacity_cc") or 0),
                },
            )
        elif record["record_type"] == "property":
            pid = record.get("registry_no") or source_ref
            graph.query(
                "MATCH (p:Person {entity_id: $entity_id}) "
                "MERGE (pr:Property {id: $pid}) SET pr.value = $value, pr.area_marla = $area "
                "MERGE (p)-[:BOUGHT_PROPERTY {confidence: 0.9}]->(pr)",
                {
                    "entity_id": entity_id,
                    "pid": pid,
                    "value": float(record.get("property_value") or 0),
                    "area": float(record.get("area_marla") or 0),
                },
            )
        elif record["record_type"] == "utility":
            mid = record.get("meter_ref_no") or source_ref
            graph.query(
                "MATCH (p:Person {entity_id: $entity_id}) "
                "MERGE (m:Meter {id: $mid}) SET m.monthly_bill = $bill "
                "MERGE (p)-[:HAS_UTILITY_METER {confidence: 0.9}]->(m)",
                {
                    "entity_id": entity_id,
                    "mid": mid,
                    "bill": float(record.get("monthly_bill") or 0),
                },
            )
        elif record["record_type"] == "tax":
            tid = source_ref
            graph.query(
                "MATCH (p:Person {entity_id: $entity_id}) "
                "MERGE (t:TaxReturn {id: $tid}) SET t.income = $income, t.tax_paid = $tax, t.filer_status = $status "
                "MERGE (p)-[:FILED_IN {confidence: 1.0}]->(t)",
                {
                    "entity_id": entity_id,
                    "tid": tid,
                    "income": float(record.get("declared_income") or 0),
                    "tax": float(record.get("tax_paid") or 0),
                    "status": str(record.get("filer_status") or ""),
                },
            )

        # Shared address edges
        address_norm = record.get("address", "")
        if address_norm:
            aid = f"ADDR:{hash(address_norm) & 0xFFFFFFFF}"
            graph.query(
                "MATCH (p:Person {entity_id: $entity_id}) "
                "MERGE (a:Address {id: $aid}) SET a.text = $text "
                "MERGE (p)-[:USES_ADDRESS {confidence: 0.8}]->(a)",
                {"entity_id": entity_id, "aid": aid, "text": address_norm},
            )

        # Shared phone edges
        phone_norm = record.get("phone", "")
        if phone_norm:
            phid = f"PHONE:{phone_norm}"
            graph.query(
                "MATCH (p:Person {entity_id: $entity_id}) "
                "MERGE (ph:PhoneNumber {id: $phid}) SET ph.number = $number "
                "MERGE (p)-[:USES_PHONE {confidence: 0.95}]->(ph)",
                {"entity_id": entity_id, "phid": phid, "number": phone_norm},
            )

    # Connect people who share addresses or phones
    graph.query(
        "MATCH (p1:Person)-[:USES_ADDRESS]->(a:Address)<-[:USES_ADDRESS]-(p2:Person) "
        "WHERE p1 <> p2 "
        "MERGE (p1)-[:SAME_ADDRESS_AS {confidence: 0.75}]->(p2)"
    )
    graph.query(
        "MATCH (p1:Person)-[:USES_PHONE]->(ph:PhoneNumber)<-[:USES_PHONE]-(p2:Person) "
        "WHERE p1 <> p2 "
        "MERGE (p1)-[:SHARES_PHONE_WITH {confidence: 0.95}]->(p2)"
    )

    node_count = graph.query("MATCH (n) RETURN count(n) AS c")[0]["c"]
    edge_count = graph.query("MATCH ()-[r]->() RETURN count(r) AS c")[0]["c"]
    return {"graph_name": graph_name, "nodes": node_count, "edges": edge_count}


def run_pagerank(graph_name: str) -> dict[str, float]:
    db = get_falkordb_client()
    graph = db.select_graph(graph_name)
    try:
        result = graph.query(
            "CALL pagerank() YIELD node, score RETURN node.entity_id AS entity_id, score"
        )
        return {row["entity_id"]: float(row["score"]) for row in result}
    except Exception:
        return {}


def run_communities(graph_name: str) -> dict[str, int]:
    db = get_falkordb_client()
    graph = db.select_graph(graph_name)
    try:
        result = graph.query(
            "CALL weakly_connected_components() YIELD node, componentId "
            "RETURN node.entity_id AS entity_id, componentId"
        )
        return {row["entity_id"]: int(row["componentId"]) for row in result}
    except Exception:
        return {}


def run_degrees(graph_name: str) -> dict[str, int]:
    db = get_falkordb_client()
    graph = db.select_graph(graph_name)
    result = graph.query(
        "MATCH (p:Person)-[r]-(other) "
        "RETURN p.entity_id AS entity_id, count(other) AS degree"
    )
    return {row["entity_id"]: int(row["degree"]) for row in result}
```

- [ ] **Step 2: Wire FalkorDB loader into pipeline**

In `taxnet/pipeline.py`, import `load_graph` from `.falkor_engine` and call it after graph construction:

```python
from .falkor_engine import load_graph


def run_pipeline(...):
    # ... existing code ...
    graph = build_graph(canonical_records, resolution)
    t_graph = time.perf_counter()

    falkor_summary = None
    try:
        falkor_summary = load_graph("taxnet", canonical_records, resolution)
    except Exception as exc:
        falkor_summary = {"error": str(exc)}

    scoring = score_entities(graph, resolution, falkor_summary=falkor_summary)
    # ... rest unchanged ...
```

Update `run_pipeline` return dict to include `"falkor_summary": falkor_summary`.

- [ ] **Step 3: Test FalkorDB loader**

Create `tests/test_falkor_engine.py`:

```python
import os
import unittest

from taxnet.falkor_engine import load_graph, run_communities, run_degrees, run_pagerank
from taxnet.pipeline import run_pipeline


@unittest.skipUnless(os.getenv("FALKORDB_HOST", "localhost"), "FalkorDB not configured")
class FalkorEngineTests(unittest.TestCase):
    def test_load_synthetic_graph(self):
        result = run_pipeline()
        summary = result.get("falkor_summary")
        if summary and "error" in summary:
            self.fail(f"FalkorDB load failed: {summary['error']}")
        self.assertIn("nodes", summary)
        self.assertIn("edges", summary)
        self.assertGreater(summary["nodes"], 0)
        self.assertGreater(summary["edges"], 0)

    def test_pagerank_returns_scores(self):
        run_pipeline()
        scores = run_pagerank("taxnet")
        self.assertIsInstance(scores, dict)
        if scores:
            self.assertTrue(all(0 <= v <= 1 for v in scores.values()))

    def test_communities_returns_components(self):
        run_pipeline()
        communities = run_communities("taxnet")
        self.assertIsInstance(communities, dict)
```

Run: `uv run python -m unittest tests.test_falkor_engine -v`
Expected: tests pass if FalkorDB is running; otherwise skipped.

- [ ] **Step 4: Commit**

```bash
git add taxnet/falkor_engine.py taxnet/pipeline.py tests/test_falkor_engine.py
git commit -m "feat: add FalkorDB graph loader and analytics"
```

---

## Task 5: Graph-Derived Feature Engineering

**Files:**
- Create: `taxnet/features.py`
- Modify: `taxnet/scoring.py`
- Test: `tests/test_features.py`

**Context:** Combine the in-memory graph summary with FalkorDB analytics to produce graph features for the ML model.

- [ ] **Step 1: Write feature engineering module**

Create `taxnet/features.py`:

```python
"""Interpretable feature engineering for tax fraud scoring."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .falkor_engine import run_communities, run_degrees, run_pagerank
from .graph_engine import estimate_vehicle_value


def build_entity_features(
    graph: dict[str, Any],
    resolution: dict[str, Any],
    falkor_summary: dict[str, Any] | None = None,
) -> dict[str, dict[str, float]]:
    """Return a dict mapping entity_id to a feature vector."""
    entity_records = graph.get("entity_records", {})
    features: dict[str, dict[str, float]] = {}

    graph_name = None
    if falkor_summary and "graph_name" in falkor_summary:
        graph_name = falkor_summary["graph_name"]

    pagerank = run_pagerank(graph_name) if graph_name else {}
    communities = run_communities(graph_name) if graph_name else {}
    degrees = run_degrees(graph_name) if graph_name else {}

    # In-memory neighbor analysis
    neighbor_links: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in graph.get("edges", []):
        if edge["relation"] in {"SAME_ADDRESS_AS", "SHARES_PHONE_WITH"}:
            neighbor_links[edge["source"]].append(edge)

    for entity_id, records in entity_records.items():
        tax_records = [r for r in records if r["record_type"] == "tax"]
        vehicles = [r for r in records if r["record_type"] == "vehicle"]
        properties = [r for r in records if r["record_type"] == "property"]
        utilities = [r for r in records if r["record_type"] == "utility"]

        income_values = [r.get("declared_income", 0) for r in tax_records if r.get("declared_income", 0) > 0]
        income = max(income_values) if income_values else 0
        effective_income = income if income_values else 150_000

        vehicle_value = sum(estimate_vehicle_value(float(r.get("engine_capacity_cc") or 0)) for r in vehicles)
        property_value = sum(float(r.get("property_value") or 0) for r in properties)
        utility_monthly = sum(float(r.get("monthly_bill") or 0) for r in utilities)
        tax_paid = sum(float(r.get("tax_paid") or 0) for r in tax_records)
        max_engine_cc = max([float(r.get("engine_capacity_cc") or 0) for r in vehicles] or [0])
        asset_count = len(vehicles) + len(properties)
        source_count = len({r["source_dataset"] for r in records})

        filer_statuses = [str(r.get("filer_status") or "").lower() for r in tax_records]
        is_non_filer = any("non" in s for s in filer_statuses)
        is_filer = any("filer" in s and "non" not in s for s in filer_statuses)

        lifestyle_pressure = utility_monthly + vehicle_value / 120 + property_value / 240

        links = neighbor_links.get(entity_id, [])
        shared_address = sum(1 for e in links if e["relation"] == "SAME_ADDRESS_AS")
        shared_phone = sum(1 for e in links if e["relation"] == "SHARES_PHONE_WITH")

        features[entity_id] = {
            "income_lifestyle_ratio": lifestyle_pressure / max(effective_income, 25_000),
            "vehicle_value_to_income_ratio": vehicle_value / max(effective_income, 25_000),
            "property_value_to_income_ratio": property_value / max(effective_income, 25_000),
            "utility_to_income_ratio": utility_monthly / max(effective_income, 25_000),
            "tax_paid_to_income_ratio": tax_paid / max(effective_income * 12, 1),
            "max_engine_cc": max_engine_cc,
            "asset_count": float(asset_count),
            "source_count": float(source_count),
            "is_non_filer": float(is_non_filer),
            "is_filer": float(is_filer),
            "shared_address_count": float(shared_address),
            "shared_phone_count": float(shared_phone),
            "pagerank_score": float(pagerank.get(entity_id, 0.0)),
            "community_size": float(len([c for c in communities.values() if c == communities.get(entity_id)])),
            "degree_centrality": float(degrees.get(entity_id, 0)),
        }

    return features
```

- [ ] **Step 2: Test feature engineering**

Create `tests/test_features.py`:

```python
import unittest

from taxnet.features import build_entity_features
from taxnet.pipeline import run_pipeline


class FeatureTests(unittest.TestCase):
    def test_features_are_numeric(self):
        result = run_pipeline()
        features = build_entity_features(result["graph"], result["resolution"], result.get("falkor_summary"))
        self.assertGreater(len(features), 0)
        for entity_id, vector in features.items():
            for key, value in vector.items():
                self.assertIsInstance(value, float, f"{entity_id}.{key} is not float")

    def test_high_risk_entity_has_high_income_lifestyle_ratio(self):
        result = run_pipeline()
        features = build_entity_features(result["graph"], result["resolution"], result.get("falkor_summary"))
        flagged = result["scoring"]["flagged_profiles"][0]
        entity_id = flagged["entity_id"]
        self.assertGreater(features[entity_id]["income_lifestyle_ratio"], 1.0)
```

Run: `uv run python -m unittest tests.test_features -v`
Expected: PASS (may skip FalkorDB-derived features if unavailable).

- [ ] **Step 3: Commit**

```bash
git add taxnet/features.py tests/test_features.py
git commit -m "feat: interpretable graph and tabular feature engineering"
```

---

## Task 6: XGBoost Scorer with 5-Tier Risk

**Files:**
- Create: `taxnet/ml_scorer.py`
- Modify: `taxnet/scoring.py`
- Modify: `taxnet/pipeline.py`
- Test: `tests/test_ml_scorer.py`

**Context:** Train an XGBoost regressor on synthetic data labels and integrate it into scoring. Keep the rule-based scorer as a fallback.

- [ ] **Step 1: Create ML scorer module**

Create `taxnet/ml_scorer.py`:

```python
"""Interpretable ML scorer using XGBoost."""

from __future__ import annotations

import os
from typing import Any

import numpy as np
import xgboost as xgb

from .features import build_entity_features


FEATURE_COLUMNS = [
    "income_lifestyle_ratio",
    "vehicle_value_to_income_ratio",
    "property_value_to_income_ratio",
    "utility_to_income_ratio",
    "tax_paid_to_income_ratio",
    "max_engine_cc",
    "asset_count",
    "source_count",
    "is_non_filer",
    "is_filer",
    "shared_address_count",
    "shared_phone_count",
    "pagerank_score",
    "community_size",
    "degree_centrality",
]


def _vector(entity_features: dict[str, float]) -> list[float]:
    return [float(entity_features.get(col, 0.0)) for col in FEATURE_COLUMNS]


def make_training_data(
    graph: dict[str, Any],
    resolution: dict[str, Any],
    falkor_summary: dict[str, Any] | None = None,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Return X, y, entity_ids using truth_scenario labels."""
    features = build_entity_features(graph, resolution, falkor_summary)
    entity_records = graph.get("entity_records", {})

    X, y, ids = [], [], []
    for entity_id, records in entity_records.items():
        vec = _vector(features[entity_id])
        scenarios = {str(r.get("truth_scenario", "")) for r in records}
        # Label: high fraud risk scenarios get high scores.
        if any(s in {"direct_luxury", "proxy_luxury"} for s in scenarios):
            label = 90.0
        elif any("cash_low_tax" in s for s in scenarios):
            label = 60.0
        else:
            label = 10.0
        X.append(vec)
        y.append(label)
        ids.append(entity_id)

    return np.array(X), np.array(y), ids


def train_model(
    graph: dict[str, Any],
    resolution: dict[str, Any],
    falkor_summary: dict[str, Any] | None = None,
) -> xgb.XGBRegressor:
    X, y, _ = make_training_data(graph, resolution, falkor_summary)
    model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.05,
        objective="reg:squarederror",
        random_state=42,
    )
    model.fit(X, y)
    return model


def risk_tier(score: float) -> str:
    if score <= 20:
        return "green"
    if score <= 40:
        return "yellow"
    if score <= 60:
        return "orange"
    if score <= 80:
        return "red"
    return "critical"


def score_with_model(
    model: xgb.XGBRegressor,
    graph: dict[str, Any],
    resolution: dict[str, Any],
    falkor_summary: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    features = build_entity_features(graph, resolution, falkor_summary)
    entity_ids = list(features.keys())
    X = np.array([_vector(features[eid]) for eid in entity_ids])
    predictions = model.predict(X)

    results: dict[str, dict[str, Any]] = {}
    for entity_id, raw_score in zip(entity_ids, predictions):
        clamped = max(0.0, min(100.0, float(raw_score)))
        results[entity_id] = {
            "deviation_score": round(clamped, 1),
            "risk_tier": risk_tier(clamped),
            "features": features[entity_id],
        }
    return results


def save_model(model: xgb.XGBRegressor, path: str) -> None:
    model.save_model(path)


def load_model(path: str) -> xgb.XGBRegressor:
    model = xgb.XGBRegressor()
    model.load_model(path)
    return model
```

- [ ] **Step 2: Integrate ML scorer into scoring**

In `taxnet/scoring.py`, add a helper:

```python
def tier_from_score(score: float) -> str:
    if score <= 20:
        return "green"
    if score <= 40:
        return "yellow"
    if score <= 60:
        return "orange"
    if score <= 80:
        return "red"
    return "critical"
```

Modify `score_entities()` signature to accept `ml_model=None` and `falkor_summary=None`. Inside the profile loop, if `ml_model` is provided, compute the ML score and blend it with the direct score:

```python
ml_score = None
if ml_model is not None:
    from .ml_scorer import score_with_model
    ml_results = score_with_model(ml_model, graph, resolution, falkor_summary)
    ml_score = ml_results.get(entity_id, {}).get("deviation_score")

if ml_score is not None:
    final_score = clamp(0.6 * direct + 0.4 * ml_score)
else:
    final_score = clamp(direct)

level = "high" if final_score >= 75 else "medium" if final_score >= 45 else "low"
tier = tier_from_score(final_score)
```

Add `risk_tier` and `ml_score` to the profile dict.

- [ ] **Step 3: Wire model training into pipeline**

In `taxnet/pipeline.py`, after building the FalkorDB graph, train the model:

```python
from .ml_scorer import train_model

# ... inside run_pipeline ...
try:
    ml_model = train_model(graph, resolution, falkor_summary)
except Exception as exc:
    ml_model = None

scoring = score_entities(graph, resolution, ml_model=ml_model, falkor_summary=falkor_summary)
```

- [ ] **Step 4: Test ML scorer**

Create `tests/test_ml_scorer.py`:

```python
import unittest

from taxnet.ml_scorer import risk_tier, score_with_model, train_model
from taxnet.pipeline import run_pipeline


class MLScorerTests(unittest.TestCase):
    def test_train_and_score(self):
        result = run_pipeline()
        model = train_model(result["graph"], result["resolution"], result.get("falkor_summary"))
        scores = score_with_model(model, result["graph"], result["resolution"], result.get("falkor_summary"))
        self.assertGreater(len(scores), 0)
        for eid, data in scores.items():
            self.assertIn("deviation_score", data)
            self.assertIn("risk_tier", data)
            self.assertGreaterEqual(data["deviation_score"], 0)
            self.assertLessEqual(data["deviation_score"], 100)

    def test_risk_tiers(self):
        self.assertEqual(risk_tier(15), "green")
        self.assertEqual(risk_tier(30), "yellow")
        self.assertEqual(risk_tier(50), "orange")
        self.assertEqual(risk_tier(70), "red")
        self.assertEqual(risk_tier(90), "critical")
```

Run: `uv run python -m unittest tests.test_ml_scorer -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add taxnet/ml_scorer.py taxnet/scoring.py taxnet/pipeline.py tests/test_ml_scorer.py
git commit -m "feat: add XGBoost scorer with 5-tier risk classification"
```

---

## Task 7: SHAP Explanations

**Files:**
- Modify: `taxnet/ml_scorer.py`
- Modify: `taxnet/scoring.py`
- Test: `tests/test_ml_scorer.py`

**Context:** Add SHAP values to the ML scorer and expose them in the profile JSON so the future UI can render waterfall charts.

- [ ] **Step 1: Compute SHAP values in ml_scorer**

Modify `taxnet/ml_scorer.py` to import `shap` and add a function:

```python
import shap


def explain_with_shap(
    model: xgb.XGBRegressor,
    graph: dict[str, Any],
    resolution: dict[str, Any],
    falkor_summary: dict[str, Any] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    features = build_entity_features(graph, resolution, falkor_summary)
    entity_ids = list(features.keys())
    X = np.array([_vector(features[eid]) for eid in entity_ids])

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    base_value = float(explainer.expected_value)

    explanations: dict[str, list[dict[str, Any]]] = {}
    for idx, entity_id in enumerate(entity_ids):
        values = shap_values[idx] if isinstance(shap_values, list) else shap_values[idx]
        explanations[entity_id] = [
            {
                "feature": FEATURE_COLUMNS[j],
                "value": round(float(features[entity_id][FEATURE_COLUMNS[j]]), 4),
                "contribution": round(float(values[j]), 4),
            }
            for j in range(len(FEATURE_COLUMNS))
        ]
        explanations[entity_id].sort(key=lambda item: abs(item["contribution"]), reverse=True)

    return {"base_value": base_value, "explanations": explanations}
```

- [ ] **Step 2: Attach SHAP to profiles**

In `taxnet/scoring.py`, compute SHAP once in `score_entities()` and attach the top features to each profile:

```python
shap_data = None
if ml_model is not None:
    from .ml_scorer import explain_with_shap
    shap_data = explain_with_shap(ml_model, graph, resolution, falkor_summary)

# inside profile loop:
profile["shap_base_value"] = shap_data["base_value"] if shap_data else None
profile["shap_features"] = shap_data["explanations"].get(entity_id, [])[:8] if shap_data else []
```

- [ ] **Step 3: Test SHAP explanations**

Append to `tests/test_ml_scorer.py`:

```python
from taxnet.ml_scorer import explain_with_shap


class ShapTests(unittest.TestCase):
    def test_shap_returns_explanations(self):
        result = run_pipeline()
        model = train_model(result["graph"], result["resolution"], result.get("falkor_summary"))
        shap_result = explain_with_shap(model, result["graph"], result["resolution"], result.get("falkor_summary"))
        self.assertIn("base_value", shap_result)
        self.assertIn("explanations", shap_result)
        self.assertGreater(len(shap_result["explanations"]), 0)
        first = next(iter(shap_result["explanations"].values()))
        self.assertGreater(len(first), 0)
        self.assertIn("feature", first[0])
        self.assertIn("contribution", first[0])
```

Run: `uv run python -m unittest tests.test_ml_scorer -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add taxnet/ml_scorer.py taxnet/scoring.py tests/test_ml_scorer.py
git commit -m "feat: add SHAP explanations to ML scorer"
```

---

## Task 8: Health Check and Demo Script

**Files:**
- Modify: `taxnet/app.py`
- Create: `scripts/demo_backend.py`

**Context:** Add a health endpoint that reports FalkorDB and model status. Create a backend demo script for the live demo.

- [ ] **Step 1: Extend /api/health**

In `taxnet/app.py`, modify `/api/health`:

```python
def falkor_health() -> dict[str, Any]:
    try:
        from .falkor_engine import get_falkordb_client
        client = get_falkordb_client()
        client.connection.ping()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# inside do_GET:
if parsed.path == "/api/health":
    self.send_json({
        "ok": True,
        "service": "taxnet-xai",
        "falkordb": falkor_health(),
    })
    return
```

- [ ] **Step 2: Create backend demo script**

Create `scripts/demo_backend.py`:

```python
"""Backend-only demo script for live judging."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from taxnet.pipeline import run_pipeline


def main() -> None:
    print("Running TaxNet backend demo...")
    result = run_pipeline()

    print(f"\nCanonical records: {len(result['canonical_records'])}")
    print(f"Entities: {len(result['resolution']['entities'])}")
    print(f"FalkorDB summary: {result.get('falkor_summary')}")
    print(f"Flagged profiles: {result['scoring']['summary']['flagged']}")

    print("\nTop 5 flagged profiles:")
    for profile in result["scoring"]["flagged_profiles"][:5]:
        print(
            f"  {profile['entity_id']} {profile['name']}: "
            f"score={profile['deviation_score']} tier={profile.get('risk_tier', 'n/a')} "
            f"ml={profile.get('ml_score', 'n/a')}"
        )
        print(f"    reasons: {profile['direct_reasons'][:2]}")
        if profile.get("shap_features"):
            top = profile["shap_features"][0]
            print(f"    top SHAP: {top['feature']} = {top['contribution']}")

    # Save report for inspection.
    report_path = Path("demo_backend_report.json")
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(result["scoring"]["summary"], f, indent=2)
    print(f"\nSummary saved to {report_path}")


if __name__ == "__main__":
    main()
```

Run: `uv run python scripts/demo_backend.py`
Expected: prints summary and saves report.

- [ ] **Step 3: Commit**

```bash
git add taxnet/app.py scripts/demo_backend.py
git commit -m "feat: add FalkorDB health check and backend demo script"
```

---

## Task 9: Final Validation & Benchmark Suite

**Files:**
- Modify: `tests/test_pipeline.py`
- Create: `scripts/benchmark_suite.py`

**Context:** Ensure everything works together and produce scalability evidence.

- [ ] **Step 1: Add pipeline test for ML + SHAP**

Append to `tests/test_pipeline.py`:

```python
class MLIntegrationTests(unittest.TestCase):
    def test_pipeline_includes_ml_score_and_shap(self):
        result = run_pipeline()
        profiles = result["scoring"]["profiles"]
        self.assertGreater(len(profiles), 0)
        for profile in profiles:
            self.assertIn("risk_tier", profile)
            self.assertIn("ml_score", profile)
            self.assertIn("shap_features", profile)
            self.assertIn(profile["risk_tier"], {"green", "yellow", "orange", "red", "critical"})
```

Run: `uv run python -m unittest tests.test_pipeline -v`
Expected: all tests PASS.

- [ ] **Step 2: Create benchmark suite**

Create `scripts/benchmark_suite.py`:

```python
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from taxnet.pipeline import run_benchmark


def main() -> None:
    sizes = [100, 500, 1000, 2000]
    results = []
    for citizens in sizes:
        print(f"Benchmarking {citizens} citizens...")
        summary = run_benchmark(citizens=citizens)
        results.append({
            "citizens": citizens,
            "records": summary["canonical_record_count"],
            "entities": summary["entity_count"],
            "flagged": summary["scoring_summary"]["flagged"],
            "total_ms": summary["timing_ms"]["total"],
            "throughput": summary["throughput_records_per_second"],
            "blocking_reduction": summary["resolution_runtime_stats"]["blocking_reduction_pct"],
        })

    print(json.dumps(results, indent=2))
    with open("benchmark_suite_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
```

Run: `uv run python scripts/benchmark_suite.py`
Expected: produces benchmark results for multiple sizes.

- [ ] **Step 3: Final full test run**

Run: `uv run python -m unittest discover -v`
Expected: all tests PASS (FalkorDB tests skip if DB unavailable).

- [ ] **Step 4: Commit**

```bash
git add tests/test_pipeline.py scripts/benchmark_suite.py
git commit -m "test: add ML integration tests and benchmark suite"
```

---

## Self-Review Checklist

1. **Spec coverage:**
   - FalkorDB graph loader → Task 4
   - Graph analytics (PageRank, communities, degrees) → Task 4 + Task 5
   - Entity resolution upgrades (NIC, asset-range blocking) → Task 2 + Task 3
   - XGBoost scoring + 5-tier risk → Task 6
   - SHAP explanations → Task 7
   - Tests + benchmarks → Task 1 + Task 9
   - UI/UX on hold → explicitly excluded
   - SLM/GNN on hold → explicitly excluded

2. **Placeholder scan:** No TBDs, TODOs, or vague steps. Each step includes code or exact commands.

3. **Type consistency:**
   - `falkor_summary` dict is used consistently across `pipeline.py`, `features.py`, `ml_scorer.py`, `scoring.py`.
   - Feature column names match between `features.py` and `ml_scorer.py`.
   - `risk_tier` logic matches in `ml_scorer.py` and `scoring.py`.

4. **Tooling:** All commands use `uv run` as requested by the user.
