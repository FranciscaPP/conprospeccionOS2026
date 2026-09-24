from __future__ import annotations

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any

from config import get_optional_env, get_settings
from ghl_client import GHLClient
from supabase_rest import SupabaseRestClient
from telegram_client import TelegramClient
from telegram_ghl_cards import (
    build_already_status_text,
    build_status_changed_text,
    build_status_keyboard,
    order_status_options,
    parse_task_command,
)

CLIENTS = ["bambutech", "gbs", "balia"]


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)


def token_for_client(slug: str) -> str:
    env_key = {"gbs": "GHL_TOKEN_GBS_LOGISTICS"}.get(slug, f"GHL_TOKEN_{slug.upper()}")
    token = get_optional_env(env_key)
    if not token:
        raise RuntimeError(f"Falta {env_key} en .env/.env.txt")
    return token


def location_for_client(supabase: SupabaseRestClient, slug: str) -> str:
    rows = supabase.select("clientes", "ghl_location_id", slug=f"eq.{slug}")
    if not rows or not rows[0].get("ghl_location_id"):
        raise RuntimeError(f"Cliente {slug} sin ghl_location_id en Supabase")
    return rows[0]["ghl_location_id"]


def find_card(supabase: SupabaseRestClient, chat_id: int, message_id: int) -> dict[str, Any] | None:
    rows = supabase.select(
        "telegram_ghl_cards", "*",
        chat_id=f"eq.{chat_id}", telegram_message_id=f"eq.{message_id}",
    )
    return rows[0] if rows else None


def default_due_date() -> str:
    due = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=13, minute=0, second=0, microsecond=0)
    return due.isoformat()


def handle_task_command(
    task_text: str, chat_id: str, card: dict[str, Any], ghl: GHLClient, telegram: TelegramClient,
) -> None:
    ghl.create_task(card["ghl_contact_id"], title=task_text[:100], due_date_iso=default_due_date(), body=task_text)
    nombre = card.get("prospect_name") or card.get("prospect_email")
    telegram.send_message(chat_id, f"✅ Tarea creada para *{nombre}*: {task_text}")


def handle_status_prompt(
    chat_id: str, card: dict[str, Any], location_id: str, ghl: GHLClient, telegram: TelegramClient,
) -> None:
    custom_field_ids = ghl.custom_field_id_map(location_id)
    field_id = custom_field_ids.get("status_prospecto")
    if not field_id:
        telegram.send_message(chat_id, "⚠️ No encontré el campo STATUS PROSPECTO en esta location.")
        return
    ordered = order_status_options(ghl.custom_field_options(location_id, field_id))
    keyboard = build_status_keyboard(ordered, card["ghl_contact_id"])
    nombre = card.get("prospect_name") or card.get("prospect_email")
    telegram.send_message(chat_id, f"¿A qué estatus movemos a *{nombre}*?", reply_markup=keyboard)


def handle_message(
    message: dict[str, Any], slug: str, telegram: TelegramClient, ghl: GHLClient,
    supabase: SupabaseRestClient, location_id: str,
) -> None:
    if "reply_to_message" not in message:
        return
    chat_id = message["chat"]["id"]
    reply_to_id = message["reply_to_message"]["message_id"]
    card = find_card(supabase, chat_id, reply_to_id)
    if not card:
        return

    text = (message.get("text") or "").strip()
    task_text = parse_task_command(text)
    if task_text:
        handle_task_command(task_text, chat_id, card, ghl, telegram)
        return

    handle_status_prompt(chat_id, card, location_id, ghl, telegram)


def handle_callback(callback: dict[str, Any], ghl: GHLClient, telegram: TelegramClient) -> None:
    data = callback.get("data") or ""
    parts = data.split(":", 2)
    if len(parts) != 3 or parts[0] != "status":
        return
    _, contact_id, idx_raw = parts
    chat_id = callback["message"]["chat"]["id"]
    telegram.answer_callback_query(callback["id"])

    contact = ghl.get_contact(contact_id)["contact"]
    location_id = contact["locationId"]
    custom_field_ids = ghl.custom_field_id_map(location_id)
    field_id = custom_field_ids.get("status_prospecto")
    if not field_id:
        return
    ordered = order_status_options(ghl.custom_field_options(location_id, field_id))
    idx = int(idx_raw)
    if idx >= len(ordered):
        return
    new_status = ordered[idx]

    nombre = f"{contact.get('firstName') or ''} {contact.get('lastName') or ''}".strip() or "(contacto)"
    current_value = next(
        (cf.get("value") for cf in contact.get("customFields") or [] if cf.get("id") == field_id), None,
    )
    if current_value == new_status:
        telegram.send_message(chat_id, build_already_status_text(nombre, new_status))
        return

    ghl.update_custom_field(contact_id, field_id, new_status)
    telegram.send_message(chat_id, build_status_changed_text(nombre, new_status))


def run_client_bot(slug: str) -> None:
    settings = get_settings()
    supabase = SupabaseRestClient(settings.supabase_url, settings.supabase_secret_key)
    token = get_optional_env(f"TELEGRAM_BOT_{slug.upper()}_TOKEN")
    if not token:
        logging.warning("%s: sin TELEGRAM_BOT_%s_TOKEN, no arranca", slug, slug.upper())
        return

    telegram = TelegramClient(token)
    ghl = GHLClient(token_for_client(slug))
    location_id = location_for_client(supabase, slug)

    offset = None
    logging.info("%s: bot escuchando", slug)
    while True:
        for update in telegram.get_updates(offset=offset, timeout=30):
            offset = update["update_id"] + 1
            try:
                if "callback_query" in update:
                    handle_callback(update["callback_query"], ghl, telegram)
                elif "message" in update:
                    handle_message(update["message"], slug, telegram, ghl, supabase, location_id)
            except Exception:
                logging.exception("%s: error procesando update %s", slug, update.get("update_id"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Bot interactivo por cliente: mover estatus y crear tareas en GHL.")
    parser.add_argument("--client", choices=CLIENTS, help="Correr un solo cliente")
    args = parser.parse_args()
    setup_logging()

    targets = [args.client] if args.client else CLIENTS
    with ThreadPoolExecutor(max_workers=len(targets)) as pool:
        list(pool.map(run_client_bot, targets))


if __name__ == "__main__":
    main()
