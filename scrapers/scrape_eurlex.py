#!/usr/bin/env python3
"""
Scrape EU directive metadata from EUR-Lex.

For v1, we combine scraped metadata with curated applicability rules.
EUR-Lex pages are public domain (EU law cannot be copyrighted).

Usage:
    python scrapers/scrape_eurlex.py

Outputs:
    data/eu-directives/directives.json
"""

import json
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:{celex_id}"

# Core directives for hardware builders with their CELEX IDs
DIRECTIVES = [
    {
        "celex_id": "32014L0035",
        "id": "2014/35/EU",
        "short_name": "LVD",
        "full_name": "Low Voltage Directive",
        "market": "EU",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32014L0035",
        "scope": "Electrical equipment designed for use with a voltage rating between 50 and 1000 V for alternating current, and between 75 and 1500 V for direct current.",
        "applicability": [
            {"condition": "voltage_ac", "operator": "between", "min": 50, "max": 1000},
            {"condition": "voltage_dc", "operator": "between", "min": 75, "max": 1500},
            {"condition": "logic", "value": "OR"},
        ],
        "key_requirements": [
            "CE marking mandatory",
            "EU Declaration of Conformity required",
            "Technical documentation must be maintained for 10 years",
            "Safety testing to harmonised EN standards",
            "Risk assessment covering electrical, thermal, mechanical, and chemical hazards",
        ],
        "referenced_standards": [
            "EN 62368-1 (Audio/video, IT and communication equipment)",
            "EN 60335-1 (Household appliances – general)",
            "EN 60335-2-15 (Appliances for heating liquids)",
            "EN 61558 (Safety of transformers)",
        ],
        "penalties": "Member states set penalties. Typically: product withdrawal, fines up to €500K+, criminal liability for serious non-compliance.",
    },
    {
        "celex_id": "32014L0030",
        "id": "2014/30/EU",
        "short_name": "EMC",
        "full_name": "Electromagnetic Compatibility Directive",
        "market": "EU",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32014L0030",
        "scope": "All electrical and electronic equipment, fixed installations, and components intended for incorporation into apparatus.",
        "applicability": [
            {"condition": "product_type", "operator": "in", "values": [
                "consumer_electronics", "usb_powered_device", "battery_powered_device",
                "iot_device", "kitchen_appliance", "heating_device", "lighting",
                "power_supply", "wireless_device", "wearable", "audio_video",
                "computing", "personal_care", "toy",
            ]},
        ],
        "key_requirements": [
            "CE marking mandatory",
            "EMC testing: emissions (conducted + radiated) and immunity",
            "EU Declaration of Conformity required",
            "Technical file with test reports",
        ],
        "referenced_standards": [
            "EN 55032 (Emissions – multimedia equipment)",
            "EN 55035 (Immunity – multimedia equipment)",
            "EN 61000-3-2 (Harmonic current emissions)",
            "EN 61000-3-3 (Voltage fluctuations and flicker)",
            "EN 55014-1 (Emissions – household appliances)",
            "EN 55014-2 (Immunity – household appliances)",
        ],
        "penalties": "Member states set penalties. Typically: product withdrawal, fines, market surveillance action.",
    },
    {
        "celex_id": "32011L0065",
        "id": "2011/65/EU",
        "short_name": "RoHS",
        "full_name": "Restriction of Hazardous Substances Directive",
        "market": "EU",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32011L0065",
        "scope": "Electrical and electronic equipment (EEE) including cables and spare parts. Covers 11 categories of EEE.",
        "applicability": [
            {"condition": "product_type", "operator": "in", "values": [
                "consumer_electronics", "usb_powered_device", "battery_powered_device",
                "iot_device", "kitchen_appliance", "heating_device", "lighting",
                "power_supply", "wireless_device", "wearable", "audio_video",
                "computing", "personal_care", "toy", "medical_device_class_I",
            ]},
        ],
        "key_requirements": [
            "10 restricted substances: Lead, Mercury, Cadmium, Hexavalent Chromium, PBB, PBDE, DEHP, BBP, DBP, DIBP",
            "Maximum concentration values (0.1% by weight, 0.01% for cadmium)",
            "Material declarations from all component suppliers",
            "CE marking includes RoHS compliance",
            "Technical documentation with material analysis",
        ],
        "referenced_standards": [
            "EN IEC 63000 (Technical documentation for RoHS assessment)",
        ],
        "penalties": "Fines vary by member state. UK: up to £5,000 per offence. Germany: up to €50,000.",
    },
    {
        "celex_id": "32012L0019",
        "id": "2012/19/EU",
        "short_name": "WEEE",
        "full_name": "Waste Electrical and Electronic Equipment Directive",
        "market": "EU",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32012L0019",
        "scope": "All electrical and electronic equipment. Producers must finance collection, treatment, recovery, and disposal of WEEE.",
        "applicability": [
            {"condition": "product_type", "operator": "in", "values": [
                "consumer_electronics", "usb_powered_device", "battery_powered_device",
                "iot_device", "kitchen_appliance", "heating_device", "lighting",
                "power_supply", "wireless_device", "wearable", "audio_video",
                "computing", "personal_care", "toy",
            ]},
        ],
        "key_requirements": [
            "Register as a producer in each EU member state where you sell",
            "Mark products with crossed-out wheeled bin symbol",
            "Finance end-of-life collection and recycling",
            "Report quantities placed on market annually",
            "Join or set up a compliance scheme in each market",
        ],
        "referenced_standards": [
            "EN 50419 (Marking of EEE – crossed-out bin symbol)",
        ],
        "penalties": "Failure to register: sales prohibition. Fines vary by state. Germany: up to €100,000.",
    },
    {
        "celex_id": "32006R1907",
        "id": "EC 1907/2006",
        "short_name": "REACH",
        "full_name": "Registration, Evaluation, Authorisation and Restriction of Chemicals",
        "market": "EU",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32006R1907",
        "scope": "All chemical substances manufactured in or imported into the EU in quantities of 1 tonne or more per year. Articles containing Substances of Very High Concern (SVHC) above 0.1% w/w.",
        "applicability": [
            {"condition": "has_materials", "operator": "true"},
        ],
        "key_requirements": [
            "Check SVHC Candidate List (updated twice yearly, 200+ substances)",
            "Notify ECHA if article contains SVHC >0.1% w/w and >1 tonne/year",
            "Provide SVHC information to recipients in the supply chain",
            "SCIP database notification for articles containing SVHCs",
            "Supplier declarations for all materials",
        ],
        "referenced_standards": [],
        "penalties": "Vary by state. Can include: sales ban, fines up to €50K+, criminal prosecution.",
    },
    {
        "celex_id": "32014L0053",
        "id": "2014/53/EU",
        "short_name": "RED",
        "full_name": "Radio Equipment Directive",
        "market": "EU",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32014L0053",
        "scope": "Equipment that intentionally emits and/or receives radio waves for communication or radio determination. Includes WiFi, Bluetooth, cellular, NFC, Zigbee, LoRa, and similar.",
        "applicability": [
            {"condition": "wireless", "operator": "equals", "value": True},
        ],
        "key_requirements": [
            "CE marking mandatory",
            "EU Declaration of Conformity required",
            "Notified Body involvement may be required (if no harmonised standards used)",
            "Radio spectrum and interference requirements",
            "Safety (LVD requirements incorporated)",
            "EMC requirements incorporated",
            "Technical documentation for 10 years",
        ],
        "referenced_standards": [
            "EN 300 328 (2.4 GHz wideband – WiFi, BLE)",
            "EN 301 489-1 (EMC for radio equipment – general)",
            "EN 301 489-17 (EMC for broadband data transmission)",
            "EN 62368-1 (Safety)",
        ],
        "penalties": "Product withdrawal, fines, criminal liability for spectrum violations.",
    },
    {
        "celex_id": "32006L0042",
        "id": "2006/42/EC",
        "short_name": "Machinery",
        "full_name": "Machinery Directive",
        "market": "EU",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32006L0042",
        "scope": "Machinery: assembly of linked parts with at least one moving part, with a drive system, for a specific application. Excludes household appliances, audio/video, low-voltage IT, and ordinary office equipment.",
        "applicability": [
            {"condition": "product_type", "operator": "in", "values": [
                "machinery", "power_tool", "industrial_equipment",
            ]},
        ],
        "key_requirements": [
            "CE marking mandatory",
            "Essential health and safety requirements (EHSR) – Annex I",
            "Risk assessment mandatory",
            "Technical file with design drawings, risk assessment, test reports",
            "Instructions for use in language of destination country",
            "EU Declaration of Conformity",
        ],
        "referenced_standards": [
            "EN ISO 12100 (Safety of machinery – general principles)",
            "EN 60204-1 (Electrical equipment of machines)",
            "EN ISO 13849-1 (Safety-related parts of control systems)",
        ],
        "penalties": "Product withdrawal, fines, criminal prosecution for accidents.",
    },
    {
        "celex_id": "32001L0095",
        "id": "2001/95/EC",
        "short_name": "GPSD",
        "full_name": "General Product Safety Directive",
        "market": "EU",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32001L0095",
        "scope": "All consumer products not covered by specific sector legislation. Acts as a safety net – if no specific directive applies, GPSD still requires products to be safe.",
        "applicability": [
            {"condition": "intended_use", "operator": "equals", "value": "consumer"},
        ],
        "key_requirements": [
            "Products must be safe under normal or reasonably foreseeable conditions of use",
            "Producers must inform consumers of risks",
            "Traceability: product identification and producer details on product/packaging",
            "Obligation to monitor safety after placing on market",
            "Notify authorities of known risks",
        ],
        "referenced_standards": [],
        "penalties": "Product recall, sales ban, fines set by member states.",
    },
    {
        "celex_id": "32009L0048",
        "id": "2009/48/EC",
        "short_name": "Toy Safety",
        "full_name": "Toy Safety Directive",
        "market": "EU",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32009L0048",
        "scope": "Products designed or intended for use in play by children under 14 years of age. Also applies to products that could be mistaken for toys.",
        "applicability": [
            {"condition": "intended_age_group", "operator": "equals", "value": "children"},
            {"condition": "product_type", "operator": "in", "values": ["toy"]},
            {"condition": "logic", "value": "OR"},
        ],
        "key_requirements": [
            "CE marking mandatory",
            "Physical and mechanical testing (EN 71-1)",
            "Flammability testing (EN 71-2)",
            "Chemical migration testing (EN 71-3)",
            "Electrical safety for electronic toys (EN 62115)",
            "Warnings and age grading",
            "EU Declaration of Conformity",
            "Notified Body assessment for chemical and electrical safety",
        ],
        "referenced_standards": [
            "EN 71-1 (Mechanical and physical properties)",
            "EN 71-2 (Flammability)",
            "EN 71-3 (Migration of certain elements)",
            "EN 62115 (Safety of electric toys)",
        ],
        "penalties": "Product withdrawal, fines, criminal prosecution. Strict enforcement due to child safety.",
    },
    {
        "celex_id": "32004R1935",
        "id": "EC 1935/2004",
        "short_name": "Food Contact",
        "full_name": "Food Contact Materials Regulation",
        "market": "EU",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32004R1935",
        "scope": "Materials and articles intended to come into contact with food, or which can reasonably be expected to come into contact with food under normal or foreseeable conditions of use.",
        "applicability": [
            {"condition": "food_contact", "operator": "in", "values": ["direct", "indirect"]},
        ],
        "key_requirements": [
            "Materials must not transfer constituents to food in quantities that could endanger health",
            "Must not cause unacceptable change in food composition, taste, or odour",
            "Declaration of Compliance from material suppliers",
            "Migration testing (overall migration + specific migration limits)",
            "Traceability: materials must be traceable one step back and one step forward",
            "Good Manufacturing Practice (EC 2023/2006)",
        ],
        "referenced_standards": [
            "EN 1186 series (Overall migration testing)",
            "EN 13130 series (Specific migration testing)",
            "EU 10/2011 (Plastic materials – positive list and limits)",
        ],
        "penalties": "Product withdrawal, fines, destruction of non-compliant goods.",
    },
    {
        "celex_id": "31994L0062",
        "id": "94/62/EC",
        "short_name": "Packaging",
        "full_name": "Packaging and Packaging Waste Directive",
        "market": "EU",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:31994L0062",
        "scope": "All packaging placed on the EU market and all packaging waste. Applies to producers who package products for sale.",
        "applicability": [
            {"condition": "intended_use", "operator": "in", "values": ["consumer", "industrial"]},
        ],
        "key_requirements": [
            "Minimise packaging weight and volume",
            "Heavy metal limits (lead, cadmium, mercury, chromium VI): <100 ppm combined",
            "Register with national packaging compliance schemes (e.g., Der Grune Punkt in Germany)",
            "Report packaging quantities annually",
            "Material identification marking recommended",
        ],
        "referenced_standards": [
            "EN 13427 (Requirements for the use of EN standards for packaging)",
            "EN 13428 (Prevention by source reduction)",
        ],
        "penalties": "Fines for non-registration. Germany: up to €200,000. France: up to €100,000.",
    },
    {
        "celex_id": "32023R1542",
        "id": "2023/1542",
        "short_name": "Battery Regulation",
        "full_name": "EU Battery Regulation",
        "market": "EU",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023R1542",
        "scope": "All batteries placed on the EU market: portable, industrial, EV, LMT, and SLI batteries. Replaces the old Battery Directive 2006/66/EC.",
        "applicability": [
            {"condition": "battery", "operator": "equals", "value": True},
        ],
        "key_requirements": [
            "Carbon footprint declaration (phased in from 2025)",
            "Recycled content requirements (phased in from 2028)",
            "Battery passport (digital – for EV and industrial batteries >2kWh, from 2027)",
            "Due diligence for raw material sourcing (cobalt, lithium, nickel, natural graphite)",
            "Collection and recycling targets",
            "Labelling: capacity, durability, chemistry, separate collection symbol",
            "Removability: portable batteries must be removable by end-user (from 2027)",
            "CE marking mandatory",
        ],
        "referenced_standards": [
            "EN 62133-2 (Safety of lithium batteries)",
            "IEC 62368-1 (for products containing batteries)",
            "UN 38.3 (Transport testing for lithium batteries)",
        ],
        "penalties": "Fines set by member states. Expected to be significant given ESG focus.",
    },
]


