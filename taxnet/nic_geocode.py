"""Pakistani CNIC/NIC prefix geocoding and district risk lookup."""

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
        "35203": "Nankana Sahib",
        "35301": "Gujranwala",
        "35302": "Narowal",
        "35303": "Sialkot",
        "35401": "Sialkot",
        "35402": "Narowal",
        "35501": "Gujrat",
        "35601": "Mandi Bahauddin",
        "35701": "Hafizabad",
        "35801": "Sargodha",
        "36101": "Faisalabad",
        "36201": "Jhang",
        "36301": "Toba Tek Singh",
        "37101": "Rawalpindi",
        "37201": "Faisalabad",
        "37301": "Chakwal",
        "37401": "Jhelum",
        "37501": "Attock",
        "38101": "Multan",
        "38201": "Khanewal",
        "38301": "Vehari",
        "38401": "Lodhran",
        "39101": "Rawalpindi",
        "39201": "Sahiwal",
        "39301": "Pakpattan",
        "39401": "Okara",
        "39501": "Bahawalpur",
        "39601": "Bahawalnagar",
        "39701": "Rahim Yar Khan",
        "39801": "Dera Ghazi Khan",
        "39901": "Layyah",
        "31001": "Muzaffargarh",
    },
    "Sindh": {
        "42201": "Karachi",
        "42301": "Karachi",
        "42401": "Karachi",
        "42501": "Karachi",
        "42601": "Karachi",
        "42701": "Karachi",
        "43501": "Hyderabad",
        "43601": "Badin",
        "43701": "Thatta",
        "43801": "Dadu",
        "43901": "Jamshoro",
        "44201": "Mirpur Khas",
        "44301": "Umerkot",
        "44401": "Tharparkar",
        "44501": "Sanghar",
        "45201": "Sukkur",
        "45301": "Khairpur",
        "45401": "Ghotki",
        "45501": "Shaheed Benazirabad",
        "46201": "Larkana",
        "46301": "Qambar Shahdadkot",
        "46401": "Jacobabad",
        "46501": "Kashmore",
        "46601": "Shikarpur",
    },
    "Khyber Pakhtunkhwa": {
        "11101": "Peshawar",
        "11201": "Charsadda",
        "11301": "Nowshera",
        "12101": "Mardan",
        "12201": "Swabi",
        "13101": "Mardan",
        "13201": "Kohat",
        "13301": "Karak",
        "13401": "Hangu",
        "14101": "Abbottabad",
        "14201": "Haripur",
        "14301": "Mansehra",
        "15101": "Abbottabad",
        "16101": "Swat",
        "16201": "Buner",
        "16301": "Shangla",
        "17101": "Dir",
        "17201": "Chitral",
        "18101": "Kohistan",
        "19101": "Bannu",
        "19201": "Lakki Marwat",
        "20101": "Dera Ismail Khan",
        "20201": "Tank",
        "21101": "Malakand",
        "21201": "Bajaur",
        "22101": "Mohmand",
        "23101": "Khyber",
        "24101": "Orakzai",
        "25101": "Kurram",
        "26101": "North Waziristan",
        "27101": "South Waziristan",
        "28101": "Waziristan",
    },
    "Balochistan": {
        "51201": "Quetta",
        "51301": "Pishin",
        "51401": "Killa Abdullah",
        "51501": "Chaman",
        "52101": "Zhob",
        "52201": "Khuzdar",
        "52301": "Kalat",
        "52401": "Mastung",
        "53101": "Sibi",
        "53201": "Kohlu",
        "53301": "Dera Bugti",
        "54101": "Nasirabad",
        "54201": "Jafarabad",
        "55101": "Turbat",
        "55201": "Gwadar",
        "56101": "Loralai",
        "56201": "Barkhan",
        "57101": "Musakhel",
        "58101": "Ziarat",
        "59101": "Sherani",
        "59201": "Lasbela",
    },
    "Islamabad Capital Territory": {
        "61101": "Islamabad",
    },
    "Gilgit-Baltistan": {
        "71101": "Gilgit",
        "71201": "Skardu",
        "71301": "Chilas",
        "71401": "Hunza",
        "71501": "Ghizer",
        "71601": "Ghanche",
        "71701": "Astore",
        "71801": "Diamer",
    },
    "Azad Kashmir": {
        "81101": "Muzaffarabad",
        "81201": "Hattian Bala",
        "81301": "Neelum",
        "82101": "Mirpur",
        "82201": "Bhimber",
        "82301": "Kotli",
        "83101": "Poonch",
        "83201": "Bagh",
        "83301": "Haveli",
        "83401": "Sudhanoti",
    },
    "FATA / Tribal Areas": {
        "21101": "Bajaur",
        "22101": "Mohmand",
        "23101": "Khyber",
        "24101": "Orakzai",
        "25101": "Kurram",
        "26101": "North Waziristan",
        "27101": "South Waziristan",
    },
}

# Static district risk scores (0–3). Higher values reflect districts that have
# appeared more frequently in public FBR/AML reporting. This is intentionally
# conservative and does not replace macro-economic indicators.
DISTRICT_RISK_SCORES: dict[str, int] = {
    "Karachi": 2,
    "Lahore": 2,
    "Peshawar": 2,
    "Quetta": 2,
    "Islamabad": 1,
    "Rawalpindi": 1,
    "Faisalabad": 1,
    "Multan": 1,
    "Hyderabad": 1,
    "Sukkur": 1,
    "Gujranwala": 1,
    "Sialkot": 1,
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


def extract_prefix(cnic: Any) -> str:
    """Return the 5-digit district prefix of a CNIC."""
    digits = _normalize_nic(cnic)
    return digits[:5] if len(digits) >= 5 else ""


def lookup_district(cnic: Any) -> dict[str, Any]:
    """Return province, district, district risk score and known flag."""
    loc = cnic_location(cnic)
    district = loc["district"]
    return {
        "province": loc["province"],
        "district": district,
        "district_risk_score": DISTRICT_RISK_SCORES.get(district, 0),
        "district_known": bool(district),
    }
