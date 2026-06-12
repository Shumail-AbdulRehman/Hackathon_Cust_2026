"""Shared dataclasses used across the TaxNet pipeline."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RecordFingerprint:
    record_id: str
    person_name: str
    norm_name: str
    address: str
    norm_address: str
    phone: str
    national_id: str
    city: str
    block_key: str
    source_dataset: str
    source_kind: str
    truth_person_id: str
