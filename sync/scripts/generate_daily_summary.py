from __future__ import annotations

import argparse
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from config import get_settings
from supabase_rest import SupabaseRestClient


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def daterange(start: date, end: date) -> list[date]:
    days = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def get_all(client: SupabaseRestClient, table: str, columns: str, **params: str) -> list[dict[str, Any]]:
    return client.select_all(table, columns, **params)


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera resumen_diario_sdr desde tablas operacionales.")
    parser.add_argument("--date", help="Fecha YYYY-MM-DD. Por defecto hoy.")
    parser.add_argument("--days", type=int, default=1, help="Cantidad de dias hacia atras incluyendo fecha final.")
    args = parser.parse_args()

    setup_logging()
    settings = get_settings()
    supabase = SupabaseRestClient(settings.supabase_url, settings.supabase_secret_key)

    end_date = date.fromisoformat(args.date) if args.date else date.today()
    start_date = end_date - timedelta(days=args.days - 1)
    days = set(daterange(start_date, end_date))

    summary: dict[tuple[date, str, str], dict[str, Any]] = {}

    def row_for(day: date, sdr_slug: str | None, cliente_slug: str | None) -> dict[str, Any] | None:
        if not sdr_slug or not cliente_slug:
            return None
        key = (day, sdr_slug, cliente_slug)
        if key not in summary:
            summary[key] = {
                "fecha": day.isoformat(),
                "sdr_slug": sdr_slug,
                "cliente_slug": cliente_slug,
                "llamadas_totales": 0,
                "minutos_totales": 0,
                "reuniones_agendadas": 0,
                "reuniones_validas": 0,
                "reuniones_no_validas": 0,
                "contactos_cargados": 0,
                "oportunidades_creadas": 0,
                "conversion_llamadas_reuniones": 0,
                "conversion_llamadas_reuniones_validas": 0,
            }
        return summary[key]

    for call in get_all(supabase, "llamadas", "fecha,sdr_slug,cliente_slug,duracion_minutos"):
        day = parse_date(call.get("fecha"))
        if day not in days:
            continue
        row = row_for(day, call.get("sdr_slug"), call.get("cliente_slug"))
        if row:
            row["llamadas_totales"] += 1
            row["minutos_totales"] += float(call.get("duracion_minutos") or 0)

    for meeting in get_all(supabase, "reuniones", "fecha_reunion,sdr_slug,cliente_slug,es_valida"):
        day = parse_date(meeting.get("fecha_reunion"))
        if day not in days:
            continue
        row = row_for(day, meeting.get("sdr_slug"), meeting.get("cliente_slug"))
        if row:
            row["reuniones_agendadas"] += 1
            if meeting.get("es_valida") is True:
                row["reuniones_validas"] += 1
            elif meeting.get("es_valida") is False:
                row["reuniones_no_validas"] += 1

    for contact in get_all(supabase, "contactos", "ghl_created_at,sdr_slug,cliente_slug"):
        day = parse_date(contact.get("ghl_created_at"))
        if day not in days:
            continue
        row = row_for(day, contact.get("sdr_slug"), contact.get("cliente_slug"))
        if row:
            row["contactos_cargados"] += 1

    for opp in get_all(supabase, "oportunidades", "ghl_created_at,sdr_slug,cliente_slug"):
        day = parse_date(opp.get("ghl_created_at"))
        if day not in days:
            continue
        row = row_for(day, opp.get("sdr_slug"), opp.get("cliente_slug"))
        if row:
            row["oportunidades_creadas"] += 1

    rows = []
    for row in summary.values():
        calls = row["llamadas_totales"]
        row["conversion_llamadas_reuniones"] = round(row["reuniones_agendadas"] / calls, 4) if calls else 0
        row["conversion_llamadas_reuniones_validas"] = round(row["reuniones_validas"] / calls, 4) if calls else 0
        rows.append(row)

    if rows:
        supabase.upsert("resumen_diario_sdr", rows, "fecha,sdr_slug,cliente_slug")
    logging.info("Resumen diario generado: %s filas", len(rows))


if __name__ == "__main__":
    main()
