# Compliance Navigator

**Open-source regulatory guidance for hardware builders.**

Compliance is the wall where solo hardware builders quit. This tool tears it down.

Describe your product. Get back the regulations that apply, a compliance checklist with cost estimates, and real recall data from similar products -- so you know what's gone wrong before.

```
compliance-nav check --file examples/heated-mug.yaml
```

## Quick Start

```bash
# Clone
git clone https://github.com/forkable-factory/compliance-navigator.git
cd compliance-navigator

# Install
pip install -e .

# Run against the example (USB heated mug)
compliance-nav check --file examples/heated-mug.yaml

# Quick check by product type
compliance-nav check --product-type wireless_device --market EU

# JSON output (for piping / automation)
compliance-nav check --file your-product.yaml --format json

# Markdown output (for docs)
compliance-nav check --file your-product.yaml --format markdown
```

## How It Works

1. You describe your product in a YAML file (type, market, voltage, materials, etc.)
2. The navigator matches your product against **12 EU directives** using structured applicability rules
3. It cross-references **9,700+ CPSC product recalls** to find failures in similar products
4. It returns: applicable directives, referenced standards, a compliance checklist, cost estimates, and risk notes

No API keys. No LLM calls. Runs offline from committed data.

## Product Definition Format

```yaml
name: My Product
type:
  - consumer_electronics
  - usb_powered_device
market:
  - EU
  - US
voltage_dc: 5           # Optional: DC voltage
voltage_ac: null         # Optional: AC voltage
power_watts: 10          # Optional
wireless: false          # Does it have WiFi/BLE/cellular?
battery: false           # Does it contain a battery?
materials:               # What's it made of?
  - abs_plastic
  - copper
  - stainless_steel
food_contact: null       # "direct", "indirect", or null
intended_use: consumer   # "consumer", "industrial", "medical"
intended_age_group: null # "children", "adults", or null
description: Short description of the product.
```

## Supported Product Categories

| Category | Example Products |
|---|---|
| `consumer_electronics` | Gadgets, accessories, monitors |
| `usb_powered_device` | USB hubs, chargers, USB-powered gadgets |
| `battery_powered_device` | Portable speakers, e-bikes, power tools |
| `iot_device` | Smart home devices, connected sensors |
| `wireless_device` | WiFi/BLE/LoRa/cellular products |
| `kitchen_appliance` | Toasters, blenders, coffee makers |
| `heating_device` | Space heaters, mug warmers, heated garments |
| `food_contact_product` | Utensils, containers, food packaging |
| `lighting` | LED lamps, fixtures, string lights |
| `power_supply` | AC/DC adapters, chargers |
| `wearable` | Smartwatches, fitness trackers |
| `toy` | Electronic toys, building sets |
| `medical_device_class_I` | Low-risk medical devices |
| `furniture` | Chairs, tables, shelving |
| `textile` | Clothing, soft furnishings |
| `packaging` | Product packaging |

## Data Sources

| Source | Records | Licence | Last Updated |
|---|---|---|---|
| **EU Directives** (EUR-Lex) | 12 directives | Public domain (EU law) | Apr 2026 |
| **CPSC Recalls** (SaferProducts.gov) | 9,700+ recalls | US Government -- Public Domain | Apr 2026 |
| **Standard Map** (curated) | 16 product categories | MIT | Apr 2026 |

All regulatory text is sourced from official government publications. No copyrighted material is included.

## CLI Commands

```bash
# Check compliance for a product
compliance-nav check --file product.yaml
compliance-nav check --product-type heating_device --market EU
compliance-nav check --file product.yaml --format json

# Browse the database
compliance-nav list-directives        # All EU directives
compliance-nav list-categories        # Supported product types
compliance-nav recalls --category heating_device --limit 10
```

## Limitations

This tool is **not legal advice**. It is a starting point.

- Covers EU and US regulations only (v1)
- Does not replace a compliance consultant or Notified Body
- Standard applicability is based on product type heuristics, not legal analysis
- Recall data is from CPSC (US) only -- EU RAPEX data is a future addition
- Directive applicability rules are simplified -- edge cases exist
- Always verify with a qualified professional before placing a product on the market

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to:
- Add new EU directives or update existing ones
- Add product categories to the standard map
- Improve recall categorisation
- Add data sources (EU RAPEX, FDA, etc.)

## Licence

Code: [MIT](LICENSE)
Data: Public domain (sourced from government publications)

## Part of Forkable Factory

This tool is part of the [Forkable Factory](https://github.com/forkable-factory) project -- an experiment in developing physical products the way software is developed: in repos, with agents, open by default.

Read the thesis: [The Forkable Factory](https://romanmartins.com/blog/the-forkable-factory)
