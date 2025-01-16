# src/forexfactory/main.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import csv
import time
from datetime import datetime, timedelta
from dateutil.tz import gettz
import undetected_chromedriver as uc
from .date_logic import build_url_for_partial_range, build_url_for_full_month
from .scraper import parse_calendar_page_with_details
from .incremental import scrape_incremental
import logging

logging.basicConfig(
    level=logging.INFO,    # یا DEBUG
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def ensure_csv_header(file_path: str):
    """
    Creates a CSV file with header if the file does not exist or is empty.
    The last column is 'Detail' for the calendarspecs data. from .detail_parser import parse_detail_table, detail_data_to_string
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            if first_line.strip():
                return
    except FileNotFoundError:
        pass

    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "DateTime",
            "Currency",
            "Impact",
            "Event",
            "Actual",
            "Forecast",
            "Previous",
            "Detail"   # extra column for the content of calendarspecs
        ])

def scrape_range_with_details(
    start_date: datetime,
    end_date: datetime,
    output_csv: str = "forex_factory_details.csv",
    tzname: str = "Asia/Tehran"
):
    """
    Main function:
    - Creates a single browser session
    - Loops from start_date.month/year to end_date.month/year
    - For each month: checks if partial or full. Builds the param ?range=... or ?month=...
    - parse_calendar_page_with_details => extracts events + detail
    - Writes them in CSV
    """
    ensure_csv_header(output_csv)

    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)
    driver.set_window_size(1400, 1000)

    current = datetime(start_date.year, start_date.month, 1, tzinfo=start_date.tzinfo)
    boundary = end_date.replace(day=1) + timedelta(days=32)
    boundary = datetime(boundary.year, boundary.month, 1, tzinfo=end_date.tzinfo)

    total_events = 0

    try:
        while current < boundary:
            # start_of_this_month / end_of_this_month
            start_of_m = current
            next_candidate = start_of_m.replace(day=28) + timedelta(days=4)
            end_of_m = datetime(next_candidate.year, next_candidate.month, 1, tzinfo=current.tzinfo) - timedelta(days=1)

            partial_start = max(start_date, start_of_m)
            partial_end   = min(end_date, end_of_m)

            # full month or partial
            if partial_start.day == 1 and partial_end.day == end_of_m.day:
                # full month
                url_param = build_url_for_full_month(current.year, current.month)
            else:
                # partial month
                url_param = build_url_for_partial_range(partial_start, partial_end)

            url = "https://www.forexfactory.com/calendar?" + url_param
            driver.get(url)
            time.sleep(2)  # wait for page load or Cloudflare

            count = parse_calendar_page_with_details(
                driver=driver,
                start_date=partial_start,
                end_date=partial_end,
                output_csv=output_csv,
                tzname=tzname
            )
            total_events += count

            # Move to next month
            next_month_candidate = current + timedelta(days=32)
            current = datetime(next_month_candidate.year, next_month_candidate.month, 1, tzinfo=current.tzinfo)

    finally:
        driver.quit()


    logger.info(f"Done. Total events with details: {total_events}")



if __name__ == "__main__":
    tz = gettz("Asia/Tehran")
    # Example usage: from 2025-01-01 to 2025-01-10
    # start_dt = datetime(2025, 1, 5, tzinfo=tz)
    # end_dt   = datetime(2025, 1, 5, tzinfo=tz)

    # scrape_range_with_details(
    #     start_date=start_dt,
    #     end_date=end_dt,
    #     output_csv="forex_factory_details.csv",
    #     tzname="Asia/Tehran"
    # )
    #
    from_date = datetime(2024, 3, 21, tzinfo=gettz("Asia/Tehran"))
    to_date   = datetime(2024, 3, 25, tzinfo=gettz("Asia/Tehran"))
    scrape_incremental(from_date, to_date, "forex_factory_cache.csv", tzname="Asia/Tehran")
