from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from config import get_optional_env, get_settings
from ghl_client import GHLClient
from supabase_rest import SupabaseRestClient


EMAIL_SDR_ALIASES: dict[tuple[str, str], str] = {
    ("gbs", "sam.miller@gbs-logistics.cl"): "sebastian_gutierrez",
    ("gbs", "sammiller@gbs-logistics.cl"): "pilar_valero",
    ("gbs", "sam@gbs-logistics.cl"): "yanina_olivo",
}


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def token_for_client(client: dict[str, Any]) -> str:
    env_key = {
        "gbs": "GHL_TOKEN_GBS_LOGISTICS",
    }.get(client["slug"], f"GHL_TOKEN_{client['slug'].upper()}")
    token = get_optional_env(env_key)
    if not token:
        raise RuntimeError(f"Falta {env_key}")
    return token


def active_clients(supabase: SupabaseRestClient) -> list[dict[str, Any]]:
    rows = supabase.select("clientes", "nombre,slug,ghl_location_id", order="nombre.asc")
    return [row for row in rows if row.get("ghl_location_id")]


def sdr_map(supabase: SupabaseRestClient) -> dict[tuple[str, str], str]:
    rows = supabase.select("sdr_cliente", "cliente_slug,sdr_slug,ghl_user_id")
    return {(row["cliente_slug"], row["ghl_user_id"]): row["sdr_slug"] for row in rows if row.get("ghl_user_id")}


def sdr_slug_for_user(
    client_slug: str,
    user_id: str | None,
    email: str | None,
    known_sdr: dict[tuple[str, str], str],
) -> str | None:
    email_key = (email or "").strip().lower()
    if email_key and (client_slug, email_key) in EMAIL_SDR_ALIASES:
        return EMAIL_SDR_ALIASES[(client_slug, email_key)]
    return known_sdr.get((client_slug, user_id)) if user_id else None


def save_sdr_cliente_mappings(supabase: SupabaseRestClient, rows: list[dict[str, Any]]) -> None:
    for row in rows:
        existing = supabase.select(
            "sdr_cliente",
            "id",
            cliente_slug=f"eq.{row['cliente_slug']}",
            sdr_slug=f"eq.{row['sdr_slug']}",
        )
        if existing:
            response = supabase.client.patch(
                "/sdr_cliente",
                params={"id": f"eq.{existing[0]['id']}"},
                headers={"Prefer": "return=minimal"},
                json=row,
            )
        else:
            response = supabase.client.post(
                "/sdr_cliente",
                headers={"Prefer": "return=minimal"},
                json=row,
            )
        response.raise_for_status()


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
            sdr_cliente_rows = []
            sdr_cliente_seen: set[tuple[str, str]] = set()
            for user in payload.get("users", []):
                user_id = user.get("id")
                sdr_slug = sdr_slug_for_user(client["slug"], user_id, user.get("email"), known_sdr)
                rows.append(
                    {
                        "ghl_user_id": user_id,
                        "cliente_slug": client["slug"],
                        "location_id": client["ghl_location_id"],
                        "sdr_slug": sdr_slug,
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
                if user_id and sdr_slug and (client["slug"], sdr_slug) not in sdr_cliente_seen:
                    sdr_cliente_rows.append(
                        {
                            "cliente_slug": client["slug"],
                            "sdr_slug": sdr_slug,
                            "ghl_user_id": user_id,
                            "location_id": client["ghl_location_id"],
                            "activo": True,
                            "estado_asignacion": "activo",
                        }
                    )
                    sdr_cliente_seen.add((client["slug"], sdr_slug))
            total += len(rows)
            logging.info("%s usuarios: %s", client["nombre"], len(rows))
            if rows and not args.dry_run:
                supabase.upsert("ghl_users", rows, "cliente_slug,ghl_user_id")
            if sdr_cliente_rows and not args.dry_run:
                save_sdr_cliente_mappings(supabase, sdr_cliente_rows)
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
