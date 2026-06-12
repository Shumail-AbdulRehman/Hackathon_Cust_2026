# Backend Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add four interpretable backend capabilities to TaxNet XAI: Benford's Law analysis, temporal graph analysis, a named Living-Luxury-Income (LLI) metric, and NIC geocoding.

**Architecture:** Each feature gets its own focused module under `taxnet/`. The features are computed from canonical records and fed into `taxnet/features.py` and `taxnet/scoring.py` so they appear in profiles, explanations, and the ML feature vector. New tests mirror the existing `tests/test_features.py` / `tests/test_pipeline.py` style.

**Tech Stack:** Python 3.11, standard library + numpy, existing TaxNet modules.

---

## Task 1: NIC geocoding

**Files:**
- Create: `taxnet/nic_geocode.py`
- Modify: `taxnet/features.py` (add geocoded features), `taxnet/normalization.py` (CNIC parser helper if needed)
- Test: `tests/test_nic_geocode.py`

### 1.1 Add CNIC prefix → province/district mapping

- [ ] **Step 1: Write failing test**

```python
def test_cnic_to_province():
    from taxnet.nic_geocode import cnic_location
    assert cnic_location("3520112345671")["province"] == "Punjab"
    assert cnic_location("4220112345671")["province"] == "Sindh"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_nic_geocode.py::test_cnic_to_province -v`
Expected: FAIL

- [ ] **Step 3: Implement `taxnet/nic_geocode.py`**

Create `taxnet/nic_geocode.py`:

```python
"""Pakistani CNIC/NIC prefix geocoding."""

from __future__ import annotations

from typing import Any


# First digit of 13-digit CNIC = province; first 5 digits = district.
_PROVINCE_BY_FIRST_DIGIT: dict[str, str] = {
    "1": "Khyber Pakhtunkhwa",
    "2": "FATA / Tribal Areas",
    "3": "Punjab",
    "4": "Sindh",
    "5": "Balochistan",
    "6": "Islamabad Capital Territory",
    "7": "Gilgit-Baltistan",
    "8": "Azad Kashmir",
}

_DISTRICT_BY_PREFIX: dict[str, dict[str, str]] = {
    "Punjab": {
        "35201": "Lahore",
        "35202": "Sheikhupura",
        "35301": "Gujranwala",
        "35401": "Sialkot",
        "37201": "Faisalabad",
        "38101": "Multan",
        "39101": "Rawalpindi",
    },
    "Sindh": {
        "42201": "Karachi",
        "43501": "Hyderabad",
        "45201": "Sukkur",
    },
    "Khyber Pakhtunkhwa": {
        "11101": "Peshawar",
        "13101": "Mardan",
        "15101": "Abbottabad",
    },
    "Balochistan": {
        "51201": "Quetta",
        "52201": "Khuzdar",
    },
    "Islamabad Capital Territory": {
        "61101": "Islamabad",
    },
    "Azad Kashmir": {
        "81101": "Muzaffarabad",
    },
    "Gilgit-Baltistan": {
        "71101": "Gilgit",
    },
}


def _normalize_nic(nic: Any) -> str:
    text = str(nic or "").strip()
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits


def cnic_location(nic: Any) -> dict[str, str]:
    """Return province and district for a Pakistani CNIC/NIC."""
    digits = _normalize_nic(nic)
    if len(digits) < 1:
        return {"province": "", "district": ""}
    province = _PROVINCE_BY_FIRST_DIGIT.get(digits[0], "Unknown")
    district = ""
    if len(digits) >= 5:
        district_map = _DISTRICT_BY_PREFIX.get(province, {})
        district = district_map.get(digits[:5], "")
    return {"province": province, "district": district}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_nic_geocode.py -v`
Expected: PASS

---

### 1.2 Integrate NIC geocoding into feature engineering

- [ ] **Step 1: Write failing test**

```python
def test_features_include_nic_geo():
    from taxnet.features import build_entity_features
    graph = {
        "entity_records": {
            "E1": [
                {
                    "record_type": "tax",
                    "declared_income": 100000,
                    "national_id": "3520112345671",
                    "source_dataset": "tax.csv",
                    "source_row_id": "1",
                }
            ]
        },
        "nodes": [],
        "edges": [],
    }
    resolution = {"entities": [{"entity_id": "E1", "canonical_name": "Test", "source_record_ids": ["tax.csv:1"]}]}
    features = build_entity_features(graph, resolution)
    assert features["E1"]["nic_province_punjab"] == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_features.py::test_features_include_nic_geo -v`
