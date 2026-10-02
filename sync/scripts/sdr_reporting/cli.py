from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from config import get_optional_env, get_settings
from supabase_rest import SupabaseRestClient

from .config import CHILE
from .extended import aggregate_week, render_weekly, render_weekly_charts
from .service import build_live_report
from .storage import SnapshotStore
from .tabular import render_tabular_report
from .telegram import EquipoAliciaTelegram


def deliver_hourly_report(
    report: dict,
    sender: EquipoAliciaTelegram,
    directory: str | Path,
    *,
    send: bool,
) -> list[Path]:
    paths = render_tabular_report(report, directory)
    if send:
        for index, path in enumerate(paths, 1):
            sender.send_photo(path, f"Reporte Nora · {index} de {len(paths)}")
    return paths


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
    parser.add_argument("--close", action="store_true", help="Marcar el corte como cierre diario")
    parser.add_argument("--close-only", action="store_true", help="Compatibilidad: generar el corte final")
    parser.add_argument("--weekly", action="store_true", help="Generar resumen semanal y tres gráficos")
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
    cache_dir = Path(__file__).resolve().parents[1] / "sdr_cache" / "tabular"
    report_images = deliver_hourly_report(report, sender, cache_dir, send=args.send)
    for index, path in enumerate(report_images, 1):
        action = "enviada" if args.send else "generada"
        print(f"imagen {index}/{len(report_images)} {action}: {path}")
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
