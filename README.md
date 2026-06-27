# Forex Factory Scraper

A pandas-based scraper for Forex Factory calendar events. It prefers non-Selenium collection methods and keeps Selenium as a best-effort fallback for cases where direct export or HTML parsing is not enough.

ForexFactory does not provide a public developer API. This project uses public calendar pages, weekly export files when discoverable, saved HTML files, or Selenium fallback. It does not bypass CAPTCHA, Cloudflare, or other security verification.

## Dataset

The main scraped CSV dataset is hosted on [Hugging Face](https://huggingface.co/datasets/Ehsanrs2/Forex_Factory_Calendar). The local `forex_factory_cache.csv` file is treated as generated/downloaded data and is intentionally ignored by git.

If you place `forex_factory_cache.csv` in the project root, the test suite validates its basic schema without requiring a live scrape.
The cache is treated as a long-lived historical store. It may contain legacy rows and rows written by the newer normalized providers, and `--start` / `--end` only control the fetch or update range. They do not delete rows outside that range.

## Installation

### Python

Use Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

For development and tests:

```bash
pip install -r requirements-dev.txt
```

### ChromeDriver Setup

ChromeDriver is not downloaded at runtime. Install Chrome/Chromium and a matching local ChromeDriver, then either put `chromedriver` on `PATH` or pass explicit paths with `--chrome-binary` and `--chromedriver`.

Confirmed Chrome for Testing paths:

```bash
/usr/local/bin/chrome-linux64/chrome
/usr/local/bin/chromedriver-linux64/chromedriver
/usr/local/bin/chrome-headless-shell-linux64/chrome-headless-shell
```

Ensure the binaries are executable:

```bash
sudo chmod +x /usr/local/bin/chrome-linux64/chrome
sudo chmod +x /usr/local/bin/chromedriver-linux64/chromedriver
sudo chmod +x /usr/local/bin/chrome-headless-shell-linux64/chrome-headless-shell
```

Check versions:

```bash
/usr/local/bin/chrome-linux64/chrome --version
/usr/local/bin/chromedriver-linux64/chromedriver --version
/usr/local/bin/chrome-headless-shell-linux64/chrome-headless-shell --version
```

Chrome and ChromeDriver major versions must match.

Optional symlink setup:

```bash
sudo ln -sf /usr/local/bin/chrome-linux64/chrome /usr/local/bin/chrome
sudo ln -sf /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver
```

## Usage

Date range options:

- `--start`: Start date in `YYYY-MM-DD` format. Required for live providers.
- `--end`: End date in `YYYY-MM-DD` format. Required for live providers.
- `saved-html` may omit `--start` and `--end`; in that case all parsed rows from the saved file are written.

Common options:

- `--provider`: Data provider: `forexfactory-export`, `forexfactory-html`, `saved-html`, or `forexfactory-selenium`. Default: `forexfactory-selenium` for backward compatibility.
- `--export-format`: Export format for `forexfactory-export`: `json`, `csv`, `xml`, or `ics`. Default: `json`.
- `--input`: Saved HTML file path for `saved-html`.
- `--csv`: Output CSV path. Default: `forex_factory_cache.csv`.
- `--tz`: Timezone for event datetimes. Default: `Asia/Tehran`.
- `--details`: Scrape detail rows when available.
- `--impact`: Comma-separated impact filter, such as `high,medium`.
- `--keep-currencies`: Space-separated currency filter, such as `USD EUR GBP`.
- `--driver`: Selenium browser backend, `selenium` or `uc`. Default: `selenium`.
- `--chrome-binary`: Explicit Chrome/Chromium binary path.
- `--chromedriver`: Explicit local ChromeDriver path.
- `--headless` / `--no-headless`: Run Chrome headless or visible.
- `--user-agent`: Custom browser user-agent string.
- `--user-data-dir`: Persistent Chrome profile directory.
- `--page-timeout`: Page load timeout in seconds. Default: `120`.
- `--retries`: Retries per day after retryable page load/browser failures. Default: `2`.
- `--manual-verification-timeout`: Seconds to wait for manual security verification. Default: `0`.
- `--debug`: Enable debug logging and debug artifact dumps for blocked or malformed pages.

Environment variables:

- `FOREXFACTORY_DRIVER`
- `FOREXFACTORY_CHROME_BINARY`
- `FOREXFACTORY_CHROMEDRIVER`
- `FOREXFACTORY_HEADLESS`
- `FOREXFACTORY_USER_AGENT`
- `FOREXFACTORY_USER_DATA_DIR`
- `FOREXFACTORY_PAGE_TIMEOUT`

## Providers

Preferred order:

1. `forexfactory-export`: discovers weekly export links from ForexFactory pages and fetches `json`, `csv`, `xml`, or `ics` files from `nfs.faireconomy.media` when available. These are export files, not a public API.
2. `forexfactory-html`: fetches ForexFactory calendar HTML directly and parses calendar rows without Selenium.
3. `saved-html`: parses a local HTML file that you manually saved from a valid ForexFactory calendar page.
4. `forexfactory-selenium`: best-effort browser fallback with local ChromeDriver and manual verification support.

Export coverage must be verified. In this environment, the page exposed `ff_calendar_thisweek.{json,csv,xml,ics}` links. Those files contained current-week data only, even when discovered from a historical week page. For historical ranges, use `forexfactory-html` or `saved-html`.

Third-party economic-calendar APIs are not guaranteed to match ForexFactory exactly and are not used by this project.

`forexfactory-html` is currently the preferred method for historical ForexFactory data because it avoids Selenium and successfully fetched the tested historical range.

## Example Commands

Export provider, JSON format:

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

Direct HTML provider for historical data:

```bash
python -m src.forexfactory.main \
  --provider forexfactory-html \
  --start 2025-04-07 \
  --end 2026-04-06 \
  --csv forex_factory_cache_test.csv \
  --tz Asia/Tehran \
  --details \
  --debug
```

Saved HTML provider:

```bash
python -m src.forexfactory.main \
  --provider saved-html \
  --input saved_forexfactory_calendar.html \
  --csv forex_factory_cache.csv \
  --tz Asia/Tehran \
  --debug
```

Selenium fallback short validation command:

```bash
python -m src.forexfactory.main \
  --provider forexfactory-selenium \
  --start 2025-04-07 \
  --end 2025-04-14 \
  --csv forex_factory_cache_test.csv \
  --tz Asia/Tehran \
  --details \
  --debug \
  --headless \
  --driver selenium \
  --chrome-binary /usr/local/bin/chrome-linux64/chrome \
  --chromedriver /usr/local/bin/chromedriver-linux64/chromedriver
```

Selenium fallback full production-range command:

```bash
python -m src.forexfactory.main \
  --provider forexfactory-selenium \
  --start 2025-04-07 \
  --end 2026-04-06 \
  --csv forex_factory_cache.csv \
  --tz Asia/Tehran \
  --details \
  --debug \
  --headless \
  --driver selenium \
  --chrome-binary /usr/local/bin/chrome-linux64/chrome \
  --chromedriver /usr/local/bin/chromedriver-linux64/chromedriver
```

Simplified command after symlink setup:

```bash
python -m src.forexfactory.main \
  --provider forexfactory-selenium \
  --start 2025-04-07 \
  --end 2026-04-06 \
  --csv forex_factory_cache.csv \
  --tz Asia/Tehran \
  --details \
  --debug \
  --headless \
  --driver selenium
```

Optional `undetected_chromedriver` backend with a local ChromeDriver:

```bash
python -m src.forexfactory.main \
  --start 2025-04-07 \
  --end 2025-04-14 \
  --driver uc \
  --chromedriver /usr/local/bin/chromedriver-linux64/chromedriver \
  --headless
```

`--driver uc` is optional and is not the default. It still requires a local ChromeDriver path or `chromedriver` on `PATH`; runtime driver downloads are intentionally avoided.

## Cache Validation

Use the validation script to canonicalize the cache before checking duplicates or missing fields:

```bash
python scripts/validate_cache.py \
  --csv forex_factory_cache.csv \
  --start 2025-04-07 \
  --end 2026-04-06
```

The validator canonicalizes legacy and new provider rows before checking anything. It reports total rows, valid canonical datetimes, missing datetimes, min/max dates, duplicate groups in the requested range, duplicate samples, source counts, currency counts, impact counts, missing-source rows, legacy rows in range, and rows with missing key fields.

For the cache snapshot validated in this workspace, the result was:

```text
range rows: 4811
range duplicate groups: 0
range duplicated rows including first: 0
source forexfactory-html: 4802
source missing/legacy: 9
```

Small numbers of missing-source rows can be legacy cache rows and are not automatically errors if they do not duplicate canonical events. If your cache snapshot is older, you may see slightly different totals.

## ForexFactory Security Verification

If the page says `Performing security verification`, the request reached a verification page instead of the calendar. This is why selectors such as `table.calendar__table` or `tr.calendar__row` are missing. This is not a ChromeDriver issue.

The scraper does not bypass CAPTCHA, Cloudflare, or other security verification. It only detects the condition, keeps diagnostics clear, and supports manual verification with a persistent Chrome profile.

Manual verification workflow:

```bash
mkdir -p ~/.forexfactory-chrome-profile

python -m src.forexfactory.main \
  --start 2025-04-07 \
  --end 2025-04-14 \
  --csv forex_factory_cache_test.csv \
  --tz Asia/Tehran \
  --details \
  --debug \
  --no-headless \
  --driver selenium \
  --chrome-binary /usr/local/bin/chrome-linux64/chrome \
  --chromedriver /usr/local/bin/chromedriver-linux64/chromedriver \
  --user-data-dir ~/.forexfactory-chrome-profile \
  --manual-verification-timeout 180
```

Complete the verification manually in the opened browser. If the calendar appears before the timeout, scraping continues.

Retry later with the same profile:

```bash
python -m src.forexfactory.main \
  --start 2025-04-07 \
  --end 2026-04-06 \
  --csv forex_factory_cache.csv \
  --tz Asia/Tehran \
  --details \
  --debug \
  --no-headless \
  --driver selenium \
  --chrome-binary /usr/local/bin/chrome-linux64/chrome \
  --chromedriver /usr/local/bin/chromedriver-linux64/chromedriver \
  --user-data-dir ~/.forexfactory-chrome-profile
```

Headless mode may still be blocked depending on ForexFactory's security service. Use `--no-headless` first when establishing or refreshing the profile.

## Debug Artifacts

When `--debug` is enabled and the scraper detects a security verification page, malformed page, missing calendar selector, or blocked HTTP export/HTML response, it writes artifacts under `debug/`:

```text
debug/forexfactory_2025-04-07.html
debug/forexfactory_2025-04-07.png
debug/forexfactory_2025-04-07.txt
debug/http_calendar_2025-04-07.html
debug/http_calendar_2025-04-07.txt
```

The HTML file contains the page source. Selenium debug also includes a PNG screenshot. The TXT file includes the URL, status code when applicable, final URL, page title, content length, export-link discovery status, calendar-row discovery status, a short body preview, and the detected reason, such as `security_verification`, `export_links_not_found`, or `calendar_selector_missing`.

These artifacts help distinguish a security verification page from a real ForexFactory DOM selector change.

## Testing

Run the normal test suite:

```bash
python -m pytest -q
```

The normal suite does not run a live Selenium scrape. If `forex_factory_cache.csv` exists in the project root, the integration test validates the cached dataset schema.

To run the live scrape integration test:

```bash
RUN_LIVE_SCRAPE=1 python -m pytest -q tests/integration/test_full_scrape.py
```

## Troubleshooting

### `HTTP Error 403` from `undetected_chromedriver`

Older code paths allowed `undetected_chromedriver` to download and patch a driver at startup. This project now avoids implicit runtime driver downloads. Use `--driver selenium` with a local ChromeDriver, or use `--driver uc --chromedriver /path/to/chromedriver`.

### `chromedriver not found`

Install ChromeDriver and put it on `PATH`, create the optional symlink, or pass `--chromedriver /path/to/chromedriver`.

### `permission denied`

Make the Chrome and ChromeDriver binaries executable:

```bash
sudo chmod +x /usr/local/bin/chrome-linux64/chrome
sudo chmod +x /usr/local/bin/chromedriver-linux64/chromedriver
```

### `session not created`

Check that Chrome and ChromeDriver major versions match. Run both `--version` commands and update whichever binary is behind.

### Missing Linux runtime dependencies

Chrome for Testing may require system libraries such as NSS, X11, GTK, GBM, and ALSA packages. Install your distribution's standard Chromium/Chrome runtime dependencies if Chrome cannot launch.

### `Performing security verification`

ForexFactory served a verification page instead of the calendar. For non-Selenium providers, this means direct HTTP/export access is blocked from the current environment. For Selenium fallback, run with `--no-headless`, `--user-data-dir ~/.forexfactory-chrome-profile`, and `--manual-verification-timeout 180`, complete verification manually, then retry with the same profile.

### Export links not found

Use `--debug` and inspect `debug/http_calendar_*.html`. ForexFactory may have removed or changed the Weekly Export panel, or the request may have received a blocked/malformed page.

### Export endpoint blocked

The discovered export URL returned an HTTP error or a non-export payload. Use `forexfactory-html` or `saved-html`, and inspect debug artifacts.

### Historical date range not supported by export

If the only discovered files are `ff_calendar_thisweek.*`, the export provider can only cover the week contained in those files. Use `forexfactory-html` for historical date ranges.

### Direct HTML returns verification page

Use `--debug` and inspect `debug/http_calendar_*.txt`. If the response is a verification page, the project will not bypass it. Use `saved-html` with a manually saved valid calendar page, or Selenium manual verification fallback.

### HTML parser cannot find calendar rows

If debug HTML shows the real calendar page but no rows are parsed, ForexFactory likely changed its DOM. Update the direct HTML provider selectors/parser.

### Saved HTML is not a calendar page

The `saved-html` provider requires a saved ForexFactory calendar page containing calendar row markup. Verification pages, empty pages, and unrelated pages are rejected.

### Cache validation

If the validator reports missing-source rows, check whether they are legacy cache rows. Validate duplicates using canonicalized `datetime_local + currency + event` keys, not raw lowercase columns.

### Calendar selector missing

If debug artifacts show the real calendar page but no expected selectors, ForexFactory likely changed the DOM. Inspect the saved `.html` file in `debug/` and update the parser selectors.

### Blocked or malformed ForexFactory pages

The scraper reports security verification, privacy/consent pages, empty body pages, and missing calendar selectors separately. Use `--debug` and inspect `debug/*.txt`, `debug/*.html`, and `debug/*.png`.

### Headless mode issues

Security services may treat headless sessions differently. Establish the profile with `--no-headless` first. Headless reuse of the same profile may or may not work depending on the site's current checks.

### Empty CSV output

If the run finishes with no rows, check logs and debug artifacts. The requested dates may have no events, the site may have returned a verification page, or the DOM selectors may need updating.

### Details scraping failures

Details are optional per row. If a detail panel fails to open or parse, the base event row is preserved and the scraper logs a warning.

## License

This project is licensed under the [MIT License](LICENSE).

## Disclaimer

This scraper is intended for personal use and educational purposes only. Ensure compliance with Forex Factory's terms and policies. The scraper does not bypass CAPTCHA, Cloudflare, or other security verification systems.