def scrape_directive_summary(celex_id: str) -> str | None:
    """Fetch the first paragraph of a directive from EUR-Lex as a summary."""
    url = BASE_URL.format(celex_id=celex_id)
    try:
        resp = requests.get(url, timeout=30, headers={"Accept-Language": "en"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # Try to find the first substantive paragraph
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if len(text) > 100:
                return text[:500]
        return None
    except Exception as e:
        print(f"  Warning: Could not fetch {celex_id}: {e}", file=sys.stderr)
        return None


def build_directives_json(fetch_summaries: bool = False) -> list[dict]:
    """Build the directives dataset, optionally enriching with scraped summaries."""
    directives = []
    for d in DIRECTIVES:
        entry = {
            "id": d["id"],
            "short_name": d["short_name"],
            "full_name": d["full_name"],
            "scope": d["scope"],
            "market": d["market"],
            "url": d["url"],
            "applicability": d["applicability"],
            "key_requirements": d["key_requirements"],
            "referenced_standards": d["referenced_standards"],
            "penalties": d.get("penalties", ""),
        }
        if fetch_summaries:
            print(f"Fetching summary for {d['short_name']} ({d['celex_id']})...")
            summary = scrape_directive_summary(d["celex_id"])
            if summary:
                entry["scraped_summary"] = summary
            time.sleep(1)  # Be polite to EUR-Lex
        directives.append(entry)
    return directives


def main():
    output_path = Path(__file__).parent.parent / "data" / "eu-directives" / "directives.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("Building EU directives dataset...")
    fetch = "--fetch" in sys.argv
    if fetch:
        print("(Fetching summaries from EUR-Lex – this takes ~15 seconds)")
    directives = build_directives_json(fetch_summaries=fetch)

    with open(output_path, "w") as f:
        json.dump(directives, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(directives)} directives to {output_path}")


if __name__ == "__main__":
    main()
