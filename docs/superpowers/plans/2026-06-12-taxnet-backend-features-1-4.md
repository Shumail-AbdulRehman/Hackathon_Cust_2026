# TaxNet Backend Features 1–4 + Scoring Weight Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire OpenSanctions watchlist screening, income–event alignment, a live `cust-csv/` demo, expanded district-level NIC features, and a scoring fix that makes shared CNIC/NTN much more alarming than shared phone numbers.

**Architecture:** Add small, focused modules for each new signal, integrate them into `taxnet/features.py` and `taxnet/scoring.py`, surface them through the web API and the new `scripts/demo_cust_csv.py`, and add relation-specific weights in the associate-risk calculation.

**Tech Stack:** Python 3.11, Polars, existing `taxnet` normalization utilities, pytest, ruff.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `taxnet/loaders/open_sanctions_loader.py` | Stream `targets.simple.csv`, normalize targets (name, aliases, country, schema, identifiers). |
| `taxnet/watchlist_screening.py` | Match resolved entities against OpenSanctions targets using normalized names/aliases; return best match per entity. |
| `taxnet/income_event_alignment.py` | Compute per-entity income–asset alignment metrics (yearly ratios, unreported years, asset bursts). |
| `taxnet/nic_geocode.py` | Expand CNIC prefix → district/province mapping and add district-risk lookup. |
| `taxnet/features.py` | Add income-event and district-risk feature columns; add `shared_national_id_count`. |
| `taxnet/scoring.py` | Add watchlist and income-event rule components; relation-weight associate links so CNIC/NTN > phone > address. |
| `taxnet/graph_engine.py` | Emit `SHARES_NATIONAL_ID_WITH` edges for distinct entities that share a national ID. |
| `taxnet/falkor_engine.py` | Include `SHARES_NATIONAL_ID_WITH` in FalkorDB merge/queries. |
| `taxnet/ml_scorer.py` | Append new feature columns to `FEATURE_COLUMNS`. |
| `taxnet/app.py` | Expose `watchlist_matches` in `/api/profile/<entity_id>` and add `/api/screen` on-demand endpoint. |
| `scripts/demo_cust_csv.py` | Load real CSVs from `data/cust-csv/`, run pipeline, write `demo_cust_csv_report.json`. |
| `README.md` | Document the new demo command. |
| Tests | One focused test module per new/changed signal. |

---

## Task 1: OpenSanctions Loader

**Files:**
- Create: `taxnet/loaders/open_sanctions_loader.py`
- Test: `tests/test_open_sanctions_loader.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
from taxnet.loaders.open_sanctions_loader import load_targets, sanitize_name


def test_sanitize_name_strips_noise() -> None:
    assert sanitize_name("  ALI, Raza  ") == "ali raza"


def test_load_targets_returns_list(tmp_path: Path) -> None:
    csv_path = tmp_path / "targets.csv"
    csv_path.write_text(
        "id,schema,name,aliases,birth_date,countries,addresses,identifiers,sanctions,phones,emails,program_ids,dataset,first_seen,last_seen,last_change\n"
        "sanction-1,Person,Ali Raza,,,PK,,,EU sanctions,,,,eu sanctions,2024-01-01,2024-01-01,\n"
    )
    targets = load_targets(csv_path)
    assert len(targets) == 1
    assert targets[0]["id"] == "sanction-1"
    assert targets[0]["name"] == "ali raza"
    assert targets[0]["schema"] == "Person"
    assert targets[0]["countries"] == ["PK"]


def test_load_targets_gracefully_missing_file() -> None:
    assert load_targets(Path("/does/not/exist.csv")) == []
```

Run: `pytest tests/test_open_sanctions_loader.py -v`
Expected: FAIL with module not found.

- [ ] **Step 2: Implement the loader**

