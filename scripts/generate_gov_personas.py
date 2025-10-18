from pathlib import Path
from typing import Dict, List

import requests
import yaml

CENSUS_BASE = "https://api.census.gov/data/2022/acs/acs1"
DATA_DIR = Path("src/ssr_service/data/personas")
DATA_DIR.mkdir(parents=True, exist_ok=True)


def fetch_census(variables: List[str]) -> Dict[str, int]:
    params = {
        "get": ",".join(["NAME"] + variables),
        "for": "us:1",
    }
    resp = requests.get(CENSUS_BASE, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    header = data[0]
    values = data[1]
    return {var: int(values[header.index(var)]) for var in variables}


def make_us_toothpaste() -> Dict:
    vars_needed = [
        "B01001_007E", "B01001_008E", "B01001_009E", "B01001_010E",
        "B01001_031E", "B01001_032E", "B01001_033E", "B01001_034E",
        "B01001_011E", "B01001_012E", "B01001_013E", "B01001_014E",
        "B01001_035E", "B01001_036E", "B01001_037E", "B01001_038E",
        "B01001_015E", "B01001_016E", "B01001_017E", "B01001_018E", "B01001_019E",
        "B01001_039E", "B01001_040E", "B01001_041E", "B01001_042E", "B01001_043E",
        "B01001_020E",
        "B01001_021E",
        "B01001_022E",
        "B01001_023E",
        "B01001_024E",
        "B01001_025E",
        "B01001_044E",
        "B01001_045E",
        "B01001_046E",
        "B01001_047E",
        "B01001_048E",
        "B01001_049E",
    ]
    data = fetch_census(vars_needed)

    def total(codes: List[str]) -> int:
        return sum(data[c] for c in codes)

    groups = {
        "18-24": total([
            "B01001_007E", "B01001_008E", "B01001_009E", "B01001_010E",
            "B01001_031E", "B01001_032E", "B01001_033E", "B01001_034E",
        ]),
        "25-44": total([
            "B01001_011E", "B01001_012E", "B01001_013E", "B01001_014E",
            "B01001_035E", "B01001_036E", "B01001_037E", "B01001_038E",
        ]),
        "45-64": total([
            "B01001_015E", "B01001_016E", "B01001_017E", "B01001_018E", "B01001_019E",
            "B01001_039E", "B01001_040E", "B01001_041E", "B01001_042E", "B01001_043E",
        ]),
        "65+": total(
            [
                "B01001_020E",
                "B01001_021E",
                "B01001_022E",
                "B01001_023E",
                "B01001_024E",
                "B01001_025E",
                "B01001_044E",
                "B01001_045E",
                "B01001_046E",
                "B01001_047E",
                "B01001_048E",
                "B01001_049E",
            ]
        ),
    }
    total_pop = sum(groups.values())

    personas = [
        {
            "name": "Young Adults 18-24",
            "age": "18-24",
            "gender": "mixed",
            "region": "US",
            "income": "Varied",
            "descriptors": [
                "high social media usage",
                "building oral care habits",
            ],
            "weight": round(groups["18-24"] / total_pop, 4),
        },
        {
            "name": "Prime Working Age 25-44",
            "age": "25-44",
            "gender": "mixed",
            "region": "US",
            "income": "Middle",
            "descriptors": ["busy professionals", "family-focused"],
            "weight": round(groups["25-44"] / total_pop, 4),
        },
        {
            "name": "Midlife Households 45-64",
            "age": "45-64",
            "gender": "mixed",
            "region": "US",
            "income": "Middle-upper",
            "descriptors": [
                "established routines",
                "value preventive care",
            ],
            "weight": round(groups["45-64"] / total_pop, 4),
        },
        {
            "name": "Older Adults 65+",
            "age": "65+",
            "gender": "mixed",
            "region": "US",
            "income": "Fixed income",
            "descriptors": ["sensitive teeth", "brand loyal"],
            "weight": round(groups["65+"] / total_pop, 4),
        },
    ]

    return {
        "group": "us_toothpaste_buyers",
        "description": (
            "Age distribution of US population 18+ from ACS 2022 1-year (Table B01001)."
        ),
        "source": "https://api.census.gov/data/2022/acs/acs1",
        "personas": personas,
    }


def make_us_backpack() -> Dict:
    college_vars = ["B14004_005E", "B14004_010E", "B14004_021E", "B14004_026E"]
    college_totals = fetch_census(college_vars)
    campus_total = sum(college_totals.values())

    income_vars = [
        "B19037_029E", "B19037_030E", "B19037_031E",
        "B19037_032E", "B19037_033E", "B19037_034E", "B19037_035E",
    ]
    income_totals = fetch_census(["B19037_019E"] + income_vars)
    mid_income = (
        income_totals["B19037_029E"]
        + income_totals["B19037_030E"]
        + income_totals["B19037_031E"]
    )
    high_income = (
        income_totals["B19037_032E"]
        + income_totals["B19037_033E"]
        + income_totals["B19037_034E"]
        + income_totals["B19037_035E"]
    )

    segments = {
        "Campus": campus_total,
        "MidIncome": mid_income,
        "HighIncome": high_income,
    }
    total = sum(segments.values())

    personas = [
        {
            "name": "Campus Commuters",
            "age": "18-24",
            "gender": "mixed",
            "region": "US",
            "income": "Student budget",
            "descriptors": ["enrolled in college", "carry laptops daily"],
            "weight": round(segments["Campus"] / total, 4),
        },
        {
            "name": "Outdoor Weekenders",
            "age": "25-44",
            "gender": "mixed",
            "region": "US",
            "income": "$50k-$99k",
            "descriptors": [
                "householders 25-44",
                "middle income",
                "active lifestyles",
            ],
            "weight": round(segments["MidIncome"] / total, 4),
        },
        {
            "name": "Minimalist Professionals",
            "age": "25-44",
            "gender": "mixed",
            "region": "US",
            "income": "$100k+",
            "descriptors": [
                "householders 25-44",
                "urban professionals",
                "premium gear seekers",
            ],
            "weight": round(segments["HighIncome"] / total, 4),
        },
    ]

    return {
        "group": "us_backpack_buyers",
        "description": (
            "College enrollment from ACS 2022 1-year (B14004) and household income "
            "for age 25-44 from ACS 2022 1-year (B19037). Shares normalized "
            "across segments."
        ),
        "source": "https://api.census.gov/data/2022/acs/acs1",
        "personas": personas,
    }


def make_us_portable_storage() -> Dict:
    internet_vars = ["B28002_006E", "B28002_008E", "B28002_013E"]
    internet_totals = fetch_census(internet_vars)
    segments = {
        "CellOnly": internet_totals["B28002_006E"],
        "BroadbandCable": internet_totals["B28002_008E"],
        "NoInternet": internet_totals["B28002_013E"],
    }
    total = sum(segments.values())

    personas = [
        {
            "name": "Mobile-First Households",
            "age": "18-64",
            "gender": "mixed",
            "region": "US",
            "income": "Varied",
            "descriptors": ["cell data only", "stream on mobile"],
            "weight": round(segments["CellOnly"] / total, 4),
        },
        {
            "name": "Broadband Power Users",
            "age": "25-64",
            "gender": "mixed",
            "region": "US",
            "income": "Middle-upper",
            "descriptors": ["cable/fiber broadband only", "heavy file usage"],
            "weight": round(segments["BroadbandCable"] / total, 4),
        },
        {
            "name": "Offline Households",
            "age": "35+",
            "gender": "mixed",
            "region": "US",
            "income": "Varied",
            "descriptors": ["no internet access", "rely on physical backups"],
            "weight": round(segments["NoInternet"] / total, 4),
        },
    ]

    return {
        "group": "us_portable_storage_buyers",
        "description": (
            "Internet subscription types from ACS 2022 1-year (B28002). "
            "Shares normalized across unique subscription statuses."
        ),
        "source": "https://api.census.gov/data/2022/acs/acs1",
        "personas": personas,
    }


def write_yaml(defn: Dict, filename: str) -> None:
    path = DATA_DIR / filename
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(defn, fh, sort_keys=False)
    print(f"Wrote {path}")


def main() -> None:
    write_yaml(make_us_toothpaste(), "us_toothpaste.yml")
    write_yaml(make_us_backpack(), "us_backpack_buyers.yml")
    write_yaml(make_us_portable_storage(), "us_portable_storage_buyers.yml")


if __name__ == "__main__":
    main()
