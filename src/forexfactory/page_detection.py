import re


def normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def detect_page_issue(title: str = "", body_text: str = "", source: str = "") -> str | None:
    haystack = " ".join([title or "", body_text or "", source or ""]).lower()
    security_signals = (
        "performing security verification",
        "security service",
        "protect against malicious bots",
        "checking your browser",
        "cloudflare",
        "captcha",
        "access denied",
        "forbidden",
        "verify you are not a bot",
        "enable javascript",
        "unusual traffic",
        "bot detection",
    )
    consent_signals = (
        "privacy/consent page",
        "consent",
        "accept cookies",
        "cookie settings",
    )
    if any(signal in haystack for signal in security_signals):
        return "security_verification"
    if any(signal in haystack for signal in consent_signals):
        return "privacy_consent"
    body_clean = normalize_text(body_text)
    source_clean = normalize_text(source)
    if not body_clean and len(source_clean) < 200:
        return "empty_body"
    return None
