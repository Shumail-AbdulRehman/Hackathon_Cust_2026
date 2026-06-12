"""Tests for optional ANN-based blocking with BlockingPy."""

from __future__ import annotations

import pytest

from taxnet.ann_blocking import ann_candidate_pairs, HAS_BLOCKINGPY
from taxnet.entity_resolution import resolve_entities
from taxnet.types import RecordFingerprint


def _make_fp(record_id: str, name: str, address: str = "", city: str = "") -> RecordFingerprint:
    return RecordFingerprint(
        record_id=record_id,
        person_name=name,
        norm_name=name.lower(),
        address=address,
        norm_address=address.lower(),
        phone="",
        national_id="",
        city=city,
        block_key="",
        source_dataset="test",
        source_kind="person",
        truth_person_id="",
    )


@pytest.mark.skipif(not HAS_BLOCKINGPY, reason="BlockingPy not installed")
def test_ann_candidate_pairs_finds_similar_names() -> None:
    fps = [
        _make_fp("r1", "Muhammad Ahmed", "House 1 Lahore", "Lahore"),
        _make_fp("r2", "Muhammed Ahmed", "House 2 Lahore", "Lahore"),
        _make_fp("r3", "Ali Raza", "House 10 Karachi", "Karachi"),
    ]
    pairs = ann_candidate_pairs(fps, k_search=2)
    # ANN should surface the two similar names as candidates.
    assert ("r1", "r2") in pairs or ("r2", "r1") in pairs


@pytest.mark.skipif(not HAS_BLOCKINGPY, reason="BlockingPy not installed")
def test_ann_candidate_pairs_returns_empty_for_small_input() -> None:
    fps = [_make_fp("r1", "Muhammad Ahmed", "Lahore", "Lahore")]
    pairs = ann_candidate_pairs(fps)
    assert pairs == set()


def test_ann_candidate_pairs_returns_empty_when_unavailable(monkeypatch) -> None:
    monkeypatch.setattr("taxnet.ann_blocking.HAS_BLOCKINGPY", False)
    fps = [
        _make_fp("r1", "Muhammad Ahmed", "Lahore", "Lahore"),
        _make_fp("r2", "Muhammed Ahmed", "Lahore", "Lahore"),
    ]
    pairs = ann_candidate_pairs(fps)
    assert pairs == set()


@pytest.mark.skipif(not HAS_BLOCKINGPY, reason="BlockingPy not installed")
def test_resolve_entities_with_ann_blocking() -> None:
    records = [
        {
            "person_name": "Muhammad Ahmed",
            "address": "House 1 Lahore",
            "phone": "",
            "national_id": "",
            "source_dataset": "tax.csv",
            "source_row_id": "1",
            "source_kind": "person",
            "truth_person_id": "p1",
        },
        {
            "person_name": "Muhammed Ahmed",
            "address": "House 2 Lahore",
            "phone": "",
            "national_id": "",
            "source_dataset": "tax.csv",
            "source_row_id": "2",
            "source_kind": "person",
            "truth_person_id": "p1",
        },
        {
            "person_name": "Ali Raza",
            "address": "House 10 Karachi",
            "phone": "",
            "national_id": "",
            "source_dataset": "tax.csv",
            "source_row_id": "3",
            "source_kind": "person",
            "truth_person_id": "p2",
        },
    ]
    resolution = resolve_entities(records, parallel=False, use_ann_blocking=True)
    assert len(resolution["entities"]) < len(records)
    # The two similar Ahmed records should merge into one entity.
    assert len(resolution["entities"]) == 2


def test_resolve_entities_without_ann_blocking_still_works() -> None:
    records = [
        {
            "person_name": "Muhammad Ahmed",
            "address": "House 1 Lahore",
            "phone": "",
            "national_id": "35201-1234567-1",
            "source_dataset": "tax.csv",
            "source_row_id": "1",
            "source_kind": "person",
            "truth_person_id": "p1",
        },
        {
            "person_name": "M Ahmed",
            "address": "House 1 Lahore",
            "phone": "",
            "national_id": "35201-1234567-1",
            "source_dataset": "tax.csv",
            "source_row_id": "2",
            "source_kind": "person",
            "truth_person_id": "p1",
        },
    ]
    resolution = resolve_entities(records, parallel=False, use_ann_blocking=False)
    assert len(resolution["entities"]) == 1
