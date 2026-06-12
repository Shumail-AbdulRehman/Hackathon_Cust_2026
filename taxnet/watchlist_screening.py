"""Watchlist screening against OpenSanctions targets."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .normalization import alias_token_set, normalize_name, token_similarity


OPEN_SANCTIONS_MATCH_THRESHOLD = 0.85

# Re-use the token-to-target index when the same target list is screened repeatedly.
_TARGET_INDEX_CACHE: dict[tuple[int, int, str], dict[str, list[int]]] = {}


def score_name_similarity(left: str, right: str) -> float:
    """Return the normalized token-based similarity score for two names."""
    return token_similarity(normalize_name(left), normalize_name(right))


def _candidate_names(entity: dict[str, Any]) -> list[str]:
    """Return the normalized canonical name plus unique normalized aliases.

    Names that rely on single-letter initials (e.g. "m ahmed") are too
    ambiguous for watchlist matching and are skipped unless a fuller alias is
    available.
    """
    names: list[str] = []
    canonical = normalize_name(entity.get("canonical_name", ""))
    if canonical and all(len(token) > 1 for token in canonical.split()):
        names.append(canonical)
    for alias in entity.get("aliases", []):
        norm = normalize_name(alias)
        if norm and norm not in names and all(len(token) > 1 for token in norm.split()):
            names.append(norm)
    return names


def _target_name_tokens(target: dict[str, Any]) -> set[str]:
    """Return the expanded token set for a target's canonical name and aliases."""
    tokens: set[str] = set()
    for name in [target["name"], *target.get("aliases", [])]:
        tokens.update(alias_token_set(name))
    return tokens


def _index_targets(targets: list[dict[str, Any]]) -> dict[str, list[int]]:
    """Build an inverted index from alias-token to target indices."""
    cache_key = (
        id(targets),
        len(targets),
        targets[0].get("id", "") if targets else "",
    )
    if cache_key in _TARGET_INDEX_CACHE:
        return _TARGET_INDEX_CACHE[cache_key]

    index: dict[str, list[int]] = defaultdict(list)
    for idx, target in enumerate(targets):
        for token in _target_name_tokens(target):
            index[token].append(idx)

    _TARGET_INDEX_CACHE[cache_key] = index
    return index


def _candidate_target_indices(entity_names: list[str], index: dict[str, list[int]]) -> set[int]:
    """Return target indices that share enough tokens with any entity name."""
    candidates: set[int] = set()
    for ename in entity_names:
        entity_tokens = alias_token_set(ename)
        if not entity_tokens:
            continue
        # High-similarity matches almost always overlap on all but at most one token.
        min_overlap = max(1, len(entity_tokens) - 1)
        counts: Counter[int] = Counter()
        for token in entity_tokens:
            counts.update(index.get(token, ()))
        candidates.update(idx for idx, count in counts.items() if count >= min_overlap)
    return candidates


def match_entity(
    entity: dict[str, Any],
    targets: list[dict[str, Any]],
    threshold: float = OPEN_SANCTIONS_MATCH_THRESHOLD,
) -> dict[str, Any] | None:
    """Return the best watchlist match for a resolved entity, or None."""
    entity_names = _candidate_names(entity)
    if not entity_names or not targets:
        return None

    index = _index_targets(targets)
    candidate_indices = _candidate_target_indices(entity_names, index)

    best_match: dict[str, Any] | None = None
    best_score = 0.0

    for target_idx in candidate_indices:
        target = targets[target_idx]
        target_name = target["name"]
        for tname in [target_name, *target.get("aliases", [])]:
            for ename in entity_names:
                score = score_name_similarity(ename, tname)
                if score > best_score:
                    best_score = score
                    best_match = {
                        "target_id": target["id"],
                        "target_name": target_name,
                        "target_schema": target.get("schema", ""),
                        "target_countries": target.get("countries", []),
                        "matched_alias": tname if tname != target_name else "",
                        "similarity": round(score, 3),
                    }

    if best_match is not None and best_score >= threshold:
        return best_match
    return None


def screen_entities(
    entities: list[dict[str, Any]],
    targets: list[dict[str, Any]],
    threshold: float = OPEN_SANCTIONS_MATCH_THRESHOLD,
) -> dict[str, dict[str, Any]]:
    """Return a mapping of entity_id to the best watchlist match."""
    results: dict[str, dict[str, Any]] = {}
    for entity in entities:
        match = match_entity(entity, targets, threshold=threshold)
        if match:
            results[entity["entity_id"]] = match
    return results
