"""Load OpenSanctions target records into TaxNet-compatible dicts.

OpenSanctions publishes consolidated sanctions and PEP datasets. This loader
reads the simplified ``targets.simple.csv`` export and normalizes each target
name for downstream entity resolution.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl

from taxnet.normalization import normalize_name


def sanitize_name(value: object) -> str:
    """Normalize a raw name into a canonical lower-cased form."""
    return normalize_name(value)


def _split(value: object) -> list[str]:
    """Split a semicolon-delimited string into stripped, non-empty parts."""
    if value is None:
        return []
    return [part.strip() for part in str(value).split(";") if part.strip()]


def load_targets(path: Path | str) -> list[dict[str, Any]]:
    """Load and normalize OpenSanctions targets from a CSV file.

    Returns an empty list if the file is missing or does not contain the
    required columns ``id``, ``schema`` and ``name``.
    """
    path = Path(path)
    if not path.exists():
        return []

    df = pl.read_csv(path, infer_schema_length=0)
    required_columns = {"id", "schema", "name"}
    if not required_columns.issubset(df.columns):
        return []

    targets: list[dict[str, Any]] = []
    for row in df.to_dicts():
        raw_name = str(row.get("name") or "").strip()
        canonical_name = sanitize_name(raw_name)
        if not canonical_name:
            continue

        raw_aliases = _split(row.get("aliases"))
        aliases = [
            alias for alias in (sanitize_name(alias) for alias in raw_aliases) if alias and alias != canonical_name
        ]

        countries = [country.upper() for country in _split(row.get("countries"))]

        targets.append(
            {
                "id": row.get("id"),
                "schema": row.get("schema"),
                "name": canonical_name,
                "aliases": aliases,
                "countries": countries,
            }
        )

    return targets