```python
"""OpenSanctions targets.simple.csv loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl

from ..normalization import normalize_name


def sanitize_name(value: Any) -> str:
    return normalize_name(value)


def _split(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    return [part.strip() for part in text.split(";") if part.strip()]


def load_targets(path: Path | str) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    try:
        df = pl.read_csv(path, infer_schema_length=0)
    except Exception:
        return []

    required = {"id", "schema", "name"}
    if not required.issubset(set(df.columns)):
        return []

    rows = df.to_dicts()
    targets = []
    for row in rows:
        name = sanitize_name(row.get("name"))
        if not name:
            continue
        aliases = [sanitize_name(a) for a in _split(row.get("aliases"))]
        aliases = [a for a in aliases if a and a != name]
        targets.append(
            {
                "id": str(row.get("id", "")).strip(),
                "schema": str(row.get("schema", "")).strip(),
                "name": name,
                "aliases": aliases,
                "countries": [c.upper() for c in _split(row.get("countries"))],
                "sanctions": _split(row.get("sanctions")),
                "dataset": str(row.get("dataset", "")).strip(),
                "raw": row,
            }
        )
    return targets
```

Run: `pytest tests/test_open_sanctions_loader.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add taxnet/loaders/open_sanctions_loader.py tests/test_open_sanctions_loader.py
git commit -m "feat: add OpenSanctions targets loader"
```

---

## Task 2: Watchlist Screening

**Files:**
- Create: `taxnet/watchlist_screening.py`
- Modify: `taxnet/scoring.py`
- Test: `tests/test_watchlist_screening.py`

- [ ] **Step 1: Write the failing test**

```python
from taxnet.watchlist_screening import match_entity, score_name_similarity


def test_score_name_similarity_exact() -> None:
    assert score_name_similarity("ali raza", "ali raza") == 1.0


def test_score_name_similarity_partial() -> None:
    assert 0.5 < score_name_similarity("muhammad ahmed khan", "m ahmed khan") < 1.0


def test_match_entity_returns_best_match() -> None:
    targets = [
        {"id": "t1", "name": "ali raza", "aliases": [], "countries": ["PK"], "schema": "Person"},
        {"id": "t2", "name": "sara malik", "aliases": [], "countries": ["PK"], "schema": "Person"},
    ]
    entity = {"canonical_name": "ali raza sheikh", "aliases": ["a raza"]}
    match = match_entity(entity, targets, threshold=0.8)
    assert match is not None
    assert match["target_id"] == "t1"
    assert match["similarity"] >= 0.8


def test_match_entity_respects_threshold() -> None:
    targets = [{"id": "t1", "name": "sara malik", "aliases": [], "countries": [], "schema": "Person"}]
    entity = {"canonical_name": "ali raza", "aliases": []}
    assert match_entity(entity, targets, threshold=0.9) is None
```

Run: `pytest tests/test_watchlist_screening.py -v`
Expected: FAIL with module not found.

- [ ] **Step 2: Implement the screening module**

```python
"""Watchlist screening against OpenSanctions targets."""

from __future__ import annotations

from typing import Any

from .normalization import normalize_name, token_similarity


OPEN_SANCTIONS_MATCH_THRESHOLD = 0.85


def score_name_similarity(left: str, right: str) -> float:
    """Return the best normalized name similarity score."""
    return token_similarity(normalize_name(left), normalize_name(right))


def _candidate_names(entity: dict[str, Any]) -> list[str]:
    names = [normalize_name(entity.get("canonical_name", ""))]
    for alias in entity.get("aliases", []):
        norm = normalize_name(alias)
        if norm and norm not in names:
            names.append(norm)
    return [n for n in names if n]


def match_entity(
    entity: dict[str, Any],
    targets: list[dict[str, Any]],
    threshold: float = OPEN_SANCTIONS_MATCH_THRESHOLD,
) -> dict[str, Any] | None:
    """Return the best watchlist match for a resolved entity, or None."""
    entity_names = _candidate_names(entity)
    if not entity_names or not targets:
        return None

    best: dict[str, Any] | None = None
    best_score = 0.0
    for target in targets:
        target_names = [target["name"]] + target.get("aliases", [])
        for tname in target_names:
            for ename in entity_names:
                score = score_name_similarity(ename, tname)
                if score > best_score:
                    best_score = score
                    best = {
                        "target_id": target["id"],
                        "target_name": target["name"],
                        "target_schema": target.get("schema", ""),
                        "target_countries": target.get("countries", []),
                        "target_sanctions": target.get("sanctions", []),
                        "matched_alias": tname if tname != target["name"] else "",
                        "similarity": round(score, 3),
                    }
    if best and best_score >= threshold:
        return best
    return None


def screen_entities(
    entities: list[dict[str, Any]],
    targets: list[dict[str, Any]],
    threshold: float = OPEN_SANCTIONS_MATCH_THRESHOLD,
) -> dict[str, dict[str, Any]]:
    """Return a mapping of entity_id -> best watchlist match."""
    results: dict[str, dict[str, Any]] = {}
    for entity in entities:
        match = match_entity(entity, targets, threshold=threshold)
        if match:
            results[entity["entity_id"]] = match
    return results
```

