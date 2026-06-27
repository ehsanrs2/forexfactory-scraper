from src.forexfactory.main import parse_args


def test_parse_driver_options():
    args = parse_args([
        "--start", "2025-04-07",
        "--end", "2025-04-14",
        "--driver", "selenium",
        "--chrome-binary", "/opt/chrome/chrome",
        "--chromedriver", "/opt/chromedriver",
        "--headless",
        "--user-agent", "test-agent",
        "--user-data-dir", "~/.forexfactory-chrome-profile",
        "--page-timeout", "45",
        "--retries", "1",
        "--manual-verification-timeout", "180",
        "--debug",
    ])

    assert args.driver == "selenium"
    assert args.chrome_binary == "/opt/chrome/chrome"
    assert args.chromedriver == "/opt/chromedriver"
    assert args.headless is True
    assert args.user_agent == "test-agent"
    assert args.user_data_dir == "~/.forexfactory-chrome-profile"
    assert args.page_timeout == 45
    assert args.retries == 1
    assert args.manual_verification_timeout == 180
    assert args.debug is True


def test_no_headless_overrides_headless_default():
    args = parse_args(["--start", "2025-04-07", "--end", "2025-04-14", "--no-headless"])

    assert args.headless is False


def test_parse_provider_options():
    args = parse_args([
        "--provider", "forexfactory-export",
        "--export-format", "json",
        "--start", "2025-04-07",
        "--end", "2025-04-14",
    ])
    assert args.provider == "forexfactory-export"
    assert args.export_format == "json"

    args = parse_args([
        "--provider", "saved-html",
        "--input", "saved_forexfactory_calendar.html",
    ])
    assert args.provider == "saved-html"
    assert args.input == "saved_forexfactory_calendar.html"
    assert args.start is None
    assert args.end is None
