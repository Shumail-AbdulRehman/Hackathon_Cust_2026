"""Run the TaxNet pipeline on a sample of the ICIJ Offshore Leaks dataset.

Usage:
    uv run python scripts/demo_icij.py [--max-entities 10000] [--seed 42]
"""

from __future__ import annotations

import argparse
import json
import time

from taxnet.loaders.icij_loader import build_icij_datasets
from taxnet.pipeline import compact_result, run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TaxNet on ICIJ Offshore Leaks sample")
    parser.add_argument("--max-entities", type=int, default=10_000, help="Number of offshore entity seeds")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible sampling")
    parser.add_argument("--hop-radius", type=int, default=1, help="Hop radius around seed entities")
    parser.add_argument("--output", type=str, default="demo_icij_report.json", help="Output JSON file")
    parser.add_argument("--no-ann", action="store_true", help="Use traditional blocking instead of ANN blocking")
    args = parser.parse_args()

    print(f"Loading ICIJ Offshore Leaks sample (max_entities={args.max_entities}, seed={args.seed})...")
    start = time.perf_counter()
    datasets = build_icij_datasets(max_entities=args.max_entities, seed=args.seed, hop_radius=args.hop_radius)
    load_time = time.perf_counter() - start
    print(f"Loaded {len(datasets['icij-offshore-leaks']):,} records in {load_time:.1f}s")

    print("Running TaxNet pipeline...")
    # Disable ML for ICIJ data because the model is currently trained only on
    # synthetic Pakistan records and would suppress real offshore-entity signals.
    # Enable ANN blocking for fast approximate-neighbor search on large name/address sets.
    result = run_pipeline(datasets=datasets, use_ml=False, use_ann_blocking=not args.no_ann)
    compact = compact_result(result)

    print(f"\nMode: {compact['mode']}")
    print(f"Canonical records: {compact['canonical_record_count']:,}")
    print(f"Entities: {len(compact['resolution']['entities']):,}")
    print(f"Graph nodes: {compact['graph']['summary'].get('nodes', 0):,}")
    print(f"Graph edges: {compact['graph']['summary'].get('edges', 0):,}")
    print(f"Flagged profiles: {compact['scoring']['summary']['flagged']:,}")
    print(f"Timing: {json.dumps(compact['timing_ms'], indent=2)}")

    print("\nTop 10 flagged profiles:")
    for profile in compact["scoring"]["flagged_profiles"][:10]:
        ml = f" ml={profile['ml_score']:.1f}" if profile.get("ml_score") is not None else ""
        print(f"  {profile['entity_id']} {profile['name']}: score={profile['deviation_score']:.1f} tier={profile['risk_tier']}{ml}")
        for reason in profile["direct_reasons"][:3]:
            print(f"    - {reason}")

    Path = __import__("pathlib").Path
    output_path = Path(args.output)
    output_path.write_text(json.dumps(compact, indent=2, default=str))
    print(f"\nReport saved to {output_path}")


if __name__ == "__main__":
    main()
