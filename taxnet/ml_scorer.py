"""Interpretable ML scorer using XGBoost."""

from __future__ import annotations

from typing import Any

from pathlib import Path

import numpy as np
import shap
import xgboost as xgb

from .features import build_entity_features


FEATURE_COLUMNS = [
    "income_lifestyle_ratio",
    "vehicle_value_to_income_ratio",
    "property_value_to_income_ratio",
    "utility_to_income_ratio",
    "tax_paid_to_income_ratio",
    "max_engine_cc",
    "asset_count",
    "source_count",
    "is_non_filer",
    "is_filer",
    "shared_address_count",
    "shared_phone_count",
    "pagerank_score",
    "community_size",
    "degree_centrality",
    "offshore_entity_count",
    "offshore_jurisdiction_count",
    "offshore_source_count",
    "lli_ratio",
    "lli_score",
    "nic_province_count",
    "nic_district_count",
    "nic_province_punjab",
    "nic_province_sindh",
    "nic_province_kp",
    "nic_province_balochistan",
    "nic_province_islamabad",
    "benford_max_mad",
    "benford_income_mad",
    "benford_tax_paid_mad",
    "benford_property_mad",
    "benford_utility_mad",
    "benford_vehicle_cc_mad",
    "asset_event_count",
    "first_asset_year",
    "last_asset_year",
    "peak_asset_year",
    "peak_year_asset_value",
    "asset_burst_detected",
    "asset_burst_window_value",
    "asset_burst_window_event_count",
    "shared_national_id_count",
    "max_asset_to_income_ratio",
    "unreported_asset_years",
    "asset_burst_count",
    "total_unexplained_value",
    "district_known",
    "district_risk_score",
]


def _vector(entity_features: dict[str, float]) -> list[float]:
    return [float(entity_features.get(col, 0.0)) for col in FEATURE_COLUMNS]


def _label_from_scenarios(scenarios: set[str]) -> float:
    """Assign a synthetic fraud-risk label from ground-truth scenarios."""
    if any(s in {"direct_luxury", "proxy_luxury"} for s in scenarios):
        return 90.0
    if any("cash_low_tax" in s for s in scenarios):
        return 60.0
    return 10.0


def make_training_data(
    graph: dict[str, Any],
    resolution: dict[str, Any],
    falkor_summary: dict[str, Any] | None = None,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Return X, y, entity_ids using truth_scenario labels."""
    features = build_entity_features(graph, resolution, falkor_summary)
    entity_records = graph.get("entity_records", {})

    X, y, ids = [], [], []
    for entity_id, records in entity_records.items():
        vec = _vector(features[entity_id])
        scenarios = {str(r.get("truth_scenario", "")) for r in records}
        label = _label_from_scenarios(scenarios)
        X.append(vec)
        y.append(label)
        ids.append(entity_id)

    return np.array(X), np.array(y), ids


def load_pretrained_model(path: str = "server_artifacts/ml/ml_model.json") -> xgb.XGBRegressor | None:
    """Load a previously trained XGBoost model from disk."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        model = xgb.XGBRegressor()
        # Work around xgboost builds where the regressor mixin does not set
        # _estimator_type, causing load_model to raise TypeError.
        if not hasattr(model, "_estimator_type"):
            model._estimator_type = "regressor"
        model.load_model(str(p))
        return model
    except Exception:
        return None


def train_model(
    graph: dict[str, Any],
    resolution: dict[str, Any],
    falkor_summary: dict[str, Any] | None = None,
) -> xgb.XGBRegressor:
    X, y, _ = make_training_data(graph, resolution, falkor_summary)
    model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.05,
        objective="reg:squarederror",
        random_state=42,
        base_score=0.5,
    )
    model.fit(X, y)
    return model


def risk_tier(score: float) -> str:
    if score <= 20:
        return "green"
    if score <= 40:
        return "yellow"
    if score <= 60:
        return "orange"
    if score <= 80:
        return "red"
    return "critical"


def score_with_model(
    model: xgb.XGBRegressor,
    graph: dict[str, Any],
    resolution: dict[str, Any],
    falkor_summary: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    features = build_entity_features(graph, resolution, falkor_summary)
    entity_ids = list(features.keys())
    X = np.array([_vector(features[eid]) for eid in entity_ids])
    predictions = model.predict(X)

    results: dict[str, dict[str, Any]] = {}
    for entity_id, raw_score in zip(entity_ids, predictions):
        clamped = max(0.0, min(100.0, float(raw_score)))
        results[entity_id] = {
            "deviation_score": round(clamped, 1),
            "risk_tier": risk_tier(clamped),
            "features": features[entity_id],
        }
    return results


def explain_with_shap(
    model: xgb.XGBRegressor,
    graph: dict[str, Any],
    resolution: dict[str, Any],
    falkor_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    features = build_entity_features(graph, resolution, falkor_summary)
    entity_ids = list(features.keys())
    X = np.array([_vector(features[eid]) for eid in entity_ids])

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    base_value = float(explainer.expected_value)

    # For single-output regressors shap_values is a 2D array.
    values_array = shap_values if not isinstance(shap_values, list) else shap_values[0]

    explanations: dict[str, list[dict[str, Any]]] = {}
    for idx, entity_id in enumerate(entity_ids):
        values = values_array[idx]
        explanations[entity_id] = [
            {
                "feature": FEATURE_COLUMNS[j],
                "value": round(float(features[entity_id][FEATURE_COLUMNS[j]]), 4),
                "contribution": round(float(values[j]), 4),
            }
            for j in range(len(FEATURE_COLUMNS))
        ]
        explanations[entity_id].sort(key=lambda item: abs(item["contribution"]), reverse=True)

    return {"base_value": base_value, "explanations": explanations}


def save_model(model: xgb.XGBRegressor, path: str) -> None:
    model.save_model(path)


def load_model(path: str) -> xgb.XGBRegressor:
    model = xgb.XGBRegressor()
    model.load_model(path)
    return model
