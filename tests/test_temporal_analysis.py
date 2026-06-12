"""Tests for temporal graph analysis."""

from __future__ import annotations

from taxnet.temporal_analysis import (
    build_event_timeline,
    detect_asset_burst,
    parse_year_month,
    temporal_features,
)


def test_parse_year_month_handles_various_formats() -> None:
    assert parse_year_month("2024-06-15") == (2024, 6)
    assert parse_year_month("15-06-2024") == (2024, 6)
    assert parse_year_month("2024/06/15") == (2024, 6)
    assert parse_year_month("2024-06") == (2024, 6)
    assert parse_year_month("2024") == (2024, 1)
    assert parse_year_month(2024) == (2024, 1)
    assert parse_year_month("") is None
    assert parse_year_month("N/A") is None


def test_build_event_timeline_extracts_property_and_vehicle_events() -> None:
    records = [
        {"record_type": "property", "transfer_date": "2024-06-01", "property_value": 10_000_000},
        {"record_type": "vehicle", "registration_year": 2024, "engine_capacity_cc": 3000},
        {"record_type": "tax", "declared_income": 100_000},
    ]
    events = build_event_timeline(records)
    assert len(events) == 2
    assert events[0]["type"] == "property"
    assert events[0]["value"] == 10_000_000
    assert events[1]["type"] == "vehicle"
    assert events[1]["value"] == 3_000_000


def test_detect_asset_burst_true() -> None:
    events = [
        {"year_month": (2024, 6), "type": "property", "value": 10_000_000},
        {"year_month": (2024, 7), "type": "vehicle", "value": 5_000_000},
        {"year_month": (2024, 12), "type": "property", "value": 2_000_000},
    ]
    burst = detect_asset_burst(events, window_months=3, value_threshold=12_000_000)
    assert burst["burst_detected"] is True
    assert burst["window_event_count"] == 2


def test_detect_asset_burst_false() -> None:
    events = [
        {"year_month": (2024, 6), "type": "property", "value": 1_000_000},
        {"year_month": (2024, 12), "type": "property", "value": 2_000_000},
    ]
    burst = detect_asset_burst(events, window_months=3, value_threshold=10_000_000)
    assert burst["burst_detected"] is False


def test_temporal_features() -> None:
    records = [
        {"record_type": "property", "transfer_date": "2024-06-01", "property_value": 10_000_000},
        {"record_type": "vehicle", "registration_year": 2024, "engine_capacity_cc": 3000},
    ]
    features = temporal_features(records)
    assert features["asset_event_count"] == 2
    assert features["first_asset_year"] == 2024
    assert features["last_asset_year"] == 2024
    assert features["peak_asset_year"] == 2024
    assert features["peak_year_asset_value"] == 13_000_000
