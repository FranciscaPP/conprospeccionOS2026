from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from config import get_optional_env, get_settings
from ghl_client import GHLClient
from supabase_rest import SupabaseRestClient


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def token_for_client(client: dict[str, Any]) -> str:
    token = get_optional_env(f"GHL_TOKEN_{client['slug'].upper()}")
    if not token:
        raise RuntimeError(f"Falta GHL_TOKEN_{client['slug'].upper()}")
    return token


def active_clients(supabase: SupabaseRestClient) -> list[dict[str, Any]]:
    rows = supabase.select("clientes", "nombre,slug,ghl_location_id", order="nombre.asc")
    return [row for row in rows if row.get("ghl_location_id")]


def owner_maps(supabase: SupabaseRestClient) -> dict[tuple[str, str], str]:
    rows = supabase.select("sdr_cliente", "cliente_slug,sdr_slug,ghl_user_id")
    direct = {(row["cliente_slug"], row["ghl_user_id"]): row["sdr_slug"] for row in rows if row.get("ghl_user_id")}
    users = supabase.select_all("ghl_users", "cliente_slug,ghl_user_id,sdr_slug")
    for user in users:
        if user.get("sdr_slug"):
            direct[(user["cliente_slug"], user["ghl_user_id"])] = user["sdr_slug"]
    return direct


def contact_map(supabase: SupabaseRestClient) -> dict[str, dict[str, Any]]:
    rows = supabase.select_all("contactos", "ghl_contact_id,cliente_slug,sdr_slug,ghl_owner_user_id,telefono")
    return {row["ghl_contact_id"]: row for row in rows if row.get("ghl_contact_id")}


def message_pages(ghl: GHLClient, conversation_id: str, max_pages: int | None = None) -> list[dict[str, Any]]:
    messages = []
    last_message_id = None
    page = 0
    while True:
        page += 1
        if max_pages and page > max_pages:
            break
        payload = ghl.list_conversation_messages(conversation_id, limit=100, last_message_id=last_message_id)
        wrapper = payload.get("messages") or {}
        page_messages = wrapper.get("messages") or []
        messages.extend(page_messages)
        if not wrapper.get("nextPage") or not page_messages:
            break
        last_message_id = wrapper.get("lastMessageId") or page_messages[-1].get("id")
        if not last_message_id:
            break
    return messages


def conversation_pages(ghl: GHLClient, location_id: str, max_conversations: int | None = None, max_pages: int | None = None) -> list[dict[str, Any]]:
    conversations: list[dict[str, Any]] = []
    start_after_date = None
    start_after_id = None
    page = 0
    page_size = 100
    while True:
        page += 1
        if max_pages and page > max_pages:
            break
        remaining = max_conversations - len(conversations) if max_conversations else page_size
        limit = min(page_size, remaining) if max_conversations else page_size
        if limit <= 0:
            break
        payload = ghl.search_conversations(
            location_id,
            limit=limit,
            start_after_date=start_after_date,
            start_after_id=start_after_id,
        )
        page_conversations = payload.get("conversations") or []
        conversations.extend(page_conversations)
        if len(page_conversations) < limit:
            break
        last = page_conversations[-1]
        start_after_date = last.get("lastMessageDate")
        start_after_id = last.get("id")
        if not start_after_date or not start_after_id:
            break
        if max_conversations and len(conversations) >= max_conversations:
            break
    return conversations


