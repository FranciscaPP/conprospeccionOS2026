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


def parse_dt(value: str | None) -> str | None:
    if not value:
        return None
    return value


def chunked(rows: list[dict[str, Any]], size: int = 100) -> list[list[dict[str, Any]]]:
    return [rows[index : index + size] for index in range(0, len(rows), size)]


def _field_tokens(value: Any) -> set[str]:
    text = str(value or "").strip().lower()
    if not text:
        return set()
    compact = "".join(char for char in text if char.isalnum())
    return {text, compact}


def custom_field_definitions(payload: dict[str, Any]) -> dict[str, set[str]]:
    rows = payload.get("customFields") or payload.get("fields") or []
    definitions: dict[str, set[str]] = {}
    for field in rows:
        field_id = str(field.get("id") or "")
        if not field_id:
            continue
        tokens: set[str] = set()
        for key in ("name", "fieldKey", "key", "placeholder"):
            tokens.update(_field_tokens(field.get(key)))
        definitions[field_id] = tokens
    return definitions


def custom_field_value(
    contact: dict[str, Any],
    *names: str,
    definitions: dict[str, set[str]] | None = None,
) -> str | None:
    # GHL API returns custom fields with only 'id' and 'value' — no name.
    # We try matching by name first (future-proof), then fall back to known field IDs.
    targets: set[str] = set()
    for name in names:
        targets.update(_field_tokens(name))
    fields = contact.get("customFields") or []

    # Try by name/key (in case GHL ever includes it)
    for field in fields:
        tokens: set[str] = set()
        for key in ("name", "fieldName", "fieldKey", "key"):
            tokens.update(_field_tokens(field.get(key)))
        tokens.update((definitions or {}).get(str(field.get("id") or ""), set()))
        if tokens & targets:
            value = field.get("value")
            if value is not None and str(value).strip():
                return str(value).strip()

    # Fallback: match by known GHL custom field IDs per semantic meaning.
    # IDs collected from raw_data across all active client locations.
    CARGO_IDS     = {"efNF4mWu0msxLAzV2iwz", "IQZMMTl5gO2zlEqmZEdQ",
                     "P7PAEC4d5TLiMe6VPN6M", "p4SAWjQigYDdkDYiNbRE",
                     "f43LHxcbFBDAKCm9gdQh", "c60cJqsxNT5Srdiv7wV3"}  # Bambutech + GBS
    INDUSTRIA_IDS = {"Wqc8iUl5U1GVF59WTqrt", "luvGYtBxYc2ngUDvuZeT",
                     "E9lTjhX14s5EDsTmnsSF", "f2WEpcm03VvepzdUvxl8",
                     "p2CZgSN3D0kvNPo9wBeq"}
    INFO_REUNION_IDS = {"mwCPOKdikR3VfS7Xf9bm", "G7iqx0zfyyIY211r2td2"}
    BANT_SDR_IDS = {"sPpRmRxaHRehCVr0UX29", "slMz9VP1KRyAeJZiWss1"}

    if targets & {"cargo", "puesto", "job title", "job_title"}:
        id_set = CARGO_IDS
    elif targets & {"industria", "industry"}:
        id_set = INDUSTRIA_IDS
    elif "informacion para reunion" in targets or any(
        "preparacion" in target and "reunion" in target for target in targets
    ):
        id_set = INFO_REUNION_IDS
    elif any("bant" in target for target in targets):
        id_set = BANT_SDR_IDS
    else:
        return None

    for field in fields:
        if field.get("id") in id_set:
            value = field.get("value")
            if value is not None and str(value).strip():
                return str(value)
    return None


def owner_maps(supabase: SupabaseRestClient) -> dict[tuple[str, str], str]:
    rows = supabase.select("sdr_cliente", "cliente_slug,sdr_slug,ghl_user_id")
    output: dict[tuple[str, str], str] = {}
    for row in rows:
        if row.get("ghl_user_id"):
            output[(row["cliente_slug"], row["ghl_user_id"])] = row["sdr_slug"]
    return output


def active_clients(supabase: SupabaseRestClient) -> list[dict[str, Any]]:
    clients = supabase.select(
        "clientes",
        "nombre,slug,ghl_location_id,estado_contrato",
        order="nombre.asc",
    )
    return [client for client in clients if client.get("ghl_location_id")]


