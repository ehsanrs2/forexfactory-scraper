import time
import re
import logging
import inspect
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
from dateutil.tz import gettz
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)

from .csv_util import CSV_COLUMNS, ensure_csv_header, read_existing_data, write_data_to_csv, merge_new_data
from .detail_parser import parse_detail_table, detail_data_to_string
from .driver import DriverConfig, create_chrome_driver
from .page_detection import detect_page_issue, normalize_text as _normalize_text

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

CALENDAR_SELECTORS = (
    "table.calendar__table",
    "tr.calendar__row",
    ".calendar__row",
    "[data-event-id]",
)
CALENDAR_SELECTOR = ", ".join(CALENDAR_SELECTORS)


class PageValidationError(RuntimeError):
    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason


def empty_calendar_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=CSV_COLUMNS)


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

    tz = gettz(tzname)
    return parsed.replace(tzinfo=tz)


def _page_snapshot(driver) -> tuple[str, str, str]:
    title = driver.title or ""
    source = driver.page_source or ""
    try:
        body = driver.find_element(By.TAG_NAME, "body").text
    except Exception:
        body = ""
    return title, body, source


def _has_calendar(driver) -> bool:
    return bool(driver.find_elements(By.CSS_SELECTOR, CALENDAR_SELECTOR))


def _wait_for_ready_and_body(driver, timeout: int):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") in {"interactive", "complete"}
    )
    WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.TAG_NAME, "body")))


def debug_artifact_paths(the_date: datetime, debug_dir: str = "debug") -> dict[str, Path]:
    base = Path(debug_dir) / f"forexfactory_{the_date.date().isoformat()}"
    return {
        "html": base.with_suffix(".html"),
        "png": base.with_suffix(".png"),
        "txt": base.with_suffix(".txt"),
    }


def dump_page_debug_artifacts(driver, the_date: datetime, reason: str, debug_dir: str = "debug") -> dict[str, Path]:
    paths = debug_artifact_paths(the_date, debug_dir)
    paths["html"].parent.mkdir(parents=True, exist_ok=True)
    title, body, source = _page_snapshot(driver)
    paths["html"].write_text(source, encoding="utf-8")
    paths["txt"].write_text(
        "\n".join([
            f"reason: {reason}",
            f"current_url: {driver.current_url}",
            f"title: {title}",
            "body_preview:",
            _normalize_text(body)[:2000],
            "",
        ]),
        encoding="utf-8",
    )
    try:
        driver.save_screenshot(str(paths["png"]))
    except Exception as exc:
        logger.warning("Could not save debug screenshot for %s: %s", the_date.date(), exc)
    logger.info("Saved ForexFactory debug artifacts for %s to %s", the_date.date(), paths["html"].parent)
    return paths


def _raise_page_validation(driver, the_date: datetime, reason: str, message: str, dump_debug_artifacts: bool):
    if dump_debug_artifacts:
        dump_page_debug_artifacts(driver, the_date, reason)
    raise PageValidationError(reason, message)


def _wait_for_manual_verification(driver, the_date: datetime, timeout: int, dump_debug_artifacts: bool) -> bool:
    logger.warning(
        "ForexFactory security verification page detected. Complete the verification in the opened browser; "
        "waiting up to %s seconds for the calendar to appear.",
        timeout,
    )
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _has_calendar(driver):
            logger.info("Calendar appeared after manual verification for %s.", the_date.date())
            return True
        title, body, source = _page_snapshot(driver)
        issue = detect_page_issue(title, body, source)
        if issue not in {"security_verification", "privacy_consent", None}:
            break
        time.sleep(2)

    if dump_debug_artifacts:
        dump_page_debug_artifacts(driver, the_date, "security_verification_timeout")
    return False