def normalize_call(message: dict[str, Any], conversation: dict[str, Any], client: dict[str, Any], owner_by_user: dict[tuple[str, str], str], contacts: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    if message.get("messageType") != "TYPE_CALL":
        return None
    message_id = message.get("id")
    if not message_id:
        return None
    contact_id = message.get("contactId") or conversation.get("contactId")
    user_id = message.get("userId") or conversation.get("assignedTo")
    contact = contacts.get(contact_id or "", {})
    sdr_slug = owner_by_user.get((client["slug"], user_id)) or contact.get("sdr_slug")
    dt = parse_dt(message.get("dateAdded"))
    duration = ((message.get("meta") or {}).get("call") or {}).get("duration")
    try:
        duration_seconds = int(round(float(duration))) if duration is not None else 0
    except (TypeError, ValueError):
        duration_seconds = 0
    return {
        "ghl_call_id": message_id,
        "conversation_id": message.get("conversationId") or conversation.get("id"),
        "cliente_slug": client["slug"],
        "sdr_slug": sdr_slug,
        "ghl_contact_id": contact_id,
        "ghl_owner_user_id": user_id,
        "location_id": message.get("locationId") or client["ghl_location_id"],
        "fecha": dt.date().isoformat() if dt else None,
        "hora": dt.time().replace(tzinfo=None).isoformat() if dt else None,
        "started_at": message.get("dateAdded"),
        "duracion_segundos": duration_seconds,
        "duracion_minutos": int(round(duration_seconds / 60)),
        "direccion": message.get("direction"),
        "resultado": message.get("status") or (((message.get("meta") or {}).get("call") or {}).get("status")),
        "telefono": message.get("to") or message.get("from") or contact.get("telefono"),
        "mensaje_tipo": message.get("messageType"),
        "source": message.get("source"),
        "raw_data": message,
        "synced_at": iso_now(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sincroniza llamadas desde Conversations TYPE_CALL de GHL.")
    parser.add_argument("--client-slug")
    parser.add_argument("--max-conversations", type=int)
    parser.add_argument("--max-conversation-pages", type=int)
    parser.add_argument("--max-message-pages", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    setup_logging()
    settings = get_settings()
    supabase = SupabaseRestClient(settings.supabase_url, settings.supabase_secret_key)
    clients = active_clients(supabase)
    if args.client_slug:
        clients = [client for client in clients if client["slug"] == args.client_slug]
    owner_by_user = owner_maps(supabase)
    contacts = contact_map(supabase)
    stats: dict[str, Any] = {"clients": {}, "dry_run": args.dry_run}
    errors = []

    for client in clients:
        try:
            ghl = GHLClient(token_for_client(client))
            conversations = conversation_pages(
                ghl,
                client["ghl_location_id"],
                max_conversations=args.max_conversations,
                max_pages=args.max_conversation_pages,
            )
            rows = []
            logging.info("%s conversaciones revisadas: %s", client["nombre"], len(conversations))
            for conversation in conversations:
                # Only fetch details when the summary indicates calls/phone activity.
                if conversation.get("lastMessageType") != "TYPE_CALL" and conversation.get("type") != "TYPE_PHONE":
                    continue
                messages = message_pages(ghl, conversation["id"], args.max_message_pages)
                for message in messages:
                    row = normalize_call(message, conversation, client, owner_by_user, contacts)
                    if row:
                        rows.append(row)
            stats["clients"][client["slug"]] = {"llamadas": len(rows), "conversaciones": len(conversations)}
            logging.info("%s llamadas detectadas: %s", client["nombre"], len(rows))
            if rows and not args.dry_run:
                for index in range(0, len(rows), 100):
                    supabase.upsert("llamadas", rows[index : index + 100], "ghl_call_id")
        except httpx.HTTPStatusError as exc:
            logging.error("%s fallo HTTP %s: %s", client["nombre"], exc.response.status_code, exc.response.text[:300])
            errors.append({"cliente": client["slug"], "status": exc.response.status_code, "body": exc.response.text[:500]})
        except Exception as exc:
            logging.error("%s fallo: %s", client["nombre"], exc)
            errors.append({"cliente": client["slug"], "error": str(exc)})

    if not args.dry_run:
        supabase.insert("sync_runs", {"source": "ghl", "entity": "llamadas", "status": "success" if not errors else "partial_error", "stats": stats, "errors": errors})
    logging.info("Sync llamadas terminado: %s", stats)


if __name__ == "__main__":
    main()
