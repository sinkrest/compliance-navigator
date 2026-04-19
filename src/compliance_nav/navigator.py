"""Core compliance checking logic."""

import json
from pathlib import Path

import yaml

from .models import (
    ChecklistItem,
    ComplianceResult,
    Directive,
    Product,
    Recall,
    Standard,
)

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def _load_directives() -> list[Directive]:
    """Load EU directives from the data file."""
    path = DATA_DIR / "eu-directives" / "directives.json"
    with open(path) as f:
        raw = json.load(f)
    return [
        Directive(
            id=d["id"],
            short_name=d["short_name"],
            full_name=d["full_name"],
            scope=d["scope"],
            market=d["market"],
            url=d["url"],
            applicability=d.get("applicability", []),
            key_requirements=d.get("key_requirements", []),
            referenced_standards=d.get("referenced_standards", []),
            penalties=d.get("penalties", ""),
        )
        for d in raw
    ]


def _load_recalls() -> list[Recall]:
    """Load CPSC recalls from the data file."""
    path = DATA_DIR / "cpsc-recalls" / "recalls.json"
    if not path.exists():
        return []
    with open(path) as f:
        raw = json.load(f)
    return [
        Recall(
            recall_id=r["recall_id"],
            date=r["date"],
            product_name=r["product_name"],
            description=r["description"],
            hazard=r["hazard"],
            remedy=r["remedy"],
            units=r["units"],
            category=r["category"],
            injuries=r.get("injuries", 0),
            deaths=r.get("deaths", 0),
            manufacturer=r.get("manufacturer", ""),
            url=r.get("url", ""),
        )
        for r in raw
    ]


def _load_standard_map() -> dict:
    """Load the standard applicability map."""
    path = DATA_DIR / "standard-map.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


# Cache loaded data
_directives: list[Directive] | None = None
_recalls: list[Recall] | None = None
_standard_map: dict | None = None


def _get_directives() -> list[Directive]:
    global _directives
    if _directives is None:
        _directives = _load_directives()
    return _directives


def _get_recalls() -> list[Recall]:
    global _recalls
    if _recalls is None:
        _recalls = _load_recalls()
    return _recalls


def _get_standard_map() -> dict:
    global _standard_map
    if _standard_map is None:
        _standard_map = _load_standard_map()
    return _standard_map


def _directive_applies(directive: Directive, product: Product) -> bool:
    """Check if a directive's applicability criteria match a product."""
    if not directive.applicability:
        return False

    # Check for OR logic
    has_or = any(
        c.get("condition") == "logic" and c.get("value") == "OR"
        for c in directive.applicability
    )

    conditions = [c for c in directive.applicability if c.get("condition") != "logic"]

    if not conditions:
        return False

    results = []
    for cond in conditions:
        field = cond.get("condition", "")
        op = cond.get("operator", "")

        if field == "voltage_ac" and op == "between":
            if product.voltage_ac is not None:
                results.append(cond["min"] <= product.voltage_ac <= cond["max"])
            else:
                results.append(False)

        elif field == "voltage_dc" and op == "between":
            if product.voltage_dc is not None:
                results.append(cond["min"] <= product.voltage_dc <= cond["max"])
            else:
                results.append(False)

        elif field == "product_type" and op == "in":
            results.append(
                any(t in cond["values"] for t in product.types)
            )

        elif field == "wireless" and op == "equals":
            results.append(product.wireless == cond["value"])

        elif field == "battery" and op == "equals":
            results.append(product.battery == cond["value"])

        elif field == "has_materials" and op == "true":
            results.append(len(product.materials) > 0)

        elif field == "intended_use" and op == "equals":
            results.append(product.intended_use == cond["value"])

        elif field == "intended_use" and op == "in":
            results.append(product.intended_use in cond["values"])

        elif field == "intended_age_group" and op == "equals":
            results.append(product.intended_age_group == cond["value"])

        elif field == "food_contact" and op == "in":
            results.append(product.food_contact in cond["values"])

        else:
            # Unknown condition – be conservative, include it
            results.append(True)

    if not results:
        return False

    if has_or:
        return any(results)
    return all(results)


