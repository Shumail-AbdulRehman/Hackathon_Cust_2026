"""Load and sample the ICIJ Offshore Leaks CSVs into TaxNet-compatible datasets.

Uses Polars for fast CSV reads and joins. The ICIJ Offshore Leaks Database is a
real-world graph of offshore entities, officers, intermediaries, addresses, and
their relationships. This loader maps it onto the TaxNet canonical record model.

Download URL:
    https://offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl

DATA_DIR = Path("data/icij-offshore-leaks")

NODE_FILES = {
    "addresses": "nodes-addresses.csv",
    "entities": "nodes-entities.csv",
    "intermediaries": "nodes-intermediaries.csv",
    "officers": "nodes-officers.csv",
    "others": "nodes-others.csv",
}

RELATIONSHIP_FILE = "relationships.csv"


NODE_COLUMNS: dict[str, dict[str, pl.DataType]] = {
    "addresses": {"node_id": pl.Int64, "address": pl.Utf8},
    "entities": {
        "node_id": pl.Int64,
        "name": pl.Utf8,
        "original_name": pl.Utf8,
        "jurisdiction": pl.Utf8,
        "jurisdiction_description": pl.Utf8,
        "status": pl.Utf8,
        "service_provider": pl.Utf8,
        "address": pl.Utf8,
        "sourceID": pl.Utf8,
        "incorporation_date": pl.Utf8,
        "inactivation_date": pl.Utf8,
        "struck_off_date": pl.Utf8,
        "countries": pl.Utf8,
    },
    "intermediaries": {"node_id": pl.Int64, "name": pl.Utf8, "countries": pl.Utf8},
    "officers": {"node_id": pl.Int64, "name": pl.Utf8, "countries": pl.Utf8},
    "others": {"node_id": pl.Int64, "name": pl.Utf8, "countries": pl.Utf8},
}

REL_COLUMNS: dict[str, pl.DataType] = {
    "node_id_start": pl.Int64,
    "node_id_end": pl.Int64,
    "rel_type": pl.Utf8,
    "link": pl.Utf8,
    "status": pl.Utf8,
    "start_date": pl.Utf8,
    "end_date": pl.Utf8,
    "sourceID": pl.Utf8,
}


def _read_csv(path: Path, columns: dict[str, pl.DataType] | None = None) -> pl.DataFrame:
    """Read a CSV with Polars, using explicit string-safe dtypes."""
    return pl.read_csv(path, columns=list(columns.keys()) if columns else None, schema_overrides=columns, null_values=["", "NULL", "N/A"])


def sample_icij_graph(
    data_dir: Path | None = None,
    max_entities: int = 10_000,
    seed: int = 42,
    hop_radius: int = 1,
) -> tuple[set[int], pl.DataFrame]:
    """Sample a connected subgraph around randomly chosen offshore entities.

    Reads the full relationships file once (Polars is memory-mapped fast), keeps
    rows touching the seed entities, expands by ``hop_radius`` hops, and returns
    the kept node IDs plus the filtered relationships DataFrame.
    """
    data_dir = Path(data_dir or DATA_DIR)

    entity_path = data_dir / NODE_FILES["entities"]
    if not entity_path.exists():
        raise FileNotFoundError(f"Missing ICIJ entities file: {entity_path}")

    entities = _read_csv(entity_path, columns=NODE_COLUMNS["entities"]).select("node_id")
    entity_count = entities.height
    if entity_count <= max_entities:
        seed_entities = set(int(x) for x in entities["node_id"].to_list())
    else:
        seed_entities = set(
            int(x)
            for x in entities.sample(n=max_entities, seed=seed)["node_id"].to_list()
        )

    rel_path = data_dir / RELATIONSHIP_FILE
    if not rel_path.exists():
        raise FileNotFoundError(f"Missing ICIJ relationships file: {rel_path}")

    relationships = _read_csv(rel_path, columns=REL_COLUMNS)

    kept: set[int] = set(seed_entities)
    frontier: set[int] = set(seed_entities)

    for _ in range(hop_radius):
        if not frontier:
            break
        frontier_df = pl.DataFrame({"node_id": list(frontier)}).with_columns(pl.col("node_id").cast(pl.Int64))
        touched = (
            relationships.join(frontier_df, left_on="node_id_start", right_on="node_id", how="semi")
            .vstack(
                relationships.join(frontier_df, left_on="node_id_end", right_on="node_id", how="semi")
            )
            .unique()
        )
        start_neighbors = (
            touched.join(frontier_df, left_on="node_id_start", right_on="node_id", how="semi")
            .select(pl.col("node_id_end").alias("neighbor"))
        )
        end_neighbors = (
            touched.join(frontier_df, left_on="node_id_end", right_on="node_id", how="semi")
            .select(pl.col("node_id_start").alias("neighbor"))
        )
        new_nodes = set(int(x) for x in start_neighbors["neighbor"].to_list())
        new_nodes.update(int(x) for x in end_neighbors["neighbor"].to_list())
        next_frontier = new_nodes - kept
        kept.update(new_nodes)
        frontier = next_frontier

    kept_df = pl.DataFrame({"node_id": list(kept)}).with_columns(pl.col("node_id").cast(pl.Int64))
    sampled = (
        relationships.join(kept_df, left_on="node_id_start", right_on="node_id", how="semi")
        .join(kept_df, left_on="node_id_end", right_on="node_id", how="semi")
    )

    return kept, sampled


def build_icij_datasets(
    data_dir: Path | None = None,
    max_entities: int = 10_000,
    seed: int = 42,
    hop_radius: int = 1,
) -> dict[str, list[dict[str, Any]]]:
    """Build TaxNet-compatible datasets from ICIJ Offshore Leaks.

    Returns a dict of ``{dataset_name: [rows]}`` that can be passed directly to
    ``taxnet.pipeline.run_pipeline(datasets=...)``.
    """
    data_dir = Path(data_dir or DATA_DIR)
    kept_node_ids, sampled_relationships = sample_icij_graph(
        data_dir=data_dir, max_entities=max_entities, seed=seed, hop_radius=hop_radius
    )

    kept_df = pl.DataFrame({"node_id": list(kept_node_ids)}).with_columns(pl.col("node_id").cast(pl.Int64))

    nodes: dict[str, pl.DataFrame] = {}
    for node_type, filename in NODE_FILES.items():
        path = data_dir / filename
        df = _read_csv(path, columns=NODE_COLUMNS[node_type])
        df = df.join(kept_df, on="node_id", how="semi")
        nodes[node_type] = df

    # Concatenate all node types into one lookup table with a type label.
    typed_nodes: list[pl.DataFrame] = []
    for node_type, df in nodes.items():
        typed_nodes.append(df.with_columns(pl.lit(node_type).alias("_node_type")))
    all_nodes = pl.concat(typed_nodes, how="diagonal_relaxed")

    node_lookup = {
        int(row["node_id"]): row
        for row in all_nodes.to_dicts()
        if row.get("node_id") is not None
    }

    # Build entity -> address mapping from registered_address relationships.
    entity_to_address: dict[int, str] = {}
    address_nodes = nodes.get("addresses")
    if address_nodes is not None and address_nodes.height > 0:
        address_lookup = {
            int(row["node_id"]): str(row.get("address") or "").strip()
            for row in address_nodes.to_dicts()
            if row.get("node_id") is not None
        }
        addr_rels = sampled_relationships.filter(
            pl.col("rel_type").str.to_lowercase().str.replace_all(" ", "_") == "registered_address"
        )
        for row in addr_rels.to_dicts():
            start_id = row.get("node_id_start")
            end_id = row.get("node_id_end")
            if start_id is None or end_id is None:
                continue
            start_id, end_id = int(start_id), int(end_id)
            address = address_lookup.get(end_id, "").strip()
            if address and start_id not in entity_to_address:
                entity_to_address[start_id] = address

    # Create canonical records from person-like -> entity-like relationships.
    records: list[dict[str, Any]] = []
    seen_pairs: set[tuple[int, int, str]] = set()

    non_address_rels = sampled_relationships.filter(
        pl.col("rel_type").str.to_lowercase().str.replace_all(" ", "_") != "registered_address"
    )

    for row in non_address_rels.to_dicts():
        rel_type = str(row.get("rel_type") or "").lower().replace(" ", "_")
        start_id = row.get("node_id_start")
        end_id = row.get("node_id_end")
        if start_id is None or end_id is None:
            continue
        start_id, end_id = int(start_id), int(end_id)

        start_node = node_lookup.get(start_id, {})
        end_node = node_lookup.get(end_id, {})
        start_type = start_node.get("_node_type", "")
        end_type = end_node.get("_node_type", "")

        person_node: dict[str, Any] | None = None
        entity_node: dict[str, Any] | None = None
        direction = ""

        if start_type in {"officers", "intermediaries", "others"} and end_type == "entities":
            person_node = start_node
            entity_node = end_node
            direction = f"{start_type}->{end_type}"
        elif start_type == "entities" and end_type in {"officers", "intermediaries", "others"}:
            person_node = end_node
            entity_node = start_node
            direction = f"{end_type}->{start_type}"
        else:
            continue

        person_id = int(person_node.get("node_id") or 0)
        entity_id = int(entity_node.get("node_id") or 0)
        pair_key = (person_id, entity_id, rel_type)
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)

        primary_address = entity_to_address.get(entity_id, "").strip()
        if not primary_address:
            primary_address = str(entity_node.get("address") or "").strip()

        person_countries = str(person_node.get("countries") or "").strip()
        person_name = str(person_node.get("name") or "").strip()

        records.append(
            {
                "source_row_id": f"icij-{start_id}-{end_id}-{rel_type}",
                "national_id": str(person_id),
                "person_name": person_name,
                "address": primary_address or person_countries,
                "offshore_entity_name": str(entity_node.get("name") or "").strip(),
                "offshore_jurisdiction": str(entity_node.get("jurisdiction") or "").strip(),
                "offshore_jurisdiction_description": str(entity_node.get("jurisdiction_description") or "").strip(),
                "offshore_status": str(entity_node.get("status") or "").strip(),
                "offshore_source": str(entity_node.get("sourceID") or "").strip(),
                "offshore_service_provider": str(entity_node.get("service_provider") or "").strip(),
                "offshore_incorporation_date": str(entity_node.get("incorporation_date") or "").strip(),
                "offshore_inactivation_date": str(entity_node.get("inactivation_date") or "").strip(),
                "offshore_struck_off_date": str(entity_node.get("struck_off_date") or "").strip(),
                "offshore_relationship": rel_type,
                "offshore_relationship_direction": direction,
                "offshore_person_countries": person_countries,
                "offshore_entity_countries": str(entity_node.get("countries") or "").strip(),
                "_kind": "offshore_entity",
            }
        )

    return {"icij-offshore-leaks": records}
