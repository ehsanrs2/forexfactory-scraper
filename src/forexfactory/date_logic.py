# src/forexfactory/date_logic.py

from datetime import datetime

def build_url_for_partial_range(start_dt: datetime, end_dt: datetime) -> str:
    """
    Builds a ForexFactory calendar param of the form: ?range=dec20.2024-dec30.2024
    """
    def ff_str(d: datetime):
        return d.strftime('%b').lower() + str(d.day) + '.' + str(d.year)
    return "range=" + ff_str(start_dt) + "-" + ff_str(end_dt)

def build_url_for_full_month(year: int, month: int) -> str:
    """
    Builds a param like: ?month=jan.2025
    """
    dt = datetime(year, month, 1)
    m_str = dt.strftime('%b').lower()
    y_str = dt.strftime('%Y')
    return "month=" + m_str + "." + y_str
