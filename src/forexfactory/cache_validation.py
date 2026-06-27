from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from .normalizer import clean, normalize_event


LEGACY_COLUMNS = ["DateTime", "Currency", "Impact", "Event", "Actual", "Forecast", "Previous", "Detail"]
CANONICAL_COLUMNS = [
    "date",
    "time",
    "datetime_local",
    "datetime_utc",
    "currency",
    "impact",
    "event",
    "actual",
    "forecast",
    "previous",
    "detail",
    "source",
    "source_url",
    "detail_url",
]
ALL_COLUMNS = LEGACY_COLUMNS + CANONICAL_COLUMNS
KEY_COLUMNS = ["datetime_local", "currency", "event"]


@dataclass
class ValidationReport:
    total_rows: int
    valid_datetime_rows: int
    missing_datetime_rows: int
    min_date: str | None
    max_date: str | None
    range_rows: int
    range_min_date: str | None
    range_max_date: str | None
    range_duplicate_groups: int
    range_duplicated_rows_including_first: int
    source_counts: pd.Series
    currency_counts: pd.Series
    impact_counts: pd.Series
    missing_source_rows: int
    legacy_rows_in_range: int
    missing_key_fields_rows: int
    duplicate_samples: pd.DataFrame


def read_cache(csv_path: str | Path) -> pd.DataFrame:
    return pd.read_csv(csv_path, dtype=str)


def _raw_has_values(row: dict, columns: Iterable[str]) -> bool:
    return any(clean(row.get(column)) for column in columns)


def canonicalize_cache_frame(df: pd.DataFrame, tzname: str = "Asia/Tehran") -> pd.DataFrame:
    rows = []
    for _, row in df.fillna("").iterrows():
        raw = {column: clean(value) for column, value in row.to_dict().items()}
        raw_legacy = _raw_has_values(raw, LEGACY_COLUMNS)
        raw_canonical = _raw_has_values(raw, CANONICAL_COLUMNS)
        schema_source = "legacy" if raw_legacy and not raw_canonical else ("canonical" if raw_canonical else "unknown")
        normalized = normalize_event(raw, tzname, default_source=raw.get("source", ""))
        normalized["schema_source"] = schema_source
        normalized["has_source"] = bool(clean(normalized.get("source")))
        normalized["has_legacy_fields"] = raw_legacy
        normalized["has_canonical_fields"] = raw_canonical
        normalized["__raw_datetime"] = clean(raw.get("DateTime") or raw.get("datetime_local") or raw.get("datetime_utc"))
        rows.append(normalized)

    if not rows:
        return pd.DataFrame(columns=ALL_COLUMNS + ["schema_source", "has_source", "has_legacy_fields", "has_canonical_fields", "__raw_datetime"])

    result = pd.DataFrame(rows)
    for column in ALL_COLUMNS + ["schema_source", "has_source", "has_legacy_fields", "has_canonical_fields", "__raw_datetime"]:
        if column not in result.columns:
            result[column] = ""
    return result


def _parse_iso_date(value: str | None) -> pd.Timestamp | None:
    if not clean(value):
        return None
    try:
        return pd.to_datetime(value, utc=False, errors="coerce")
    except Exception:
        return None


def _canonical_datetime_series(df: pd.DataFrame) -> pd.Series:
    series = df["datetime_local"].fillna("").astype(str).str.strip()
    if "DateTime" in df.columns:
        legacy = df["DateTime"].fillna("").astype(str).str.strip()
        series = series.where(series.ne(""), legacy)
    return series


def _canonical_date_series(df: pd.DataFrame) -> pd.Series:
    date_series = df["date"].fillna("").astype(str).str.strip()
    if "DateTime" in df.columns:
        legacy_date = pd.to_datetime(df["DateTime"], errors="coerce", utc=False).dt.date.astype(str)
        date_series = date_series.where(date_series.ne(""), legacy_date)
    return date_series


def _missing_key_mask(df: pd.DataFrame) -> pd.Series:
    return (
        df["datetime_local"].fillna("").astype(str).str.strip().eq("")
        | df["currency"].fillna("").astype(str).str.strip().eq("")
        | df["event"].fillna("").astype(str).str.strip().eq("")
    )


