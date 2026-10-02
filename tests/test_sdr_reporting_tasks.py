import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from sdr_reporting.metrics import build_task_baseline, largest_task_backlogs, task_progress

CHILE = ZoneInfo("America/Santiago")
DAY = date(2026, 9, 24)


def task(task_id, due, completed=False, kind="otro"):
    return {"id": task_id, "due_at": datetime.fromisoformat(due).replace(tzinfo=CHILE),
            "completed": completed, "task_type": kind}


def test_baseline_separates_overdue_from_due_today():
    tasks = [
        task("today-open", "2026-09-24T12:00:00"),
        task("today-done", "2026-09-24T13:00:00", True),
        task("old-open", "2026-09-23T12:00:00"),
        task("old-done", "2026-09-23T12:00:00", True),
        task("future", "2026-09-25T12:00:00"),
    ]
    baseline = build_task_baseline("gbs", tasks, DAY)
    assert baseline.due_today_ids == frozenset({"today-open", "today-done"})
    assert baseline.overdue_ids == frozenset({"old-open"})
    assert baseline.total == 3


def test_older_task_is_not_part_of_previous_day_late_count():
    resolved = task("old-resolved", "2026-09-22T12:00:00", True)
    resolved["completed_at"] = datetime(2026, 9, 24, 14, 0, tzinfo=CHILE)
    baseline = build_task_baseline("gbs", [resolved], DAY)
    assert baseline.overdue_ids == frozenset()


def test_progress_keeps_original_denominator_and_separates_pending():
    baseline = build_task_baseline("gbs", [
        task("today-open", "2026-09-24T12:00:00"),
        task("today-done", "2026-09-24T13:00:00", kind="nuevos"),
        task("old-open", "2026-09-22T12:00:00", kind="coordinando"),
    ], DAY)
    progress = task_progress(baseline, {"old-open", "today-done"})
    assert progress.today_done == 1
    assert progress.today_total == 2
    assert progress.pending_today == 1
    assert progress.pending_overdue == 0


def test_progress_combines_previous_day_and_today_for_tabular_report():
    baseline = build_task_baseline("gbs", [
        task("today-open", "2026-09-24T12:00:00"),
        task("today-done", "2026-09-24T13:00:00", kind="nuevos"),
        task("yesterday", "2026-09-23T12:00:00", kind="coordinando"),
    ], DAY)

    progress = task_progress(baseline, {"yesterday", "today-done"})

    assert progress.overdue_total == 1
    assert progress.today_total == 2
    assert progress.completed == 2
    assert progress.total == 3
    assert progress.pending == 1
    assert progress.percent == 67


def test_only_previous_day_open_tasks_are_reported_as_late():
    baseline = build_task_baseline("gbs", [
        task("yesterday", "2026-09-23T12:00:00"),
        task("older", "2026-09-22T12:00:00"),
    ], DAY)
    assert baseline.overdue_ids == frozenset({"yesterday"})


def test_largest_percentage_backlog_requires_three_tasks():
    rows = [
        {"client": "gbs", "task_type": "raro", "done": 0, "total": 1},
        {"client": "gbs", "task_type": "coordinando", "done": 2, "total": 5},
        {"client": "balia", "task_type": "nuevos", "done": 5, "total": 10},
    ]
    percentage, volume = largest_task_backlogs(rows)
    assert percentage["task_type"] == "coordinando"
    assert volume["task_type"] == "nuevos"
