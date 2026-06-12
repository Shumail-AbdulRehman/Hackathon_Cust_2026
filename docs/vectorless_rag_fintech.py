"""
Vectorless RAG — Fintech Forensic / Tax Evasion Analysis
=========================================================
Stack: Polars (lazy streaming) + DuckDB (FTS + SQL) + FalkorDB (graph traversal)

API sources used:
  - Polars scan_parquet / collect(engine="streaming") / sink_parquet:
      https://docs.pola.rs/user-guide/lazy/sources_sinks/
  - DuckDB FTS extension (PRAGMA create_fts_index / stem() / match_bm25()):
      https://duckdb.org/docs/current/core_extensions/full_text_search
  - DuckDB register() for zero-copy from Polars Arrow:
      https://duckdb.org/docs/current/clients/python/data_ingestion
  - FalkorDB Python client + Cypher (v1.2.x):
      https://docs.falkordb.com/  and  https://orchestrator.dev/blog/2025-12-11-falkordb/
  - FalkorDB GraphRAG-SDK schema / ingest / query:
      https://falkordb.github.io/GraphRAG-SDK/getting-started/

Install:
    pip install polars duckdb falkordb spacy
    python -m spacy download en_core_web_sm
    # Optional — only needed if you want FalkorDB GraphRAG-SDK for document ingestion:
    # pip install "graphrag-sdk[all]"

Run FalkorDB (Docker):
    docker run -d --name falkordb -p 6379:6379 falkordb/falkordb
"""

from __future__ import annotations

import os
import json
import logging
from typing import Optional
from dataclasses import dataclass, field

import polars as pl
import duckdb
import spacy
from falkordb import FalkorDB

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("vectorless_rag")


# ---------------------------------------------------------------------------
# 1.  SCHEMA — what entities and relationships we care about
# ---------------------------------------------------------------------------

FINTECH_ENTITY_LABELS = {
    "Person": "Natural person — individual taxpayer, beneficial owner, director",
    "Company": "Legal entity — shell company, holding, SPV, operating company",
    "Account": "Bank / crypto / broker account",
    "Transaction": "Individual financial transaction",
    "Jurisdiction": "Country or territory relevant to a filing or incorporation",
    "Filing": "Tax filing, regulatory report, SAR, CTR",
}

FINTECH_REL_LABELS = {
    "CONTROLS": "Person or Company controls another Company or Account",
    "OWNS": "Beneficial ownership stake",
    "TRANSFERS_TO": "Account transfers funds to another Account",
    "FILED": "Person or Company filed a regulatory document",
    "INCORPORATED_IN": "Company incorporated in a Jurisdiction",
    "DIRECTOR_OF": "Person is director / officer of a Company",
    "ALIAS_OF": "Two nodes refer to the same real-world entity (deduplication edge)",
}


# ---------------------------------------------------------------------------
# 2.  POLARS LAYER — lazy streaming ingestion + NER batch
# ---------------------------------------------------------------------------

