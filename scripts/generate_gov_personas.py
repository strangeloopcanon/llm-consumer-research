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
            "occupation": "Students and entry-level workers",
            "education": "Some college or trade program",
            "household": "Roommates or shared housing",
            "purchase_frequency": "Replenishes whitening products every 4-6 weeks",
            "background": (
                "Balances social life, school, and first jobs while building routines."
            ),
            "descriptors": [
                "high social media usage",
                "building oral care habits",
            ],
            "habits": [
                "watches TikTok reviews before buying",
                "experiments with flavor-forward pastes",
            ],
            "motivations": [
                "wants fast cosmetic results ahead of social events",
                "responds to influencer proof",
            ],
            "pain_points": ["worries about enamel sensitivity"],
            "preferred_channels": ["TikTok", "Discount retailers"],
            "notes": "Looks for bundle deals that include whitening strips.",
            "weight": round(groups["18-24"] / total_pop, 4),
        },
        {
            "name": "Prime Working Age 25-44",
            "age": "25-44",
            "gender": "mixed",
            "region": "US",
            "income": "Middle",
            "occupation": "Salaried professionals and parents",
            "education": "Bachelor's or vocational degree",
            "household": "Young families in suburban settings",
            "purchase_frequency": "Keeps toothpaste stocked via monthly trips",
            "background": "Juggles work schedules with family health routines.",
            "descriptors": ["busy professionals", "family-focused"],
            "habits": ["buys at warehouse clubs", "reads parenting blogs for recommendations"],
            "motivations": [
                "seeks reliable preventive care for the household",
                "values dentist endorsements",
            ],
            "pain_points": ["dislikes mess from whitening gels"],
            "preferred_channels": ["Big-box retailers", "Online delivery services"],
            "notes": "Open to auto-ship refills with kid-friendly flavors.",
            "weight": round(groups["25-44"] / total_pop, 4),
        },
        {
            "name": "Midlife Households 45-64",
            "age": "45-64",
            "gender": "mixed",
            "region": "US",
            "income": "Middle-upper",
            "occupation": "Established managers and caregivers",
            "education": "College and postgraduate mix",
            "household": "Multi-person households with teens or aging parents",
            "purchase_frequency": "Sticks to brand multi-packs twice per quarter",
            "background": (
                "Maintains preventive health routines to avoid costly dental visits."
            ),
            "descriptors": [
                "established routines",
                "value preventive care",
            ],
            "habits": [
                "reads Consumer Reports style guides",
                "keeps backup stock in pantry",
            ],
            "motivations": [
                "prioritizes enamel protection and long-term health",
                "trusts ADA-certified claims",
            ],
            "pain_points": ["skeptical of gimmicky claims"],
            "preferred_channels": ["Warehouse clubs", "Dental offices"],
            "notes": "Appreciates subscription programs that include refill reminders.",
            "weight": round(groups["45-64"] / total_pop, 4),
        },
        {
            "name": "Older Adults 65+",
            "age": "65+",
            "gender": "mixed",
            "region": "US",
            "income": "Fixed income",
            "occupation": "Retirees and part-time workers",
            "education": "High school plus some college",
            "household": "Smaller households or empty nesters",
            "purchase_frequency": "Purchases gentle formulas every 2-3 months",
            "background": (
                "Focuses on comfort products that address sensitivity and dryness."
            ),
            "descriptors": ["sensitive teeth", "brand loyal"],
            "habits": [
                "reads print circulars for coupons",
                "consults dentists before switching brands",
            ],
            "motivations": [
                "wants gentle formulas and medical reassurance",
                "prefers value packs with loyalty rewards",
            ],
            "pain_points": ["dislikes strong abrasives or overpowering mint"],
            "preferred_channels": ["Pharmacies", "Direct mail catalogs"],
            "notes": "Responds well to senior discounts and caregiver bundles.",
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
            "occupation": "Full-time students and part-time service workers",
            "education": "Undergraduate programs",
            "household": "Dorms or shared apartments",
            "purchase_frequency": "Replaces backpacks at start of each semester",
            "background": (
                "Splits time between classes, internships, and commuting across campus."
            ),
            "descriptors": ["enrolled in college", "carry laptops daily"],
            "habits": [
                "walks or bikes to campus with tech gear",
                "compares durability reviews on YouTube",
            ],
            "motivations": [
                "wants lightweight protection for electronics",
                "looks for multi-pocket organization",
            ],
            "pain_points": ["straps fray under heavy textbooks"],
            "preferred_channels": ["Campus bookstores", "Online marketplaces"],
            "notes": "Responds to student discounts and bundle deals with accessories.",
            "weight": round(segments["Campus"] / total, 4),
        },
        {
            "name": "Outdoor Weekenders",
            "age": "25-44",
            "gender": "mixed",
            "region": "US",
            "income": "$50k-$99k",
            "occupation": "Healthcare, education, and public sector professionals",
            "education": "Mix of bachelor's and associate degrees",
            "household": "Young families in suburban neighborhoods",
            "purchase_frequency": "Adds gear seasonally ahead of trips",
            "background": (
                "Plans family day trips and hiking weekends that demand versatile storage."
            ),
            "descriptors": [
                "householders 25-44",
                "middle income",
                "active lifestyles",
            ],
            "habits": ["researches gear blogs", "shops in-store to test comfort"],
            "motivations": [
                "needs rugged bags that transition from work to trails",
                "values warranty coverage",
            ],
            "pain_points": ["dislikes bags that lack water resistance"],
            "preferred_channels": ["Sporting goods chains", "Brand outlet stores"],
            "notes": "Prefers earth-tone palettes and modular add-ons.",
            "weight": round(segments["MidIncome"] / total, 4),
        },
        {
            "name": "Minimalist Professionals",
            "age": "25-44",
            "gender": "mixed",
            "region": "US",
            "income": "$100k+",
            "occupation": "Tech, finance, and consulting roles",
            "education": "Bachelor's and graduate degrees",
            "household": "Urban households with limited storage",
            "purchase_frequency": "Upgrades premium gear every 18 months",
            "background": (
                "Values design-led products that look polished in client meetings."
            ),
            "descriptors": [
                "householders 25-44",
                "urban professionals",
                "premium gear seekers",
            ],
            "habits": [
                "follows minimalist product reviewers",
                "shops direct-to-consumer brands",
            ],
            "motivations": [
                "needs slim profiles that fit carry-on rules",
                "expects laptop-first compartments with cable management",
            ],
            "pain_points": ["rejects noisy branding or bulky silhouettes"],
            "preferred_channels": ["Direct brand websites", "Boutique tech retailers"],
            "notes": "Will pay extra for recycled materials and lifetime guarantees.",
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
            "occupation": "Service workers and gig earners",
            "education": "High school plus certificates",
            "household": "Multi-person households relying on smartphones",
            "purchase_frequency": "Adds storage cards with every new device upgrade",
            "background": (
                "Streams entertainment exclusively on mobile networks with tight data caps."
            ),
            "descriptors": ["cell data only", "stream on mobile"],
            "habits": [
                "backs up photos to SD cards",
                "uses prepaid plans and retail kiosks",
            ],
            "motivations": [
                "wants reliable offline media access",
                "prioritizes affordability and durability",
            ],
            "pain_points": ["limited by mobile data throttling"],
            "preferred_channels": ["Big box electronics aisles", "Wireless carrier stores"],
            "notes": "Looks for bundles that include adapters across Android devices.",
            "weight": round(segments["CellOnly"] / total, 4),
        },
        {
            "name": "Broadband Power Users",
            "age": "25-64",
            "gender": "mixed",
            "region": "US",
            "income": "Middle-upper",
            "occupation": "Remote professionals and content creators",
            "education": "Bachelor's degrees and certifications",
            "household": "Dual-income households with home offices",
            "purchase_frequency": "Purchases high-capacity drives quarterly for backups",
            "background": (
                "Moves large media files daily for work-from-home setups."
            ),
            "descriptors": ["cable/fiber broadband only", "heavy file usage"],
            "habits": [
                "runs automated backups overnight",
                "compares transfer speeds in tech forums",
            ],
            "motivations": [
                "needs redundancy for client deliverables",
                "values encryption and reliability",
            ],
            "pain_points": [
                "frustrated by slow write speeds and drive failures",
            ],
            "preferred_channels": ["Online specialty retailers", "Manufacturer direct stores"],
            "notes": "Interested in bundled cloud + hardware plans.",
            "weight": round(segments["BroadbandCable"] / total, 4),
        },
        {
            "name": "Offline Households",
            "age": "35+",
            "gender": "mixed",
            "region": "US",
            "income": "Varied",
            "occupation": "Retired or fixed-income households",
            "education": "High school graduates",
            "household": "Rural or small-town residences with limited broadband",
            "purchase_frequency": "Buys external drives annually for photo archival",
            "background": (
                "Keeps family records and media offline due to unreliable internet access."
            ),
            "descriptors": ["no internet access", "rely on physical backups"],
            "habits": [
                "prints photos and backs up on DVDs",
                "shops local hardware stores for tech",
            ],
            "motivations": [
                "wants simple plug-and-play storage",
                "looks for long warranties",
            ],
            "pain_points": ["intimidated by complex setup instructions"],
            "preferred_channels": ["Local electronics shops", "Mail-order catalogs"],
            "notes": "Responds to phone support and easy-start guides.",
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
