# taxnet/csv_upload.py
from __future__ import annotations

import csv
from io import BytesIO, TextIOWrapper
from pathlib import Path
from typing import BinaryIO

import polars as pl

MAX_ROWS_DEFAULT = 500_000


def parse_uploaded_csv(
    file_like: BinaryIO,
    filename: str,
    *,
    max_rows: int = MAX_ROWS_DEFAULT,
) -> list[dict[str, str]]:
    """Parse an uploaded CSV file into a list of plain dicts.

    Uses Polars for speed and falls back to csv.DictReader if Polars fails.
    Raises ValueError for unsupported formats or row limits exceeded.
    """
    suffix = Path(filename).suffix.lower()
    if suffix and suffix not in {".csv", ".tsv", ".txt"}:
        raise ValueError(f"Unsupported file extension: {suffix}")

    # Capture the entire stream in memory so it can be rewound between Polars
    # and the csv.DictReader fallback.
    full_bytes = file_like.read()
    file_like = BytesIO(full_bytes)

    sample_bytes = full_bytes[:8192]
    encoding = "utf-8"
    try:
        sample_text = sample_bytes.decode(encoding)
    except UnicodeDecodeError:
        encoding = "utf-8-sig"
        sample_text = sample_bytes.decode(encoding, errors="replace")

    delimiter = _sniff_delimiter(sample_text)

    def _row_limit_message() -> str:
        return (
            f"{filename} has more than {max_rows:,} rows. "
            "Please upload a smaller file or sample it first."
        )

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
            file_like.seek(0)
            text_io = TextIOWrapper(file_like, encoding=encoding)
            reader = csv.DictReader(text_io, delimiter=delimiter)
            rows = list(reader)
        except Exception:
            raise ValueError(f"Could not parse {filename}: {exc}") from exc
    else:
        rows = df.to_dicts()

    if len(rows) > max_rows:
        raise ValueError(_row_limit_message())

    if not rows:
        raise ValueError(f"{filename} contains no data rows.")

    return [{str(k): str(v) if v is not None else "" for k, v in row.items()} for row in rows]


def _sniff_delimiter(sample: str) -> str:
    counts = {",": sample.count(","), "\t": sample.count("\t"), ";": sample.count(";")}
    delimiter = max(counts, key=counts.get)
    return delimiter if counts[delimiter] > 0 else ","
