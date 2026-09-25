from __future__ import annotations

import argparse
import sys
from datetime import date

from config import get_optional_env, get_settings
from supabase_rest import SupabaseRestClient

from .render import render_hourly
from .service import build_live_report
from .storage import SnapshotStore
from .telegram import EquipoAliciaTelegram


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    parser = argparse.ArgumentParser(description="Reporte operativo de @equipo_alicia_bot")
    parser.add_argument("--date", help="Fecha YYYY-MM-DD; por defecto hoy en Chile")
    parser.add_argument("--send", action="store_true", help="Enviar al único chat principal configurado")
    parser.add_argument("--scheduled", action="store_true", help="Aplicar guardia laboral 12:00–20:00")
    parser.add_argument("--verify-bot", action="store_true", help="Verificar identidad sin enviar")
    args = parser.parse_args(argv)

    if args.scheduled:
        from .config import CHILE
        from datetime import datetime

        local_now = datetime.now(CHILE)
        if local_now.weekday() >= 5 or not 12 <= local_now.hour <= 20:
            print("Fuera de ventana programada; no se envía.")
            return 0

    sender = EquipoAliciaTelegram(
        get_optional_env("TELEGRAM_SDR_TOKEN") or "",
        get_optional_env("TELEGRAM_SDR_CHAT_ID") or "",
    )
    if args.verify_bot:
        identity = sender.verify_identity()
        print(f"@{identity['username']} verificado · destinatarios: 1")
        return 0

    report = build_live_report(date.fromisoformat(args.date) if args.date else None)
    try:
        settings = get_settings()
        store = SnapshotStore(SupabaseRestClient(settings.supabase_url, settings.supabase_secret_key))
        previous = store.load_yesterday_same_hour(report["day"], report["cut"])
        if previous:
            current_calls = sum(c.get("calls", 0) for c in report["clients"].values())
            previous_calls = sum(c.get("calls", 0) for c in previous.get("clients", {}).values())
            current_tasks = sum(c.get("tasks_done", 0) for c in report["clients"].values())
            previous_tasks = sum(c.get("tasks_done", 0) for c in previous.get("clients", {}).values())
            report["comparison"] = (
                f"Tareas completadas: {current_tasks} vs {previous_tasks}\n"
                f"Llamadas: {current_calls} vs {previous_calls}"
            )
        store.save_report(report)
    except Exception as exc:
        report["alerts"] = [f"Histórico no persistido: {type(exc).__name__}.", *report.get("alerts", [])][:3]
    messages = render_hourly(report)
    for index, message in enumerate(messages, 1):
        if args.send:
            sender.send_message(message)
            print(f"mensaje {index}/{len(messages)} enviado")
        else:
            print(f"\n--- MENSAJE {index}/{len(messages)} ---\n{message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
