from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from config import get_optional_env, get_settings
from supabase_rest import SupabaseRestClient

from .config import CHILE
from .render import render_hourly
from .extended import (aggregate_week, fetch_calendar_meetings, new_meeting_alert,
                       render_chart, render_daily_close, render_weekly, render_weekly_charts)
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
    parser.add_argument("--scheduled", action="store_true", help="Aplicar guardia laboral 11:00–20:59")
    parser.add_argument("--verify-bot", action="store_true", help="Verificar identidad sin enviar")
    parser.add_argument("--close", action="store_true", help="Generar cierre diario y gráfico")
    parser.add_argument("--close-only", action="store_true", help="Enviar solo cierre y gráfico")
    parser.add_argument("--weekly", action="store_true", help="Generar resumen semanal y tres gráficos")
    parser.add_argument("--monitor-meetings", action="store_true", help="Alertar citas nuevas ya inicializado")
    parser.add_argument("--seed-meetings", action="store_true", help="Registrar citas existentes sin alertarlas")
    args = parser.parse_args(argv)
    if args.close_only:
        args.close = True

    if args.scheduled:
        local_now = datetime.now(CHILE)
        if local_now.weekday() >= 5 or not 11 <= local_now.hour <= 20:
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

    settings = get_settings()
    store = SnapshotStore(SupabaseRestClient(settings.supabase_url, settings.supabase_secret_key))
    if args.monitor_meetings or args.seed_meetings:
        known = store.known_meeting_ids()
        sent = 0
        for item in fetch_calendar_meetings():
            key = (item["slug"], item["id"])
            if key in known:
                continue
            store.mark_meeting(item["slug"], item["id"], item["event"])
            if args.monitor_meetings and args.send:
                sender.send_message(new_meeting_alert(item["slug"], item["event"]))
                sent += 1
        print(f"reuniones nuevas alertadas: {sent}" if args.monitor_meetings else "citas existentes inicializadas")
        return 0

    local_now = datetime.now(CHILE)
    if args.scheduled and local_now.hour >= 20:
        args.close = True
        if local_now.weekday() == 4:
            args.weekly = True

    report = build_live_report(date.fromisoformat(args.date) if args.date else None)
    try:
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
    messages = [] if args.close_only else render_hourly(report)
    if args.close:
        messages.append(render_daily_close(report))
    for index, message in enumerate(messages, 1):
        if args.send:
            sender.send_message(message)
            print(f"mensaje {index}/{len(messages)} enviado")
        else:
            print(f"\n--- MENSAJE {index}/{len(messages)} ---\n{message}")
    if args.close:
        chart = render_chart(report, Path(__file__).resolve().parents[1] / "sdr_cache" / f"cierre_{report['day']}.png")
        if args.send:
            sender.send_photo(chart, f"Cierre Nora · {report['day'].strftime('%d/%m/%Y')}")
        else:
            print(f"gráfico: {chart}")
    if args.weekly:
        week_start = report["day"] - timedelta(days=report["day"].weekday())
        reports = store.load_closes(week_start, report["day"])
        summary = aggregate_week(reports)
        weekly_text = render_weekly(summary, week_start, report["day"])
        if args.send:
            sender.send_message(weekly_text)
            for chart in render_weekly_charts(summary, Path(__file__).resolve().parents[1] / "sdr_cache" / "weekly"):
                sender.send_photo(chart, "Resumen semanal · Nora")
        else:
            print(f"\n--- SEMANAL ---\n{weekly_text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
