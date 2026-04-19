"""
Data quality tests for the Compliance Navigator.

These tests validate that the scraped and curated datasets are
complete, well-formed, and functional. Run these after any data
update (re-scrape, new directives, new categories) to catch issues.
"""

import json
from pathlib import Path

import pytest
import yaml

DATA_DIR = Path(__file__).parent.parent / "data"


# ---------------------------------------------------------------------------
# EU Directives
# ---------------------------------------------------------------------------

class TestDirectivesData:
    """Validate the EU directives dataset."""

    @pytest.fixture(autouse=True)
    def load_directives(self):
        with open(DATA_DIR / "eu-directives" / "directives.json") as f:
            self.directives = json.load(f)

    def test_file_exists_and_not_empty(self):
        assert len(self.directives) > 0

    def test_minimum_directive_count(self):
        """We should have at least 10 core directives."""
        assert len(self.directives) >= 10

    def test_required_fields_present(self):
        """Every directive must have all required fields."""
        required = ["id", "short_name", "full_name", "scope", "market", "url",
                     "applicability", "key_requirements"]
        for d in self.directives:
            for field in required:
                assert field in d, f"Directive {d.get('id', '?')} missing field: {field}"

    def test_ids_are_unique(self):
        ids = [d["id"] for d in self.directives]
        assert len(ids) == len(set(ids)), f"Duplicate directive IDs: {[x for x in ids if ids.count(x) > 1]}"

    def test_short_names_are_unique(self):
        names = [d["short_name"] for d in self.directives]
        assert len(names) == len(set(names)), f"Duplicate short names: {[x for x in names if names.count(x) > 1]}"

    def test_urls_are_eurlex(self):
        """All directive URLs should point to EUR-Lex."""
        for d in self.directives:
            assert "eur-lex.europa.eu" in d["url"], f"{d['id']} has non-EUR-Lex URL: {d['url']}"

    def test_applicability_rules_are_valid(self):
        """Applicability rules must have condition + operator."""
        valid_operators = {"between", "in", "equals", "true"}
        for d in self.directives:
            for rule in d["applicability"]:
                if rule.get("condition") == "logic":
                    continue  # OR/AND logic markers
                assert "condition" in rule, f"{d['id']} has rule without condition"
                assert "operator" in rule, f"{d['id']} has rule without operator: {rule}"
                assert rule["operator"] in valid_operators, (
                    f"{d['id']} has unknown operator: {rule['operator']}"
                )

    def test_key_requirements_not_empty(self):
        """Every directive should have at least one requirement."""
        for d in self.directives:
            assert len(d["key_requirements"]) > 0, f"{d['id']} has no key requirements"

    def test_core_directives_present(self):
        """The essentials for hardware builders must be in the dataset."""
        short_names = {d["short_name"] for d in self.directives}
        required = {"LVD", "EMC", "RoHS", "WEEE", "REACH", "RED", "GPSD",
                     "Food Contact", "Packaging", "Battery Regulation"}
        missing = required - short_names
        assert not missing, f"Missing core directives: {missing}"


# ---------------------------------------------------------------------------
# CPSC Recalls
# ---------------------------------------------------------------------------

class TestRecallsData:
    """Validate the CPSC recall dataset."""

    @pytest.fixture(autouse=True)
    def load_recalls(self):
        path = DATA_DIR / "cpsc-recalls" / "recalls.json"
        if path.exists():
            with open(path) as f:
                self.recalls = json.load(f)
        else:
            self.recalls = []

    def test_file_exists_and_not_empty(self):
        assert len(self.recalls) > 0, "recalls.json is empty or missing"

    def test_minimum_recall_count(self):
        """We should have thousands of recalls."""
        assert len(self.recalls) >= 5000, f"Only {len(self.recalls)} recalls – expected 5000+"

    def test_required_fields_present(self):
        """Every recall must have core fields."""
        required = ["recall_id", "date", "product_name", "hazard", "category"]
        for r in self.recalls[:100]:  # Spot-check first 100
            for field in required:
                assert field in r, f"Recall {r.get('recall_id', '?')} missing field: {field}"

    def test_recall_ids_are_unique(self):
        ids = [r["recall_id"] for r in self.recalls]
        assert len(ids) == len(set(ids)), "Duplicate recall IDs found"

    def test_categories_are_known(self):
        """All assigned categories should be from our defined set."""
        valid = {"electronics", "heating_device", "kitchen_appliance", "lighting",
                 "battery", "toy", "children", "outdoor", "furniture",
                 "personal_care", "electrical", "other"}
        for r in self.recalls:
            assert r["category"] in valid, (
                f"Recall {r['recall_id']} has unknown category: {r['category']}"
            )

    def test_dates_are_parseable(self):
        """Dates should be in ISO format."""
        import re
        pattern = re.compile(r"^\d{4}-\d{2}-\d{2}")
        for r in self.recalls[:200]:  # Spot-check
            if r["date"]:
                assert pattern.match(r["date"]), (
                    f"Recall {r['recall_id']} has unparseable date: {r['date']}"
                )

    def test_category_distribution_reasonable(self):
        """No single category should dominate >50% of all recalls."""
        from collections import Counter
        counts = Counter(r["category"] for r in self.recalls)
        total = len(self.recalls)
        for cat, count in counts.items():
            ratio = count / total
            assert ratio < 0.5, f"Category '{cat}' is {ratio:.0%} of all recalls – suspiciously dominant"

    def test_heating_recalls_exist(self):
        """We need heating device recalls for the reference implementation."""
        heating = [r for r in self.recalls if r["category"] == "heating_device"]
        assert len(heating) >= 50, f"Only {len(heating)} heating recalls – need more for useful risk analysis"

    def test_category_files_match_main(self):
        """By-category JSON files should sum to the same total as recalls.json."""
        by_cat_dir = DATA_DIR / "cpsc-recalls" / "by-category"
        if not by_cat_dir.exists():
            pytest.skip("by-category dir not present")
        total = 0
        for cat_file in by_cat_dir.glob("*.json"):
            with open(cat_file) as f:
                total += len(json.load(f))
        assert total == len(self.recalls), (
            f"Category files have {total} recalls but main has {len(self.recalls)}"
        )


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