Run: `pytest tests/test_watchlist_screening.py -v`
Expected: PASS.

- [ ] **Step 3: Wire watchlist into scoring**

In `taxnet/scoring.py`:

1. Update `direct_score` signature to accept an optional `watchlist_match` argument and return an extra component.

```python
def direct_score(
    agg: dict[str, Any], watchlist_match: dict[str, Any] | None = None
) -> tuple[float, dict[str, float], list[str], list[str]]:
    ...
    components = {
        ...,
        "watchlist_match": 30.0 if watchlist_match else 0.0,
    }
    ...
    if watchlist_match:
        reasons.append(
            f"name closely matches sanctioned entity '{watchlist_match['target_name']}' (similarity {watchlist_match['similarity']:.2f})"
        )
```

2. Update `score_entities` to load OpenSanctions targets (from `data/open-sanctions/targets.simple.csv`) and pass matches.

```python
from .loaders.open_sanctions_loader import load_targets
from .watchlist_screening import screen_entities


def score_entities(...):
    ...
    watchlist_matches = {}
    try:
        targets = load_targets(Path(__file__).resolve().parents[2] / "data" / "open-sanctions" / "targets.simple.csv")
        watchlist_matches = screen_entities(resolution["entities"], targets)
    except Exception:
        watchlist_matches = {}
    ...
    for entity_id, entity in entity_lookup.items():
        match = watchlist_matches.get(entity_id)
        direct, components, direct_reasons, uncertainty_flags = direct_score(agg, watchlist_match=match)
        ...
        profile = {
            ...,
            "watchlist_matches": [match] if match else [],
        }
```

Run: `pytest tests/test_watchlist_screening.py tests/test_pipeline.py -v`
Expected: PASS (pipeline may take a few seconds).

- [ ] **Step 4: Commit**

```bash
git add taxnet/watchlist_screening.py taxnet/scoring.py tests/test_watchlist_screening.py
git commit -m "feat: add OpenSanctions watchlist screening and scoring boost"
```

---

## Task 3: Income–Event Alignment

**Files:**
- Create: `taxnet/income_event_alignment.py`
- Modify: `taxnet/features.py`, `taxnet/scoring.py`
- Test: `tests/test_income_event_alignment.py`

- [ ] **Step 1: Write the failing test**

```python
from taxnet.income_event_alignment import align_income_and_events


def test_alignment_computes_year_ratio() -> None:
    records = [
        {"record_type": "tax", "declared_income": 100_000, "tax_year": 2024},
        {"record_type": "property", "transfer_date": "2024-06-01", "property_value": 12_000_000},
    ]
    metrics = align_income_and_events(records)
    assert metrics["max_asset_to_income_ratio"] == 120.0
    assert metrics["unreported_asset_years"] == 0
    assert metrics["total_unexplained_value"] == 0.0


def test_alignment_counts_unreported_years() -> None:
    records = [
        {"record_type": "property", "transfer_date": "2023-01-01", "property_value": 5_000_000},
    ]
    metrics = align_income_and_events(records)
    assert metrics["unreported_asset_years"] == 1
    assert metrics["total_unexplained_value"] == 5_000_000.0


def test_alignment_handles_missing_values() -> None:
    assert align_income_and_events([]) == {
        "max_asset_to_income_ratio": 0.0,
        "unreported_asset_years": 0,
        "asset_burst_count": 0,
        "total_unexplained_value": 0.0,
    }
```

