import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from sdr_reporting.config import work_blocks_for
from sdr_reporting.metrics import call_metrics, operational_gaps

CHILE = ZoneInfo("America/Santiago")


def at(hour, minute):
    return datetime(2026, 9, 24, hour, minute, tzinfo=CHILE)


def test_calls_count_unique_contacts_separately():
    calls = [
        {"contact_id": "a", "status": "completed", "duration_seconds": 8},
        {"contact_id": "a", "status": "no-answer", "duration_seconds": 0},
        {"contact_id": "b", "status": "completed", "duration_seconds": 30},
    ]
    metrics = call_metrics(calls)
    assert metrics.calls == 3
    assert metrics.unique_contacts == 2
    assert metrics.repeated_contacts == 1
    assert metrics.answered == 1
    assert metrics.unanswered == 2
    assert metrics.answered_seconds == 30
    assert metrics.retry_calls == 1


def test_twenty_seconds_is_not_answered_and_groups_are_exhaustive():
    metrics = call_metrics([
        {"contact_id": "a", "duration_seconds": 20, "phone_seconds": 25},
        {"contact_id": "b", "duration_seconds": 21, "phone_seconds": 30},
    ])
    assert metrics.answered == 1
    assert metrics.unanswered == 1
    assert metrics.answered + metrics.unanswered == metrics.calls
    assert metrics.unanswered_phone_seconds == 25


def test_gap_detection_only_inside_block_and_at_least_twenty_minutes():
    block = work_blocks_for(date(2026, 9, 24))[0]
    events = [{"occurred_at": at(11, 5)}, {"occurred_at": at(11, 14)}, {"occurred_at": at(11, 40)}]
    gaps = operational_gaps(block, events, at(11, 50))
    assert [(g.start.strftime("%H:%M"), g.end.strftime("%H:%M")) for g in gaps] == [
        ("11:14", "11:40")
    ]


def test_no_gap_is_created_for_lunch_or_short_silence():
    assert operational_gaps(None, [], at(16, 45)) == []
    block = work_blocks_for(date(2026, 9, 24))[0]
    events = [{"occurred_at": at(11, 0)}, {"occurred_at": at(11, 19)}, {"occurred_at": at(11, 38)}]
    assert operational_gaps(block, events, at(11, 50)) == []
