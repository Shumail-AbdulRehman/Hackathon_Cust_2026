"""Interpretable feature engineering for tax fraud scoring."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .falkor_engine import run_communities, run_degrees, run_pagerank
from .graph_engine import estimate_vehicle_value


def build_entity_features(
    graph: dict[str, Any],
    resolution: dict[str, Any],
    falkor_summary: dict[str, Any] | None = None,
) -> dict[str, dict[str, float]]:
    """Return a dict mapping entity_id to a feature vector."""
    entity_records = graph.get("entity_records", {})
    features: dict[str, dict[str, float]] = {}

    graph_name = None
    if falkor_summary and "graph_name" in falkor_summary:
        graph_name = falkor_summary["graph_name"]

    pagerank = run_pagerank(graph_name) if graph_name else {}
    communities = run_communities(graph_name) if graph_name else {}
    degrees = run_degrees(graph_name) if graph_name else {}

    # In-memory neighbor analysis
    neighbor_links: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in graph.get("edges", []):
        if edge["relation"] in {"SAME_ADDRESS_AS", "SHARES_PHONE_WITH"}:
            neighbor_links[edge["source"]].append(edge)

    for entity_id, records in entity_records.items():
        tax_records = [r for r in records if r["record_type"] == "tax"]
        vehicles = [r for r in records if r["record_type"] == "vehicle"]
        properties = [r for r in records if r["record_type"] == "property"]
        utilities = [r for r in records if r["record_type"] == "utility"]

        income_values = [r.get("declared_income", 0) for r in tax_records if r.get("declared_income", 0) > 0]
        income = max(income_values) if income_values else 0
        effective_income = income if income_values else 150_000

        vehicle_value = sum(estimate_vehicle_value(float(r.get("engine_capacity_cc") or 0)) for r in vehicles)
        property_value = sum(float(r.get("property_value") or 0) for r in properties)
        utility_monthly = sum(float(r.get("monthly_bill") or 0) for r in utilities)
        tax_paid = sum(float(r.get("tax_paid") or 0) for r in tax_records)
        max_engine_cc = max([float(r.get("engine_capacity_cc") or 0) for r in vehicles] or [0])
        asset_count = len(vehicles) + len(properties)
        source_count = len({r["source_dataset"] for r in records})

        filer_statuses = [str(r.get("filer_status") or "").lower() for r in tax_records]
        is_non_filer = any("non" in s for s in filer_statuses)
        is_filer = any("filer" in s and "non" not in s for s in filer_statuses)

        lifestyle_pressure = utility_monthly + vehicle_value / 120 + property_value / 240

        links = neighbor_links.get(entity_id, [])
        shared_address = sum(1 for e in links if e["relation"] == "SAME_ADDRESS_AS")
        shared_phone = sum(1 for e in links if e["relation"] == "SHARES_PHONE_WITH")

        community_id = communities.get(entity_id)
        community_size = sum(1 for c in communities.values() if c == community_id) if community_id is not None else 0

        features[entity_id] = {
            "income_lifestyle_ratio": lifestyle_pressure / max(effective_income, 25_000),
            "vehicle_value_to_income_ratio": vehicle_value / max(effective_income, 25_000),
            "property_value_to_income_ratio": property_value / max(effective_income, 25_000),
            "utility_to_income_ratio": utility_monthly / max(effective_income, 25_000),
            "tax_paid_to_income_ratio": tax_paid / max(effective_income * 12, 1),
            "max_engine_cc": float(max_engine_cc),
            "asset_count": float(asset_count),
            "source_count": float(source_count),
            "is_non_filer": float(is_non_filer),
            "is_filer": float(is_filer),
            "shared_address_count": float(shared_address),
            "shared_phone_count": float(shared_phone),
            "pagerank_score": float(pagerank.get(entity_id, 0.0)),
            "community_size": float(community_size),
            "degree_centrality": float(degrees.get(entity_id, 0)),
        }

    return features
