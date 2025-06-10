# src/forexfactory/scraper.py

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
    ElementClickInterceptedException,
    StaleElementReferenceException
)
import undetected_chromedriver as uc
from pyvirtualdisplay import Display

from .csv_util import ensure_csv_header, read_existing_data, write_data_to_csv, merge_new_data
from .detail_parser import parse_detail_table, detail_data_to_string

#basicConfig is expected to be called in main.py
logger = logging.getLogger(__name__)


def _parse_event_time(time_text: str, current_day: datetime) -> datetime:
    """
    Helper function to parse event time string (e.g., "10:30am", "All Day")
    and return a datetime object. 'All Day' or 'Tentative' events are set
    to the beginning of the day (00:00:01) for consistent sorting.
    """
    event_dt = current_day
    time_lower = time_text.lower()
    if "day" in time_lower:
        event_dt = event_dt.replace(hour=23, minute=59, second=59)
    elif "data" in time_lower:  # Typically "All Day" or "Tentative"
        event_dt = event_dt.replace(hour=0, minute=0, second=1) # Mark as start of day for sorting
    else:
        m = re.match(r'(\d{1,2}):(\d{2})(am|pm)', time_lower)
        if m:
            hh = int(m.group(1))
            mm = int(m.group(2))
            ampm = m.group(3)
            if ampm == 'pm' and hh < 12:
                hh += 12
            if ampm == 'am' and hh == 12:  # Midnight case
                hh = 0
            event_dt = event_dt.replace(hour=hh, minute=mm, second=0)
    return event_dt


def _parse_impact_text(impact_el) -> str:
    """Helper function to parse impact text from impact WebElement."""
    impact_text = ""
    try:
        # Try to get impact from title attribute of a span inside
        impact_span = impact_el.find_element(By.XPATH, './/span')
        impact_text = impact_span.get_attribute("title") or ""
    except NoSuchElementException: # If span not found, use the text of the td
        impact_text = impact_el.text.strip()
    except Exception as e: # Catch any other exception during impact parsing
        logger.debug(f"Could not parse impact text: {e}")
        impact_text = impact_el.text.strip() # Fallback
    return impact_text


