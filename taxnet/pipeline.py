"""End-to-end TaxNet XAI pipeline."""

from __future__ import annotations

import time
from typing import Any

from .entity_resolution import resolve_entities
from .falkor_engine import load_graph
from .graph_engine import build_graph
from .ingestion import canonicalize_datasets
from .scoring import score_entities
from .synthetic import generate_synthetic_datasets

try:
    from .ml_scorer import train_model
except Exception:
    train_model = None  # type: ignore[assignment]


def run_pipeline(
    datasets: dict[str, list[dict[str, Any]]] | None = None,
    mappings: dict[str, dict[str, str]] | None = None,
    synthetic_seed: int = 42,
    use_ml: bool = True,
    use_ann_blocking: bool = False,
) -> dict[str, Any]:
    start = time.perf_counter()
    if datasets is None:
        datasets = generate_synthetic_datasets(seed=synthetic_seed)
        mode = "synthetic"
    else:
        mode = "uploaded"

    canonical_records, profiles = canonicalize_datasets(datasets, mappings)
    t_ingest = time.perf_counter()
    resolution = resolve_entities(canonical_records, use_ann_blocking=use_ann_blocking)
    t_er = time.perf_counter()
    graph = build_graph(canonical_records, resolution)
    t_graph = time.perf_counter()

    falkor_summary = None
    try:
        falkor_summary = load_graph("taxnet", canonical_records, resolution)
    except Exception as exc:
        falkor_summary = {"error": str(exc)}

    ml_model = None
    if use_ml and train_model is not None:
        try:
            ml_model = train_model(graph, resolution, falkor_summary)
        except Exception:
            ml_model = None

    scoring = score_entities(graph, resolution, ml_model=ml_model, falkor_summary=falkor_summary)
    t_score = time.perf_counter()

    return {
        "mode": mode,
        "profiles": profiles,
        "canonical_records": canonical_records,
        "resolution": resolution,
        "graph": graph,
        "falkor_summary": falkor_summary,
        "scoring": scoring,
        "timing_ms": {
            "ingestion": round((t_ingest - start) * 1000, 2),
            "entity_resolution": round((t_er - t_ingest) * 1000, 2),
            "graph": round((t_graph - t_er) * 1000, 2),
            "scoring": round((t_score - t_graph) * 1000, 2),
            "total": round((t_score - start) * 1000, 2),
        },
        "scalability_notes": {
            "blocking": "Candidate generation avoids all-to-all comparison by phone, city plus surname, address block, and initials.",
            "storage": "Production deployment should persist canonical records, entity IDs, edge lists, and score snapshots with indexes.",
            "thirty_million": "For 30M citizens, run blocking partitions in batch jobs, store pair features, and update clusters incrementally.",
        },
    }


def compact_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": result["mode"],
        "profiles": result["profiles"],
        "resolution": {
            **result["resolution"],
            "matches": result["resolution"]["matches"][:100],
        },
        "graph": {
            "nodes": result["graph"]["nodes"],
            "edges": result["graph"]["edges"],
            "summary": result["graph"]["summary"],
        },
        "scoring": result["scoring"],
        "timing_ms": result["timing_ms"],
        "scalability_notes": result["scalability_notes"],
        "canonical_record_count": len(result["canonical_records"]),
    }


def strip_truth_labels(datasets: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    return {
        name: [{key: value for key, value in row.items() if not key.startswith("_")} for row in rows]
        for name, rows in datasets.items()
    }


def run_benchmark(citizens: int = 500, synthetic_seed: int = 42) -> dict[str, Any]:
    citizens = max(1, citizens)
    datasets = strip_truth_labels(generate_synthetic_datasets(seed=synthetic_seed, citizens=citizens))
    result = run_pipeline(datasets=datasets, synthetic_seed=synthetic_seed)
    total_ms = result["timing_ms"]["total"]
    record_count = len(result["canonical_records"])
    throughput = round(record_count / (total_ms / 1000), 2) if total_ms else record_count
    return {
        "mode": "benchmark",
        "citizens": citizens,
        "synthetic_seed": synthetic_seed,
        "truth_metrics_skipped": True,
        "canonical_record_count": record_count,
        "entity_count": len(result["resolution"]["entities"]),
        "resolution_runtime_stats": result["resolution"]["runtime_stats"],
        "graph_summary": result["graph"]["summary"],
        "scoring_summary": result["scoring"]["summary"],
        "timing_ms": result["timing_ms"],
        "throughput_records_per_second": throughput,
        "scalability_notes": result["scalability_notes"],
    }

