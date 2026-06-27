from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from ..page_detection import detect_page_issue, normalize_text

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass
class HttpResult:
    url: str
    status_code: int
    final_url: str
    content_type: str
    text: str


def http_debug_artifact_paths(debug_name: str, debug_dir: str = "debug") -> dict[str, Path]:
    base = Path(debug_dir) / debug_name
    return {
        "html": base.with_suffix(".html"),
        "txt": base.with_suffix(".txt"),
    }


def fetch_url(url: str, headers: dict | None = None, timeout: int = 30) -> HttpResult:
    req = Request(url, headers=headers or DEFAULT_HEADERS)
    try:
        with urlopen(req, timeout=timeout) as response:
            body = response.read()
            status_code = response.status
            final_url = response.geturl()
            content_type = response.headers.get("content-type", "")
    except HTTPError as exc:
        body = exc.read()
        status_code = exc.code
        final_url = exc.geturl()
        content_type = exc.headers.get("content-type", "") if exc.headers else ""
    except URLError as exc:
        raise RuntimeError(f"Could not fetch {url}: {exc}") from exc
    return HttpResult(url, status_code, final_url, content_type, body.decode("utf-8", "replace"))


def extract_title(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return normalize_text(unescape(match.group(1))) if match else ""


def body_text(html: str) -> str:
    text = re.sub(r"<script\b.*?</script>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return normalize_text(unescape(text))


def discover_export_links(html: str, base_url: str) -> list[str]:
    links = []
    for match in re.finditer(r"""(?:href|src)=["']([^"']+)["']""", html, re.I):
        href = unescape(match.group(1))
        if re.search(r"(\.ics|\.csv|\.json|\.xml|nfs\.faireconomy\.media|ff_calendar)", href, re.I):
            links.append(urljoin(base_url, href))
    return sorted(set(links))


def calendar_rows_present(html: str) -> bool:
    lowered = html.lower()
    return "calendar__table" in lowered or "calendar__row" in lowered or "data-event-id" in lowered


def dump_http_debug(result: HttpResult, reason: str, debug_name: str, export_links: list[str] | None = None):
    paths = http_debug_artifact_paths(debug_name)
    paths["html"].parent.mkdir(parents=True, exist_ok=True)
    html_path = paths["html"]
    txt_path = paths["txt"]
    html_path.write_text(result.text, encoding="utf-8")
    title = extract_title(result.text)
    body = body_text(result.text)
    links = export_links or []
    txt_path.write_text(
        "\n".join([
            f"url: {result.url}",
            f"status_code: {result.status_code}",
            f"final_url: {result.final_url}",
            f"title: {title}",
            f"content_length: {len(result.text)}",
            f"detected_reason: {reason}",
            f"export_links_found: {bool(links)}",
            f"calendar_rows_found: {calendar_rows_present(result.text)}",
            "export_links:",
            *links,
            "body_preview:",
            body[:2000],
            "",
        ]),
        encoding="utf-8",
    )
    return {"html": html_path, "txt": txt_path}


def classify_http_calendar(result: HttpResult) -> str | None:
    issue = detect_page_issue(extract_title(result.text), body_text(result.text), result.text)
    if issue == "security_verification" and calendar_rows_present(result.text):
        strong = (
            "performing security verification",
            "protect against malicious bots",
            "checking your browser",
            "verify you are not a bot",
        )
        lowered = result.text.lower()
        if not any(signal in lowered for signal in strong):
            return None
    return issue