class PolarsPipeline:
    """
    Reads large financial datasets (CSV / Parquet) without loading them fully
    into memory.  Uses scan_parquet + collect(engine='streaming') per the
    official Polars streaming docs (https://docs.pola.rs/user-guide/lazy/sources_sinks/).

    NER runs on batches via map_elements so spaCy never sees the full frame.
    """

    def __init__(self, spacy_model: str = "en_core_web_sm"):
        self.nlp = spacy.load(spacy_model)
        log.info("spaCy model loaded: %s", spacy_model)

    # ------------------------------------------------------------------
    # 2a.  Lazy scan — push predicates down into the reader
    # ------------------------------------------------------------------
    def scan_transactions(self, path: str) -> pl.LazyFrame:
        """
        Accepts a glob ("data/txns/*.parquet"), a single file, or a directory.
        Polars pushes the filter predicates into the Parquet row-group reader,
        skipping groups that don't match — no full load needed.
        """
        lf = pl.scan_parquet(path)
        log.info("LazyFrame created for: %s  (no data loaded yet)", path)
        return lf

    # ------------------------------------------------------------------
    # 2b.  Suspicious-pattern pre-filter (streaming-safe operations)
    # ------------------------------------------------------------------
    def filter_suspicious(self, lf: pl.LazyFrame) -> pl.LazyFrame:
        """
        Pre-filter to structuring patterns and large round-dollar amounts.
        All operations here are streaming-compatible (filter, with_columns).

        Structuring = splitting deposits just below $10,000 CTR threshold.
        """
        return (
            lf
            # Keep rows that match at least one suspicious-amount band
            .filter(
                # Classic structuring band: just below CTR threshold
                (pl.col("amount").is_between(9_000, 9_999))
                # Large round-dollar amounts (common in layering)
                | ((pl.col("amount") % 1_000 == 0) & (pl.col("amount") >= 50_000))
                # Rapid small transactions that aggregate large (smurfing)
                | (pl.col("amount").is_between(500, 3_000))
            )
            .with_columns(
                # Normalise entity_id to string for consistent joins
                pl.col("entity_id").cast(pl.Utf8).alias("entity_id"),
                # Flag the band reason for downstream context
                pl.when(pl.col("amount").is_between(9_000, 9_999))
                  .then(pl.lit("structuring"))
                  .when((pl.col("amount") % 1_000 == 0) & (pl.col("amount") >= 50_000))
                  .then(pl.lit("round_dollar"))
                  .otherwise(pl.lit("smurfing"))
                  .alias("flag_reason"),
            )
        )

    # ------------------------------------------------------------------
    # 2c.  Collect with streaming engine
    # ------------------------------------------------------------------
    def collect_streaming(self, lf: pl.LazyFrame) -> pl.DataFrame:
        """
        Materialise the lazy query using the streaming engine.
        Polars processes data in small batches — constant memory profile.
        Note: not all operations are streaming-safe; Polars falls back
        to the standard engine for those automatically.
        """
        df = lf.collect(engine="streaming")
        log.info("Collected %d rows via streaming engine", len(df))
        return df

    # ------------------------------------------------------------------
    # 2d.  Sink directly to Parquet (for truly huge outputs)
    # ------------------------------------------------------------------
    def sink_suspicious(self, lf: pl.LazyFrame, out_path: str) -> None:
        """
        Write filtered results to Parquet without materialising in memory.
        sink_parquet always uses the streaming engine.
        Source: https://docs.pola.rs/api/python/dev/reference/api/polars.LazyFrame.sink_parquet.html
        """
        self.filter_suspicious(lf).sink_parquet(out_path, compression="zstd")
        log.info("Sunk suspicious transactions to %s", out_path)

    # ------------------------------------------------------------------
    # 2e.  NER on narrative / memo fields
    # ------------------------------------------------------------------
    def extract_entities_from_text_col(
        self, df: pl.DataFrame, text_col: str = "memo"
    ) -> pl.DataFrame:
        """
        Run spaCy NER over a text column.
        map_elements processes one cell at a time; batching is handled
        by Polars internals.  Returns the original frame plus an
        'ner_entities' column containing a JSON list of {text, label} dicts.
        """

        def _ner(text: Optional[str]) -> str:
            if not text:
                return "[]"
            doc = self.nlp(str(text))
            entities = [
                {"text": ent.text, "label": ent.label_}
                for ent in doc.ents
                if ent.label_ in {"ORG", "PERSON", "GPE", "MONEY", "DATE"}
            ]
            return json.dumps(entities)

        return df.with_columns(
            pl.col(text_col)
              .map_elements(_ner, return_dtype=pl.Utf8)
              .alias("ner_entities")
        )


# ---------------------------------------------------------------------------
# 3.  DUCKDB LAYER — structured SQL retrieval (no embeddings)
# ---------------------------------------------------------------------------

