"""Tests for the live cust-csv demo script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_demo_cust_csv_creates_report() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/demo_cust_csv.py", "--no-server"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    report = Path("demo_cust_csv_report.json")
    assert report.exists()
    data = json.loads(report.read_text())
    assert "flagged" in data
    assert "high" in data
    assert "medium" in data
    assert "low" in data
