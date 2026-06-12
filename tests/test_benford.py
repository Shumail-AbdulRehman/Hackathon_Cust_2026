"""Tests for Benford's Law analysis."""

from __future__ import annotations


import pytest

from taxnet.benford import benford_anomaly_score, benford_counts, benford_mad, first_digit


def test_first_digit_extracts_leading_nonzero() -> None:
    assert first_digit("1234") == 1
    assert first_digit("0.045") == 4
    assert first_digit("9,999") == 9
    assert first_digit(0) is None
    assert first_digit("") is None


def test_benford_counts() -> None:
    values = ["123", "456", "789", "100", "0.023"]
    counts = benford_counts(values)
    assert counts[1] == 2  # 123 and 100
    assert counts[4] == 1
    assert counts[7] == 1
    assert counts[2] == 1
    assert sum(counts.values()) == 5


def test_benford_perfect_distribution() -> None:
    """A synthetic perfect Benford distribution should yield near-zero MAD."""
    counts = {d: int(1000 * expected) for d, expected in {
        1: 0.301,
        2: 0.176,
        3: 0.125,
        4: 0.097,
        5: 0.079,
        6: 0.067,
        7: 0.058,
        8: 0.051,
        9: 0.046,
    }.items()}
    mad, _ = benford_mad(counts)
    assert mad < 0.005


def test_benford_uniform_distribution_high_mad() -> None:
    counts = {d: 100 for d in range(1, 10)}
    mad, deviations = benford_mad(counts)
    assert mad > 0.05
    assert deviations[1] > 0.18


def test_small_sample_returns_zero_mad() -> None:
    counts = {d: 1 for d in range(1, 10)}
    mad, _ = benford_mad(counts)
    assert mad == 0.0


@pytest.mark.parametrize(
    "mad, score",
    [
        (0.0, 0.0),
        (0.006, 25.0),
        (0.010, 50.0),
        (0.014, 75.0),
        (0.020, 100.0),
    ],
)
def test_benford_anomaly_score_buckets(mad: float, score: float) -> None:
    assert benford_anomaly_score(mad) == score
