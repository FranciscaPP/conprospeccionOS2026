from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


CHILE = ZoneInfo("America/Santiago")
REPORT_HOURS = frozenset({9, 11, 13, 15, 17, 19, 21})


def chile_now(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(CHILE)
    if now.tzinfo is None:
        raise ValueError("now must include a timezone")
    return now.astimezone(CHILE)


def is_report_window(now: datetime | None = None) -> bool:
    local = chile_now(now)
    return local.weekday() < 5 and local.hour in REPORT_HOURS


def delivery_key_for(now: datetime | None = None) -> str:
    local = chile_now(now)
    return f"hourly:{local:%Y-%m-%d:%H}:America/Santiago"
