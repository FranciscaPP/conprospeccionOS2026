from __future__ import annotations

import argparse
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any

from config import get_optional_env, get_settings
from ghl_client import GHLClient
from supabase_rest import SupabaseRestClient
from telegram_client import TelegramClient
from telegram_ghl_cards import (
    build_agendar_keyboard,
    build_agendar_prompt,
    build_already_status_text,
    build_status_changed_text,
    build_status_keyboard,
    build_status_prompt,
    build_tarea_keyboard,
    build_tarea_prompt,
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


PENDING_MANUAL_TASK: dict[int, dict[str, Any]] = {}  # chat_id -> {contact_id, step, titulo, descripcion, fecha_hora}

TASK_STEPS = ["titulo", "descripcion", "fecha_hora"]
TASK_STEP_PROMPTS = {
    "titulo": "¿Cuál es el título de la tarea?",
    "descripcion": "¿Descripción?",
    "fecha_hora": "¿Fecha y hora? (ej. \"mañana 11am\", \"viernes 3pm\")",
}

_WEEKDAY_NAMES = [
    ("lunes", 0), ("martes", 1), ("miercoles", 2), ("miércoles", 2),
    ("jueves", 3), ("viernes", 4), ("sabado", 5), ("sábado", 5), ("domingo", 6),
]

_TIME_PATTERN = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", re.IGNORECASE)


def parse_fecha_hora(texto: str) -> str | None:
    """Interpreta frases simples de fecha/hora ("mañana 11am", "viernes
    3pm"). Devuelve un ISO datetime en UTC, o None si no reconoce el
    formato — el llamador debe usar default_due_date() como respaldo."""
    if not texto:
        return None
    lowered = texto.strip().lower()
    now = datetime.now(timezone.utc)

    if "hoy" in lowered:
        target_date = (now).date()
    elif "manana" in lowered or "mañana" in lowered:
        target_date = (now + timedelta(days=1)).date()
    else:
        target_date = None
        for name, weekday in _WEEKDAY_NAMES:
            if name in lowered:
                days_ahead = (weekday - now.weekday()) % 7 or 7
                target_date = (now + timedelta(days=days_ahead)).date()
                break
        if target_date is None:
            return None

    match = _TIME_PATTERN.search(lowered)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    meridiem = (match.group(3) or "").lower()
    if meridiem == "pm" and hour < 12:
        hour += 12
    elif meridiem == "am" and hour == 12:
        hour = 0
    if not (0 <= hour <= 23) or not (0 <= minute <= 59):
        return None

    due = datetime(target_date.year, target_date.month, target_date.day, hour, minute, tzinfo=timezone.utc)
    return due.isoformat()


def handle_tarea_callback(parts: list[str], chat_id: int, telegram: TelegramClient) -> None:
    _, contact_id, modo = parts
    if modo == "auto":
        telegram.send_message(chat_id, "⚙️ Listo, no se crea una tarea manual — queda a cargo de la automatización del estatus que le pongas.")
        return
    PENDING_MANUAL_TASK[chat_id] = {"contact_id": contact_id, "step": "titulo"}
    telegram.send_message(chat_id, TASK_STEP_PROMPTS["titulo"])


def send_status_options(
    chat_id: str, nombre: str, contact_id: str, location_id: str, ghl: GHLClient, telegram: TelegramClient,
) -> None:
    custom_field_ids = ghl.custom_field_id_map(location_id)
    field_id = custom_field_ids.get("status_prospecto")
    if not field_id:
        telegram.send_message(chat_id, "⚠️ No encontré el campo STATUS PROSPECTO en esta location.")
        return
    ordered = order_status_options(ghl.custom_field_options(location_id, field_id))
    keyboard = build_status_keyboard(ordered, contact_id)
    telegram.send_message(chat_id, build_status_prompt(nombre), reply_markup=keyboard)


def handle_message(
    message: dict[str, Any], slug: str, telegram: TelegramClient, ghl: GHLClient,
    supabase: SupabaseRestClient, location_id: str,
) -> None:
    chat_id = message["chat"]["id"]
    if chat_id in PENDING_MANUAL_TASK and message.get("text"):
        pending = PENDING_MANUAL_TASK[chat_id]
        pending[pending["step"]] = message["text"].strip()
        current_index = TASK_STEPS.index(pending["step"])
        if current_index + 1 < len(TASK_STEPS):
            pending["step"] = TASK_STEPS[current_index + 1]
            telegram.send_message(chat_id, TASK_STEP_PROMPTS[pending["step"]])
        else:
            PENDING_MANUAL_TASK.pop(chat_id)
            due_iso = parse_fecha_hora(pending["fecha_hora"]) or default_due_date()
            ghl.create_task(
                pending["contact_id"], title=pending["titulo"][:100],
                due_date_iso=due_iso, body=pending.get("descripcion", ""),
            )
            telegram.send_message(chat_id, f"✅ Tarea creada: *{pending['titulo']}*")
        return

    if "reply_to_message" not in message:
        return
    reply_to_id = message["reply_to_message"]["message_id"]
    card = find_card(supabase, chat_id, reply_to_id)
    if not card:
        return

    nombre = card.get("prospect_name") or card.get("prospect_email")
    contact_id = card["ghl_contact_id"]

    send_status_options(chat_id, nombre, contact_id, location_id, ghl, telegram)
    telegram.send_message(chat_id, build_agendar_prompt(nombre), reply_markup=build_agendar_keyboard(contact_id))
    telegram.send_message(chat_id, build_tarea_prompt(nombre), reply_markup=build_tarea_keyboard(contact_id))


def handle_callback(callback: dict[str, Any], ghl: GHLClient, telegram: TelegramClient) -> None:
    data = callback.get("data") or ""
    parts = data.split(":", 2)
    if len(parts) != 3:
        return
    chat_id = callback["message"]["chat"]["id"]
    telegram.answer_callback_query(callback["id"])

    if parts[0] == "tarea":
        handle_tarea_callback(parts, chat_id, telegram)
        return

    if parts[0] != "status":
        return

    _, contact_id, idx_raw = parts
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
    try:
        settings = get_settings()
        supabase = SupabaseRestClient(settings.supabase_url, settings.supabase_secret_key)
        token = get_optional_env(f"TELEGRAM_BOT_{slug.upper()}_TOKEN")
        if not token:
            logging.warning("%s: sin TELEGRAM_BOT_%s_TOKEN, no arranca", slug, slug.upper())
            return

        try:
            telegram = TelegramClient(token)
            ghl = GHLClient(token_for_client(slug))
            location_id = location_for_client(supabase, slug)
        except Exception:
            logging.exception("%s: error en el arranque, no arranca", slug)
            return

        offset = None
        logging.info("%s: bot escuchando", slug)
        while True:
            try:
                for update in telegram.get_updates(offset=offset, timeout=30):
                    offset = update["update_id"] + 1
                    try:
                        if "callback_query" in update:
                            handle_callback(update["callback_query"], ghl, telegram)
                        elif "message" in update:
                            handle_message(update["message"], slug, telegram, ghl, supabase, location_id)
                    except Exception:
                        logging.exception("%s: error procesando update %s", slug, update.get("update_id"))
            except Exception:
                logging.exception("%s: error en el loop principal, reintentando en 10s", slug)
                time.sleep(10)
    except Exception:
        logging.exception("%s: error inesperado no manejado, el bot se detiene", slug)


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
