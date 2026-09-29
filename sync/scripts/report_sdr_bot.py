from __future__ import annotations

"""Bot privado de consultas operativas para @equipo_alicia_bot."""

import sys
import time
from collections.abc import Callable

import httpx

from config import get_optional_env
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


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    token = get_optional_env("TELEGRAM_SDR_TOKEN") or ""
    chat_id = get_optional_env("TELEGRAM_SDR_CHAT_ID") or ""
    sender = EquipoAliciaTelegram(token, chat_id)
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
    raise SystemExit(main())
