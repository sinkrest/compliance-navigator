#!/usr/bin/env python3
"""
Scrape the US Consumer Product Safety Commission (CPSC) recall database.

Uses the SaferProducts.gov public REST API (no auth required).
API docs: https://www.saferproducts.gov/RestWebServices

Usage:
    python scrapers/scrape_cpsc.py              # Scrape all recalls
    python scrapers/scrape_cpsc.py --limit 500  # Scrape first 500

Outputs:
    data/cpsc-recalls/recalls.json         – Full dataset
    data/cpsc-recalls/by-category/*.json   – Split by product category
    data/cpsc-recalls/metadata.json        – Scrape metadata
"""

import json
import re
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import requests

API_URL = "https://www.saferproducts.gov/RestWebServices/Recall"
HEADERS = {
    "User-Agent": "ComplianceNavigator/0.1 (https://github.com/forkable-factory/compliance-navigator)",
    "Accept": "application/json",
}

# Keyword-based category assignment
CATEGORY_KEYWORDS = {
    "electronics": [
        "charger", "adapter", "cable", "usb", "computer", "laptop", "tablet",
        "phone", "monitor", "speaker", "headphone", "earphone", "smartwatch",
        "electronic", "circuit", "power bank", "hub", "dongle",
    ],
    "heating_device": [
        "heater", "heating", "heated", "warmer", "warming", "radiator",
        "fireplace", "stove", "furnace", "boiler", "heat pump", "mug warmer",
        "space heater", "baseboard", "thermostat",
    ],
    "kitchen_appliance": [
        "toaster", "blender", "mixer", "microwave", "oven", "cooker",
        "coffee", "kettle", "fryer", "grill", "food processor", "juicer",
        "dishwasher", "refrigerator", "freezer", "range", "cooktop",
        "pressure cooker", "instant pot", "slow cooker", "rice cooker",
    ],
    "lighting": [
        "lamp", "light", "bulb", "led", "chandelier", "fixture",
        "string light", "nightlight", "flashlight", "lantern",
    ],
    "battery": [
        "battery", "lithium", "li-ion", "rechargeable", "power bank",
        "cell", "e-bike battery", "e-scooter battery",
    ],
    "toy": [
        "toy", "doll", "plush", "action figure", "game", "puzzle",
        "building block", "lego", "playset", "playpen", "rattle",
    ],
    "children": [
        "crib", "stroller", "car seat", "highchair", "baby", "infant",
        "child", "kid", "bunk bed", "bib", "pacifier", "bottle",
        "bassinet", "swing", "bouncer", "walker",
    ],
    "outdoor": [
        "grill", "mower", "chainsaw", "trimmer", "pool", "trampoline",
        "bicycle", "scooter", "skateboard", "helmet", "kayak", "tent",
        "camping", "generator", "pressure washer",
    ],
    "furniture": [
        "chair", "table", "desk", "sofa", "bed", "dresser", "shelf",
        "cabinet", "mattress", "ottoman", "bench", "bookcase", "drawer",
    ],
    "personal_care": [
        "hair dryer", "curling iron", "straightener", "shaver", "razor",
        "cosmetic", "cream", "lotion", "skincare", "massage",
    ],
    "electrical": [
        "outlet", "plug", "extension cord", "power strip", "wire",
        "switch", "breaker", "panel", "receptacle", "wiring",
    ],
}


def categorise_recall(product_name: str, description: str) -> str:
    """Assign a category based on keyword matching."""
    text = f"{product_name} {description}".lower()
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[category] = score
    if scores:
        return max(scores, key=scores.get)
    return "other"


def fetch_recalls(limit: int | None = None) -> list[dict]:
    """Fetch recalls from the CPSC API."""
    params = {"format": "json"}
    print("Fetching recalls from CPSC API...")

    try:
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=120)
        resp.raise_for_status()
        raw_recalls = resp.json()
    except requests.exceptions.Timeout:
        print("API timed out. Trying with smaller date ranges...", file=sys.stderr)
        return fetch_recalls_by_year(limit)
    except Exception as e:
        print(f"API error: {e}", file=sys.stderr)
        print("Trying year-by-year fetch...", file=sys.stderr)
        return fetch_recalls_by_year(limit)

    print(f"Received {len(raw_recalls)} raw recall records")

    if limit:
        raw_recalls = raw_recalls[:limit]

    return raw_recalls


