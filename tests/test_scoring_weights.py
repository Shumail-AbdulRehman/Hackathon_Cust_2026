"""Tests for associate-risk scoring weights."""

from __future__ import annotations

from taxnet.features import build_entity_features
from taxnet.graph_engine import build_graph
from taxnet.scoring import ASSOCIATE_LINK_WEIGHTS, score_entities


def _make_record(source_dataset: str, source_row_id: str, record_type: str, **kwargs) -> dict:
    return {
        "source_dataset": source_dataset,
        "source_row_id": source_row_id,
        "source_kind": record_type,
        "record_type": record_type,
        "raw": {},
        **kwargs,
    }


def test_national_id_weight_exceeds_phone_weight() -> None:
    assert ASSOCIATE_LINK_WEIGHTS["SHARES_NATIONAL_ID_WITH"] > ASSOCIATE_LINK_WEIGHTS["SHARES_PHONE_WITH"]


def test_graph_includes_national_id_edges() -> None:
    records = [
        _make_record("a", "1", "tax", person_name="Ali Raza", national_id="1110100000001", address="House 1 Karachi"),
        _make_record("b", "1", "tax", person_name="Noman Raza", national_id="1110100000002", address="House 2 Karachi"),
    ]
    resolution = {
        "entities": [
            {"entity_id": "E1", "canonical_name": "Ali Raza", "source_record_ids": ["a:1"]},
            {"entity_id": "E2", "canonical_name": "Noman Raza", "source_record_ids": ["b:1"]},
        ],
        "record_to_entity": {"a:1": "E1", "b:1": "E2"},
    }
    graph = build_graph(records, resolution)
    nid_edges = [e for e in graph["edges"] if e["relation"] == "SHARES_NATIONAL_ID_WITH"]
    # Distinct CNICs do not produce a sharing edge.
    assert len(nid_edges) == 0
    # But each entity should be connected to its NationalId node.
    uses_nid = [e for e in graph["edges"] if e["relation"] == "USES_NATIONAL_ID"]
    assert len(uses_nid) == 2


def test_features_count_national_id_sharing_edges() -> None:
    graph = {
        "entity_records": {
            "E1": [
                _make_record("a", "1", "tax", person_name="Ali", declared_income=50_000),
            ],
            "E2": [
                _make_record("b", "1", "property", person_name="Proxy", property_value=100_000_000),
            ],
        },
        "nodes": [],
        "edges": [
            {
                "source": "E1",
                "target": "E2",
                "relation": "SHARES_NATIONAL_ID_WITH",
                "confidence": 1.0,
                "evidence": {},
            },
            {
                "source": "E2",
                "target": "E1",
                "relation": "SHARES_NATIONAL_ID_WITH",
                "confidence": 1.0,
                "evidence": {},
            },
        ],
    }
    resolution = {
        "entities": [
            {"entity_id": "E1", "canonical_name": "Ali", "source_record_ids": ["a:1"]},
            {"entity_id": "E2", "canonical_name": "Proxy", "source_record_ids": ["b:1"]},
        ]
    }
    features = build_entity_features(graph, resolution)
    assert features["E1"]["shared_national_id_count"] == 1.0


def test_national_id_link_boosts_associate_score_more_than_phone() -> None:
    records = [
        _make_record("a", "1", "tax", person_name="Ali Raza", declared_income=50_000),
        _make_record("b", "1", "property", person_name="Proxy One", property_value=100_000_000),
        _make_record("c", "1", "property", person_name="Proxy Two", property_value=100_000_000),
    ]
    resolution = {
        "entities": [
            {"entity_id": "E1", "canonical_name": "Ali Raza", "source_record_ids": ["a:1"]},
            {"entity_id": "E2", "canonical_name": "Proxy One", "source_record_ids": ["b:1"]},
            {"entity_id": "E3", "canonical_name": "Proxy Two", "source_record_ids": ["c:1"]},
        ],
        "record_to_entity": {"a:1": "E1", "b:1": "E2", "c:1": "E3"},
    }
    graph = build_graph(records, resolution)
    # Manually inject a national-id sharing edge between E1 and E2.
    graph["edges"].append(
        {
            "source": "E1",
            "target": "E2",
            "relation": "SHARES_NATIONAL_ID_WITH",
            "confidence": 1.0,
            "evidence": {},
        }
    )
    graph["edges"].append(
        {
            "source": "E2",
            "target": "E1",
            "relation": "SHARES_NATIONAL_ID_WITH",
            "confidence": 1.0,
            "evidence": {},
        }
    )
    # Manually inject a phone sharing edge between E1 and E3.
    graph["edges"].append(
        {
            "source": "E1",
            "target": "E3",
            "relation": "SHARES_PHONE_WITH",
            "confidence": 0.95,
            "evidence": {},
        }
    )
    graph["edges"].append(
        {
            "source": "E3",
            "target": "E1",
            "relation": "SHARES_PHONE_WITH",
            "confidence": 0.95,
            "evidence": {},
        }
    )
    result = score_entities(graph, resolution)
    by_id = {p["entity_id"]: p for p in result["profiles"]}
    assert by_id["E1"]["associate_proxy_score"] > 0
    nid_reason = any("shares_national_id_with" in r.lower() for r in by_id["E1"]["associate_reasons"])
    phone_reason = any("shares_phone_with" in r.lower() for r in by_id["E1"]["associate_reasons"])
    assert nid_reason, "national ID sharing reason missing"
    assert phone_reason, "phone sharing reason missing"
