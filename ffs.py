import csv
import time
import re
from datetime import datetime, timedelta
from dateutil.tz import gettz
import undetected_chromedriver as uc

from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def ensure_csv_header(file_path: str):
    """
    Creates a CSV file with header if the file does not exist or is empty.
    The last column is 'Detail' for the calendarspecs data.
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


def build_url_for_partial_range(start_dt: datetime, end_dt: datetime) -> str:
    """
    Builds a ForexFactory calendar param of the form: ?range=dec20.2024-dec30.2024
    """
    def ff_str(d: datetime):
        return d.strftime('%b').lower() + str(d.day) + '.' + str(d.year)

    return "range=" + ff_str(start_dt) + "-" + ff_str(end_dt)


def build_url_for_full_month(year: int, month: int) -> str:
    """
    Builds a param like: ?month=jan.2025
    """
    dt = datetime(year, month, 1)
    m_str = dt.strftime('%b').lower()  # e.g. "jan"
    y_str = dt.strftime('%Y')          # e.g. "2025"
    return "month=" + m_str + "." + y_str


def parse_detail_table(driver):
    detail_data = {}
    try:
        print("[DEBUG] Wait for at least one calendarspecs table to appear...")
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH,
              '//tr[contains(@class,"calendar__details--detail")]//table[@class="calendarspecs"]'
            ))
        )

        # find all tables
        all_tables = driver.find_elements(By.XPATH,
          '//tr[contains(@class,"calendar__details--detail")]//table[@class="calendarspecs"]'
        )
        print("[DEBUG] Found", len(all_tables), "tables with class=calendarspecs.")

        # pick the last table or second table
        if len(all_tables) >= 2:
            detail_table = all_tables[-1]  # or all_tables[1]
        else:
            detail_table = all_tables[0]

        outer_html = detail_table.get_attribute("outerHTML")
        print("[DEBUG] detail_table outerHTML =>", outer_html)

        rows = detail_table.find_elements(By.XPATH, './tr')
        print("[DEBUG] Found", len(rows), "rows in detail table.")

        for r in rows:
            try:
                spec_name = r.find_element(By.XPATH, './td[1]').text.strip()
                spec_desc = r.find_element(By.XPATH, './td[2]').text.strip()
                detail_data[spec_name] = spec_desc
                print(f"[DEBUG] spec: {spec_name} => {spec_desc}")
            except:
                pass

    except Exception as e:
        print("[ERROR] parse_detail_table =>", e)

    return detail_data


def detail_data_to_string(detail_data: dict) -> str:
    """
    Converts the dictionary from parse_detail_table() into a single string for CSV storage.
    Replaces any newline with a space to avoid multi-line CSV fields.
    """
    parts = []
    for k, v in detail_data.items():
        # Replace all newlines with a space or some other delimiter
        v_clean = v.replace('\n', ' ').replace('\r', ' ')
        # If k also might contain newlines, do the same for k:
        k_clean = k.replace('\n', ' ').replace('\r', ' ')

        parts.append(f"{k_clean}: {v_clean}")
    return " | ".join(parts)


def get_day_from_day_breaker(row, fallback_date: datetime, tzname: str):
    """
    Extracts date from a day-breaker row (e.g. "Sun Jan 5").
    If the site doesn't specify a year, we use fallback_date.year.
    Returns a datetime object with hour=0, or None on error.
    """
    local_tz = gettz(tzname)
    day_breaker_cell = row.find_element(By.XPATH, './/td[contains(@class,"calendar__cell")]')
    raw_text = day_breaker_cell.get_attribute("textContent") or ""
    raw_text = raw_text.strip()
    # e.g. "Sun Jan 5"
    parts = raw_text.split()
    if len(parts) >= 2:
        month_abbr = parts[-2]
        day_str = parts[-1]
        guess_year = fallback_date.year
        dt_str = f"{month_abbr}{day_str} {guess_year}"  # e.g. "Jan5 2025"
        try:
            parsed_day = datetime.strptime(dt_str, "%b%d %Y").replace(tzinfo=local_tz)
            return parsed_day
        except:
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
    except:
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
                except:
                    # if site toggles the same link or no close link found
                    pass

                time.sleep(1)  # small delay to ensure accordion closes
            except Exception as e:
                # can't open or parse detail
                pass

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

        except:
            pass

    return total_written


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

    print(f"[LOG] Done. Total events with details: {total_events}")




if __name__ == "__main__":
    tz = gettz("Asia/Tehran")
    # Example usage: from 2025-01-01 to 2025-01-10
    start_dt = datetime(2025, 1, 5, tzinfo=tz)
    end_dt   = datetime(2025, 1, 5, tzinfo=tz)

    scrape_range_with_details(
        start_date=start_dt,
        end_date=end_dt,
        output_csv="forex_factory_details.csv",
        tzname="Asia/Tehran"
    )



# "https://www.forexfactory.com/calendar?day=jan5.2025"