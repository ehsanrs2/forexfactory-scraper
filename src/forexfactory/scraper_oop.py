# src/forexfactory/scraper_oop.py

from datetime import datetime, timedelta
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dateutil.tz import gettz

from .date_logic import build_url_for_partial_range, build_url_for_full_month
from .detail_parser import parse_detail_table, detail_data_to_string
from .csv_util import ensure_csv_header   # اگر در فایل جدا دارید؛ یا همان ensure_csv_header
# همچنین می‌توانید تابع extract_basic_cells و get_day_from_day_breaker را اینجا بیاورید

class ForexFactoryScraper:
    def __init__(self, start_date: datetime, end_date: datetime, tzname: str = "Asia/Tehran",
                 output_csv: str = "forex_factory_details.csv"):
        """
        Constructor. Initializes the Selenium driver, sets up config.
        """
        self.start_date = start_date
        self.end_date = end_date
        self.tzname = tzname
        self.output_csv = output_csv

        # build driver
        options = uc.ChromeOptions()
        self.driver = uc.Chrome(options=options)
        self.driver.set_window_size(1400, 1000)

    def close(self):
        """Gracefully close the driver session."""
        self.driver.quit()

    def scrape(self):
        """
        Main method to scrape from start_date to end_date (month by month).
        """
        ensure_csv_header(self.output_csv)

        current = datetime(self.start_date.year, self.start_date.month, 1, tzinfo=self.start_date.tzinfo)
        boundary = self.end_date.replace(day=1) + timedelta(days=32)
        boundary = datetime(boundary.year, boundary.month, 1, tzinfo=self.end_date.tzinfo)

        total_events = 0
        try:
            while current < boundary:
                start_of_m = current
                next_candidate = start_of_m.replace(day=28) + timedelta(days=4)
                end_of_m = datetime(next_candidate.year, next_candidate.month, 1, tzinfo=current.tzinfo) - timedelta(days=1)

                partial_start = max(self.start_date, start_of_m)
                partial_end   = min(self.end_date, end_of_m)

                if partial_start.day == 1 and partial_end.day == end_of_m.day:
                    # full month
                    url_param = build_url_for_full_month(current.year, current.month)
                else:
                    # partial
                    url_param = build_url_for_partial_range(partial_start, partial_end)

                url = "https://www.forexfactory.com/calendar?" + url_param
                self.driver.get(url)
                # short wait
                import time
                time.sleep(2)

                count = self.parse_calendar_page(partial_start, partial_end)
                total_events += count

                # next month
                next_month_candidate = current + timedelta(days=32)
                current = datetime(next_month_candidate.year, next_month_candidate.month, 1, tzinfo=current.tzinfo)
        finally:
            self.close()
        print(f"[LOG] Done. Total events with details: {total_events}")


    def parse_calendar_page(self, start_dt: datetime, end_dt: datetime) -> int:
        """
        Similar to parse_calendar_page_with_details in the old approach, but now it's a method.
        """
        rows = self.driver.find_elements(
            By.XPATH,
            '//table[contains(@class,"calendar__table")]//tr[contains(@class,"calendar__row")]'
        )

        current_day = None
        total_written = 0

        for row in rows:
            row_class = row.get_attribute("class")
            if "calendar__row--day-breaker" in row_class:
                # set current_day
                current_day = self.get_day_from_day_breaker(row, start_dt)
                continue

            # skip if no current_day
            if not current_day:
                continue

            # filter out events outside [start_dt, end_dt]
            if current_day < start_dt or current_day > end_dt:
                continue

            try:
                # extract cells
                event_dt, currency_text, impact_text, event_text, actual_text, forecast_text, previous_text = \
                    self.extract_basic_cells(row, current_day)

                # detail
                detail_str = ""
                try:
                    open_link = row.find_element(By.XPATH, './/td[contains(@class,"calendar__detail")]/a')
                    open_link.click()
                    detail_data = parse_detail_table(self.driver)
                    detail_str = detail_data_to_string(detail_data)

                    # close detail if found
                    try:
                        close_link = row.find_element(By.XPATH, './/a[@title="Close Detail"]')
                        close_link.click()
                    except:
                        pass
                    import time
                    time.sleep(1)
                except:
                    pass

                # write CSV
                with open(self.output_csv, 'a', newline='', encoding='utf-8') as f:
                    import csv
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

    def get_day_from_day_breaker(self, row, fallback_date: datetime):
        """
        Similar to previous get_day_from_day_breaker but instance-based now.
        """
        from dateutil.tz import gettz
        local_tz = gettz(self.tzname)
        day_breaker_cell = row.find_element(By.XPATH, './/td[contains(@class,"calendar__cell")]')
        raw_text = (day_breaker_cell.get_attribute("textContent") or "").strip()
        parts = raw_text.split()
        if len(parts) >= 2:
            month_abbr = parts[-2]
            day_str = parts[-1]
            guess_year = fallback_date.year
            from datetime import datetime
            try:
                dt_str = f"{month_abbr}{day_str} {guess_year}"
                parsed_day = datetime.strptime(dt_str, "%b%d %Y").replace(tzinfo=local_tz)
                return parsed_day
            except:
                return None
        return None

    def extract_basic_cells(self, row, current_day: datetime):
        """
        Moved from the old extract_basic_cells function.
        This is now an instance method.
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

        event_dt = current_day
        time_lower = time_text.lower()
        import re
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
