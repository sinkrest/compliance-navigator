#!/usr/bin/env python3
"""
Build lightweight data files for the web tool.

Transforms the full datasets into browser-friendly JSON:
- directives.json: as-is (already small, ~16KB)
- standard-map.json: converted from YAML
- recall-stats.json: summarised recall data per category (~5KB)
- recall-samples.json: 5 most recent recalls per category (~50KB)

Usage:
    python scrapers/build_web_data.py

Outputs:
    web/data/directives.json
    web/data/standard-map.json
    web/data/recall-stats.json
    web/data/recall-samples.json
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

import yaml

DATA_DIR = Path(__file__).parent.parent / "data"
WEB_DIR = Path(__file__).parent.parent / "web" / "data"


def build_recall_stats(recalls: list[dict]) -> dict:
    """Summarise recall data by category."""
    stats = {}
    by_category = defaultdict(list)

    for r in recalls:
        by_category[r["category"]].append(r)

    for cat, cat_recalls in by_category.items():
        # Count hazard keywords
        hazard_counts = Counter()
        total_injuries = 0
        total_deaths = 0

        for r in cat_recalls:
            hazard_lower = r.get("hazard", "").lower()
            for keyword in ["fire", "burn", "shock", "laceration", "choking",
                           "fall", "poison", "electrocution", "entrapment",
                           "explosion", "carbon monoxide", "drowning"]:
                if keyword in hazard_lower:
                    hazard_counts[keyword] += 1
            total_injuries += r.get("injuries", 0)
            total_deaths += r.get("deaths", 0)

        top_hazards = [
            {"hazard": h, "count": c}
            for h, c in hazard_counts.most_common(5)
        ]

        stats[cat] = {
            "total": len(cat_recalls),
            "top_hazards": top_hazards,
            "total_injuries": total_injuries,
            "total_deaths": total_deaths,
        }

    return stats


def build_recall_samples(recalls: list[dict], per_category: int = 5) -> dict:
    """Get the N most recent recalls per category."""
    by_category = defaultdict(list)
    for r in recalls:
        by_category[r["category"]].append(r)

    samples = {}
    for cat, cat_recalls in by_category.items():
        sorted_recalls = sorted(cat_recalls, key=lambda x: x.get("date", ""), reverse=True)
        samples[cat] = [
            {
                "date": r["date"][:10] if r["date"] else "",
                "product_name": r["product_name"][:80],
                "hazard": r["hazard"][:200],
                "units": r["units"][:50],
                "url": r["url"],
            }
            for r in sorted_recalls[:per_category]
        ]

    return samples


def main():
    WEB_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Copy directives (already small)
    with open(DATA_DIR / "eu-directives" / "directives.json") as f:
        directives = json.load(f)
    with open(WEB_DIR / "directives.json", "w") as f:
        json.dump(directives, f, separators=(",", ":"))
    print(f"directives.json: {len(directives)} directives")

    # 2. Convert standard map from YAML to JSON
    with open(DATA_DIR / "standard-map.yaml") as f:
        smap = yaml.safe_load(f)
    with open(WEB_DIR / "standard-map.json", "w") as f:
        json.dump(smap, f, separators=(",", ":"))
    print(f"standard-map.json: {len(smap.get('categories', {}))} categories")

    # 3. Build recall stats
    recalls_path = DATA_DIR / "cpsc-recalls" / "recalls.json"
    if recalls_path.exists():
        with open(recalls_path) as f:
            recalls = json.load(f)

        stats = build_recall_stats(recalls)
        with open(WEB_DIR / "recall-stats.json", "w") as f:
            json.dump(stats, f, separators=(",", ":"))
        print(f"recall-stats.json: {len(stats)} categories, {sum(s['total'] for s in stats.values())} total recalls")

        # 4. Build recall samples
        samples = build_recall_samples(recalls)
        with open(WEB_DIR / "recall-samples.json", "w") as f:
            json.dump(samples, f, separators=(",", ":"))
        total_samples = sum(len(v) for v in samples.values())
        print(f"recall-samples.json: {total_samples} sample recalls")

    # Report sizes
    print("\nFile sizes:")
    for f in sorted(WEB_DIR.glob("*.json")):
        size = f.stat().st_size
        print(f"  {f.name}: {size/1024:.1f} KB")


if __name__ == "__main__":
    main()
