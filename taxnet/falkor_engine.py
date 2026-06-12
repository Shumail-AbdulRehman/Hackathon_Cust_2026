"""FalkorDB graph loader and analytics."""

from __future__ import annotations

import os
from typing import Any


def _get_falkordb_module() -> Any:
    try:
        from falkordb import FalkorDB

        return FalkorDB
    except ImportError as exc:
        raise RuntimeError(
            "falkordb package is not installed. Run: uv add falkordb "
            "or start the container with: uv run python scripts/setup_falkordb.py"
        ) from exc


def get_falkordb_client() -> Any:
    FalkorDB = _get_falkordb_module()
    host = os.getenv("FALKORDB_HOST", "localhost")
    port = int(os.getenv("FALKORDB_PORT", "6379"))
    return FalkorDB(host=host, port=port)


def _stable_id(prefix: str, value: object) -> str:
    import hashlib

    digest = hashlib.sha1(str(value).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def load_graph(
    graph_name: str,
    records: list[dict[str, Any]],
    resolution: dict[str, Any],
) -> dict[str, Any]:
    db = get_falkordb_client()
    graph = db.select_graph(graph_name)

    # Idempotent reload: delete existing graph if present.
    try:
        graph.delete()
    except Exception:
        pass
    graph = db.select_graph(graph_name)

    record_to_entity = resolution["record_to_entity"]

    for entity in resolution["entities"]:
        graph.query(
            "MERGE (p:Person {entity_id: $entity_id}) SET p.name = $name",
            {"entity_id": entity["entity_id"], "name": entity["canonical_name"]},
        )

    for record in records:
        source_ref = f"{record['source_dataset']}:{record['source_row_id']}"
        entity_id = record_to_entity.get(source_ref)
        if not entity_id:
            continue

        if record["record_type"] == "vehicle":
            vid = record.get("vehicle_reg_no") or source_ref
            graph.query(
                "MATCH (p:Person {entity_id: $entity_id}) "
                "MERGE (v:Vehicle {id: $vid}) SET v.make_model = $make, v.engine_cc = $cc "
                "MERGE (p)-[:OWNS_VEHICLE {confidence: 0.9}]->(v)",
                {
                    "entity_id": entity_id,
                    "vid": vid,
                    "make": str(record.get("vehicle_make_model") or ""),
                    "cc": float(record.get("engine_capacity_cc") or 0),
                },
            )
        elif record["record_type"] == "property":
            pid = record.get("registry_no") or source_ref
            graph.query(
                "MATCH (p:Person {entity_id: $entity_id}) "
                "MERGE (pr:Property {id: $pid}) SET pr.value = $value, pr.area_marla = $area "
                "MERGE (p)-[:BOUGHT_PROPERTY {confidence: 0.9}]->(pr)",
                {
                    "entity_id": entity_id,
                    "pid": pid,
                    "value": float(record.get("property_value") or 0),
                    "area": float(record.get("area_marla") or 0),
                },
            )
        elif record["record_type"] == "utility":
            mid = record.get("meter_ref_no") or source_ref
            graph.query(
                "MATCH (p:Person {entity_id: $entity_id}) "
                "MERGE (m:Meter {id: $mid}) SET m.monthly_bill = $bill "
                "MERGE (p)-[:HAS_UTILITY_METER {confidence: 0.9}]->(m)",
                {
                    "entity_id": entity_id,
                    "mid": mid,
                    "bill": float(record.get("monthly_bill") or 0),
                },
            )
        elif record["record_type"] == "tax":
            tid = source_ref
            graph.query(
                "MATCH (p:Person {entity_id: $entity_id}) "
                "MERGE (t:TaxReturn {id: $tid}) SET t.income = $income, t.tax_paid = $tax, t.filer_status = $status "
                "MERGE (p)-[:FILED_IN {confidence: 1.0}]->(t)",
                {
                    "entity_id": entity_id,
                    "tid": tid,
                    "income": float(record.get("declared_income") or 0),
                    "tax": float(record.get("tax_paid") or 0),
                    "status": str(record.get("filer_status") or ""),
                },
            )

        address_norm = str(record.get("address") or "")
        if address_norm:
            aid = _stable_id("ADDR", address_norm)
            graph.query(
                "MATCH (p:Person {entity_id: $entity_id}) "
                "MERGE (a:Address {id: $aid}) SET a.text = $text "
                "MERGE (p)-[:USES_ADDRESS {confidence: 0.8}]->(a)",
                {"entity_id": entity_id, "aid": aid, "text": address_norm},
            )

        phone_norm = str(record.get("phone") or "")
        if phone_norm:
            phid = f"PHONE:{phone_norm}"
            graph.query(
                "MATCH (p:Person {entity_id: $entity_id}) "
                "MERGE (ph:PhoneNumber {id: $phid}) SET ph.number = $number "
                "MERGE (p)-[:USES_PHONE {confidence: 0.95}]->(ph)",
                {"entity_id": entity_id, "phid": phid, "number": phone_norm},
            )

    graph.query(
        "MATCH (p1:Person)-[:USES_ADDRESS]->(a:Address)<-[:USES_ADDRESS]-(p2:Person) "
        "WHERE p1 <> p2 "
        "MERGE (p1)-[:SAME_ADDRESS_AS {confidence: 0.75}]->(p2)"
    )
    graph.query(
        "MATCH (p1:Person)-[:USES_PHONE]->(ph:PhoneNumber)<-[:USES_PHONE]-(p2:Person) "
        "WHERE p1 <> p2 "
        "MERGE (p1)-[:SHARES_PHONE_WITH {confidence: 0.95}]->(p2)"
    )

    node_result = graph.query("MATCH (n) RETURN count(n) AS c")
    edge_result = graph.query("MATCH ()-[r]->() RETURN count(r) AS c")
    node_count = _extract_count(node_result)
    edge_count = _extract_count(edge_result)
    return {"graph_name": graph_name, "nodes": node_count, "edges": edge_count}


def _extract_count(query_result: Any) -> int:
    """Handle different FalkorDB result shapes."""
    try:
        if hasattr(query_result, "result_set"):
            return int(query_result.result_set[0][0])
        return int(query_result[0]["c"])
    except Exception:
        return 0


def _extract_rows(query_result: Any) -> list[dict[str, Any]]:
    """Handle different FalkorDB result shapes."""
    try:
        if hasattr(query_result, "result_set"):
            rows = []
            for row in query_result.result_set:
                rows.append({key: row[idx] for idx, key in enumerate(query_result.header)})
            return rows
        return list(query_result)
    except Exception:
        return []


def run_pagerank(graph_name: str) -> dict[str, float]:
    db = get_falkordb_client()
    graph = db.select_graph(graph_name)
    try:
        result = graph.query(
            "CALL pagerank() YIELD node, score RETURN node.entity_id AS entity_id, score"
        )
        rows = _extract_rows(result)
        return {row["entity_id"]: float(row["score"]) for row in rows if row.get("entity_id")}
    except Exception:
        return {}


def run_communities(graph_name: str) -> dict[str, int]:
    db = get_falkordb_client()
    graph = db.select_graph(graph_name)
    try:
        result = graph.query(
            "CALL weakly_connected_components() YIELD node, componentId "
            "RETURN node.entity_id AS entity_id, componentId"
        )
        rows = _extract_rows(result)
        return {row["entity_id"]: int(row["componentId"]) for row in rows if row.get("entity_id")}
    except Exception:
        return {}


def run_degrees(graph_name: str) -> dict[str, int]:
    db = get_falkordb_client()
    graph = db.select_graph(graph_name)
    try:
        result = graph.query(
            "MATCH (p:Person)-[r]-(other) "
            "RETURN p.entity_id AS entity_id, count(other) AS degree"
        )
        rows = _extract_rows(result)
        return {row["entity_id"]: int(row["degree"]) for row in rows if row.get("entity_id")}
    except Exception:
        return {}


def shortest_path(graph_name: str, source: str, target: str) -> list[dict[str, Any]] | None:
    db = get_falkordb_client()
    graph = db.select_graph(graph_name)
    try:
        result = graph.query(
            "MATCH path = shortestPath((src:Person {entity_id: $source})-[:SAME_ADDRESS_AS|SHARES_PHONE_WITH*]-(tgt:Person {entity_id: $target})) "
            "RETURN [n in nodes(path) | n.entity_id] AS node_ids, length(path) AS hops",
            {"source": source, "target": target},
        )
        rows = _extract_rows(result)
        if rows:
            return rows[0]
        return None
    except Exception:
        return None
