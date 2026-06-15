from __future__ import annotations

import argparse
import logging
import re
import unicodedata
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


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKD", value)
    text = text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", text).strip().upper()


def classify_stage(stage_name: str) -> tuple[str, bool, bool | None]:
    name = normalize_text(stage_name)
    if "REUNION VALIDA" in name:
        return "reunion_valida", True, True
    if "REUNION NO VALIDA" in name:
        return "reunion_no_valida", True, False
    if "ESPERA VALIDACION" in name:
        return "pendiente_validacion", True, None
    if "REAGENDAR REUNION" in name:
        return "reagendada", True, None
    if "REUNION AGENDADA" in name:
        return "agendada", True, None
    if "COORDINANDO REUNION" in name:
        return "coordinando_reunion", False, None
    if "COTIZ" in name:
        return "cotizacion", False, None
    if "SEGUIMIENTO" in name:
        return "seguimiento", False, None
    if "NO CONTESTA" in name:
        return "no_contesta", False, None
    if "NO INTERESADO" in name:
        return "no_interesado", False, None
    if "NO CALIFICA" in name:
        return "no_califica", False, None
    if "RESPONDE" in name:
        return "responde", False, None
    return "otro", False, None


def token_for_client(client: dict[str, Any]) -> str:
    env_key = f"GHL_TOKEN_{client['slug'].upper()}"
    token = get_optional_env(env_key)
    if not token:
        raise RuntimeError(f"Falta {env_key} en .env/.env.txt")
    return token


def active_clients(supabase: SupabaseRestClient) -> list[dict[str, Any]]:
    rows = supabase.select("clientes", "nombre,slug,ghl_location_id", order="nombre.asc")
    return [row for row in rows if row.get("ghl_location_id")]


def main() -> None:
    parser = argparse.ArgumentParser(description="Sincroniza pipelines/stages de GHL.")
    parser.add_argument("--client-slug")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    setup_logging()
    settings = get_settings()
    supabase = SupabaseRestClient(settings.supabase_url, settings.supabase_secret_key)
    clients = active_clients(supabase)
    if args.client_slug:
        clients = [client for client in clients if client["slug"] == args.client_slug]

    total = 0
    errors = []
    for client in clients:
        try:
            ghl = GHLClient(token_for_client(client))
            payload = ghl.list_pipelines(client["ghl_location_id"])
            rows_by_key = {}
            for pipeline in payload.get("pipelines", []):
                for stage in pipeline.get("stages", []):
                    category, is_meeting, is_valid = classify_stage(stage.get("name") or "")
                    key = (client["slug"], pipeline.get("id"), stage.get("id"))
                    rows_by_key[key] = {
                        "cliente_slug": client["slug"],
                        "location_id": client["ghl_location_id"],
                        "pipeline_id": pipeline.get("id"),
                        "pipeline_name": pipeline.get("name"),
                        "stage_id": stage.get("id"),
                        "stage_name": stage.get("name"),
                        "stage_position": stage.get("position"),
                        "stage_probability": stage.get("stageWinProbability"),
                        "stage_category": category,
                        "is_meeting_stage": is_meeting,
                        "is_valid_meeting": is_valid,
                        "raw_data": stage,
                        "synced_at": iso_now(),
                    }
            rows = list(rows_by_key.values())
            logging.info("%s stages: %s", client["nombre"], len(rows))
            total += len(rows)
            if rows and not args.dry_run:
                supabase.upsert("ghl_pipeline_stages", rows, "cliente_slug,pipeline_id,stage_id")
        except httpx.HTTPStatusError as exc:
            logging.error("%s fallo HTTP %s: %s", client["nombre"], exc.response.status_code, exc.response.text[:300])
            errors.append({"cliente": client["slug"], "status": exc.response.status_code, "body": exc.response.text[:500]})
        except Exception as exc:
            logging.error("%s fallo: %s", client["nombre"], exc)
            errors.append({"cliente": client["slug"], "error": str(exc)})

    if not args.dry_run:
        supabase.insert(
            "sync_runs",
            {
                "source": "ghl",
                "entity": "pipeline_stages",
                "status": "success" if not errors else "partial_error",
                "stats": {"stages": total, "dry_run": args.dry_run},
                "errors": errors,
            },
        )
    logging.info("Sync pipeline stages terminado: %s stages", total)


if __name__ == "__main__":
    main()
