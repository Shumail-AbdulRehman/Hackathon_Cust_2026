"""Synthetic Pakistani civic datasets with hidden ground truth."""

from __future__ import annotations

import random
from typing import Any


NAMES = [
    ("Muhammad Ahmed Khan", "Lahore", "House 21 Street 4 DHA Phase 5 Lahore", "03001234567"),
    ("Ali Raza Sheikh", "Karachi", "Bungalow 18 Khayaban e Ittehad DHA Karachi", "03124567890"),
    ("Sara Malik", "Islamabad", "House 7 Street 16 F-10 Islamabad", "03331234567"),
    ("Usman Tariq", "Rawalpindi", "Flat 4 Block C Bahria Town Rawalpindi", "03451230001"),
    ("Nadia Hussain", "Faisalabad", "House 80 Jinnah Colony Faisalabad", "03219876543"),
    ("Bilal Mahmood", "Multan", "House 9 Gulgasht Colony Multan", "03015550991"),
    ("Hira Noor", "Peshawar", "House 42 University Road Peshawar", "03445559000"),
    ("Kamran Ali", "Quetta", "House 11 Zarghoon Road Quetta", "03335557891"),
    ("Zara Iqbal", "Lahore", "House 33 Model Town Lahore", "03008881234"),
    ("Asif Khan", "Karachi", "Flat 15 Clifton Block 5 Karachi", "03117770123"),
    ("Farhan Qureshi", "Islamabad", "House 12 G-11 Islamabad", "03336660001"),
    ("Ayesha Siddiqui", "Lahore", "House 91 Johar Town Lahore", "03224440002"),
]

ASSOCIATES = {
    "P002": [
        ("Noman Raza", "brother"),
        ("Sana Ali", "spouse"),
    ],
    "P004": [
        ("Tariq Usman", "father"),
    ],
    "P009": [
        ("Iqbal Ahmed", "father"),
    ],
}

LUXURY_MODELS = [
    ("Toyota Land Cruiser ZX", 3000),
    ("Mercedes S400", 3000),
    ("BMW X7", 2998),
    ("Audi Q7", 3000),
]

NORMAL_MODELS = [
    ("Suzuki Alto", 660),
    ("Toyota Corolla", 1300),
    ("Honda City", 1300),
    ("Suzuki Cultus", 1000),
]

URDU_NAME_VARIANTS = {
    "Muhammad Ahmed Khan": "محمد احمد خان",
    "Ali Raza Sheikh": "علی رضا شیخ",
    "Sara Malik": "سارہ ملک",
    "Usman Tariq": "عثمان طارق",
}

SYNTHETIC_FIRST_NAMES = [
    "Hamza",
    "Danish",
    "Mariam",
    "Imran",
    "Saad",
    "Rabia",
    "Omer",
    "Mehwish",
]

SYNTHETIC_LAST_NAMES = [
    "Khan",
    "Raza",
    "Malik",
    "Sheikh",
    "Qureshi",
    "Siddiqui",
    "Iqbal",
    "Tariq",
]

AREAS_BY_CITY = {
    "Lahore": "Johar Town",
    "Karachi": "DHA",
    "Islamabad": "G-11",
    "Rawalpindi": "Bahria Town",
    "Faisalabad": "Jinnah Colony",
    "Multan": "Gulgasht Colony",
    "Peshawar": "University Road",
    "Quetta": "Zarghoon Road",
}


def mutate_name(name: str, rng: random.Random, include_urdu_noise: bool = False) -> str:
    if include_urdu_noise and name in URDU_NAME_VARIANTS and rng.random() < 0.14:
        return URDU_NAME_VARIANTS[name]
    parts = name.split()
    choices = [
        name,
        name.replace("Muhammad", "M."),
        name.replace("Muhammad", "Mohd"),
        " ".join(parts[:2]),
        f"Chaudhary {parts[0][0]}. {parts[-1]}" if len(parts) >= 2 else name,
        f"{parts[0][0]}. {' '.join(parts[1:])}" if len(parts) > 1 else name,
    ]
    return rng.choice([choice for choice in choices if choice.strip()])


