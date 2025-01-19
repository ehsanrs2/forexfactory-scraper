# src/forexfactory/detail_parser.py

import re
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

MAX_RETRIES = 3

def parse_detail_table(driver):
    """
    Parses the detail table when detail row is expanded.
    Returns a dictionary of specs.
    """
    detail_data = {}
    for attempt in range(MAX_RETRIES):
        try:
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.XPATH,
                  '//tr[contains(@class,"calendar__details--detail")]//table[@class="calendarspecs"]'
                ))
            )
            all_tables = driver.find_elements(By.XPATH,
              '//tr[contains(@class,"calendar__details--detail")]//table[@class="calendarspecs"]'
            )
            if not all_tables:
                logger.warning("No detail_table found.")
                break
            detail_table = all_tables[-1]  # or the first if needed

            rows = detail_table.find_elements(By.XPATH, './tr')
            for r in rows:
                try:
                    spec_name = r.find_element(By.XPATH, './td[1]').text.strip()
                    spec_desc = r.find_element(By.XPATH, './td[2]').text.strip()
                    detail_data[spec_name] = spec_desc
                except NoSuchElementException as e:
                    pass
            break
        except TimeoutException as e:
            logger.error("Timeout in parse_detail_table: %s", e, exc_info=True)
            if attempt < MAX_RETRIES - 1:
                logger.info("Retrying parse_detail_table...")
            else:
                logger.error("Max retries reached.")
    return detail_data

def detail_data_to_string(detail_data: dict) -> str:
    """
    Convert dictionary from parse_detail_table() into a single string for CSV storage.
    Replace newlines or excessive whitespaces with space.
    """
    parts = []
    for k, v in detail_data.items():
        # Replacing all whitespace (including \n, \r, tabs) with a single space
        k_clean = re.sub(r'\s+', ' ', k).strip()
        v_clean = re.sub(r'\s+', ' ', v).strip()
        parts.append(f"{k_clean}: {v_clean}")
    return " | ".join(parts)
