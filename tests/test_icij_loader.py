"""Tests for the ICIJ Offshore Leaks loader and pipeline integration."""

from __future__ import annotations

from pathlib import Path

import pytest

from taxnet.graph_engine import build_graph
from taxnet.ingestion import canonicalize_datasets
from taxnet.loaders.icij_loader import DATA_DIR, build_icij_datasets
from taxnet.pipeline import run_pipeline


def test_data_dir_exists() -> None:
    assert DATA_DIR.exists(), f"ICIJ data dir not found at {DATA_DIR}"
    for filename in [
        "nodes-entities.csv",
        "nodes-officers.csv",
        "nodes-intermediaries.csv",
        "nodes-addresses.csv",
        "nodes-others.csv",
        "relationships.csv",
    ]:
        assert (DATA_DIR / filename).exists(), f"Missing ICIJ file: {filename}"


def test_build_icij_datasets_sample() -> None:
    datasets = build_icij_datasets(max_entities=50, seed=42, hop_radius=1)
    assert "icij-offshore-leaks" in datasets
    records = datasets["icij-offshore-leaks"]
    assert len(records) > 0

    for record in records:
        assert record["source_row_id"].startswith("icij-")
        assert record["_kind"] == "offshore_entity"
        assert record.get("person_name")
        assert record.get("offshore_entity_name")
        assert record.get("national_id")
        assert record.get("offshore_relationship")


def test_canonicalize_offshore_entity() -> None:
    datasets = build_icij_datasets(max_entities=10, seed=42, hop_radius=1)
    records, profiles = canonicalize_datasets(datasets)
    assert len(records) > 0

    profile = profiles[0]
    assert profile["detected_kind"] == "offshore_entity"

    for record in records:
        assert record["record_type"] == "offshore_entity"
        assert "offshore_entity_name" in record
        assert "offshore_jurisdiction" in record


def test_graph_build_offshore_entities() -> None:
    datasets = build_icij_datasets(max_entities=10, seed=42, hop_radius=1)
    canonical_records, _ = canonicalize_datasets(datasets)

    # Minimal identity resolution: group by national_id.
    from taxnet.entity_resolution import resolve_entities

    resolution = resolve_entities(canonical_records)
    graph = build_graph(canonical_records, resolution)

    node_types = {node["type"] for node in graph["nodes"]}
    assert "Person" in node_types
    assert "OffshoreEntity" in node_types

    relations = {edge["relation"] for edge in graph["edges"]}
    assert "LINKED_TO_OFFSHORE_ENTITY" in relations


def test_pipeline_icij_small_sample() -> None:
    datasets = build_icij_datasets(max_entities=20, seed=42, hop_radius=1)
    result = run_pipeline(datasets=datasets, use_ml=False)
    assert result["mode"] == "uploaded"
    assert len(result["scoring"]["profiles"]) > 0
    assert result["timing_ms"]["total"] > 0
