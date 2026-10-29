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


def hourly_breakdown(
    day: date,
    now,
    blocks: Iterable[WorkBlock],
    calls: Iterable[dict],
    manual_message_times: Iterable,
    meeting_times: Iterable,
    min_talk_seconds: int = 20,
) -> list[dict]:
    """Una fila por hora de horario laboral transcurrida: llamadas, minutos y tiempo sin trabajar."""
    blocks = list(blocks)
    calls = [c for c in calls if c.get("occurred_at")]
    message_times = list(manual_message_times)
    meeting_times = list(meeting_times)
    rows = []
    for hour in range(24):
        slot_start = now.replace(year=day.year, month=day.month, day=day.day,
                                 hour=hour, minute=0, second=0, microsecond=0)
        slot_end = slot_start + timedelta(hours=1)
        elapsed = 0
        expected_client = None
        for block in blocks:
            end = min(block.end, slot_end, now)
            start = max(block.start, slot_start)
            if end > start:
                elapsed += round((end - start).total_seconds())
                expected_client = expected_client or block.client
        if elapsed <= 0:
            continue
        in_hour = [c for c in calls if slot_start <= c["occurred_at"] < slot_end]
        phone = sum(int(c.get("phone_seconds") or c.get("duration_seconds") or 0) for c in in_hour)
        calls_by_client = Counter(str(c.get("client") or "unknown") for c in in_hour)
        phone_seconds_by_client: Counter[str] = Counter()
        for call in in_hour:
            phone_seconds_by_client[str(call.get("client") or "unknown")] += int(
                call.get("phone_seconds") or call.get("duration_seconds") or 0
            )
        messages = sum(1 for t in message_times if slot_start <= t < slot_end)
        worked = min(elapsed, phone + messages * 300)
        actual_clients = [client for client in calls_by_client if client != "unknown"]
        rows.append({
            "hour": hour,
            "expected_client": expected_client,
            "client": actual_clients[0] if len(actual_clients) == 1 else None,
            "calls_by_client": dict(calls_by_client),
            "phone_seconds_by_client": dict(phone_seconds_by_client),
            "calls": len(in_hour),
            "contacts": len({c.get("contact_id") for c in in_hour if c.get("contact_id")}),
            "answered": sum(1 for c in in_hour if int(c.get("duration_seconds") or 0) > min_talk_seconds),
            "phone_seconds": phone,
            "messages": messages,
            "elapsed_seconds": elapsed,
            "worked_seconds": worked,
            "idle_seconds": elapsed - worked,
            "meetings": sum(1 for t in meeting_times if slot_start <= t < slot_end),
        })
    return rows


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
