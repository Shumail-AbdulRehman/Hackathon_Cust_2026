"""Approximate-nearest-neighbor blocking for entity resolution.

Uses BlockingPy (FAISS-CPU, no GPU required) to build an HNSW index over
character-shingle embeddings of a blocking text. Much faster than exhaustive
key-based blocking for large datasets with noisy names/addresses.

This module is optional: if BlockingPy is not installed, the function falls back
to returning an empty set and the caller can use traditional blocking.
"""

from __future__ import annotations


from .types import RecordFingerprint

try:
    from blockingpy import Blocker

    HAS_BLOCKINGPY = True
except Exception:  # pragma: no cover - optional dependency
    HAS_BLOCKINGPY = False


def _build_blocking_text(fp: RecordFingerprint) -> str:
    """Combine name, city, and address into a single blocking string."""
    parts = [fp.person_name, fp.city, fp.address]
    return " ".join(part for part in parts if part).strip()


def ann_candidate_pairs(
    fingerprints: list[RecordFingerprint],
    k_search: int = 10,
    hnsw_M: int = 32,
    hnsw_ef_construction: int = 200,
    hnsw_ef_search: int = 200,
) -> set[tuple[str, str]]:
    """Return candidate record-id pairs using ANN blocking.

    Parameters match the user's BlockingPy + FAISS-HNSW configuration. The
    shingle encoder is CPU-only and requires no GPU.
    """
    if not HAS_BLOCKINGPY:
        return set()
    if len(fingerprints) < 2:
        return set()

    texts = [_build_blocking_text(fp) for fp in fingerprints]
    record_ids = [fp.record_id for fp in fingerprints]

    try:
        import pandas as pd
    except Exception:  # pragma: no cover
        return set()

    x_series = pd.Series(texts)

    control_txt = {
        "encoder": "shingle",
        "shingle": {
            "n_shingles": 2,
            "max_features": 5000,
            "lowercase": True,
            "strip_non_alphanum": True,
        },
    }

    control_ann = {
        "faiss": {
            "index_type": "hnsw",
            "distance": "cosine",
            "k_search": min(k_search, len(fingerprints) - 1),
            "hnsw_M": hnsw_M,
            "hnsw_ef_construction": hnsw_ef_construction,
            "hnsw_ef_search": hnsw_ef_search,
        }
    }

    blocker = Blocker()
    result = blocker.block(
        x=x_series,
        ann="faiss",
        control_txt=control_txt,
        control_ann=control_ann,
        verbose=0,
    )

    candidates: set[tuple[str, str]] = set()
    for _, row in result.result.iterrows():
        x = int(row["x"])
        y = int(row["y"])
        if x == y:
            continue
        left = record_ids[x]
        right = record_ids[y]
        if left == right:
            continue
        # Canonical ordering.
        if left > right:
            left, right = right, left
        candidates.add((left, right))

    return candidates