def mutate_address(address: str, rng: random.Random) -> str:
    replacements = [
        ("House", "H"),
        ("Street", "St"),
        ("Phase", "Ph"),
        ("Block", "Blk"),
        ("Road", "Rd"),
    ]
    result = address
    for left, right in replacements:
        if rng.random() < 0.45:
            result = result.replace(left, right)
    if rng.random() < 0.25:
        result = result.replace(",", "")
    return result


def tax_paid_for(income: int, scenario: str) -> int:
    if scenario in {"direct_luxury", "proxy_luxury"}:
        return 0
    if income < 80000:
        return 2000
    return int(income * 12 * 0.07)


def scenario_for(index: int) -> str:
    if index in {1, 4}:
        return "direct_luxury"
    if index in {2, 9}:
        return "proxy_luxury"
    if index in {5, 8}:
        return "cash_low_tax"
    return "normal"


def person_template(index: int) -> tuple[str, str, str, str]:
    if index <= len(NAMES):
        return NAMES[index - 1]
    city = NAMES[(index - 1) % len(NAMES)][1]
    first = SYNTHETIC_FIRST_NAMES[(index - 1) % len(SYNTHETIC_FIRST_NAMES)]
    last = SYNTHETIC_LAST_NAMES[((index - 1) // len(SYNTHETIC_FIRST_NAMES)) % len(SYNTHETIC_LAST_NAMES)]
    name = f"{first} {last}"
    area = AREAS_BY_CITY.get(city, "Central")
    house = 20 + index * 3
    street = 1 + index % 31
    address = f"House {house} Street {street} {area} {city}"
    phone = f"03{index % 10}{index:08d}"[-11:]
    return name, city, address, phone


def associates_for(person_id: str, person_name: str) -> list[tuple[str, str]]:
    configured = ASSOCIATES.get(person_id)
    if configured:
        return configured
    surname_value = person_name.split()[-1]
    return [(f"Nominee {surname_value}", "associate"), (f"Household {surname_value}", "household")]


def generate_synthetic_datasets(
    seed: int = 42,
    citizens: int = 12,
    include_urdu_noise: bool = True,
) -> dict[str, list[dict[str, Any]]]:
    rng = random.Random(seed)
    people = []
    for idx in range(1, citizens + 1):
        name, city, address, phone = person_template(idx)
        scenario = scenario_for(idx)
        income = rng.choice([45000, 60000, 85000]) if scenario != "normal" else rng.choice([180000, 260000, 420000])
        people.append(
            {
                "id": f"P{idx:03d}",
                "name": name,
                "city": city,
                "address": address,
                "phone": phone,
                "income": income,
                "scenario": scenario,
            }
        )

    tax_rows = []
    vehicle_rows = []
    utility_rows = []
    property_rows = []

    for idx, person in enumerate(people, start=1):
        filer_status = "Non-Filer" if person["scenario"] in {"cash_low_tax", "proxy_luxury"} and rng.random() < 0.6 else "Filer"
        tax_rows.append(
            {
                "fbr_id": f"FBR-{idx:05d}",
                "full_name": mutate_name(person["name"], rng, include_urdu_noise),
                "declared_income_pkr": person["income"],
                "tax_paid_pkr": tax_paid_for(person["income"], person["scenario"]),
                "filer_status": filer_status,
                "reported_address": mutate_address(person["address"], rng),
                "phone_number": person["phone"],
                "_truth_person_id": person["id"],
                "_truth_scenario": person["scenario"],
            }
        )

        bill = rng.choice([18000, 32000, 55000])
        if person["scenario"] in {"direct_luxury", "proxy_luxury"}:
            bill = rng.choice([180000, 240000, 310000])
        utility_rows.append(
            {
                "meter_ref_no": f"LESCO-{idx:06d}" if person["city"] == "Lahore" else f"DISCO-{idx:06d}",
                "consumer_name": mutate_name(person["name"], rng, include_urdu_noise),
                "installation_address": mutate_address(person["address"], rng),
                "avg_monthly_bill_pkr": bill,
                "connection_type": "Residential",
                "_truth_person_id": person["id"],
                "_truth_scenario": person["scenario"],
            }
        )

        if person["scenario"] == "direct_luxury":
            model, cc = rng.choice(LUXURY_MODELS)
            vehicle_rows.append(
                {
                    "vehicle_reg_no": f"{person['city'][:3].upper()}-{rng.randint(1000, 9999)}",
                    "owner_name": mutate_name(person["name"], rng, include_urdu_noise),
                    "engine_capacity_cc": cc,
                    "vehicle_make_model": model,
                    "registration_year": rng.choice([2021, 2022, 2023, 2024]),
                    "owner_address": mutate_address(person["address"], rng),
                    "_truth_person_id": person["id"],
                    "_truth_scenario": person["scenario"],
                }
            )
            property_rows.append(
                {
                    "registry_no": f"REG-{idx:05d}",
                    "buyer_name": mutate_name(person["name"], rng, include_urdu_noise),
                    "seller_name": "Private Seller",
                    "property_address": mutate_address(person["address"], rng),
                    "property_value_pkr": rng.choice([65000000, 92000000, 135000000]),
                    "transfer_date": f"2025-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
                    "area_marla": rng.choice([20, 40, 80]),
                    "property_type": rng.choice(["House", "Plot", "Commercial"]),
                    "_truth_person_id": person["id"],
                    "_truth_scenario": person["scenario"],
                }
            )
        elif person["scenario"] == "proxy_luxury":
            for assoc_index, (associate_name, relation) in enumerate(associates_for(person["id"], person["name"]), start=1):
                associate_id = f"{person['id']}-A{assoc_index}"
                model, cc = rng.choice(LUXURY_MODELS)
                vehicle_rows.append(
                    {
                        "vehicle_reg_no": f"{person['city'][:3].upper()}-{rng.randint(1000, 9999)}",
                        "owner_name": mutate_name(associate_name, rng, include_urdu_noise),
                        "engine_capacity_cc": cc,
                        "vehicle_make_model": model,
                        "registration_year": rng.choice([2022, 2023, 2024]),
                        "owner_address": mutate_address(person["address"], rng),
                        "_truth_person_id": associate_id,
                        "_truth_scenario": f"associate_of_{person['id']}",
                    }
                )
                property_rows.append(
                    {
                        "registry_no": f"REG-{idx:05d}-{assoc_index}",
                        "buyer_name": mutate_name(associate_name, rng, include_urdu_noise),
                        "seller_name": "Private Seller",
                        "property_address": mutate_address(person["address"], rng),
                        "property_value_pkr": rng.choice([45000000, 78000000, 115000000]),
                        "transfer_date": f"2025-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
                        "area_marla": rng.choice([20, 40]),
                        "property_type": rng.choice(["House", "Plot"]),
                        "_truth_person_id": associate_id,
                        "_truth_scenario": f"associate_of_{person['id']}",
                    }
                )
        else:
            if rng.random() < 0.75:
                model, cc = rng.choice(NORMAL_MODELS)
                vehicle_rows.append(
                    {
                        "vehicle_reg_no": f"{person['city'][:3].upper()}-{rng.randint(1000, 9999)}",
                        "owner_name": mutate_name(person["name"], rng, include_urdu_noise),
                        "engine_capacity_cc": cc,
                        "vehicle_make_model": model,
                        "registration_year": rng.choice([2017, 2019, 2020, 2021]),
                        "owner_address": mutate_address(person["address"], rng),
                        "_truth_person_id": person["id"],
                        "_truth_scenario": person["scenario"],
                    }
                )

    return {
        "fbr_tax_records.csv": tax_rows,
        "excise_vehicles.csv": vehicle_rows,
        "disco_consumption.csv": utility_rows,
        "property_transfers.csv": property_rows,
    }
