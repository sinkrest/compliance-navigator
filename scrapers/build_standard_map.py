#!/usr/bin/env python3
"""
Build/validate the standard applicability map.

The standard map (data/standard-map.yaml) is primarily hand-curated,
but this script validates it against the directives database and
prints a coverage report.

Usage:
    python scrapers/build_standard_map.py
"""

import json
from pathlib import Path

import yaml

DATA_DIR = Path(__file__).parent.parent / "data"


def main():
    # Load directives
    with open(DATA_DIR / "eu-directives" / "directives.json") as f:
        directives = json.load(f)
    directive_ids = {d["id"] for d in directives}

    # Load standard map
    with open(DATA_DIR / "standard-map.yaml") as f:
        smap = yaml.safe_load(f)

    categories = smap.get("categories", {})
    print(f"Standard map: {len(categories)} categories\n")

    # Validate
    all_referenced = set()
    for cat_name, cat_data in categories.items():
        cat_directives = set(cat_data.get("eu_directives", []))
        all_referenced.update(cat_directives)

        unknown = cat_directives - directive_ids
        if unknown:
            print(f"  WARNING: {cat_name} references unknown directives: {unknown}")

        print(f"  {cat_name}: {len(cat_directives)} directives, "
              f"{len(cat_data.get('en_standards', []))} standards, "
              f"{len(cat_data.get('common_pitfalls', []))} pitfalls")

    # Coverage
    unused = directive_ids - all_referenced
    if unused:
        print(f"\n  Directives not referenced by any category: {unused}")

    print(f"\n  Coverage: {len(all_referenced)}/{len(directive_ids)} directives referenced")


if __name__ == "__main__":
    main()
