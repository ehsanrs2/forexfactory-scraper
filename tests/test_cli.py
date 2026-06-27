from src.forexfactory.main import parse_args


def test_default_provider_is_html():
    args = parse_args(["--start", "2025-04-07", "--end", "2025-04-14"])

    assert args.provider == "forexfactory-html"


def test_parse_provider_options():
    args = parse_args([
        "--provider", "saved-html",
        "--input", "saved_forexfactory_calendar.html",
    ])

    assert args.provider == "saved-html"
    assert args.input == "saved_forexfactory_calendar.html"
    assert args.start is None
    assert args.end is None

    args = parse_args([
        "--provider", "forexfactory-export",
        "--export-format", "json",
        "--start", "2025-04-07",
        "--end", "2025-04-14",
    ])

    assert args.provider == "forexfactory-export"
    assert args.export_format == "json"


def test_parse_common_cache_options():
    args = parse_args([
        "--start", "2025-04-07",
        "--end", "2025-04-14",
        "--csv", "cache.csv",
        "--tz", "Asia/Tehran",
        "--details",
        "--impact", "high,medium",
        "--keep-currencies", "USD", "EUR",
        "--debug",
    ])

    assert args.csv == "cache.csv"
    assert args.tz == "Asia/Tehran"
    assert args.details is True
    assert args.impact == "high,medium"
    assert args.keep_currencies == ["USD", "EUR"]
    assert args.debug is True
