"""Tests for the OpenSanctions targets loader."""

from __future__ import annotations

from pathlib import Path

from taxnet.loaders.open_sanctions_loader import load_targets


def test_load_targets_returns_list(tmp_path: Path) -> None:
    csv_path = tmp_path / "targets.csv"
    csv_path.write_text(
        "id,schema,name,aliases,countries,sanctions,dataset\n"
        'os-1,Person,John DOE,"J. Doe;Johnny Doe",us;ca,program-a,default\n'
        "os-2,Company,Acme Inc.,,us,program-b,default\n"
    )
    targets = load_targets(csv_path)
    assert isinstance(targets, list)
    assert len(targets) == 2

    first = targets[0]
    assert first["id"] == "os-1"
    assert first["schema"] == "Person"
    assert first["name"] == "john doe"
    assert first["aliases"] == ["j doe", "johnny doe"]
    assert first["countries"] == ["US", "CA"]
    assert list(first.keys()) == ["id", "schema", "name", "aliases", "countries"]

    second = targets[1]
    assert second["name"] == "acme inc"
    assert second["aliases"] == []
    assert second["countries"] == ["US"]


def test_load_targets_gracefully_missing_file(tmp_path: Path) -> None:
    assert load_targets(tmp_path / "does-not-exist.csv") == []


def test_load_targets_missing_required_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "targets.csv"
    csv_path.write_text("id,name\nos-1,John DOE\n")
    assert load_targets(csv_path) == []


def test_load_targets_skips_empty_canonical_names(tmp_path: Path) -> None:
    csv_path = tmp_path / "targets.csv"
    csv_path.write_text(
        "id,schema,name,aliases,countries,sanctions,dataset\n"
        'os-1,Person,,"J. Doe",us,program-a,default\n'
        'os-2,Person,Jane DOE,"J. Doe",us,program-a,default\n'
    )
    targets = load_targets(csv_path)
    assert len(targets) == 1
    assert targets[0]["id"] == "os-2"
    assert targets[0]["name"] == "jane doe"


def test_load_targets_deduplicates_aliases(tmp_path: Path) -> None:
    csv_path = tmp_path / "targets.csv"
    csv_path.write_text(
        "id,schema,name,aliases,countries,sanctions,dataset\n"
        'os-1,Person,John DOE,"J. Doe;J. Doe;Johnny Doe;J. Doe",us,program-a,default\n'
    )
    targets = load_targets(csv_path)
    assert len(targets) == 1
    assert targets[0]["aliases"] == ["j doe", "johnny doe"]


def test_load_targets_empty_aliases_and_countries(tmp_path: Path) -> None:
    csv_path = tmp_path / "targets.csv"
    csv_path.write_text(
        "id,schema,name,aliases,countries,sanctions,dataset\nos-1,Person,John DOE,,,program-a,default\n"
    )
    targets = load_targets(csv_path)
    assert len(targets) == 1
    assert targets[0]["aliases"] == []
    assert targets[0]["countries"] == []