def _find_related_recalls(product: Product, max_results: int = 20) -> list[Recall]:
    """Find recalls related to the product's categories."""
    recalls = _get_recalls()

    # Map product types to recall categories
    type_to_category = {
        "consumer_electronics": "electronics",
        "usb_powered_device": "electronics",
        "battery_powered_device": "battery",
        "iot_device": "electronics",
        "kitchen_appliance": "kitchen_appliance",
        "heating_device": "heating_device",
        "lighting": "lighting",
        "power_supply": "electrical",
        "wireless_device": "electronics",
        "wearable": "electronics",
        "toy": "toy",
        "food_contact_product": "kitchen_appliance",
        "furniture": "furniture",
        "personal_care": "personal_care",
    }

    target_categories = set()
    for t in product.types:
        if t in type_to_category:
            target_categories.add(type_to_category[t])

    if not target_categories:
        return []

    # Filter recalls by category
    matching = [r for r in recalls if r.category in target_categories]

    # Sort by date (newest first) and limit
    matching.sort(key=lambda r: r.date, reverse=True)
    return matching[:max_results]


def _build_checklist(directives: list[Directive], product: Product) -> list[ChecklistItem]:
    """Generate a compliance checklist from applicable directives."""
    items = []

    # Standard checklist actions per directive type
    checklist_templates = {
        "LVD": [
            ChecklistItem("2014/35/EU", "Safety testing to applicable EN standard", "testing", "required", "€2,000–5,000"),
            ChecklistItem("2014/35/EU", "Prepare technical documentation (risk assessment, test reports, drawings)", "documentation", "required"),
            ChecklistItem("2014/35/EU", "Draft EU Declaration of Conformity", "documentation", "required"),
            ChecklistItem("2014/35/EU", "Affix CE marking to product", "marking", "required"),
        ],
        "EMC": [
            ChecklistItem("2014/30/EU", "EMC testing: conducted + radiated emissions", "testing", "required", "€1,500–4,000"),
            ChecklistItem("2014/30/EU", "EMC testing: immunity (ESD, surge, radiated RF)", "testing", "required"),
            ChecklistItem("2014/30/EU", "EU Declaration of Conformity (can combine with LVD DoC)", "documentation", "required"),
        ],
        "RoHS": [
            ChecklistItem("2011/65/EU", "Collect RoHS declarations from all component suppliers", "documentation", "required"),
            ChecklistItem("2011/65/EU", "XRF screening or chemical analysis of materials if supplier data unavailable", "testing", "recommended", "€500–2,000"),
            ChecklistItem("2011/65/EU", "Prepare RoHS technical documentation per EN IEC 63000", "documentation", "required"),
        ],
        "WEEE": [
            ChecklistItem("2012/19/EU", "Register as EEE producer in each EU country of sale", "registration", "required", "€200–1,000 per country"),
            ChecklistItem("2012/19/EU", "Apply crossed-out wheeled bin marking to product (EN 50419)", "marking", "required"),
            ChecklistItem("2012/19/EU", "Join national compliance scheme (e.g., take-e-back in DE)", "registration", "required"),
        ],
        "REACH": [
            ChecklistItem("EC 1907/2006", "Screen all materials against SVHC Candidate List", "documentation", "required"),
            ChecklistItem("EC 1907/2006", "Obtain REACH declarations from material suppliers", "documentation", "required"),
            ChecklistItem("EC 1907/2006", "SCIP database notification if SVHC >0.1% w/w", "registration", "required"),
        ],
        "RED": [
            ChecklistItem("2014/53/EU", "Radio testing to applicable ETSI EN standard", "testing", "required", "€3,000–8,000"),
            ChecklistItem("2014/53/EU", "EMC testing (included in RED scope)", "testing", "required"),
            ChecklistItem("2014/53/EU", "Safety testing (included in RED scope)", "testing", "required"),
            ChecklistItem("2014/53/EU", "Notified Body assessment if no harmonised standard", "testing", "required"),
            ChecklistItem("2014/53/EU", "EU Declaration of Conformity", "documentation", "required"),
        ],
        "Toy Safety": [
            ChecklistItem("2009/48/EC", "EN 71-1 mechanical and physical testing", "testing", "required", "€1,000–3,000"),
            ChecklistItem("2009/48/EC", "EN 71-2 flammability testing", "testing", "required"),
            ChecklistItem("2009/48/EC", "EN 71-3 chemical migration testing", "testing", "required", "€2,000–5,000"),
            ChecklistItem("2009/48/EC", "Notified Body type-examination (for chemical + electrical)", "testing", "required"),
            ChecklistItem("2009/48/EC", "Age grading and warning labels", "marking", "required"),
        ],
        "Food Contact": [
            ChecklistItem("EC 1935/2004", "Migration testing for all food-contact materials", "testing", "required", "€1,000–4,000 per material"),
            ChecklistItem("EC 1935/2004", "Declarations of Compliance from material suppliers", "documentation", "required"),
            ChecklistItem("EC 1935/2004", "Traceability system for food-contact materials", "documentation", "required"),
        ],
        "Packaging": [
            ChecklistItem("94/62/EC", "Heavy metal testing of packaging (<100 ppm combined)", "testing", "recommended", "€200–500"),
            ChecklistItem("94/62/EC", "Register with national packaging compliance schemes", "registration", "required", "€100–500 per country"),
            ChecklistItem("94/62/EC", "Report packaging quantities annually", "documentation", "required"),
        ],
        "Battery Regulation": [
            ChecklistItem("2023/1542", "Battery safety testing (EN 62133-2 for lithium)", "testing", "required", "€2,000–5,000"),
            ChecklistItem("2023/1542", "UN 38.3 transport testing", "testing", "required", "€1,500–3,000"),
            ChecklistItem("2023/1542", "Battery labelling (capacity, chemistry, collection symbol)", "marking", "required"),
            ChecklistItem("2023/1542", "Battery due diligence for raw material sourcing", "documentation", "required"),
        ],
        "Machinery": [
            ChecklistItem("2006/42/EC", "Risk assessment per EN ISO 12100", "documentation", "required"),
            ChecklistItem("2006/42/EC", "Safety testing to applicable EN standards", "testing", "required", "€3,000–10,000"),
            ChecklistItem("2006/42/EC", "Instructions for use in destination language", "documentation", "required"),
            ChecklistItem("2006/42/EC", "EU Declaration of Conformity + CE marking", "marking", "required"),
        ],
        "GPSD": [
            ChecklistItem("2001/95/EC", "Risk assessment for foreseeable use and misuse", "documentation", "recommended"),
            ChecklistItem("2001/95/EC", "Product identification + producer traceability on product/packaging", "marking", "required"),
        ],
    }

    for d in directives:
        if d.short_name in checklist_templates:
            items.extend(checklist_templates[d.short_name])

    return items


