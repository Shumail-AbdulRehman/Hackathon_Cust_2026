"""Entity resolution for noisy Pakistani civic data."""

from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from itertools import combinations
from typing import Any

from .normalization import (
    address_block,
    city_hint,
    first_initial,
    initials_compatible,
    ngram_embedding_similarity,
    normalize_address,
    normalize_name,
    normalize_national_id,
    normalize_phone,
    phonetic_similarity,
    sequence_score,
    surname,
    token_similarity,
)


@dataclass
class RecordFingerprint:
    record_id: str
    person_name: str
    norm_name: str
    address: str
    norm_address: str
    phone: str
    national_id: str
    city: str
    block_key: str
    source_dataset: str
    source_kind: str
    truth_person_id: str


class UnionFind:
    def __init__(self, items: list[str]) -> None:
        self.parent = {item: item for item in items}

    def find(self, item: str) -> str:
        parent = self.parent[item]
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, left: str, right: str) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left != root_right:
            self.parent[root_right] = root_left


def fingerprint(record: dict[str, Any]) -> RecordFingerprint:
    source_ref = f"{record['source_dataset']}:{record['source_row_id']}"
    name = str(record.get("person_name") or "")
    address = str(record.get("address") or "")
    phone = normalize_phone(record.get("phone", ""))
    national_id = normalize_national_id(record.get("national_id", ""))
    return RecordFingerprint(
        record_id=source_ref,
        person_name=name,
        norm_name=normalize_name(name),
        address=address,
        norm_address=normalize_address(address),
        phone=phone,
        national_id=national_id,
        city=city_hint(address),
        block_key=address_block(address),
        source_dataset=record["source_dataset"],
        source_kind=record["source_kind"],
        truth_person_id=str(record.get("truth_person_id") or ""),
    )


def should_compare(left: RecordFingerprint, right: RecordFingerprint) -> bool:
    if left.record_id == right.record_id:
        return False
    if left.national_id and right.national_id and left.national_id == right.national_id:
        return True
    if left.phone and right.phone and left.phone == right.phone:
        return True
    if left.city and right.city and left.city == right.city and surname(left.norm_name) == surname(right.norm_name):
        return True
    if left.block_key and right.block_key and left.block_key == right.block_key:
        return True
    if initials_compatible(left.norm_name, right.norm_name) and surname(left.norm_name) == surname(right.norm_name):
        return True
    if (
        left.city
        and right.city
        and left.city == right.city
        and first_initial(left.norm_name)
        and first_initial(left.norm_name) == first_initial(right.norm_name)
    ):
        return True
    return False


def asset_range_key(fp: RecordFingerprint) -> str | None:
    surname_value = surname(fp.norm_name)
    if fp.city and surname_value:
        return f"asset_city_surname:{fp.city}:{surname_value}"
    return None


def blocking_keys(fp: RecordFingerprint) -> list[str]:
    keys = []
    if fp.national_id:
        keys.append(f"national_id:{fp.national_id}")
    if fp.phone:
        keys.append(f"phone:{fp.phone}")
    name_surname = surname(fp.norm_name)
    if fp.city and name_surname:
        keys.append(f"city_surname:{fp.city}:{name_surname}")
    if fp.block_key:
        keys.append(f"address:{fp.block_key}")
    if first_initial(fp.norm_name) and name_surname:
        keys.append(f"initial_surname:{first_initial(fp.norm_name)}:{name_surname}")
    if fp.city and first_initial(fp.norm_name):
        keys.append(f"city_first:{fp.city}:{first_initial(fp.norm_name)}")
    asset_key = asset_range_key(fp)
    if asset_key:
        keys.append(asset_key)
    return keys


def candidate_pairs(fingerprints: list[RecordFingerprint]) -> set[tuple[str, str]]:
    index: dict[str, list[str]] = defaultdict(list)
    by_id = {fp.record_id: fp for fp in fingerprints}
    pairs: set[tuple[str, str]] = set()
    for fp in fingerprints:
        for key in blocking_keys(fp):
            index[key].append(fp.record_id)
    for record_ids in index.values():
        if len(record_ids) < 2:
            continue
        for left, right in combinations(sorted(set(record_ids)), 2):
            left_fp = by_id[left]
            right_fp = by_id[right]
            if should_compare(left_fp, right_fp):
                pairs.add((left, right))
    return pairs