class TestMetadata:
    """Validate scrape metadata."""

    def test_metadata_exists(self):
        path = DATA_DIR / "cpsc-recalls" / "metadata.json"
        assert path.exists()

    def test_metadata_has_required_fields(self):
        with open(DATA_DIR / "cpsc-recalls" / "metadata.json") as f:
            meta = json.load(f)
        assert "scrape_date" in meta
        assert "total_recalls" in meta
        assert "categories" in meta
        assert meta["total_recalls"] > 0

    def test_metadata_count_matches_data(self):
        with open(DATA_DIR / "cpsc-recalls" / "metadata.json") as f:
            meta = json.load(f)
        with open(DATA_DIR / "cpsc-recalls" / "recalls.json") as f:
            recalls = json.load(f)
        assert meta["total_recalls"] == len(recalls)


# ---------------------------------------------------------------------------
# Standard Map
# ---------------------------------------------------------------------------

class TestStandardMap:
    """Validate the standard applicability map."""

    @pytest.fixture(autouse=True)
    def load_map(self):
        with open(DATA_DIR / "standard-map.yaml") as f:
            self.smap = yaml.safe_load(f)
        self.categories = self.smap.get("categories", {})

    def test_file_exists_and_not_empty(self):
        assert len(self.categories) > 0

    def test_minimum_category_count(self):
        """We should have at least 10 product categories."""
        assert len(self.categories) >= 10, f"Only {len(self.categories)} categories"

    def test_required_fields_per_category(self):
        """Each category must have description, directives, and standards."""
        for name, data in self.categories.items():
            assert "description" in data, f"Category '{name}' missing description"
            assert "eu_directives" in data or "note" in data, (
                f"Category '{name}' missing eu_directives"
            )
            assert "en_standards" in data, f"Category '{name}' missing en_standards"

    def test_directive_references_are_valid(self):
        """All directive IDs in the standard map should exist in directives.json."""
        with open(DATA_DIR / "eu-directives" / "directives.json") as f:
            directives = json.load(f)
        valid_ids = {d["id"] for d in directives}

        for name, data in self.categories.items():
            for did in data.get("eu_directives", []):
                assert did in valid_ids, (
                    f"Category '{name}' references unknown directive: {did}"
                )

    def test_key_categories_present(self):
        """Essential categories for hardware builders must exist."""
        required = {
            "consumer_electronics", "usb_powered_device", "battery_powered_device",
            "iot_device", "heating_device", "kitchen_appliance", "toy",
        }
        missing = required - set(self.categories.keys())
        assert not missing, f"Missing key categories: {missing}"

    def test_cost_estimates_present(self):
        """Most categories should have test cost estimates."""
        with_costs = sum(
            1 for data in self.categories.values()
            if "typical_test_costs" in data
        )
        ratio = with_costs / len(self.categories)
        assert ratio >= 0.7, f"Only {ratio:.0%} of categories have cost estimates"

    def test_pitfalls_present(self):
        """Most categories should have common pitfalls."""
        with_pitfalls = sum(
            1 for data in self.categories.values()
            if data.get("common_pitfalls")
        )
        ratio = with_pitfalls / len(self.categories)
        assert ratio >= 0.7, f"Only {ratio:.0%} of categories have pitfalls"


# ---------------------------------------------------------------------------
# End-to-end: data flows into navigator correctly
# ---------------------------------------------------------------------------

class TestDataIntegration:
    """Verify that scraped data actually works in the navigator."""

    def test_every_category_returns_results(self):
        """Running a check for each category should return at least one directive."""
        from compliance_nav.models import Product
        from compliance_nav.navigator import check_compliance, _get_standard_map

        smap = _get_standard_map()
        categories = list(smap.get("categories", {}).keys())

        for cat in categories:
            product = Product(name=f"Test {cat}", types=[cat], markets=["EU"])
            result = check_compliance(product)
            assert (
                len(result.applicable_directives) > 0
                or len(result.applicable_standards) > 0
            ), f"Category '{cat}' returned zero directives and zero standards"

    def test_recall_search_returns_results_for_major_categories(self):
        """Major product categories should find related recalls."""
        from compliance_nav.models import Product
        from compliance_nav.navigator import check_compliance

        major = ["consumer_electronics", "heating_device", "kitchen_appliance",
                 "toy", "lighting", "battery_powered_device"]
        for cat in major:
            product = Product(name=f"Test {cat}", types=[cat], markets=["US"])
            result = check_compliance(product)
            assert len(result.related_recalls) > 0, (
                f"Category '{cat}' found zero related recalls"
            )

    def test_checklist_generated_for_eu_products(self):
        """Any EU electronic product should get a non-empty checklist."""
        from compliance_nav.models import Product
        from compliance_nav.navigator import check_compliance

        product = Product(
            name="Generic EU Electronics",
            types=["consumer_electronics"],
            markets=["EU"],
            intended_use="consumer",
        )
        result = check_compliance(product)
        assert len(result.checklist) >= 5, (
            f"Only {len(result.checklist)} checklist items for EU electronics"
        )