def parse_calendar_day(driver, the_date: datetime, scrape_details=False, existing_df=None) -> pd.DataFrame:
    """
    Scrapes economic event data for a single specified day from Forex Factory.

    Args:
        driver: Selenium WebDriver instance.
        the_date: datetime object representing the target day to scrape. The date part
                  is used for navigation; time components are ignored as event times
                  are parsed from the page content relative to this day.
        scrape_details: Boolean flag to enable scraping of detailed event descriptions.
                        Defaults to False.
        existing_df: Optional pandas DataFrame containing previously scraped data.
                     Used to avoid re-scraping details if already present.

    Returns:
        A pandas DataFrame containing the scraped event data with columns:
        "DateTime", "Currency", "Impact", "Event", "Actual", "Forecast",
        "Previous", "Detail". Returns an empty DataFrame if the page fails to load
        or no events are found.
    """
    date_str = the_date.strftime('%b%d.%Y').lower() # Format for Forex Factory URL
    url = f"https://www.forexfactory.com/calendar?day={date_str}"
    logger.info(f"Scraping URL: {url}")
    driver.get(url)

    try:
        WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.XPATH, '//table[contains(@class,"calendar__table")]'))
        )
    except TimeoutException:
        logger.warning(f"Page did not load for day={the_date.date()}")
        return pd.DataFrame(
            columns=["DateTime", "Currency", "Impact", "Event", "Actual", "Forecast", "Previous", "Detail"])

    rows = driver.find_elements(By.XPATH, '//tr[contains(@class,"calendar__row")]')
    data_list = []
    current_day = the_date

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
        impact_text = _parse_impact_text(impact_el)

        event_text = event_el.text.strip()
        actual_text = actual_el.text.strip()
        forecast_text = forecast_el.text.strip()
        previous_text = previous_el.text.strip()

        # Determine event time using helper function
        event_dt = _parse_event_time(time_text, current_day)

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
                    except Exception: # General exception during close
                        logger.debug(f"Minor issue closing detail for event on {event_dt.strftime('%Y-%m-%d %H:%M:%S')} for {currency_text} - {event_text}.", exc_info=True)
                        pass # Continue if closing detail fails
                except (TimeoutException, ElementClickInterceptedException) as e:
                    logger.warning(f"Could not open/parse details for event on {event_dt.strftime('%Y-%m-%d %H:%M:%S')} for {currency_text} - {event_text} due to {type(e).__name__}.", exc_info=True)
                except Exception as e: # Catch any other exception during detail scraping
                    logger.error(f"Failed to scrape details for event on {event_dt.strftime('%Y-%m-%d %H:%M:%S')} for {currency_text} - {event_text}.", exc_info=True)
                    # detail_str remains empty or as previously set

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
    Re-scrapes data for a single specified day.

    This function primarily serves as a wrapper around `parse_calendar_day`,
    facilitating the use of an existing DataFrame to potentially skip re-scraping
    event details if they have been previously fetched.

    Args:
        driver: Selenium WebDriver instance.
        the_date: datetime object for the target day.
        existing_df: pandas DataFrame of existing data to check against.
        scrape_details: Boolean, passed to `parse_calendar_day`.

    Returns:
        A pandas DataFrame with the day's event data.
    """
    df_day_new = parse_calendar_day(driver, the_date, scrape_details=scrape_details, existing_df=existing_df)
    return df_day_new


def scrape_range_pandas(from_date: datetime, to_date: datetime, output_csv: str, tzname: str,
                        scrape_details=False):
    """
    Scrapes Forex Factory calendar data for a specified date range and saves it to a CSV file.

    It iterates through each day in the range, scrapes data using `scrape_day`,
    merges it with existing data from the CSV, and writes the updated data back.
    This function manages the WebDriver instance lifecycle.

    Args:
        from_date: datetime object, the start date of the scraping range (inclusive).
        to_date: datetime object, the end date of the scraping range (inclusive).
        output_csv: String, path to the CSV file for storing scraped data.
        tzname: String, the timezone name (e.g., "Asia/Tehran", "America/New_York")
                to ensure correct interpretation of dates. This timezone is primarily
                used for logging and ensuring date boundaries, not for converting
                event times themselves which are based on Forex Factory's display.
        scrape_details: Boolean, whether to scrape detailed event descriptions.
                        Defaults to False.
    """
    # csv_util is imported here to avoid circular dependency if it also imported scraper functions
    from .csv_util import ensure_csv_header, read_existing_data, merge_new_data, write_data_to_csv

    ensure_csv_header(output_csv)
    existing_df = read_existing_data(output_csv)

    display = None
    driver = None
    total_new = 0 # Initialize total_new here to ensure it's always defined
    try:
        display = Display(visible=0, size=(1400, 1000))
        display.start()
        logger.info("Virtual display started.")

        # Configure Chrome options for headless-like behavior within Xvfb
        chrome_options = uc.ChromeOptions()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--remote-debugging-port=9222') # May or may not help
        chrome_options.add_argument('--disable-setuid-sandbox')
        # chrome_options.add_argument('--headless') # uc might handle this, or Xvfb makes it unnecessary

        driver = uc.Chrome(
            browser_executable_path="/usr/bin/google-chrome-stable",
            options=chrome_options
        )
        # It's good practice to set window size if the virtual display has one,
        # or if specific layout is expected by the site.
        # driver.set_window_size(1400, 1000) # Already set by Display size

        # total_new = 0 # Moved outside the try block
        day_count = (to_date - from_date).days + 1
        logger.info(f"Scraping from {from_date.date()} to {to_date.date()} for {day_count} days.")

        current_day = from_date
        while current_day <= to_date:
            logger.info(f"Scraping day {current_day.strftime('%Y-%m-%d')}...")
            # Ensure driver is available here, or handle if it failed to init
            if not driver:
                logger.error("WebDriver not initialized, cannot scrape.")
                break
            df_new = scrape_day(driver, current_day, existing_df, scrape_details=scrape_details)

            if not df_new.empty:
                merged_df = merge_new_data(existing_df, df_new)
                new_rows = len(merged_df) - len(existing_df)
                if new_rows > 0:
                    logger.info(f"Added/Updated {new_rows} rows for {current_day.date()}")
                existing_df = merged_df # existing_df gets updated with merged data
                total_new += new_rows

                # Save updated data to CSV after processing the day's data.
                write_data_to_csv(existing_df, output_csv)

            current_day += timedelta(days=1)
        # The loop and its logic are now inside the main try block

    except Exception as e:
        logger.error(f"An error occurred during the scraping process: {e}", exc_info=True)
        # existing_df might be partially updated, decide if to save or not
        # For now, we will save what we have before the error, as done in the finally block.

    finally:
        if driver:
            try:
                driver.quit()
                logger.info("Chrome WebDriver closed successfully.")
            except OSError as ose:
                logger.debug(f"Ignored OSError during WebDriver quit: {ose}")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")
            finally:
                driver = None # Ensure driver is None even if quit fails

        if display:
            try:
                display.stop()
                logger.info("Virtual display stopped.")
            except Exception as e:
                logger.error(f"Error stopping virtual display: {e}")
            finally:
                display = None


    # Final save (if needed, though it's saved per day too)
    if not existing_df.empty: # ensure existing_df is defined
        write_data_to_csv(existing_df, output_csv)
    logger.info(f"Done. Total new/updated rows: {total_new}")