def _generate_risk_notes(
    recalls: list[Recall], product: Product, directives: list[Directive]
) -> list[str]:
    """Generate risk notes from recall data and product attributes."""
    notes = []

    if recalls:
        # Summarise recall patterns
        hazard_keywords = {}
        for r in recalls:
            for word in ["fire", "burn", "shock", "laceration", "choking", "fall", "poison", "electrocution"]:
                if word in r.hazard.lower():
                    hazard_keywords[word] = hazard_keywords.get(word, 0) + 1

        if hazard_keywords:
            top_hazards = sorted(hazard_keywords.items(), key=lambda x: -x[1])[:3]
            hazard_str = ", ".join(f"{h} ({c} recalls)" for h, c in top_hazards)
            notes.append(f"Top hazards in similar product recalls: {hazard_str}")

        total_injuries = sum(r.injuries for r in recalls)
        total_deaths = sum(r.deaths for r in recalls)
        if total_injuries or total_deaths:
            notes.append(
                f"Similar product recalls reported {total_injuries} injuries and {total_deaths} deaths"
            )

    # Product-specific risk notes
    if product.food_contact:
        notes.append(
            "Food contact: migration testing is material-specific – each material "
            "in contact with food needs separate testing"
        )

    if product.battery:
        notes.append(
            "Lithium batteries: UN 38.3 transport testing is mandatory before shipping. "
            "Cannot ship lithium batteries by air without this certification"
        )

    if product.wireless:
        notes.append(
            "Radio equipment: antenna changes (even minor) can invalidate "
            "compliance – re-test after any antenna modification"
        )

    if any(t in product.types for t in ["heating_device", "kitchen_appliance"]):
        notes.append(
            "Heating/kitchen products have high recall rates. "
            "Independent thermal fuse and overheat protection strongly recommended"
        )

    return notes


