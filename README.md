# Forex Factory Economic Calendar Scraper (Python)

[![Tests](https://github.com/ehsanrs2/forexfactory-scraper/actions/workflows/tests.yml/badge.svg)](https://github.com/ehsanrs2/forexfactory-scraper/actions/workflows/tests.yml)
[![GitHub stars](https://img.shields.io/github/stars/ehsanrs2/forexfactory-scraper?style=flat)](https://github.com/ehsanrs2/forexfactory-scraper/stargazers)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)
[![Hugging Face Dataset](https://img.shields.io/badge/%F0%9F%A4%97-Dataset-yellow)](https://huggingface.co/datasets/Ehsanrs2/Forex_Factory_Calendar)

![Forex Factory Scraper — historical economic calendar data](assets/forex-factory-social-preview.webp)

A **Python Forex Factory economic calendar scraper** for collecting, normalizing, and validating economic events in a persistent CSV cache. Use the resulting data in financial research, historical event analysis, backtesting workflows, or machine-learning feature engineering.

Unlike a one-off export, the scraper supports **incremental updates**, **preservation of previously collected rows**, **duplicate-aware merges**, timezone-aware timestamps, and offline validation.

> **Availability:** Forex Factory may serve security-verification pages or change its HTML. This project does not bypass Cloudflare, CAPTCHA, or other access controls. Historical coverage depends on the source being available. It is an independent community project, not an official Forex Factory API.

## Features

- **Economic calendar extraction:** currency, event, impact, actual, forecast, previous, and available detail fields.
- **Incremental historical CSV cache:** update a requested range while retaining older cached events.
- **Repeatable merging:** canonical event keys help avoid duplicate records across repeated runs.
- **Timezone-aware data:** normalized local and UTC datetime fields.
- **Filters:** choose impact levels and currencies.
- **Multiple input methods:** public calendar HTML, a locally saved HTML page, or available weekly export files.
- **Cache validation:** inspect missing keys, duplicate groups, dates, and data sources.

## Quick Start

Requires Python and a network connection for the default HTML provider. Run these commands from the repository root:

```bash
git clone https://github.com/ehsanrs2/forexfactory-scraper.git
cd forexfactory-scraper
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, activate the environment with `.venv\Scripts\activate` instead.

**1. Collect a sample historical range:**

```bash
python -m src.forexfactory.main \
  --start 2025-04-07 \
  --end 2025-04-14 \
  --csv forex_factory_cache.csv \
  --tz UTC
```

**2. Validate the result:**

```bash
python scripts/validate_cache.py \
  --csv forex_factory_cache.csv \
  --start 2025-04-07 \
  --end 2025-04-14 \
  --tz UTC
```

**3. Inspect the CSV:** The default output is `forex_factory_cache.csv`. The normalized schema contains fields such as:

| Column | Meaning |
| --- | --- |
| `datetime_local`, `datetime_utc` | Event timestamps with timezone information |
| `currency` | Affected currency, such as USD or EUR |
| `impact`, `event` | Event impact classification and name |
| `actual`, `forecast`, `previous` | Indicator values, when reported |
| `source`, `source_url`, `detail_url` | Available source and detail metadata |

The CSV also retains legacy columns (`DateTime`, `Currency`, `Impact`, `Event`, `Actual`, `Forecast`, `Previous`, `Detail`) for compatibility. Some values may be missing in the source.

**Example CSV:** [View five real historical events in the current normalized CSV schema](examples/sample_events.csv). This small example was derived from the repository's existing [`high_impact_events_calendar.csv`](high_impact_events_calendar.csv) (January 2020) using the current normalization field conventions in UTC. **It is not the result of a new live scrape.** Original event values are preserved; `source`, `source_url`, and `detail_url` are empty because that legacy file did not record them.

If the source responds with a verification page instead of calendar HTML, consult [Troubleshooting](#troubleshooting); successful live scraping is not guaranteed.

## Historical Dataset on Hugging Face

**[Forex Factory Economic Calendar Dataset — Hugging Face](https://huggingface.co/datasets/Ehsanrs2/Forex_Factory_Calendar)**

A companion **published historical dataset** covers **2007-01-01 through 2025-04-07**, as described in its dataset card. It provides a downloadable CSV snapshot for research and analysis.

The published dataset and this repository's **local incremental cache are separate artifacts**: running the scraper does not automatically update the Hugging Face dataset. The dataset card describes its original collection process; the current scraper supports a different HTML-first workflow.

Use the dataset for exploring historical economic events, or use this repository to build and validate a new local cache. Check the dataset card for provenance, usage limitations, and the original source's terms.

## CLI Reference

```bash
python -m src.forexfactory.main --help
```

| Option | Description |
| --- | --- |
| `--start`, `--end` | Inclusive date range in `YYYY-MM-DD` (required for online providers) |
| `--csv` | Cache output path; default `forex_factory_cache.csv` |
| `--tz` | Output timezone; default `Asia/Tehran` |
| `--impact` | Comma-separated levels, for example `high,medium` |
| `--keep-currencies` | Space-separated currencies, for example `USD EUR GBP` |
| `--provider` | `forexfactory-html`, `saved-html`, or `forexfactory-export` |
| `--input` | Local HTML path for `saved-html` |
| `--export-format` | `json`, `csv`, `xml`, or `ics` with export provider |
| `--details` | Compatibility option |
| `--debug` | Enable diagnostic logging and related debugging artifacts |

### Filter by impact and currency

```bash
python -m src.forexfactory.main \
  --start 2025-04-07 --end 2025-04-14 \
  --impact high,medium --keep-currencies USD EUR GBP \
  --csv forex_factory_cache.csv --tz UTC
```

### Use locally saved HTML

Useful when a legitimate calendar HTML page has already been saved:

```bash
python -m src.forexfactory.main \
  --provider saved-html \
  --input saved_forexfactory_calendar.html \
  --csv forex_factory_cache.csv \
  --tz UTC
```

The saved-HTML provider does not require `--start` and `--end` when processing the saved file.

### Use available Forex Factory export files

```bash
python -m src.forexfactory.main \
  --provider forexfactory-export \
  --start 2025-04-07 --end 2025-04-14 \
  --export-format json \
  --csv forex_factory_cache.csv
```

This provider uses exports **when Forex Factory exposes them**. It is not an official public API; recent-only or incomplete coverage is possible.

## Incremental Cache and Validation

- `--start` and `--end` control the requested **fetch/update range**, not deletion of earlier cached rows.
- Repeated runs merge using canonicalized event date/time, currency, and event identity; a previous event can receive newly available detail text.
- Legacy and normalized records can coexist in the input cache; validation normalizes them before duplicate checks.
- A source's availability and data quality still affect completeness. Review the validator's report before using the cache for research.

### Previously reported validation snapshot

An earlier validation documented the range **2025-04-07 to 2026-04-06** with **4,811 rows in range**, **0 duplicate groups**, and **0 rows missing key fields**. This is a **historical report from the repository's prior documentation**, not a fresh test or a guarantee of current source availability.

To generate a new report, run:

```bash
python scripts/validate_cache.py \
  --csv forex_factory_cache.csv \
  --start 2025-04-07 --end 2025-04-14
```

The report includes counts of canonical timestamps, in-range rows, duplicate groups, missing keys, provider sources, and legacy rows.

## Troubleshooting

**Security verification / blocked page:** The scraper reports this condition instead of bypassing it. Use an already saved, legitimately accessible HTML page or try again when the source permits access.

**No calendar rows found:** Confirm that the requested range has events and that the source HTML is valid. Page structure changes may require parser maintenance.

**Empty CSV:** A source response may be blocked, empty, or incompatible with the current selectors. Run with `--debug` to inspect diagnostics.

**Duplicate validation:** The validator checks normalized date/time, currency, and event keys; use its duplicate samples to investigate.

**Export coverage limitations:** Weekly export files may only expose recent data and may be unavailable for historical ranges.

**Network errors:** A live provider needs access to the source. The `saved-html` provider supports offline parsing of a file you already have.

## More Documentation

- [FAQ: historical Forex Factory data, Python usage, backtesting, and troubleshooting](docs/faq.md)
- [Companion dataset on Hugging Face](https://huggingface.co/datasets/Ehsanrs2/Forex_Factory_Calendar)

## Development and Contributing

Install development requirements and run the offline tests:

```bash
python -m pip install -r requirements-dev.txt
python -m compileall -q src scripts
python -m pytest -q
```

The live integration test is opt-in via `RUN_LIVE_SCRAPE=1` and is intentionally not enabled in CI.

Issues and pull requests are welcome for parser compatibility, tests, documentation, and reproducible examples. Please include the Python version, relevant command, sanitized error output, and a minimal reproduction when reporting problems.

Do not commit generated caches, `debug/` outputs, local virtual environments, or sensitive data.

## License and Data Source

- **Scraper code:** [GNU GPL-3.0](LICENSE).
- **Economic-calendar data:** sourced from [Forex Factory](https://www.forexfactory.com/calendar); review the [original source's notices and terms](https://www.forexfactory.com/notices) before using or redistributing extracted content.
- **Published companion dataset:** [Hugging Face dataset card](https://huggingface.co/datasets/Ehsanrs2/Forex_Factory_Calendar). Its metadata and permissions should be evaluated separately from the scraper code license.

This project is not affiliated with, endorsed by, or sponsored by Forex Factory.
