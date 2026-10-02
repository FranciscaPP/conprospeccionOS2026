from __future__ import annotations

from collections import Counter
from datetime import date, time, timedelta
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
        elif due_at.date() == day - timedelta(days=1):
            completed_at = task.get("completed_at")
            if not task.get("completed") or (completed_at and completed_at.date() >= day):
                overdue.add(task_id)
    return TaskBaseline(day, client, frozenset(due_today), frozenset(overdue), task_types)


def task_progress(baseline: TaskBaseline, completed_ids: Iterable[str]) -> TaskProgress:
    completed = set(completed_ids)
    done_today = baseline.due_today_ids & completed
    done_overdue = baseline.overdue_ids & completed
    return TaskProgress(
        today_done=len(done_today),
        today_total=len(baseline.due_today_ids),
        overdue_done=len(done_overdue),
        overdue_total=len(baseline.overdue_ids),
        pending_today=len(baseline.due_today_ids - done_today),
        pending_overdue=len(baseline.overdue_ids - completed),
    )


def split_calls_by_period(calls: Iterable[dict], day: date) -> dict[str, list[dict]]:
    periods: dict[str, list[dict]] = {
        "scheduled": [],
        "before": [],
        "lunch": [],
        "after": [],
        "outside": [],
    }
    weekend = day.weekday() >= 5
    for call in calls:
        occurred_at = call.get("occurred_at")
        if occurred_at is None:
            periods["outside"].append(call)
            continue
        local_time = occurred_at.timetz().replace(tzinfo=None)
        if weekend:
            periods["outside"].append(call)
        elif local_time < time(11):
            periods["before"].append(call)
            periods["outside"].append(call)
        elif time(16) <= local_time < time(17):
            periods["lunch"].append(call)
            periods["outside"].append(call)
        elif local_time >= time(20):
            periods["after"].append(call)
            periods["outside"].append(call)
        else:
            periods["scheduled"].append(call)
    return periods


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
    answered_calls = [c for c in calls if int(c.get("duration_seconds") or 0) > min_talk_seconds]
    unanswered = [c for c in calls if int(c.get("duration_seconds") or 0) <= min_talk_seconds]
    retry_calls = sum(max(0, count - 1) for count in contacts.values())
    seen: Counter[str] = Counter()
    retry_seconds = 0
    for call in calls:
        contact_id = call.get("contact_id")
        if contact_id:
            seen[contact_id] += 1
            if seen[contact_id] > 1:
                retry_seconds += int(call.get("phone_seconds") or call.get("duration_seconds") or 0)
    return CallMetrics(
        calls=len(calls),
        unique_contacts=len(contacts),
        answered=len(answered_calls),
        unanswered=len(unanswered),
        retry_calls=retry_calls,
        answered_seconds=sum(int(c.get("duration_seconds") or 0) for c in answered_calls),
        unanswered_phone_seconds=sum(int(c.get("phone_seconds") or c.get("duration_seconds") or 0) for c in unanswered),
        retry_phone_seconds=retry_seconds,
        phone_seconds=sum(int(c.get("phone_seconds") or c.get("duration_seconds") or 0) for c in calls),
    )


def worked_time(
    elapsed_seconds: int,
    phone_seconds: int,
    responded_emails: int,
    responded_whatsapp: int = 0,
) -> dict[str, int]:
    worked = min(
        max(0, int(elapsed_seconds)),
        max(0, int(phone_seconds))
        + max(0, int(responded_emails)) * 300
        + max(0, int(responded_whatsapp)) * 300,
    )
    return {
        "worked_seconds": worked,
        "unregistered_seconds": max(0, int(elapsed_seconds) - worked),
    }


def elapsed_work_seconds(blocks: Iterable[WorkBlock], now, client: str | None = None) -> int:
    total = 0
    for block in blocks:
        if client is not None and block.client != client:
            continue
        end = min(block.end, now)
        if end > block.start:
            total += round((end - block.start).total_seconds())
    return total


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