def _generate_warnings(product: Product, directives: list[Directive]) -> list[str]:
    """Generate warnings about potential compliance issues."""
    warnings = []

    directive_ids = {d.id for d in directives}

    # Check for common oversights
    if "2014/30/EU" in directive_ids and "2014/35/EU" not in directive_ids:
        if product.voltage_dc and product.voltage_dc < 75:
            warnings.append(
                f"LVD does not apply (DC voltage {product.voltage_dc}V < 75V threshold), "
                "but safety testing is still recommended and often required by retailers"
            )

    if product.intended_use == "consumer" and "2001/95/EC" not in directive_ids:
        pass  # GPSD is a catch-all, usually included

    if len(product.markets) > 1:
        warnings.append(
            "Multiple markets selected. Requirements differ between EU and US – "
            "you may need separate testing and documentation for each"
        )

    return warnings


def check_compliance(product: Product) -> ComplianceResult:
    """
    Main entry point: check a product against the compliance database.

    Returns a ComplianceResult with applicable directives, standards,
    related recalls, a compliance checklist, and risk notes.
    """
    all_directives = _get_directives()
    standard_map = _get_standard_map()

    # Step 1: Match directives based on applicability criteria
    applicable = []
    for d in all_directives:
        if d.market == "EU" and "EU" not in product.markets:
            continue
        if _directive_applies(d, product):
            applicable.append(d)

    # Step 2: Enrich with standards from the standard map
    standards = []
    category_data = standard_map.get("categories", {})
    matched_categories = []
    for product_type in product.types:
        if product_type in category_data:
            matched_categories.append(category_data[product_type])

    seen_standards = set()
    for cat_data in matched_categories:
        for std_str in cat_data.get("en_standards", []):
            if std_str not in seen_standards:
                seen_standards.add(std_str)
                # Parse standard ID from string like "EN 62368-1 (Safety)"
                std_id = std_str.split("(")[0].strip()
                std_desc = std_str.split("(")[1].rstrip(")") if "(" in std_str else ""
                standards.append(
                    Standard(
                        id=std_id,
                        name=std_str,
                        scope=std_desc,
                        product_types=product.types,
                    )
                )

    # Step 3: Find related recalls
    related_recalls = _find_related_recalls(product)

    # Step 4: Build checklist
    checklist = _build_checklist(applicable, product)

    # Step 5: Risk notes and warnings
    risk_notes = _generate_risk_notes(related_recalls, product, applicable)
    warnings = _generate_warnings(product, applicable)

    return ComplianceResult(
        product=product,
        applicable_directives=applicable,
        applicable_standards=standards,
        related_recalls=related_recalls,
        checklist=checklist,
        risk_notes=risk_notes,
        warnings=warnings,
    )


def load_product_from_yaml(path: str | Path) -> Product:
    """Load a product definition from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)

    return Product(
        name=data.get("name", "Unknown Product"),
        types=data.get("type", data.get("types", [])),
        markets=data.get("market", data.get("markets", [])),
        description=data.get("description", ""),
        voltage_ac=data.get("voltage_ac"),
        voltage_dc=data.get("voltage_dc"),
        power_watts=data.get("power_watts"),
        wireless=data.get("wireless", False),
        battery=data.get("battery", False),
        materials=data.get("materials", []),
        food_contact=data.get("food_contact"),
        intended_use=data.get("intended_use", "consumer"),
        intended_age_group=data.get("intended_age_group"),
    )
