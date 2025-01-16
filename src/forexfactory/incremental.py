# src/forexfactory/incremental.py
from datetime import datetime, timedelta
from dateutil.tz import gettz

from .csv_util import ensure_csv_header, get_last_datetime_from_csv
from .scraper import parse_calendar_page_with_details
from .date_logic import build_url_for_full_month, build_url_for_partial_range

def scrape_incremental(from_date, to_date, output_csv, tzname="Asia/Tehran"):
    """
    1) Checks what date the last CSV row is.
    2) If that date is >= to_date, we don't need to scrape.
    3) Otherwise, we just get the range [real_start, to_date].
    """

    # Step 1: File header if empty
    ensure_csv_header(output_csv)

    # Step 2: Read the latest date
    last_dt = get_last_datetime_from_csv(output_csv)
    if last_dt is not None:
        if last_dt >= to_date:
            print("No need to scrape. Data up to", to_date, "already in CSV.")
            return
        # real_start: max(last_dt + 1 day, from_date)
        real_start = max(last_dt + timedelta(days=1), from_date)
    else:
        real_start = from_date

    # Step 3: Same month-by-month scrolling logic
    # We can edit the same scrape_range_with_details logic
    # or create one directly.
    _scrape_range(real_start, to_date, output_csv, tzname)


def _scrape_range(from_date, to_date, output_csv, tzname):
    """
    Similar to what we did before in scrape_range_with_details,
    but in a simpler form or we reuse the same.
    """
    import undetected_chromedriver as uc
    import time

    from .scraper import parse_calendar_page_with_details

    driver = uc.Chrome()
    driver.set_window_size(1400, 1000)

    # Month-to-month interval logic
    current = datetime(from_date.year, from_date.month, 1, tzinfo=from_date.tzinfo)
    boundary = to_date.replace(day=1) + timedelta(days=32)
    boundary = datetime(boundary.year, boundary.month, 1, tzinfo=to_date.tzinfo)

    try:
        total_events = 0
        while current < boundary:
            start_of_m = current
            next_candidate = start_of_m.replace(day=28) + timedelta(days=4)
            end_of_m = datetime(next_candidate.year, next_candidate.month, 1, tzinfo=current.tzinfo) - timedelta(days=1)

            partial_start = max(from_date, start_of_m)
            partial_end   = min(to_date,   end_of_m)

            # full or partial
            if partial_start.day == 1 and partial_end.day == end_of_m.day:
                url_param = build_url_for_full_month(current.year, current.month)
            else:
                url_param = build_url_for_partial_range(partial_start, partial_end)

            url = "https://www.forexfactory.com/calendar?" + url_param
            driver.get(url)
            time.sleep(2)  # wait load / Cloudflare

            count = parse_calendar_page_with_details(
                driver=driver,
                start_date=partial_start,
                end_date=partial_end,
                output_csv=output_csv,
                tzname=tzname
            )
            total_events += count

            # next month
            next_month_candidate = current + timedelta(days=32)
            current = datetime(next_month_candidate.year, next_month_candidate.month, 1, tzinfo=current.tzinfo)

        print("[INCREMENTAL] Done. total events:", total_events)
    finally:
        driver.quit()

