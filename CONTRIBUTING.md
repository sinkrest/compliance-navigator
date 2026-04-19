# Contributing to Compliance Navigator

Thanks for wanting to improve compliance guidance for hardware builders.

## Adding a New EU Directive

1. Add the directive to `scrapers/scrape_eurlex.py` in the `DIRECTIVES` list
2. Include: `id`, `short_name`, `full_name`, `scope`, `applicability` criteria, `key_requirements`, `referenced_standards`
3. Run `python scrapers/scrape_eurlex.py` to regenerate `data/eu-directives/directives.json`
4. Add checklist templates in `src/compliance_nav/navigator.py` under `checklist_templates`
5. Add tests in `tests/test_navigator.py`

## Adding a Product Category

1. Add the category to `data/standard-map.yaml` under `categories`
2. Include: `description`, `eu_directives`, `en_standards`, `us_regulations`, `common_pitfalls`, `typical_test_costs`
3. Update the category list in `README.md`

## Improving Recall Categorisation

The keyword-based categorisation in `scrapers/scrape_cpsc.py` is simple. To improve:

1. Add keywords to `CATEGORY_KEYWORDS` in `scrape_cpsc.py`
2. Re-run the scraper: `python scrapers/scrape_cpsc.py`
3. Check the category distribution in the output

## Adding a New Data Source

Good candidates:
- **EU RAPEX/Safety Gate** -- EU recall database
- **FDA MAUDE** -- Medical device adverse events
- **UK OPSS** -- UK product safety
- **Health Canada recalls**

Steps:
1. Create a new scraper in `scrapers/`
2. Add data output to `data/`
3. Integrate into the navigator logic in `src/compliance_nav/navigator.py`

## Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Code Style

- Python 3.10+
- Type hints on function signatures
- Docstrings on public functions
- No external dependencies beyond what's in `pyproject.toml`
