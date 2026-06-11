import unittest

from taxnet.ingestion import canonicalize_datasets, profile_datasets
from taxnet.pipeline import run_benchmark, run_pipeline
from taxnet.synthetic import generate_synthetic_datasets


class PipelineTests(unittest.TestCase):
    def test_synthetic_pipeline_produces_flagged_profiles_and_metrics(self):
        result = run_pipeline()
        self.assertGreater(len(result["canonical_records"]), 30)
        self.assertGreater(len(result["resolution"]["entities"]), 5)
        self.assertGreater(len(result["scoring"]["flagged_profiles"]), 0)
        metrics = result["resolution"]["resolution_metrics"]
        self.assertTrue(metrics["available"])
        self.assertGreaterEqual(metrics["precision"], 0.9)
        self.assertGreaterEqual(metrics["f1"], 0.85)

    def test_ingestion_maps_example_tax_columns(self):
        datasets = {
            "fbr_tax_records.csv": [
                {
                    "fbr_id": "FBR-1",
                    "full_name": "M. Ahmed",
                    "declared_income_pkr": "50000",
                    "tax_paid_pkr": "0",
                    "filer_status": "Filer",
                    "reported_address": "House 1 Lahore",
                    "phone_number": "03001234567",
                }
            ]
        }
        records, profiles = canonicalize_datasets(datasets)
        self.assertEqual(profiles[0]["detected_kind"], "tax")
        self.assertEqual(records[0]["person_name"], "M. Ahmed")
        self.assertEqual(records[0]["declared_income"], 50000)

    def test_uploaded_like_datasets_run_without_truth_labels(self):
        datasets = generate_synthetic_datasets()
        stripped = {
            name: [{k: v for k, v in row.items() if not k.startswith("_")} for row in rows]
            for name, rows in datasets.items()
        }
        result = run_pipeline(datasets=stripped)
        self.assertFalse(result["resolution"]["resolution_metrics"]["available"])
        self.assertGreater(len(result["scoring"]["profiles"]), 0)

    def test_low_risk_profile_explanation_is_not_flagged(self):
        datasets = {
            "tax.csv": [
                {
                    "full_name": "M Ahmed",
                    "declared_income_pkr": "150000",
                    "tax_paid_pkr": "10000",
                    "filer_status": "Filer",
                    "reported_address": "House 1 Lahore",
                    "phone_number": "03001234567",
                }
            ]
        }
        result = run_pipeline(datasets=datasets)
        profile = result["scoring"]["profiles"][0]
        self.assertEqual(profile["deviation_score"], 0.0)
        self.assertIn("not currently in the flagged audit queue", profile["explanation"])
        self.assertNotIn("is flagged for audit review", profile["explanation"])

    def test_mapping_override_controls_uploaded_dataset_kind(self):
        datasets = {
            "assets_upload.csv": [
                {
                    "citizen": "M Ahmed",
                    "addr": "House 2 Lahore",
                    "engine": "3000",
                    "asset": "Toyota Land Cruiser",
                }
            ]
        }
        mappings = {
            "assets_upload.csv": {
                "_kind": "vehicle",
                "person_name": "citizen",
                "address": "addr",
                "engine_capacity_cc": "engine",
                "vehicle_make_model": "asset",
            }
        }
        profiles = profile_datasets(datasets, mappings=mappings)
        records, canonical_profiles = canonicalize_datasets(datasets, mappings=mappings)
        self.assertEqual(profiles[0]["detected_kind"], "vehicle")
        self.assertEqual(canonical_profiles[0]["detected_kind"], "vehicle")
        self.assertEqual(records[0]["record_type"], "vehicle")
        self.assertEqual(records[0]["person_name"], "M Ahmed")
        self.assertEqual(records[0]["engine_capacity_cc"], 3000)

    def test_shared_address_does_not_force_same_person_merge(self):
        datasets = {
            "fbr_tax_records.csv": [
                {
                    "full_name": "Ali Raza",
                    "declared_income_pkr": "50000",
                    "tax_paid_pkr": "0",
                    "filer_status": "Filer",
                    "reported_address": "House 10 Model Town Lahore",
                }
            ],
            "excise_vehicles.csv": [
                {
                    "owner_name": "Kamran Butt",
                    "engine_capacity_cc": "3000",
                    "vehicle_make_model": "Mercedes S400",
                    "owner_address": "House 10 Model Town Lahore",
                }
            ],
        }
        result = run_pipeline(datasets=datasets)
        self.assertEqual(len(result["resolution"]["entities"]), 2)
        associate_edges = [edge for edge in result["graph"]["edges"] if edge["relation"] == "SAME_ADDRESS_AS"]
        self.assertEqual(len(associate_edges), 2)

    def test_proxy_risk_is_scored_separately_from_direct_risk(self):
        result = run_pipeline()
        ali = next(profile for profile in result["scoring"]["profiles"] if profile["name"] == "Ali Raza Sheikh")
        self.assertGreater(ali["associate_proxy_score"], 0)
        self.assertGreaterEqual(ali["deviation_score"], 45)
        self.assertIn(ali["risk_basis"], {"associate-linked", "mixed"})
        self.assertTrue(ali["associate_reasons"])

    def test_benchmark_mode_returns_scalability_summary_without_truth_metrics(self):
        summary = run_benchmark(citizens=30)
        self.assertEqual(summary["mode"], "benchmark")
        self.assertEqual(summary["citizens"], 30)
        self.assertTrue(summary["truth_metrics_skipped"])
        self.assertGreater(summary["canonical_record_count"], 30)
        self.assertGreater(summary["entity_count"], 20)
        self.assertIn("candidate_pairs_after_blocking", summary["resolution_runtime_stats"])
        self.assertGreater(summary["throughput_records_per_second"], 0)


if __name__ == "__main__":
    unittest.main()

