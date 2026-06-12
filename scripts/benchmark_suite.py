import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from taxnet.pipeline import run_benchmark


def main() -> None:
    sizes = [100, 250, 500]
    results = []
    for citizens in sizes:
        print(f"Benchmarking {citizens} citizens...")
        summary = run_benchmark(citizens=citizens)
        results.append(
            {
                "citizens": citizens,
                "records": summary["canonical_record_count"],
                "entities": summary["entity_count"],
                "flagged": summary["scoring_summary"]["flagged"],
                "total_ms": summary["timing_ms"]["total"],
                "throughput": summary["throughput_records_per_second"],
                "blocking_reduction": summary["resolution_runtime_stats"]["blocking_reduction_pct"],
            }
        )

    print(json.dumps(results, indent=2))
    with open("benchmark_suite_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
