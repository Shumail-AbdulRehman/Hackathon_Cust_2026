"""Benford's Law first-digit analysis for numeric columns."""

from __future__ import annotations

from typing import Any


BENFORD_EXPECTED = {
    1: 0.301,
    2: 0.176,
    3: 0.125,
    4: 0.097,
    5: 0.079,
    6: 0.067,
    7: 0.058,
    8: 0.051,
    9: 0.046,
}


def first_digit(value: Any) -> int | None:
    """Return the first non-zero digit of a positive number."""
    text = str(value or "").strip().replace(",", "")
    digits = "".join(ch for ch in text if ch.isdigit())
    for ch in digits:
        if ch != "0":
            return int(ch)
    return None


def benford_counts(values: list[Any]) -> dict[int, int]:
    """Count first non-zero digits for a list of values."""
    counts: dict[int, int] = {d: 0 for d in range(1, 10)}
    for value in values:
        digit = first_digit(value)
        if digit is not None:
            counts[digit] += 1
    return counts


def benford_mad(counts: dict[int, int]) -> tuple[float, dict[int, float]]:
    """Mean Absolute Deviation from Benford distribution.

    Returns the MAD and a per-digit absolute deviation map.
    """
    total = sum(counts.values())
    if total < 30:
        return 0.0, {d: 0.0 for d in range(1, 10)}
    observed = {d: counts[d] / total for d in range(1, 10)}
    deviations = {d: abs(observed[d] - BENFORD_EXPECTED[d]) for d in range(1, 10)}
    mad = sum(deviations.values()) / 9
    return mad, deviations


def benford_anomaly_score(mad: float) -> float:
    """Scale MAD to a 0-100 anomaly score."""
    if mad <= 0.004:
        return 0.0
    if mad <= 0.008:
        return 25.0
    if mad <= 0.012:
        return 50.0
    if mad <= 0.016:
        return 75.0
    return 100.0
