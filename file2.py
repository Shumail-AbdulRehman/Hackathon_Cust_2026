#!/usr/bin/env python3
"""file2.py — Download datasets, build the entity graph, and train the ML model.

Run on the server:
    uv run python file2.py

Inputs:
    - ICIJ Offshore Leaks (local or downloaded)
    - OpenSanctions (local or downloaded)
    - UK Companies House (sampled)
    - Elliptic++ Bitcoin transaction graph (sampled)
    - IBM AML transactions (sampled)

Outputs (in server_artifacts/ml/):
    ml_model.json               Trained XGBoost model
    feature_columns.json        Ordered feature column names
    entity_profiles.jsonl       One profile per entity (used by file3.py)
    training_report.json        Summary of dataset sizes, label distribution, metrics

The script is idempotent: completed stages are skipped unless --force is passed.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import xgboost as xgb
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split

from server_utils import (
    download_if_missing,
    is_checkpoint_complete,
    log as _log,
    save_checkpoint,
    write_jsonl,
)
from taxnet.features import build_entity_features
from taxnet.ml_scorer import FEATURE_COLUMNS as TAXNET_FEATURE_COLUMNS
from taxnet.pipeline import run_pipeline

# Optional progress bars
try:
    from tqdm import tqdm
except Exception:  # pragma: no cover

    def tqdm(iterable=None, **kwargs):  # type: ignore[misc]
        return iterable


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

STAGE = "file2"

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
ARTIFACTS_DIR = ROOT / "server_artifacts" / "ml"
MODEL_PATH = ARTIFACTS_DIR / "ml_model.json"
FEATURE_COLUMNS_PATH = ARTIFACTS_DIR / "feature_columns.json"
PROFILES_PATH = ARTIFACTS_DIR / "entity_profiles.jsonl"
TRAINING_REPORT_PATH = ARTIFACTS_DIR / "training_report.json"

ICIJ_DIR = DATA_DIR / "icij-offshore-leaks"
OPEN_SANCTIONS_DIR = DATA_DIR / "open-sanctions"
RAW_DIR = ARTIFACTS_DIR / "raw_downloads"

# External dataset download URLs / identifiers
DATASET_CONFIG: dict[str, dict[str, Any]] = {
    "icij": {
        "local_dir": ICIJ_DIR,
        "required_files": ["nodes-entities.csv", "nodes-officers.csv", "nodes-intermediaries.csv", "relationships.csv"],
        # Full ICIJ is expected to be present locally; download URL kept for reference.
        "download_url": "https://offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip",
        "use_full": True,
    },
    "open-sanctions": {
        "local_file": OPEN_SANCTIONS_DIR / "targets.simple.csv",
        "download_url": "https://data.opensanctions.org/datasets/latest/default/targets.simple.csv",
        "use_full": True,
    },
    "uk-companies-house": {
        "sample_fraction": 0.05,
        # URLs are snapshots; the script will use the latest if available.
        "basic_url": "http://download.companieshouse.gov.uk/BasicCompanyDataAsOneFile-2026-06-01.zip",
        "psc_url": "http://download.companieshouse.gov.uk/persons-with-significant-control-snapshot-2026-06-12.zip",
    },
    "elliptic": {
        "repo_url": "https://github.com/git-disl/EllipticPlusPlus",
        "sample_fraction": 0.2,
    },
    "ibm-aml": {
        "kaggle_dataset": "ealtman2019/ibm-transactions-for-anti-money-laundering-aml",
        "variant": "LI-Small_Trans.csv",
        "sample_size": 200_000,
    },
}

# Feature columns from TaxNet + source indicators added by file2.py
SOURCE_INDICATOR_COLUMNS = [
    "source_icij",
    "source_open_sanctions",
    "source_uk_companies_house",
    "source_elliptic",
    "source_ibm_aml",
]

FEATURE_COLUMNS = list(TAXNET_FEATURE_COLUMNS) + SOURCE_INDICATOR_COLUMNS


def log(message: str) -> None:
    _log(STAGE, message)


# ---------------------------------------------------------------------------
# Dataset loaders
# ---------------------------------------------------------------------------


def load_icij_datasets(use_full: bool = True) -> dict[str, list[dict[str, Any]]]:
    """Load ICIJ Offshore Leaks into TaxNet-compatible records."""
    from taxnet.loaders.icij_loader import build_icij_datasets

    if use_full:
        log("Loading full ICIJ Offshore Leaks graph...")
        # Passing a very large max_entities forces the loader to use every entity.
        return build_icij_datasets(data_dir=ICIJ_DIR, max_entities=10_000_000, seed=42, hop_radius=1)
    else:
        log("Loading ICIJ Offshore Leaks sample...")
        return build_icij_datasets(data_dir=ICIJ_DIR, max_entities=50_000, seed=42, hop_radius=1)


def load_open_sanctions(path: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    """Load OpenSanctions targets.simple.csv into TaxNet-compatible records."""
    path = path or DATASET_CONFIG["open-sanctions"]["local_file"]
    if not path.exists():
        raise FileNotFoundError(f"OpenSanctions file not found: {path}")

    log(f"Loading OpenSanctions from {path} ...")
    df = pl.read_csv(path, infer_schema_length=1000, null_values=["", "NULL", "N/A"])

    # Expected columns: id, schema, name, aliases, birth_date, countries, addresses,
    # identifiers, sanctions, phones, emails, program_ids, dataset, first_seen, last_seen, last_change
    records: list[dict[str, Any]] = []
    for row in tqdm(df.to_dicts(), desc="OpenSanctions", total=df.height):
        target_id = str(row.get("id") or "").strip()
        name = str(row.get("name") or "").strip()
        if not target_id or not name:
            continue

        aliases = str(row.get("aliases") or "").strip()
        address = str(row.get("addresses") or "").strip()
        countries = str(row.get("countries") or "").strip()
        schema = str(row.get("schema") or "").strip()
        programs = str(row.get("sanctions") or "").strip() or str(row.get("program_ids") or "").strip()

        records.append(
            {
                "source_row_id": f"os-{target_id}",
                "person_name": name,
                "address": address or countries,
                "national_id": target_id,
                "phone": str(row.get("phones") or "").strip(),
                "email": str(row.get("emails") or "").strip(),
                "open_sanctions_schema": schema,
                "open_sanctions_countries": countries,
                "open_sanctions_programs": programs,
                "_kind": "generic",
            }
        )

    return {"open-sanctions": records}


def load_uk_companies_house(data_dir: Path, sample_fraction: float = 0.05) -> dict[str, list[dict[str, Any]]]:
    """Load a sample of UK Companies House basic + PSC data.

    Expects:
        data_dir/BasicCompanyDataAsOneFile-*.zip (CSV inside)
        data_dir/persons-with-significant-control-snapshot-*.zip (JSON inside)
    """
    basic_zip = next((p for p in data_dir.glob("BasicCompanyDataAsOneFile-*.zip")), None)
    psc_zip = next((p for p in data_dir.glob("persons-with-significant-control-snapshot-*.zip")), None)

    if not basic_zip or not psc_zip:
        log("WARNING: UK Companies House data not found; skipping.")
        return {}

    log(f"Loading UK Companies House sample (fraction={sample_fraction}) ...")
    basic_csv = data_dir / "basic_company_data.csv"
    if not basic_csv.exists():
        with zipfile.ZipFile(basic_zip) as z:
            csv_name = next((n for n in z.namelist() if n.endswith(".csv")), None)
            if csv_name:
                z.extract(csv_name, data_dir)
                (data_dir / csv_name).replace(basic_csv)

    psc_jsonl = data_dir / "psc_data.jsonl"
    if not psc_jsonl.exists():
        with zipfile.ZipFile(psc_zip) as z:
            json_name = next((n for n in z.namelist() if n.endswith(".json") or n.endswith(".jsonl")), None)
            if json_name:
                z.extract(json_name, data_dir)
                (data_dir / json_name).replace(psc_jsonl)

    # Read a sample of active companies.
    basic_df = pl.read_csv(basic_csv, infer_schema_length=1000, null_values=["", "NULL", "N/A"])
    if "CompanyStatus" in basic_df.columns:
        basic_df = basic_df.filter(pl.col("CompanyStatus").str.to_lowercase() == "active")
    company_cols = [c for c in basic_df.columns if "CompanyName" in c or "CompanyNumber" in c]
    if not company_cols:
        log("WARNING: UK basic data has unexpected columns; skipping.")
        return {}

    sample_n = max(1, int(basic_df.height * sample_fraction))
    sampled_companies = basic_df.sample(n=sample_n, seed=42).select(
        [pl.col(c) for c in basic_df.columns if "CompanyNumber" in c or "CompanyName" in c]
    )
    company_numbers = set(str(x) for x in sampled_companies["CompanyNumber"].to_list())

    # Load matching PSC records.
    records: list[dict[str, Any]] = []
    if psc_jsonl.exists():
        with open(psc_jsonl, "r", encoding="utf-8") as f:
            for line in tqdm(f, desc="UK PSC"):
                line = line.strip()
                if not line:
                    continue
                try:
                    psc = json.loads(line)
                except json.JSONDecodeError:
                    continue
                company_number = str(psc.get("company_number") or "").strip()
                if company_number not in company_numbers:
                    continue
                name = str(psc.get("data", {}).get("name") or "").strip()
                address = str(psc.get("data", {}).get("address", {}) or "").strip()
                if not name:
                    continue
                records.append(
                    {
                        "source_row_id": f"uk-{company_number}-{psc.get('data', {}).get('notification_id', 'x')}",
                        "person_name": name,
                        "address": address,
                        "national_id": company_number,
                        "uk_company_number": company_number,
                        "uk_company_name": str(psc.get("company_name") or "").strip(),
                        "uk_psc_kind": str(psc.get("data", {}).get("kind") or "").strip(),
                        "_kind": "generic",
                    }
                )

    return {"uk-companies-house": records}


def load_elliptic(data_dir: Path, sample_fraction: float = 0.2) -> dict[str, list[dict[str, Any]]]:
    """Load a sample of Elliptic++ transaction data.

    Expects files like:
        data_dir/txs.csv
        data_dir/edges.csv
        data_dir/classes.csv
    """
    txs_path = data_dir / "txs.csv"
    edges_path = data_dir / "edges.csv"
    classes_path = data_dir / "classes.csv"

    if not txs_path.exists() or not edges_path.exists() or not classes_path.exists():
        log("WARNING: Elliptic++ data not found; skipping.")
        return {}

    log(f"Loading Elliptic++ sample (fraction={sample_fraction}) ...")
    txs_df = pl.read_csv(txs_path, infer_schema_length=1000)
    classes_df = pl.read_csv(classes_path, infer_schema_length=1000)

    # Classes typically: txId, class (1=illicit, 2=licit, 3=unknown)
    labeled = classes_df.filter(pl.col("class").is_in([1, 2]))
    sample_n = max(1, int(labeled.height * sample_fraction))
    sampled_txids = set(
        int(x)
        for x in labeled.sample(n=sample_n, seed=42)["txId"].to_list()
    )

    # Build a mapping from txId to class label.
    class_map = {int(row["txId"]): int(row["class"]) for row in classes_df.to_dicts()}

    records: list[dict[str, Any]] = []
    for row in tqdm(txs_df.to_dicts(), desc="Elliptic", total=txs_df.height):
        txid = int(row.get("txId") or 0)
        if txid not in sampled_txids:
            continue
        cls = class_map.get(txid, 3)
        records.append(
            {
                "source_row_id": f"elliptic-{txid}",
                "person_name": f"elliptic_account_{txid}",
                "address": f"tx_{txid}",
                "national_id": f"elliptic_{txid}",
                "elliptic_tx_id": txid,
                "elliptic_class": cls,
                "_kind": "generic",
            }
        )

    return {"elliptic": records}


def load_ibm_aml(data_dir: Path, variant: str = "LI-Small_Trans.csv", sample_size: int = 200_000) -> dict[str, list[dict[str, Any]]]:
    """Load a sample of IBM AML transaction data.

    Expects a CSV like LI-Small_Trans.csv with columns including:
        From Bank, Account, To Bank, Account.1, Amount Received, Receiving Currency,
        Amount Paid, Payment Currency, Payment Format, Is Laundering, etc.
    """
    csv_path = data_dir / variant
    if not csv_path.exists():
        # Try to find any matching CSV.
        csv_path = next((p for p in data_dir.glob("*Trans.csv")), None)

    if not csv_path or not csv_path.exists():
        log("WARNING: IBM AML data not found; skipping.")
        return {}

    log(f"Loading IBM AML sample (sample_size={sample_size}) from {csv_path} ...")
    df = pl.read_csv(csv_path, infer_schema_length=1000, null_values=["", "NULL", "N/A"])

    # Determine label column.
    label_col = None
    for col in df.columns:
        if "laundering" in col.lower() or "is_fraud" in col.lower() or "fraud" in col.lower():
            label_col = col
            break

    if label_col is None:
        log("WARNING: IBM AML has no recognized label column; skipping.")
        return {}

    sample_n = min(sample_size, df.height)
    df = df.sample(n=sample_n, seed=42)

    records: list[dict[str, Any]] = []
    for row in tqdm(df.to_dicts(), desc="IBM AML", total=df.height):
        from_account = str(row.get("Account") or row.get("From Account") or "").strip()
        to_account = str(row.get("Account.1") or row.get("To Account") or "").strip()
        if not from_account:
            continue
        label = int(row.get(label_col) or 0)
        records.append(
            {
                "source_row_id": f"ibm-{from_account}-{to_account}",
                "person_name": f"ibm_account_{from_account}",
                "address": f"to_{to_account}",
                "national_id": f"ibm_{from_account}",
                "ibm_amount_paid": float(row.get("Amount Paid") or 0),
                "ibm_amount_received": float(row.get("Amount Received") or 0),
                "ibm_is_laundering": label,
                "_kind": "generic",
            }
        )

    return {"ibm-aml": records}


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------


def ensure_icij() -> None:
    """Download ICIJ if the required files are missing."""
    missing = [f for f in DATASET_CONFIG["icij"]["required_files"] if not (ICIJ_DIR / f).exists()]
    if not missing:
        return

    zip_path = RAW_DIR / "full-oldb.LATEST.zip"
    download_if_missing(DATASET_CONFIG["icij"]["download_url"], zip_path, stage=STAGE)
    log("Extracting ICIJ archive...")
    ICIJ_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(ICIJ_DIR)


def ensure_open_sanctions() -> None:
    """Download OpenSanctions if the targets file is missing."""
    path = DATASET_CONFIG["open-sanctions"]["local_file"]
    if path.exists():
        return
    OPEN_SANCTIONS_DIR.mkdir(parents=True, exist_ok=True)
    download_if_missing(DATASET_CONFIG["open-sanctions"]["download_url"], path, stage=STAGE)


def ensure_uk_companies_house() -> Path:
    """Download UK Companies House data if missing. Returns data directory."""
    data_dir = RAW_DIR / "uk-companies-house"
    data_dir.mkdir(parents=True, exist_ok=True)

    basic_zip = next((p for p in data_dir.glob("BasicCompanyDataAsOneFile-*.zip")), None)
    if not basic_zip:
        basic_url = DATASET_CONFIG["uk-companies-house"]["basic_url"]
        basic_zip = data_dir / Path(basic_url).name
        download_if_missing(basic_url, basic_zip, stage=STAGE)

    psc_zip = next((p for p in data_dir.glob("persons-with-significant-control-snapshot-*.zip")), None)
    if not psc_zip:
        psc_url = DATASET_CONFIG["uk-companies-house"]["psc_url"]
        psc_zip = data_dir / Path(psc_url).name
        download_if_missing(psc_url, psc_zip, stage=STAGE)

    return data_dir


def ensure_elliptic() -> Path:
    """Return the Elliptic++ data directory (user must clone the repo manually)."""
    data_dir = RAW_DIR / "elliptic"
    data_dir.mkdir(parents=True, exist_ok=True)
    log(
        "NOTE: Elliptic++ must be downloaded manually from "
        f"{DATASET_CONFIG['elliptic']['repo_url']} into {data_dir}"
    )
    return data_dir


def ensure_ibm_aml() -> Path:
    """Return the IBM AML data directory (user must download via Kaggle manually)."""
    data_dir = RAW_DIR / "ibm-aml"
    data_dir.mkdir(parents=True, exist_ok=True)
    log(
        "NOTE: IBM AML must be downloaded manually via Kaggle: "
        f"kaggle datasets download -d {DATASET_CONFIG['ibm-aml']['kaggle_dataset']} "
        f"and extracted into {data_dir}"
    )
    return data_dir


# ---------------------------------------------------------------------------
# Labeling
# ---------------------------------------------------------------------------


def build_proxy_labels(
    entity_records: dict[str, list[dict[str, Any]]]
) -> dict[str, float]:
    """Assign a proxy risk label to each entity based on its source records."""
    labels: dict[str, float] = {}

    for entity_id, records in entity_records.items():
        scores = []
        for rec in records:
            source = rec.get("source_dataset", "")
            raw = rec.get("raw", {})

            if source == "icij-offshore-leaks":
                scores.append(80.0)
            elif source == "open-sanctions":
                scores.append(95.0)
            elif source == "elliptic":
                cls = int(raw.get("elliptic_class") or 3)
                if cls == 1:
                    scores.append(85.0)
                elif cls == 2:
                    scores.append(15.0)
            elif source == "ibm-aml":
                if int(raw.get("ibm_is_laundering") or 0) == 1:
                    scores.append(85.0)
                else:
                    scores.append(15.0)
            elif source == "uk-companies-house":
                # Multiple PSC links or generic UK presence = mild signal
                scores.append(40.0)

        if scores:
            labels[entity_id] = max(scores)
        else:
            labels[entity_id] = 10.0

    return labels


def add_source_indicators(
    entity_records: dict[str, list[dict[str, Any]]]
) -> dict[str, dict[str, int]]:
    """Return per-entity binary source-indicator dicts."""
    indicators: dict[str, dict[str, int]] = {}
    source_map = {
        "icij-offshore-leaks": "source_icij",
        "open-sanctions": "source_open_sanctions",
        "uk-companies-house": "source_uk_companies_house",
        "elliptic": "source_elliptic",
        "ibm-aml": "source_ibm_aml",
    }
    for entity_id, records in entity_records.items():
        vec = {col: 0 for col in SOURCE_INDICATOR_COLUMNS}
        for rec in records:
            col = source_map.get(rec.get("source_dataset", ""))
            if col:
                vec[col] = 1
        indicators[entity_id] = vec
    return indicators


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def train_xgboost(
    X: np.ndarray,
    y: np.ndarray,
    entity_ids: list[str],
) -> tuple[xgb.XGBRegressor, dict[str, Any]]:
    """Train an XGBoost regressor and report basic metrics."""
    y_binary = (y > 50).astype(int)
    class_counts = np.bincount(y_binary)
    can_stratify = len(class_counts) == 2 and min(class_counts) >= 5

    split_kwargs: dict[str, Any] = {"test_size": 0.2, "random_state": 42}
    if can_stratify:
        split_kwargs["stratify"] = y_binary

    X_train, X_test, y_train, y_test, ids_train, ids_test = train_test_split(
        X, y, entity_ids, **split_kwargs
    )

    model = xgb.XGBRegressor(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        objective="reg:squarederror",
        random_state=42,
        base_score=0.5,
        early_stopping_rounds=20,
    )
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    y_pred = model.predict(X_test)
    y_pred_binary = (y_pred > 50).astype(int)
    y_test_binary = (y_test > 50).astype(int)

    metrics = {
        "test_size": len(y_test),
        "train_size": len(y_train),
        "auc": round(roc_auc_score(y_test_binary, y_pred), 4),
        "classification_report": classification_report(
            y_test_binary, y_pred_binary, output_dict=True, zero_division=0
        ),
    }

    return model, metrics


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Train TaxNet ML model on real datasets.")
    parser.add_argument("--force-download", action="store_true", help="Re-download datasets.")
    parser.add_argument("--force-train", action="store_true", help="Retrain the model even if it exists.")
    parser.add_argument("--skip-download", action="store_true", help="Use existing downloaded files only.")
    parser.add_argument("--skip-uk", action="store_true", help="Skip UK Companies House.")
    parser.add_argument("--skip-elliptic", action="store_true", help="Skip Elliptic++.")
    parser.add_argument("--skip-ibm", action="store_true", help="Skip IBM AML.")
    parser.add_argument("--icij-sample", action="store_true", help="Use a 50k-entity ICIJ sample instead of the full graph.")
    parser.add_argument("--use-ann-blocking", action="store_true", help="Use ANN blocking for entity resolution.")
    args = parser.parse_args()

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if MODEL_PATH.exists() and not args.force_train:
        log(f"Model already exists at {MODEL_PATH}. Use --force-train to retrain.")
        return 0

    # ------------------------------------------------------------------
    # Stage 1: ensure datasets are available
    # ------------------------------------------------------------------
    if not args.skip_download:
        if is_checkpoint_complete("file2_downloads") and not args.force_download:
            log("Downloads checkpoint found; skipping. Use --force-download to override.")
        else:
            log("Ensuring datasets are available...")
            ensure_icij()
            ensure_open_sanctions()
            if not args.skip_uk:
                ensure_uk_companies_house()
            if not args.skip_elliptic:
                ensure_elliptic()
            if not args.skip_ibm:
                ensure_ibm_aml()
            save_checkpoint("file2_downloads", {"datasets": list(DATASET_CONFIG.keys())})
    else:
        log("Skipping downloads (--skip-download).")

    # ------------------------------------------------------------------
    # Stage 2: load datasets
    # ------------------------------------------------------------------
    log("Loading datasets...")
    datasets: dict[str, list[dict[str, Any]]] = {}
    datasets.update(load_icij_datasets(use_full=not args.icij_sample))
    datasets.update(load_open_sanctions())

    if not args.skip_uk:
        uk_dir = RAW_DIR / "uk-companies-house"
        if uk_dir.exists():
            datasets.update(load_uk_companies_house(uk_dir, sample_fraction=DATASET_CONFIG["uk-companies-house"]["sample_fraction"]))

    if not args.skip_elliptic:
        elliptic_dir = RAW_DIR / "elliptic"
        if elliptic_dir.exists():
            datasets.update(load_elliptic(elliptic_dir, sample_fraction=DATASET_CONFIG["elliptic"]["sample_fraction"]))

    if not args.skip_ibm:
        ibm_dir = RAW_DIR / "ibm-aml"
        if ibm_dir.exists():
            cfg = DATASET_CONFIG["ibm-aml"]
            datasets.update(load_ibm_aml(ibm_dir, variant=cfg["variant"], sample_size=cfg["sample_size"]))

    if not datasets:
        log("ERROR: no datasets loaded.")
        return 1

    total_records = sum(len(rows) for rows in datasets.values())
    log(f"Loaded {total_records:,} records from {len(datasets)} datasets.")

    # ------------------------------------------------------------------
    # Stage 3: run TaxNet pipeline
    # ------------------------------------------------------------------
    log("Running TaxNet pipeline (ingestion, entity resolution, graph build)...")
    result = run_pipeline(
        datasets=datasets,
        use_ml=False,  # we train our own model below with proxy labels
        use_ann_blocking=args.use_ann_blocking,
    )

    # ------------------------------------------------------------------
    # Stage 4: features + proxy labels
    # ------------------------------------------------------------------
    log("Building entity features...")
    features = build_entity_features(result["graph"], result["resolution"], result.get("falkor_summary"))
    entity_records = result["graph"].get("entity_records", {})
    labels = build_proxy_labels(entity_records)
    source_indicators = add_source_indicators(entity_records)

    # ------------------------------------------------------------------
    # Stage 5: train ML model
    # ------------------------------------------------------------------
    log("Preparing feature matrix...")
    X, y, entity_ids = [], [], []
    for entity_id in features:
        base_vec = [float(features[entity_id].get(col, 0.0)) for col in TAXNET_FEATURE_COLUMNS]
        source_vec = [float(source_indicators[entity_id].get(col, 0.0)) for col in SOURCE_INDICATOR_COLUMNS]
        X.append(base_vec + source_vec)
        y.append(labels.get(entity_id, 10.0))
        entity_ids.append(entity_id)

    X = np.array(X)
    y = np.array(y)

    log(f"Training XGBoost on {len(X)} entities...")
    model, metrics = train_xgboost(X, y, entity_ids)

    # Build entity lookup for canonical names.
    entity_lookup = {e["entity_id"]: e for e in result["resolution"].get("entities", [])}

    # ------------------------------------------------------------------
    # Stage 6: save artifacts
    # ------------------------------------------------------------------
    log(f"Saving model to {MODEL_PATH} ...")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    model.save_model(str(MODEL_PATH))

    FEATURE_COLUMNS_PATH.write_text(json.dumps(FEATURE_COLUMNS, indent=2), encoding="utf-8")

    # Entity profiles for file3.py
    log(f"Saving entity profiles to {PROFILES_PATH} ...")
    profiles: list[dict[str, Any]] = []
    predictions = model.predict(X)
    for idx, entity_id in enumerate(entity_ids):
        recs = entity_records.get(entity_id, [])
        profiles.append(
            {
                "entity_id": entity_id,
                "canonical_name": entity_lookup.get(entity_id, {}).get("canonical_name", ""),
                "risk_score": round(float(predictions[idx]), 2),
                "proxy_label": round(float(y[idx]), 2),
                "features": {col: float(features[entity_id].get(col, 0.0)) for col in TAXNET_FEATURE_COLUMNS},
                "source_indicators": source_indicators[entity_id],
                "record_sources": list({r.get("source_dataset", "") for r in recs}),
                "record_count": len(recs),
            }
        )
    write_jsonl(PROFILES_PATH, profiles)

    # Training report
    report = {
        "datasets": {name: len(rows) for name, rows in datasets.items()},
        "total_records": total_records,
        "entities": len(entity_ids),
        "feature_count": len(FEATURE_COLUMNS),
        "metrics": metrics,
    }
    TRAINING_REPORT_PATH.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    log("Done.")
    log(f"Artifacts: {MODEL_PATH}, {FEATURE_COLUMNS_PATH}, {PROFILES_PATH}, {TRAINING_REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
