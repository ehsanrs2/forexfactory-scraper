# Forex Factory Economic Calendar Scraper — FAQ and Examples

[← Project README](../README.md) · [Historical CSV dataset on Hugging Face](https://huggingface.co/datasets/Ehsanrs2/Forex_Factory_Calendar)

This FAQ covers the common questions behind searches for a **Forex Factory Python scraper**, **historical economic calendar CSV**, and **economic calendar data for backtesting**.

## Is this an official Forex Factory API?

No. It is an independent Python project that reads available public HTML, locally saved HTML, or export files when exposed by the source. It is not an official or guaranteed API, and it does not bypass CAPTCHA, Cloudflare, or access controls.

## How do I collect Forex Factory economic events with Python?

Install dependencies from the repository root and run a bounded range:

```bash
python -m pip install -r requirements.txt
python -m src.forexfactory.main --start 2025-04-07 --end 2025-04-14 --csv forex_factory_cache.csv --tz UTC
```

Run the accompanying validator:

```bash
python scripts/validate_cache.py --csv forex_factory_cache.csv --start 2025-04-07 --end 2025-04-14 --tz UTC
```

Live collection requires source availability and may fail with a verification response.

## Can I download a historical Forex Factory economic calendar CSV without scraping?

Yes. A separately published [Hugging Face dataset](https://huggingface.co/datasets/Ehsanrs2/Forex_Factory_Calendar) contains an original historical snapshot for 2007-01-01 to 2025-04-07. It is not automatically refreshed by this repository's incremental cache workflow.

## Can I scrape without Selenium?

The current `forexfactory-html` provider parses publicly available HTML without Selenium. If the source does not expose the calendar HTML, the provider reports a failure rather than bypassing website security.

The companion historical Hugging Face dataset was originally documented as collected using a Selenium-based process; that provenance is separate from this repository's current implementation.

## How do I collect only high-impact USD events?

```bash
python -m src.forexfactory.main --start 2025-04-07 --end 2025-04-14 --impact high --keep-currencies USD --csv forex_factory_cache.csv
```

`--impact` filters by impact value and `--keep-currencies` accepts one or more currency codes.

## How does the historical cache avoid duplicates?

Existing CSV rows are normalized before merging with newly fetched events. Event identity is based on normalized date/time, currency, and event name. The validator reports duplicate groups and rows with missing key fields. Source changes can still affect completeness and semantic consistency.

## Does updating one week erase earlier cached events?

No. The `--start` and `--end` options define the requested fetch range; the cache is intended to accumulate history. Back up your cache before large migrations or source format changes.

## Which timezones are supported?

Use `--tz` with a timezone identifier such as `UTC` or `Asia/Tehran`. The new normalized CSV schema includes both `datetime_local` and `datetime_utc`. Check historical timezone offsets carefully when joining to market datasets.

## Can I use the data for automated trading or backtesting?

You can use the CSV for research, but historical point-in-time accuracy is **not guaranteed**. Revised economic values, event edits, and reporting delays may introduce look-ahead bias. Validate timing and provenance independently before making claims about trading performance.

## What do I do if the scraper hits a CAPTCHA or Cloudflare page?

The project does not bypass security verification. Use an HTML file legitimately saved from an accessible calendar page with `--provider saved-html --input saved_forexfactory_calendar.html` or obtain data from a source you are permitted to use.

## Does the export provider provide every historical year?

No. Weekly exports may be available for recent periods only and are not a documented public API with guaranteed historical coverage.

## Where should I report parsing failures?

Open a [GitHub issue](https://github.com/ehsanrs2/forexfactory-scraper/issues) with the sanitized command and error, Python version, selected provider, and a reproducible non-sensitive HTML sample if redistribution is permitted. Do not share cookies, credentials, or protected pages.

## Licensing and provenance

The code is licensed under [GPL-3.0](../LICENSE). Economic calendar data originates from [Forex Factory](https://www.forexfactory.com/calendar), and its usage rights are separate from the code license. Review the [source's notices and terms](https://www.forexfactory.com/notices) and the published dataset's own card before redistribution.