def fetch_recalls_by_year(limit: int | None = None) -> list[dict]:
    """Fallback: fetch recalls year by year if the bulk API is slow."""
    all_recalls = []
    current_year = datetime.now().year

    for year in range(current_year, 1970, -1):
        if limit and len(all_recalls) >= limit:
            break

        params = {
            "format": "json",
            "RecallDateStart": f"{year}-01-01",
            "RecallDateEnd": f"{year}-12-31",
        }
        try:
            print(f"  Fetching year {year}...", end=" ", flush=True)
            resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=60)
            resp.raise_for_status()
            year_recalls = resp.json()
            print(f"{len(year_recalls)} recalls")
            all_recalls.extend(year_recalls)
            time.sleep(0.5)  # Be polite
        except Exception as e:
            print(f"Error for {year}: {e}", file=sys.stderr)
            time.sleep(2)
            continue

    return all_recalls[:limit] if limit else all_recalls


def parse_recall(raw: dict) -> dict:
    """Parse a raw CPSC API recall record into our schema."""
    # Extract product names
    products = raw.get("Products", [])
    product_name = ", ".join(p.get("Name", "") for p in products) if products else ""

    # Extract manufacturer
    manufacturers = raw.get("Manufacturers", [])
    manufacturer = ", ".join(m.get("Name", "") for m in manufacturers) if manufacturers else ""

    # Extract hazard description
    hazards = raw.get("Hazards", [])
    hazard = " ".join(h.get("Name", "") for h in hazards) if hazards else ""

    # Extract remedy
    remedies = raw.get("Remedies", [])
    remedy = " ".join(r.get("Name", "") for r in remedies) if remedies else ""

    # Count injuries and deaths
    injuries = 0
    deaths = 0
    for h in hazards:
        injury_text = h.get("Name", "")
        # Try to extract numbers from hazard description
        inj_match = re.search(r"(\d+)\s*(?:report|injur)", injury_text, re.IGNORECASE)
        death_match = re.search(r"(\d+)\s*(?:death|fatal)", injury_text, re.IGNORECASE)
        if inj_match:
            injuries += int(inj_match.group(1))
        if death_match:
            deaths += int(death_match.group(1))

    # Extract units
    units_text = ""
    for p in products:
        if p.get("NumberOfUnits"):
            units_text = p["NumberOfUnits"]
            break

    description = raw.get("Description", "")
    recall_date = raw.get("RecallDate", "")

    return {
        "recall_id": str(raw.get("RecallID", "")),
        "date": recall_date,
        "product_name": product_name,
        "description": description,
        "hazard": hazard,
        "remedy": remedy,
        "units": units_text,
        "injuries": injuries,
        "deaths": deaths,
        "manufacturer": manufacturer,
        "category": categorise_recall(product_name, description),
        "url": raw.get("URL", ""),
    }


def main():
    base_path = Path(__file__).parent.parent / "data" / "cpsc-recalls"
    base_path.mkdir(parents=True, exist_ok=True)
    (base_path / "by-category").mkdir(exist_ok=True)

    # Parse limit arg
    limit = None
    for i, arg in enumerate(sys.argv):
        if arg == "--limit" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])

    # Fetch
    raw_recalls = fetch_recalls(limit=limit)

    if not raw_recalls:
        print("No recalls fetched. Check API connectivity.", file=sys.stderr)
        sys.exit(1)

    # Parse
    print("Parsing recalls...")
    recalls = [parse_recall(r) for r in raw_recalls]

    # Save full dataset
    full_path = base_path / "recalls.json"
    with open(full_path, "w") as f:
        json.dump(recalls, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(recalls)} recalls to {full_path}")

    # Split by category
    by_category: dict[str, list] = {}
    for recall in recalls:
        cat = recall["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(recall)

    for cat, cat_recalls in by_category.items():
        cat_path = base_path / "by-category" / f"{cat}.json"
        with open(cat_path, "w") as f:
            json.dump(cat_recalls, f, indent=2, ensure_ascii=False)

    # Write metadata
    category_counts = {cat: len(recs) for cat, recs in sorted(by_category.items())}
    metadata = {
        "scrape_date": datetime.now().isoformat(),
        "total_recalls": len(recalls),
        "categories": category_counts,
        "source": "https://www.saferproducts.gov/RestWebServices/Recall",
        "licence": "US Government – Public Domain",
    }
    meta_path = base_path / "metadata.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Wrote metadata to {meta_path}")

    # Summary
    print(f"\nCategory distribution:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
