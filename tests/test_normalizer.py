from src.forexfactory.normalizer import normalize_event


def test_normalize_event_populates_legacy_and_provider_fields():
    row = normalize_event(
        {
            "title": "GDP",
            "country": "usd",
            "date": "2025-04-07T08:30:00-04:00",
            "impact": "High",
            "forecast": "1",
            "previous": "2",
            "url": "https://example.test",
        },
        "Asia/Tehran",
        default_source="forexfactory-export",
    )

    assert row["Currency"] == "USD"
    assert row["currency"] == "USD"
    assert row["Event"] == "GDP"
    assert row["event"] == "GDP"
    assert row["source"] == "forexfactory-export"
    assert row["DateTime"].startswith("2025-04-07T")
