# src/forexfactory/scraper.py
import time
import re
from datetime import datetime
from dateutil.tz import gettz
from selenium.webdriver.common.by import By
from .detail_parser import parse_detail_table, detail_data_to_string
import logging
import csv

logging.basicConfig(
    level=logging.INFO,    # یا DEBUG
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def get_day_from_day_breaker(row, fallback_date: datetime, tzname: str):
    local_tz = gettz(tzname)
    day_breaker_cell = row.find_element(By.XPATH, './/td[contains(@class,"calendar__cell")]')
    raw_text = (day_breaker_cell.get_attribute("textContent") or "").strip()
    parts = raw_text.split()
    if len(parts) >= 2:
        month_abbr = parts[-2]
        day_str = parts[-1]
        guess_year = fallback_date.year
        dt_str = f"{month_abbr}{day_str} {guess_year}"
        try:
            parsed_day = datetime.strptime(dt_str, "%b%d %Y").replace(tzinfo=local_tz)
            return parsed_day
        except Exception as e:
            logger.error("Error in get_day_from_day_breaker: %s", e, exc_info=True)
            return None
    return None

def extract_basic_cells(row, current_day: datetime):
    """
    Extracts main columns from an event row:
    - time, currency, impact, event, actual, forecast, previous
    Then calculates event_dt based on current_day + time.
    Returns (event_dt, currency_text, impact_text, event_text, actual_text, forecast_text, previous_text).
    """
    time_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__time")]')
    currency_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__currency")]')
    impact_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__impact")]')
    event_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__event")]')
    actual_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__actual")]')
    forecast_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__forecast")]')
    previous_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__previous")]')

    time_text = time_el.text.strip()
    currency_text = currency_el.text.strip()

    # impact
    impact_text = ""
    try:
        impact_span = impact_el.find_element(By.XPATH, './/span')
        impact_text = impact_span.get_attribute("title") or ""
    except Exception as e:
        logger.error("Error in extract_basic_cells: %s", e, exc_info=True)
        impact_text = impact_el.text.strip()

    event_text = event_el.text.strip()
    actual_text = actual_el.text.strip()
    forecast_text = forecast_el.text.strip()
    previous_text = previous_el.text.strip()

    # compute event_dt
    event_dt = current_day
    time_lower = time_text.lower()
    if "day" in time_lower:
        # "All Day"
        event_dt = event_dt.replace(hour=23, minute=59, second=59)
    elif "data" in time_lower:
        # "No Data"
        event_dt = event_dt.replace(hour=0, minute=0, second=1)
    else:
        m = re.match(r'(\d{1,2}):(\d{2})(am|pm)', time_lower)
        if m:
            hh = int(m.group(1))
            mm = int(m.group(2))
            ampm = m.group(3)
            if ampm == 'pm' and hh < 12:
                hh += 12
            if ampm == 'am' and hh == 12:
                hh = 0
            event_dt = event_dt.replace(hour=hh, minute=mm, second=0)

    return event_dt, currency_text, impact_text, event_text, actual_text, forecast_text, previous_text


def parse_calendar_page_with_details(driver, start_date, end_date, output_csv, tzname):
    """
    Parses the loaded page (whether it's ?month=xxx.yyyy or ?range=...).
    For each row:
      - if day-breaker => set current_day
      - if event => extract main columns + open detail + parse detail + close detail => write to CSV
    Returns total number of events written.
    """
    rows = driver.find_elements(
        By.XPATH,
        '//table[contains(@class,"calendar__table")]//tr[contains(@class,"calendar__row")]'
    )

    current_day = None
    total_written = 0

    for row in rows:
        row_class = row.get_attribute("class")

        # Day-breaker => sets current_day
        if "calendar__row--day-breaker" in row_class:
            current_day = get_day_from_day_breaker(row, start_date, tzname)
            continue

        # If it's an event row but no current_day => skip
        if not current_day:
            continue

        # Filter out events outside [start_date, end_date]
        if current_day < start_date or current_day > end_date:
            continue

        try:
            # A) Extract main columns
            (
                event_dt,
                currency_text,
                impact_text,
                event_text,
                actual_text,
                forecast_text,
                previous_text
            ) = extract_basic_cells(row, current_day)

            # B) Click detail icon => parse detail => close it
            detail_str = ""
            try:
                open_link = row.find_element(By.XPATH, './/td[contains(@class,"calendar__detail")]/a')
                open_link.click()
                # parse the detail table
                detail_data = parse_detail_table(driver)
                detail_str = detail_data_to_string(detail_data)

                # If there's a separate "Close Detail" link => click it
                try:
                    close_link = row.find_element(By.XPATH, './/a[@title="Close Detail"]')
                    close_link.click()
                except Exception as e:
                    logger.error("Error in parse_calendar_page_with_details: %s", e, exc_info=True)
                    # if site toggles the same link or no close link found
                    pass

                time.sleep(1)  # small delay to ensure accordion closes
            except Exception as e:
                # can't open or parse detail
                pass
                logger.error("Error in parse_calendar_page_with_details (detail): %s", e, exc_info=True)
            # C) Write to CSV
            with open(output_csv, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    event_dt.isoformat(),
                    currency_text,
                    impact_text,
                    event_text,
                    actual_text,
                    forecast_text,
                    previous_text,
                    detail_str
                ])

            total_written += 1

        except Exception as e:
            logger.error("Error in parse_calendar_page_with_details: %s", e, exc_info=True)
            pass

    return total_written
