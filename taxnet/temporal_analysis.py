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
                    "value": float(r.get("engine_capacity_cc") or 0) * 1000,  # rough proxy value
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


def _add_months(year: int, month: int, months: int) -> tuple[int, int]:
    total = year * 12 + (month - 1) + months
    return (total // 12, total % 12 + 1)


def detect_asset_burst(
    events: list[dict[str, Any]],
    window_months: int = 6,
    value_threshold: float = 10_000_000,
) -> dict[str, Any]:
    """Detect if multiple asset events cluster within a short window and exceed a value threshold."""
    if not events:
        return {
            "burst_detected": False,
            "max_window_value": 0.0,
            "window_event_count": 0,
            "window_months": window_months,
        }
    events_sorted = sorted(events, key=lambda e: e["year_month"])
    best_value = 0.0
    best_count = 0
    for i, e in enumerate(events_sorted):
        window = [e]
        end_year, end_month = _add_months(*e["year_month"], window_months - 1)
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
