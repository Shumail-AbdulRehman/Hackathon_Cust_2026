"""Income–event alignment metrics for tax fraud detection."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .temporal_analysis import parse_year_month


ASSET_BURST_WINDOWS_DAYS = (90, 180, 365)
ASSET_BURST_VALUE_THRESHOLD = 10_000_000


def _event_value(record: dict[str, Any]) -> float:
    record_type = record.get("record_type")
    if record_type == "property":
        return float(record.get("property_value") or 0)
    if record_type == "vehicle":
        return float(record.get("engine_capacity_cc") or 0) * 1000.0
    if record_type == "offshore_entity":
        return 1.0
    return 0.0


def _event_year_month(record: dict[str, Any]) -> tuple[int, int] | None:
    record_type = record.get("record_type")
    if record_type == "property":
        return parse_year_month(record.get("transfer_date"))
    if record_type == "vehicle":
        return parse_year_month(record.get("registration_year"))
    if record_type == "offshore_entity":
        return parse_year_month(record.get("offshore_incorporation_date"))
    return None


def _add_months(year: int, month: int, months: int) -> tuple[int, int]:
    total = year * 12 + (month - 1) + months
    return (total // 12, total % 12 + 1)


def align_income_and_events(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Return per-entity income–event alignment metrics."""
    yearly_income: dict[int, float] = defaultdict(float)
    yearly_asset_value: dict[int, float] = defaultdict(float)
    events: list[dict[str, Any]] = []

    for record in records:
        if record.get("record_type") == "tax":
            ym = parse_year_month(record.get("tax_year"))
            if ym:
                yearly_income[ym[0]] += float(record.get("declared_income") or 0)
            continue

        ym = _event_year_month(record)
        value = _event_value(record)
        if ym and value > 0:
            events.append({"year_month": ym, "value": value, "record_type": record["record_type"]})
            yearly_asset_value[ym[0]] += value

    max_ratio = 0.0
    unreported_years = 0
    total_unexplained = 0.0
    for year in yearly_asset_value:
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
        for days in ASSET_BURST_WINDOWS_DAYS:
            window_months = max(1, days // 30)
            for i, event in enumerate(events_sorted):
                window_value = event["value"]
                window_count = 1
                end_year, end_month = _add_months(*event["year_month"], window_months - 1)
                for j in range(i + 1, len(events_sorted)):
                    ey, em = events_sorted[j]["year_month"]
                    if (ey, em) <= (end_year, end_month):
                        window_value += events_sorted[j]["value"]
                        window_count += 1
                    else:
                        break
                if window_value >= ASSET_BURST_VALUE_THRESHOLD and window_count >= 2:
                    asset_burst_count += 1
                    break

    return {
        "max_asset_to_income_ratio": max_ratio,
        "unreported_asset_years": unreported_years,
        "asset_burst_count": asset_burst_count,
        "total_unexplained_value": total_unexplained,
    }
