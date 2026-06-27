from datetime import datetime

from dateutil.tz import gettz

from src.forexfactory.incremental import _group_contiguous_days, _iter_days


def test_iter_days_inclusive_with_timezone():
    tz = gettz("Asia/Tehran")
    start = datetime(2025, 4, 7, tzinfo=tz)
    end = datetime(2025, 4, 9, tzinfo=tz)

    days = list(_iter_days(start, end))

    assert [day.date().isoformat() for day in days] == ["2025-04-07", "2025-04-08", "2025-04-09"]
    assert all(day.tzinfo is not None for day in days)


def test_group_contiguous_days_splits_gaps():
    tz = gettz("Asia/Tehran")
    days = [
        datetime(2025, 4, 7, tzinfo=tz),
        datetime(2025, 4, 8, tzinfo=tz),
        datetime(2025, 4, 10, tzinfo=tz),
    ]

    groups = _group_contiguous_days(days)

    assert [(start.date().isoformat(), end.date().isoformat()) for start, end in groups] == [
        ("2025-04-07", "2025-04-08"),
        ("2025-04-10", "2025-04-10"),
    ]
