#!/usr/bin/env python3
"""Shared utilities for the server training pipeline (file1.py, file2.py, file3.py).

Provides idempotent downloads, checkpoint files, and safe JSONL I/O.
All helper functions are pure Python + stdlib where possible so they can be
imported without heavy ML dependencies.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def get_artifacts_dir() -> Path:
    """Return the root artifacts directory used by all server files."""
    return Path(__file__).resolve().parent / "server_artifacts"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def log(stage: str, message: str) -> None:
    """Print a prefixed log line."""
    print(f"[{stage}] {message}", flush=True)


# ---------------------------------------------------------------------------
# Idempotent downloads
# ---------------------------------------------------------------------------


def download_file(
    url: str,
    dest: Path,
    retries: int = 3,
    timeout: int = 120,
    stage: str = "download",
) -> None:
    """Download a URL to a local file with retries and resume support.

    The download is idempotent: if ``dest`` already exists and is complete,
    calling this function again will skip the download. If a previous download
    was interrupted, it resumes from the existing partial file using HTTP Range.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        existing_size = dest.stat().st_size if dest.exists() else 0
        headers: dict[str, str] = {"User-Agent": "Mozilla/5.0"}
        if existing_size > 0:
            headers["Range"] = f"bytes={existing_size}-"

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                # If the server returns 206 we append; otherwise overwrite.
                mode = "ab" if existing_size > 0 and resp.status == 206 else "wb"
                with open(dest, mode) as f:
                    while True:
                        block = resp.read(8192)
                        if not block:
                            break
                        f.write(block)
            return
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code in (404, 403):
                raise
            log(stage, f"  attempt {attempt}/{retries} failed: {exc}; retrying...")
        except Exception as exc:
            last_error = exc
            log(stage, f"  attempt {attempt}/{retries} failed: {exc}; retrying...")
        time.sleep(2**attempt)

    raise RuntimeError(f"Failed to download {url}: {last_error}")


def download_if_missing(
    url: str,
    dest: Path,
    force: bool = False,
    retries: int = 3,
    timeout: int = 120,
    stage: str = "download",
) -> bool:
    """Download ``url`` to ``dest`` only if ``dest`` does not exist.

    Returns True if a download happened, False if the file was already present.
    If ``force`` is True, delete the existing file and re-download.
    """
    if dest.exists() and not force:
        log(stage, f"  skipping {dest.name} (already exists)")
        return False
    if force and dest.exists():
        dest.unlink()
    download_file(url, dest, retries=retries, timeout=timeout, stage=stage)
    return True


# ---------------------------------------------------------------------------
# Checkpoints
# ---------------------------------------------------------------------------


def checkpoint_path(name: str) -> Path:
    """Return the path for a named checkpoint file."""
    cp_dir = get_artifacts_dir() / "checkpoints"
    cp_dir.mkdir(parents=True, exist_ok=True)
    return cp_dir / f"{name}.json"


def save_checkpoint(name: str, data: dict[str, Any] | None = None) -> None:
    """Write a checkpoint file indicating a stage completed successfully."""
    payload = {"completed": True}
    if data:
        payload.update(data)
    checkpoint_path(name).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_checkpoint(name: str) -> dict[str, Any] | None:
    """Load a checkpoint file if it exists, otherwise return None."""
    cp = checkpoint_path(name)
    if not cp.exists():
        return None
    try:
        return json.loads(cp.read_text(encoding="utf-8"))
    except Exception:
        return None


def is_checkpoint_complete(name: str) -> bool:
    """Return True if the named checkpoint exists and is marked complete."""
    data = load_checkpoint(name)
    return bool(data and data.get("completed"))


def clear_checkpoint(name: str) -> None:
    """Delete a checkpoint file."""
    cp = checkpoint_path(name)
    if cp.exists():
        cp.unlink()


# ---------------------------------------------------------------------------
# JSONL helpers
# ---------------------------------------------------------------------------


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file, skipping malformed lines."""
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    """Write a list of records to a JSONL file atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.replace(path)


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append a single record to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
