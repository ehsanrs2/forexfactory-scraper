# src/forexfactory/incremental.py

import logging
import os
import pandas as pd
from datetime import datetime, timedelta
from dateutil.tz import gettz

from .csv_util import ensure_csv_header, read_existing_data, write_data_to_csv, merge_new_data
from .scraper import scrape_range_pandas

#basicConfig is expected to be called in main.py
logger = logging.getLogger(__name__)

def scrape_incremental(from_date: datetime, to_date: datetime, output_csv: str, tzname: str, scrape_details: bool = False):
    """
    Orchestrates the scraping of Forex Factory data for a given date range.

    Currently, this function delegates to `scrape_range_pandas`, which scrapes data
    for the entire specified range and merges it into the CSV. The name "scrape_incremental"
    is aspirational, suggesting future enhancements where it might perform more targeted
    updates (e.g., only missing days or truly incremental updates).

    Args:
        from_date: The start date (inclusive) for scraping.
        to_date: The end date (inclusive) for scraping.
        output_csv: Path to the CSV file where data will be stored.
        tzname: Timezone name (e.g., "America/New_York") for date handling.
        scrape_details: If True, scrapes detailed event information. Defaults to False.
    """
    # Note: The current implementation calls scrape_range_pandas, which handles the
    # full range. True incremental logic (e.g., checking for missing days or
    # only fetching new data) is not yet implemented here.
    scrape_range_pandas(from_date, to_date, output_csv, tzname=tzname, scrape_details=scrape_details)
