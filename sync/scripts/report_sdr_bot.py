from __future__ import annotations

"""Bot privado de consultas operativas para @equipo_alicia_bot."""

import argparse
import sys
import time
from collections.abc import Callable

import httpx

from config import get_optional_env, get_settings
from supabase_rest import SupabaseRestClient
from sdr_reporting.cloud_state import CloudStateStore
from sdr_reporting.intents import QueryRequest, parse_query
from sdr_reporting.render import render_query
from sdr_reporting.service import build_live_report
from sdr_reporting.telegram import EquipoAliciaTelegram


MENU_KEYBOARD = {
    "keyboard": [
        [{"text": "Tiempo trabajado"}, {"text": "Llamadas"}],
        [{"text": "Tareas"}, {"text": "Correos"}],
        [{"text": "WhatsApp BAMBU TECH"}, {"text": "Reuniones"}],
        [{"text": "Funnel"}, {"text": "Adherencia"}],
        [{"text": "Resumen"}],
    ],
    "resize_keyboard": True,
}


def query_operational(request: QueryRequest) -> list[str]:
    report = build_live_report(day=request.day)
    return render_query(report, request)


class BotController:
    def __init__(self, allowed_chat_id: str, query: Callable[[QueryRequest], list[str]] = query_operational):
        self.allowed_chat_id = str(allowed_chat_id)
        self.query = query

    def handle(self, message: dict) -> list[str] | None:
        chat = message.get("chat") or {}
        if str(chat.get("id") or "") != self.allowed_chat_id:
            return None
        text = message.get("text") or ""
        if not text:
            return None
        return self.query(parse_query(text))


def process_queued_query(
    update_id: int,
    store: CloudStateStore,
    sender: EquipoAliciaTelegram,
    allowed_chat_id: str,
    *,
    query: Callable[[QueryRequest], list[str]] = query_operational,
) -> bool:
    """Claim and answer one Telegram update; duplicates produce no output."""
    row = store.claim_query(int(update_id))
    if not row:
        return False
    try:
        if str(row.get("chat_id") or "") != str(allowed_chat_id):
            raise RuntimeError("chat no autorizado en la cola")
        replies = query(parse_query(str(row.get("text") or "")))
        for index, reply in enumerate(replies):
            sender.send_message(
                reply,
                reply_markup=MENU_KEYBOARD if index == len(replies) - 1 else None,
            )
        store.mark_query_answered(int(update_id))
        return True
    except Exception as exc:
        store.mark_query_failed(int(update_id), exc)
        raise


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    parser = argparse.ArgumentParser(description="Consultas privadas de @equipo_alicia_bot")
    parser.add_argument("--cloud-update-id", type=int, help="Procesar una consulta ya encolada")
    args = parser.parse_args(argv)
    token = get_optional_env("TELEGRAM_SDR_TOKEN") or ""
    chat_id = get_optional_env("TELEGRAM_SDR_CHAT_ID") or ""
    sender = EquipoAliciaTelegram(token, chat_id)
    if args.cloud_update_id is not None:
        settings = get_settings()
        store = CloudStateStore(SupabaseRestClient(settings.supabase_url, settings.supabase_secret_key))
        processed = process_queued_query(args.cloud_update_id, store, sender, chat_id)
        print("Consulta respondida." if processed else "Consulta duplicada o ya procesada.")
        return 0

    identity = sender.verify_identity()
    controller = BotController(chat_id)
    offset = None
    print(f"@{identity['username']} escuchando un único chat autorizado", flush=True)
    while True:
        try:
            response = sender.transport.get(
                f"{sender.base_url}/getUpdates",
                params={"timeout": 50, "offset": offset, "allowed_updates": ["message"]},
                timeout=60,
            )
            response.raise_for_status()
            updates = response.json().get("result") or []
        except (httpx.HTTPError, ValueError) as exc:
            print(f"poll error: {type(exc).__name__}", flush=True)
            time.sleep(3)
            continue
        for update in updates:
            offset = int(update["update_id"]) + 1
            replies = controller.handle(update.get("message") or {})
            if replies is None:
                continue
            try:
                for index, reply in enumerate(replies):
                    sender.send_message(reply, reply_markup=MENU_KEYBOARD if index == len(replies) - 1 else None)
            except Exception as exc:
                print(f"query error: {type(exc).__name__}: {exc}", flush=True)
                sender.send_message("No pude consultar los datos ahora. Intenta nuevamente en un momento.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
