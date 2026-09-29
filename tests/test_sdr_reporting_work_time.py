import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from sdr_reporting.config import work_blocks_for
from sdr_reporting.metrics import elapsed_work_seconds, worked_time


CHILE = ZoneInfo("America/Santiago")


def test_worked_time_is_phone_plus_five_minutes_per_answered_email():
    result = worked_time(elapsed_seconds=4 * 3600, phone_seconds=3600, responded_emails=5)
    assert result == {"worked_seconds": 5100, "unregistered_seconds": 9300}


def test_worked_time_adds_verified_whatsapp_effort():
    result = worked_time(
        elapsed_seconds=3600,
        phone_seconds=600,
        responded_emails=1,
        whatsapp_seconds=360,
    )
    assert result == {"worked_seconds": 1260, "unregistered_seconds": 2340}


def test_worked_time_never_exceeds_elapsed_period():
    result = worked_time(elapsed_seconds=600, phone_seconds=500, responded_emails=2)
    assert result == {"worked_seconds": 600, "unregistered_seconds": 0}


def test_elapsed_time_only_counts_scheduled_blocks_and_can_filter_client():
    blocks = work_blocks_for(date(2026, 9, 24))
    now = datetime(2026, 9, 24, 15, 30, tzinfo=CHILE)
    assert elapsed_work_seconds(blocks, now) == 4 * 3600 + 30 * 60
    assert elapsed_work_seconds(blocks, now, "bambutech") == 2 * 3600 + 30 * 60
    assert elapsed_work_seconds(blocks, now, "gbs") == 3600
