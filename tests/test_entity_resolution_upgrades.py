import unittest

from taxnet.ingestion import canonicalize_datasets
from taxnet.normalization import normalize_national_id


class NationalIdTests(unittest.TestCase):
    def test_cnic_with_dashes(self):
        self.assertEqual(normalize_national_id("35202-1234567-8"), "3520212345678")

    def test_cnic_clean(self):
        self.assertEqual(normalize_national_id("3520212345678"), "3520212345678")

    def test_ntn(self):
        self.assertEqual(normalize_national_id("1234567"), "1234567")

    def test_invalid_returns_empty(self):
        self.assertEqual(normalize_national_id("abc"), "")


class IngestionNicTests(unittest.TestCase):
    def test_tax_record_extracts_cnic(self):
        datasets = {
            "tax.csv": [
                {
                    "full_name": "M Ahmed",
                    "cnic": "35202-1234567-8",
                    "declared_income_pkr": "50000",
                    "tax_paid_pkr": "0",
                    "filer_status": "Filer",
                    "reported_address": "House 1 Lahore",
                }
            ]
        }
        records, _ = canonicalize_datasets(datasets)
        self.assertEqual(records[0]["national_id"], "3520212345678")

    def test_vehicle_record_extracts_ntn(self):
        datasets = {
            "vehicles.csv": [
                {
                    "owner_name": "M Ahmed",
                    "ntn": "1234567",
                    "engine_capacity_cc": "1300",
                }
            ]
        }
        records, _ = canonicalize_datasets(datasets)
        self.assertEqual(records[0]["national_id"], "1234567")


class CnicBlockingTests(unittest.TestCase):
    def test_same_cnic_merges_despite_name_drift(self):
        from taxnet.entity_resolution import resolve_entities

        records = [
            {
                "source_dataset": "a",
                "source_row_id": "1",
                "source_kind": "tax",
                "person_name": "Muhammad Ahmed Khan",
                "address": "House 1 Lahore",
                "national_id": "35202-1234567-8",
            },
            {
                "source_dataset": "b",
                "source_row_id": "2",
                "source_kind": "vehicle",
                "person_name": "M. Ahmed",
                "address": "H 1 Lahore",
                "national_id": "3520212345678",
            },
        ]
        result = resolve_entities(records)
        self.assertEqual(len(result["entities"]), 1)


class AssetRangeBlockingTests(unittest.TestCase):
    def test_different_people_same_city_same_surname_stay_separate(self):
        from taxnet.entity_resolution import resolve_entities

        records = [
            {
                "source_dataset": "a",
                "source_row_id": "1",
                "source_kind": "tax",
                "person_name": "Ali Khan",
                "address": "House 1 Lahore",
            },
            {
                "source_dataset": "a",
                "source_row_id": "2",
                "source_kind": "tax",
                "person_name": "Bilal Khan",
                "address": "House 2 Lahore",
            },
        ]
        result = resolve_entities(records)
        self.assertEqual(len(result["entities"]), 2)
