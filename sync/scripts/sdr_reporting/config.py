from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo


CHILE = ZoneInfo("America/Santiago")


@dataclass(frozen=True)
class ClientConfig:
    slug: str
    name: str
    short: str
    emoji: str
    color: str


@dataclass(frozen=True)
class WorkBlock:
    start: datetime
    end: datetime
    client: str


CLIENTS = {
    "bambutech": ClientConfig("bambutech", "BAMBU TECH", "BAM", "🟩", "#22C55E"),
    "gbs": ClientConfig("gbs", "GBS", "GBS", "🟪", "#8B5CF6"),
    "balia": ClientConfig("balia", "BALIA", "BAL", "🩷", "#EC4899"),
}

TOTAL_COLOR = "#334155"
BACKGROUND_COLOR = "#F8FAFC"
CARD_COLOR = "#FFFFFF"
TEXT_COLOR = "#0F172A"
SECONDARY_TEXT_COLOR = "#64748B"
GAP_COLOR = "#DC2626"

_SCHEDULE = (
    (time(11), time(12), "balia"),
    (time(12), time(13), "gbs"),
    (time(13), time(16), "bambutech"),
    (time(17), time(18), "gbs"),
    (time(18), time(20), "bambutech"),
)


def work_blocks_for(day: date) -> list[WorkBlock]:
    if day.weekday() >= 5:
        return []
    return [
        WorkBlock(
            datetime.combine(day, start, tzinfo=CHILE),
            datetime.combine(day, end, tzinfo=CHILE),
            client,
        )
        for start, end, client in _SCHEDULE
    ]


def client_at(moment: datetime) -> str | None:
    local = moment.astimezone(CHILE)
    for block in work_blocks_for(local.date()):
        if block.start <= local < block.end:
            return block.client
    return None

