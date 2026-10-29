from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from report_calls_live import GHLClient, LOCATION, token_for, to_chile
from report_tareas import ETIQUETA, fetch_tasks, tipo_de
from report_actividad import stage_moves

from .config import CHILE, CLIENTS, CON_PROSPECCION, is_conprospeccion, work_blocks_for
from .metrics import (
    build_task_baseline,
    call_metrics,
    elapsed_work_seconds,
    hourly_breakdown,
    operational_gaps,
    split_calls_by_period,
    task_progress,
    worked_time,
)
from .sources import (
    fetch_activity_messages,
    summarize_conversation_work,
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
        "assigned_to": task.get("assignedTo"),
        "contact_name": " ".join(
            value for value in (contact.get("firstName"), contact.get("lastName")) if value
        ).strip(),
    }


def _meeting_user_id(event: dict) -> str | None:
    return (
        event.get("assignedUserId")
        or event.get("assignedTo")
        or event.get("userId")
    )


def _partition_balia_records(records: list[dict], owner_field: str) -> tuple[list[dict], list[dict]]:
    prospecting = [item for item in records if is_conprospeccion(item.get(owner_field))]
    balia = [item for item in records if not is_conprospeccion(item.get(owner_field))]
    return balia, prospecting


def _outside_metrics(call_periods: dict[str, list[dict]]) -> dict[str, dict[str, int]]:
    outside_hours = {}
    for period in ("before", "lunch", "after", "outside"):
        period_metrics = call_metrics(call_periods[period])
        outside_hours["total" if period == "outside" else period] = {
            "count": period_metrics.calls,
            "phone_seconds": period_metrics.phone_seconds,
        }
    return outside_hours


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
                    "assigned_user_id": _meeting_user_id(event),
                })
    return sorted(meetings, key=lambda item: (item["chile"], item["title"]))


def _meetings_scheduled_today(ghl: GHLClient, location_id: str, day: date) -> list[dict]:
    """Reuniones AGENDADAS (creadas) hoy, con la hora en que se agendaron."""
    start = datetime.combine(day - timedelta(days=1), time.min, tzinfo=CHILE)
    end = start + timedelta(days=181)
    seen: set[str] = set()
    scheduled: list[dict] = []
    calendars = ghl.list_calendars(location_id).get("calendars") or []
    for calendar in calendars:
        payload = ghl.list_calendar_events(
            location_id,
            str(int(start.timestamp() * 1000)),
            str(int(end.timestamp() * 1000)),
            calendar_id=calendar.get("id"),
        )
        for event in payload.get("events") or payload.get("appointments") or []:
            event_id = str(event.get("id") or event.get("appointmentId") or "")
            if not event_id or event_id in seen:
                continue
            seen.add(event_id)
            created = to_chile(event.get("dateAdded") or event.get("createdAt"))
            status = (event.get("appointmentStatus") or event.get("status") or "").lower()
            if created and created.date() == day and status not in {"cancelled", "canceled", "noshow"}:
                starts_at = to_chile(event.get("startTime") or event.get("start") or event.get("startDate"))
                scheduled.append({
                    "id": event_id,
                    "title": event.get("title") or event.get("contactName") or "Reunión",
                    "created_at": created,
                    "starts_at": starts_at.strftime("%d/%m %H:%M") if starts_at else "N/D",
                    "assigned_user_id": _meeting_user_id(event),
                })
    return sorted(scheduled, key=lambda item: item["created_at"])


