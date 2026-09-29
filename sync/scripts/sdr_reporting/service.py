from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from report_calls_live import GHLClient, LOCATION, token_for, to_chile
from report_tareas import ETIQUETA, fetch_tasks, tipo_de
from report_actividad import stage_moves

from .config import CHILE, CLIENTS, work_blocks_for
from .metrics import (
    build_task_baseline,
    call_metrics,
    elapsed_work_seconds,
    operational_gaps,
    task_progress,
    worked_time,
)
from .sources import (
    fetch_activity_messages,
    summarize_email_messages,
    summarize_whatsapp_messages,
)


def _task_id(task: dict) -> str:
    return str(task.get("_id") or task.get("id") or "")


def _task_adapter(task: dict) -> dict:
    contact = task.get("contactDetails") or {}
    return {
        "id": _task_id(task),
        "due_at": to_chile(task.get("dueDate")),
        "completed": bool(task.get("completed")),
        "completed_at": to_chile(task.get("dateUpdated")) if task.get("completed") else None,
        "task_type": tipo_de(task),
        "contact_id": task.get("contactId"),
        "contact_name": " ".join(
            value for value in (contact.get("firstName"), contact.get("lastName")) if value
        ).strip(),
    }


def _meetings_today(ghl: GHLClient, location_id: str, day: date) -> list[dict]:
    start = datetime.combine(day, time.min, tzinfo=CHILE)
    end = start + timedelta(days=1)
    seen: set[str] = set()
    meetings: list[dict] = []
    lima = ZoneInfo("America/Lima")
    calendars = ghl.list_calendars(location_id).get("calendars") or []
    for calendar in calendars:
        payload = ghl.list_calendar_events(
            location_id,
            str(int(start.timestamp() * 1000)),
            str(int(end.timestamp() * 1000)),
            calendar_id=calendar.get("id"),
        )
        events = payload.get("events") or payload.get("appointments") or []
        for event in events:
            event_id = str(event.get("id") or event.get("appointmentId") or "")
            if not event_id or event_id in seen:
                continue
            seen.add(event_id)
            status = (event.get("appointmentStatus") or event.get("status") or "").lower()
            starts_at = to_chile(event.get("startTime") or event.get("start") or event.get("startDate"))
            if starts_at and starts_at.date() == day and status not in {"cancelled", "canceled", "noshow"}:
                meetings.append({
                    "id": event_id,
                    "title": event.get("title") or event.get("contactName") or "Reunión",
                    "chile": starts_at.strftime("%H:%M"),
                    "peru": starts_at.astimezone(lima).strftime("%H:%M"),
                })
    return sorted(meetings, key=lambda item: (item["chile"], item["title"]))


