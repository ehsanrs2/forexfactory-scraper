from src.forexfactory.page_detection import detect_page_issue
from src.forexfactory.providers.http import HttpResult, dump_http_debug, http_debug_artifact_paths


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


def test_http_debug_artifact_paths_are_deterministic():
    paths = http_debug_artifact_paths("http_calendar_2025-04-07", debug_dir="debug")

    assert str(paths["html"]) == "debug/http_calendar_2025-04-07.html"
    assert str(paths["txt"]) == "debug/http_calendar_2025-04-07.txt"


def test_dump_http_debug_writes_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = HttpResult(
        url="https://www.forexfactory.com/calendar?week=apr07.2025",
        status_code=200,
        final_url="https://www.forexfactory.com/calendar?week=apr07.2025",
        content_type="text/html",
        text="<html><head><title>Performing security verification</title></head><body>security service</body></html>",
    )

    paths = dump_http_debug(result, "security_verification", "http_calendar_2025-04-07", ["https://example.test/export.json"])

    assert paths["html"].read_text(encoding="utf-8") == result.text
    txt = paths["txt"].read_text(encoding="utf-8")
    assert "detected_reason: security_verification" in txt
    assert "export_links_found: True" in txt
