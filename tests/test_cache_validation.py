import pandas as pd

from src.forexfactory.cache_validation import canonicalize_cache_frame, validate_cache_frame
from src.forexfactory.csv_util import merge_new_data


def test_canonicalize_legacy_only_rows():
    df = pd.DataFrame([
        {
            "DateTime": "2025-04-07T10:00:00+03:30",
            "Currency": "usd",
            "Impact": "High",
            "Event": "Jobs",
            "Actual": "1",
            "Forecast": "2",
            "Previous": "3",
            "Detail": "legacy detail",
        }
    ])

    canonical = canonicalize_cache_frame(df)

    assert canonical.iloc[0]["datetime_local"] == "2025-04-07T10:00:00+03:30"
    assert canonical.iloc[0]["currency"] == "USD"
    assert canonical.iloc[0]["event"] == "Jobs"
    assert canonical.iloc[0]["schema_source"] == "legacy"


def test_canonicalize_new_provider_rows():
    df = pd.DataFrame([
        {
            "date": "2025-04-07",
            "time": "10:00:00",
            "datetime_local": "2025-04-07T10:00:00+03:30",
            "datetime_utc": "2025-04-07T06:30:00+00:00",
            "currency": "USD",
            "impact": "High",
            "event": "Jobs",
            "actual": "1",
            "forecast": "2",
            "previous": "3",
            "detail": "new detail",
            "source": "forexfactory-html",
            "source_url": "https://example.test",
            "detail_url": "https://example.test/detail",
        }
    ])

    canonical = canonicalize_cache_frame(df)

    assert canonical.iloc[0]["datetime_local"] == "2025-04-07T10:00:00+03:30"
    assert canonical.iloc[0]["source"] == "forexfactory-html"
    assert canonical.iloc[0]["schema_source"] == "canonical"


def test_duplicate_detection_across_legacy_and_new_schema():
    df = pd.DataFrame([
        {
            "DateTime": "2025-04-07T10:00:00+03:30",
            "Currency": "USD",
            "Impact": "High",
            "Event": "Jobs",
            "Actual": "1",
            "Forecast": "2",
            "Previous": "3",
            "Detail": "",
        },
        {
            "date": "2025-04-07",
            "time": "10:00:00",
            "datetime_local": "2025-04-07T10:00:00+03:30",
            "datetime_utc": "2025-04-07T06:30:00+00:00",
            "currency": "USD",
            "impact": "High",
            "event": "Jobs",
            "actual": "1",
            "forecast": "2",
            "previous": "3",
            "detail": "",
            "source": "forexfactory-html",
            "source_url": "https://example.test",
            "detail_url": "https://example.test/detail",
        },
    ])

    report = validate_cache_frame(df, "2025-04-07", "2025-04-07")

    assert report.range_duplicate_groups == 1
    assert report.range_duplicated_rows_including_first == 2


def test_preserves_rows_outside_requested_range():
    df = pd.DataFrame([
        {
            "date": "2025-04-06",
            "time": "10:00:00",
            "datetime_local": "2025-04-06T10:00:00+03:30",
            "datetime_utc": "2025-04-06T06:30:00+00:00",
            "currency": "USD",
            "impact": "High",
            "event": "Old",
            "actual": "",
            "forecast": "",
            "previous": "",
            "detail": "",
            "source": "forexfactory-html",
        },
        {
            "date": "2025-04-07",
            "time": "10:00:00",
            "datetime_local": "2025-04-07T10:00:00+03:30",
            "datetime_utc": "2025-04-07T06:30:00+00:00",
            "currency": "USD",
            "impact": "High",
            "event": "New",
            "actual": "",
            "forecast": "",
            "previous": "",
            "detail": "",
            "source": "forexfactory-html",
        },
    ])

    report = validate_cache_frame(df, "2025-04-07", "2025-04-07")

    assert report.total_rows == 2
    assert report.range_rows == 1
    assert report.range_min_date == "2025-04-07"
    assert report.range_max_date == "2025-04-07"


def test_missing_source_rows_reported():
    df = pd.DataFrame([
        {
            "DateTime": "2025-04-07T10:00:00+03:30",
            "Currency": "USD",
            "Impact": "High",
            "Event": "Jobs",
            "Actual": "1",
            "Forecast": "2",
            "Previous": "3",
            "Detail": "",
        },
        {
            "date": "2025-04-07",
            "time": "10:00:00",
            "datetime_local": "2025-04-07T10:00:00+03:30",
            "datetime_utc": "2025-04-07T06:30:00+00:00",
            "currency": "USD",
            "impact": "High",
            "event": "Jobs 2",
            "actual": "1",
            "forecast": "2",
            "previous": "3",
            "detail": "",
            "source": "forexfactory-html",
        },
    ])

    report = validate_cache_frame(df, "2025-04-07", "2025-04-07")

    assert report.missing_source_rows == 1
    assert report.legacy_rows_in_range == 1


def test_zero_duplicate_range():
    df = pd.DataFrame([
        {
            "date": "2025-04-07",
            "time": "10:00:00",
            "datetime_local": "2025-04-07T10:00:00+03:30",
            "datetime_utc": "2025-04-07T06:30:00+00:00",
            "currency": "USD",
            "impact": "High",
            "event": "Jobs",
            "actual": "",
            "forecast": "",
            "previous": "",
            "detail": "",
            "source": "forexfactory-html",
        },
        {
            "date": "2025-04-07",
            "time": "11:00:00",
            "datetime_local": "2025-04-07T11:00:00+03:30",
            "datetime_utc": "2025-04-07T07:30:00+00:00",
            "currency": "EUR",
            "impact": "Low",
            "event": "Trade",
            "actual": "",
            "forecast": "",
            "previous": "",
            "detail": "",
            "source": "forexfactory-html",
        },
    ])

    report = validate_cache_frame(df, "2025-04-07", "2025-04-07")

    assert report.range_duplicate_groups == 0
    assert report.range_duplicated_rows_including_first == 0


def test_merge_helper_is_idempotent():
    existing = pd.DataFrame([
        {
            "DateTime": "2025-04-07T10:00:00+03:30",
            "Currency": "USD",
            "Impact": "High",
            "Event": "Jobs",
            "Actual": "",
            "Forecast": "",
            "Previous": "",
            "Detail": "",
        }
    ])
    incoming = pd.DataFrame([
        {
            "DateTime": "2025-04-07T10:00:00+03:30",
            "Currency": "USD",
            "Impact": "High",
            "Event": "Jobs",
            "Actual": "1",
            "Forecast": "2",
            "Previous": "3",
            "Detail": "source detail",
        }
    ])

    once = merge_new_data(existing, incoming)
    twice = merge_new_data(once, incoming)

    assert len(once) == 1
    assert len(twice) == 1
    assert twice.iloc[0]["Detail"] == "source detail"
