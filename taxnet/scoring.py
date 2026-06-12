"""Deviation scoring and explainable audit trail generation."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .graph_engine import estimate_vehicle_value

UNKNOWN_INCOME_BASELINE = 150_000


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def tier_from_score(score: float) -> str:
    if score <= 20:
        return "green"
    if score <= 40:
        return "yellow"
    if score <= 60:
        return "orange"
    if score <= 80:
        return "red"
    return "critical"


# Alias used by ml_scorer and tests.
risk_tier = tier_from_score


def aggregate_entity(records: list[dict[str, Any]]) -> dict[str, Any]:
    tax_records = [r for r in records if r["record_type"] == "tax"]
    income_values = [r.get("declared_income", 0) for r in tax_records if r.get("declared_income", 0) > 0]
    tax_paid = sum(float(r.get("tax_paid") or 0) for r in tax_records)
    filer_statuses = [str(r.get("filer_status") or "").lower() for r in tax_records]
    vehicles = [r for r in records if r["record_type"] == "vehicle"]
    properties = [r for r in records if r["record_type"] == "property"]
    utilities = [r for r in records if r["record_type"] == "utility"]
    offshore_entities = [r for r in records if r["record_type"] == "offshore_entity"]
    vehicle_value = sum(estimate_vehicle_value(float(r.get("engine_capacity_cc") or 0)) for r in vehicles)
    property_value = sum(float(r.get("property_value") or 0) for r in properties)
    utility_monthly = sum(float(r.get("monthly_bill") or 0) for r in utilities)
    max_engine_cc = max([float(r.get("engine_capacity_cc") or 0) for r in vehicles] or [0])
    offshore_count = len(offshore_entities)
    offshore_jurisdictions = sorted({str(r.get("offshore_jurisdiction") or "").strip() for r in offshore_entities if r.get("offshore_jurisdiction")})
    offshore_sources = sorted({str(r.get("offshore_source") or "").strip() for r in offshore_entities if r.get("offshore_source")})
    has_declared_income = bool(income_values)
    has_tax_record = bool(tax_records)
    income = max(income_values) if income_values else 0
    effective_income = income if has_declared_income else UNKNOWN_INCOME_BASELINE
    pressure = lifestyle_pressure({
        "monthly_utility_bill": utility_monthly,
        "estimated_vehicle_value": vehicle_value,
        "estimated_property_value": property_value,
    })
    lli_ratio = pressure / max(effective_income, 25_000)
    if has_declared_income:
        income_status = "reported"
    elif has_tax_record:
        income_status = "tax_record_without_income"
    else:
        income_status = "no_linked_tax_record"
    return {
        "declared_monthly_income": income,
        "effective_monthly_income_for_scoring": effective_income,
        "income_evidence_status": income_status,
        "has_tax_record": has_tax_record,
        "has_declared_income": has_declared_income,
        "tax_record_count": len(tax_records),
        "tax_paid": tax_paid,
        "filer_statuses": filer_statuses,
        "vehicle_count": len(vehicles),
        "property_count": len(properties),
        "utility_meter_count": len(utilities),
        "offshore_entity_count": offshore_count,
        "offshore_jurisdictions": offshore_jurisdictions,
        "offshore_sources": offshore_sources,
        "estimated_vehicle_value": vehicle_value,
        "estimated_property_value": property_value,
        "monthly_utility_bill": utility_monthly,
        "max_engine_cc": max_engine_cc,
        "lli_ratio": lli_ratio,
        "records": records,
    }


def lifestyle_pressure(agg: dict[str, Any]) -> float:
    return (
        float(agg["monthly_utility_bill"])
        + float(agg["estimated_vehicle_value"]) / 120
        + float(agg["estimated_property_value"]) / 240
    )


def direct_score(agg: dict[str, Any]) -> tuple[float, dict[str, float], list[str], list[str]]:
    income = float(agg["effective_monthly_income_for_scoring"])
    vehicle_value = float(agg["estimated_vehicle_value"])
    property_value = float(agg["estimated_property_value"])
    monthly_bill = float(agg["monthly_utility_bill"])
    tax_paid = float(agg["tax_paid"])
    pressure = lifestyle_pressure(agg)
    ratio = pressure / max(income, 25_000)

    offshore_count = int(agg.get("offshore_entity_count") or 0)
    lli_ratio = float(agg.get("lli_ratio") or 0.0)
    components = {
        "income_lifestyle_gap": clamp((ratio - 1.2) * 18, 0, 35),
        "lli_gap": clamp((lli_ratio - 1.0) * 20, 0, 25),
        "luxury_vehicle": 18 if agg["max_engine_cc"] >= 2800 else 10 if agg["max_engine_cc"] >= 1800 else 0,
        "property_value": 20 if property_value >= 70_000_000 else 12 if property_value >= 30_000_000 else 0,
        "utility_pressure": 16 if monthly_bill >= 200_000 else 9 if monthly_bill >= 100_000 else 0,
        "tax_status": 14
        if ("non-filer" in agg["filer_statuses"] or agg["has_tax_record"] and tax_paid == 0 and pressure > 150_000)
        else 0,
        "missing_tax_return": 10 if not agg["has_tax_record"] and pressure > 150_000 else 0,
        "offshore_entity": min(offshore_count * 20, 60),
        "asset_burst": 20.0 if agg.get("asset_burst_detected") else 0.0,
    }
    score = clamp(sum(components.values()))

    reasons = []
    uncertainty_flags = []
    if not agg["has_tax_record"]:
        uncertainty_flags.append("no linked tax return")
    if not agg["has_declared_income"]:
        uncertainty_flags.append("declared income unavailable; conservative baseline used")
    if components["income_lifestyle_gap"] > 0:
        reasons.append(f"lifestyle pressure is {ratio:.1f}x declared monthly income")
    if components.get("lli_gap", 0) > 0:
        reasons.append(f"living-luxury-income ratio is {lli_ratio:.1f}x")
    if components.get("asset_burst", 0) > 0:
        reasons.append(
            f"asset burst detected: PKR {agg.get('asset_burst_window_value', 0):,.0f} within window"
        )
    if components["luxury_vehicle"] > 0:
        reasons.append(f"vehicle engine capacity reaches {agg['max_engine_cc']:.0f}cc")
    if components["property_value"] > 0:
        reasons.append(f"direct property value is PKR {property_value:,.0f}")
    if components["utility_pressure"] > 0:
        reasons.append(f"monthly utility bill is PKR {monthly_bill:,.0f}")
    if components["tax_status"] > 0:
        reasons.append("tax status or tax paid is inconsistent with lifestyle signals")
    if components["missing_tax_return"] > 0:
        reasons.append("high-value lifestyle signals have no linked tax return in the resolved entity")
    if offshore_count > 0:
        jurisdictions = ", ".join(agg.get("offshore_jurisdictions", [])[:3])
        reasons.append(f"linked to {offshore_count} offshore entity(s) in {jurisdictions or 'unknown jurisdictions'}")
    if not reasons:
        reasons.append("direct records are broadly consistent with declared income")
    return score, components, reasons, uncertainty_flags


def score_entities(
    graph: dict[str, Any],
    resolution: dict[str, Any],
    ml_model: Any | None = None,
    falkor_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entity_records = graph["entity_records"]
    entity_lookup = {entity["entity_id"]: entity for entity in resolution["entities"]}
    aggregates = {entity_id: aggregate_entity(records) for entity_id, records in entity_records.items()}

    ml_scores: dict[str, float] = {}
    shap_data: dict[str, Any] | None = None
    if ml_model is not None:
        from .ml_scorer import explain_with_shap, score_with_model

        ml_scores = {
            eid: data["deviation_score"]
            for eid, data in score_with_model(ml_model, graph, resolution, falkor_summary).items()
        }
        shap_data = explain_with_shap(ml_model, graph, resolution, falkor_summary)

    neighbor_links: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in graph["edges"]:
        if edge["relation"] in {"SAME_ADDRESS_AS", "SHARES_PHONE_WITH"}:
            neighbor_links[edge["source"]].append(edge)

    possible_matches_by_entity = possible_matches_for_entities(resolution)

    direct_results: dict[str, tuple[float, dict[str, float], list[str], list[str]]] = {}
    for entity_id, agg in aggregates.items():
        direct_results[entity_id] = direct_score(agg)

    peer_values = {
        "pressure": [lifestyle_pressure(agg) for agg in aggregates.values()],
        "assets": [
            float(agg["estimated_vehicle_value"]) + float(agg["estimated_property_value"])
            for agg in aggregates.values()
        ],
        "utility": [float(agg["monthly_utility_bill"]) for agg in aggregates.values()],
    }

    profiles = []
    for entity_id, entity in entity_lookup.items():
        agg = aggregates.get(entity_id, aggregate_entity([]))
        direct, components, direct_reasons, uncertainty_flags = direct_results.get(entity_id, (0.0, {}, [], []))
        anomaly_score, anomaly_reasons = peer_anomaly_score(agg, peer_values)
        if anomaly_score > 0:
            components["peer_anomaly"] = anomaly_score
            direct = clamp(direct + anomaly_score)
            direct_reasons.extend(anomaly_reasons)
        associate_asset_value = 0.0
        associate_reasons: list[str] = []
        strongest_link = 0.0

        for link in neighbor_links.get(entity_id, []):
            neighbor_id = link["target"]
            neighbor_agg = aggregates.get(neighbor_id)
            if not neighbor_agg:
                continue
            neighbor_assets = neighbor_agg["estimated_vehicle_value"] + neighbor_agg["estimated_property_value"]
            if neighbor_assets <= 0:
                continue
            strongest_link = max(strongest_link, float(link["confidence"]))
            associate_asset_value += neighbor_assets * float(link["confidence"])
            neighbor_name = entity_lookup.get(neighbor_id, {}).get("canonical_name", neighbor_id)
            associate_reasons.append(
                f"{link['relation'].lower()} {neighbor_name}, linked assets PKR {neighbor_assets:,.0f}"
            )

        income = float(agg["effective_monthly_income_for_scoring"])
        associate_ratio = associate_asset_value / max(income * 120, 3_000_000)
        associate_score = clamp((associate_ratio - 1.0) * 24 + strongest_link * 18, 0, 100)
        rule_score = clamp(max(direct, direct * 0.65 + associate_score * 0.55))

        ml_score = ml_scores.get(entity_id)
        if ml_score is not None:
            final_score = clamp(0.6 * rule_score + 0.4 * ml_score)
        else:
            final_score = rule_score

        if final_score >= 75:
            level = "high"
        elif final_score >= 45:
            level = "medium"
        else:
            level = "low"
        tier = tier_from_score(final_score)

        source_rows = []
        for record in agg["records"]:
            source_rows.append(
                {
                    "dataset": record["source_dataset"],
                    "row_id": record["source_row_id"],
                    "record_type": record["record_type"],
                    "raw": {key: value for key, value in record["raw"].items() if not key.startswith("_")},
                }
            )

        profile_possible_matches = possible_matches_by_entity.get(entity_id, [])
        if profile_possible_matches:
            uncertainty_flags.append("unresolved possible identity matches")
        if len(entity.get("source_record_ids", [])) <= 1:
            uncertainty_flags.append("single-source profile")

        evidence_coverage = evidence_coverage_score(agg, len(entity.get("source_record_ids", [])))
        scoring_confidence = clamp(evidence_coverage - min(len(profile_possible_matches), 3) * 8, 0, 100)
        risk_basis = "mixed"
        if associate_score <= 0:
            risk_basis = "direct"
        elif direct < 45:
            risk_basis = "associate-linked"

        explanation = build_explanation(
            entity.get("canonical_name", entity_id),
            final_score,
            direct,
            associate_score,
            direct_reasons,
            associate_reasons,
            uncertainty_flags,
        )

        profiles.append(
            {
                "entity_id": entity_id,
                "name": entity.get("canonical_name", entity_id),
                "risk_level": level,
                "risk_tier": tier,
                "deviation_score": round(final_score, 1),
                "direct_score": round(direct, 1),
                "associate_proxy_score": round(associate_score, 1),
                "ml_score": round(ml_score, 1) if ml_score is not None else None,
                "shap_base_value": shap_data["base_value"] if shap_data else None,
                "shap_features": shap_data["explanations"].get(entity_id, [])[:8] if shap_data else [],
                "risk_basis": risk_basis,
                "scoring_confidence": round(scoring_confidence, 1),
                "evidence_coverage": round(evidence_coverage, 1),
                "score_components": {key: round(value, 1) for key, value in components.items()},
                "aggregate": {
                    key: value
                    for key, value in agg.items()
                    if key
                    not in {
                        "records",
                    }
                },
                "direct_reasons": direct_reasons,
                "associate_reasons": associate_reasons[:6],
                "uncertainty_flags": sorted(set(uncertainty_flags)),
                "possible_matches": profile_possible_matches[:8],
                "explanation": explanation,
                "source_rows": source_rows,
                "source_record_ids": entity.get("source_record_ids", []),
                "truth_person_ids": entity.get("truth_person_ids", []),
            }
        )

    profiles.sort(key=lambda item: item["deviation_score"], reverse=True)
    flagged = [profile for profile in profiles if profile["deviation_score"] >= 45]
    return {
        "profiles": profiles,
        "flagged_profiles": flagged,
        "summary": {
            "profiles": len(profiles),
            "flagged": len(flagged),
            "high": sum(1 for profile in profiles if profile["risk_level"] == "high"),
            "medium": sum(1 for profile in profiles if profile["risk_level"] == "medium"),
            "low": sum(1 for profile in profiles if profile["risk_level"] == "low"),
            "average_scoring_confidence": round(
                sum(profile["scoring_confidence"] for profile in profiles) / len(profiles), 1
            )
            if profiles
            else 0,
        },
    }


def peer_anomaly_score(agg: dict[str, Any], peer_values: dict[str, list[float]]) -> tuple[float, list[str]]:
    checks = {
        "lifestyle pressure": lifestyle_pressure(agg),
        "asset value": float(agg["estimated_vehicle_value"]) + float(agg["estimated_property_value"]),
        "utility bill": float(agg["monthly_utility_bill"]),
    }
    value_keys = {
        "lifestyle pressure": "pressure",
        "asset value": "assets",
        "utility bill": "utility",
    }
    max_z = 0.0
    max_label = ""
    for label, value in checks.items():
        z_score = robust_z_score(value, peer_values[value_keys[label]])
        if z_score > max_z:
            max_z = z_score
            max_label = label
    score = clamp((max_z - 1.6) * 5, 0, 12)
    reasons = []
    if score > 0:
        reasons.append(f"{max_label} is a peer outlier with z-score {max_z:.1f}")
    return score, reasons


def robust_z_score(value: float, values: list[float]) -> float:
    if len(values) < 3:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((item - mean) ** 2 for item in values) / len(values)
    std_dev = variance**0.5
    if std_dev == 0:
        return 0.0
    return (value - mean) / std_dev


def evidence_coverage_score(agg: dict[str, Any], source_count: int) -> float:
    has_asset = bool(agg["vehicle_count"] or agg["property_count"] or agg.get("offshore_entity_count"))
    has_utility = bool(agg["utility_meter_count"])
    coverage = 0.0
    coverage += 35 if agg["has_tax_record"] else 0
    coverage += 30 if has_asset else 0
    coverage += 15 if has_utility else 0
    coverage += 20 if source_count >= 2 else 10 if source_count == 1 else 0
    return clamp(coverage)


def possible_matches_for_entities(resolution: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    record_to_entity = resolution.get("record_to_entity", {})
    entity_names = {entity["entity_id"]: entity.get("canonical_name", entity["entity_id"]) for entity in resolution.get("entities", [])}
    possible_by_entity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for match in resolution.get("possible_matches", []):
        left_entity = record_to_entity.get(match["left"])
        right_entity = record_to_entity.get(match["right"])
        if not left_entity or not right_entity or left_entity == right_entity:
            continue
        left_payload = {
            **match,
            "this_record": match["left"],
            "other_record": match["right"],
            "other_entity_id": right_entity,
            "other_entity_name": entity_names.get(right_entity, right_entity),
        }
        right_payload = {
            **match,
            "this_record": match["right"],
            "other_record": match["left"],
            "other_entity_id": left_entity,
            "other_entity_name": entity_names.get(left_entity, left_entity),
        }
        possible_by_entity[left_entity].append(left_payload)
        possible_by_entity[right_entity].append(right_payload)
    for matches in possible_by_entity.values():
        matches.sort(key=lambda item: item["confidence"], reverse=True)
    return dict(possible_by_entity)


def build_explanation(
    name: str,
    final_score: float,
    direct_score_value: float,
    associate_score: float,
    direct_reasons: list[str],
    associate_reasons: list[str],
    uncertainty_flags: list[str] | None = None,
) -> str:
    if final_score >= 45:
        opening = f"{name} is flagged for audit review with a deviation score of {final_score:.1f}/100."
    else:
        opening = f"{name} is not currently in the flagged audit queue; deviation score is {final_score:.1f}/100."
    pieces = [
        opening,
        f"Direct risk contributes {direct_score_value:.1f}/100.",
    ]
    if associate_score > 0:
        pieces.append(f"Associate-linked risk contributes {associate_score:.1f}/100.")
    if direct_reasons:
        pieces.append("Direct evidence: " + "; ".join(direct_reasons[:4]) + ".")
    if associate_reasons:
        pieces.append("Associate evidence: " + "; ".join(associate_reasons[:3]) + ".")
    if uncertainty_flags:
        pieces.append("Review notes: " + "; ".join(sorted(set(uncertainty_flags))[:4]) + ".")
    pieces.append("This is an audit-risk signal, not a legal conclusion.")
    return " ".join(pieces)
