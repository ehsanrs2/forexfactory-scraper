from __future__ import annotations

from datetime import datetime
from typing import Protocol


class ProviderError(RuntimeError):
    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason


class EconomicCalendarProvider(Protocol):
    def fetch_events(self, start_date: datetime, end_date: datetime, tzname: str, **kwargs) -> list[dict]:
        ...