def build_live_report(day: date | None = None, now: datetime | None = None) -> dict:
    now = (now or datetime.now(CHILE)).astimezone(CHILE)
    day = day or now.date()
    clients: dict[str, dict] = {}
    calls_by_client: dict[str, list[dict]] = {}
    all_activity_events: list[dict] = []
    manual_message_times: list[datetime] = []
    conprospeccion: dict = {
        "tasks_done": 0,
        "tasks_total": 0,
        "tasks_overdue": 0,
        "tasks_today": 0,
        "tasks_completed": 0,
        "tasks_pending": 0,
        "task_percent": 0,
        "calls": 0,
        "contacts": 0,
        "answered": 0,
        "unanswered": 0,
        "answered_seconds": 0,
        "unanswered_phone_seconds": 0,
        "phone_seconds": 0,
        "meetings": [],
        "meetings_scheduled": [],
        "email": None,
        "whatsapp": None,
        "outside_hours": {},
        "work_time": {"worked_seconds": 0, "unregistered_seconds": 0},
        "all_calls": [],
    }
    alerts: list[str] = []
    for slug in CLIENTS:
        ghl = GHLClient(token_for(slug))
        location_id = LOCATION[slug]
        if not location_id:
            raise RuntimeError(f"Falta location de {slug}")
        raw_tasks = fetch_tasks(ghl, location_id)
        all_tasks = [_task_adapter(task) for task in raw_tasks if _task_id(task)]
        all_tasks = [
            task for task in all_tasks
            if "test" not in (task.get("contact_name") or "").lower().split()
        ]
        cp_tasks: list[dict] = []
        tasks = all_tasks
        if slug == "balia":
            tasks, cp_tasks = _partition_balia_records(all_tasks, "assigned_to")
        baseline = build_task_baseline(slug, tasks, day)
        completed_ids = {task["id"] for task in tasks if task["completed"]}
        progress = task_progress(baseline, completed_ids)

        w0 = datetime.combine(day, time.min, tzinfo=CHILE)
        history_start = w0 - timedelta(days=1)
        try:
            all_activity_messages_for_client = fetch_activity_messages(
                ghl, location_id, history_start, min(w0 + timedelta(days=1), now + timedelta(seconds=1))
            )
        except Exception as exc:
            all_activity_messages_for_client = []
            alerts.append(f"{CLIENTS[slug].name} · actividad multicanal no disponible ({type(exc).__name__}).")
        cp_activity_messages: list[dict] = []
        activity_messages = all_activity_messages_for_client
        if slug == "balia":
            cp_contact_ids = {task.get("contact_id") for task in cp_tasks if task.get("contact_id")}
            cp_activity_messages = [
                message for message in all_activity_messages_for_client
                if is_conprospeccion(message.get("user_id"))
                or message.get("contact_id") in cp_contact_ids
            ]
            cp_message_ids = {id(message) for message in cp_activity_messages}
            activity_messages = [
                message for message in all_activity_messages_for_client
                if id(message) not in cp_message_ids
            ]
        raw_calls = [
            message for message in activity_messages
            if message.get("message_type") == "TYPE_CALL"
            and (message.get("direction") or "outbound") == "outbound"
            and message.get("occurred_at")
            and message["occurred_at"].date() == day
        ]
        normalized_calls = [
            {
                "contact_id": call.get("contact_id"),
                "status": call.get("status"),
                "duration_seconds": int(call.get("duration_seconds") or 0),
                "phone_seconds": int(call.get("phone_seconds") or call.get("duration_seconds") or 0),
                "occurred_at": call.get("occurred_at"),
                "client": slug,
            }
            for call in raw_calls
        ]
        cp_calls: list[dict] = [
            {
                "contact_id": call.get("contact_id"),
                "status": call.get("status"),
                "duration_seconds": int(call.get("duration_seconds") or 0),
                "phone_seconds": int(call.get("phone_seconds") or call.get("duration_seconds") or 0),
                "occurred_at": call.get("occurred_at"),
                "client": "conprospeccion",
            }
            for call in cp_activity_messages
            if call.get("message_type") == "TYPE_CALL"
            and (call.get("direction") or "outbound") == "outbound"
            and call.get("occurred_at")
            and call["occurred_at"].date() == day
        ]
        if slug == "balia":
            cp_periods = split_calls_by_period(cp_calls, day)
            cp_metrics = call_metrics(cp_periods["scheduled"])
            cp_baseline = build_task_baseline("conprospeccion", cp_tasks, day)
            cp_completed_ids = {task["id"] for task in cp_tasks if task["completed"]}
            cp_progress = task_progress(cp_baseline, cp_completed_ids)
            cp_email = {
                **summarize_email_messages([
                    message for message in cp_activity_messages
                    if message.get("occurred_at") and message["occurred_at"].date() == day
                ]),
                **summarize_conversation_work(cp_activity_messages, day, "TYPE_EMAIL"),
            }
            cp_email["pending"] = cp_email["unanswered"]
            conprospeccion.update({
                "tasks_done": cp_progress.completed,
                "tasks_total": cp_progress.total,
                "tasks_overdue": cp_progress.overdue_total,
                "tasks_today": cp_progress.today_total,
                "tasks_completed": cp_progress.completed,
                "tasks_pending": cp_progress.pending,
                "task_percent": cp_progress.percent,
                "calls": cp_metrics.calls,
                "contacts": cp_metrics.unique_contacts,
                "answered": cp_metrics.answered,
                "unanswered": cp_metrics.unanswered,
                "answered_seconds": cp_metrics.answered_seconds,
                "unanswered_phone_seconds": cp_metrics.unanswered_phone_seconds,
                "phone_seconds": cp_metrics.phone_seconds,
                "outside_hours": _outside_metrics(cp_periods),
                "email": cp_email,
                "all_calls": cp_calls,
                "work_time": {
                    "worked_seconds": cp_metrics.phone_seconds + int(cp_email.get("responded") or 0) * 300,
                    "unregistered_seconds": 0,
                },
            })
            calls_by_client["conprospeccion"] = cp_calls
            all_activity_events.extend(
                {"occurred_at": call["occurred_at"]}
                for call in cp_calls if call.get("occurred_at")
            )
            all_activity_events.extend(
                {"occurred_at": task["completed_at"]}
                for task in cp_tasks
                if task.get("completed_at") and task["completed_at"].date() == day
            )
        call_periods = split_calls_by_period(normalized_calls, day)
        scheduled_calls = call_periods["scheduled"]
        calls_by_client[slug] = normalized_calls
        all_activity_events.extend(
            {"occurred_at": call["occurred_at"]}
            for call in normalized_calls if call.get("occurred_at")
        )
        calls = call_metrics(scheduled_calls)
        outside_hours = _outside_metrics(call_periods)
        try:
            current_messages = [
                message for message in activity_messages
                if message.get("occurred_at") and message["occurred_at"].date() == day
            ]
            email = {
                **summarize_email_messages(current_messages),
                **summarize_conversation_work(activity_messages, day, "TYPE_EMAIL"),
            }
            email["pending"] = email["unanswered"]
            whatsapp = None
            if slug == "bambutech":
                whatsapp = {
                    **summarize_whatsapp_messages(current_messages),
                    **summarize_conversation_work(activity_messages, day, "TYPE_WHATSAPP"),
                }
                whatsapp["pending"] = whatsapp["unanswered"]
                whatsapp["work_seconds"] = whatsapp["responded"] * 300
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

        manual_message_times.extend(
            message["occurred_at"] for message in all_activity_messages_for_client
            if message.get("message_type") in {"TYPE_EMAIL", "TYPE_WHATSAPP"}
            and message.get("direction") == "outbound"
            and message.get("source") in {"app", "bulk_actions"}
            and message.get("occurred_at") and message["occurred_at"].date() == day
        )
        try:
            meetings_scheduled = _meetings_scheduled_today(ghl, location_id, day)
            meetings_today = _meetings_today(ghl, location_id, day)
            if slug == "balia":
                meetings_scheduled, cp_meetings_scheduled = _partition_balia_records(
                    meetings_scheduled, "assigned_user_id"
                )
                meetings_today, cp_meetings_today = _partition_balia_records(
                    meetings_today, "assigned_user_id"
                )
                conprospeccion["meetings_scheduled"] = cp_meetings_scheduled
                conprospeccion["meetings"] = cp_meetings_today
        except Exception as exc:
            meetings_scheduled = []
            meetings_today = []
            alerts.append(f"{CLIENTS[slug].name} · reuniones agendadas no disponibles ({type(exc).__name__}).")

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
            int((whatsapp or {}).get("responded") or 0),
        )
        clients[slug] = {
            "tasks_done": progress.completed,
            "tasks_total": progress.total,
            "tasks_overdue": progress.overdue_total,
            "tasks_today": progress.today_total,
            "tasks_completed": progress.completed,
            "tasks_pending": progress.pending,
            "task_percent": progress.percent,
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
            "outside_hours": outside_hours,
            "gaps": gap_labels,
            "meetings": meetings_today,
            "meetings_scheduled": meetings_scheduled,
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
        call_slugs = (*CLIENTS, "conprospeccion")
        counts = {
            slug: sum(
                1 for call in calls_by_client.get(slug, [])
                if block.start <= call["occurred_at"] < block_end
            )
            for slug in call_slugs
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
    total_phone_seconds = sum(int(clients[slug].get("phone_seconds") or 0) for slug in CLIENTS) + int(
        conprospeccion.get("phone_seconds") or 0
    )
    responded_emails = sum(
        int((clients[slug].get("email") or {}).get("responded") or 0)
        for slug in CLIENTS
    ) + int((conprospeccion.get("email") or {}).get("responded") or 0)
    responded_whatsapp = sum(
        int((clients[slug].get("whatsapp") or {}).get("responded") or 0)
        for slug in CLIENTS
    )
    total_work = worked_time(
        elapsed_seconds,
        total_phone_seconds,
        responded_emails,
        responded_whatsapp,
    )
    hourly = hourly_breakdown(
        day, now, work_blocks_for(day),
        [call for calls in calls_by_client.values() for call in calls],
        manual_message_times,
        [m["created_at"] for slug in CLIENTS for m in clients[slug].get("meetings_scheduled", [])]
        + [m["created_at"] for m in conprospeccion.get("meetings_scheduled", [])],
    )
    return {
        "day": day,
        "cut": now,
        "sdr": "Nora",
        "clients": clients,
        "conprospeccion": {k: v for k, v in conprospeccion.items() if k != "all_calls"},
        "hourly": hourly,
        "work_time": {
            "elapsed_seconds": elapsed_seconds,
            "email_seconds": responded_emails * 300,
            "whatsapp_seconds": responded_whatsapp * 300,
            **total_work,
        },
        "comparison": None,
        "email_available": all(clients[slug].get("email") is not None for slug in CLIENTS),
        "baseline_available": False,
        "alerts": [*operational_alerts, *alerts][:3],
        "block_adherence": block_adherence,
    }
