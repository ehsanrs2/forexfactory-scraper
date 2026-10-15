import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

from seleniumbase import SB

from src.forexfactory.browser import read_details, read_month
from src.forexfactory.details import DetailCache, detail_text
from src.forexfactory.events import drop_clashes, events_from_states, in_window, iso_utc, months_between
from src.forexfactory.upload import load_env, upload

HERE = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("run")


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Scrape the ForexFactory calendar and upload it to tmd-auth")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--window", action="store_true", help="This month and next month, whole")
    mode.add_argument("--year", type=int, help="A whole calendar year")
    mode.add_argument("--range", nargs=2, metavar=("FROM", "TO"), help="Dates as YYYY-MM-DD, both included")
    parser.add_argument("--no-details", action="store_true", help="Skip the detail of each event")
    parser.add_argument("--dry-run", metavar="FILE", help="Write the payload to FILE instead of uploading it")
    parser.add_argument("--cache", default=os.path.join(HERE, "cache", "details.json"))
    return parser.parse_args(argv)


def window_of(args) -> tuple[datetime, datetime]:
    if args.year:
        return datetime(args.year, 1, 1, tzinfo=timezone.utc), datetime(args.year + 1, 1, 1, tzinfo=timezone.utc)
    if args.range:
        first = datetime.fromisoformat(args.range[0]).replace(tzinfo=timezone.utc)
        last = datetime.fromisoformat(args.range[1]).replace(tzinfo=timezone.utc)
        return first, last + timedelta(days=1)
    first = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return first, next_month(next_month(first))


def next_month(moment: datetime) -> datetime:
    return (moment.replace(day=28) + timedelta(days=4)).replace(day=1)


def month_chunks(start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    chunks = []
    cursor = start
    while cursor < end:
        stop = min(next_month(cursor.replace(day=1)), end)
        chunks.append((cursor, stop))
        cursor = stop
    return chunks


def scrape(start: datetime, end: datetime, cache: DetailCache, with_details: bool) -> list[dict]:
    by_id: dict[int, dict] = {}
    with SB(uc=True, xvfb=True) as sb:
        for year, month in months_between(start, end):
            for event in events_from_states(read_month(sb, year, month)):
                if in_window(event, start, end):
                    by_id[event["ffId"]] = event
        if with_details:
            now = datetime.now(timezone.utc)
            near = (now - timedelta(days=3), now + timedelta(days=14))
            stale = [ff_id for ff_id, e in by_id.items() if cache.needs(ff_id, in_window(e, *near))]
            logger.info("%d events, %d need a detail", len(by_id), len(stale))
            for ff_id, specs in read_details(sb, stale).items():
                cache.put(ff_id, detail_text(specs))
            cache.save()
    unique, dropped = drop_clashes(list(by_id.values()))
    for event in dropped:
        logger.warning("Skipped ffId %d, same title, country and time as another event: %s %s %s", event["ffId"], event["date"], event["country"], event["title"])
    events = sorted(unique, key=lambda e: (e["date"], e["ffId"]))
    for event in events:
        event["detail"] = cache.get(event["ffId"])
    return events


def main(argv=None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    load_env(HERE)
    start, end = window_of(args)
    logger.info("Window %s to %s", iso_utc(start), iso_utc(end))
    cache = DetailCache(args.cache)
    events = scrape(start, end, cache, not args.no_details)
    if not events:
        logger.error("No events found, nothing uploaded")
        return 1
    payloads = []
    for chunk_start, chunk_end in month_chunks(start, end):
        chunk = [e for e in events if in_window(e, chunk_start, chunk_end)]
        if chunk:
            payloads.append(
                {"source": "ForexFactory", "from": iso_utc(chunk_start), "to": iso_utc(chunk_end), "events": chunk}
            )
    if args.dry_run:
        with open(args.dry_run, "w", encoding="utf-8") as f:
            json.dump(payloads, f, ensure_ascii=False, indent=2)
        logger.info("Wrote %d events in %d months to %s", len(events), len(payloads), args.dry_run)
        return 0
    for payload in payloads:
        result = upload(payload)
        logger.info("Uploaded %s to %s: %s", payload["from"], payload["to"], result)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        logger.exception("Run failed")
        sys.exit(1)
