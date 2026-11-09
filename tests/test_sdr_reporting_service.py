import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from sdr_reporting.config import CON_PROSPECCION_USER_ID
from sdr_reporting.service import (
    _future_tasks_this_week,
    _meeting_user_id,
    _partition_balia_records,
    _task_adapter,
)


CHILE = ZoneInfo("America/Santiago")


def test_future_tasks_only_count_open_tasks_through_friday():
    day = date(2026, 11, 9)
    tasks = [
        {"due_at": datetime(2026, 11, 10, 10, tzinfo=CHILE), "completed": False},
        {"due_at": datetime(2026, 11, 10, 11, tzinfo=CHILE), "completed": True},
        {"due_at": datetime(2026, 11, 13, 10, tzinfo=CHILE), "completed": False},
        {"due_at": datetime(2026, 11, 16, 10, tzinfo=CHILE), "completed": False},
    ]
    assert _future_tasks_this_week(tasks, day) == {"2026-11-10": 1, "2026-11-13": 1}


def test_task_adapter_preserves_assigned_user():
    task = _task_adapter({
        "id": "task-1",
        "dueDate": "2026-10-29T15:00:00-03:00",
        "assignedTo": CON_PROSPECCION_USER_ID,
    })

    assert task["assigned_to"] == CON_PROSPECCION_USER_ID


def test_balia_records_are_partitioned_without_duplicates():
    records = [
        {"id": "cp", "assigned_to": CON_PROSPECCION_USER_ID},
        {"id": "balia", "assigned_to": "NC7mvmYoQQuKfINV1Mmp"},
    ]

    balia, prospecting = _partition_balia_records(records, "assigned_to")

    assert [item["id"] for item in balia] == ["balia"]
    assert [item["id"] for item in prospecting] == ["cp"]
    assert {item["id"] for item in balia}.isdisjoint(item["id"] for item in prospecting)


def test_meeting_user_id_uses_ghl_assigned_user_field():
    assert _meeting_user_id({"assignedUserId": CON_PROSPECCION_USER_ID}) == CON_PROSPECCION_USER_ID