class DuckDBRetriever:
    """
    Vectorless structured retrieval using DuckDB.

    - Registers Polars DataFrames as virtual tables (zero-copy via Arrow)
    - PRAGMA create_fts_index builds BM25 full-text index on memo/narrative fields
    - SQL queries detect financial-crime patterns deterministically

    FTS extension docs: https://duckdb.org/docs/current/core_extensions/full_text_search
    """

    def __init__(self):
        # In-memory DuckDB; use duckdb.connect("forensics.duckdb") for persistence
        self.con = duckdb.connect()
        self.con.execute("INSTALL fts; LOAD fts;")
        log.info("DuckDB connection established; FTS extension loaded")
        self._fts_built: set[str] = set()

    # ------------------------------------------------------------------
    # 3a.  Register Polars DataFrame (zero-copy, Arrow-backed)
    # ------------------------------------------------------------------
    def register(self, name: str, df: pl.DataFrame) -> None:
        """
        Expose a Polars DataFrame as a DuckDB table.
        DuckDB reads the Arrow format directly — no serialisation.
        Source: https://duckdb.org/docs/current/clients/python/data_ingestion
        """
        self.con.register(name, df)
        log.info("Registered '%s' in DuckDB (%d rows)", name, len(df))

    # ------------------------------------------------------------------
    # 3b.  Build FTS index on a text column
    # ------------------------------------------------------------------
    def build_fts_index(
        self,
        table: str,
        id_col: str = "tx_id",
        text_col: str = "memo",
        stemmer: str = "porter",
    ) -> None:
        """
        Create a BM25 full-text index.
        PRAGMA create_fts_index autoloads the fts extension.
        Source: https://duckdb.org/docs/current/core_extensions/full_text_search

        Args:
            table:    name of the registered DuckDB table
            id_col:   unique row identifier column
            text_col: column(s) to index — can pass multiple as positional args
            stemmer:  'porter' | 'english' | 'none'
        """
        if table in self._fts_built:
            return
        pragma = (
            f"PRAGMA create_fts_index('{table}', '{id_col}', '{text_col}', "
            f"stemmer='{stemmer}', overwrite=1);"
        )
        self.con.execute(pragma)
        self._fts_built.add(table)
        log.info("FTS index built on %s.%s", table, text_col)

    # ------------------------------------------------------------------
    # 3c.  BM25 keyword search (vectorless semantic-like retrieval)
    # ------------------------------------------------------------------
    def keyword_search(
        self, table: str, query: str, limit: int = 20
    ) -> pl.DataFrame:
        """
        Full-text BM25 search using match_bm25().
        Returns rows ranked by relevance score.
        Source: https://duckdb.org/docs/current/core_extensions/full_text_search
        """
        sql = f"""
            SELECT *, fts_main_{table}.match_bm25(tx_id, '{query}') AS bm25_score
            FROM {table}
            WHERE bm25_score IS NOT NULL
            ORDER BY bm25_score DESC
            LIMIT {limit};
        """
        result = self.con.execute(sql).pl()
        log.info("BM25 search '%s' → %d results", query, len(result))
        return result

    # ------------------------------------------------------------------
    # 3d.  Structuring detection (amounts just below CTR threshold)
    # ------------------------------------------------------------------
    def detect_structuring(
        self,
        table: str = "txns",
        threshold: float = 10_000.0,
        band: float = 1_000.0,
        min_count: int = 3,
    ) -> pl.DataFrame:
        """
        Classic structuring (smurfing) detection:
        entities that make multiple deposits in the band [threshold-band, threshold)
        within a rolling 24-hour window.

        Returns aggregated suspects with tx_count and total_amount.
        """
        sql = f"""
            WITH suspect_txns AS (
                SELECT
                    entity_id,
                    amount,
                    ts,
                    COUNT(*) OVER (
                        PARTITION BY entity_id
                        ORDER BY ts
                        RANGE BETWEEN INTERVAL 24 HOURS PRECEDING AND CURRENT ROW
                    ) AS rolling_24h_count,
                    SUM(amount) OVER (
                        PARTITION BY entity_id
                        ORDER BY ts
                        RANGE BETWEEN INTERVAL 24 HOURS PRECEDING AND CURRENT ROW
                    ) AS rolling_24h_sum
                FROM {table}
                WHERE amount BETWEEN {threshold - band} AND {threshold - 0.01}
            )
            SELECT
                entity_id,
                COUNT(*) AS tx_count,
                SUM(amount) AS total_amount,
                MIN(ts) AS first_tx,
                MAX(ts) AS last_tx,
                MAX(rolling_24h_count) AS max_24h_burst
            FROM suspect_txns
            GROUP BY entity_id
            HAVING tx_count >= {min_count}
            ORDER BY total_amount DESC;
        """
        result = self.con.execute(sql).pl()
        log.info("Structuring scan → %d suspects", len(result))
        return result

    # ------------------------------------------------------------------
    # 3e.  Layering detection (rapid pass-through transactions)
    # ------------------------------------------------------------------
    def detect_layering(
        self, table: str = "txns", minutes_window: int = 60
    ) -> pl.DataFrame:
        """
        Layering: money received and immediately re-sent within a short window.
        Entities where inflow ≈ outflow within `minutes_window` minutes.
        """
        sql = f"""
            WITH inflow AS (
                SELECT dest_entity_id AS entity_id, SUM(amount) AS in_total, ts
                FROM {table}
                GROUP BY dest_entity_id, ts
            ),
            outflow AS (
                SELECT entity_id, SUM(amount) AS out_total, ts
                FROM {table}
                GROUP BY entity_id, ts
            ),
            matched AS (
                SELECT
                    i.entity_id,
                    i.in_total,
                    o.out_total,
                    ABS(i.in_total - o.out_total) / NULLIF(i.in_total, 0) AS ratio_diff,
                    i.ts AS in_ts,
                    o.ts AS out_ts,
                    DATEDIFF('minute', i.ts, o.ts) AS lag_minutes
                FROM inflow i
                JOIN outflow o
                  ON i.entity_id = o.entity_id
                 AND o.ts BETWEEN i.ts AND i.ts + INTERVAL '{minutes_window} minutes'
            )
            SELECT *
            FROM matched
            WHERE ratio_diff < 0.05          -- outflow within 5% of inflow
              AND lag_minutes <= {minutes_window}
            ORDER BY in_total DESC
            LIMIT 100;
        """
        result = self.con.execute(sql).pl()
        log.info("Layering scan → %d suspect flows", len(result))
        return result

    # ------------------------------------------------------------------
    # 3f.  Entity aggregate summary (for RAG context block)
    # ------------------------------------------------------------------
    def entity_summary(self, table: str, entity_id: str) -> pl.DataFrame:
        sql = f"""
            SELECT
                entity_id,
                COUNT(*)                      AS total_txns,
                SUM(amount)                   AS total_volume,
                AVG(amount)                   AS avg_amount,
                MIN(ts)                       AS first_seen,
                MAX(ts)                       AS last_seen,
                COUNT(DISTINCT dest_entity_id) AS unique_counterparties
            FROM {table}
            WHERE entity_id = '{entity_id}'
            GROUP BY entity_id;
        """
        return self.con.execute(sql).pl()

    # ------------------------------------------------------------------
    # 3g.  Arbitrary SQL passthrough (for ad-hoc LLM-generated queries)
    # ------------------------------------------------------------------
    def query(self, sql: str) -> pl.DataFrame:
        return self.con.execute(sql).pl()


