import re
from datetime import date, datetime, timedelta, timezone

FF_BASE = "https://www.forexfactory.com"

IMPACT = {
    "high": "High",
    "medium": "Medium",
    "low": "Low",
    "holiday": "Holiday",
    "non-economic": "Holiday",
}

BETTER_WORSE = {1: "better", 2: "worse"}

WHOLE_DAY = re.compile(
    r"^(all day|tentative|day \d+|\d{1,2}(st|nd|rd|th)\s*-\s*\d{1,2}(st|nd|rd|th))$",
    re.IGNORECASE,
)


def iso_utc(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def display_offset(day_dateline: int) -> int:
    offset = (-day_dateline) % 86400
    return offset - 86400 if offset > 14 * 3600 else offset


def local_day(day_dateline: int) -> date:
    moment = datetime.fromtimestamp(day_dateline + display_offset(day_dateline), timezone.utc)
    return moment.date()


def event_moment(event: dict, day_dateline: int) -> datetime:
    if not WHOLE_DAY.match((event.get("timeLabel") or "").strip()):
        return datetime.fromtimestamp(int(event["dateline"]), timezone.utc)
    day = local_day(day_dateline)
    return datetime(day.year, day.month, day.day, tzinfo=timezone.utc)


def absolute(path: str) -> str:
    if not path:
        return ""
    return path if path.startswith("http") else FF_BASE + path


def to_event(event: dict, day_dateline: int) -> dict:
    return {
        "ffId": int(event["id"]),
        "ebaseId": int(event["ebaseId"]) if event.get("ebaseId") else None,
        "title": (event.get("name") or "").strip(),
        "country": (event.get("currency") or "").strip().upper(),
        "date": iso_utc(event_moment(event, day_dateline)),
        "impact": IMPACT.get((event.get("impactName") or "").lower(), "Low"),
        "forecast": (event.get("forecast") or "").strip(),
        "previous": (event.get("previous") or "").strip(),
        "revision": (event.get("revision") or "").strip(),
        "actual": (event.get("actual") or "").strip(),
        "actual_dir": BETTER_WORSE.get(event.get("actualBetterWorse"), ""),
        "url": absolute(event.get("url") or ""),
        "soloUrl": absolute(event.get("soloUrl") or ""),
    }


def events_from_states(states: dict) -> list[dict]:
    out = []
    for state in (states or {}).values():
        for day in state.get("days") or []:
            for event in day.get("events") or []:
                out.append(to_event(event, int(day["dateline"])))
    return out


def drop_clashes(events: list[dict]) -> tuple[list[dict], list[dict]]:
    kept: dict[tuple, dict] = {}
    dropped = []
    for event in sorted(events, key=lambda e: e["ffId"]):
        key = (event["title"], event["country"], event["date"])
        if key in kept:
            dropped.append(event)
        else:
            kept[key] = event
    return list(kept.values()), dropped


def in_window(event: dict, start: datetime, end: datetime) -> bool:
    moment = datetime.fromisoformat(event["date"])
    return start <= moment < end


def months_between(start: datetime, end: datetime) -> list[tuple[int, int]]:
    first = (start - timedelta(days=1)).date().replace(day=1)
    last = (end + timedelta(days=1)).date()
    months = []
    cursor = first
    while cursor <= last:
        months.append((cursor.year, cursor.month))
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
    return months


def month_param(year: int, month: int) -> str:
    return date(year, month, 1).strftime("%b").lower() + f".{year}"
