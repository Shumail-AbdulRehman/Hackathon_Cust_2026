"""Backend-only demo script for live judging."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from taxnet.pipeline import run_pipeline


def main() -> None:
    print("Running TaxNet backend demo...")
    result = run_pipeline()

    print(f"\nCanonical records: {len(result['canonical_records'])}")
    print(f"Entities: {len(result['resolution']['entities'])}")
    print(f"FalkorDB summary: {result.get('falkor_summary')}")
    print(f"Flagged profiles: {result['scoring']['summary']['flagged']}")

    print("\nTop 5 flagged profiles:")
    for profile in result["scoring"]["flagged_profiles"][:5]:
        print(
            f"  {profile['entity_id']} {profile['name']}: "
            f"score={profile['deviation_score']} tier={profile.get('risk_tier', 'n/a')} "
            f"ml={profile.get('ml_score', 'n/a')}"
        )
        print(f"    reasons: {profile['direct_reasons'][:2]}")
        if profile.get("shap_features"):
            top = profile["shap_features"][0]
            print(f"    top SHAP: {top['feature']} = {top['contribution']}")

    report_path = Path("demo_backend_report.json")
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(result["scoring"]["summary"], f, indent=2)
    print(f"\nSummary saved to {report_path}")


if __name__ == "__main__":
    main()
