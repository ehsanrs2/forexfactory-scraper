import argparse
import logging
from datetime import datetime

from dateutil.tz import gettz

from .incremental import scrape_incremental
from .providers import ForexFactoryExportProvider, ForexFactoryHtmlProvider, ProviderError, SavedHtmlProvider

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)


def build_parser():
    parser = argparse.ArgumentParser(description="ForexFactory calendar scraper")
    parser.add_argument("--start", type=str, required=False, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, required=False, help="End date (YYYY-MM-DD)")
    parser.add_argument("--csv", type=str, default="forex_factory_cache.csv", help="Output CSV file")
    parser.add_argument("--tz", type=str, default="Asia/Tehran", help="Timezone")
    parser.add_argument("--details", action="store_true", help="Keep the compatibility flag for detail-oriented updates")
    parser.add_argument("--impact", type=str, default="", help="Filter by impact levels (comma-separated: high,medium,low)")
    parser.add_argument("--keep-currencies", type=str, nargs="+", help="Filter by currencies to keep (space-separated: USD EUR GBP etc.)")
    parser.add_argument(
        "--provider",
        choices=["forexfactory-html", "saved-html", "forexfactory-export"],
        default="forexfactory-html",
        help="Data provider. Default: forexfactory-html.",
    )
    parser.add_argument(
        "--export-format",
        choices=["json", "csv", "xml", "ics"],
        default="json",
        help="Export format for --provider forexfactory-export",
    )
    parser.add_argument("--input", type=str, default=None, help="Saved HTML input path for --provider saved-html")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser


def parse_args(argv=None):
    return build_parser().parse_args(argv)


def _resolve_dates(args, parser):
    tz = gettz(args.tz)
    if tz is None:
        parser.error(f"Unknown timezone: {args.tz}")

    if args.provider != "saved-html" and (not args.start or not args.end):
        parser.error("--start and --end are required unless --provider saved-html is used")

    from_date = datetime.fromisoformat(args.start).replace(tzinfo=tz) if args.start else datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    to_date = datetime.fromisoformat(args.end).replace(tzinfo=tz) if args.end else from_date
    if to_date < from_date:
        parser.error("--end must be greater than or equal to --start")
    return from_date, to_date


def _build_provider(args):
    if args.provider == "forexfactory-html":
        return ForexFactoryHtmlProvider(debug=args.debug)
    if args.provider == "saved-html":
        if not args.input:
            raise ValueError("--input is required with --provider saved-html")
        return SavedHtmlProvider(args.input, debug=args.debug)
    return ForexFactoryExportProvider(export_format=args.export_format, debug=args.debug)


def scrape_range_with_details(start_date, end_date, output_csv, tzname="Asia/Tehran"):
    return scrape_incremental(
        start_date,
        end_date,
        output_csv,
        tzname=tzname,
        scrape_details=True,
        provider=ForexFactoryHtmlProvider(),
        provider_kwargs={},
    )


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    impact_filter = [i.strip().lower() for i in args.impact.split(",")] if args.impact else None
    from_date, to_date = _resolve_dates(args, parser)

    try:
        provider = _build_provider(args)
    except ValueError as exc:
        parser.error(str(exc))

    provider_kwargs = {}
    if args.provider == "saved-html":
        provider_kwargs["all_dates"] = not (args.start and args.end)

    try:
        scrape_incremental(
            from_date,
            to_date,
            args.csv,
            tzname=args.tz,
            scrape_details=args.details,
            impact_filter=impact_filter,
            keep_currencies=args.keep_currencies,
            provider=provider,
            provider_kwargs=provider_kwargs,
        )
    except (ProviderError, RuntimeError) as exc:
        parser.exit(4, f"error: {exc}\n")


if __name__ == "__main__":
    main()
