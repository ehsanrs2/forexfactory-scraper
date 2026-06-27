import logging

import pandas as pd

from .csv_util import ensure_csv_header, read_existing_data, merge_new_data, write_data_to_csv
from .providers import EconomicCalendarProvider, ForexFactoryHtmlProvider

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def scrape_incremental(
    from_date,
    to_date,
    output_csv,
    tzname="Asia/Tehran",
    scrape_details=False,
    impact_filter=None,
    keep_currencies=None,
    provider: EconomicCalendarProvider | None = None,
    provider_kwargs: dict | None = None,
):
    """
    Fetch a requested date range with the chosen provider and merge it into the CSV cache.
    The merge is idempotent and preserves historical rows outside the requested range.
    """
    ensure_csv_header(output_csv)
    existing_df = read_existing_data(output_csv)
    provider = provider or ForexFactoryHtmlProvider()
    provider_kwargs = dict(provider_kwargs or {})
    provider_kwargs.setdefault("scrape_details", scrape_details)

    events = provider.fetch_events(from_date, to_date, tzname, **provider_kwargs)
    df_new = pd.DataFrame(events)
    if df_new.empty:
        logger.info("Provider returned no events; CSV unchanged.")
        write_data_to_csv(existing_df, output_csv)
        return

    if impact_filter and "impact" in df_new.columns:
        import re

        pattern = "|".join(re.escape(i) for i in impact_filter)
        df_new = df_new[df_new["impact"].fillna("").astype(str).str.lower().str.contains(pattern, regex=True)]
    if keep_currencies and "currency" in df_new.columns:
        keep = {currency.upper() for currency in keep_currencies}
        df_new = df_new[df_new["currency"].fillna("").astype(str).str.upper().isin(keep)]

    merged_df = merge_new_data(existing_df, df_new)
    write_data_to_csv(merged_df, output_csv)
    logger.info("Done. Added/updated %s provider rows.", max(len(merged_df) - len(existing_df), 0))
