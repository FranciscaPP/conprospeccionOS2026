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


PENDING_MANUAL_TASK: dict[tuple[str, int], dict[str, Any]] = {}  # (slug, chat_id) -> {contact_id, step, titulo, descripcion, fecha_hora}
PENDING_EMAIL_REPLY: dict[tuple[str, int], dict[str, str]] = {}  # (slug, chat_id) -> {contact_id, account_email, to, subject, references}
PENDING_AGENDAR_SLOTS: dict[tuple[str, int], dict[str, str]] = {}  # (slug, chat_id) -> {index_str: slot_iso}
# (slug, chat_id) -> {contact_id, slot_iso, stage: "title"|"confirm", titulo?}
# stage "title": el proximo texto se guarda como titulo y se pasa a "confirm".
# stage "confirm": el proximo texto se evalua como si/no antes de agendar de verdad.
PENDING_AGENDAR_TITLE: dict[tuple[str, int], dict[str, str]] = {}

# Las 3 lineas de arriba (menos PENDING_AGENDAR_SLOTS, que se elige con botones,
# no con texto libre) son "esperando la proxima respuesta de texto de este chat".
# Solo una puede estar activa a la vez por (slug, chat_id) — si no se limpian
# entre si, un texto sin relacion enviado despues de arrancar un segundo flujo
# se cuela como respuesta del primero (ver incidente Task 25: colaba como
# titulo de reunion y creaba una cita real sin confirmar).
_PENDING_TEXT_DICTS = (PENDING_EMAIL_REPLY, PENDING_MANUAL_TASK, PENDING_AGENDAR_TITLE)

_CONFIRMACIONES_AFIRMATIVAS = {"si", "sí", "yes", "confirmar"}


def _clear_pending(slug: str, chat_id: int) -> None:
    """Cancela cualquier otro flujo de 'esperando texto libre' pendiente
    para este (slug, chat_id) antes de arrancar uno nuevo."""
    key = (slug, chat_id)
    for pending_dict in _PENDING_TEXT_DICTS:
        pending_dict.pop(key, None)


def _is_confirmacion_afirmativa(texto: str) -> bool:
    return texto.strip().lower() in _CONFIRMACIONES_AFIRMATIVAS

# Unico calendario configurado hasta ahora (Task 24) — Agenda BambuTech
# Services Michelle N, calendario de trabajo de Norma. gbs/balia todavia no
# tienen calendario cableado.
BAMBUTECH_CALENDAR_ID = "uB5sjspYMHvb42qeYVrj"
BAMBUTECH_AGENDAR_TIMEZONE = "America/Mexico_City"

