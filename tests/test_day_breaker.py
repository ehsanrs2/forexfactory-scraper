# tests/test_day_breaker.py

import unittest
from unittest.mock import MagicMock
from datetime import datetime
from dateutil.tz import gettz
from src.forexfactory.scraper import get_day_from_day_breaker


class MockWebElement:
    """
    A minimal mock for Selenium WebElement that can respond to .find_element() and .get_attribute()
    """
    def __init__(self, text_content):
        self.text_content = text_content

    def find_element(self, by, locator):
        # returns self if the user wants .get_attribute("textContent")
        return self

    def get_attribute(self, attr):
        if attr == "textContent":
            return self.text_content
        return None

class TestDayBreakerWithMock(unittest.TestCase):

    def test_valid_daybreaker_row(self):
        tz = gettz("Asia/Tehran")
        fallback = datetime(2025, 1, 1, tzinfo=tz)
        # Suppose row's day-breaker cell text is "Sun Jan 5"
        row_mock = MockWebElement("Sun Jan 5")
        result = get_day_from_day_breaker(row_mock, fallback, "Asia/Tehran")
        self.assertEqual(result.year, 2025)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 5)

    def test_invalid_daybreaker_row(self):
        tz = gettz("Asia/Tehran")
        fallback = datetime(2025, 1, 1, tzinfo=tz)
        # Suppose row's day-breaker cell text is "????"
        row_mock = MockWebElement("????")
        result = get_day_from_day_breaker(row_mock, fallback, "Asia/Tehran")
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
