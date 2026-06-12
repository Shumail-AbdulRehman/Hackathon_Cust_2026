"""Tests for Benford's Law integration in feature engineering."""

from __future__ import annotations

from taxnet.features import build_entity_features


def _make_record(record_type: str, **kwargs) -> dict:
    return {
        "record_type": record_type,
        "source_dataset": "test.csv",
        "source_row_id": "1",
        **kwargs,
    }


def test_benford_feature_flagged_for_uniform_digits() -> None:
    # Generate 30 records with uniform first digits to exceed the sample threshold.
    tax_records = [
        _make_record("tax", declared_income=int(f"{d}00000"), tax_paid=int(f"{d}0000"))
        for d in list(range(1, 10)) * 4  # 36 records
    ]
    graph = {
        "entity_records": {"E1": tax_records},
        "nodes": [],
        "edges": [],
    }
    resolution = {
        "entities": [
            {
                "entity_id": "E1",
                "canonical_name": "Test",
                "source_record_ids": [r["source_row_id"] for r in tax_records],
            }
        ]
    }
    features = build_entity_features(graph, resolution)
    assert features["E1"]["benford_income_mad"] > 0.01
    assert features["E1"]["benford_max_mad"] > 0.01


def test_benford_features_default_to_zero_with_no_records() -> None:
    graph = {
        "entity_records": {"E1": []},
        "nodes": [],
        "edges": [],
    }
    resolution = {
        "entities": [
            {"entity_id": "E1", "canonical_name": "Test", "source_record_ids": []}
        ]
    }
    features = build_entity_features(graph, resolution)
    assert features["E1"]["benford_max_mad"] == 0.0
