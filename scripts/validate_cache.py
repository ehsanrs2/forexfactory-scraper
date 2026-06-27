#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.forexfactory.cache_validation import format_validation_report, read_cache, validate_cache_frame


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a Forex Factory cache CSV")
    parser.add_argument("--csv", required=True, help="Path to the cache CSV file")
    parser.add_argument("--start", required=True, help="Start date in YYYY-MM-DD format")
    parser.add_argument("--end", required=True, help="End date in YYYY-MM-DD format")
    parser.add_argument("--tz", default="Asia/Tehran", help="Timezone used when canonicalizing legacy rows")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    df = read_cache(args.csv)
    report = validate_cache_frame(df, args.start, args.end, tzname=args.tz)
    print(format_validation_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
