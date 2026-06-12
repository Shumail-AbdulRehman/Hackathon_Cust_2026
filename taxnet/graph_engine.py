"""Evidence graph construction without external graph dependencies."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any

from .normalization import normalize_address, normalize_national_id, normalize_phone


def estimate_vehicle_value(engine_cc: float) -> float:
    if engine_cc >= 2800:
        return 45_000_000
    if engine_cc >= 2000:
        return 18_000_000
    if engine_cc >= 1300:
        return 5_500_000
    if engine_cc >= 1000:
        return 3_800_000
    if engine_cc > 0:
        return 2_500_000
    return 0


def stable_id(prefix: str, value: object, length: int = 12) -> str:
    digest = hashlib.sha1(str(value).encode("utf-8")).hexdigest()[:length]
    return f"{prefix}-{digest}"


def build_graph(records: list[dict[str, Any]], resolution: dict[str, Any]) -> dict[str, Any]:
    record_to_entity = resolution["record_to_entity"]
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    entity_records: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for entity in resolution["entities"]:
        nodes[entity["entity_id"]] = {
            "id": entity["entity_id"],
            "type": "Person",
            "label": entity["canonical_name"],
            "meta": entity,
        }

    def add_node(node_id: str, node_type: str, label: str, meta: dict[str, Any] | None = None) -> None:
        if node_id not in nodes:
            nodes[node_id] = {"id": node_id, "type": node_type, "label": label, "meta": meta or {}}

    def add_edge(
        source: str, target: str, relation: str, confidence: float = 1.0, evidence: dict[str, Any] | None = None
    ) -> None:
        edges.append(
            {
                "source": source,
                "target": target,
                "relation": relation,
                "confidence": round(confidence, 3),
                "evidence": evidence or {},
            }
        )

    address_to_entities: dict[str, set[str]] = defaultdict(set)
    phone_to_entities: dict[str, set[str]] = defaultdict(set)
    national_id_to_entities: dict[str, set[str]] = defaultdict(set)

    for record in records:
        source_ref = f"{record['source_dataset']}:{record['source_row_id']}"
        entity_id = record_to_entity.get(source_ref)
        if not entity_id:
            continue
        entity_records[entity_id].append(record)
        evidence = {
            "source_dataset": record["source_dataset"],
            "source_row_id": record["source_row_id"],
            "record_type": record["record_type"],
        }

        address_norm = normalize_address(record.get("address", ""))
        if address_norm:
            address_id = stable_id("ADDR", address_norm)
            add_node(
                address_id,
                "Address",
                record.get("address", ""),
                {"normalized": address_norm, "stable_key": address_norm},
            )
            add_edge(entity_id, address_id, "USES_ADDRESS", 0.8, evidence)
            address_to_entities[address_norm].add(entity_id)

        phone_norm = normalize_phone(record.get("phone", ""))
        if phone_norm:
            phone_id = stable_id("PHONE", phone_norm)
            add_node(
                phone_id, "PhoneNumber", f"***{phone_norm[-4:]}", {"normalized": phone_norm, "suffix": phone_norm[-4:]}
            )
            add_edge(entity_id, phone_id, "USES_PHONE", 0.95, evidence)
            phone_to_entities[phone_norm].add(entity_id)

        national_id = normalize_national_id(record.get("national_id", ""))
        if national_id:
            national_id_id = stable_id("NID", national_id)
            add_node(
                national_id_id,
                "NationalId",
                f"ID-{national_id[:5]}",
                {"normalized": national_id, "prefix": national_id[:5]},
            )
            add_edge(entity_id, national_id_id, "USES_NATIONAL_ID", 1.0, evidence)
            national_id_to_entities[national_id].add(entity_id)

        if record["record_type"] == "tax":
            node_id = f"TAX-{source_ref}"
            label = f"Return {record.get('filer_status') or 'Unknown'}"
            add_node(node_id, "TaxReturn", label, record)
            add_edge(entity_id, node_id, "FILED_IN", 1.0, evidence)
        elif record["record_type"] == "vehicle":
            node_id = f"VEH-{record.get('vehicle_reg_no') or source_ref}"
            label = str(record.get("vehicle_make_model") or "Vehicle")
            vehicle_value = estimate_vehicle_value(float(record.get("engine_capacity_cc") or 0))
            add_node(node_id, "Vehicle", label, {**record, "estimated_value": vehicle_value})
            add_edge(entity_id, node_id, "OWNS_VEHICLE", 0.9, evidence)
        elif record["record_type"] == "utility":
            node_id = f"METER-{record.get('meter_ref_no') or source_ref}"
            label = str(record.get("meter_ref_no") or "Meter")
            add_node(node_id, "Meter", label, record)
            add_edge(entity_id, node_id, "HAS_UTILITY_METER", 0.9, evidence)
        elif record["record_type"] == "property":
            node_id = f"PROP-{record.get('registry_no') or source_ref}"
            label = str(record.get("property_type") or "Property")
            add_node(node_id, "Property", label, record)
            add_edge(entity_id, node_id, "BOUGHT_PROPERTY", 0.9, evidence)
        elif record["record_type"] == "offshore_entity":
            entity_name = str(record.get("offshore_entity_name") or "Offshore Entity").strip()
            node_id = stable_id(
                "OFFSHORE",
                f"{entity_name}:{record.get('offshore_jurisdiction') or ''}:{record.get('offshore_source') or ''}",
            )
            label = entity_name
            add_node(node_id, "OffshoreEntity", label, record)
            add_edge(entity_id, node_id, "LINKED_TO_OFFSHORE_ENTITY", 0.95, evidence)

    for norm_address, entity_ids in address_to_entities.items():
        sorted_ids = sorted(entity_ids)
        for idx, left in enumerate(sorted_ids):
            for right in sorted_ids[idx + 1 :]:
                add_edge(left, right, "SAME_ADDRESS_AS", 0.75, {"normalized_address": norm_address})
                add_edge(right, left, "SAME_ADDRESS_AS", 0.75, {"normalized_address": norm_address})

    for phone, entity_ids in phone_to_entities.items():
        sorted_ids = sorted(entity_ids)
        for idx, left in enumerate(sorted_ids):
            for right in sorted_ids[idx + 1 :]:
                add_edge(left, right, "SHARES_PHONE_WITH", 0.95, {"phone_suffix": phone[-4:]})
                add_edge(right, left, "SHARES_PHONE_WITH", 0.95, {"phone_suffix": phone[-4:]})

    for national_id, entity_ids in national_id_to_entities.items():
        sorted_ids = sorted(entity_ids)
        for idx, left in enumerate(sorted_ids):
            for right in sorted_ids[idx + 1 :]:
                add_edge(left, right, "SHARES_NATIONAL_ID_WITH", 1.0, {"national_id_prefix": national_id[:5]})
                add_edge(right, left, "SHARES_NATIONAL_ID_WITH", 1.0, {"national_id_prefix": national_id[:5]})

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "entity_records": dict(entity_records),
        "summary": {
            "nodes": len(nodes),
            "edges": len(edges),
            "persons": sum(1 for node in nodes.values() if node["type"] == "Person"),
            "assets": sum(1 for node in nodes.values() if node["type"] in {"Vehicle", "Property", "Meter"}),
        },
    }
