"""Tests for income-event alignment."""

from __future__ import annotations

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


def test_alignment_asset_burst_count() -> None:
    records = [
        {"record_type": "tax", "declared_income": 1_000_000, "tax_year": 2024},
        {"record_type": "property", "transfer_date": "2024-06-01", "property_value": 6_000_000},
        {"record_type": "vehicle", "registration_year": 2024, "engine_capacity_cc": 5000},
    ]
    metrics = align_income_and_events(records)
    assert metrics["asset_burst_count"] == 2


def test_alignment_multiple_tax_years_sums_income() -> None:
    records = [
        {"record_type": "tax", "declared_income": 50_000, "tax_year": 2024},
        {"record_type": "tax", "declared_income": 50_000, "tax_year": 2024},
        {"record_type": "property", "transfer_date": "2024-01-01", "property_value": 1_000_000},
    ]
    metrics = align_income_and_events(records)
    assert metrics["max_asset_to_income_ratio"] == 10.0
