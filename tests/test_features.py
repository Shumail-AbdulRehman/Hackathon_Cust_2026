import unittest

from taxnet.features import build_entity_features
from taxnet.pipeline import run_pipeline


class FeatureTests(unittest.TestCase):
    def test_features_are_numeric(self):
        result = run_pipeline()
        features = build_entity_features(result["graph"], result["resolution"], result.get("falkor_summary"))
        self.assertGreater(len(features), 0)
        for entity_id, vector in features.items():
            for key, value in vector.items():
                self.assertIsInstance(value, float, f"{entity_id}.{key} is not float")

    def test_high_risk_entity_has_high_income_lifestyle_ratio(self):
        result = run_pipeline()
        features = build_entity_features(result["graph"], result["resolution"], result.get("falkor_summary"))
        flagged = result["scoring"]["flagged_profiles"][0]
        entity_id = flagged["entity_id"]
        self.assertGreater(features[entity_id]["income_lifestyle_ratio"], 1.0)
