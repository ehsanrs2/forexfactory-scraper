import time
import re
import logging
import pandas as pd
from datetime import datetime, timedelta
from dateutil.tz import gettz
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
)

from .csv_util import CSV_COLUMNS, ensure_csv_header, read_existing_data, write_data_to_csv, merge_new_data
from .detail_parser import parse_detail_table, detail_data_to_string

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def empty_calendar_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=CSV_COLUMNS)


def create_chrome_driver():
    import undetected_chromedriver as uc

    return uc.Chrome()


def get_day_from_day_breaker(row, fallback_date: datetime, tzname="Asia/Tehran"):
    """
    Parse Forex Factory day-breaker text like "Sun Jan 5" into a datetime.
    Returns None when the row does not contain a parseable day.
    """
    try:
        cell = row.find_element(By.XPATH, './/*[contains(@class,"calendar__date")]')
        text = cell.get_attribute("textContent") or ""
    except Exception:
        text = row.get_attribute("textContent") or ""

    match = re.search(r'\b([A-Za-z]{3})\s+(\d{1,2})\b', text)
    if not match:
        return None

    month_text, day_text = match.groups()
    try:
        parsed = datetime.strptime(
            f"{month_text} {int(day_text)} {fallback_date.year}",
            "%b %d %Y",
        )
    except ValueError:
        return None

    if fallback_date.month == 12 and parsed.month == 1:
        parsed = parsed.replace(year=fallback_date.year + 1)
    elif fallback_date.month == 1 and parsed.month == 12:
        parsed = parsed.replace(year=fallback_date.year - 1)

    return parsed.replace(tzinfo=gettz(tzname))


def parse_calendar_day(driver, the_date: datetime, scrape_details=False, existing_df=None) -> pd.DataFrame:
    """
    Scrape data for a single day (the_date) and return a DataFrame with columns:
      DateTime, Currency, Impact, Event, Actual, Forecast, Previous, Detail
    If scrape_details is False, skip detail parsing.

    Before fetching detail data from the Internet, this function checks if the record
    already exists (using existing_df) with a non-empty "Detail" field.
    """
    date_str = the_date.strftime('%b%d.%Y').lower()
    url = f"https://www.forexfactory.com/calendar?day={date_str}"
    logger.info(f"Scraping URL: {url}")
    try:
        driver.get(url)
    except Exception as e:
        logger.warning(f"Failed to load page for {the_date.date()}: {e}")
        return empty_calendar_frame()

    try:
        WebDriverWait(driver, 30).until(  # Increased wait time
            EC.visibility_of_element_located((By.XPATH, '//table[contains(@class,"calendar__table")]'))
        )
    except TimeoutException:
        logger.warning(f"Page did not load for day={the_date.date()}")
        return empty_calendar_frame()

    rows = driver.find_elements(By.XPATH, '//tr[contains(@class,"calendar__row")]')
    data_list = []
    current_day = the_date
    last_clock_time = None

    for row in rows:
        row_class = row.get_attribute("class")
        if "day-breaker" in row_class or "no-event" in row_class:
            continue

        # Parse the basic cells
        try:
            time_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__time")]')
            currency_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__currency")]')
            impact_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__impact")]')
            event_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__event")]')
            actual_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__actual")]')
            forecast_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__forecast")]')
            previous_el = row.find_element(By.XPATH, './/td[contains(@class,"calendar__previous")]')
        except NoSuchElementException:
            continue

        time_text = time_el.text.strip()
        currency_text = currency_el.text.strip()

        # Get impact text
        impact_text = ""
        try:
            impact_span = impact_el.find_element(By.XPATH, './/span')
            impact_text = impact_span.get_attribute("title") or ""
        except Exception:
            impact_text = impact_el.text.strip()

        event_text = event_el.text.strip()
        actual_text = actual_el.text.strip()
        forecast_text = forecast_el.text.strip()
        previous_text = previous_el.text.strip()

        # Determine event time based on text
        event_dt = current_day
        time_lower = time_text.lower()
        if not time_lower and last_clock_time is not None:
            event_dt = event_dt.replace(hour=last_clock_time[0], minute=last_clock_time[1], second=0)
        elif "day" in time_lower:
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
                last_clock_time = (hh, mm)

        # Compute a unique key for the event using DateTime, Currency, and Event
        unique_key = f"{event_dt.isoformat()}_{currency_text}_{event_text}"

        # Initialize detail string
        detail_str = ""
        if scrape_details:
            # If an existing CSV DataFrame is provided, check if this record exists and has detail.
            if existing_df is not None:
                matched = existing_df[
                    (existing_df["DateTime"] == event_dt.isoformat()) &
                    (existing_df["Currency"].str.strip() == currency_text) &
                    (existing_df["Event"].str.strip() == event_text)
                    ]
                if not matched.empty:
                    existing_detail = str(matched.iloc[0]["Detail"]).strip() if pd.notnull(
                        matched.iloc[0]["Detail"]) else ""
                    if existing_detail:
                        detail_str = existing_detail

            # If detail_str is still empty, then fetch detail from the Internet.
            if not detail_str:
                try:
                    open_link = row.find_element(By.XPATH, './/td[contains(@class,"calendar__detail")]/a')
                    driver.execute_script("arguments[0].scrollIntoView({behavior:'smooth',block:'center'});", open_link)
                    time.sleep(1)
                    open_link.click()
                    WebDriverWait(driver, 5).until(
                        EC.visibility_of_element_located(
                            (By.XPATH, '//tr[contains(@class,"calendar__details--detail")]'))
                    )
                    detail_data = parse_detail_table(driver)
                    detail_str = detail_data_to_string(detail_data)
                    try:
                        close_link = row.find_element(By.XPATH, './/a[@title="Close Detail"]')
                        close_link.click()
                    except Exception as e:
                        logger.debug("Could not close detail row for %s %s: %s", event_dt.isoformat(), event_text, e)
                except Exception as e:
                    logger.warning("Could not scrape detail for %s %s %s: %s", event_dt.isoformat(), currency_text, event_text, e)

        data_list.append({
            "DateTime": event_dt.isoformat(),
            "Currency": currency_text,
            "Impact": impact_text,
            "Event": event_text,
            "Actual": actual_text,
            "Forecast": forecast_text,
            "Previous": previous_text,
            "Detail": detail_str
        })

    return pd.DataFrame(data_list)


