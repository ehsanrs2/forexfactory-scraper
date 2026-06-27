from __future__ import annotations

from datetime import datetime

from ..scraper import scrape_range_pandas


class ForexFactorySeleniumProvider:
    name = "forexfactory-selenium"

    def scrape_to_csv(self, start_date: datetime, end_date: datetime, output_csv: str, tzname: str, **kwargs):
        return scrape_range_pandas(
            start_date,
            end_date,
            output_csv,
            tzname=tzname,
            scrape_details=kwargs.get("scrape_details", False),
            impact_filter=kwargs.get("impact_filter"),
            keep_currencies=kwargs.get("keep_currencies"),
            driver_config=kwargs.get("driver_config"),
            page_timeout=kwargs.get("page_timeout", 120),
            retries=kwargs.get("retries", 2),
            manual_verification_timeout=kwargs.get("manual_verification_timeout", 0),
            dump_debug_artifacts=kwargs.get("dump_debug_artifacts", False),
        )
