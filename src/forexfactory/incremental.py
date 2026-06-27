import logging
from datetime import timedelta

import pandas as pd

from .csv_util import ensure_csv_header, read_existing_data, merge_new_data, write_data_to_csv
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


def scrape_incremental(
    from_date,
    to_date,
    output_csv,
    tzname="Asia/Tehran",
    scrape_details=False,
    impact_filter=None,
    keep_currencies=None,
    driver_config=None,
    page_timeout=120,
    retries=2,
    manual_verification_timeout=0,
    dump_debug_artifacts=False,
):
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
            driver_config=driver_config,
            page_timeout=page_timeout,
            retries=retries,
            manual_verification_timeout=manual_verification_timeout,
            dump_debug_artifacts=dump_debug_artifacts,
        )


def write_provider_events(output_csv, events, impact_filter=None, keep_currencies=None):
    ensure_csv_header(output_csv)
    existing_df = read_existing_data(output_csv)
    df_new = pd.DataFrame(events)
    if df_new.empty:
        logger.info("Provider returned no events; CSV unchanged.")
        write_data_to_csv(existing_df, output_csv)
        return

    if impact_filter and "impact" in df_new.columns:
        import re
        pattern = "|".join(re.escape(i) for i in impact_filter)
        df_new = df_new[df_new["impact"].fillna("").str.lower().str.contains(pattern)]
    if keep_currencies and "currency" in df_new.columns:
        keep = {currency.upper() for currency in keep_currencies}
        df_new = df_new[df_new["currency"].fillna("").str.upper().isin(keep)]

    merged_df = merge_new_data(existing_df, df_new)
    write_data_to_csv(merged_df, output_csv)
    logger.info("Done. Added/updated %s provider rows.", max(len(merged_df) - len(existing_df), 0))
