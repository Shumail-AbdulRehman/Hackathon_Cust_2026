"""Sample headers and first rows from all data files for quick inspection."""

from __future__ import annotations

import csv
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path("data")


def sample_csv(path: Path) -> None:
    print(f"\n{'='*60}")
    print(f"CSV: {path}")
    print("=" * 60)
    try:
        with path.open(encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            print(f"Headers: {headers}")
            for i, row in enumerate(reader):
                if i >= 3:
                    break
                print(f"Row {i+1}: {row}")
    except Exception as exc:
        print(f"Error reading CSV: {exc}")


def sample_txt(path: Path) -> None:
    print(f"\n{'='*60}")
    print(f"TXT: {path}")
    print("=" * 60)
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in lines[:8]:
            print(line[:200])
    except Exception as exc:
        print(f"Error reading TXT: {exc}")


def sample_excel(path: Path) -> None:
    print(f"\n{'='*60}")
    print(f"Excel: {path}")
    print("=" * 60)
    try:
        xl = pd.ExcelFile(path)
        print(f"Sheets: {xl.sheet_names}")
        df = xl.parse(xl.sheet_names[0])
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print(df.head(3).to_string())
    except Exception as exc:
        print(f"Error reading Excel: {exc}")


def sample_pdf(path: Path) -> None:
    print(f"\n{'='*60}")
    print(f"PDF: {path}")
    print("=" * 60)
    try:
        text = subprocess.run(
            ["pdftotext", "-f", "1", "-l", "2", str(path), "-"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        ).stdout
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines[:15]:
            print(line[:200])
    except Exception as exc:
        print(f"Error reading PDF: {exc}")


def main() -> None:
    files = sorted(p for p in ROOT.rglob("*") if p.is_file())
    for path in files:
        suffix = path.suffix.lower()
        if suffix == ".csv":
            sample_csv(path)
        elif suffix == ".txt":
            sample_txt(path)
        elif suffix in {".xlsx", ".xls"}:
            sample_excel(path)
        elif suffix == ".pdf":
            sample_pdf(path)
        elif suffix == ".md":
            pass
        elif ".part" in suffix:
            pass
        else:
            print(f"\n{'='*60}")
            print(f"Unknown: {path}")
            print("=" * 60)


if __name__ == "__main__":
    main()