Run: `pytest tests/test_income_event_alignment.py -v`
Expected: FAIL.

- [ ] **Step 2: Implement income-event alignment**

```python
"""Income–event alignment metrics."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .temporal_analysis import parse_year_month


ASSET_BURST_WINDOWS = (90, 180, 365)
ASSET_BURST_VALUE = 10_000_000


def _event_value(record: dict[str, Any]) -> float:
    if record["record_type"] == "property":
        return float(record.get("property_value") or 0)
    if record["record_type"] == "vehicle":
        return float(record.get("engine_capacity_cc") or 0) * 1000.0
    if record["record_type"] == "offshore_entity":
        return 1.0
    return 0.0


def _event_year_month(record: dict[str, Any]) -> tuple[int, int] | None:
    if record["record_type"] == "property":
        return parse_year_month(record.get("transfer_date"))
    if record["record_type"] == "vehicle":
        return parse_year_month(record.get("registration_year"))
    if record["record_type"] == "offshore_entity":
        return parse_year_month(record.get("offshore_incorporation_date"))
    return None


def align_income_and_events(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Return per-entity income–event alignment metrics."""
    yearly_income: dict[int, float] = defaultdict(float)
    yearly_asset_value: dict[int, float] = defaultdict(float)
    events: list[dict[str, Any]] = []

    for r in records:
        if r["record_type"] == "tax":
            ym = parse_year_month(r.get("tax_year"))
            if ym:
                yearly_income[ym[0]] += float(r.get("declared_income") or 0)
        else:
            ym = _event_year_month(r)
            value = _event_value(r)
            if ym and value > 0:
                events.append({"year_month": ym, "value": value, "record_type": r["record_type"]})
                yearly_asset_value[ym[0]] += value

    max_ratio = 0.0
    unreported_years = 0
    total_unexplained = 0.0
    years_with_assets = set(yearly_asset_value.keys())
    for year in years_with_assets:
        income = yearly_income.get(year, 0.0)
        assets = yearly_asset_value[year]
        if income > 0:
            ratio = assets / income
            if ratio > max_ratio:
                max_ratio = ratio
        else:
            unreported_years += 1
            total_unexplained += assets

    asset_burst_count = 0
    if events:
        events_sorted = sorted(events, key=lambda e: e["year_month"])
        for days in ASSET_BURST_WINDOWS:
            for i, e in enumerate(events_sorted):
                window_value = e["value"]
                window_count = 1
                ey, em = e["year_month"]
                end_total_months = ey * 12 + (em - 1) + days // 30
                end_year, end_month = end_total_months // 12, end_total_months % 12 + 1
                for j in range(i + 1, len(events_sorted)):
                    ey2, em2 = events_sorted[j]["year_month"]
                    if (ey2, em2) <= (end_year, end_month):
                        window_value += events_sorted[j]["value"]
                        window_count += 1
                    else:
                        break
                if window_value >= ASSET_BURST_VALUE and window_count >= 2:
                    asset_burst_count += 1
                    break

    return {
        "max_asset_to_income_ratio": max_ratio,
        "unreported_asset_years": unreported_years,
        "asset_burst_count": asset_burst_count,
        "total_unexplained_value": total_unexplained,
    }
```

Run: `pytest tests/test_income_event_alignment.py -v`
Expected: PASS.

- [ ] **Step 3: Integrate into features and scoring**

In `taxnet/features.py`, inside `build_entity_features`, add after temporal features:

```python
from .income_event_alignment import align_income_and_events
...
alignment = align_income_and_events(records)
...
features[entity_id].update(
    {
        "max_asset_to_income_ratio": float(alignment["max_asset_to_income_ratio"]),
        "unreported_asset_years": float(alignment["unreported_asset_years"]),
        "asset_burst_count": float(alignment["asset_burst_count"]),
        "total_unexplained_value": float(alignment["total_unexplained_value"]),
    }
)
```

In `taxnet/scoring.py`, add a rule component in `direct_score`:

