import os
import unittest
from pathlib import Path
from datetime import datetime
from dateutil.tz import gettz
import pandas as pd
import pytest

from src.forexfactory.csv_util import CSV_COLUMNS
from src.forexfactory.normalizer import LEGACY_COLUMNS
from src.forexfactory.main import scrape_range_with_details


class TestFullScrape(unittest.TestCase):

    def setUp(self):
        self.output_file = "test_integration_output.csv"
        if os.path.exists(self.output_file):
            os.remove(self.output_file)

    def tearDown(self):
        if os.path.exists(self.output_file):
            os.remove(self.output_file)

    def test_cached_dataset_shape(self):
        cache_file = Path("forex_factory_cache.csv")
        if not cache_file.exists():
            self.skipTest("forex_factory_cache.csv is not available")

        df = pd.read_csv(cache_file, dtype=str, nrows=50)
        self.assertTrue(
            list(df.columns) == CSV_COLUMNS or list(df.columns) == LEGACY_COLUMNS,
            "Cached dataset should use either the legacy schema or the current normalized schema.",
        )
        self.assertGreater(len(df), 0)
        self.assertTrue(df["DateTime"].str.match(r"\d{4}-\d{2}-\d{2}T").all())

    @pytest.mark.skipif(
        os.environ.get("RUN_LIVE_SCRAPE") != "1",
        reason="Live scrape is disabled unless RUN_LIVE_SCRAPE=1",
    )
    def test_scrape_small_range(self):
        """
        یک تست انتها به انتها که یک بازه کوچک را اسکرپ می‌کند
        و بررسی می‌کند آیا فایل CSV تولید شده و حاوی سطر(های) مورد انتظار هست یا خیر.
        """
        tz = gettz("Asia/Tehran")
        start_dt = datetime(2025, 1, 5, tzinfo=tz)
        end_dt   = datetime(2025, 1, 5, tzinfo=tz)
        scrape_range_with_details(
            start_date=start_dt,
            end_date=end_dt,
            output_csv=self.output_file,
            tzname="Asia/Tehran"
        )

        # حالا بررسی می‌کنیم آیا فایل تولید شده و آیا حداقل یک رویداد ثبت شده است
        self.assertTrue(os.path.exists(self.output_file), "CSV output file should be created.")

        with open(self.output_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            self.assertGreater(len(lines), 1, "Should have at least one row of data (plus header).")

if __name__ == '__main__':
    unittest.main()
