from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Iterable

from report_calls_live import call_duration, call_status, fetch_messages, to_chile


MANUAL_EMAIL_SOURCES = {"app", "bulk_actions"}
MANUAL_WHATSAPP_SOURCES = {"app", "bulk_actions"}


def summarize_email_messages(messages: Iterable[dict]) -> dict[str, int]:
    by_conversation: dict[str, list[dict]] = defaultdict(list)
    for message in messages:
        if message.get("message_type") == "TYPE_EMAIL":
            by_conversation[str(message.get("conversation_id") or "")].append(message)

    received = responded = pending = new_manual = manual_sent = 0
    for thread in by_conversation.values():
        thread.sort(key=lambda item: item["occurred_at"])
        inbound_times = [m["occurred_at"] for m in thread if m.get("direction") == "inbound"]
        manual = [
            m for m in thread
            if m.get("direction") == "outbound" and m.get("source") in MANUAL_EMAIL_SOURCES
        ]
        manual_sent += len(manual)
        if inbound_times:
            received += 1
            if any(m["occurred_at"] > min(inbound_times) for m in manual):
                responded += 1
            else:
                pending += 1
        if manual and not any(t < manual[0]["occurred_at"] for t in inbound_times):
            new_manual += 1
    return {
        "received": received,
        "responded": responded,
        "pending": pending,
        "new_manual": new_manual,
        "manual_sent": manual_sent,
    }


def summarize_whatsapp_messages(messages: Iterable[dict]) -> dict[str, int]:
    by_conversation: dict[str, list[dict]] = defaultdict(list)
    for message in messages:
        if message.get("message_type") == "TYPE_WHATSAPP":
            by_conversation[str(message.get("conversation_id") or "")].append(message)

    manual_sent = automatic_sent = received = responded = pending = new_manual = 0
    for thread in by_conversation.values():
        thread.sort(key=lambda item: item["occurred_at"])
        inbound = [m for m in thread if m.get("direction") == "inbound"]
        manual = [
            m for m in thread
            if m.get("direction") == "outbound" and m.get("source") in MANUAL_WHATSAPP_SOURCES
        ]
        automatic = [
            m for m in thread
            if m.get("direction") == "outbound" and m.get("source") not in MANUAL_WHATSAPP_SOURCES
        ]
        manual_sent += len(manual)
        automatic_sent += len(automatic)
        received += len(inbound)
        if inbound:
            first_inbound = min(m["occurred_at"] for m in inbound)
            if any(m["occurred_at"] > first_inbound for m in manual):
                responded += 1
            else:
                pending += 1
        new_manual += sum(
            1 for message in manual
            if not any(item["occurred_at"] < message["occurred_at"] for item in inbound)
        )
    return {
        "manual_sent": manual_sent,
        "automatic_sent": automatic_sent,
        "received": received,
        "responded": responded,
        "pending": pending,
        "new_manual": new_manual,
        "work_seconds": new_manual * 60 + responded * 300,
    }


def fetch_activity_messages(ghl, location_id: str, start: datetime, end: datetime) -> list[dict]:
    start_ms = int(start.timestamp() * 1000)
    conversations: list[tuple[str, str | None]] = []
    start_after_date = start_after_id = None
    for _ in range(60):
        payload = ghl.search_conversations(
            location_id, limit=100,
            start_after_date=start_after_date, start_after_id=start_after_id,
        )
        page = payload.get("conversations") or []
        if not page:
            break
        stop = False
        for conversation in page:
            last_ms = conversation.get("lastMessageDate")
            if isinstance(last_ms, (int, float)) and last_ms < start_ms:
                stop = True
                break
            conversations.append((conversation["id"], conversation.get("contactId")))
        last = page[-1]
        start_after_date = last.get("lastMessageDate")
        start_after_id = last.get("id")
        if stop or len(page) < 100 or not start_after_date:
            break

    def load(item: tuple[str, str | None]) -> list[dict]:
        conversation_id, contact_id = item
        output = []
        for raw in fetch_messages(ghl, conversation_id):
            occurred_at = to_chile(raw.get("dateAdded"))
            if occurred_at is None or not start <= occurred_at < end:
                continue
            updated_at = to_chile(raw.get("dateUpdated"))
            duration = call_duration(raw) if raw.get("messageType") == "TYPE_CALL" else 0
            phone_seconds = 0
            if updated_at:
                phone_seconds = max(0, round((updated_at - occurred_at).total_seconds()))
                phone_seconds = min(phone_seconds, duration + 90 if duration else 60)
            output.append({
                "id": raw.get("id"),
                "conversation_id": conversation_id,
                "contact_id": raw.get("contactId") or contact_id,
                "message_type": raw.get("messageType"),
                "direction": raw.get("direction"),
                "source": raw.get("source"),
                "occurred_at": occurred_at,
                "status": call_status(raw),
                "duration_seconds": duration,
                "phone_seconds": phone_seconds,
            })
        return output

    messages: list[dict] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for batch in pool.map(load, conversations):
            messages.extend(batch)
    return messages
