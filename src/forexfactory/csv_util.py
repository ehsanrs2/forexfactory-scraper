# src/forexfactory/csv_util.py

import csv
import os
import pandas as pd
from datetime import datetime

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def ensure_csv_header(file_path: str):
    """
    Creates a CSV file with header if the file does not exist or is empty.
    The last column is 'Detail' for the calendarspecs data.
    """
    if not os.path.exists(file_path) or os.stat(file_path).st_size == 0:
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
                "Detail"
            ])

def read_existing_data(csv_file: str) -> pd.DataFrame:
    """
    Load existing data from CSV into a pandas DataFrame.
    """
    if not os.path.exists(csv_file) or os.stat(csv_file).st_size == 0:
        logger.info(f"CSV '{csv_file}' is empty or nonexistent.")
        columns = ["DateTime","Currency","Impact","Event","Actual","Forecast","Previous","Detail"]
        return pd.DataFrame(columns=columns)
    try:
        df = pd.read_csv(csv_file)
        return df
    except Exception as e:
        logger.error(f"Error reading CSV: {e}")
        columns = ["DateTime","Currency","Impact","Event","Actual","Forecast","Previous","Detail"]
        return pd.DataFrame(columns=columns)

def write_data_to_csv(df: pd.DataFrame, csv_file: str):
    """
    Write final merged data to CSV, overwriting it.
    """
    df.to_csv(csv_file, index=False)

def merge_new_data(existing_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge new data into existing data, updating rows for the same (DateTime, Currency, Event),
    and adding new rows if needed. You may change subset if you need more precise keys.
    """
    merged = pd.concat([existing_df, new_df], ignore_index=True)
    # Drop duplicates based on a subset of columns that identify a unique event
    merged.drop_duplicates(subset=["DateTime","Currency","Event"], keep="last", inplace=True)
    merged.reset_index(drop=True, inplace=True)
    return merged