Expected: FAIL

- [ ] **Step 3: Modify `taxnet/features.py`**

At the top add:
```python
from .nic_geocode import cnic_location
```

Inside `build_entity_features`, after computing `effective_income`, add:
```python
        # NIC geocoding
        nic_provinces: set[str] = set()
        nic_districts: set[str] = set()
        for r in records:
            loc = cnic_location(r.get("national_id"))
            if loc["province"]:
                nic_provinces.add(loc["province"])
            if loc["district"]:
                nic_districts.add(loc["district"])
```

Add to the returned feature dict:
```python
            "nic_province_count": float(len(nic_provinces)),
            "nic_district_count": float(len(nic_districts)),
```

Also add one-hot province flags for the top provinces (Punjab, Sindh, KP, Balochistan, Islamabad):
```python
            "nic_province_punjab": float("Punjab" in nic_provinces),
            "nic_province_sindh": float("Sindh" in nic_provinces),
            "nic_province_kp": float("Khyber Pakhtunkhwa" in nic_provinces),
            "nic_province_balochistan": float("Balochistan" in nic_provinces),
            "nic_province_islamabad": float("Islamabad Capital Territory" in nic_provinces),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_features.py -v`
Expected: PASS

---

## Task 2: Benford's Law analysis

**Files:**
- Create: `taxnet/benford.py`
- Modify: `taxnet/features.py` (add benford deviation features), `taxnet/scoring.py` (add benford reasons)
- Test: `tests/test_benford.py`

### 2.1 Implement Benford analysis

- [ ] **Step 1: Write failing test**

```python
def test_benford_known_distribution():
    from taxnet.benford import benford_mad
    # Perfect Benford first digits 1-9
    counts = [301, 176, 125, 97, 79, 67, 58, 51, 46]
    mad, _ = benford_mad(counts)
    assert mad < 0.005
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_benford.py::test_benford_known_distribution -v`
Expected: FAIL

- [ ] **Step 3: Implement `taxnet/benford.py`**

```python
"""Benford's Law first-digit analysis for numeric columns."""

from __future__ import annotations

import math
from typing import Any


BENFORD_EXPECTED = {
    1: 0.301,
    2: 0.176,
    3: 0.125,
    4: 0.097,
    5: 0.079,
    6: 0.067,
    7: 0.058,
    8: 0.051,
    9: 0.046,
}


def first_digit(value: Any) -> int | None:
    """Return the first non-zero digit of a positive number."""
    text = str(value or "").strip().replace(",", "")
    digits = "".join(ch for ch in text if ch.isdigit())
    for ch in digits:
        if ch != "0":
            return int(ch)
    return None


def benford_counts(values: list[Any]) -> dict[int, int]:
    counts: dict[int, int] = {d: 0 for d in range(1, 10)}
    for value in values:
        digit = first_digit(value)
        if digit is not None:
            counts[digit] += 1
    return counts


def benford_mad(counts: dict[int, int]) -> tuple[float, dict[int, float]]:
    """Mean Absolute Deviation from Benford distribution; returns MAD and per-digit deviations."""
    total = sum(counts.values())
    if total < 30:
        return 0.0, {d: 0.0 for d in range(1, 10)}
    observed = {d: counts[d] / total for d in range(1, 10)}
    deviations = {d: abs(observed[d] - BENFORD_EXPECTED[d]) for d in range(1, 10)}
    mad = sum(deviations.values()) / 9
    return mad, deviations


def benford_anomaly_score(mad: float) -> float:
    """Scale MAD to a 0-100 anomaly score."""
    if mad <= 0.004:
        return 0.0
    if mad <= 0.008:
        return 25.0
    if mad <= 0.012:
        return 50.0
    if mad <= 0.016:
        return 75.0
    return 100.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_benford.py -v`
Expected: PASS

---

### 2.2 Add Benford features per entity

- [ ] **Step 1: Write failing test**