def scrape_day(driver, the_date: datetime, existing_df: pd.DataFrame, scrape_details=False) -> pd.DataFrame:
    """
    Re-scrape a single day, using existing_df to check for already-saved details.
    """
    df_day_new = parse_calendar_day(driver, the_date, scrape_details=scrape_details, existing_df=existing_df)
    return df_day_new


def scrape_range_pandas(from_date: datetime, to_date: datetime, output_csv: str, tzname="Asia/Tehran",
                        scrape_details=False, impact_filter=None, keep_currencies=None, driver_factory=create_chrome_driver):
    ensure_csv_header(output_csv)
    existing_df = read_existing_data(output_csv)

    driver = driver_factory()
    driver.set_window_size(1400, 1000)
    driver.set_page_load_timeout(300)  # Increase timeout to 5 minutes

    total_new = 0
    day_count = (to_date - from_date).days + 1
    logger.info(f"Scraping from {from_date.date()} to {to_date.date()} for {day_count} days.")

    try:
        current_day = from_date
        while current_day <= to_date:
            logger.info(f"Scraping day {current_day.strftime('%Y-%m-%d')}...")
            df_new = scrape_day(driver, current_day, existing_df, scrape_details=scrape_details)

            if impact_filter and not df_new.empty:
                df_new = df_new[df_new['Impact'].str.lower().str.contains('|'.join(impact_filter))]

            if keep_currencies and not df_new.empty:
                df_new = df_new[df_new['Currency'].isin(keep_currencies)]

            if not df_new.empty:
                merged_df = merge_new_data(existing_df, df_new)
                new_rows = len(merged_df) - len(existing_df)
                if new_rows > 0:
                    logger.info(f"Added/Updated {new_rows} rows for {current_day.date()}")
                existing_df = merged_df
                total_new += new_rows

                # Save updated data to CSV after processing the day's data.
                write_data_to_csv(existing_df, output_csv)

            current_day += timedelta(days=1)
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("Chrome WebDriver closed successfully.")
            except OSError as ose:
                # Ignore specific OSError during final cleanup (e.g., WinError 6)
                logger.debug(f"Ignored OSError during WebDriver quit: {ose}")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")
            finally:
                driver = None

    # Final save (if needed)
    write_data_to_csv(existing_df, output_csv)
    logger.info(f"Done. Total new/updated rows: {total_new}")
