import logging
from datetime import timedelta

from .csv_util import ensure_csv_header, read_existing_data
from .scraper import scrape_range_pandas

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def _iter_days(from_date, to_date):
    current_day = from_date
    while current_day <= to_date:
        yield current_day
        current_day += timedelta(days=1)


def _has_complete_day(existing_df, day, scrape_details=False):
    if existing_df.empty or "DateTime" not in existing_df.columns:
        return False

    day_prefix = day.date().isoformat()
    day_rows = existing_df[existing_df["DateTime"].astype(str).str.startswith(day_prefix)]
    if day_rows.empty:
        return False

    if not scrape_details:
        return True

    detail = day_rows["Detail"].fillna("").astype(str).str.strip()
    return bool(detail.ne("").all())


def _group_contiguous_days(days):
    if not days:
        return []

    groups = []
    start = prev = days[0]
    for day in days[1:]:
        if day.date() == (prev + timedelta(days=1)).date():
            prev = day
            continue
        groups.append((start, prev))
        start = prev = day
    groups.append((start, prev))
    return groups


def scrape_incremental(from_date, to_date, output_csv, tzname="Asia/Tehran", scrape_details=False, impact_filter=None, keep_currencies=None):
    """
    Scrape only days that are missing from the output CSV.
    When scrape_details=True, days with any empty Detail values are refreshed.
    """
    ensure_csv_header(output_csv)
    existing_df = read_existing_data(output_csv)

    days_to_scrape = [
        day for day in _iter_days(from_date, to_date)
        if not _has_complete_day(existing_df, day, scrape_details=scrape_details)
    ]

    if not days_to_scrape:
        logger.info("All requested days already exist in %s; nothing to scrape.", output_csv)
        return

    for start_day, end_day in _group_contiguous_days(days_to_scrape):
        scrape_range_pandas(
            start_day,
            end_day,
            output_csv,
            tzname=tzname,
            scrape_details=scrape_details,
            impact_filter=impact_filter,
            keep_currencies=keep_currencies,
        )
