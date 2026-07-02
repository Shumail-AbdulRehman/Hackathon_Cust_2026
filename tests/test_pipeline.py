# tests/test_pipeline.py
from unittest.mock import patch

from taxnet.pipeline import run_pipeline


def test_run_pipeline_does_not_train_on_uploaded_data():
    datasets = {
        "tax.csv": [
            {"person_name": "Alice", "declared_income": "50000", "tax_paid": "2000", "filer_status": "Filer"}
        ]
    }
    with patch("taxnet.ml_scorer.train_model") as mock_train:
        result = run_pipeline(datasets=datasets, use_ml=True)
        mock_train.assert_not_called()
        assert result["mode"] == "uploaded"


def test_run_pipeline_reports_ml_used():
    datasets = {
        "tax.csv": [
            {"person_name": "Alice", "declared_income": "50000", "tax_paid": "2000", "filer_status": "Filer"}
        ]
    }
    result = run_pipeline(datasets=datasets, use_ml=True)
    assert "ml_used" in result["scoring"]["summary"]
    # Without a pretrained model, ml_used should be False.
    assert result["scoring"]["summary"]["ml_used"] is False
