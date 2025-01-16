# src/forexfactory/scraper.py

import time
import re
import logging
import csv
from datetime import datetime
from dateutil.tz import gettz
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
    StaleElementReferenceException
)

from .detail_parser import parse_detail_table, detail_data_to_string
from .csv_util import ensure_csv_header


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def get_day_from_day_breaker(row, fallback_date: datetime, tzname: str):
    local_tz = gettz(tzname)
    try:
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
            except ValueError as ve:
                logger.error(f"Date parsing error: {ve} for text: {dt_str}")
                return None
    except NoSuchElementException as e:
        logger.warning(f"Day breaker cell not found in row: {row}. Error: {e}")
    return None

def extract_basic_cells(row, current_day: datetime):
    """
    Extracts main columns from an event row.
    """
    try:
        time_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__time")]')
        currency_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__currency")]')
        impact_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__impact")]')
        event_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__event")]')
        actual_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__actual")]')
        forecast_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__forecast")]')
        previous_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__previous")]')
    except NoSuchElementException as e:
        logger.warning(f"Missing one or more required cells in row: {row}. Error: {e}")
        raise


    time_text = time_el.text.strip()
    currency_text = currency_el.text.strip()

    impact_text = ""
    try:
        impact_span = impact_el.find_element(By.XPATH, './/span')
        impact_text = impact_span.get_attribute("title") or ""
    except NoSuchElementException:
        impact_text = impact_el.text.strip()

    event_text = event_el.text.strip()
    actual_text = actual_el.text.strip()
    forecast_text = forecast_el.text.strip()
    previous_text = previous_el.text.strip()


    event_dt = current_day
    time_lower = time_text.lower()
    if "day" in time_lower:
        event_dt = event_dt.replace(hour=23, minute=59, second=59)
    elif "data" in time_lower:
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

    return (event_dt, currency_text, impact_text, event_text,
            actual_text, forecast_text, previous_text)

def parse_calendar_page_with_details(driver, start_date, end_date, output_csv, tzname,scrape_details=False):
    """
    Parses the loaded page (month=... or range=...).
    Extracts events and their details, then writes them to CSV.
    """
    try:

        WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((By.XPATH, '//table[contains(@class,"calendar__table")]'))
        )
    except TimeoutException:
        logger.error("Calendar table did not load in time.")
        return 0


    rows = driver.find_elements(
        By.XPATH,
        '//tr[contains(@class,"calendar__row")]'
    )

    logger.info(f"Found {len(rows)} total rows.")

    if len(rows) == 0:
        logger.warning("No rows found with the current XPath.")
        return 0

    events = []
    current_day = None


    for row in rows:
        try:
            row_class = row.get_attribute("class")


            if "calendar__row--day-breaker" in row_class:
                current_day = get_day_from_day_breaker(row, start_date, tzname)
                if current_day:
                    logger.info(f"Updated current_day to {current_day}")
                else:
                    logger.warning(f"Failed to parse date from day-breaker row: {row}")
                continue


            event_id = row.get_attribute("data-event-id")
            if event_id:
                if not current_day:
                    logger.warning(f"No current_day set for event row: {row}")
                    continue

                if current_day < start_date or current_day > end_date:
                    logger.info(f"Skipping row for date {current_day} as it's outside the range.")
                    continue

                events.append({'event_id': event_id, 'current_day': current_day})
        except StaleElementReferenceException as e:
            logger.warning(f"StaleElementReferenceException while collecting rows. Error: {e}")
            continue
        except Exception as e:
            logger.exception(f"Unexpected error while collecting rows: {e}")
            continue

    logger.info(f"Found {len(events)} events to process.")

    total_written = 0


    for event in events:
        event_id = event['event_id']
        current_day = event['current_day']

        try:

            event_row = driver.find_element(By.XPATH, f'//tr[@data-event-id="{event_id}"]')


            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", event_row)
            time.sleep(1)


            open_link = WebDriverWait(event_row, 10).until(
                EC.element_to_be_clickable((By.XPATH, './/td[contains(@class,"calendar__detail")]/a'))
            )
            try:
                open_link.click()
            except ElementClickInterceptedException as e:
                logger.warning(f"ElementClickInterceptedException when clicking detail for event_id {event_id}. Error: {e}")

                driver.execute_script("arguments[0].click();", open_link)


            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, '//tr[contains(@class,"calendar__details--detail")]'))
            )


            detail_data = parse_detail_table(driver)
            detail_str = detail_data_to_string(detail_data)

            try:
                close_link = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, './/a[@title="Close Detail"]'))
                )
                try:
                    close_link.click()
                except ElementClickInterceptedException as e:
                    logger.warning(f"ElementClickInterceptedException when closing detail for event_id {event_id}. Error: {e}")
                    driver.execute_script("arguments[0].click();", close_link)

                WebDriverWait(driver, 5).until(
                    EC.invisibility_of_element_located((By.XPATH, '//tr[contains(@class,"calendar__details--detail")]'))
                )
            except TimeoutException:
                logger.warning(f"Close link not found or not clickable for event_id {event_id}")
            except Exception as e:
                logger.exception(f"Unexpected error while closing detail for event_id {event_id}. Error: {e}")


            (event_dt, currency_text, impact_text,
             event_text, actual_text, forecast_text,
             previous_text) = extract_basic_cells(event_row, current_day)


            ensure_csv_header(output_csv)

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

        except NoSuchElementException as e:
            logger.warning(f"Could not find event row with event_id {event_id}. Error: {e}")
            continue
        except TimeoutException as e:
            logger.warning(f"Timeout while processing event_id {event_id}. Error: {e}")
            continue
        except StaleElementReferenceException as e:
            logger.warning(f"StaleElementReferenceException for event_id {event_id}. Error: {e}")
            continue
        except Exception as e:
            logger.exception(f"Unexpected error while processing event_id {event_id}. Error: {e}")
            continue

    logger.info(f"Total events written: {total_written}")
    return total_written
