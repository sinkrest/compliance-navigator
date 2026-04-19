"""Tests for the Compliance Navigator."""

import pytest

from compliance_nav.models import Product
from compliance_nav.navigator import check_compliance


def test_heated_mug_directives():
    """USB heated mug should trigger EMC, RoHS, WEEE, REACH, Food Contact, Packaging, GPSD."""
    product = Product(
        name="HeatMug USB-C",
        types=["heating_device", "usb_powered_device", "food_contact_product", "consumer_electronics"],
        markets=["EU"],
        voltage_dc=20,
        power_watts=20,
        materials=["stainless_steel", "silicone", "abs_plastic"],
        food_contact="indirect",
        intended_use="consumer",
    )
    result = check_compliance(product)
    directive_ids = {d.short_name for d in result.applicable_directives}

    assert "EMC" in directive_ids
    assert "RoHS" in directive_ids
    assert "WEEE" in directive_ids
    assert "REACH" in directive_ids
    assert "Food Contact" in directive_ids
    assert "Packaging" in directive_ids
    assert "GPSD" in directive_ids


def test_heated_mug_no_lvd():
    """USB heated mug at 20V DC should NOT trigger LVD (threshold is 75V DC)."""
    product = Product(
        name="HeatMug USB-C",
        types=["heating_device", "usb_powered_device"],
        markets=["EU"],
        voltage_dc=20,
    )
    result = check_compliance(product)
    directive_ids = {d.short_name for d in result.applicable_directives}

    assert "LVD" not in directive_ids


def test_mains_powered_triggers_lvd():
    """A 230V AC product should trigger LVD."""
    product = Product(
        name="Mains Heater",
        types=["heating_device"],
        markets=["EU"],
        voltage_ac=230,
        intended_use="consumer",
    )
    result = check_compliance(product)
    directive_ids = {d.short_name for d in result.applicable_directives}

    assert "LVD" in directive_ids


def test_wireless_iot_triggers_red():
    """A wireless IoT device should trigger RED."""
    product = Product(
        name="WiFi Sensor",
        types=["iot_device", "wireless_device"],
        markets=["EU"],
        wireless=True,
        intended_use="consumer",
    )
    result = check_compliance(product)
    directive_ids = {d.short_name for d in result.applicable_directives}

    assert "RED" in directive_ids
    assert "RoHS" in directive_ids
    assert "WEEE" in directive_ids


def test_battery_product_triggers_battery_reg():
    """A battery-powered product should trigger Battery Regulation."""
    product = Product(
        name="Portable Speaker",
        types=["consumer_electronics", "battery_powered_device"],
        markets=["EU"],
        battery=True,
        intended_use="consumer",
    )
    result = check_compliance(product)
    directive_ids = {d.short_name for d in result.applicable_directives}

    assert "Battery Regulation" in directive_ids


def test_toy_triggers_toy_safety():
    """A children's toy should trigger Toy Safety Directive."""
    product = Product(
        name="Electronic Learning Toy",
        types=["toy"],
        markets=["EU"],
        intended_age_group="children",
        intended_use="consumer",
    )
    result = check_compliance(product)
    directive_ids = {d.short_name for d in result.applicable_directives}

    assert "Toy Safety" in directive_ids
    assert "RoHS" in directive_ids


def test_us_only_skips_eu_directives():
    """A US-only product should not get EU directives."""
    product = Product(
        name="US Only Widget",
        types=["consumer_electronics"],
        markets=["US"],
        intended_use="consumer",
    )
    result = check_compliance(product)

    # All our directives are EU, so none should apply for US-only
    assert len(result.applicable_directives) == 0


def test_checklist_generated():
    """Compliance check should generate a non-empty checklist."""
    product = Product(
        name="Test Product",
        types=["consumer_electronics"],
        markets=["EU"],
        intended_use="consumer",
    )
    result = check_compliance(product)

    assert len(result.checklist) > 0
    assert all(item.priority in ("required", "recommended", "optional") for item in result.checklist)


def test_recalls_found_for_heating():
    """Heating device should find related recalls."""
    product = Product(
        name="Test Heater",
        types=["heating_device"],
        markets=["US"],
    )
    result = check_compliance(product)

    # CPSC dataset should have heating_device recalls
    assert len(result.related_recalls) > 0


def test_risk_notes_for_heating():
    """Heating products should get risk notes."""
    product = Product(
        name="Test Heater",
        types=["heating_device"],
        markets=["EU"],
        intended_use="consumer",
    )
    result = check_compliance(product)

    assert len(result.risk_notes) > 0
    assert any("heating" in note.lower() or "recall" in note.lower() for note in result.risk_notes)


def test_multiple_markets_warning():
    """Selecting both EU and US should produce a warning."""
    product = Product(
        name="Global Product",
        types=["consumer_electronics"],
        markets=["EU", "US"],
        intended_use="consumer",
    )
    result = check_compliance(product)

    assert any("multiple markets" in w.lower() for w in result.warnings)
