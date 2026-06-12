"""Tests for the Living-Luxury-Income (LLI) metric."""

from __future__ import annotations

from taxnet.features import build_entity_features
from taxnet.scoring import aggregate_entity


def _make_record(record_type: str, **kwargs) -> dict:
    return {
        "record_type": record_type,
        "source_dataset": "test.csv",
        "source_row_id": "1",
        **kwargs,
    }


def test_lli_metric_high_for_luxury() -> None:
    graph = {
        "entity_records": {
            "E1": [
                _make_record("tax", declared_income=100_000),
                _make_record("vehicle", engine_capacity_cc=3000),
            ]
        },
        "nodes": [],
        "edges": [],
    }
    resolution = {
        "entities": [
            {
                "entity_id": "E1",
                "canonical_name": "Test",
                "source_record_ids": ["test.csv:1", "test.csv:2"],
            }
        ]
    }
    features = build_entity_features(graph, resolution)
    assert features["E1"]["lli_ratio"] > 1.0
    assert features["E1"]["lli_score"] > 0.0


def test_aggregate_entity_includes_lli_ratio() -> None:
    records = [
        _make_record("tax", declared_income=100_000),
        _make_record("vehicle", engine_capacity_cc=3000),
    ]
    agg = aggregate_entity(records)
    assert agg["lli_ratio"] > 0.0
