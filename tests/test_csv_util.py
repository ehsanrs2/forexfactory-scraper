import pandas as pd

from src.forexfactory.csv_util import CSV_COLUMNS, merge_new_data, normalize_calendar_frame


def test_normalize_calendar_frame_sorts_and_prefers_detail():
    df = pd.DataFrame([
        {"DateTime": "2025-04-07T10:00:00+03:30", "Currency": "USD", "Impact": "High", "Event": "Jobs", "Detail": ""},
        {"DateTime": "2025-04-07T10:00:00+03:30", "Currency": "USD", "Impact": "High", "Event": "Jobs", "Detail": "Source: BLS"},
        {"DateTime": "2025-04-06T09:00:00+03:30", "Currency": "EUR", "Impact": "Low", "Event": "Retail"},
    ])

    result = normalize_calendar_frame(df)

    assert list(result.columns) == CSV_COLUMNS
    assert result["DateTime"].tolist() == [
        "2025-04-06T09:00:00+03:30",
        "2025-04-07T10:00:00+03:30",
    ]
    assert result.iloc[1]["Detail"] == "Source: BLS"


def test_merge_new_data_updates_missing_detail_only():
    existing = pd.DataFrame([
        {
            "DateTime": "2025-04-07T10:00:00+03:30",
            "Currency": "USD",
            "Impact": "High",
            "Event": "Jobs",
            "Actual": "",
            "Forecast": "",
            "Previous": "",
            "Detail": "",
        }
    ])
    new = pd.DataFrame([
        {
            "DateTime": "2025-04-07T10:00:00+03:30",
            "Currency": "USD",
            "Impact": "High",
            "Event": "Jobs",
            "Actual": "1",
            "Forecast": "2",
            "Previous": "3",
            "Detail": "Source: BLS",
        }
    ])

    result = merge_new_data(existing, new)

    assert len(result) == 1
    assert result.iloc[0]["Detail"] == "Source: BLS"
