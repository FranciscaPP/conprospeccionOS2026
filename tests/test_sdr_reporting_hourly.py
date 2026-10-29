import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from sdr_reporting.config import work_blocks_for
from sdr_reporting.metrics import hourly_breakdown

CHILE = ZoneInfo("America/Santiago")
DAY = date(2026, 10, 2)


def at(hour, minute=0):
    return datetime(2026, 10, 2, hour, minute, tzinfo=CHILE)


def call(hour, minute, contact, phone_seconds, duration=0, client="balia"):
    return {
        "contact_id": contact,
        "occurred_at": at(hour, minute),
        "duration_seconds": duration,
        "phone_seconds": phone_seconds,
        "client": client,
    }


def test_hourly_breakdown_counts_calls_unique_contacts_and_idle_minutes():
    calls = [
        call(11, 5, "a", 600, 45),
        call(11, 20, "a", 300, 0),
        call(11, 40, "b", 900, 30),
    ]
    rows = hourly_breakdown(
        DAY, at(12, 30), work_blocks_for(DAY), calls,
        manual_message_times=[at(11, 50)],
        meeting_times=[at(11, 55), at(12, 10)],
    )
    assert [row["hour"] for row in rows] == [11, 12]
    first, second = rows
    assert first["client"] == "balia"
    assert first["calls_by_client"] == {"balia": 3}
    assert first["phone_seconds_by_client"] == {"balia": 1800}
    assert first["calls"] == 3
    assert first["contacts"] == 2
    assert first["answered"] == 2
    assert first["phone_seconds"] == 1800
    assert first["messages"] == 1
    assert first["elapsed_seconds"] == 3600
    assert first["worked_seconds"] == 1800 + 300
    assert first["idle_seconds"] == 3600 - 2100
    assert first["meetings"] == 1
    assert second["elapsed_seconds"] == 1800
    assert second["calls"] == 0
    assert second["idle_seconds"] == 1800
    assert second["meetings"] == 1


def test_hourly_breakdown_skips_lunch_hour_and_future_hours():
    rows = hourly_breakdown(DAY, at(17, 30), work_blocks_for(DAY), [], [], [])
    assert [row["hour"] for row in rows] == [11, 12, 13, 14, 15, 17]
    assert rows[-1]["elapsed_seconds"] == 1800


def test_idle_never_negative_when_calls_overflow_the_hour():
    rows = hourly_breakdown(
        DAY, at(11, 30), work_blocks_for(DAY), [call(11, 1, "a", 5000, 60)], [], [],
    )
    assert rows[0]["idle_seconds"] == 0
    assert rows[0]["worked_seconds"] == rows[0]["elapsed_seconds"]


def test_conprospeccion_is_detected_by_the_user_who_made_the_call():
    from sdr_reporting.config import CON_PROSPECCION_USER_ID, is_conprospeccion

    assert is_conprospeccion(CON_PROSPECCION_USER_ID)
    assert not is_conprospeccion("NC7mvmYoQQuKfINV1Mmp")
    assert not is_conprospeccion(None)


def test_hourly_breakdown_uses_real_clients_and_reconciles_with_summary():
    calls = [
        call(13, 5, "a", 90, 40, "conprospeccion"),
        call(13, 20, "b", 30, 10, "gbs"),
    ]

    rows = hourly_breakdown(DAY, at(14), work_blocks_for(DAY), calls, [], [])

    row = next(item for item in rows if item["hour"] == 13)
    assert row["client"] is None
    assert row["calls_by_client"] == {"conprospeccion": 1, "gbs": 1}
    assert row["phone_seconds_by_client"] == {"conprospeccion": 90, "gbs": 30}
    assert sum(row["calls_by_client"].values()) == row["calls"]
    assert sum(row["phone_seconds_by_client"].values()) == row["phone_seconds"]


def test_tabular_adds_conprospeccion_row_and_includes_it_in_totals():
    from test_sdr_reporting_tabular import sample_report
    from sdr_reporting.tabular import build_table_document

    report = sample_report()
    base_total = build_table_document(report)["calls_count"]["total"]["today"]
    report["conprospeccion"] = {"calls": 7, "answered": 2, "unanswered": 5,
                                "answered_seconds": 120, "unanswered_phone_seconds": 50, "phone_seconds": 170}
    document = build_table_document(report)
    assert document["calls_count"]["conprospeccion"]["today"] == 7
    assert document["calls_count"]["total"]["today"] == base_total
    assert document["calls_minutes"]["total"]["today"] >= 170