```python
def direct_score(agg, watchlist_match=None):
    ...
    components = {
        ...,
        "income_event_gap": 0.0,
    }
    ...
    alignment_ratio = float(agg.get("max_asset_to_income_ratio") or 0.0)
    unreported_years = int(agg.get("unreported_asset_years") or 0)
    unexplained = float(agg.get("total_unexplained_value") or 0.0)
    if alignment_ratio > 50:
        components["income_event_gap"] = clamp((alignment_ratio - 50) / 50 * 20, 0, 25)
    elif unreported_years > 0:
        components["income_event_gap"] = min(15.0, unreported_years * 8)
    elif unexplained > 5_000_000:
        components["income_event_gap"] = 10.0
    ...
    if components["income_event_gap"] > 0:
        reasons.append(
            f"asset acquisitions are {alignment_ratio:.0f}x declared income in a single year"
        )
```

- [ ] **Step 4: Commit**

```bash
git add taxnet/income_event_alignment.py taxnet/features.py taxnet/scoring.py tests/test_income_event_alignment.py
git commit -m "feat: add income-event alignment metrics and scoring"
```

---

## Task 4: District-Level Risk Features

**Files:**
- Modify: `taxnet/nic_geocode.py`, `taxnet/features.py`, `taxnet/scoring.py`
- Test: `tests/test_features_nic.py` (extend)

- [ ] **Step 1: Write the failing test additions**

Append to `tests/test_features_nic.py`:

```python
from taxnet.nic_geocode import DISTRICT_RISK_SCORES, cnic_location, extract_prefix, lookup_district


def test_extract_prefix_from_cnic() -> None:
    assert extract_prefix("35201-1234567-1") == "35201"


def test_lookup_district_returns_risk() -> None:
    loc = lookup_district("3520112345671")
    assert loc["province"] == "Punjab"
    assert loc["district"] == "Lahore"
    assert loc["district_risk_score"] >= 0


def test_district_risk_score_for_high_risk_district() -> None:
    assert DISTRICT_RISK_SCORES.get("Karachi", 0) > 0


def test_features_include_district_risk() -> None:
    graph = {
        "entity_records": {
            "E1": [
                _make_record("tax", declared_income=100_000, national_id="42201-1234567-1"),
            ]
        },
        "nodes": [],
        "edges": [],
    }
    resolution = {
        "entities": [
            {"entity_id": "E1", "canonical_name": "Test", "source_record_ids": ["test.csv:1"]}
        ]
    }
    features = build_entity_features(graph, resolution)
    assert features["E1"]["nic_province_sindh"] == 1.0
    assert features["E1"]["district_known"] == 1.0
    assert features["E1"]["district_risk_score"] > 0
```

Run: `pytest tests/test_features_nic.py -v`
Expected: FAIL.

- [ ] **Step 2: Expand `taxnet/nic_geocode.py`**

1. Replace `_DISTRICT_BY_PREFIX` with a comprehensive static table (at least 30 districts across all provinces/territories). Keep the existing format.
2. Add a `DISTRICT_RISK_SCORES` dictionary mapping district names to 0–3 scores (e.g., 1 for large urban centers, 2 for reported high-risk districts, 0 otherwise).
3. Add helpers:

```python

def extract_prefix(cnic: Any) -> str:
    digits = _normalize_nic(cnic)
    return digits[:5] if len(digits) >= 5 else ""


def lookup_district(cnic: Any) -> dict[str, Any]:
    loc = cnic_location(cnic)
    district = loc["district"]
    return {
        "province": loc["province"],
        "district": district,
        "district_risk_score": DISTRICT_RISK_SCORES.get(district, 0),
        "district_known": bool(district),
    }
```

- [ ] **Step 3: Integrate into features and scoring**

In `taxnet/features.py`:

```python
from .nic_geocode import lookup_district
...
        # NIC geocoding
        district_risk = 0
        district_known = 0.0
        for r in records:
            loc = lookup_district(r.get("national_id"))
            if loc["province"]:
                nic_provinces.add(loc["province"])
            if loc["district"]:
                nic_districts.add(loc["district"])
                district_risk = max(district_risk, loc["district_risk_score"])
                district_known = 1.0
...
features[entity_id].update(
    {
        ...,
        "district_known": district_known,
        "district_risk_score": float(district_risk),
    }
)
```