def validate_cache_frame(df: pd.DataFrame, start: str | datetime, end: str | datetime, tzname: str = "Asia/Tehran") -> ValidationReport:
    canonical = canonicalize_cache_frame(df, tzname=tzname)
    total_rows = len(canonical)
    valid_datetime_rows = canonical["datetime_local"].fillna("").astype(str).str.strip().ne("").sum()
    missing_datetime_rows = total_rows - int(valid_datetime_rows)

    valid_dates = pd.to_datetime(canonical["date"], errors="coerce").dropna()
    min_date = valid_dates.min().date().isoformat() if not valid_dates.empty else None
    max_date = valid_dates.max().date().isoformat() if not valid_dates.empty else None

    start_ts = pd.Timestamp(start).date()
    end_ts = pd.Timestamp(end).date()
    range_mask = pd.to_datetime(canonical["date"], errors="coerce").dt.date.between(start_ts, end_ts)
    range_df = canonical.loc[range_mask].copy()
    range_rows = len(range_df)
    range_dates = pd.to_datetime(range_df["date"], errors="coerce").dropna()
    range_min_date = range_dates.min().date().isoformat() if not range_dates.empty else None
    range_max_date = range_dates.max().date().isoformat() if not range_dates.empty else None

    key_frame = range_df.loc[
        range_df["datetime_local"].fillna("").astype(str).str.strip().ne("")
        & range_df["currency"].fillna("").astype(str).str.strip().ne("")
        & range_df["event"].fillna("").astype(str).str.strip().ne("")
    ].copy()
    key_frame["__canonical_key"] = (
        key_frame["datetime_local"].fillna("").astype(str).str.strip()
        + "|"
        + key_frame["currency"].fillna("").astype(str).str.strip().str.upper()
        + "|"
        + key_frame["event"].fillna("").astype(str).str.strip()
    )
    duplicate_groups = int((key_frame.groupby("__canonical_key").size() > 1).sum()) if not key_frame.empty else 0
    duplicated_rows_including_first = int(key_frame["__canonical_key"].duplicated(keep=False).sum())
    duplicate_samples = key_frame.loc[key_frame["__canonical_key"].duplicated(keep=False), ["datetime_local", "currency", "event", "source", "schema_source"]].drop_duplicates().head(10)

    source_counts = range_df["source"].replace("", "<NA>").fillna("<NA>").value_counts(dropna=False)
    currency_counts = range_df["currency"].replace("", "<NA>").fillna("<NA>").value_counts(dropna=False)
    impact_counts = range_df["impact"].replace("", "<NA>").fillna("<NA>").value_counts(dropna=False)

    missing_source_rows = int(range_df["source"].fillna("").astype(str).str.strip().eq("").sum())
    legacy_rows_in_range = int(range_df["source"].fillna("").astype(str).str.strip().eq("").sum())
    missing_key_fields_rows = int(_missing_key_mask(range_df).sum())

    return ValidationReport(
        total_rows=total_rows,
        valid_datetime_rows=int(valid_datetime_rows),
        missing_datetime_rows=int(missing_datetime_rows),
        min_date=min_date,
        max_date=max_date,
        range_rows=range_rows,
        range_min_date=range_min_date,
        range_max_date=range_max_date,
        range_duplicate_groups=duplicate_groups,
        range_duplicated_rows_including_first=duplicated_rows_including_first,
        source_counts=source_counts,
        currency_counts=currency_counts,
        impact_counts=impact_counts,
        missing_source_rows=missing_source_rows,
        legacy_rows_in_range=legacy_rows_in_range,
        missing_key_fields_rows=missing_key_fields_rows,
        duplicate_samples=duplicate_samples,
    )


def format_validation_report(report: ValidationReport) -> str:
    lines = [
        f"total rows: {report.total_rows}",
        f"valid datetime rows: {report.valid_datetime_rows}",
        f"missing datetime rows: {report.missing_datetime_rows}",
        f"min date: {report.min_date or '<none>'}",
        f"max date: {report.max_date or '<none>'}",
        f"range rows: {report.range_rows}",
        f"range date min: {report.range_min_date or '<none>'}",
        f"range date max: {report.range_max_date or '<none>'}",
        f"range duplicate groups: {report.range_duplicate_groups}",
        f"range duplicated rows including first: {report.range_duplicated_rows_including_first}",
        "source counts:",
        *[f"  {index}: {count}" for index, count in report.source_counts.items()],
        "currency counts:",
        *[f"  {index}: {count}" for index, count in report.currency_counts.head(20).items()],
        "impact counts:",
        *[f"  {index}: {count}" for index, count in report.impact_counts.items()],
        f"rows with missing source: {report.missing_source_rows}",
        f"legacy rows inside requested range: {report.legacy_rows_in_range}",
        f"rows with missing key fields: {report.missing_key_fields_rows}",
    ]
    if not report.duplicate_samples.empty:
        lines.append("duplicate samples:")
        lines.extend("  " + line for line in report.duplicate_samples.to_string(index=False).splitlines())
    return "\n".join(lines)
