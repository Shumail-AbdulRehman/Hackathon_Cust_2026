"""Interpretable feature engineering for tax fraud scoring."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .benford import benford_counts, benford_mad
from .falkor_engine import run_communities, run_degrees, run_pagerank
from .graph_engine import estimate_vehicle_value
from .income_event_alignment import align_income_and_events
from .nic_geocode import lookup_district
from .scoring import clamp
from .temporal_analysis import temporal_features


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
        offshore_entities = [r for r in records if r["record_type"] == "offshore_entity"]

        income_values = [r.get("declared_income", 0) for r in tax_records if r.get("declared_income", 0) > 0]
        income = max(income_values) if income_values else 0
        effective_income = income if income_values else 150_000

        vehicle_value = sum(estimate_vehicle_value(float(r.get("engine_capacity_cc") or 0)) for r in vehicles)
        property_value = sum(float(r.get("property_value") or 0) for r in properties)
        utility_monthly = sum(float(r.get("monthly_bill") or 0) for r in utilities)
        tax_paid = sum(float(r.get("tax_paid") or 0) for r in tax_records)
        max_engine_cc = max([float(r.get("engine_capacity_cc") or 0) for r in vehicles] or [0])
        asset_count = len(vehicles) + len(properties) + len(offshore_entities)
        source_count = len({r["source_dataset"] for r in records})
        offshore_count = len(offshore_entities)
        offshore_jurisdictions = {str(r.get("offshore_jurisdiction") or "").strip() for r in offshore_entities}
        offshore_sources = {str(r.get("offshore_source") or "").strip() for r in offshore_entities}

        filer_statuses = [str(r.get("filer_status") or "").lower() for r in tax_records]
        is_non_filer = any("non" in s for s in filer_statuses)
        is_filer = any("filer" in s and "non" not in s for s in filer_statuses)

        # NIC geocoding
        nic_provinces: set[str] = set()
        nic_districts: set[str] = set()
        district_risk = 0
        district_known = 0.0
        for r in records:
            loc = lookup_district(r.get("national_id"))
            if loc["province"]:
                nic_provinces.add(loc["province"])
            if loc["district"]:
                nic_districts.add(loc["district"])
                district_risk = max(district_risk, loc["district_risk_score"])
                district_known = 1.0

        lifestyle_pressure = utility_monthly + vehicle_value / 120 + property_value / 240

        # Living-Luxury-Income (LLI) metric: monthly lifestyle pressure + imputed monthly asset cost / income
        annualized_asset_cost = vehicle_value / 120 + property_value / 240
        lli_numerator = lifestyle_pressure + annualized_asset_cost
        lli_ratio = lli_numerator / max(effective_income, 25_000)

        # Temporal analysis
        temporal = temporal_features(records)

        # Income-event alignment
        alignment = align_income_and_events(records)

        # Benford's Law analysis across numeric columns (per-entity, small samples usually yield 0 MAD)
        benford_fields = {
            "income": [r.get("declared_income") for r in tax_records],
            "tax_paid": [r.get("tax_paid") for r in tax_records],
            "property_value": [r.get("property_value") for r in properties],
            "utility_bill": [r.get("monthly_bill") for r in utilities],
            "vehicle_cc": [r.get("engine_capacity_cc") for r in vehicles],
        }
        benford_mads: dict[str, float] = {}
        for label, values in benford_fields.items():
            counts = benford_counts(values)
            mad, _ = benford_mad(counts)
            benford_mads[label] = mad

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
            "offshore_entity_count": float(offshore_count),
            "offshore_jurisdiction_count": float(len(offshore_jurisdictions)),
            "offshore_source_count": float(len(offshore_sources)),
            "nic_province_count": float(len(nic_provinces)),
            "nic_district_count": float(len(nic_districts)),
            "nic_province_punjab": float("Punjab" in nic_provinces),
            "nic_province_sindh": float("Sindh" in nic_provinces),
            "nic_province_kp": float("Khyber Pakhtunkhwa" in nic_provinces),
            "nic_province_balochistan": float("Balochistan" in nic_provinces),
            "nic_province_islamabad": float("Islamabad Capital Territory" in nic_provinces),
            "benford_income_mad": benford_mads.get("income", 0.0),
            "benford_tax_paid_mad": benford_mads.get("tax_paid", 0.0),
            "benford_property_mad": benford_mads.get("property_value", 0.0),
            "benford_utility_mad": benford_mads.get("utility_bill", 0.0),
            "benford_vehicle_cc_mad": benford_mads.get("vehicle_cc", 0.0),
            "benford_max_mad": max(benford_mads.values()) if benford_mads else 0.0,
            "lli_ratio": float(lli_ratio),
            "lli_score": float(clamp(lli_ratio * 25, 0, 100)),
            "asset_event_count": float(temporal["asset_event_count"]),
            "first_asset_year": float(temporal["first_asset_year"]),
            "last_asset_year": float(temporal["last_asset_year"]),
            "peak_asset_year": float(temporal["peak_asset_year"]),
            "peak_year_asset_value": temporal["peak_year_asset_value"],
            "asset_burst_detected": float(temporal["asset_burst_detected"]),
            "asset_burst_window_value": temporal["asset_burst_window_value"],
            "asset_burst_window_event_count": float(temporal["asset_burst_window_event_count"]),
            "max_asset_to_income_ratio": float(alignment["max_asset_to_income_ratio"]),
            "unreported_asset_years": float(alignment["unreported_asset_years"]),
            "asset_burst_count": float(alignment["asset_burst_count"]),
            "total_unexplained_value": float(alignment["total_unexplained_value"]),
            "district_known": district_known,
            "district_risk_score": float(district_risk),
        }

    return features
