from __future__ import annotations

import logging
from datetime import datetime, timedelta
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin

from ..normalizer import normalize_events
from ..page_detection import normalize_text
from .base import ProviderError
from .http import (
    calendar_rows_present,
    classify_http_calendar,
    discover_export_links,
    dump_http_debug,
    fetch_url,
)

logger = logging.getLogger(__name__)


def _ff_date(dt: datetime) -> str:
    return dt.strftime("%b%d.%Y").lower()


def iter_weeks(start_date: datetime, end_date: datetime):
    current = start_date - timedelta(days=start_date.weekday())
    while current <= end_date:
        yield current
        current += timedelta(days=7)


class _CalendarTableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows: list[dict] = []
        self.current_row: dict | None = None
        self.current_cell: str | None = None
        self.current_link: str = ""
        self.current_day_text = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        class_name = attrs_dict.get("class", "")
        if tag == "tr" and "calendar__row" in class_name:
            self.current_row = {"_class": class_name, "_cells": {}, "detail_url": "", "_dateline": attrs_dict.get("data-day-dateline", "")}
            self.current_day_text = ""
        if self.current_row is None:
            return
        if tag == "td":
            for name in ("time", "currency", "impact", "event", "actual", "forecast", "previous", "date"):
                if f"calendar__{name}" in class_name:
                    self.current_cell = name
                    break
        if tag == "span" and self.current_cell == "impact":
            title = attrs_dict.get("title")
            if title:
                self.current_row["_cells"]["impact"] = title
            elif "icon--ff-impact-red" in class_name:
                self.current_row["_cells"]["impact"] = "High"
            elif "icon--ff-impact-ora" in class_name:
                self.current_row["_cells"]["impact"] = "Medium"
            elif "icon--ff-impact-yel" in class_name:
                self.current_row["_cells"]["impact"] = "Low"
            elif "icon--ff-impact-gra" in class_name:
                self.current_row["_cells"]["impact"] = "Non-Economic"
        if tag == "a":
            href = attrs_dict.get("href", "")
            if href:
                self.current_link = href
                if self.current_cell in {"event", "impact"} or "calendar/" in href:
                    self.current_row["detail_url"] = href

    def handle_data(self, data):
        if self.current_row is None:
            return
        text = normalize_text(data)
        if not text:
            return
        if self.current_cell:
            current = self.current_row["_cells"].get(self.current_cell, "")
            self.current_row["_cells"][self.current_cell] = normalize_text(f"{current} {text}")

    def handle_endtag(self, tag):
        if tag == "td":
            self.current_cell = None
        if tag == "a":
            self.current_link = ""
        if tag == "tr" and self.current_row is not None:
            self.rows.append(self.current_row)
            self.current_row = None
            self.current_cell = None


def parse_calendar_html(html: str, base_url: str, fallback_date: datetime, tzname: str) -> list[dict]:
    parser = _CalendarTableParser()
    parser.feed(html)
    events = []
    current_day = fallback_date
    last_time = ""
    for row in parser.rows:
        row_class = row.get("_class", "")
        cells = row.get("_cells", {})
        dateline = row.get("_dateline")
        if dateline:
            try:
                current_day = datetime.fromtimestamp(int(dateline), tz=current_day.tzinfo)
                last_time = ""
            except (TypeError, ValueError, OSError):
                pass
        day_text = cells.get("date", "")
        if day_text:
            parsed = _parse_day_text(day_text, current_day, tzname)
            if parsed is not None:
                current_day = parsed
                last_time = ""
        if "day-breaker" in row_class or "no-event" in row_class:
            continue
        currency = cells.get("currency", "")
        event = cells.get("event", "")
        if not currency or not event:
            continue
        time_text = cells.get("time", "") or last_time
        if cells.get("time"):
            last_time = cells.get("time", "")
        events.append({
            "date": current_day.date().isoformat(),
            "time": time_text,
            "currency": currency,
            "impact": cells.get("impact", ""),
            "event": event,
            "actual": cells.get("actual", ""),
            "forecast": cells.get("forecast", ""),
            "previous": cells.get("previous", ""),
            "detail_url": urljoin(base_url, row.get("detail_url", "")) if row.get("detail_url") else "",
            "source_url": base_url,
            "source": "forexfactory-html",
        })
    return normalize_events(events, tzname, default_source="forexfactory-html")


def _parse_day_text(text: str, fallback_date: datetime, tzname: str) -> datetime | None:
    from datetime import datetime as dt
    from dateutil.tz import gettz
    import re

    match = re.search(r"\b([A-Za-z]{3})\s+(\d{1,2})\b", text)
    if not match:
        return None
    month_text, day_text = match.groups()
    try:
        parsed = dt.strptime(f"{month_text} {int(day_text)} {fallback_date.year}", "%b %d %Y")
    except ValueError:
        return None
    if fallback_date.month == 12 and parsed.month == 1:
        parsed = parsed.replace(year=fallback_date.year + 1)
    elif fallback_date.month == 1 and parsed.month == 12:
        parsed = parsed.replace(year=fallback_date.year - 1)
    return parsed.replace(tzinfo=gettz(tzname))


class ForexFactoryHtmlProvider:
    name = "forexfactory-html"

    def __init__(self, debug: bool = False, timeout: int = 30):
        self.debug = debug
        self.timeout = timeout

    def fetch_events(self, start_date: datetime, end_date: datetime, tzname: str, **kwargs) -> list[dict]:
        events: list[dict] = []
        for week in iter_weeks(start_date, end_date):
            url = f"https://www.forexfactory.com/calendar?week={_ff_date(week)}"
            logger.info("Fetching ForexFactory HTML: %s", url)
            result = fetch_url(url, timeout=self.timeout)
            export_links = discover_export_links(result.text, result.final_url)
            issue = classify_http_calendar(result)
            if issue:
                if self.debug:
                    dump_http_debug(result, issue, f"http_calendar_{week.date().isoformat()}", export_links)
                raise ProviderError(issue, f"ForexFactory HTML fetch returned {issue} for {url}.")
            if not calendar_rows_present(result.text):
                if self.debug:
                    dump_http_debug(result, "calendar_selector_missing", f"http_calendar_{week.date().isoformat()}", export_links)
                raise ProviderError("calendar_selector_missing", f"Calendar rows were not found in fetched HTML for {url}.")
            events.extend(parse_calendar_html(result.text, result.final_url, week, tzname))

        return [
            event for event in events
            if event.get("datetime_local") and start_date.date().isoformat() <= event["date"] <= end_date.date().isoformat()
        ]