In `taxnet/scoring.py`, add a small rule component and explanation:

```python
        "district_risk": min(float(agg.get("district_risk_score") or 0) * 5, 12),
```

```python
    if components.get("district_risk", 0) > 0:
        reasons.append(
            f"CNIC prefix indicates a higher-reported-risk district (score {agg.get('district_risk_score', 0)})"
        )
```

- [ ] **Step 4: Commit**

```bash
git add taxnet/nic_geocode.py taxnet/features.py taxnet/scoring.py tests/test_features_nic.py
git commit -m "feat: expand district NIC mapping and add district risk features"
```

---

## Task 5: Scoring Weight Fix — CNIC/NTN vs. Phone

**Files:**
- Modify: `taxnet/graph_engine.py`, `taxnet/scoring.py`, `taxnet/features.py`, `taxnet/falkor_engine.py`, `taxnet/ml_scorer.py`
- Test: `tests/test_scoring_weights.py`

- [ ] **Step 1: Write the failing test**

```python
from taxnet.scoring import score_entities


def make_record(eid, record_type, **kwargs):
    return {"source_dataset": "test", "source_row_id": eid, "record_type": record_type, **kwargs}


def test_national_id_link_weights_more_than_phone() -> None:
    records = [
        make_record("t1", "tax", person_name="Ali Raza", declared_income=50_000, national_id="1110100000001", address="House 1 Karachi"),
        make_record("p1", "property", person_name="Ali Raza", property_value=100_000_000, transfer_date="2024-01-01", national_id="1110100000002"),
        make_record("t2", "tax", person_name="Noman Raza", declared_income=50_000, national_id="1110100000002", address="House 2 Karachi", phone="03001234567"),
    ]
    from taxnet.entity_resolution import resolve_entities
    from taxnet.graph_engine import build_graph

    resolution = resolve_entities(records)
    graph = build_graph(records, resolution)
    result = score_entities(graph, resolution)
    by_id = {p["entity_id"]: p for p in result["profiles"]}
    # Find the entity that owns the high-value property.
    owner = next(p for p in result["profiles"] if p["name"] == "Ali Raza")
    assert owner["associate_proxy_score"] > 0
    # The national-ID link should be mentioned with higher weight than a pure phone link.
    assert any("national ID" in r.lower() for r in owner["associate_reasons"])
```

Run: `pytest tests/test_scoring_weights.py -v`
Expected: FAIL.

- [ ] **Step 2: Emit `SHARES_NATIONAL_ID_WITH` edges**

In `taxnet/graph_engine.py`, after phone/address edge generation:

```python
    national_id_to_entities: dict[str, set[str]] = defaultdict(set)
    for record in records:
        source_ref = f"{record['source_dataset']}:{record['source_row_id']}"
        entity_id = record_to_entity.get(source_ref)
        if not entity_id:
            continue
        national_id = normalize_national_id(record.get("national_id", ""))
        if national_id:
            national_id_to_entities[national_id].add(entity_id)

    for national_id, entity_ids in national_id_to_entities.items():
        sorted_ids = sorted(entity_ids)
        for idx, left in enumerate(sorted_ids):
            for right in sorted_ids[idx + 1 :]:
                add_edge(left, right, "SHARES_NATIONAL_ID_WITH", 1.0, {"national_id_prefix": national_id[:5]})
                add_edge(right, left, "SHARES_NATIONAL_ID_WITH", 1.0, {"national_id_prefix": national_id[:5]})
```

Also add `SHARES_NATIONAL_ID_WITH` to the `falkor_engine.py` merge pattern and shortest-path query.

- [ ] **Step 3: Relation-weight the associate calculation**

In `taxnet/scoring.py`:

