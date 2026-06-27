from datetime import datetime

import pandas as pd
from dateutil.tz import gettz

from src.forexfactory.incremental import scrape_incremental


class DummyProvider:
    def __init__(self, events):
        self.events = events
        self.calls = []

    def fetch_events(self, start_date, end_date, tzname, **kwargs):
        self.calls.append((start_date, end_date, tzname, kwargs))
        return list(self.events)


def _event(datetime_local: str, currency: str, event: str, source: str = "forexfactory-html"):
    return {
        "date": datetime_local[:10],
        "time": datetime_local[11:19],
        "datetime_local": datetime_local,
        "datetime_utc": "2025-04-07T06:30:00+00:00",
        "currency": currency,
        "impact": "High",
        "event": event,
        "actual": "",
        "forecast": "",
        "previous": "",
        "source": source,
        "source_url": "https://example.test",
        "detail_url": "https://example.test/detail",
    }


def test_scrape_incremental_is_idempotent(tmp_path):
    output = tmp_path / "cache.csv"
    provider = DummyProvider([_event("2025-04-07T10:00:00+03:30", "USD", "Jobs")])
    tz = gettz("Asia/Tehran")
    start = datetime(2025, 4, 7, tzinfo=tz)
    end = datetime(2025, 4, 7, tzinfo=tz)

    scrape_incremental(start, end, str(output), tzname="Asia/Tehran", provider=provider)
    scrape_incremental(start, end, str(output), tzname="Asia/Tehran", provider=provider)

    df = pd.read_csv(output, dtype=str)

    assert len(df) == 1
    assert df.iloc[0]["DateTime"] == "2025-04-07T10:00:00+03:30"
    assert len(provider.calls) == 2


def test_scrape_incremental_preserves_existing_history(tmp_path):
    output = tmp_path / "cache.csv"
    existing = pd.DataFrame([
        {
            "DateTime": "2025-04-06T09:00:00+03:30",
            "Currency": "EUR",
            "Impact": "Low",
            "Event": "Old",
            "Actual": "",
            "Forecast": "",
            "Previous": "",
            "Detail": "",
        }
    ])
    existing.to_csv(output, index=False)

    provider = DummyProvider([_event("2025-04-07T10:00:00+03:30", "USD", "Jobs")])
    tz = gettz("Asia/Tehran")
    start = datetime(2025, 4, 7, tzinfo=tz)
    end = datetime(2025, 4, 7, tzinfo=tz)

    scrape_incremental(start, end, str(output), tzname="Asia/Tehran", provider=provider)
    df = pd.read_csv(output, dtype=str)

    assert set(df["DateTime"]) == {"2025-04-06T09:00:00+03:30", "2025-04-07T10:00:00+03:30"}