_DIAS_CORTOS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
_MESES_CORTOS = ["", "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
_DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
_MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

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

# Solo matchea numeros que claramente son una hora: pegados a am/pm, con
# minutos separados por ":", o precedidos por "a las"/"las". Un numero suelto
# (ej. el "20" de "20 de noviembre") no matchea ninguna de las 3 alternativas.
_TIME_PATTERN = re.compile(
    r"(?:a\s+las|las)\s+(?P<h1>\d{1,2})(?::(?P<m1>\d{2}))?\s*(?P<mer1>am|pm)?"
    r"|(?P<h2>\d{1,2}):(?P<m2>\d{2})\s*(?P<mer2>am|pm)?"
    r"|(?P<h3>\d{1,2})\s*(?P<mer3>am|pm)\b",
    re.IGNORECASE,
)


def _extract_time(match: re.Match[str]) -> tuple[int, int, str] | None:
    groups = match.groupdict()
    for h_key, m_key, mer_key in (("h1", "m1", "mer1"), ("h2", "m2", "mer2"), ("h3", None, "mer3")):
        if groups.get(h_key) is not None:
            hour = int(groups[h_key])
            minute = int(groups[m_key]) if m_key and groups.get(m_key) else 0
            meridiem = (groups.get(mer_key) or "").lower()
            return hour, minute, meridiem
    return None


def parse_fecha_hora(texto: str) -> str | None:
    """Interpreta frases simples de fecha/hora ("mañana 11am", "viernes
    3pm", "pasado mañana 10am"). Devuelve un ISO datetime en UTC, o None si
    no reconoce el formato con confianza — el llamador debe usar
    default_due_date() como respaldo en vez de arriesgar un valor mal
    interpretado."""
    if not texto:
        return None
    lowered = texto.strip().lower()
    now = datetime.now(timezone.utc)

    if "hoy" in lowered:
        target_date = now.date()
    elif "pasado" in lowered and ("manana" in lowered or "mañana" in lowered):
        # "pasado mañana" contiene la subcadena "mañana" — hay que
        # descartarla explícitamente antes del chequeo de "mañana" sola,
        # o quedaría mal interpretado como "mañana" (un día de menos).
        target_date = (now + timedelta(days=2)).date()
    elif "manana" in lowered or "mañana" in lowered:
        target_date = (now + timedelta(days=1)).date()
    else:
        # Si mencionan más de un día de la semana (ej. "no puedo el lunes,
        # mejor el viernes"), nos quedamos con el que aparece más a la
        # derecha en el texto — es el que la persona quiso decir al final.
        last_pos = -1
        last_weekday = None
        for name, weekday in _WEEKDAY_NAMES:
            pos = lowered.rfind(name)
            if pos > last_pos:
                last_pos = pos
                last_weekday = weekday
        if last_weekday is None:
            return None
        days_ahead = (last_weekday - now.weekday()) % 7 or 7
        target_date = (now + timedelta(days=days_ahead)).date()

    match = _TIME_PATTERN.search(lowered)
    if not match:
        return None
    extracted = _extract_time(match)
    if extracted is None:
        return None
    hour, minute, meridiem = extracted
    if meridiem == "pm" and hour < 12:
        hour += 12
    elif meridiem == "am" and hour == 12:
        hour = 0
    if not (0 <= hour <= 23) or not (0 <= minute <= 59):
        return None

    due = datetime(target_date.year, target_date.month, target_date.day, hour, minute, tzinfo=timezone.utc)
    return due.isoformat()


def handle_tarea_callback(parts: list[str], chat_id: int, slug: str, telegram: TelegramClient) -> None:
    _, contact_id, modo = parts
    if modo == "auto":
        telegram.send_message(chat_id, "⚙️ Listo, no se crea una tarea manual — queda a cargo de la automatización del estatus que le pongas.")
        return
    # Clave (slug, chat_id): el mismo chat_id de Telegram identifica a la
    # misma persona en los 3 bots de cliente (bambutech/gbs/balia) — sin el
    # slug, arrancar el flujo manual en un bot y responder en otro
    # contaminaria la tarea del cliente equivocado.
    _clear_pending(slug, chat_id)
    PENDING_MANUAL_TASK[(slug, chat_id)] = {"contact_id": contact_id, "step": "titulo"}
    telegram.send_message(chat_id, TASK_STEP_PROMPTS["titulo"])


def handle_email_callback(contact_id: str, chat_id: int, slug: str, ghl: GHLClient, telegram: TelegramClient) -> None:
    from bambutech_mailboxes import find_reply_thread

    contact = ghl.get_contact(contact_id)["contact"]
    prospect_email = contact.get("email")
    if not prospect_email:
        telegram.send_message(chat_id, "⚠️ Este contacto no tiene correo cargado.")
        return

    thread = find_reply_thread(prospect_email)
    if not thread:
        telegram.send_message(chat_id, "⚠️ No encontré el correo real de este prospecto en las casillas de BambuTech.")
        return

    # Clave (slug, chat_id): mismo motivo que PENDING_MANUAL_TASK — el mismo
    # chat_id de Telegram identifica a la misma persona en los 3 bots de
    # cliente, sin el slug un reply cruzaria clientes.
    _clear_pending(slug, chat_id)
    PENDING_EMAIL_REPLY[(slug, chat_id)] = {
        "contact_id": contact_id,
        "account_email": thread["account_email"],
        "to": prospect_email,
        "subject": thread["subject"],
        "references": thread["references"] or "",
    }
    preview = thread["body"].strip().replace("\r\n", " ").replace("\n", " ")[:500]
    telegram.send_message(
        chat_id,
        f"📨 Esto escribió el prospecto (desde `{thread['account_email']}`):\n\n_{preview}_\n\n"
        "Escribime la respuesta que quieras mandar.",
    )


def _format_slot_short(slot_iso: str) -> str:
    """Etiqueta corta para el boton (ej. 'lun 28-sep 10:00')."""
    dt = datetime.fromisoformat(slot_iso)
    return f"{_DIAS_CORTOS[dt.weekday()]} {dt.day}-{_MESES_CORTOS[dt.month]} {dt.strftime('%H:%M')}"


def _format_slot_long(slot_iso: str) -> str:
    """Fecha legible para el mensaje de confirmacion (ej. 'lunes 28 de septiembre a las 10:00')."""
    dt = datetime.fromisoformat(slot_iso)
    return f"{_DIAS[dt.weekday()]} {dt.day} de {_MESES[dt.month]} a las {dt.strftime('%H:%M')}"


def handle_agendar_callback(contact_id: str, chat_id: int, slug: str, ghl: GHLClient, telegram: TelegramClient) -> None:
    # Solo BambuTech tiene calendario cableado (Task 24) — gbs/balia no
    # tienen la Agenda de GHL configurada todavia.
    if slug != "bambutech":
        telegram.send_message(chat_id, "⚠️ Todavía no está configurado el calendario de este cliente")
        return

    now_ms = int(time.time() * 1000)
    week_ms = now_ms + 7 * 24 * 3600 * 1000
    try:
        raw = ghl.free_slots(BAMBUTECH_CALENDAR_ID, now_ms, week_ms, BAMBUTECH_AGENDAR_TIMEZONE)
    except Exception:
        logging.exception("%s: error consultando horarios libres para %s", slug, contact_id)
        telegram.send_message(chat_id, "⚠️ No pude traer los horarios disponibles del calendario. Probá de nuevo en un rato.")
        return

    # La respuesta de GHL viene como {"YYYY-MM-DD": {"slots": [iso, ...]}, ...,
    # "traceId": "..."} — hay que aplanar los dias y descartar el traceId.
    slots: list[str] = []
    for key, value in raw.items():
        if key == "traceId" or not isinstance(value, dict):
            continue
        slots.extend(value.get("slots") or [])
    slots.sort()
    slots = slots[:6]

    if not slots:
        telegram.send_message(chat_id, "⚠️ No hay horarios libres en los próximos 7 días en este calendario.")
        return

    # Clave (slug, chat_id): mismo motivo que PENDING_MANUAL_TASK/PENDING_EMAIL_REPLY.
    # Se guardan los ISO completos indexados por posicion en vez de mandarlos
    # en el callback_data — un ISO + el contact_id de GHL puede superar el
    # limite de 64 bytes de Telegram.
    PENDING_AGENDAR_SLOTS[(slug, chat_id)] = {str(i): slot for i, slot in enumerate(slots)}

    keyboard = {
        "inline_keyboard": [
            [{"text": _format_slot_short(slot), "callback_data": f"agendar_slot:{contact_id}:{i}"}]
            for i, slot in enumerate(slots)
        ]
    }
    telegram.send_message(chat_id, "🕒 Horarios disponibles (hora México):", reply_markup=keyboard)


def handle_agendar_slot_callback(
    contact_id: str, idx_raw: str, chat_id: int, slug: str, ghl: GHLClient, telegram: TelegramClient,
) -> None:
    pending = PENDING_AGENDAR_SLOTS.get((slug, chat_id))
    slot_iso = pending.get(idx_raw) if pending else None
    if not slot_iso:
        telegram.send_message(chat_id, "⚠️ Ese horario ya no está disponible, pedí la lista de nuevo.")
        return

    # No se agenda todavia — falta el titulo (y despues la confirmacion). Se
    # guarda el slot elegido y se espera el proximo mensaje de texto de este
    # chat (mismo patron secuencial que PENDING_MANUAL_TASK: una pregunta,
    # una respuesta). _clear_pending cancela cualquier otro flujo de texto
    # libre que hubiera quedado pendiente (ej. una tarea manual a medio
    # completar) para que no se mezcle con este.
    PENDING_AGENDAR_SLOTS.pop((slug, chat_id), None)
    _clear_pending(slug, chat_id)
    PENDING_AGENDAR_TITLE[(slug, chat_id)] = {"contact_id": contact_id, "slot_iso": slot_iso, "stage": "title"}
    telegram.send_message(chat_id, "¿Qué título le ponemos a la reunión?")


def _nombre_contacto(contact: dict[str, Any]) -> str:
    return f"{contact.get('firstName') or ''} {contact.get('lastName') or ''}".strip() or "(contacto)"


def _build_agendar_confirmation_text(pending: dict[str, str], titulo: str, ghl: GHLClient) -> str:
    contact = ghl.get_contact(pending["contact_id"])["contact"]
    nombre = _nombre_contacto(contact)
    fecha = _format_slot_long(pending["slot_iso"])
    return f"¿Confirmás agendar con {nombre} el {fecha} con el título '{titulo}'? Respondé 'si' para confirmar."


def _complete_agendar(pending: dict[str, str], titulo: str, chat_id: int, ghl: GHLClient, telegram: TelegramClient) -> None:
    # Capa de seguridad #2: esta funcion solo se llama despues de que el SDR
    # confirmo explicitamente (ver handle_message, stage "confirm") — nunca
    # directo desde el texto del titulo, para que un mensaje sin relacion no
    # pueda crear una cita real por si solo.
    contact_id = pending["contact_id"]
    slot_iso = pending["slot_iso"]
    contact = ghl.get_contact(contact_id)["contact"]
    location_id = contact["locationId"]
    nombre = _nombre_contacto(contact)

    ghl.create_appointment(BAMBUTECH_CALENDAR_ID, location_id, contact_id, slot_iso, titulo)
    telegram.send_message(
        chat_id,
        f"✅ Reunión agendada con {nombre} para {_format_slot_long(slot_iso)} — *{titulo}*.",
    )


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
    telegram.send_message(chat_id, build_status_prompt(nombre, contact_id), reply_markup=keyboard)


def handle_message(
    message: dict[str, Any], slug: str, telegram: TelegramClient, ghl: GHLClient,
    supabase: SupabaseRestClient, location_id: str,
) -> None:
    chat_id = message["chat"]["id"]
    pending_key = (slug, chat_id)

    if pending_key in PENDING_EMAIL_REPLY and message.get("text"):
        from bambutech_mailboxes import send_reply
        pending = PENDING_EMAIL_REPLY.pop(pending_key)
        send_reply(
            pending["account_email"], pending["to"], pending["subject"],
            message["text"].strip(), pending["references"] or None,
        )
        telegram.send_message(chat_id, f"✅ Correo enviado desde `{pending['account_email']}`.")
        return

    if pending_key in PENDING_AGENDAR_TITLE and message.get("text"):
        pending = PENDING_AGENDAR_TITLE[pending_key]
        texto = message["text"].strip()
        if pending.get("stage") == "confirm":
            PENDING_AGENDAR_TITLE.pop(pending_key, None)
            if _is_confirmacion_afirmativa(texto):
                _complete_agendar(pending, pending["titulo"], chat_id, ghl, telegram)
            else:
                telegram.send_message(chat_id, "❌ No se agendó nada. Si querés, elegí el horario de nuevo.")
            return
        # stage "title": todavia no se agenda nada. Se arma y manda la
        # confirmacion PRIMERO; el titulo y el stage "confirm" solo se
        # guardan si esa confirmacion se entrego con exito. Si
        # _build_agendar_confirmation_text/send_message explota a mitad de
        # camino (ej. GHL 5xx/timeout al pedir el contacto), el SDR nunca vio
        # el prompt de confirmacion — dejar el pending armado en "confirm" en
        # ese caso haria que un "si" suelto y sin relacion, mandado despues,
        # agendara una cita real sin confirmacion genuina (hallazgo de
        # revisor sobre este flujo).
        try:
            confirmation_text = _build_agendar_confirmation_text(pending, texto, ghl)
            telegram.send_message(chat_id, confirmation_text)
        except Exception:
            logging.exception("%s: error armando/mandando la confirmacion de agendar", slug)
            PENDING_AGENDAR_TITLE.pop(pending_key, None)
            try:
                telegram.send_message(chat_id, "⚠️ No pude armar la confirmación, intentá elegir el horario de nuevo.")
            except Exception:
                logging.exception("%s: error mandando el aviso de fallo de confirmacion", slug)
            return
        pending["titulo"] = texto
        pending["stage"] = "confirm"
        return

    if pending_key in PENDING_MANUAL_TASK and message.get("text"):
        pending = PENDING_MANUAL_TASK[pending_key]
        pending[pending["step"]] = message["text"].strip()
        current_index = TASK_STEPS.index(pending["step"])
        if current_index + 1 < len(TASK_STEPS):
            pending["step"] = TASK_STEPS[current_index + 1]
            telegram.send_message(chat_id, TASK_STEP_PROMPTS[pending["step"]])
        else:
            PENDING_MANUAL_TASK.pop(pending_key)
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
    telegram.send_message(chat_id, build_agendar_prompt(nombre, contact_id), reply_markup=build_agendar_keyboard(contact_id))
    telegram.send_message(chat_id, build_tarea_prompt(nombre, contact_id), reply_markup=build_tarea_keyboard(contact_id))


def handle_callback(callback: dict[str, Any], slug: str, ghl: GHLClient, telegram: TelegramClient) -> None:
    data = callback.get("data") or ""
    parts = data.split(":", 2)
    if len(parts) < 2:
        return
    chat_id = callback["message"]["chat"]["id"]
    telegram.answer_callback_query(callback["id"])

    # callback_data "email:{contact_id}" trae solo 2 partes (a diferencia de
    # "tarea"/"status"/"agendar" que son type:id:extra), por eso se rutea
    # antes del chequeo de 3 partes.
    if parts[0] == "email" and len(parts) >= 2:
        handle_email_callback(parts[1], chat_id, slug, ghl, telegram)
        return

    if len(parts) != 3:
        return

    if parts[0] == "tarea":
        handle_tarea_callback(parts, chat_id, slug, telegram)
        return

    if parts[0] == "agendar":
        handle_agendar_callback(parts[1], chat_id, slug, ghl, telegram)
        return

    if parts[0] == "agendar_slot":
        handle_agendar_slot_callback(parts[1], parts[2], chat_id, slug, ghl, telegram)
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
        telegram.send_message(chat_id, build_already_status_text(nombre, new_status, contact_id))
        return

    ghl.update_custom_field(contact_id, field_id, new_status)
    telegram.send_message(chat_id, build_status_changed_text(nombre, new_status, contact_id))


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
                            handle_callback(update["callback_query"], slug, ghl, telegram)
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