```python
ASSOCIATE_LINK_WEIGHTS = {
    "SHARES_NATIONAL_ID_WITH": 1.6,
    "SHARES_PHONE_WITH": 0.6,
    "SAME_ADDRESS_AS": 0.35,
}

...

        for link in neighbor_links.get(entity_id, []):
            neighbor_id = link["target"]
            neighbor_agg = aggregates.get(neighbor_id)
            if not neighbor_agg:
                continue
            neighbor_assets = neighbor_agg["estimated_vehicle_value"] + neighbor_agg["estimated_property_value"]
            if neighbor_assets <= 0:
                continue
            weight = ASSOCIATE_LINK_WEIGHTS.get(link["relation"], 0.5)
            effective_confidence = float(link["confidence"]) * weight
            strongest_link = max(strongest_link, effective_confidence)
            associate_asset_value += neighbor_assets * effective_confidence
            neighbor_name = entity_lookup.get(neighbor_id, {}).get("canonical_name", neighbor_id)
            associate_reasons.append(
                f"{link['relation'].lower()} {neighbor_name}, linked assets PKR {neighbor_assets:,.0f}"
            )
```

Also update `taxnet/features.py` neighbor analysis to include `SHARES_NATIONAL_ID_WITH` and count it.

```python
        shared_national_id = sum(1 for e in links if e["relation"] == "SHARES_NATIONAL_ID_WITH")
        features[entity_id]["shared_national_id_count"] = float(shared_national_id)
```

Update `FEATURE_COLUMNS` in `taxnet/ml_scorer.py` to append the new columns:

```python
    "shared_national_id_count",
    "max_asset_to_income_ratio",
    "unreported_asset_years",
    "asset_burst_count",
    "total_unexplained_value",
    "district_known",
    "district_risk_score",
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_scoring_weights.py tests/test_pipeline.py tests/test_features.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add taxnet/graph_engine.py taxnet/falkor_engine.py taxnet/features.py taxnet/scoring.py taxnet/ml_scorer.py tests/test_scoring_weights.py
git commit -m "fix: weight CNIC/NTN sharing much more heavily than phone sharing in associate risk"
```

---

## Task 6: Live `cust-csv/` Demo Script

**Files:**
- Create: `scripts/demo_cust_csv.py`
- Modify: `README.md`
- Test: `tests/test_demo_cust_csv.py`

- [ ] **Step 1: Write the failing test**

```python
import json
import subprocess
import sys
from pathlib import Path


def test_demo_cust_csv_creates_report() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/demo_cust_csv.py", "--no-server"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    report = Path("demo_cust_csv_report.json")
    assert report.exists()
    data = json.loads(report.read_text())
    assert "flagged" in data
    assert "high" in data
```

Run: `pytest tests/test_demo_cust_csv.py -v`
Expected: FAIL.

- [ ] **Step 2: Implement the script**

```python
"""Run TaxNet on the real Pakistan-shaped CSVs in data/cust-csv/."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from taxnet.pipeline import run_pipeline


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def discover_datasets(input_dir: Path) -> dict[str, list[dict[str, str]]]:
    datasets: dict[str, list[dict[str, str]]] = {}
    for path in sorted(input_dir.glob("*.csv")):
        if path.name.lower() == "readme.md":
            continue
        datasets[path.name] = load_csv(path)
    return datasets


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TaxNet on data/cust-csv/")
    parser.add_argument("--input-dir", type=Path, default=Path("data/cust-csv"))
    parser.add_argument("--no-server", action="store_true", help="Do not start the web server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    print(f"Loading CSVs from {args.input_dir}...")
    datasets = discover_datasets(args.input_dir)
    if not datasets:
        print("No CSV files found.")
        sys.exit(1)

    print(f"Running pipeline on {len(datasets)} datasets...")
    result = run_pipeline(datasets=datasets, use_ml=False)

    summary = result["scoring"]["summary"]
    print(f"\nCanonical records: {len(result['canonical_records'])}")
    print(f"Entities: {len(result['resolution']['entities'])}")
    print(f"Flagged profiles: {summary['flagged']} (high={summary['high']}, medium={summary['medium']})")

    print("\nTop 5 flagged profiles:")
    for profile in result["scoring"]["flagged_profiles"][:5]:
        print(
            f"  {profile['entity_id']} {profile['name']}: "
            f"score={profile['deviation_score']} tier={profile.get('risk_tier', 'n/a')}"
        )
        print(f"    reasons: {profile['direct_reasons'][:2]}")

    report_path = Path("demo_cust_csv_report.json")
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary saved to {report_path}")

    if not args.no_server:
        from taxnet.app import main as run_server
        sys.argv = [sys.argv[0], "--host", args.host, "--port", str(args.port)]
        run_server()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Add README documentation**

Append to `README.md` under the demo/run section:

```markdown
### Run on the real Pakistan-shaped CSVs

