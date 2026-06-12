"""Pakistani CNIC/NIC prefix geocoding."""

from __future__ import annotations

from typing import Any


# First digit of 13-digit CNIC = province; first 5 digits = district.
_PROVINCE_BY_FIRST_DIGIT: dict[str, str] = {
    "1": "Khyber Pakhtunkhwa",
    "2": "FATA / Tribal Areas",
    "3": "Punjab",
    "4": "Sindh",
    "5": "Balochistan",
    "6": "Islamabad Capital Territory",
    "7": "Gilgit-Baltistan",
    "8": "Azad Kashmir",
}

_DISTRICT_BY_PREFIX: dict[str, dict[str, str]] = {
    "Punjab": {
        "35201": "Lahore",
        "35202": "Sheikhupura",
        "35301": "Gujranwala",
        "35401": "Sialkot",
        "37201": "Faisalabad",
        "38101": "Multan",
        "39101": "Rawalpindi",
    },
    "Sindh": {
        "42201": "Karachi",
        "43501": "Hyderabad",
        "45201": "Sukkur",
    },
    "Khyber Pakhtunkhwa": {
        "11101": "Peshawar",
        "13101": "Mardan",
        "15101": "Abbottabad",
    },
    "Balochistan": {
        "51201": "Quetta",
        "52201": "Khuzdar",
    },
    "Islamabad Capital Territory": {
        "61101": "Islamabad",
    },
    "Azad Kashmir": {
        "81101": "Muzaffarabad",
    },
    "Gilgit-Baltistan": {
        "71101": "Gilgit",
    },
}


def _normalize_nic(nic: Any) -> str:
    text = str(nic or "").strip()
    return "".join(ch for ch in text if ch.isdigit())


def cnic_location(nic: Any) -> dict[str, str]:
    """Return province and district for a Pakistani CNIC/NIC."""
    digits = _normalize_nic(nic)
    if len(digits) < 1:
        return {"province": "", "district": ""}
    province = _PROVINCE_BY_FIRST_DIGIT.get(digits[0], "Unknown")
    district = ""
    if len(digits) >= 5:
        district_map = _DISTRICT_BY_PREFIX.get(province, {})
        district = district_map.get(digits[:5], "")
    return {"province": province, "district": district}
