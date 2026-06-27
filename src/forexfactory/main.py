import logging
import argparse
from datetime import datetime
from dateutil.tz import gettz

from .incremental import scrape_incremental, write_provider_events
from .scraper import PageValidationError, scrape_range_pandas
from .driver import DriverConfig, DriverStartupError
from .providers import ForexFactoryExportProvider, ForexFactoryHtmlProvider, SavedHtmlProvider, ProviderError

LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)


def scrape_range_with_details(start_date, end_date, output_csv, tzname="Asia/Tehran", driver_config=None):
    return scrape_range_pandas(
        start_date,
        end_date,
        output_csv,
        tzname=tzname,
        scrape_details=True,
        driver_config=driver_config,
    )


def build_parser():
    parser = argparse.ArgumentParser(description="Forex Factory Scraper (Incremental + pandas)")
    parser.add_argument('--start', type=str, required=False, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, required=False, help='End date (YYYY-MM-DD)')
    parser.add_argument('--csv', type=str, default="forex_factory_cache.csv", help='Output CSV file')
    parser.add_argument('--tz', type=str, default="Asia/Tehran", help='Timezone')
    parser.add_argument('--details', action='store_true', help='Scrape details or not')
    parser.add_argument('--impact', type=str, default='', help='Filter by impact levels (comma-separated: high,medium,low)')
    parser.add_argument('--keep-currencies', type=str, nargs='+', help='Filter by currencies to keep (space-separated: USD EUR GBP etc.)')
    parser.add_argument(
        '--provider',
        choices=['forexfactory-export', 'forexfactory-html', 'saved-html', 'forexfactory-selenium'],
        default='forexfactory-selenium',
        help='Data provider. Prefer forexfactory-export or forexfactory-html when available.',
    )
    parser.add_argument('--export-format', choices=['json', 'csv', 'xml', 'ics'], default='json', help='Export format for --provider forexfactory-export')
    parser.add_argument('--input', type=str, default=None, help='Saved HTML input path for --provider saved-html')
    parser.add_argument('--driver', choices=['selenium', 'uc'], default=None, help='Browser driver backend. Default: FOREXFACTORY_DRIVER or selenium')
    parser.add_argument('--chrome-binary', type=str, default=None, help='Path to Chrome/Chromium binary. Env: FOREXFACTORY_CHROME_BINARY')
    parser.add_argument('--chromedriver', type=str, default=None, help='Path to local ChromeDriver. Env: FOREXFACTORY_CHROMEDRIVER')
    headless_group = parser.add_mutually_exclusive_group()
    headless_group.add_argument('--headless', dest='headless', action='store_true', help='Run Chrome in headless mode')
    headless_group.add_argument('--no-headless', dest='headless', action='store_false', help='Run Chrome with a visible window')
    parser.set_defaults(headless=None)
    parser.add_argument('--user-agent', type=str, default=None, help='Custom browser user-agent. Env: FOREXFACTORY_USER_AGENT')
    parser.add_argument('--user-data-dir', type=str, default=None, help='Persistent Chrome profile directory. Env: FOREXFACTORY_USER_DATA_DIR')
    parser.add_argument('--page-timeout', type=int, default=None, help='Page load timeout in seconds. Default: 120')
    parser.add_argument('--retries', type=int, default=2, help='Retries per day after page load/browser failures. Default: 2')
    parser.add_argument('--manual-verification-timeout', type=int, default=0, help='Seconds to wait for manual security verification. Default: 0')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    return parser


def parse_args(argv=None):
    return build_parser().parse_args(argv)


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.retries < 0:
        parser.error("--retries must be greater than or equal to 0")
    if args.manual_verification_timeout < 0:
        parser.error("--manual-verification-timeout must be greater than or equal to 0")

    tz = gettz(args.tz)
    if tz is None:
        parser.error(f"Unknown timezone: {args.tz}")

    if args.provider != 'saved-html' and (not args.start or not args.end):
        parser.error("--start and --end are required unless --provider saved-html is used")
    from_date = datetime.fromisoformat(args.start).replace(tzinfo=tz) if args.start else datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    to_date = datetime.fromisoformat(args.end).replace(tzinfo=tz) if args.end else from_date
    if to_date < from_date:
        parser.error("--end must be greater than or equal to --start")

    impact_filter = [i.strip().lower() for i in args.impact.split(',')] if args.impact else None
    page_timeout = args.page_timeout or 120
    if page_timeout <= 0:
        parser.error("--page-timeout must be greater than 0")

    driver_config = DriverConfig.from_env(
        driver=args.driver,
        chrome_binary=args.chrome_binary,
        chromedriver=args.chromedriver,
        headless=args.headless,
        user_agent=args.user_agent,
        user_data_dir=args.user_data_dir,
        page_timeout=page_timeout,
    )
    logger.debug("Driver config: %s", driver_config)
    if args.manual_verification_timeout > 0 and driver_config.headless:
        logger.warning("Manual verification usually requires --no-headless so you can interact with the browser.")

    try:
        if args.provider == 'forexfactory-export':
            provider = ForexFactoryExportProvider(export_format=args.export_format, debug=args.debug, timeout=page_timeout)
            events = provider.fetch_events(from_date, to_date, args.tz)
            write_provider_events(args.csv, events, impact_filter=impact_filter, keep_currencies=args.keep_currencies)
            return

        if args.provider == 'forexfactory-html':
            provider = ForexFactoryHtmlProvider(debug=args.debug, timeout=page_timeout)
            events = provider.fetch_events(from_date, to_date, args.tz)
            write_provider_events(args.csv, events, impact_filter=impact_filter, keep_currencies=args.keep_currencies)
            return

        if args.provider == 'saved-html':
            if not args.input:
                parser.error("--input is required with --provider saved-html")
            provider = SavedHtmlProvider(args.input, debug=args.debug)
            events = provider.fetch_events(from_date, to_date, args.tz, all_dates=not (args.start and args.end))
            write_provider_events(args.csv, events, impact_filter=impact_filter, keep_currencies=args.keep_currencies)
            return

        scrape_incremental(
            from_date,
            to_date,
            args.csv,
            tzname=args.tz,
            scrape_details=args.details,
            impact_filter=impact_filter,
            keep_currencies=args.keep_currencies,
            driver_config=driver_config,
            page_timeout=page_timeout,
            retries=args.retries,
            manual_verification_timeout=args.manual_verification_timeout,
            dump_debug_artifacts=args.debug,
        )
    except DriverStartupError as exc:
        parser.exit(2, f"error: {exc}\n")
    except PageValidationError as exc:
        parser.exit(3, f"error: {exc}\n")
    except ProviderError as exc:
        parser.exit(4, f"error: {exc}\n")

if __name__ == "__main__":
    main()