```python
def test_benford_feature_flagged_for_uniform_digits():
    from taxnet.features import build_entity_features
    graph = {
        "entity_records": {
            "E1": [
                {
                    "record_type": "tax",
                    "declared_income": 111111,
                    "tax_paid": 222222,
                    "source_dataset": "tax.csv",
                    "source_row_id": "1",
                }
            ]
        },
        "nodes": [],
        "edges": [],
    }
    resolution = {"entities": [{"entity_id": "E1", "canonical_name": "Test", "source_record_ids": ["tax.csv:1"]}]}
    features = build_entity_features(graph, resolution)
    assert features["E1"]["benford_income_mad"] > 0.01
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_features.py::test_benford_feature_flagged_for_uniform_digits -v`
Expected: FAIL

- [ ] **Step 3: Modify `taxnet/features.py`**

At the top add:
```python
from .benford import benford_counts, benford_mad
```

Inside `build_entity_features`, after collecting tax/vehicle/property/utility records, add:
```python
        # Benford analysis across numeric columns
        benford_fields = {
            "income": [r.get("declared_income") for r in tax_records],
            "tax_paid": [r.get("tax_paid") for r in tax_records],
            "property_value": [r.get("property_value") for r in properties],
            "utility_bill": [r.get("monthly_bill") for r in utilities],
            "vehicle_cc": [r.get("engine_capacity_cc") for r in vehicles],
        }
        benford_mads: dict[str, float] = {}
        for label, values in benford_fields.items():
            counts = benford_counts(values)
            mad, _ = benford_mad(counts)
            benford_mads[label] = mad
```

Add to returned dict:
```python
            "benford_income_mad": benford_mads.get("income", 0.0),
            "benford_tax_paid_mad": benford_mads.get("tax_paid", 0.0),
            "benford_property_mad": benford_mads.get("property_value", 0.0),
            "benford_utility_mad": benford_mads.get("utility_bill", 0.0),
            "benford_vehicle_cc_mad": benford_mads.get("vehicle_cc", 0.0),
            "benford_max_mad": max(benford_mads.values()) if benford_mads else 0.0,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_features.py -v`
Expected: PASS

---

## Task 3: Living-Luxury-Income (LLI) metric

**Files:**
- Modify: `taxnet/features.py`, `taxnet/scoring.py`
- Test: `tests/test_features.py`, `tests/test_pipeline.py`

### 3.1 Compute LLI in features

- [ ] **Step 1: Write failing test**

```python
def test_lli_metric():
    from taxnet.features import build_entity_features
    graph = {
        "entity_records": {
            "E1": [
                {
                    "record_type": "tax",
                    "declared_income": 100000,
                    "source_dataset": "tax.csv",
                    "source_row_id": "1",
                },
                {
                    "record_type": "vehicle",
                    "engine_capacity_cc": 3000,
                    "source_dataset": "vehicles.csv",
                    "source_row_id": "1",
                },
            ]
        },
        "nodes": [],
        "edges": [],
    }
    resolution = {"entities": [{"entity_id": "E1", "canonical_name": "Test", "source_record_ids": ["tax.csv:1", "vehicles.csv:1"]}]}
    features = build_entity_features(graph, resolution)
    assert features["E1"]["lli_ratio"] > 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_features.py::test_lli_metric -v`
Expected: FAIL

- [ ] **Step 3: Modify `taxnet/features.py`**

Inside `build_entity_features`, after `lifestyle_pressure` is computed, add:
```python
        # Living-Luxury-Income metric: monthly lifestyle pressure + imputed monthly asset cost / declared income
        annualized_asset_cost = vehicle_value / 120 + property_value / 240
        lli_numerator = lifestyle_pressure + annualized_asset_cost
        lli_ratio = lli_numerator / max(effective_income, 25_000)
```

Add to returned dict:
```python
            "lli_ratio": lli_ratio,
            "lli_score": clamp(lli_ratio * 25, 0, 100),
```

