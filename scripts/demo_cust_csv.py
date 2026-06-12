"""Run TaxNet on the real Pakistan-shaped CSVs in data/cust-csv/."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from taxnet.pipeline import run_pipeline


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def discover_datasets(input_dir: Path) -> dict[str, list[dict[str, str]]]:
    datasets: dict[str, list[dict[str, str]]] = {}
    for path in sorted(input_dir.glob("*.csv")):
        if path.name.lower() == "readme.md":
            continue
        datasets[path.name] = load_csv(path)
    return datasets


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TaxNet on data/cust-csv/")
    parser.add_argument("--input-dir", type=Path, default=Path("data/cust-csv"))
    parser.add_argument("--no-server", action="store_true", help="Do not start the web server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--use-ann-blocking", action="store_true", help="Use ANN blocking for entity resolution")
    args = parser.parse_args()

    print(f"Loading CSVs from {args.input_dir}...")
    datasets = discover_datasets(args.input_dir)
    if not datasets:
        print("No CSV files found.")
        sys.exit(1)

    print(f"Running pipeline on {len(datasets)} datasets...")
    result = run_pipeline(datasets=datasets, use_ml=False, use_ann_blocking=args.use_ann_blocking)

    summary = result["scoring"]["summary"]
    print(f"\nCanonical records: {len(result['canonical_records'])}")
    print(f"Entities: {len(result['resolution']['entities'])}")
    print(f"Flagged profiles: {summary['flagged']} (high={summary['high']}, medium={summary['medium']})")

    print("\nTop 5 flagged profiles:")
    for profile in result["scoring"]["flagged_profiles"][:5]:
        print(
            f"  {profile['entity_id']} {profile['name']}: "
            f"score={profile['deviation_score']} tier={profile.get('risk_tier', 'n/a')}"
        )
        print(f"    reasons: {profile['direct_reasons'][:2]}")

    report_path = Path("demo_cust_csv_report.json")
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary saved to {report_path}")

    if not args.no_server:
        from taxnet.app import main as run_server

        sys.argv = [sys.argv[0], "--host", args.host, "--port", str(args.port)]
        run_server()


if __name__ == "__main__":
    main()
