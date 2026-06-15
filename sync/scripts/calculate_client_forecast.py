from __future__ import annotations

import argparse
import logging
from datetime import date
from typing import Any

from config import get_settings
from supabase_rest import SupabaseRestClient


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Calcula resumen_cliente con avance, forecast y riesgo.")
    parser.add_argument("--date", help="Fecha YYYY-MM-DD. Por defecto hoy.")
    args = parser.parse_args()

    setup_logging()
    settings = get_settings()
    supabase = SupabaseRestClient(settings.supabase_url, settings.supabase_secret_key)
    today = date.fromisoformat(args.date) if args.date else date.today()

    clients = supabase.select_all("vw_clientes_riesgo", "*")
    contacts = supabase.select_all("contactos", "cliente_slug")
    calls = supabase.select_all("llamadas", "cliente_slug,duracion_minutos")
    meetings = supabase.select_all("reuniones", "cliente_slug,es_valida")

    by_client: dict[str, dict[str, Any]] = {}
    for client in clients:
        by_client[client["cliente_slug"]] = {
            "fecha": today.isoformat(),
            "cliente_slug": client["cliente_slug"],
            "contactos_totales": 0,
            "llamadas_totales": 0,
            "minutos_totales": 0,
            "reuniones_agendadas": 0,
            "reuniones_validas": float(client.get("reuniones_validas_total") or 0),
            "reuniones_no_validas": 0,
            "avance_meta": float(client.get("avance_meta") or 0),
            "forecast": 0,
            "riesgo": client.get("riesgo") or "sin_datos",
        }

    for row in contacts:
        if row.get("cliente_slug") in by_client:
            by_client[row["cliente_slug"]]["contactos_totales"] += 1

    for row in calls:
        if row.get("cliente_slug") in by_client:
            by_client[row["cliente_slug"]]["llamadas_totales"] += 1
            by_client[row["cliente_slug"]]["minutos_totales"] += float(row.get("duracion_minutos") or 0)

    for row in meetings:
        if row.get("cliente_slug") in by_client:
            by_client[row["cliente_slug"]]["reuniones_agendadas"] += 1
            if row.get("es_valida") is False:
                by_client[row["cliente_slug"]]["reuniones_no_validas"] += 1

    rows = list(by_client.values())
    if rows:
        supabase.upsert("resumen_cliente", rows, "fecha,cliente_slug")
    logging.info("Forecast cliente generado: %s filas", len(rows))


if __name__ == "__main__":
    main()
