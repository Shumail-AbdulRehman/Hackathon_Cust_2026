"""Dataset profiling and mapping into canonical civic records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .normalization import normalize_national_id, normalize_text


FIELD_SYNONYMS = {
    "person_name": [
        "full_name",
        "name",
        "owner_name",
        "consumer_name",
        "buyer_name",
        "taxpayer_name",
        "applicant_name",
    ],
    "seller_name": ["seller_name", "seller", "previous_owner"],
    "address": [
        "address",
        "reported_address",
        "owner_address",
        "installation_address",
        "property_address",
        "service_address",
        "mailing_address",
    ],
    "phone": ["phone", "phone_number", "mobile", "mobile_number", "contact_no", "cell"],
    "declared_income": ["declared_income_pkr", "declared_income", "income", "monthly_income", "annual_income"],
    "tax_paid": ["tax_paid_pkr", "tax_paid", "tax_amount"],
    "filer_status": ["filer_status", "status", "tax_status"],
    "vehicle_reg_no": ["vehicle_reg_no", "registration_no", "reg_no", "vehicle_no"],
    "engine_capacity_cc": ["engine_capacity_cc", "engine_cc", "cc", "vehicle_cc"],
    "vehicle_make_model": ["vehicle_make_model", "make_model", "model", "vehicle_model"],
    "registration_year": ["registration_year", "reg_year", "year"],
    "meter_ref_no": ["meter_ref_no", "meter_no", "reference_no", "consumer_no"],
    "monthly_bill": ["avg_monthly_bill_pkr", "monthly_bill", "bill_amount", "average_bill"],
    "connection_type": ["connection_type", "tariff", "meter_type"],
    "registry_no": ["registry_no", "property_reg_no", "transfer_id"],
    "property_value": ["property_value_pkr", "property_value", "declared_value", "transaction_value"],
    "transfer_date": ["transfer_date", "sale_date", "transaction_date"],
    "area_marla": ["area_marla", "marla", "area"],
    "property_type": ["property_type", "property_category", "land_use"],
    "national_id": [
        "cnic",
        "nic",
        "national_id",
        "ntn",
        "national_id_number",
        "cnic_no",
    ],
}


@dataclass(frozen=True)
class DatasetProfile:
    name: str
    row_count: int
    columns: list[str]
    detected_kind: str
    mapping: dict[str, str]
    missing_ratio: dict[str, float]
    samples: dict[str, list[Any]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "row_count": self.row_count,
            "columns": self.columns,
            "detected_kind": self.detected_kind,
            "mapping": self.mapping,
            "missing_ratio": self.missing_ratio,
            "samples": self.samples,
        }


def clean_number(value: Any) -> float:
    if value is None:
        return 0.0
    text = str(value).replace(",", "")
    digits = "".join(ch for ch in text if ch.isdigit() or ch == ".")
    if not digits:
        return 0.0
    try:
        return float(digits)
    except ValueError:
        return 0.0


def detect_kind(columns: list[str], dataset_name: str) -> str:
    joined = " ".join(columns + [dataset_name]).lower()
    if any(token in joined for token in ("tax", "fbr", "filer", "declared_income")):
        return "tax"
    if any(token in joined for token in ("vehicle", "excise", "engine", "reg_no")):
        return "vehicle"
    if any(token in joined for token in ("disco", "meter", "utility", "bill", "consumer")):
        return "utility"
    if any(token in joined for token in ("property", "registry", "transfer", "marla")):
        return "property"
    return "generic"


def auto_mapping(columns: list[str]) -> dict[str, str]:
    normalized = {col: normalize_text(col).replace(" ", "_") for col in columns}
    mapping: dict[str, str] = {}
    for canonical, synonyms in FIELD_SYNONYMS.items():
        for col, norm in normalized.items():
            if norm in synonyms:
                mapping[canonical] = col
                break
        if canonical in mapping:
            continue
        for col, norm in normalized.items():
            if any(syn in norm or norm in syn for syn in synonyms):
                mapping[canonical] = col
                break
    return mapping


def profile_dataset(name: str, rows: list[dict[str, Any]]) -> DatasetProfile:
    columns: list[str] = []
    seen = set()
    for row in rows:
        for col in row.keys():
            if col not in seen:
                seen.add(col)
                columns.append(col)
    mapping = auto_mapping(columns)
    kind = detect_kind(columns, name)
    missing_ratio: dict[str, float] = {}
    samples: dict[str, list[Any]] = {}
    total = max(len(rows), 1)
    for col in columns:
        values = [row.get(col, "") for row in rows]
        missing = sum(1 for value in values if value is None or str(value).strip() == "")
        missing_ratio[col] = round(missing / total, 3)
        sample_values = []
        for value in values:
            if value is not None and str(value).strip() and value not in sample_values:
                sample_values.append(value)
            if len(sample_values) >= 3:
                break
        samples[col] = sample_values
    return DatasetProfile(name, len(rows), columns, kind, mapping, missing_ratio, samples)


def value(row: dict[str, Any], mapping: dict[str, str], key: str, default: Any = "") -> Any:
    col = mapping.get(key)
    if not col:
        return default
    return row.get(col, default)


def canonicalize_datasets(
    datasets: dict[str, list[dict[str, Any]]],
    mappings: dict[str, dict[str, str]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    profiles: list[dict[str, Any]] = []
    mappings = mappings or {}

    for dataset_name, rows in datasets.items():
        profile = profile_dataset(dataset_name, rows)
        mapping_override = mappings.get(dataset_name, {})
        kind = str(
            mapping_override.get("_kind")
            or mapping_override.get("detected_kind")
            or mapping_override.get("record_type")
            or profile.detected_kind
        )
        clean_override = {key: value for key, value in mapping_override.items() if not key.startswith("_") and value}
        mapping = {**profile.mapping, **clean_override}
        profiles.append({**profile.as_dict(), "detected_kind": kind, "mapping": mapping})

        for index, row in enumerate(rows, start=1):
            source_row_id = str(row.get("source_row_id") or row.get("id") or index)
            base = {
                "source_dataset": dataset_name,
                "source_row_id": source_row_id,
                "source_kind": kind,
                "raw": row,
                "truth_person_id": row.get("_truth_person_id", ""),
                "truth_scenario": row.get("_truth_scenario", ""),
            }

            if kind == "tax":
                records.append(
                    {
                        **base,
                        "record_type": "tax",
                        "person_name": value(row, mapping, "person_name"),
                        "address": value(row, mapping, "address"),
                        "phone": value(row, mapping, "phone"),
                        "national_id": normalize_national_id(value(row, mapping, "national_id")),
                        "declared_income": clean_number(value(row, mapping, "declared_income")),
                        "tax_paid": clean_number(value(row, mapping, "tax_paid")),
                        "filer_status": str(value(row, mapping, "filer_status", "")).strip(),
                    }
                )
            elif kind == "vehicle":
                records.append(
                    {
                        **base,
                        "record_type": "vehicle",
                        "person_name": value(row, mapping, "person_name"),
                        "address": value(row, mapping, "address"),
                        "national_id": normalize_national_id(value(row, mapping, "national_id")),
                        "vehicle_reg_no": value(row, mapping, "vehicle_reg_no"),
                        "engine_capacity_cc": clean_number(value(row, mapping, "engine_capacity_cc")),
                        "vehicle_make_model": value(row, mapping, "vehicle_make_model"),
                        "registration_year": value(row, mapping, "registration_year"),
                    }
                )
            elif kind == "utility":
                records.append(
                    {
                        **base,
                        "record_type": "utility",
                        "person_name": value(row, mapping, "person_name"),
                        "address": value(row, mapping, "address"),
                        "national_id": normalize_national_id(value(row, mapping, "national_id")),
                        "meter_ref_no": value(row, mapping, "meter_ref_no"),
                        "monthly_bill": clean_number(value(row, mapping, "monthly_bill")),
                        "connection_type": value(row, mapping, "connection_type"),
                    }
                )
            elif kind == "property":
                buyer_name = value(row, mapping, "person_name")
                seller_name = value(row, mapping, "seller_name")
                records.append(
                    {
                        **base,
                        "record_type": "property",
                        "person_name": buyer_name,
                        "seller_name": seller_name,
                        "address": value(row, mapping, "address"),
                        "national_id": normalize_national_id(value(row, mapping, "national_id")),
                        "registry_no": value(row, mapping, "registry_no"),
                        "property_value": clean_number(value(row, mapping, "property_value")),
                        "transfer_date": value(row, mapping, "transfer_date"),
                        "area_marla": clean_number(value(row, mapping, "area_marla")),
                        "property_type": value(row, mapping, "property_type"),
                    }
                )
            else:
                records.append(
                    {
                        **base,
                        "record_type": "generic",
                        "person_name": value(row, mapping, "person_name"),
                        "address": value(row, mapping, "address"),
                        "phone": value(row, mapping, "phone"),
                        "national_id": normalize_national_id(value(row, mapping, "national_id")),
                    }
                )
    return records, profiles

def profile_datasets(
    datasets: dict[str, list[dict[str, Any]]],
    mappings: dict[str, dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    mappings = mappings or {}
    for dataset_name, rows in datasets.items():
        profile = profile_dataset(dataset_name, rows)
        mapping_override = mappings.get(dataset_name, {})
        kind = str(
            mapping_override.get("_kind")
            or mapping_override.get("detected_kind")
            or mapping_override.get("record_type")
            or profile.detected_kind
        )
        clean_override = {key: value for key, value in mapping_override.items() if not key.startswith("_") and value}
        profiles.append(
            {
                **profile.as_dict(),
                "detected_kind": kind,
                "mapping": {**profile.mapping, **clean_override},
            }
        )
    return profiles

