from datetime import datetime

from src.forexfactory.scraper import (
    debug_artifact_paths,
    detect_page_issue,
    dump_page_debug_artifacts,
)


def test_security_verification_text_is_flagged():
    reason = detect_page_issue(
        title="Performing security verification",
        body_text="This website uses a security service to protect against malicious bots.",
        source="",
    )

    assert reason == "security_verification"


def test_normal_calendar_html_is_not_flagged():
    reason = detect_page_issue(
        title="Forex Factory Calendar",
        body_text="USD Non-Farm Employment Change",
        source='<table class="calendar__table"><tr class="calendar__row"></tr></table>',
    )

    assert reason is None


def test_debug_artifact_paths_are_deterministic():
    paths = debug_artifact_paths(datetime(2025, 4, 7), debug_dir="debug")

    assert str(paths["html"]) == "debug/forexfactory_2025-04-07.html"
    assert str(paths["png"]) == "debug/forexfactory_2025-04-07.png"
    assert str(paths["txt"]) == "debug/forexfactory_2025-04-07.txt"


class FakeElement:
    text = "Performing security verification This website uses a security service."


class FakeDriver:
    title = "Performing security verification"
    page_source = "<html><body>security service</body></html>"
    current_url = "https://www.forexfactory.com/calendar?day=apr7.2025"

    def __init__(self):
        self.screenshot_path = None

    def find_element(self, by, value):
        return FakeElement()

    def save_screenshot(self, path):
        self.screenshot_path = path
        return True


def test_dump_page_debug_artifacts_writes_files(tmp_path):
    driver = FakeDriver()
    paths = dump_page_debug_artifacts(
        driver,
        datetime(2025, 4, 7),
        "security_verification",
        debug_dir=str(tmp_path),
    )

    assert paths["html"].read_text(encoding="utf-8") == driver.page_source
    txt = paths["txt"].read_text(encoding="utf-8")
    assert "reason: security_verification" in txt
    assert driver.current_url in txt
    assert driver.screenshot_path == str(paths["png"])