(Import `clamp` from scoring or duplicate a local helper.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_features.py -v`
Expected: PASS

---

### 3.2 Expose LLI in scoring profile

- [ ] **Step 1: Modify `taxnet/scoring.py`**

In `direct_score`, after computing `components`, add:
```python
        lli_ratio = float(agg.get("lli_ratio") or 0.0)
        components["lli_gap"] = clamp((lli_ratio - 1.0) * 20, 0, 25)
```

In reasons section add:
```python
    if components.get("lli_gap", 0) > 0:
        reasons.append(f"living-luxury-income ratio is {lli_ratio:.1f}x")
```

Make sure `aggregate_entity` copies `lli_ratio` from the first record or from features. Actually `agg` is built from records; we need to pass features into `direct_score` OR compute LLI inside `aggregate_entity` as well.

Simpler: compute LLI in `aggregate_entity`:
```python
    pressure = lifestyle_pressure(agg)
    income = float(agg["effective_monthly_income_for_scoring"])
    agg["lli_ratio"] = pressure / max(income, 25_000)
```

- [ ] **Step 2: Update pipeline / API profile output**

Ensure `profile["aggregate"]` includes `lli_ratio` so the frontend/API can show it.

---

## Task 4: Temporal graph analysis

**Files:**
- Create: `taxnet/temporal_analysis.py`
- Modify: `taxnet/features.py`, `taxnet/graph_engine.py` (store dates on edges/nodes), `taxnet/scoring.py`
- Test: `tests/test_temporal_analysis.py`

### 4.1 Parse dates and detect bursts

- [ ] **Step 1: Write failing test**

```python
def test_asset_burst_detection():
    from taxnet.temporal_analysis import detect_asset_burst
    events = [
        {"date": "2024-06-01", "type": "property", "value": 10000000},
        {"date": "2024-06-15", "type": "vehicle", "value": 5000000},
        {"date": "2024-12-01", "type": "property", "value": 2000000},
    ]
    burst = detect_asset_burst(events, window_months=3, value_threshold=12000000)
    assert burst["burst_detected"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_temporal_analysis.py::test_asset_burst_detection -v`
Expected: FAIL

- [ ] **Step 3: Implement `taxnet/temporal_analysis.py`**

```python
"""Temporal graph analysis: asset bursts, timing anomalies, date parsing."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any


def parse_year_month(value: Any) -> tuple[int, int] | None:
    """Extract (year, month) from a date string/int."""
    if value is None:
        return None
    if isinstance(value, int):
        return (value, 1)
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y", "%Y-%m", "%Y"):
        try:
            dt = datetime.strptime(text, fmt)
            return (dt.year, dt.month)
        except ValueError:
            continue
    # Try extracting 4-digit year anywhere in the string
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 4:
        year = int(digits[:4])
        if 1990 <= year <= 2100:
            month = int(digits[4:6]) if len(digits) >= 6 and 1 <= int(digits[4:6]) <= 12 else 1
            return (year, month)
    return None


def build_event_timeline(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract dated asset/income events from an entity's records."""
    events = []
    for r in records:
        record_type = r.get("record_type")
        if record_type == "property":
            ym = parse_year_month(r.get("transfer_date"))
            if ym:
                events.append({
                    "year_month": ym,
                    "type": "property",
                    "value": float(r.get("property_value") or 0),
                    "record_type": record_type,
                })
        elif record_type == "vehicle":
            year = r.get("registration_year")
            ym = parse_year_month(year)
            if ym:
                events.append({
                    "year_month": ym,
                    "type": "vehicle",
                    "value": float(r.get("engine_capacity_cc") or 0) * 1000,  # rough proxy
                    "record_type": record_type,
                })
        elif record_type == "offshore_entity":
            ym = parse_year_month(r.get("offshore_incorporation_date"))
            if ym:
                events.append({
                    "year_month": ym,
                    "type": "offshore_entity",
                    "value": 1.0,
                    "record_type": record_type,
                })
    return events


def detect_asset_burst(
    events: list[dict[str, Any]],
    window_months: int = 6,
    value_threshold: float = 10_000_000,
) -> dict[str, Any]:
    """Detect if multiple asset events cluster within a short window and exceed a value threshold."""
    if not events:
        return {"burst_detected": False, "max_window_value": 0.0, "window_event_count": 0, "window_months": window_months}
    events_sorted = sorted(events, key=lambda e: e["year_month"])
    best_value = 0.0
    best_count = 0
    for i, e in enumerate(events_sorted):
        window = [e]
        year, month = e["year_month"]
        end_year = year + (month + window_months - 1) // 12
        end_month = (month + window_months - 1) % 12 + 1
        for j in range(i + 1, len(events_sorted)):
            ey, em = events_sorted[j]["year_month"]
            if (ey, em) <= (end_year, end_month):
                window.append(events_sorted[j])
            else:
                break
        total = sum(item["value"] for item in window)
        if total > best_value:
            best_value = total
            best_count = len(window)
    return {
        "burst_detected": bool(best_value >= value_threshold and best_count >= 2),
        "max_window_value": best_value,
        "window_event_count": best_count,
        "window_months": window_months,
    }


def temporal_features(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a dict of temporal features for a single entity."""
    events = build_event_timeline(records)
    burst = detect_asset_burst(events)
    first_year = min((e["year_month"][0] for e in events), default=0)
    last_year = max((e["year_month"][0] for e in events), default=0)
    yearly_counts: dict[int, int] = defaultdict(int)
    yearly_values: dict[int, float] = defaultdict(float)
    for e in events:
        y = e["year_month"][0]
        yearly_counts[y] += 1
        yearly_values[y] += e["value"]
    peak_year = max(yearly_values, key=yearly_values.get, default=0)
    return {
        "asset_event_count": len(events),
        "first_asset_year": first_year,
        "last_asset_year": last_year,
        "asset_burst_detected": burst["burst_detected"],
        "asset_burst_window_value": burst["max_window_value"],
        "asset_burst_window_event_count": burst["window_event_count"],
        "peak_asset_year": peak_year,
        "peak_year_asset_value": yearly_values.get(peak_year, 0.0),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_temporal_analysis.py -v`
Expected: PASS

---

### 4.2 Add temporal features to scoring

- [ ] **Step 1: Modify `taxnet/features.py`**

At top:
```python
from .temporal_analysis import temporal_features
```

Inside loop:
```python
        temporal = temporal_features(records)
```

Add to returned dict:
```python
            "asset_event_count": float(temporal["asset_event_count"]),
            "asset_burst_detected": float(temporal["asset_burst_detected"]),
            "asset_burst_window_value": temporal["asset_burst_window_value"],
            "peak_asset_year": float(temporal["peak_asset_year"]),
            "first_asset_year": float(temporal["first_asset_year"]),
            "last_asset_year": float(temporal["last_asset_year"]),
```

- [ ] **Step 2: Modify `taxnet/scoring.py`**

In `direct_score`, add:
```python
        if agg.get("asset_burst_detected"):
            components["asset_burst"] = 20.0
            reasons.append(f"asset burst detected: PKR {agg.get('asset_burst_window_value', 0):,.0f} within window")
```

- [ ] **Step 3: Run pipeline test**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: PASS

---

## Task 5: Update ML feature columns

**Files:**
- Modify: `taxnet/ml_scorer.py`

- [ ] **Step 1: Add new features to `FEATURE_COLUMNS`**

Append to the list:
```python
    "lli_ratio",
    "lli_score",
    "nic_province_count",
    "nic_province_punjab",
    "nic_province_sindh",
    "nic_province_kp",
    "nic_province_balochistan",
    "nic_province_islamabad",
    "nic_district_count",
    "benford_max_mad",
    "benford_income_mad",
    "asset_event_count",
    "asset_burst_detected",
```

- [ ] **Step 2: Run tests**

Run: `uv run pytest tests/test_ml_scorer.py -v`
Expected: PASS

---

## Task 6: Update docs

**Files:**
- Modify: `README.md`, `STATUS.md`

- [ ] **Step 1: Update README.md**

Add to project layout:
```
  nic_geocode.py        # CNIC/NIC prefix → province/district
  benford.py            # First-digit Benford analysis
  temporal_analysis.py  # Asset burst / timing anomaly detection
```

Add Notes bullet:
- **New interpretability features:** NIC geocoding, Benford's Law, LLI ratio, and temporal asset-burst detection are computed per entity and shown in profiles.

- [ ] **Step 2: Update STATUS.md**

Mark the four areas as done in §1 and remove/adjust them from §3 and §5.

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest tests -q`
Expected: 45+ tests passing
