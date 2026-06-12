"""Tests for OpenSanctions watchlist screening."""

from __future__ import annotations

from taxnet.watchlist_screening import match_entity, screen_entities, score_name_similarity


def test_score_name_similarity_exact() -> None:
    assert score_name_similarity("ali raza", "ali raza") == 1.0


def test_score_name_similarity_partial() -> None:
    score = score_name_similarity("ahmed ali khan", "ahmed ali")
    assert 0.5 < score < 1.0


def test_match_entity_returns_best_match() -> None:
    targets = [
        {"id": "t1", "name": "ali raza", "aliases": [], "countries": ["PK"], "schema": "Person"},
        {"id": "t2", "name": "sara malik", "aliases": [], "countries": ["PK"], "schema": "Person"},
    ]
    entity = {"canonical_name": "ali raza", "aliases": []}
    match = match_entity(entity, targets, threshold=0.85)
    assert match is not None
    assert match["target_id"] == "t1"
    assert match["target_name"] == "ali raza"
    assert match["target_schema"] == "Person"
    assert match["target_countries"] == ["PK"]
    assert match["matched_alias"] == ""
    assert match["similarity"] == 1.0


def test_match_entity_respects_threshold() -> None:
    targets = [{"id": "t1", "name": "sara malik", "aliases": [], "countries": [], "schema": "Person"}]
    entity = {"canonical_name": "ali raza", "aliases": []}
    assert match_entity(entity, targets, threshold=0.9) is None


def test_screen_entities_maps_by_entity_id() -> None:
    targets = [
        {"id": "t1", "name": "ali raza", "aliases": [], "countries": ["PK"], "schema": "Person"},
    ]
    entities = [
        {"entity_id": "E1", "canonical_name": "ali raza", "aliases": []},
        {"entity_id": "E2", "canonical_name": "sara malik", "aliases": []},
    ]
    results = screen_entities(entities, targets, threshold=0.85)
    assert set(results.keys()) == {"E1"}
    assert results["E1"]["target_id"] == "t1"