def _validate_calendar_page(
    driver,
    the_date: datetime,
    *,
    page_timeout: int,
    manual_verification_timeout: int,
    dump_debug_artifacts: bool,
):
    _wait_for_ready_and_body(driver, min(page_timeout, 30))
    title, body, source = _page_snapshot(driver)
    issue = detect_page_issue(title, body, source)
    if issue == "security_verification":
        if manual_verification_timeout > 0:
            if _wait_for_manual_verification(driver, the_date, manual_verification_timeout, dump_debug_artifacts):
                return
            raise PageValidationError(
                "security_verification",
                "ForexFactory security verification page detected and manual verification timed out. "
                "Run with --no-headless and --user-data-dir, complete the verification manually, then retry using the same profile.",
            )
        _raise_page_validation(
            driver,
            the_date,
            issue,
            "ForexFactory security verification page detected. The browser reached a verification page instead of the calendar. "
            "Run with --no-headless and --user-data-dir, complete the verification manually, then retry using the same profile.",
            dump_debug_artifacts,
        )
    if issue in {"privacy_consent", "empty_body"}:
        _raise_page_validation(
            driver,
            the_date,
            issue,
            f"ForexFactory returned a {issue.replace('_', ' ')} page instead of the calendar.",
            dump_debug_artifacts,
        )

    try:
        WebDriverWait(driver, page_timeout).until(lambda d: _has_calendar(d))
    except TimeoutException as exc:
        title, body, source = _page_snapshot(driver)
        issue = detect_page_issue(title, body, source)
        if issue == "security_verification":
            message = (
                "ForexFactory security verification page detected. The browser reached a verification page instead of the calendar. "
                "Run with --no-headless and --user-data-dir, complete the verification manually, then retry using the same profile."
            )
            _raise_page_validation(driver, the_date, issue, message, dump_debug_artifacts)
        reason = issue or "calendar_selector_missing"
        message = (
            f"ForexFactory calendar selectors were not found after page load. Tried: {CALENDAR_SELECTOR}. "
            "This usually means the calendar DOM changed, the page is blocked, or ForexFactory returned malformed HTML."
        )
        if dump_debug_artifacts:
            dump_page_debug_artifacts(driver, the_date, reason)
        raise PageValidationError(reason, message) from exc


def parse_calendar_day(
    driver,
    the_date: datetime,
    scrape_details=False,
    existing_df=None,
    *,
    page_timeout=30,
    tzname="Asia/Tehran",
    manual_verification_timeout=0,
    dump_debug_artifacts=False,
) -> pd.DataFrame:
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
    driver.get(url)

    _validate_calendar_page(
        driver,
        the_date,
        page_timeout=page_timeout,
        manual_verification_timeout=manual_verification_timeout,
        dump_debug_artifacts=dump_debug_artifacts,
    )

    rows = driver.find_elements(By.CSS_SELECTOR, 'tr.calendar__row')
    if not rows:
        if driver.find_elements(By.CSS_SELECTOR, "[data-event-id]"):
            message = (
                "ForexFactory exposed event containers but not tr.calendar__row rows. "
                "The calendar DOM likely changed and parser selectors need updating."
            )
        else:
            message = "No calendar rows found after calendar validation; page layout may have changed."
        _raise_page_validation(
            driver,
            the_date,
            "calendar_selector_missing",
            message,
            dump_debug_artifacts,
        )

    data_list = []
    current_day = the_date
    last_clock_time = None

    for row in rows:
        row_class = row.get_attribute("class") or ""
        parsed_day = get_day_from_day_breaker(row, current_day, tzname=tzname)
        if parsed_day is not None:
            current_day = parsed_day
            last_clock_time = None
        if "day-breaker" in row_class or "no-event" in row_class:
            continue

        # Parse the basic cells
        try:
            time_el = row.find_element(By.CSS_SELECTOR, 'td.calendar__time')
            currency_el = row.find_element(By.CSS_SELECTOR, 'td.calendar__currency')
            impact_el = row.find_element(By.CSS_SELECTOR, 'td.calendar__impact')
            event_el = row.find_element(By.CSS_SELECTOR, 'td.calendar__event')
            actual_el = row.find_element(By.CSS_SELECTOR, 'td.calendar__actual')
            forecast_el = row.find_element(By.CSS_SELECTOR, 'td.calendar__forecast')
            previous_el = row.find_element(By.CSS_SELECTOR, 'td.calendar__previous')
        except NoSuchElementException:
            logger.debug("Skipping malformed calendar row for %s: %s", the_date.date(), row_class)
            continue

        time_text = _normalize_text(time_el.text)
        currency_text = _normalize_text(currency_el.text)

        # Get impact text
        impact_text = ""
        try:
            impact_span = impact_el.find_element(By.XPATH, './/span')
            impact_text = _normalize_text(impact_span.get_attribute("title"))
        except Exception:
            impact_text = _normalize_text(impact_el.text)

        event_text = _normalize_text(event_el.text)
        actual_text = _normalize_text(actual_el.text)
        forecast_text = _normalize_text(forecast_el.text)
        previous_text = _normalize_text(previous_el.text)
        if not currency_text or not event_text:
            logger.debug("Skipping row with missing currency/event for %s", the_date.date())
            continue

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


