# taxnet/csv_upload.py
from __future__ import annotations

import csv
from io import BytesIO, TextIOWrapper
from pathlib import Path
from typing import Any, BinaryIO

import polars as pl

MAX_ROWS_DEFAULT = 500_000


def parse_uploaded_csv(
    file_like: BinaryIO,
    filename: str,
    *,
    max_rows: int = MAX_ROWS_DEFAULT,
) -> list[dict[str, Any]]:
    """Parse an uploaded CSV file into a list of plain dicts.

    Uses Polars for speed and falls back to csv.DictReader if Polars fails.
    Raises ValueError for unsupported formats or row limits exceeded.
    """
    suffix = Path(filename).suffix.lower()
    if suffix and suffix not in {".csv", ".tsv", ".txt"}:
        raise ValueError(f"Unsupported file extension: {suffix}")

    sample_bytes = file_like.read(8192)
    file_like = BytesIO(sample_bytes + file_like.read())

    encoding = "utf-8"
    try:
        sample_text = sample_bytes.decode(encoding)
    except UnicodeDecodeError:
        encoding = "utf-8-sig"
        sample_text = sample_bytes.decode(encoding, errors="replace")

    delimiter = _sniff_delimiter(sample_text)

    try:
        df = pl.read_csv(
            file_like,
            encoding=encoding,
            separator=delimiter,
            infer_schema=False,
            try_parse_dates=False,
            n_rows=max_rows + 1,
        )
    except Exception as exc:
        try:
            text_io = TextIOWrapper(file_like, encoding=encoding)
            reader = csv.DictReader(text_io, delimiter=delimiter)
            rows = list(reader)
        except Exception:
            raise ValueError(f"Could not parse {filename}: {exc}") from exc
    else:
        if len(df) > max_rows:
            raise ValueError(
                f"{filename} has more than {max_rows:,} rows. "
                "Please upload a smaller file or sample it first."
            )
        rows = df.to_dicts()

    if not rows:
        raise ValueError(f"{filename} contains no data rows.")

    return [{str(k): str(v) if v is not None else "" for k, v in row.items()} for row in rows]


def _sniff_delimiter(sample: str) -> str:
    counts = {",": sample.count(","), "\t": sample.count("\t"), ";": sample.count(";")}
    delimiter = max(counts, key=counts.get)
    return delimiter if counts[delimiter] > 0 else ","