def build_live_report(day: date | None = None, now: datetime | None = None) -> dict:
    now = (now or datetime.now(CHILE)).astimezone(CHILE)
    day = day or now.date()
    clients: dict[str, dict] = {}
    calls_by_client: dict[str, list[dict]] = {}
    all_activity_events: list[dict] = []
    alerts: list[str] = []
    for slug in CLIENTS:
        ghl = GHLClient(token_for(slug))
        location_id = LOCATION[slug]
        if not location_id:
            raise RuntimeError(f"Falta location de {slug}")
        raw_tasks = fetch_tasks(ghl, location_id)
        tasks = [_task_adapter(task) for task in raw_tasks if _task_id(task)]
        tasks = [
            task for task in tasks
            if "test" not in (task.get("contact_name") or "").lower().split()
        ]
        baseline = build_task_baseline(slug, tasks, day)
        completed_ids = {task["id"] for task in tasks if task["completed"]}
        progress = task_progress(baseline, completed_ids)

        w0 = datetime.combine(day, time.min, tzinfo=CHILE)
        try:
            activity_messages = fetch_activity_messages(
                ghl, location_id, w0, min(w0 + timedelta(days=1), now + timedelta(seconds=1))
            )
        except Exception as exc:
            activity_messages = []
            alerts.append(f"{CLIENTS[slug].name} · actividad multicanal no disponible ({type(exc).__name__}).")
        raw_calls = [
            message for message in activity_messages
            if message.get("message_type") == "TYPE_CALL"
            and (message.get("direction") or "outbound") == "outbound"
        ]
        normalized_calls = [
            {
                "contact_id": call.get("contact_id"),
                "status": call.get("status"),
                "duration_seconds": int(call.get("duration_seconds") or 0),
                "phone_seconds": int(call.get("phone_seconds") or call.get("duration_seconds") or 0),
                "occurred_at": call.get("occurred_at"),
            }
            for call in raw_calls
        ]
        calls_by_client[slug] = normalized_calls
        all_activity_events.extend(
            {"occurred_at": call["occurred_at"]}
            for call in normalized_calls if call.get("occurred_at")
        )
        calls = call_metrics(normalized_calls)
        try:
            email = None if slug == "balia" else summarize_email_messages(activity_messages)
            whatsapp = summarize_whatsapp_messages(activity_messages) if slug == "bambutech" else None
            movements = stage_moves(
                ghl, location_id, w0, min(w0 + timedelta(days=1), now + timedelta(seconds=1))
            )
            all_activity_events.extend(
                {"occurred_at": message["occurred_at"]}
                for message in activity_messages
                if message.get("message_type") == "TYPE_EMAIL"
                and (
                    message.get("direction") == "inbound"
                    or message.get("source") in {"app", "bulk_actions"}
                )
            )
            all_activity_events.extend(
                {"occurred_at": message["occurred_at"]}
                for message in activity_messages
                if message.get("message_type") == "TYPE_WHATSAPP"
                and (
                    message.get("direction") == "inbound"
                    or message.get("source") in {"app", "bulk_actions"}
                )
            )
        except Exception as exc:
            email = None
            whatsapp = None
            movements = {}
            alerts.append(f"{CLIENTS[slug].name} · movimientos no disponibles ({type(exc).__name__}).")

        by_type: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        scope = baseline.due_today_ids
        for task in tasks:
            if task["id"] not in scope:
                continue
            label = ETIQUETA.get(task["task_type"], task["task_type"])
            by_type[label][1] += 1
            if task["id"] in completed_ids:
                by_type[label][0] += 1

        overdue_contacts = []
        overdue_open = sorted(
            (
                task for task in tasks
                if task["id"] in baseline.overdue_ids and task["id"] not in completed_ids
            ),
            key=lambda task: (not bool(task.get("contact_name")), task["due_at"]),
        )
        for task in overdue_open[:3]:
            overdue_contacts.append({
                "name": task.get("contact_name") or "Contacto sin nombre",
                "days": max(1, (day - task["due_at"].date()).days),
                "type": ETIQUETA.get(task["task_type"], task["task_type"]),
            })

        gap_labels: list[str] = []
        events = [{"occurred_at": call["occurred_at"]} for call in normalized_calls if call.get("occurred_at")]
        events.extend(
            {"occurred_at": task["completed_at"]}
            for task in tasks
            if task.get("completed_at") and task["completed_at"].date() == day
        )
        all_activity_events.extend(
            {"occurred_at": task["completed_at"]}
            for task in tasks
            if task.get("completed_at") and task["completed_at"].date() == day
        )
        for block in work_blocks_for(day):
            if block.client != slug or block.start >= now:
                continue
            for gap in operational_gaps(block, events, now):
                gap_labels.append(
                    f"{gap.start.strftime('%H:%M')}–{gap.end.strftime('%H:%M')} · {round(gap.seconds / 60)} min sin actividad registrada"
                )

        if progress.total and progress.percent < 60:
            alerts.append(f"{CLIENTS[slug].name} · tareas en {progress.percent}%.")
        hour_start = now.replace(minute=0, second=0, microsecond=0)
        tasks_done_last_hour = sum(
            1 for task in tasks
            if task["id"] in baseline.due_today_ids
            and task.get("completed_at")
            and hour_start <= task["completed_at"] <= now
        )
        elapsed_seconds = elapsed_work_seconds(work_blocks_for(day), now, slug)
        client_work = worked_time(
            elapsed_seconds,
            calls.phone_seconds,
            int((email or {}).get("responded") or 0),
            int((whatsapp or {}).get("work_seconds") or 0),
        )
        clients[slug] = {
            "tasks_done": progress.completed,
            "tasks_total": progress.total,
            "pending_today": progress.pending_today,
            "overdue_pending": progress.pending_overdue,
            "tasks_done_last_hour": tasks_done_last_hour,
            "task_types": {key: tuple(value) for key, value in by_type.items()},
            "calls": calls.calls,
            "contacts": calls.unique_contacts,
            "repeated_contacts": calls.repeated_contacts,
            "answered": calls.answered,
            "unanswered": calls.unanswered,
            "answered_seconds": calls.answered_seconds,
            "unanswered_phone_seconds": calls.unanswered_phone_seconds,
            "conversation_seconds": calls.conversation_seconds,
            "phone_seconds": calls.phone_seconds,
            "gaps": gap_labels,
            "meetings": _meetings_today(ghl, location_id, day),
            "email": email,
            "whatsapp": whatsapp,
            "work_time": client_work,
            "movements": movements,
            "overdue_contacts": overdue_contacts,
        }
    block_adherence = []
    for block in work_blocks_for(day):
        if block.start >= now:
            continue
        block_end = min(block.end, now)
        counts = {
            slug: sum(
                1 for call in calls_by_client.get(slug, [])
                if block.start <= call["occurred_at"] < block_end
            )
            for slug in CLIENTS
        }
        gaps = operational_gaps(block, all_activity_events, now)
        block_adherence.append({
            "client": block.client,
            "start": block.start.strftime("%H:%M"),
            "end": block.end.strftime("%H:%M"),
            "correct_calls": counts[block.client],
            "other_calls": sum(counts.values()) - counts[block.client],
            "calls_by_client": counts,
            "no_activity_gaps": [
                f"{gap.start.strftime('%H:%M')}–{gap.end.strftime('%H:%M')} · {round(gap.seconds / 60)} min"
                for gap in gaps
            ],
        })
    operational_alerts = []
    for block in block_adherence:
        cfg = CLIENTS[block["client"]]
        total_calls = block["correct_calls"] + block["other_calls"]
        longest_gap = max(
            (
                int(gap.rsplit("·", 1)[1].replace("min", "").strip())
                for gap in block["no_activity_gaps"]
            ),
            default=0,
        )
        if total_calls <= 5:
            operational_alerts.append(
                f"{cfg.name} {block['start']}–{block['end']} · solo {total_calls} llamadas registradas."
            )
        elif block["correct_calls"] == 0 and block["other_calls"]:
            operational_alerts.append(
                f"{cfg.name} {block['start']}–{block['end']} · 0 llamadas al cliente; {block['other_calls']} a otros."
            )
        elif longest_gap >= 40:
            operational_alerts.append(
                f"{cfg.name} {block['start']}–{block['end']} · hueco de {longest_gap} min sin actividad registrada."
            )
    elapsed_seconds = elapsed_work_seconds(work_blocks_for(day), now)
    total_phone_seconds = sum(int(clients[slug].get("phone_seconds") or 0) for slug in CLIENTS)
    responded_emails = sum(
        int((clients[slug].get("email") or {}).get("responded") or 0)
        for slug in CLIENTS
    )
    whatsapp_seconds = sum(
        int((clients[slug].get("whatsapp") or {}).get("work_seconds") or 0)
        for slug in CLIENTS
    )
    total_work = worked_time(
        elapsed_seconds,
        total_phone_seconds,
        responded_emails,
        whatsapp_seconds,
    )
    return {
        "day": day,
        "cut": now,
        "sdr": "Nora",
        "clients": clients,
        "work_time": {
            "elapsed_seconds": elapsed_seconds,
            "email_seconds": responded_emails * 300,
            "whatsapp_seconds": whatsapp_seconds,
            **total_work,
        },
        "comparison": None,
        "email_available": all(clients[slug].get("email") is not None for slug in CLIENTS),
        "baseline_available": False,
        "alerts": [*operational_alerts, *alerts][:3],
        "block_adherence": block_adherence,
    }