def compare_records(left: RecordFingerprint, right: RecordFingerprint) -> dict[str, Any]:
    token_name_score = token_similarity(left.norm_name, right.norm_name)
    phonetic_name_score = phonetic_similarity(left.norm_name, right.norm_name)
    embedding_name_score = ngram_embedding_similarity(left.norm_name, right.norm_name)
    name_score = max(token_name_score, phonetic_name_score * 0.92, embedding_name_score * 0.9)
    address_score = sequence_score(left.norm_address, right.norm_address)
    same_phone = bool(left.phone and right.phone and left.phone == right.phone)
    same_national_id = bool(left.national_id and right.national_id and left.national_id == right.national_id)
    same_city = bool(left.city and right.city and left.city == right.city)
    initial_ok = initials_compatible(left.norm_name, right.norm_name)
    same_surname = bool(surname(left.norm_name) and surname(left.norm_name) == surname(right.norm_name))
    same_first_initial = bool(first_initial(left.norm_name) and first_initial(left.norm_name) == first_initial(right.norm_name))

    if initial_ok and same_surname:
        name_score = max(name_score, 0.82)
    if same_first_initial and same_surname and address_score >= 0.82:
        name_score = max(name_score, 0.86)

    phone_score = 1.0 if same_phone else 0.0
    city_score = 1.0 if same_city else 0.0
    national_id_score = 1.0 if same_national_id else 0.0
    initial_bonus = 0.08 if initial_ok and same_surname else 0.0
    if initial_ok and same_surname and address_score >= 0.7:
        initial_bonus += 0.16
    if same_first_initial and same_surname and address_score >= 0.86:
        initial_bonus = max(initial_bonus, 0.18)
    if address_score >= 0.9 and name_score >= 0.72:
        initial_bonus = max(initial_bonus, 0.1)
    if address_score >= 0.9 and name_score >= 0.88 and same_city:
        initial_bonus = max(initial_bonus, 0.14)

    score = (
        name_score * 0.48
        + address_score * 0.22
        + phone_score * 0.18
        + city_score * 0.04
        + national_id_score * 0.40
        + initial_bonus
    )

    if same_national_id:
        score = max(score, 0.96)

    # A shared phone/address alone can indicate relatives or proxies, not the same person.
    if name_score < 0.42 and not (initial_ok and same_surname):
        score = min(score, 0.68)

    confidence = round(max(0.0, min(1.0, score)) * 100, 1)
    reasons = []
    if same_national_id:
        reasons.append("same national ID")
    if name_score >= 0.82:
        reasons.append("high name similarity")
    elif initial_ok and same_surname:
        reasons.append("compatible initials and surname")
    elif phonetic_name_score >= 0.5:
        reasons.append("phonetic name similarity")
    elif embedding_name_score >= 0.68:
        reasons.append("semantic n-gram name similarity")
    if address_score >= 0.78:
        reasons.append("high address similarity")
    if same_phone:
        reasons.append("same phone number")
    if same_city:
        reasons.append("same city")
    if not reasons:
        reasons.append("weak partial similarity")

    decision = "match" if confidence >= 72 else "possible" if confidence >= 58 else "reject"
    return {
        "left": left.record_id,
        "right": right.record_id,
        "confidence": confidence,
        "decision": decision,
        "features": {
            "name_score": round(name_score, 3),
            "token_name_score": round(token_name_score, 3),
            "phonetic_name_score": round(phonetic_name_score, 3),
            "ngram_embedding_score": round(embedding_name_score, 3),
            "address_score": round(address_score, 3),
            "same_phone": same_phone,
            "same_national_id": same_national_id,
            "same_city": same_city,
            "initials_compatible": initial_ok,
            "same_first_initial": same_first_initial,
            "same_surname": same_surname,
        },
        "reasons": reasons,
    }


_PAIR_LOOKUP: dict[str, RecordFingerprint] = {}


def _compare_pair(pair: tuple[str, str]) -> dict[str, Any]:
    """Standalone comparator for process-pool parallelism."""
    left_id, right_id = pair
    left = _PAIR_LOOKUP.get(left_id)
    right = _PAIR_LOOKUP.get(right_id)
    if left is None or right is None:
        return {"left": left_id, "right": right_id, "decision": "reject", "confidence": 0.0}
    return compare_records(left, right)


def _exact_merge_groups(fingerprints: list[RecordFingerprint]) -> list[tuple[str, str]]:
    """Return pairs that should be merged immediately based on exact IDs."""
    by_national_id: dict[str, list[str]] = defaultdict(list)
    by_phone: dict[str, list[str]] = defaultdict(list)
    for fp in fingerprints:
        if fp.national_id:
            by_national_id[fp.national_id].append(fp.record_id)
        if fp.phone:
            by_phone[fp.phone].append(fp.record_id)

    pairs: set[tuple[str, str]] = set()
    for ids in by_national_id.values():
        for left, right in combinations(sorted(ids), 2):
            pairs.add((left, right))
    for ids in by_phone.values():
        for left, right in combinations(sorted(ids), 2):
            pairs.add((left, right))
    return list(pairs)


