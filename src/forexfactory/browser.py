import json
import logging
import time

from .events import FF_BASE, month_param

logger = logging.getLogger(__name__)

READ_STATES = "return JSON.stringify(window.calendarComponentStates || null)"

FETCH_DETAILS = """
const ids = arguments[0];
const out = {};
let next = 0;
async function worker() {
  while (next < ids.length) {
    const id = ids[next++];
    try {
      const r = await fetch('/calendar/details/1-' + id, { credentials: 'include' });
      out[id] = r.ok ? (await r.json()).data?.specs ?? [] : null;
    } catch (e) {
      out[id] = null;
    }
  }
}
await Promise.all([worker(), worker(), worker()]);
return JSON.stringify(out);
"""


class PageError(Exception):
    pass


def read_month(sb, year: int, month: int, wait_seconds: int = 40, empty_seconds: int = 10) -> dict:
    url = f"{FF_BASE}/calendar?month={month_param(year, month)}"
    logger.info("Opening %s", url)
    sb.uc_open_with_reconnect(url, 6)
    started = time.time()
    while time.time() - started < wait_seconds:
        raw = sb.execute_script(READ_STATES)
        states = json.loads(raw) if raw else None
        days = [d for s in (states or {}).values() for d in s.get("days") or []]
        if len(days) >= 28:
            return states
        if states is not None and not days and time.time() - started >= empty_seconds:
            logger.info("%d-%02d is not published yet", year, month)
            return states
        time.sleep(2)
    raise PageError(f"No calendar data for {year}-{month:02d} after {wait_seconds}s")


def read_details(sb, ids: list[int], batch: int = 30, pause: float = 1.0) -> dict[int, list]:
    found: dict[int, list] = {}
    for start in range(0, len(ids), batch):
        chunk = ids[start : start + batch]
        raw = sb.execute_script(FETCH_DETAILS, chunk)
        for key, specs in json.loads(raw or "{}").items():
            if specs is not None:
                found[int(key)] = specs
        logger.info("Details %d/%d", min(start + batch, len(ids)), len(ids))
        time.sleep(pause)
    return found
