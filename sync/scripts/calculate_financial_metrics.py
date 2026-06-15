from __future__ import annotations

import argparse
import logging

from config import get_settings
from supabase_rest import SupabaseRestClient


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Calcula resumen_financiero desde la vista financiera.")
    parser.add_argument("--periodo", default="actual", help="Etiqueta de periodo, ejemplo 2026-05 o actual.")
    args = parser.parse_args()

    setup_logging()
    settings = get_settings()
    supabase = SupabaseRestClient(settings.supabase_url, settings.supabase_secret_key)
    rows = []
    for item in supabase.select("vw_financiero_cliente", "*"):
        rows.append(
            {
                "cliente_slug": item["cliente_slug"],
                "periodo": args.periodo,
                "ingresos_fijos": item.get("ingreso_mensual") or 0,
                "ingresos_variables": (item.get("ingreso_variable_por_reunion") or 0) * (item.get("reuniones_validas") or 0),
                "ingresos_totales": item.get("ingresos_totales_estimados") or 0,
                "costos_sdr": item.get("costos_sdr") or 0,
                "costos_herramientas": item.get("costos_herramientas") or 0,
                "costos_totales": item.get("costos_totales_estimados") or 0,
                "margen": item.get("margen_estimado") or 0,
                "rentabilidad": item.get("rentabilidad_estimada") or 0,
                "costo_por_reunion_valida": item.get("costo_por_reunion_valida") or 0,
            }
        )
    if rows:
        supabase.upsert("resumen_financiero", rows, "cliente_slug,periodo")
    logging.info("Resumen financiero generado: %s filas", len(rows))


if __name__ == "__main__":
    main()
