from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable

from dateutil import parser as date_parser
from dateutil.tz import gettz


NORMALIZED_COLUMNS = [
    "date",
    "time",
    "datetime_local",
    "datetime_utc",
    "currency",
    "impact",
    "event",
    "actual",
    "forecast",
    "previous",
    "source",
    "source_url",
    "detail_url",
]

LEGACY_COLUMNS = ["DateTime", "Currency", "Impact", "Event", "Actual", "Forecast", "Previous", "Detail"]
CSV_COLUMNS = LEGACY_COLUMNS + NORMALIZED_COLUMNS


def clean(value) -> str:
    return "" if value is None else str(value).strip()


def parse_event_datetime(value: str | None, tzname: str, *, date_value: str | None = None, time_value: str | None = None) -> datetime | None:
    tz = gettz(tzname)
    text = clean(value)
    try:
        if text:
            dt = date_parser.parse(text)
        elif date_value:
            date_text = clean(date_value)
            time_text = clean(time_value) or "12:00am"
            dt = date_parser.parse(f"{date_text} {time_text}")
        else:
            return None
    except (ValueError, TypeError, OverflowError):
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def normalize_event(raw: dict, tzname: str, default_source: str = "") -> dict:
    raw_date = raw.get("date") or raw.get("Date")
    datetime_value = raw.get("datetime") or raw.get("date_iso") or raw.get("DateTime")
    if not datetime_value and "T" in clean(raw_date):
        datetime_value = raw_date
    dt = parse_event_datetime(
        datetime_value,
        tzname,
        date_value=raw_date,
        time_value=raw.get("time") or raw.get("Time"),
    )
    datetime_local = dt.isoformat() if dt else clean(raw.get("datetime_local"))
    datetime_utc = dt.astimezone(timezone.utc).isoformat() if dt else clean(raw.get("datetime_utc"))
    date = dt.date().isoformat() if dt else clean(raw.get("date") or raw.get("Date"))
    time = dt.strftime("%H:%M:%S") if dt else clean(raw.get("time") or raw.get("Time"))

    currency = clean(raw.get("currency") or raw.get("country") or raw.get("Country") or raw.get("Currency")).upper()
    impact = clean(raw.get("impact") or raw.get("Impact"))
    event = clean(raw.get("event") or raw.get("title") or raw.get("Title") or raw.get("Event"))
    actual = clean(raw.get("actual") or raw.get("Actual"))
    forecast = clean(raw.get("forecast") or raw.get("Forecast"))
    previous = clean(raw.get("previous") or raw.get("Previous"))
    detail = clean(raw.get("detail") or raw.get("Detail"))
    source_url = clean(raw.get("source_url") or raw.get("url") or raw.get("URL"))
    detail_url = clean(raw.get("detail_url") or source_url)
    source = clean(raw.get("source") or default_source)

    return {
        "DateTime": datetime_local,
        "Currency": currency,
        "Impact": impact,
        "Event": event,
        "Actual": actual,
        "Forecast": forecast,
        "Previous": previous,
        "Detail": detail,
        "date": date,
        "time": time,
        "datetime_local": datetime_local,
        "datetime_utc": datetime_utc,
        "currency": currency,
        "impact": impact,
        "event": event,
        "actual": actual,
        "forecast": forecast,
        "previous": previous,
        "source": source,
        "source_url": source_url,
        "detail_url": detail_url,
    }


def normalize_events(events: Iterable[dict], tzname: str, default_source: str = "") -> list[dict]:
    return [normalize_event(event, tzname, default_source=default_source) for event in events]


def event_in_range(event: dict, start_date: datetime, end_date: datetime) -> bool:
    dt = parse_event_datetime(event.get("datetime_local") or event.get("DateTime"), start_date.tzname() or "UTC")
    if dt is None:
        try:
            dt = date_parser.parse(event.get("date", ""))
        except (ValueError, TypeError):
            return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=start_date.tzinfo)
    return start_date.date() <= dt.date() <= end_date.date()


def parse_ics_datetime(value: str, tzname: str) -> datetime | None:
    value = clean(value)
    if not value:
        return None
    try:
        if value.endswith("Z"):
            return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).astimezone(gettz(tzname))
        return datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=gettz(tzname))
    except ValueError:
        try:
            return parsedate_to_datetime(value).astimezone(gettz(tzname))
        except Exception:
            return None
