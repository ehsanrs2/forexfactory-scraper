from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .base import ProviderError
from .forexfactory_html import parse_calendar_html
from .http import calendar_rows_present
from ..page_detection import detect_page_issue, normalize_text


class SavedHtmlProvider:
    name = "saved-html"

    def __init__(self, input_path: str, debug: bool = False):
        self.input_path = Path(input_path).expanduser()
        self.debug = debug

    def fetch_events(self, start_date: datetime, end_date: datetime, tzname: str, **kwargs) -> list[dict]:
        if not self.input_path.exists():
            raise ProviderError("input_not_found", f"Saved HTML file does not exist: {self.input_path}")
        html = self.input_path.read_text(encoding="utf-8", errors="replace")
        issue = detect_page_issue("", normalize_text(html), html)
        if issue:
            raise ProviderError(issue, f"Saved HTML appears to be a {issue} page, not a ForexFactory calendar page.")
        if not calendar_rows_present(html):
            raise ProviderError("calendar_selector_missing", "Saved HTML does not contain ForexFactory calendar rows.")
        events = parse_calendar_html(html, "https://www.forexfactory.com/calendar", start_date, tzname)
        if kwargs.get("all_dates"):
            return events
        return [
            event for event in events
            if event.get("date") and start_date.date().isoformat() <= event["date"] <= end_date.date().isoformat()
        ]