def scrape_day(
    driver,
    the_date: datetime,
    existing_df: pd.DataFrame,
    scrape_details=False,
    *,
    page_timeout=30,
    tzname="Asia/Tehran",
    manual_verification_timeout=0,
    dump_debug_artifacts=False,
) -> pd.DataFrame:
    """
    Re-scrape a single day, using existing_df to check for already-saved details.
    """
    df_day_new = parse_calendar_day(
        driver,
        the_date,
        scrape_details=scrape_details,
        existing_df=existing_df,
        page_timeout=page_timeout,
        tzname=tzname,
        manual_verification_timeout=manual_verification_timeout,
        dump_debug_artifacts=dump_debug_artifacts,
    )
    return df_day_new


def _create_driver(driver_factory, driver_config):
    parameters = inspect.signature(driver_factory).parameters
    if not parameters:
        if driver_config is not None:
            logger.debug("Driver factory does not accept DriverConfig; calling without arguments")
        return driver_factory()
    return driver_factory(driver_config)


def scrape_range_pandas(from_date: datetime, to_date: datetime, output_csv: str, tzname="Asia/Tehran",
                        scrape_details=False, impact_filter=None, keep_currencies=None,
                        driver_factory=create_chrome_driver, driver_config: DriverConfig | None = None,
                        page_timeout=120, retries=2, manual_verification_timeout=0,
                        dump_debug_artifacts=False):
    ensure_csv_header(output_csv)
    existing_df = read_existing_data(output_csv)

    driver = _create_driver(driver_factory, driver_config)
    driver.set_window_size(1400, 1000)
    driver.set_page_load_timeout(page_timeout)

    total_new = 0
    day_count = (to_date - from_date).days + 1
    logger.info(f"Scraping from {from_date.date()} to {to_date.date()} for {day_count} days.")

    try:
        current_day = from_date
        while current_day <= to_date:
            logger.info("Scraping day %s...", current_day.strftime('%Y-%m-%d'))
            df_new = empty_calendar_frame()
            for attempt in range(1, retries + 2):
                try:
                    df_new = scrape_day(
                        driver,
                        current_day,
                        existing_df,
                        scrape_details=scrape_details,
                        page_timeout=min(page_timeout, 60),
                        tzname=tzname,
                        manual_verification_timeout=manual_verification_timeout,
                        dump_debug_artifacts=dump_debug_artifacts,
                    )
                    break
                except PageValidationError:
                    raise
                except (TimeoutException, WebDriverException) as exc:
                    if attempt > retries:
                        logger.error("Failed to scrape %s after %s attempt(s): %s", current_day.date(), attempt, exc)
                        break
                    delay = min(2 ** attempt, 30)
                    logger.warning(
                        "Failed to scrape %s on attempt %s/%s: %s; retrying in %ss",
                        current_day.date(),
                        attempt,
                        retries + 1,
                        exc,
                        delay,
                    )
                    time.sleep(delay)

            if impact_filter and not df_new.empty:
                impact_pattern = '|'.join(re.escape(i) for i in impact_filter)
                df_new = df_new[df_new['Impact'].fillna('').str.lower().str.contains(impact_pattern)]

            if keep_currencies and not df_new.empty:
                keep = {c.upper() for c in keep_currencies}
                df_new = df_new[df_new['Currency'].str.upper().isin(keep)]

            if not df_new.empty:
                merged_df = merge_new_data(existing_df, df_new)
                new_rows = len(merged_df) - len(existing_df)
                if new_rows > 0:
                    logger.info("Added/updated %s rows for %s", new_rows, current_day.date())
                existing_df = merged_df
                total_new += new_rows

                # Save updated data to CSV after processing the day's data.
                write_data_to_csv(existing_df, output_csv)
            else:
                logger.info("No rows collected for %s", current_day.date())

            current_day += timedelta(days=1)
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("Chrome WebDriver closed successfully.")
            except OSError as ose:
                # Ignore specific OSError during final cleanup (e.g., WinError 6)
                logger.debug("Ignored OSError during WebDriver quit: %s", ose)
            except Exception as e:
                logger.error("Error closing WebDriver: %s", e)
            finally:
                driver = None

    # Final save (if needed)
    write_data_to_csv(existing_df, output_csv)
    logger.info("Done. Total new/updated rows: %s", total_new)
