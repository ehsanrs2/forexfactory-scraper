from __future__ import annotations

import csv
import json
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from io import StringIO

from ..normalizer import normalize_events, parse_ics_datetime
from .base import ProviderError
from .http import classify_http_calendar, discover_export_links, dump_http_debug, fetch_url

logger = logging.getLogger(__name__)

EXPORT_FORMATS = {"json", "csv", "xml", "ics"}


class ForexFactoryExportProvider:
    name = "forexfactory-export"

    def __init__(self, export_format: str = "json", debug: bool = False, timeout: int = 30):
        if export_format not in EXPORT_FORMATS:
            raise ProviderError("invalid_export_format", f"--export-format must be one of {', '.join(sorted(EXPORT_FORMATS))}.")
        self.export_format = export_format
        self.debug = debug
        self.timeout = timeout

    def fetch_events(self, start_date: datetime, end_date: datetime, tzname: str, **kwargs) -> list[dict]:
        calendar_url = f"https://www.forexfactory.com/calendar?week={start_date.strftime('%b%d.%Y').lower()}"
        logger.info("Discovering ForexFactory export links from %s", calendar_url)
        page = fetch_url(calendar_url, timeout=self.timeout)
        links = discover_export_links(page.text, page.final_url)
        issue = classify_http_calendar(page)
        if issue:
            if self.debug:
                dump_http_debug(page, issue, f"http_calendar_{start_date.date().isoformat()}", links)
            raise ProviderError(issue, f"ForexFactory export discovery returned {issue}.")
        export_url = self._select_export_link(links)
        if not export_url:
            if self.debug:
                dump_http_debug(page, "export_links_not_found", f"http_calendar_{start_date.date().isoformat()}", links)
            raise ProviderError("export_links_not_found", f"No {self.export_format.upper()} export link was found on {calendar_url}.")

        logger.info("Fetching ForexFactory export: %s", export_url)
        result = fetch_url(export_url, timeout=self.timeout)
        if result.status_code >= 400:
            raise ProviderError("export_endpoint_blocked", f"Export endpoint returned HTTP {result.status_code}: {export_url}")
        raw_events = self._parse_export(result.text, tzname)
        events = normalize_events(raw_events, tzname, default_source="forexfactory-export")
        filtered = [
            event for event in events
            if event.get("date") and start_date.date().isoformat() <= event["date"] <= end_date.date().isoformat()
        ]
        if raw_events and not filtered and any("ff_calendar_thisweek" in link for link in links):
            sample_dates = sorted({event.get("date", "") for event in events if event.get("date")})
            raise ProviderError(
                "historical_export_not_supported",
                "Discovered export links are ff_calendar_thisweek files and did not contain the requested date range. "
                f"Available export dates include: {', '.join(sample_dates[:3])} ...",
            )
        return filtered

    def _select_export_link(self, links: list[str]) -> str | None:
        suffix = f".{self.export_format}"
        for link in links:
            if suffix in link.lower() and "ff_calendar" in link.lower():
                return link
        return None

    def _parse_export(self, text: str, tzname: str) -> list[dict]:
        if self.export_format == "json":
            return self._parse_json(text)
        if self.export_format == "csv":
            return self._parse_csv(text)
        if self.export_format == "xml":
            return self._parse_xml(text)
        if self.export_format == "ics":
            return self._parse_ics(text, tzname)
        return []

    def _parse_json(self, text: str) -> list[dict]:
        data = json.loads(text)
        if not isinstance(data, list):
            raise ProviderError("invalid_export_payload", "JSON export did not contain a list of events.")
        return [
            {
                "title": item.get("title", ""),
                "country": item.get("country", ""),
                "datetime": item.get("date", ""),
                "impact": item.get("impact", ""),
                "actual": item.get("actual", ""),
                "forecast": item.get("forecast", ""),
                "previous": item.get("previous", ""),
                "url": item.get("url", ""),
                "source": "forexfactory-export",
            }
            for item in data
            if isinstance(item, dict)
        ]

    def _parse_csv(self, text: str) -> list[dict]:
        return [
            {
                "title": row.get("Title", ""),
                "country": row.get("Country", ""),
                "date": row.get("Date", ""),
                "time": row.get("Time", ""),
                "impact": row.get("Impact", ""),
                "actual": row.get("Actual", ""),
                "forecast": row.get("Forecast", ""),
                "previous": row.get("Previous", ""),
                "url": row.get("URL", ""),
                "source": "forexfactory-export",
            }
            for row in csv.DictReader(StringIO(text))
        ]

    def _parse_xml(self, text: str) -> list[dict]:
        root = ET.fromstring(text)
        events = []
        for node in root.findall(".//event"):
            item = {child.tag.lower(): (child.text or "") for child in node}
            item["source"] = "forexfactory-export"
            events.append(item)
        return events

    def _parse_ics(self, text: str, tzname: str) -> list[dict]:
        events = []
        current: dict | None = None
        for line in _unfold_ics(text):
            if line == "BEGIN:VEVENT":
                current = {}
            elif line == "END:VEVENT" and current is not None:
                events.append(current)
                current = None
            elif current is not None and ":" in line:
                key, value = line.split(":", 1)
                key = key.split(";", 1)[0].upper()
                current[key] = value.replace("\\n", "\n")
        parsed = []
        for item in events:
            description = item.get("DESCRIPTION", "")
            dt = parse_ics_datetime(item.get("DTSTART", ""), tzname)
            summary = item.get("SUMMARY", "")
            parsed.append({
                "title": re.sub(r"^[^\w]+", "", summary).strip(),
                "datetime": dt.isoformat() if dt else "",
                "impact": _desc_value(description, "Impact"),
                "forecast": _desc_value(description, "Forecast"),
                "previous": _desc_value(description, "Previous"),
                "url": _desc_url(description),
                "source": "forexfactory-export",
            })
        return parsed


def _unfold_ics(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        if raw.startswith((" ", "\t")) and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw.strip())
    return lines


def _desc_value(description: str, key: str) -> str:
    match = re.search(rf"{re.escape(key)}:\s*([^\n]+)", description)
    return match.group(1).strip() if match else ""


def _desc_url(description: str) -> str:
    match = re.search(r"https?://\S+", description)
    return match.group(0).strip() if match else ""