# ---------------------------------------------------------------------------
# 4.  FALKORDB LAYER — entity graph (ownership chains, relationship traversal)
# ---------------------------------------------------------------------------

class FalkorDBGraph:
    """
    Graph-based retrieval using FalkorDB's OpenCypher interface.

    Source:
      https://docs.falkordb.com/
      https://orchestrator.dev/blog/2025-12-11-falkordb/
      https://www.falkordb.com/news-updates/data-retrieval-graphrag-ai-agents/
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        graph_name: str = "fintech_forensics",
    ):
        db = FalkorDB(host=host, port=port)
        self.graph = db.select_graph(graph_name)
        self._init_schema()
        log.info("FalkorDB connected — graph: %s", graph_name)

    # ------------------------------------------------------------------
    # 4a.  Schema constraints + indexes
    # ------------------------------------------------------------------
    def _init_schema(self) -> None:
        """
        Create range indexes on commonly-queried properties.
        FalkorDB indexing docs: https://docs.falkordb.com/cypher/indexing/range-index.html
        """
        index_stmts = [
            "CREATE INDEX FOR (p:Person) ON (p.name)",
            "CREATE INDEX FOR (c:Company) ON (c.name)",
            "CREATE INDEX FOR (c:Company) ON (c.reg_number)",
            "CREATE INDEX FOR (a:Account) ON (a.account_id)",
            "CREATE INDEX FOR (t:Transaction) ON (t.tx_id)",
            "CREATE INDEX FOR (t:Transaction) ON (t.amount)",
        ]
        for stmt in index_stmts:
            try:
                self.graph.query(stmt)
            except Exception:
                pass  # Index already exists — safe to ignore

    # ------------------------------------------------------------------
    # 4b.  Upsert entities extracted from Polars/DuckDB results
    # ------------------------------------------------------------------
    def upsert_entity(
        self,
        entity_id: str,
        entity_type: str,
        properties: dict,
    ) -> None:
        """
        MERGE avoids duplicates — creates node only if it doesn't exist,
        then sets / updates properties.
        """
        props_cypher = ", ".join(
            f"e.{k} = {json.dumps(v)}" for k, v in properties.items()
        )
        cypher = f"""
            MERGE (e:{entity_type} {{entity_id: '{entity_id}'}})
            SET e.entity_id = '{entity_id}', {props_cypher}
        """
        self.graph.query(cypher)

    # ------------------------------------------------------------------
    # 4c.  Upsert relationship
    # ------------------------------------------------------------------
    def upsert_relationship(
        self,
        from_id: str,
        rel_type: str,
        to_id: str,
        properties: dict | None = None,
    ) -> None:
        props_str = ""
        if properties:
            inner = ", ".join(f"{k}: {json.dumps(v)}" for k, v in properties.items())
            props_str = f" {{{inner}}}"
        cypher = f"""
            MATCH (a {{entity_id: '{from_id}'}})
            MATCH (b {{entity_id: '{to_id}'}})
            MERGE (a)-[r:{rel_type}{props_str}]->(b)
        """
        self.graph.query(cypher)

    # ------------------------------------------------------------------
    # 4d.  Bulk-load entities from a Polars DataFrame
    # ------------------------------------------------------------------
    def load_entities_from_df(
        self,
        df: pl.DataFrame,
        id_col: str,
        entity_type: str,
        property_cols: list[str],
    ) -> None:
        """
        Iterate rows and upsert.  For large frames consider FalkorDB's
        bulk loader: https://docs.falkordb.com/integration/bulk-loader.html
        """
        for row in df.iter_rows(named=True):
            props = {c: row[c] for c in property_cols if row.get(c) is not None}
            self.upsert_entity(str(row[id_col]), entity_type, props)
        log.info(
            "Loaded %d %s nodes into FalkorDB", len(df), entity_type
        )

    # ------------------------------------------------------------------
    # 4e.  Find ownership / control chains (N-hop traversal)
    # ------------------------------------------------------------------
    def find_control_chains(
        self,
        suspect_entity_id: str,
        max_hops: int = 5,
        limit: int = 50,
    ) -> list[dict]:
        """
        Variable-length path query — the core of shell-company detection.
        Returns every path from suspect to controlled accounts/companies.

        Source: FalkorDB Cypher MATCH docs
        https://docs.falkordb.com/cypher/match.html
        """
        cypher = f"""
            MATCH p=(suspect {{entity_id: '{suspect_entity_id}'}})-[:CONTROLS|OWNS*1..{max_hops}]->(target)
            RETURN
                suspect.entity_id        AS suspect_id,
                [n IN nodes(p) | coalesce(n.name, n.entity_id)]  AS chain,
                [r IN relationships(p) | type(r)]                AS rel_types,
                length(p)                                        AS depth,
                target.entity_id                                 AS target_id,
                labels(target)[0]                                AS target_type
            ORDER BY depth DESC
            LIMIT {limit}
        """
        result = self.graph.query(cypher)
        chains = []
        for row in result.result_set:
            chains.append({
                "suspect_id": row[0],
                "chain": row[1],
                "rel_types": row[2],
                "depth": row[3],
                "target_id": row[4],
                "target_type": row[5],
            })
        log.info(
            "Control chain query for '%s' → %d paths", suspect_entity_id, len(chains)
        )
        return chains

    # ------------------------------------------------------------------
    # 4f.  Find circular ownership (indicative of fictitious transactions)
    # ------------------------------------------------------------------
    def find_circular_ownership(self, limit: int = 20) -> list[dict]:
        cypher = f"""
            MATCH p=(a:Company)-[:OWNS|CONTROLS*2..6]->(a)
            RETURN
                a.name AS company_name,
                a.entity_id AS company_id,
                [n IN nodes(p) | coalesce(n.name, n.entity_id)] AS cycle,
                length(p) AS cycle_length
            ORDER BY cycle_length ASC
            LIMIT {limit}
        """
        result = self.graph.query(cypher)
        cycles = []
        for row in result.result_set:
            cycles.append({
                "company_name": row[0],
                "company_id": row[1],
                "cycle": row[2],
                "cycle_length": row[3],
            })
        log.info("Circular ownership scan → %d cycles", len(cycles))
        return cycles

    # ------------------------------------------------------------------
    # 4g.  Find beneficial owner (walk up ownership until a Person node)
    # ------------------------------------------------------------------
    def find_beneficial_owner(self, company_entity_id: str) -> list[dict]:
        cypher = f"""
            MATCH p=(owner:Person)-[:OWNS|CONTROLS*1..8]->(company {{entity_id: '{company_entity_id}'}})
            RETURN
                owner.name         AS owner_name,
                owner.entity_id    AS owner_id,
                length(p)          AS hops,
                [n IN nodes(p) | coalesce(n.name, n.entity_id)] AS ownership_path
            ORDER BY hops ASC
            LIMIT 10
        """
        result = self.graph.query(cypher)
        owners = []
        for row in result.result_set:
            owners.append({
                "owner_name": row[0],
                "owner_id": row[1],
                "hops": row[2],
                "ownership_path": row[3],
            })
        return owners

    # ------------------------------------------------------------------
    # 4h.  Degree centrality — most connected nodes (key hubs in network)
    # ------------------------------------------------------------------
    def high_degree_nodes(self, limit: int = 20) -> list[dict]:
        """
        Nodes with the highest combined in+out degree are network hubs —
        often nominee directors, shell holding companies, or key accounts.
        """
        cypher = f"""
            MATCH (n)
            RETURN
                coalesce(n.name, n.entity_id) AS name,
                n.entity_id AS entity_id,
                labels(n)[0] AS node_type,
                size((n)-->()) + size((n)<--()) AS degree
            ORDER BY degree DESC
            LIMIT {limit}
        """
        result = self.graph.query(cypher)
        return [
            {"name": r[0], "entity_id": r[1], "node_type": r[2], "degree": r[3]}
            for r in result.result_set
        ]

    # ------------------------------------------------------------------
    # 4i.  Shortest path between two entities
    # ------------------------------------------------------------------
    def shortest_path(self, from_id: str, to_id: str) -> list:
        cypher = f"""
            MATCH p=shortestPath(
                (a {{entity_id: '{from_id}'}})-[*..10]-(b {{entity_id: '{to_id}'}})
            )
            RETURN [n IN nodes(p) | coalesce(n.name, n.entity_id)] AS path,
                   length(p) AS hops
        """
        result = self.graph.query(cypher)
        if result.result_set:
            return result.result_set[0]
        return []

    # ------------------------------------------------------------------
    # 4j.  Raw Cypher passthrough (for LLM-generated queries)
    # ------------------------------------------------------------------
    def query_raw(self, cypher: str) -> list:
        result = self.graph.query(cypher)
        return result.result_set


# ---------------------------------------------------------------------------
# 5.  CONTEXT ASSEMBLER — combines DuckDB + FalkorDB results into LLM prompt
# ---------------------------------------------------------------------------

@dataclass
class ForensicContext:
    entity_id: str
    sql_summary: str = ""
    structuring_hits: list[dict] = field(default_factory=list)
    layering_hits: list[dict] = field(default_factory=list)
    keyword_hits: list[dict] = field(default_factory=list)
    ownership_chains: list[dict] = field(default_factory=list)
    circular_ownership: list[dict] = field(default_factory=list)
    beneficial_owners: list[dict] = field(default_factory=list)
    high_degree_neighbors: list[dict] = field(default_factory=list)

    def to_prompt_block(self) -> str:
        """
        Serialise all retrieved context into a structured text block
        suitable for injecting into an LLM prompt.
        No embeddings — everything is structured facts.
        """
        lines = [
            f"=== FORENSIC CONTEXT: {self.entity_id} ===",
            "",
            "--- Transaction Summary (DuckDB) ---",
            self.sql_summary or "(no data)",
            "",
        ]
        if self.structuring_hits:
            lines.append("--- Structuring Alerts (DuckDB) ---")
            for h in self.structuring_hits:
                lines.append(json.dumps(h))
            lines.append("")

        if self.layering_hits:
            lines.append("--- Layering Alerts (DuckDB) ---")
            for h in self.layering_hits:
                lines.append(json.dumps(h))
            lines.append("")

        if self.keyword_hits:
            lines.append("--- Keyword / FTS Hits (DuckDB BM25) ---")
            for h in self.keyword_hits[:5]:
                lines.append(json.dumps(h))
            lines.append("")

        if self.ownership_chains:
            lines.append("--- Ownership / Control Chains (FalkorDB) ---")
            for chain in self.ownership_chains[:10]:
                chain_str = " → ".join(chain.get("chain", []))
                lines.append(
                    f"  Depth {chain['depth']}: {chain_str}  "
                    f"(target: {chain['target_type']} {chain['target_id']})"
                )
            lines.append("")

        if self.circular_ownership:
            lines.append("--- CIRCULAR OWNERSHIP DETECTED (FalkorDB) ---")
            for c in self.circular_ownership:
                lines.append(
                    f"  {c['company_name']}  cycle_length={c['cycle_length']}  "
                    f"path={' → '.join(c['cycle'])}"
                )
            lines.append("")

        if self.beneficial_owners:
            lines.append("--- Beneficial Owners (FalkorDB) ---")
            for o in self.beneficial_owners:
                lines.append(
                    f"  {o['owner_name']} via {o['hops']} hops: "
                    + " → ".join(o["ownership_path"])
                )
            lines.append("")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 6.  ORCHESTRATOR — ties everything together
# ---------------------------------------------------------------------------

class VectorlessRAG:
    """
    Main entry point.  Wires Polars → DuckDB → FalkorDB → context assembly.

    Usage:
        rag = VectorlessRAG()
        rag.ingest_transactions("data/transactions.parquet")
        context = rag.retrieve("ENT_001", keywords="offshore cayman shell")
        answer = rag.generate_finding(context, question="Is this entity evading tax?")
    """

    def __init__(
        self,
        falkordb_host: str = "localhost",
        falkordb_port: int = 6379,
        graph_name: str = "fintech_forensics",
        spacy_model: str = "en_core_web_sm",
        anthropic_api_key: str | None = None,
    ):
        self.polars = PolarsPipeline(spacy_model=spacy_model)
        self.duckdb = DuckDBRetriever()
        self.graph = FalkorDBGraph(
            host=falkordb_host, port=falkordb_port, graph_name=graph_name
        )
        self._api_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._table_registered = False

    # ------------------------------------------------------------------
    # 6a.  Ingest
    # ------------------------------------------------------------------
    def ingest_transactions(
        self,
        path: str,
        text_col: str | None = "memo",
        entity_id_col: str = "entity_id",
    ) -> pl.DataFrame:
        """
        Full ingestion pipeline:
          1. Polars lazy scan
          2. Suspicious pre-filter (streaming)
          3. NER on memo field (optional)
          4. Register in DuckDB
          5. Build FTS index
          6. Push entity nodes to FalkorDB
        """
        log.info("=== Ingestion start: %s ===", path)

        lf = self.polars.scan_transactions(path)
        lf_filtered = self.polars.filter_suspicious(lf)
        df = self.polars.collect_streaming(lf_filtered)

        if text_col and text_col in df.columns:
            df = self.polars.extract_entities_from_text_col(df, text_col)

        # Register in DuckDB
        self.duckdb.register("txns", df)
        self._table_registered = True

        # FTS index on memo if present
        if text_col and text_col in df.columns and "tx_id" in df.columns:
            self.duckdb.build_fts_index("txns", id_col="tx_id", text_col=text_col)

        # Push unique entities to FalkorDB
        if entity_id_col in df.columns:
            entity_df = (
                df
                .select(entity_id_col)
                .unique()
                .rename({entity_id_col: "entity_id"})
                .with_columns(pl.lit("Account").alias("node_type"))
            )
            self.graph.load_entities_from_df(
                entity_df, id_col="entity_id", entity_type="Account", property_cols=[]
            )

        log.info("=== Ingestion complete: %d suspicious rows ===", len(df))
        return df

    # ------------------------------------------------------------------
    # 6b.  Retrieve — vectorless RAG context assembly
    # ------------------------------------------------------------------
    def retrieve(
        self,
        entity_id: str,
        keywords: str | None = None,
    ) -> ForensicContext:
        """
        Pulls context from DuckDB (SQL patterns) and FalkorDB (graph traversal).
        No embedding model involved at any point.
        """
        ctx = ForensicContext(entity_id=entity_id)

        # SQL: entity summary
        if self._table_registered:
            summary_df = self.duckdb.entity_summary("txns", entity_id)
            ctx.sql_summary = summary_df.to_pandas().to_string(index=False)

            # Structuring scan — filter to this entity
            struct_df = self.duckdb.detect_structuring("txns")
            ctx.structuring_hits = (
                struct_df
                .filter(pl.col("entity_id") == entity_id)
                .to_dicts()
            )

            # Layering scan
            layer_df = self.duckdb.detect_layering("txns")
            ctx.layering_hits = (
                layer_df
                .filter(pl.col("entity_id") == entity_id)
                .to_dicts()
            )

            # BM25 keyword search
            if keywords:
                kw_df = self.duckdb.keyword_search("txns", keywords, limit=10)
                ctx.keyword_hits = kw_df.filter(
                    pl.col("entity_id") == entity_id
                ).to_dicts()

        # Graph: ownership chains
        ctx.ownership_chains = self.graph.find_control_chains(entity_id)

        # Graph: circular ownership
        ctx.circular_ownership = self.graph.find_circular_ownership()

        # Graph: beneficial owners
        ctx.beneficial_owners = self.graph.find_beneficial_owner(entity_id)

        log.info(
            "Context assembled for %s — %d chain paths, %d struct alerts",
            entity_id,
            len(ctx.ownership_chains),
            len(ctx.structuring_hits),
        )
        return ctx

    # ------------------------------------------------------------------
    # 6c.  Generate finding via Anthropic API (vectorless — context is SQL + graph)
    # ------------------------------------------------------------------
    def generate_finding(
        self,
        ctx: ForensicContext,
        question: str,
        model: str = "claude-sonnet-4-6",
    ) -> str:
        """
        Passes the structured forensic context to Claude.
        The context block contains only SQL aggregates and graph paths —
        no embedding-retrieved chunks.  This keeps the LLM grounded on
        deterministic, auditable facts.

        Requires ANTHROPIC_API_KEY environment variable.
        """
        try:
            import anthropic
        except ImportError:
            return (
                "anthropic package not installed.  Run: pip install anthropic\n"
                "Context block:\n" + ctx.to_prompt_block()
            )

        system_prompt = (
            "You are a senior financial forensics analyst specialising in tax evasion, "
            "money laundering, and corporate fraud.  You receive structured context "
            "from a graph database and SQL analytics engine — no documents or web search.  "
            "Base every conclusion ONLY on the context provided.  "
            "Cite specific transaction counts, amounts, chain depths, and entity IDs.  "
            "If the context is insufficient to answer, say so explicitly."
        )

        user_message = (
            f"QUESTION: {question}\n\n"
            f"{ctx.to_prompt_block()}"
        )

        client = anthropic.Anthropic(api_key=self._api_key)
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text


# ---------------------------------------------------------------------------
# 7.  DEMO / quick-start
# ---------------------------------------------------------------------------

def demo_with_synthetic_data() -> None:
    """
    End-to-end demonstration with synthetic transaction data.
    No real files needed — creates a Polars DataFrame in memory and
    exercises the full Polars → DuckDB → FalkorDB → context pipeline.
    """
    import random
    from datetime import datetime, timedelta

    log.info("Building synthetic transaction dataset …")

    n = 5_000
    rng = random.Random(42)

    entities = [f"ENT_{i:04d}" for i in range(50)]
    amounts = (
        [rng.uniform(9_000, 9_999) for _ in range(n // 5)]      # structuring band
        + [rng.uniform(50_000, 500_000) for _ in range(n // 10)] # large round
        + [rng.uniform(500, 3_000) for _ in range(n - n // 5 - n // 10)]
    )
    rng.shuffle(amounts)

    base_ts = datetime(2024, 1, 1)
    df = pl.DataFrame({
        "tx_id": [f"TX_{i:06d}" for i in range(n)],
        "entity_id": [rng.choice(entities) for _ in range(n)],
        "dest_entity_id": [rng.choice(entities) for _ in range(n)],
        "amount": [round(a, 2) for a in amounts],
        "ts": [base_ts + timedelta(minutes=rng.randint(0, 525_600)) for _ in range(n)],
        "memo": [
            rng.choice([
                "wire transfer cayman offshore account",
                "invoice payment consulting",
                "dividend payment BVI holding",
                "loan repayment",
                "cash deposit",
                "transfer to nominee account shell",
                None,
            ])
            for _ in range(n)
        ],
        "flag_reason": ["synthetic"] * n,
    })

    # ---- Polars Pipeline ----
    pipeline = PolarsPipeline()
    df_ner = pipeline.extract_entities_from_text_col(df, "memo")
    log.info("NER complete.  Sample: %s", df_ner["ner_entities"][0])

    # ---- DuckDB ----
    retriever = DuckDBRetriever()
    retriever.register("txns", df_ner)
    retriever.build_fts_index("txns", id_col="tx_id", text_col="memo")

    structuring = retriever.detect_structuring("txns", min_count=2)
    log.info("Structuring suspects:\n%s", structuring.head(5))

    kw_results = retriever.keyword_search("txns", "cayman offshore shell", limit=5)
    log.info("BM25 hits:\n%s", kw_results[["tx_id", "entity_id", "memo", "bm25_score"]].head(5))

    # ---- FalkorDB (requires running Docker container) ----
    try:
        graph = FalkorDBGraph()
        # Load the top suspicious entities
        top_entities = structuring.head(10).select("entity_id")
        graph.load_entities_from_df(top_entities, "entity_id", "Person", [])

        # Manually wire a couple of ownership relationships for demo
        if len(structuring) >= 2:
            e1 = structuring["entity_id"][0]
            e2 = structuring["entity_id"][1]
            graph.upsert_entity(e1, "Company", {"name": f"Shell_{e1}"})
            graph.upsert_entity(e2, "Account", {"name": f"Account_{e2}"})
            graph.upsert_relationship(e1, "CONTROLS", e2, {"stake_pct": 100})
            chains = graph.find_control_chains(e1)
            log.info("Control chains from %s: %s", e1, chains)

    except Exception as exc:
        log.warning(
            "FalkorDB not reachable (%s).  "
            "Start with: docker run -d -p 6379:6379 falkordb/falkordb",
            exc,
        )

    log.info("Demo complete.")


if __name__ == "__main__":
    demo_with_synthetic_data()