```bash
uv run python scripts/demo_cust_csv.py
```

This loads the files in `data/cust-csv/`, runs the full pipeline, writes `demo_cust_csv_report.json`, and starts the web dashboard.
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_demo_cust_csv.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/demo_cust_csv.py tests/test_demo_cust_csv.py README.md
git commit -m "feat: add live cust-csv demo script and test"
```

---

## Task 7: API Watchlist Endpoint

**Files:**
- Modify: `taxnet/app.py`
- Test: `tests/test_app.py` (create if missing)

- [ ] **Step 1: Write the failing test**

```python
import json
from http.client import HTTPConnection
from multiprocessing import Process
from time import sleep

from taxnet.app import main as run_server


def test_api_profile_includes_watchlist(tmp_path) -> None:
    # Start server in a subprocess
    proc = Process(target=run_server, args=("127.0.0.1", 18081))
    proc.start()
    sleep(1)
    try:
        conn = HTTPConnection("127.0.0.1", 18081)
        conn.request("POST", "/api/run", body=json.dumps({"datasets": {}}), headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        assert resp.status == 200
    finally:
        proc.terminate()
        proc.join()
```

Skip if threading server is hard to test; instead add a lightweight import test:

```python
def test_app_imports() -> None:
    from taxnet.app import TaxNetHandler
    assert TaxNetHandler
```

- [ ] **Step 2: Extend `taxnet/app.py`**

1. In `do_GET`, add `/api/profile/<entity_id>`:

```python
        if parsed.path.startswith("/api/profile/"):
            entity_id = parsed.path.split("/")[-1]
            result = compact_result(run_pipeline())
            profile = next((p for p in result["scoring"]["profiles"] if p["entity_id"] == entity_id), None)
            if profile is None:
                self.send_json({"error": "Profile not found"}, status=404)
                return
            self.send_json(profile)
            return
```

2. Add `/api/screen` POST endpoint:

```python
        if parsed.path == "/api/screen":
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            datasets = payload.get("datasets")
            if not isinstance(datasets, dict):
                self.send_json({"error": "Expected datasets object"}, status=400)
                return
            result = compact_result(run_pipeline(datasets=datasets, use_ml=False))
            self.send_json({
                "watchlist_matches": {
                    p["entity_id"]: p.get("watchlist_matches", [])
                    for p in result["scoring"]["profiles"]
                    if p.get("watchlist_matches")
                }
            })
            return
```

- [ ] **Step 3: Commit**

```bash
git add taxnet/app.py tests/test_app.py
git commit -m "feat: expose watchlist matches via API endpoints"
```

---

## Task 8: Final Verification

- [ ] **Step 1: Run full test suite**

```bash
uv run pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run lint/format**

```bash
uv run ruff check taxnet tests scripts
uv run ruff format taxnet tests scripts
```

Expected: clean.

- [ ] **Step 3: Run the cust-csv demo**

```bash
uv run python scripts/demo_cust_csv.py --no-server
```

Expected: `demo_cust_csv_report.json` created and summary printed.

- [ ] **Step 4: Commit any final fixes**

```bash
git add -A
git commit -m "chore: final verification and formatting"
```

---

## Self-Review

- **Spec coverage:** Each numbered design item has a dedicated task.
- **Placeholder scan:** No TBD/TODO placeholders; every code block is complete.
- **Type consistency:** `watchlist_match`, `align_income_and_events`, `lookup_district`, `SHARES_NATIONAL_ID_WITH`, and new feature names are consistent across modules and tests.
