import html
import json
import os
import re
import time

TAG = re.compile(r"<[^>]+>")
BREAK = re.compile(r"<br\s*/?>", re.IGNORECASE)
SPACE = re.compile(r"\s+")

MAX_AGE_SECONDS = 24 * 3600


def plain(value: str) -> str:
    text = BREAK.sub(" ", value or "")
    text = html.unescape(TAG.sub("", text))
    return SPACE.sub(" ", text).strip()


def detail_text(specs: list[dict]) -> str:
    parts = []
    for spec in sorted(specs or [], key=lambda s: s.get("order", 0)):
        title = plain(spec.get("title", ""))
        body = plain(spec.get("html", ""))
        if title and body:
            parts.append(f"{title}: {body}")
    return " | ".join(parts)


class DetailCache:
    def __init__(self, path: str):
        self.path = path
        self.entries: dict[str, dict] = {}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                self.entries = json.load(f)

    def needs(self, ff_id: int, near: bool, now: float | None = None) -> bool:
        entry = self.entries.get(str(ff_id))
        if not entry or not entry["text"]:
            return True
        return near and (now or time.time()) - entry["fetchedAt"] > MAX_AGE_SECONDS

    def get(self, ff_id: int) -> str:
        entry = self.entries.get(str(ff_id))
        return entry["text"] if entry else ""

    def put(self, ff_id: int, text: str, now: float | None = None):
        self.entries[str(ff_id)] = {"text": text, "fetchedAt": now or time.time()}

    def save(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.entries, f, ensure_ascii=False)
        os.replace(tmp, self.path)
