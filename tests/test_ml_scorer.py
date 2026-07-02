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


from pathlib import Path

import numpy as np
import pytest
import xgboost as xgb
from taxnet.ml_scorer import load_pretrained_model


def test_load_pretrained_model_missing_file(tmp_path):
    missing = tmp_path / "missing.json"
    assert load_pretrained_model(str(missing)) is None


def test_load_pretrained_model_loads_saved_model(tmp_path):
    path = tmp_path / "model.json"
    X = np.array([[1, 2], [3, 4], [5, 6]])
    y = np.array([1, 2, 3])
    model = xgb.XGBRegressor(n_estimators=2, max_depth=2)
    model.fit(X, y)
    # Work around xgboost builds where the regressor mixin does not set
    # _estimator_type, causing save_model/load_model to raise TypeError.
    model._estimator_type = "regressor"
    model.save_model(str(path))

    loaded = load_pretrained_model(str(path))
    assert loaded is not None
    assert loaded.predict(X).shape == (3,)


def test_load_pretrained_model_corrupt_file(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("not valid xgboost json")
    assert load_pretrained_model(str(path)) is None
