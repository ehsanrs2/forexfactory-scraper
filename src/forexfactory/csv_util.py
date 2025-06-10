# src/forexfactory/csv_util.py

import csv
import os
import pandas as pd
from datetime import datetime

import logging

#basicConfig is expected to be called in main.py
logger = logging.getLogger(__name__)

# Define the CSV columns
CSV_COLUMNS = ["DateTime", "Currency", "Impact", "Event", "Actual", "Forecast", "Previous", "Detail"]

def ensure_csv_header(csv_file: str):
    """
    Ensures that the specified CSV file exists and has the correct header row.
    If the file does not exist, it is created with the header defined by `CSV_COLUMNS`.

    Args:
        csv_file: Path to the CSV file.
    """
    if not os.path.exists(csv_file):
        df = pd.DataFrame(columns=CSV_COLUMNS)
        df.to_csv(csv_file, index=False)


def read_existing_data(csv_file: str) -> pd.DataFrame:
    """
    Reads data from the specified CSV file into a pandas DataFrame.

    It ensures that all columns defined in `CSV_COLUMNS` are present in the
    DataFrame, adding missing ones with empty strings. The 'DateTime' column
    is explicitly converted to a string type. If the file doesn't exist or an
    error occurs during reading, an empty DataFrame with the correct columns
    is returned.

    Args:
        csv_file: Path to the CSV file.

    Returns:
        A pandas DataFrame containing the data from the CSV file, or an empty
        DataFrame if the file does not exist or an error occurs.
    """
    if os.path.exists(csv_file):
        try:
            df = pd.read_csv(csv_file, dtype=str)
            # Ensure all columns exist in the DataFrame
            for col in CSV_COLUMNS:
                if col not in df.columns:
                    df[col] = ""  # Add missing columns with empty strings
            # Ensure DateTime column is string for consistent key generation
            if 'DateTime' in df.columns:
                df['DateTime'] = df['DateTime'].astype(str).str.strip()
            return df[CSV_COLUMNS]
        except Exception as e:
            logger.error(f"Error reading CSV: {e}", exc_info=True)
            return pd.DataFrame(columns=CSV_COLUMNS)
    else:
        return pd.DataFrame(columns=CSV_COLUMNS)

def write_data_to_csv(df: pd.DataFrame, csv_file: str):
    """
    Writes the given DataFrame to a CSV file, overwriting any existing file.
    The DataFrame is sorted by the "DateTime" column in ascending order before saving.

    Args:
        df: pandas DataFrame to write.
        csv_file: Path to the output CSV file.
    """
    # sort the data by DateTime
    df = df.sort_values(by="DateTime", ascending=True)
    df.to_csv(csv_file, index=False)


def merge_new_data(existing_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merges new data (`new_df`) into an existing DataFrame (`existing_df`).

    The merge logic is as follows:
    - A unique key is generated for each row based on "DateTime", "Currency", and "Event".
    - If a row from `new_df` (based on its unique key) is not in `existing_df`, it's added.
    - If a row from `new_df` exists in `existing_df`:
        - The "Detail" field is updated only if the existing "Detail" is empty and
          the new row provides a non-empty "Detail".
    - Other fields of existing rows are not modified.

    Args:
        existing_df: DataFrame with existing data.
        new_df: DataFrame with new data to merge.

    Returns:
        A new DataFrame containing the merged data, with columns ordered as per `CSV_COLUMNS`.
    """
    if existing_df.empty:
        return new_df

    # Helper function to create a consistent unique key for merging operations.
    def add_unique_key(df):
        df = df.copy()
        df['unique_key'] = (
            df["DateTime"].astype(str).str.strip() + "_" +  # DateTime is already str.strip()'d by read_existing_data
            df["Currency"].astype(str).str.strip() + "_" +
            df["Event"].astype(str).str.strip()
        )
        return df

    existing_df = add_unique_key(existing_df)
    new_df = add_unique_key(new_df)

    # Set unique_key as index for efficient lookup and updates.
    existing_df.set_index('unique_key', inplace=True)
    new_df.set_index('unique_key', inplace=True)

    # Accumulate new rows that are not present in existing_df
    new_rows_list = []
    for key, new_row in new_df.iterrows():
        if key in existing_df.index:
            # Retrieve the 'Detail' field for comparison
            existing_detail = str(existing_df.at[key, "Detail"]).strip() if pd.notna(existing_df.at[key, "Detail"]) else ""
            new_detail = str(new_row["Detail"]).strip() if pd.notna(new_row["Detail"]) else ""

            # Update 'Detail' only if it's missing in existing data and available in the new scrape.
            if not existing_detail and new_detail:
                existing_df.at[key, "Detail"] = new_detail
        else:
            new_rows_list.append(new_row)

    if new_rows_list:
        new_rows_df = pd.DataFrame(new_rows_list)
        # Concatenate new rows with the existing DataFrame
        existing_df = pd.concat([existing_df, new_rows_df])

    # Reset the index and ensure the DataFrame has the original column order
    merged_df = existing_df.reset_index(drop=True)
    merged_df = merged_df[CSV_COLUMNS]
    return merged_df
