"""Tests for Pakistani CNIC/NIC geocoding."""

from __future__ import annotations

import pytest

from taxnet.nic_geocode import cnic_location


@pytest.mark.parametrize(
    "nic, province, district",
    [
        ("3520112345671", "Punjab", "Lahore"),
        ("4220112345671", "Sindh", "Karachi"),
        ("1110112345671", "Khyber Pakhtunkhwa", "Peshawar"),
        ("5120112345671", "Balochistan", "Quetta"),
        ("6110112345671", "Islamabad Capital Territory", "Islamabad"),
        ("8110112345671", "Azad Kashmir", "Muzaffarabad"),
        ("7110112345671", "Gilgit-Baltistan", "Gilgit"),
    ],
)
def test_cnic_to_province_and_district(nic: str, province: str, district: str) -> None:
    loc = cnic_location(nic)
    assert loc["province"] == province
    assert loc["district"] == district


def test_cnic_with_dashes_and_spaces() -> None:
    loc = cnic_location("35201-1234567-1")
    assert loc["province"] == "Punjab"
    assert loc["district"] == "Lahore"


def test_empty_nic() -> None:
    loc = cnic_location("")
    assert loc["province"] == ""
    assert loc["district"] == ""


def test_unknown_prefix() -> None:
    loc = cnic_location("9999912345671")
    assert loc["province"] == "Unknown"
    assert loc["district"] == ""
