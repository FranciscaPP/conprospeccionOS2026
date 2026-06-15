from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from config import get_optional_env, get_settings
from ghl_client import GHLClient
from supabase_rest import SupabaseRestClient


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def token_for_client(client: dict[str, Any]) -> str:
    token = get_optional_env(f"GHL_TOKEN_{client['slug'].upper()}")
    if not token:
        raise RuntimeError(f"Falta GHL_TOKEN_{client['slug'].upper()}")
    return token


def active_clients(supabase: SupabaseRestClient) -> list[dict[str, Any]]:
    rows = supabase.select("clientes", "nombre,slug,ghl_location_id", order="nombre.asc")
    return [row for row in rows if row.get("ghl_location_id")]


def sdr_map(supabase: SupabaseRestClient) -> dict[tuple[str, str], str]:
    rows = supabase.select("sdr_cliente", "cliente_slug,sdr_slug,ghl_user_id")
    return {(row["cliente_slug"], row["ghl_user_id"]): row["sdr_slug"] for row in rows if row.get("ghl_user_id")}


def main() -> None:
    parser = argparse.ArgumentParser(description="Sincroniza usuarios GHL por subcuenta.")
    parser.add_argument("--client-slug")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    setup_logging()
    settings = get_settings()
    supabase = SupabaseRestClient(settings.supabase_url, settings.supabase_secret_key)
    clients = active_clients(supabase)
    if args.client_slug:
        clients = [client for client in clients if client["slug"] == args.client_slug]
    known_sdr = sdr_map(supabase)

    total = 0
    errors = []
    for client in clients:
        try:
            ghl = GHLClient(token_for_client(client))
            payload = ghl.list_users(client["ghl_location_id"])
            rows = []
            for user in payload.get("users", []):
                user_id = user.get("id")
                rows.append(
                    {
                        "ghl_user_id": user_id,
                        "cliente_slug": client["slug"],
                        "location_id": client["ghl_location_id"],
                        "sdr_slug": known_sdr.get((client["slug"], user_id)),
                        "nombre": user.get("name"),
                        "first_name": user.get("firstName"),
                        "last_name": user.get("lastName"),
                        "email": user.get("email"),
                        "phone": user.get("phone"),
                        "deleted": user.get("deleted") or False,
                        "raw_data": user,
                        "synced_at": iso_now(),
                    }
                )
            total += len(rows)
            logging.info("%s usuarios: %s", client["nombre"], len(rows))
            if rows and not args.dry_run:
                supabase.upsert("ghl_users", rows, "cliente_slug,ghl_user_id")
        except httpx.HTTPStatusError as exc:
            logging.error("%s fallo HTTP %s: %s", client["nombre"], exc.response.status_code, exc.response.text[:300])
            errors.append({"cliente": client["slug"], "status": exc.response.status_code, "body": exc.response.text[:500]})
        except Exception as exc:
            logging.error("%s fallo: %s", client["nombre"], exc)
            errors.append({"cliente": client["slug"], "error": str(exc)})

    if not args.dry_run:
        supabase.insert("sync_runs", {"source": "ghl", "entity": "users", "status": "success" if not errors else "partial_error", "stats": {"users": total}, "errors": errors})
    logging.info("Sync usuarios terminado: %s", total)


if __name__ == "__main__":
    main()
