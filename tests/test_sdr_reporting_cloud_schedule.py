import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from sdr_reporting.cloud_schedule import delivery_key_for, is_report_window


CHILE = ZoneInfo("America/Santiago")


def test_cloud_window_is_weekdays_from_10_through_22_chile():
    monday = datetime(2026, 10, 5, tzinfo=CHILE)

    assert is_report_window(monday.replace(hour=9, minute=59)) is False
    assert is_report_window(monday.replace(hour=10, minute=0)) is True
    assert is_report_window(monday.replace(hour=22, minute=59)) is True
    assert is_report_window(monday.replace(hour=23, minute=0)) is False
    assert is_report_window(datetime(2026, 10, 10, 12, tzinfo=CHILE)) is False


def test_delivery_key_uses_chile_calendar_across_utc_offsets():
    summer_utc = datetime(2026, 10, 5, 13, 15, tzinfo=timezone.utc)
    winter_utc = datetime(2026, 6, 8, 14, 15, tzinfo=timezone.utc)

    assert delivery_key_for(summer_utc) == "hourly:2026-10-05:10:America/Santiago"
    assert delivery_key_for(winter_utc) == "hourly:2026-06-08:10:America/Santiago"