def resolve_entities(
    records: list[dict[str, Any]],
    parallel: bool = True,
    max_workers: int | None = None,
) -> dict[str, Any]:
    fingerprints = [fingerprint(record) for record in records if record.get("person_name")]
    by_id = {fp.record_id: fp for fp in fingerprints}
    uf = UnionFind([fp.record_id for fp in fingerprints])
    comparisons = len(fingerprints) * (len(fingerprints) - 1) // 2

    # Phase 1: exact-match merges (national_id / phone) — no fuzzy comparison needed.
    for left_id, right_id in _exact_merge_groups(fingerprints):
        uf.union(left_id, right_id)

    # Phase 2: blocking + fuzzy comparison on remaining candidates.
    pairs = candidate_pairs(fingerprints)
    candidates = len(pairs)
    matches: list[dict[str, Any]] = []
    possibles: list[dict[str, Any]] = []

    pair_list = sorted(pairs)
    results: list[dict[str, Any]] = []
    if parallel and len(pair_list) > 200:
        global _PAIR_LOOKUP
        _PAIR_LOOKUP = by_id
        try:
            workers = max_workers or min(8, max(2, (len(pair_list) // 500) + 1))
            with ProcessPoolExecutor(max_workers=workers) as executor:
                results = list(
                    executor.map(_compare_pair, pair_list, chunksize=max(1, len(pair_list) // workers // 4))
                )
        finally:
            _PAIR_LOOKUP = {}
    else:
        results = [compare_records(by_id[left_id], by_id[right_id]) for left_id, right_id in pair_list]

    for result in results:
        if result["decision"] == "match":
            uf.union(result["left"], result["right"])
            matches.append(result)
        elif result["decision"] == "possible":
            possibles.append(result)

    clusters: dict[str, list[str]] = {}
    for fp in fingerprints:
        root = uf.find(fp.record_id)
        clusters.setdefault(root, []).append(fp.record_id)

    sorted_clusters = sorted(clusters.values(), key=lambda ids: (-len(ids), ids[0]))
    record_to_entity: dict[str, str] = {}
    entities = []
    for idx, record_ids in enumerate(sorted_clusters, start=1):
        entity_id = f"ENT-{idx:04d}"
        fps = [by_id[record_id] for record_id in record_ids]
        names = [fp.person_name for fp in fps if fp.person_name]
        canonical_name = sorted(names, key=lambda name: (-len(normalize_name(name).split()), -len(name), name))[0]
        addresses = sorted({fp.address for fp in fps if fp.address})
        phones = sorted({fp.phone for fp in fps if fp.phone})
        truth_ids = sorted({fp.truth_person_id for fp in fps if fp.truth_person_id})
        for record_id in record_ids:
            record_to_entity[record_id] = entity_id
        entities.append(
            {
                "entity_id": entity_id,
                "canonical_name": canonical_name,
                "source_record_ids": sorted(record_ids),
                "addresses": addresses,
                "phones": phones,
                "truth_person_ids": truth_ids,
            }
        )

    metrics = evaluate_pairwise(fingerprints, record_to_entity)
    possibles.sort(key=lambda item: item["confidence"], reverse=True)
    return {
        "entities": entities,
        "record_to_entity": record_to_entity,
        "matches": matches,
        "possible_matches": possibles[:100],
        "resolution_metrics": metrics,
        "runtime_stats": {
            "records": len(fingerprints),
            "all_pairs": comparisons,
            "candidate_pairs_after_blocking": candidates,
            "blocking_reduction_pct": round((1 - (candidates / comparisons)) * 100, 2) if comparisons else 0,
        },
    }


def evaluate_pairwise(fingerprints: list[RecordFingerprint], record_to_entity: dict[str, str]) -> dict[str, Any]:
    truth_available = all(fp.truth_person_id for fp in fingerprints)
    if not truth_available or len(fingerprints) < 2:
        return {"available": False, "reason": "ground truth labels not present"}

    true_positive = false_positive = false_negative = true_negative = 0
    false_positive_examples = []
    false_negative_examples = []
    for left, right in combinations(fingerprints, 2):
        same_truth = left.truth_person_id == right.truth_person_id
        same_pred = record_to_entity.get(left.record_id) == record_to_entity.get(right.record_id)
        if same_truth and same_pred:
            true_positive += 1
        elif not same_truth and same_pred:
            false_positive += 1
            if len(false_positive_examples) < 10:
                false_positive_examples.append(pair_example(left, right, record_to_entity))
        elif same_truth and not same_pred:
            false_negative += 1
            if len(false_negative_examples) < 10:
                false_negative_examples.append(pair_example(left, right, record_to_entity))
        else:
            true_negative += 1
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "available": True,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "true_positive_pairs": true_positive,
        "false_positive_pairs": false_positive,
        "false_negative_pairs": false_negative,
        "true_negative_pairs": true_negative,
        "false_positive_examples": false_positive_examples,
        "false_negative_examples": false_negative_examples,
    }


def pair_example(
    left: RecordFingerprint,
    right: RecordFingerprint,
    record_to_entity: dict[str, str],
) -> dict[str, Any]:
    return {
        "left": left.record_id,
        "right": right.record_id,
        "left_name": left.person_name,
        "right_name": right.person_name,
        "left_entity": record_to_entity.get(left.record_id),
        "right_entity": record_to_entity.get(right.record_id),
        "left_truth": left.truth_person_id,
        "right_truth": right.truth_person_id,
    }
