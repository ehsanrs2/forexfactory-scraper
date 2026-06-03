import logging
import argparse
from datetime import datetime
from dateutil.tz import gettz

from .incremental import scrape_incremental
from .scraper import scrape_range_pandas

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def scrape_range_with_details(start_date, end_date, output_csv, tzname="Asia/Tehran"):
    return scrape_range_pandas(
        start_date,
        end_date,
        output_csv,
        tzname=tzname,
        scrape_details=True,
    )


def main():
    parser = argparse.ArgumentParser(description="Forex Factory Scraper (Incremental + pandas)")
    parser.add_argument('--start', type=str, required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--csv', type=str, default="forex_factory_cache.csv", help='Output CSV file')
    parser.add_argument('--tz', type=str, default="Asia/Tehran", help='Timezone')
    parser.add_argument('--details', action='store_true', help='Scrape details or not')
    parser.add_argument('--impact', type=str, default='', help='Filter by impact levels (comma-separated: high,medium,low)')
    parser.add_argument('--keep-currencies', type=str, nargs='+', help='Filter by currencies to keep (space-separated: USD EUR GBP etc.)')

    args = parser.parse_args()

    tz = gettz(args.tz)
    if tz is None:
        parser.error(f"Unknown timezone: {args.tz}")

    from_date = datetime.fromisoformat(args.start).replace(tzinfo=tz)
    to_date = datetime.fromisoformat(args.end).replace(tzinfo=tz)
    if to_date < from_date:
        parser.error("--end must be greater than or equal to --start")

    impact_filter = [i.strip().lower() for i in args.impact.split(',')] if args.impact else None

    scrape_incremental(from_date, to_date, args.csv, tzname=args.tz, scrape_details=args.details, impact_filter=impact_filter, keep_currencies=args.keep_currencies)

if __name__ == "__main__":
    main()
