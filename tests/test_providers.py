from datetime import datetime

from dateutil.tz import gettz

from src.forexfactory.providers.forexfactory_export import ForexFactoryExportProvider
from src.forexfactory.providers.forexfactory_html import parse_calendar_html
from src.forexfactory.providers.http import discover_export_links
from src.forexfactory.providers.saved_html import SavedHtmlProvider


EXPORT_HTML = """
<html><body>
<h2>Weekly Export</h2>
<a href="https://nfs.faireconomy.media/ff_calendar_thisweek.ics?version=abc">ICS</a>
<a href="https://nfs.faireconomy.media/ff_calendar_thisweek.csv?version=abc">CSV</a>
<a href="https://nfs.faireconomy.media/ff_calendar_thisweek.json?version=abc">JSON</a>
<a href="https://nfs.faireconomy.media/ff_calendar_thisweek.xml?version=abc">XML</a>
</body></html>
"""

CALENDAR_HTML = """
<table class="calendar__table">
<tr class="calendar__row calendar__row--day-breaker"><td class="calendar__date">Mon Apr 7</td></tr>
<tr class="calendar__row" data-event-id="1">
  <td class="calendar__time">8:30am</td>
  <td class="calendar__currency">USD</td>
  <td class="calendar__impact"><span title="High Impact Expected"></span></td>
  <td class="calendar__event"><a href="/calendar/1-test-event">Test Event</a></td>
  <td class="calendar__actual">1.0%</td>
  <td class="calendar__forecast">0.8%</td>
  <td class="calendar__previous">0.7%</td>
</tr>
</table>
"""


def test_export_link_discovery():
    links = discover_export_links(EXPORT_HTML, "https://www.forexfactory.com/calendar")

    assert len([link for link in links if "ff_calendar_thisweek" in link]) == 4


def test_json_export_parsing():
    provider = ForexFactoryExportProvider("json")
    rows = provider._parse_json('[{"title":"GDP","country":"USD","date":"2025-04-07T08:30:00-04:00","impact":"High","forecast":"1","previous":"2","url":"https://example.test"}]')

    assert rows[0]["title"] == "GDP"
    assert rows[0]["country"] == "USD"


def test_csv_export_parsing():
    provider = ForexFactoryExportProvider("csv")
    rows = provider._parse_csv("Title,Country,Date,Time,Impact,Forecast,Previous,URL\nGDP,USD,04-07-2025,8:30am,High,1,2,https://example.test\n")

    assert rows[0]["title"] == "GDP"
    assert rows[0]["time"] == "8:30am"


def test_xml_export_parsing():
    provider = ForexFactoryExportProvider("xml")
    rows = provider._parse_xml("<weeklyevents><event><title>GDP</title><country>USD</country><date>04-07-2025</date><time>8:30am</time></event></weeklyevents>")

    assert rows[0]["title"] == "GDP"
    assert rows[0]["country"] == "USD"


def test_ics_export_parsing():
    provider = ForexFactoryExportProvider("ics")
    rows = provider._parse_ics("BEGIN:VCALENDAR\nBEGIN:VEVENT\nDTSTART:20250407T123000Z\nSUMMARY:⁎ US GDP\nDESCRIPTION:Impact: High\\n\\nForecast: 1\\n\\nPrevious: 2\\n\\nView Event : https://example.test\nEND:VEVENT\nEND:VCALENDAR", "Asia/Tehran")

    assert rows[0]["title"] == "US GDP"
    assert rows[0]["impact"] == "High"


def test_html_calendar_parsing():
    tz = gettz("Asia/Tehran")
    rows = parse_calendar_html(CALENDAR_HTML, "https://www.forexfactory.com/calendar", datetime(2025, 4, 7, tzinfo=tz), "Asia/Tehran")

    assert rows[0]["currency"] == "USD"
    assert rows[0]["event"] == "Test Event"
    assert rows[0]["detail_url"].endswith("/calendar/1-test-event")


def test_saved_html_provider(tmp_path):
    path = tmp_path / "calendar.html"
    path.write_text(CALENDAR_HTML, encoding="utf-8")
    tz = gettz("Asia/Tehran")
    provider = SavedHtmlProvider(str(path))

    rows = provider.fetch_events(datetime(2025, 4, 7, tzinfo=tz), datetime(2025, 4, 7, tzinfo=tz), "Asia/Tehran")

    assert len(rows) == 1
    assert rows[0]["source"] == "forexfactory-html"
