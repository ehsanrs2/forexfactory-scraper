# tests/test_urls.py

import unittest
from datetime import datetime
from dateutil.tz import gettz

# اگر تابع build_url_for_partial_range و build_url_for_full_month در main.py هستند:
#   from src.forexfactory.main import build_url_for_partial_range, build_url_for_full_month
#
# یا اگر بعداً به فایل جدا مثلاً date_logic.py منتقل کردید، آن را اصلاح کنید.
from src.forexfactory.date_logic import build_url_for_partial_range, build_url_for_full_month


class TestUrlBuilders(unittest.TestCase):

    def test_partial_range_simple(self):
        tz = gettz("Asia/Tehran")
        start_dt = datetime(2024, 12, 20, tzinfo=tz)
        end_dt   = datetime(2024, 12, 30, tzinfo=tz)
        result = build_url_for_partial_range(start_dt, end_dt)
        self.assertEqual(result, "range=dec20.2024-dec30.2024")

    def test_partial_range_same_day(self):
        tz = gettz("Asia/Tehran")
        dt = datetime(2025, 1, 5, tzinfo=tz)
        result = build_url_for_partial_range(dt, dt)
        # انتظار داریم "range=jan5.2025-jan5.2025"
        self.assertEqual(result, "range=jan5.2025-jan5.2025")

    def test_build_url_for_full_month(self):
        # مثلاً january 2025 => "month=jan.2025"
        result = build_url_for_full_month(2025, 1)
        self.assertEqual(result, "month=jan.2025")


if __name__ == '__main__':
    unittest.main()
