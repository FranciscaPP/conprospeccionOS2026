from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Iterable

from .models import CallMetrics, OperationalGap, TaskBaseline, TaskProgress
from .config import WorkBlock


def build_task_baseline(client: str, tasks: Iterable[dict], day: date) -> TaskBaseline:
    due_today: set[str] = set()
    overdue: set[str] = set()
    task_types: dict[str, str] = {}
    for task in tasks:
        task_id = str(task["id"])
        due_at = task.get("due_at")
        if due_at is None:
            continue
        task_types[task_id] = task.get("task_type") or "otro"
        if due_at.date() == day:
            due_today.add(task_id)
        elif due_at.date() < day:
            completed_at = task.get("completed_at")
            if not task.get("completed") or (completed_at and completed_at.date() >= day):
                overdue.add(task_id)
    return TaskBaseline(day, client, frozenset(due_today), frozenset(overdue), task_types)


def task_progress(baseline: TaskBaseline, completed_ids: Iterable[str]) -> TaskProgress:
    completed = set(completed_ids)
    scope = baseline.due_today_ids | baseline.overdue_ids
    done = scope & completed
    return TaskProgress(
        completed=len(done),
        total=len(scope),
        pending_today=len(baseline.due_today_ids - done),
        pending_overdue=len(baseline.overdue_ids - done),
    )


def largest_task_backlogs(rows: Iterable[dict]) -> tuple[dict | None, dict | None]:
    rows = list(rows)
    eligible = [row for row in rows if int(row.get("total") or 0) >= 3]
    percentage = min(
        eligible,
        key=lambda row: (int(row.get("done") or 0) / int(row["total"]), -int(row["total"])),
        default=None,
    )
    volume = max(
        rows,
        key=lambda row: int(row.get("total") or 0) - int(row.get("done") or 0),
        default=None,
    )
    return percentage, volume


def call_metrics(calls: Iterable[dict], min_talk_seconds: int = 20) -> CallMetrics:
    calls = list(calls)
    contacts = Counter(c.get("contact_id") for c in calls if c.get("contact_id"))
    answered_calls = [c for c in calls if (c.get("status") or "").lower() == "completed"]
    relevant = [c for c in answered_calls if int(c.get("duration_seconds") or 0) >= min_talk_seconds]
    unanswered = [c for c in calls if (c.get("status") or "").lower() in {"no-answer", "busy"}]
    return CallMetrics(
        calls=len(calls),
        unique_contacts=len(contacts),
        repeated_contacts=sum(1 for count in contacts.values() if count > 1),
        answered=len(answered_calls),
        unanswered=len(unanswered),
        relevant_conversations=len(relevant),
        conversation_seconds=sum(int(c.get("duration_seconds") or 0) for c in answered_calls),
        phone_seconds=sum(int(c.get("phone_seconds") or c.get("duration_seconds") or 0) for c in calls),
    )


def operational_gaps(
    block: WorkBlock | None,
    events: Iterable[dict],
    now,
    minimum_seconds: int = 20 * 60,
) -> list[OperationalGap]:
    if block is None or now <= block.start:
        return []
    end = min(now, block.end)
    points = sorted(
        event["occurred_at"]
        for event in events
        if event.get("occurred_at") and block.start <= event["occurred_at"] <= end
    )
    boundaries = [block.start, *points, end]
    gaps: list[OperationalGap] = []
    for start, stop in zip(boundaries, boundaries[1:]):
        if (stop - start).total_seconds() >= minimum_seconds:
            gaps.append(OperationalGap(start, stop))
    return gaps
