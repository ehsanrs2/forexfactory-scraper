# src/forexfactory/csv_util.py

import csv
from datetime import datetime


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

def get_last_datetime_from_csv(file_path: str):
    """
    Reads the CSV file from the end and returns the last event's datetime (as a datetime object).
    If file is empty or doesn't exist, returns None.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            if len(rows) <= 1:
                # only header or empty
                return None
            # the last row:
            last_row = rows[-1]
            # Assume the first column is the datetime
            date_str = last_row[0]
            return datetime.fromisoformat(date_str)  # If you have a different date format, change this line
    except FileNotFoundError:
        return None
    except Exception as e:
        # If an error occurs (e.g., wrong CSV format), it's better to return None
        return None
