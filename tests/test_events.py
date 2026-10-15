import unittest
from datetime import datetime, timezone

from src.forexfactory.events import (
    display_offset,
    drop_clashes,
    events_from_states,
    in_window,
    local_day,
    month_param,
    months_between,
)

CPI = {
    "id": 153057,
    "ebaseId": 933,
    "name": "Core CPI y/y",
    "currency": "USD",
    "dateline": 1791981000,
    "timeLabel": "7:30pm",
    "impactName": "high",
    "actual": "2.6%",
    "forecast": "2.5%",
    "previous": "2.4%",
    "revision": "",
    "actualBetterWorse": 1,
    "url": "/calendar?day=oct14.2026#detail=153057",
    "soloUrl": "/calendar/933-us-core-cpi-yy",
}

PERMITS = {
    "id": 149305,
    "name": "Building Permits m/m",
    "currency": "CAD",
    "dateline": 1791981000,
    "timeLabel": "7:30pm",
    "impactName": "low",
    "actual": "8.8%",
    "forecast": "2.9%",
    "previous": "-17.3%",
    "revision": "-15.8%",
    "actualBetterWorse": 2,
}

HOLIDAY = {
    "id": 1,
    "name": "Bank Holiday",
    "currency": "JPY",
    "dateline": 1791910800,
    "timeLabel": "All Day",
    "impactName": "holiday",
}


def states(day_dateline, *events):
    return {"1": {"days": [{"dateline": day_dateline, "events": list(events)}]}}


BANGKOK_DAY = int(datetime(2026, 10, 13, 17, 0, tzinfo=timezone.utc).timestamp())
NEW_YORK_DAY = int(datetime(2026, 10, 14, 4, 0, tzinfo=timezone.utc).timestamp())


class EventsFromStates(unittest.TestCase):
    def test_timed_event_uses_its_dateline_in_utc(self):
        [event] = events_from_states(states(BANGKOK_DAY, CPI))
        self.assertEqual(event["date"], "2026-10-14T12:30:00+00:00")

    def test_fields_keep_the_names_the_backend_reads(self):
        [event] = events_from_states(states(BANGKOK_DAY, CPI))
        self.assertEqual(event["ffId"], 153057)
        self.assertEqual(event["ebaseId"], 933)
        self.assertEqual(event["title"], "Core CPI y/y")
        self.assertEqual(event["country"], "USD")
        self.assertEqual(event["impact"], "High")
        self.assertEqual((event["actual"], event["forecast"], event["previous"]), ("2.6%", "2.5%", "2.4%"))
        self.assertEqual(event["actual_dir"], "better")
        self.assertEqual(event["url"], "https://www.forexfactory.com/calendar?day=oct14.2026#detail=153057")
        self.assertEqual(event["soloUrl"], "https://www.forexfactory.com/calendar/933-us-core-cpi-yy")

    def test_revision_and_worse(self):
        [event] = events_from_states(states(BANGKOK_DAY, PERMITS))
        self.assertEqual(event["previous"], "-17.3%")
        self.assertEqual(event["revision"], "-15.8%")
        self.assertEqual(event["actual_dir"], "worse")
        self.assertIsNone(event["ebaseId"])

    def test_all_day_event_sits_at_midnight_utc_of_the_page_day(self):
        [event] = events_from_states(states(BANGKOK_DAY, HOLIDAY))
        self.assertEqual(event["date"], "2026-10-14T00:00:00+00:00")
        self.assertEqual(event["impact"], "Holiday")

    def test_a_label_that_is_not_a_clock_still_uses_the_dateline(self):
        adp = {**CPI, "id": 153355, "timeLabel": "Jan 10th", "dateline": 1770729180}
        [event] = events_from_states(states(BANGKOK_DAY, adp))
        self.assertEqual(event["date"], "2026-02-10T13:13:00+00:00")

    def test_tentative_numbered_days_and_ranges_are_whole_days(self):
        for label in ("Tentative", "Day 2", "19th-23rd", "1st-3rd"):
            [event] = events_from_states(states(BANGKOK_DAY, {**HOLIDAY, "timeLabel": label}))
            self.assertEqual(event["date"], "2026-10-14T00:00:00+00:00")

    def test_all_day_event_on_a_page_behind_utc(self):
        [event] = events_from_states(states(NEW_YORK_DAY, HOLIDAY))
        self.assertEqual(event["date"], "2026-10-14T00:00:00+00:00")


class DropClashes(unittest.TestCase):
    def test_keeps_the_lowest_id_of_events_that_match_exactly(self):
        a = {"ffId": 153365, "title": "ADP", "country": "USD", "date": "2026-11-10T13:15:00+00:00"}
        b = {**a, "ffId": 151052}
        c = {**a, "ffId": 9, "date": "2026-11-10T13:14:00+00:00"}
        kept, dropped = drop_clashes([a, b, c])
        self.assertEqual(sorted(e["ffId"] for e in kept), [9, 151052])
        self.assertEqual([e["ffId"] for e in dropped], [153365])


class DisplayDay(unittest.TestCase):
    def test_offsets(self):
        self.assertEqual(display_offset(BANGKOK_DAY), 7 * 3600)
        self.assertEqual(display_offset(NEW_YORK_DAY), -4 * 3600)
        self.assertEqual(local_day(BANGKOK_DAY).isoformat(), "2026-10-14")
        self.assertEqual(local_day(NEW_YORK_DAY).isoformat(), "2026-10-14")


class Window(unittest.TestCase):
    def test_end_is_excluded(self):
        start = datetime(2026, 10, 14, tzinfo=timezone.utc)
        end = datetime(2026, 10, 15, tzinfo=timezone.utc)
        self.assertTrue(in_window({"date": "2026-10-14T00:00:00+00:00"}, start, end))
        self.assertFalse(in_window({"date": "2026-10-15T00:00:00+00:00"}, start, end))

    def test_months_cover_a_day_either_side(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2027, 1, 1, tzinfo=timezone.utc)
        months = months_between(start, end)
        self.assertEqual(months[0], (2025, 12))
        self.assertEqual(months[-1], (2027, 1))
        self.assertEqual(len(months), 14)

    def test_month_param(self):
        self.assertEqual(month_param(2026, 10), "oct.2026")


if __name__ == "__main__":
    unittest.main()
