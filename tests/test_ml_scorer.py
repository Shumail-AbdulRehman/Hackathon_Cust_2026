import unittest

from taxnet.scoring import risk_tier

try:
    from taxnet.ml_scorer import explain_with_shap, score_with_model, train_model

    ML_AVAILABLE = True
except Exception:
    ML_AVAILABLE = False

from taxnet.pipeline import run_pipeline


@unittest.skipUnless(ML_AVAILABLE, "xgboost/shap not installed")
class MLScorerTests(unittest.TestCase):
    def test_train_and_score(self):
        result = run_pipeline()
        model = train_model(result["graph"], result["resolution"], result.get("falkor_summary"))
        scores = score_with_model(model, result["graph"], result["resolution"], result.get("falkor_summary"))
        self.assertGreater(len(scores), 0)
        for eid, data in scores.items():
            self.assertIn("deviation_score", data)
            self.assertIn("risk_tier", data)
            self.assertGreaterEqual(data["deviation_score"], 0)
            self.assertLessEqual(data["deviation_score"], 100)


class RiskTierTests(unittest.TestCase):
    def test_risk_tiers(self):
        self.assertEqual(risk_tier(15), "green")
        self.assertEqual(risk_tier(30), "yellow")
        self.assertEqual(risk_tier(50), "orange")
        self.assertEqual(risk_tier(70), "red")
        self.assertEqual(risk_tier(90), "critical")


@unittest.skipUnless(ML_AVAILABLE, "xgboost/shap not installed")
class ShapTests(unittest.TestCase):
    def test_shap_returns_explanations(self):
        result = run_pipeline()
        model = train_model(result["graph"], result["resolution"], result.get("falkor_summary"))
        shap_result = explain_with_shap(model, result["graph"], result["resolution"], result.get("falkor_summary"))
        self.assertIn("base_value", shap_result)
        self.assertIn("explanations", shap_result)
        self.assertGreater(len(shap_result["explanations"]), 0)
        first = next(iter(shap_result["explanations"].values()))
        self.assertGreater(len(first), 0)
        self.assertIn("feature", first[0])
        self.assertIn("contribution", first[0])
