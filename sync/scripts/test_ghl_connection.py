from __future__ import annotations

import argparse
import logging
from typing import Any

import httpx

from config import get_optional_env, get_settings
from ghl_client import GHLClient
from supabase_rest import SupabaseRestClient


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def load_clients() -> list[dict[str, Any]]:
    settings = get_settings()
    supabase = SupabaseRestClient(settings.supabase_url, settings.supabase_secret_key)
    return supabase.select(
        "clientes",
        "nombre,slug,ghl_location_id,estado_contrato",
        order="nombre.asc",
    )


def check_location(ghl: GHLClient, client: dict[str, Any], include_samples: bool) -> dict[str, Any]:
    location_id = client.get("ghl_location_id")
    result = {
        "cliente": client["nombre"],
        "slug": client["slug"],
        "location_id": location_id,
        "location_ok": False,
        "contacts_ok": None,
        "opportunities_ok": None,
        "error": None,
    }

    if not location_id:
        result["error"] = "Sin ghl_location_id"
        return result

    try:
        location = ghl.get_location(location_id)
        location_data = location.get("location") if isinstance(location, dict) else None
        result["location_ok"] = True
        result["ghl_name"] = (location_data or location).get("name") if isinstance(location_data or location, dict) else None

        if include_samples:
            token_env_key = f"GHL_TOKEN_{client['slug'].upper()}"
            data_token = get_optional_env(token_env_key)
            data_ghl = GHLClient(data_token) if data_token else ghl
            result["data_token_env_key"] = token_env_key
            result["using_location_token"] = bool(data_token)

            try:
                data_ghl.list_contacts_sample(location_id)
                result["contacts_ok"] = True
            except httpx.HTTPStatusError as exc:
                result["contacts_ok"] = False
                result["contacts_error"] = f"HTTP {exc.response.status_code}: {exc.response.text[:300]}"

            try:
                data_ghl.list_opportunities_sample(location_id)
                result["opportunities_ok"] = True
            except httpx.HTTPStatusError as exc:
                result["opportunities_ok"] = False
                result["opportunities_error"] = f"HTTP {exc.response.status_code}: {exc.response.text[:300]}"
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500]
        result["error"] = f"HTTP {exc.response.status_code}: {body}"
    except Exception as exc:
        result["error"] = str(exc)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Valida conexion GHL API V2 por subcuenta.")
    parser.add_argument(
        "--include-samples",
        action="store_true",
        help="Ademas de validar location, prueba lectura minima de contactos y oportunidades.",
    )
    args = parser.parse_args()

    setup_logging()
    settings = get_settings()
    ghl = GHLClient(settings.ghl_agency_token)
    clients = load_clients()

    logging.info("Validando %s clientes desde Supabase", len(clients))
    for client in clients:
        result = check_location(ghl, client, args.include_samples)
        if result["location_ok"]:
            logging.info(
                "LOCATION OK %s | %s | GHL: %s",
                result["cliente"],
                result["location_id"],
                result.get("ghl_name") or "sin nombre",
            )
            if args.include_samples:
                token_source = "token de subcuenta" if result.get("using_location_token") else "GHL_AGENCY_TOKEN"
                logging.info("  DATOS usando %s", token_source)
                if result["contacts_ok"]:
                    logging.info("  CONTACTOS OK")
                else:
                    logging.warning(
                        "  CONTACTOS ERROR %s | Para esta subcuenta puedes agregar %s",
                        result.get("contacts_error"),
                        result.get("data_token_env_key"),
                    )
                if result["opportunities_ok"]:
                    logging.info("  OPORTUNIDADES OK")
                else:
                    logging.warning(
                        "  OPORTUNIDADES ERROR %s | Para esta subcuenta puedes agregar %s",
                        result.get("opportunities_error"),
                        result.get("data_token_env_key"),
                    )
        else:
            logging.warning("SKIP/ERROR %s | %s", result["cliente"], result["error"])


if __name__ == "__main__":
    main()