def token_for_client(client: dict[str, Any]) -> str:
    env_key = {
        "gbs": "GHL_TOKEN_GBS_LOGISTICS",
    }.get(client["slug"], f"GHL_TOKEN_{client['slug'].upper()}")
    token = get_optional_env(env_key)
    if not token:
        raise RuntimeError(f"Falta {env_key} en .env/.env.txt")
    return token


def normalize_contact(
    contact: dict[str, Any],
    client: dict[str, Any],
    owner_by_user: dict[tuple[str, str], str],
    definitions: dict[str, set[str]] | None = None,
) -> dict[str, Any]:
    owner_id = contact.get("assignedTo")
    sdr_slug = owner_by_user.get((client["slug"], owner_id)) if owner_id else None
    return {
        "ghl_contact_id": contact.get("id"),
        "cliente_slug": client["slug"],
        "location_id": contact.get("locationId") or client["ghl_location_id"],
        "sdr_slug": sdr_slug,
        "ghl_owner_user_id": owner_id,
        "nombre": contact.get("contactName") or " ".join(filter(None, [contact.get("firstName"), contact.get("lastName")])) or None,
        "nombre_contacto": contact.get("contactName"),
        "nombre_empresa": contact.get("companyName"),
        "email": contact.get("email"),
        "telefono": contact.get("phone"),
        "tipo": contact.get("type"),
        "fuente": contact.get("source"),
        "pais": contact.get("country"),
        "ciudad": contact.get("city"),
        "estado_region": contact.get("state"),
        "industria": custom_field_value(contact, "industria", "industry", definitions=definitions),
        "cargo": custom_field_value(contact, "cargo", "puesto", "job title", "job_title", definitions=definitions),
        "informacion_reunion": custom_field_value(
            contact,
            "informacin_de_preparacin_para_la_reunin",
            "informacion_de_preparacion_para_la_reunion",
            "información de preparación para la reunión",
            "preparacion_para_la_reunion",
            "informacion para reunion",
            definitions=definitions,
        ),
        "bant_sdr": custom_field_value(
            contact,
            "validacin_sdr_bant",
            "validacion_sdr_bant",
            "validación_sdr_bant",
            "validacion sdr bant",
            definitions=definitions,
        ),
        "tags": contact.get("tags") or [],
        "custom_fields": contact.get("customFields") or [],
        "raw_data": contact,
        "ghl_created_at": parse_dt(contact.get("dateAdded")),
        "ghl_updated_at": parse_dt(contact.get("dateUpdated")),
        "synced_at": iso_now(),
    }


def normalize_opportunity(opp: dict[str, Any], client: dict[str, Any], owner_by_user: dict[tuple[str, str], str]) -> dict[str, Any]:
    owner_id = opp.get("assignedTo")
    sdr_slug = owner_by_user.get((client["slug"], owner_id)) if owner_id else None
    contact = opp.get("contact") or {}
    tags = contact.get("tags") or []
    return {
        "ghl_opportunity_id": opp.get("id"),
        "ghl_contact_id": opp.get("contactId") or contact.get("id"),
        "cliente_slug": client["slug"],
        "location_id": opp.get("locationId") or client["ghl_location_id"],
        "sdr_slug": sdr_slug,
        "ghl_owner_user_id": owner_id,
        "nombre": opp.get("name"),
        "valor_monetario": opp.get("monetaryValue"),
        "pipeline_id": opp.get("pipelineId"),
        "pipeline_stage_id": opp.get("pipelineStageId"),
        "pipeline_stage_uid": opp.get("pipelineStageUId"),
        "estado": opp.get("status"),
        "fuente": opp.get("source"),
        "probabilidad_forecast": opp.get("forecastProbability"),
        "probabilidad_efectiva": opp.get("effectiveProbability"),
        "contacto_nombre": contact.get("name"),
        "contacto_empresa": contact.get("companyName"),
        "contacto_email": contact.get("email"),
        "contacto_telefono": contact.get("phone"),
        "tags": tags,
        "custom_fields": opp.get("customFields") or [],
        "raw_data": opp,
        "ghl_created_at": parse_dt(opp.get("createdAt")),
        "ghl_updated_at": parse_dt(opp.get("updatedAt")),
        "last_status_change_at": parse_dt(opp.get("lastStatusChangeAt")),
        "last_stage_change_at": parse_dt(opp.get("lastStageChangeAt")),
        "synced_at": iso_now(),
    }


