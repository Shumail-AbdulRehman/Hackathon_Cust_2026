"""Tests for NIC geocoding integration in feature engineering."""

from __future__ import annotations

from taxnet.features import build_entity_features


def _make_record(record_type: str, **kwargs) -> dict:
    return {
        "record_type": record_type,
        "source_dataset": "test.csv",
        "source_row_id": "1",
        **kwargs,
    }


def test_features_include_nic_geo() -> None:
    graph = {
        "entity_records": {
            "E1": [
                _make_record("tax", declared_income=100_000, national_id="35201-1234567-1"),
            ]
        },
        "nodes": [],
        "edges": [],
    }
    resolution = {"entities": [{"entity_id": "E1", "canonical_name": "Test", "source_record_ids": ["test.csv:1"]}]}
    features = build_entity_features(graph, resolution)
    assert features["E1"]["nic_province_punjab"] == 1.0
    assert features["E1"]["nic_province_sindh"] == 0.0
    assert features["E1"]["nic_district_count"] == 1.0
    assert features["E1"]["district_known"] == 1.0
    assert features["E1"]["district_risk_score"] > 0


def test_features_include_district_risk_for_sindh() -> None:
    graph = {
        "entity_records": {
            "E1": [
                _make_record("tax", declared_income=100_000, national_id="42201-1234567-1"),
            ]
        },
        "nodes": [],
        "edges": [],
    }
    resolution = {"entities": [{"entity_id": "E1", "canonical_name": "Test", "source_record_ids": ["test.csv:1"]}]}
    features = build_entity_features(graph, resolution)
    assert features["E1"]["nic_province_sindh"] == 1.0
    assert features["E1"]["district_known"] == 1.0
    assert features["E1"]["district_risk_score"] > 0
