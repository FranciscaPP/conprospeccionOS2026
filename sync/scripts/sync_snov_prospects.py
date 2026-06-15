from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from typing import Any

from config import get_optional_env, get_settings
from snov_client import SnovClient
from supabase_rest import SupabaseRestClient


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def pick(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return None


def first_email(item: dict[str, Any]) -> tuple[str | None, str | None]:
    emails = item.get("emails")
    if isinstance(emails, list) and emails:
        first = emails[0] or {}
        return first.get("email"), str(first.get("status") or first.get("jobStatus") or first.get("smtpStatus") or "")
    email = item.get("email")
    return email, str(item.get("emailStatus") or "") if email else None


def custom_value(item: dict[str, Any], *names: str) -> Any:
    custom_fields = item.get("customFields") or item.get("custom_fields") or item.get("fields") or []
    wanted = {name.lower() for name in names}
    if isinstance(custom_fields, dict):
        for key, value in custom_fields.items():
            if key.lower() in wanted and value not in (None, ""):
                return value
    if isinstance(custom_fields, list):
        for field in custom_fields:
            if not isinstance(field, dict):
                continue
            key = str(field.get("name") or field.get("key") or field.get("label") or "").lower()
            value = field.get("value")
            if key in wanted and value not in (None, ""):
                return value
    return None


def normalize_prospect(
    item: dict[str, Any],
    campaign: dict[str, Any],
    mapping: dict[str, Any] | None,
    list_name: str | None,
) -> dict[str, Any] | None:
    prospect_id = str(item.get("id") or item.get("prospectId") or "")
    if not prospect_id:
        return None
    email, email_status = first_email(item)
    empresa = pick(item, "companyName", "company", "currentCompany") or custom_value(item, "empresa", "company", "compania")
    cargo = pick(item, "position", "jobTitle", "title") or custom_value(item, "cargo", "position", "job title", "title")
    industria = pick(item, "industry") or custom_value(item, "industria", "industry", "rubro")
    pais = pick(item, "country") or custom_value(item, "pais", "país", "country")
    localidad = pick(item, "locality", "city", "location") or custom_value(item, "localidad", "ciudad", "city", "location")
    return {
        "snov_prospect_id": prospect_id,
        "cliente_slug": (mapping or {}).get("cliente_slug"),
        "sdr_slug": (mapping or {}).get("sdr_slug"),
        "snov_campaign_id": str(campaign.get("snov_campaign_id")),
        "list_id": str(campaign.get("list_id")) if campaign.get("list_id") is not None else None,
        "list_name": list_name,
        "nombre": pick(item, "name", "fullName"),
        "first_name": pick(item, "firstName", "first_name"),
        "last_name": pick(item, "lastName", "last_name"),
        "email": email,
        "email_status": email_status,
        "empresa": empresa,
        "cargo": cargo,
        "industria": industria,
        "pais": pais,
        "localidad": localidad,
        "linkedin_url": pick(item, "linkedInUrl", "linkedin", "linkedinUrl"),
        "status": str(item.get("status")) if item.get("status") is not None else None,
        "raw_data": item,
        "synced_at": iso_now(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sincroniza prospectos/listas de Snov.io para enriquecer correo con cargo, industria y pais.")
    parser.add_argument("--campaign-id", action="append")
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    setup_logging()

    client_id = get_optional_env("SNOV_CLIENT_ID")
    client_secret = get_optional_env("SNOV_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Faltan SNOV_CLIENT_ID y/o SNOV_CLIENT_SECRET en .env/.env.txt")

    supabase_settings = get_settings()
    supabase = SupabaseRestClient(supabase_settings.supabase_url, supabase_settings.supabase_secret_key)
    snov = SnovClient(client_id, client_secret)
    campaigns = supabase.select_all("snov_campaigns", "snov_campaign_id,list_id,nombre,status")
    if args.campaign_id:
        selected = set(args.campaign_id)
        campaigns = [campaign for campaign in campaigns if campaign.get("snov_campaign_id") in selected]
    maps = {
        row["snov_campaign_id"]: row
        for row in supabase.select_all("snov_campaign_map", "snov_campaign_id,cliente_slug,sdr_slug")
        if row.get("snov_campaign_id")
    }

    rows = []
    stats: dict[str, Any] = {}
    for campaign in campaigns:
        list_id = campaign.get("list_id")
        if not list_id or list_id == "0":
            continue
        campaign_id = campaign["snov_campaign_id"]
        page = 1
        campaign_rows = 0
        list_name = None
        while True:
            if args.max_pages and page > args.max_pages:
                break
            payload = snov.prospects_in_list(str(list_id), page=page, per_page=5000)
            list_info = payload.get("list") or {}
            list_name = list_info.get("name") or list_name
            prospects = payload.get("prospects") or []
            for prospect in prospects:
                row = normalize_prospect(prospect, campaign, maps.get(campaign_id), list_name)
                if row:
                    rows.append(row)
                    campaign_rows += 1
            if len(prospects) < 5000:
                break
            page += 1
        stats[campaign_id] = {"list_id": list_id, "prospects": campaign_rows}
        logging.info("%s prospectos: %s", campaign.get("nombre"), campaign_rows)

    logging.info("Prospectos detectados: %s", len(rows))
    if rows and not args.dry_run:
        for index in range(0, len(rows), 500):
            supabase.upsert("snov_prospects", rows[index : index + 500], "snov_prospect_id")
        supabase.insert("sync_runs", {"source": "snov", "entity": "prospects", "status": "success", "stats": stats, "errors": []})


if __name__ == "__main__":
    main()
