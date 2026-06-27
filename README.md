# ForexFactory Calendar Scraper

Fetch ForexFactory economic calendar data into a long-lived CSV cache, keep the cache idempotent, and validate the result without duplicating rows.

The project does not bypass Cloudflare, CAPTCHA, or other security verification. It uses public calendar HTML, saved HTML files, and weekly export files when available.

## Quick Start

Run the historical cache update with the default HTML provider:

```bash
python -m src.forexfactory.main \
  --start 2025-04-07 \
  --end 2026-04-06 \
  --csv forex_factory_cache.csv \
  --tz Asia/Tehran \
  --details \
  --debug
```

Validate the cache:

```bash
python scripts/validate_cache.py \
  --csv forex_factory_cache.csv \
  --start 2025-04-07 \
  --end 2026-04-06
```

## What This Project Does

- Fetches ForexFactory calendar rows and stores them in a CSV cache.
- Preserves historical rows outside the requested range.
- Merges repeated runs without creating duplicates.
- Supports legacy cache rows and the newer normalized provider schema.
- Validates duplicates and missing fields using canonicalized datetime, currency, and event values.

## Recommended Workflow

1. Create and activate a virtual environment.
2. Run the update command.
3. Run the validation command.

The cache is treated as a long-lived historical store. `--start` and `--end` control the fetch/update range only. They do not delete older rows.

## Updating the Cache

Default provider:

- `forexfactory-html`: online HTML fetcher, preferred for historical ranges.

Useful options:

- `--start`, `--end`: inclusive date range in `YYYY-MM-DD`.
- `--csv`: output cache path. Default: `forex_factory_cache.csv`.
- `--tz`: timezone used when canonicalizing times. Default: `Asia/Tehran`.
- `--details`: accepted for compatibility.
- `--impact`: filter by impact values such as `high,medium`.
- `--keep-currencies`: keep only selected currencies such as `USD EUR GBP`.
- `--provider`: choose `forexfactory-html`, `saved-html`, or `forexfactory-export`.
- `--input`: saved HTML file for `saved-html`.
- `--export-format`: `json`, `csv`, `xml`, or `ics` for `forexfactory-export`.
- `--debug`: write debug artifacts when HTML parsing detects blocked or malformed pages.

Example:

```bash
python -m src.forexfactory.main \
  --start 2025-04-07 \
  --end 2026-04-06 \
  --csv forex_factory_cache.csv \
  --tz Asia/Tehran \
  --details
```

## Validating the Cache

`scripts/validate_cache.py` canonicalizes legacy rows and normalized rows before checking duplicates, missing fields, and range coverage.

Example:

```bash
python scripts/validate_cache.py \
  --csv forex_factory_cache.csv \
  --start 2025-04-07 \
  --end 2026-04-06
```

What the report means:

- `total rows`: rows in the cache after canonicalization.
- `valid datetime rows`: rows with a canonical `datetime_local`.
- `range rows`: rows that fall inside the requested validation range.
- `range duplicate groups`: canonical duplicate keys in the requested range.
- `range duplicated rows including first`: duplicate rows counted across those groups.
- `source counts`: how many rows were written by each provider.
- `rows with missing source`: rows that do not have a `source` value, usually legacy rows.
- `legacy rows inside requested range`: rows that still use the legacy schema.
- `rows with missing key fields`: rows missing canonical datetime, currency, or event.

In the currently validated cache snapshot for `2025-04-07` to `2026-04-06`, the report showed:

```text
range rows: 4811
range duplicate groups: 0
range duplicated rows including first: 0
rows with missing key fields: 0
source forexfactory-html: 4802
source missing/legacy: 9
```

Small numbers of missing-source rows can be legacy cache rows and are not automatically errors if they do not duplicate canonical events.

## Understanding the Cache

- The cache is historical and cumulative.
- Re-running the same provider and date range should be idempotent.
- Duplicate detection uses canonicalized fields, not raw column names.
- Validation normalizes both legacy and new schema rows before it checks anything.
- A small number of missing-source rows can exist in older cache entries.

## Providers

### `forexfactory-html`

Default provider and preferred online method.

It fetches ForexFactory calendar HTML directly and parses the calendar rows without Selenium.

### `saved-html`

Offline fallback for a local HTML file that you saved manually from a valid ForexFactory calendar page.

Example:

```bash
python -m src.forexfactory.main \
  --provider saved-html \
  --input saved_forexfactory_calendar.html \
  --csv forex_factory_cache.csv \
  --tz Asia/Tehran \
  --debug
```

### `forexfactory-export`

Optional export-file provider. It discovers weekly export links when available and fetches `json`, `csv`, `xml`, or `ics` files.

Important:

- It is not a public API.
- It is limited to whatever export files ForexFactory exposes.
- Historical coverage is not guaranteed.
- In this workspace, discovered export files were `ff_calendar_thisweek.*` and contained current-week data only.

Example:

```bash
python -m src.forexfactory.main \
  --provider forexfactory-export \
  --start 2025-04-07 \
  --end 2025-04-14 \
  --csv forex_factory_cache_test.csv \
  --tz Asia/Tehran \
  --export-format json \
  --debug
```

## Troubleshooting

### Direct HTML returns a security verification page

ForexFactory may return a page that says `Performing security verification` or similar text instead of the calendar. That means the request reached a verification page, not the calendar DOM.

The scraper will report that clearly. It does not bypass the verification page.

### Parser cannot find calendar rows

If the HTML is real calendar HTML but the parser cannot find rows, ForexFactory likely changed the DOM. Inspect the saved debug HTML and update selectors in the HTML provider.

### Empty CSV output

Check the logs and debug artifacts. The requested range may contain no events, the page may have been blocked, or the parser may need a selector update.

### Duplicate validation reports rows

Validate with the canonical duplicate key (`datetime_local + currency + event`) and inspect the duplicate samples in the report.

### Missing source rows

These are often legacy cache rows. They are only a problem if they are also duplicate canonical events or are missing key fields.

### Export historical limitation

If export files only expose the current week, use `forexfactory-html` for historical ranges.

### Network or timeout failures

Retry later or use `--debug` to inspect the fetched HTML and determine whether the response was blocked or malformed.

## Development

Run the basic checks:

```bash
python -m compileall src scripts
python -m src.forexfactory.main --help
python -m pytest -q
python scripts/validate_cache.py \
  --csv forex_factory_cache.csv \
  --start 2025-04-07 \
  --end 2026-04-06
```

Git hygiene:

- Do not commit `forex_factory_cache.csv` or other generated cache files.
- Do not commit `debug/` artifacts.
- Do not commit local virtual environments or `__pycache__/` directories.