def sync_entity(
    supabase: SupabaseRestClient,
    client: dict[str, Any],
    entity: str,
    page_limit: int,
    max_pages: int | None,
    dry_run: bool,
    owner_by_user: dict[tuple[str, str], str],
) -> int:
    ghl = GHLClient(token_for_client(client))
    definitions: dict[str, set[str]] = {}
    if entity == "contactos":
        try:
            definitions = custom_field_definitions(
                ghl.list_custom_fields(client["ghl_location_id"])
            )
        except httpx.HTTPStatusError:
            logging.warning("%s: no fue posible cargar definiciones de custom fields", client["nombre"])
    start_after = None
    start_after_id = None
    total = 0
    page = 0

    while True:
        page += 1
        if max_pages and page > max_pages:
            break

        if entity == "contactos":
            data = ghl.list_contacts_page(client["ghl_location_id"], page_limit, start_after, start_after_id)
            items = data.get("contacts") or []
            rows = [
                normalize_contact(item, client, owner_by_user, definitions)
                for item in items
                if item.get("id")
            ]
            table = "contactos"
            conflict = "ghl_contact_id"
        elif entity == "oportunidades":
            data = ghl.list_opportunities_page(client["ghl_location_id"], page_limit, start_after, start_after_id)
            items = data.get("opportunities") or []
            rows = [normalize_opportunity(item, client, owner_by_user) for item in items if item.get("id")]
            table = "oportunidades"
            conflict = "ghl_opportunity_id"
        else:
            raise ValueError(entity)

        logging.info("%s %s pagina %s: %s registros", client["nombre"], entity, page, len(rows))
        if not dry_run:
            for part in chunked(rows, 100):
                supabase.upsert(table, part, conflict)

        total += len(rows)
        meta = data.get("meta") or {}
        start_after = meta.get("startAfter")
        start_after_id = meta.get("startAfterId")
        if not items or not start_after or not start_after_id:
            break

    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="Sincroniza contactos y oportunidades desde GHL hacia Supabase.")
    parser.add_argument("--entity", choices=["contactos", "oportunidades", "all"], default="all")
    parser.add_argument("--client-slug", help="Sincroniza solo un cliente especifico.")
    parser.add_argument("--page-limit", type=int, default=100)
    parser.add_argument("--max-pages", type=int, help="Limita paginas por cliente para pruebas.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    setup_logging()
    settings = get_settings()
    supabase = SupabaseRestClient(settings.supabase_url, settings.supabase_secret_key)
    clients = active_clients(supabase)
    if args.client_slug:
        clients = [client for client in clients if client["slug"] == args.client_slug]
    owner_by_user = owner_maps(supabase)

    entities = ["contactos", "oportunidades"] if args.entity == "all" else [args.entity]
    stats: dict[str, Any] = {"clients": {}, "dry_run": args.dry_run}
    errors: list[dict[str, Any]] = []

    for client in clients:
        stats["clients"][client["slug"]] = {}
        for entity in entities:
            try:
                count = sync_entity(supabase, client, entity, args.page_limit, args.max_pages, args.dry_run, owner_by_user)
                stats["clients"][client["slug"]][entity] = count
            except httpx.HTTPStatusError as exc:
                error = {"cliente": client["slug"], "entity": entity, "status": exc.response.status_code, "body": exc.response.text[:500]}
                errors.append(error)
                logging.error("%s %s fallo: HTTP %s %s", client["nombre"], entity, exc.response.status_code, exc.response.text[:300])
            except Exception as exc:
                error = {"cliente": client["slug"], "entity": entity, "error": str(exc)}
                errors.append(error)
                logging.error("%s %s fallo: %s", client["nombre"], entity, exc)

    if not args.dry_run:
        supabase.insert(
            "sync_runs",
            {
                "source": "ghl",
                "entity": args.entity,
                "status": "success" if not errors else "partial_error",
                "stats": stats,
                "errors": errors,
            },
        )
    logging.info("Sync terminado: %s", stats)


if __name__ == "__main__":
    main()
