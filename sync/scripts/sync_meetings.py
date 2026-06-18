from __future__ import annotations

import argparse
import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

import httpx

from config import get_optional_env, get_settings
from ghl_client import GHLClient
from supabase_rest import SupabaseRestClient


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def pick(event: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in event and event[key] is not None:
            return event[key]
    return None


def company_from_title(title: str | None, client_name: str) -> str | None:
    value = (title or "").strip()
    if not value:
        return None
    for marker in (f"- {client_name}", "- GBS Logistics", "- GBS LOGISTICS"):
        if marker in value:
            value = value.split(marker, 1)[0].strip()
            break
    return value or None


def contact_name_from_email(email: str | None) -> str | None:
    value = (email or "").strip()
    if "@" not in value:
        return None
    local = value.split("@", 1)[0].replace(".", " ").replace("_", " ").replace("-", " ")
    return " ".join(part.capitalize() for part in local.split() if part) or None


def normalize_ghl_contact(payload: dict[str, Any]) -> dict[str, Any]:
    contact = payload.get("contact") if isinstance(payload.get("contact"), dict) else payload
    first_name = contact.get("firstName") or contact.get("first_name") or ""
    last_name = contact.get("lastName") or contact.get("last_name") or ""
    full_name = contact.get("name") or " ".join(part for part in [first_name, last_name] if part).strip()
    return {
        "nombre": full_name,
        "nombre_contacto": full_name,
        "nombre_empresa": contact.get("companyName") or contact.get("company_name"),
        "email": contact.get("email"),
        "telefono": contact.get("phone"),
        "cargo": contact.get("jobTitle") or contact.get("job_title"),
        "pais": contact.get("country"),
        "ghl_owner_user_id": contact.get("assignedTo") or contact.get("assigned_to"),
        "custom_fields": contact.get("customFields") or [],
        "raw_data": contact,
    }


def token_for_client(client: dict[str, Any]) -> str:
    env_key = {
        "gbs": "GHL_TOKEN_GBS_LOGISTICS",
    }.get(client["slug"], f"GHL_TOKEN_{client['slug'].upper()}")
    token = get_optional_env(env_key)
    if not token:
        raise RuntimeError(f"Falta {env_key} en .env/.env.txt")
    return token


def owner_maps(supabase: SupabaseRestClient) -> dict[tuple[str, str], str]:
    rows = supabase.select("sdr_cliente", "cliente_slug,sdr_slug,ghl_user_id")
    return {(row["cliente_slug"], row["ghl_user_id"]): row["sdr_slug"] for row in rows if row.get("ghl_user_id")}


def active_clients(supabase: SupabaseRestClient) -> list[dict[str, Any]]:
    rows = supabase.select("clientes", "nombre,slug,ghl_location_id", order="nombre.asc")
    return [row for row in rows if row.get("ghl_location_id")]


def normalize_calendar(calendar: dict[str, Any], client: dict[str, Any]) -> dict[str, Any]:
    return {
        "ghl_calendar_id": calendar.get("id"),
        "cliente_slug": client["slug"],
        "location_id": calendar.get("locationId") or client["ghl_location_id"],
        "nombre": calendar.get("name"),
        "tipo_calendario": calendar.get("calendarType"),
        "tipo_evento": calendar.get("eventType"),
        "activo": calendar.get("isActive"),
        "team_members": calendar.get("teamMembers") or [],
        "raw_data": calendar,
        "synced_at": iso_now(),
    }


def contact_lookup(supabase: SupabaseRestClient) -> dict[str, dict[str, Any]]:
    rows = supabase.select_all(
        "contactos",
        "ghl_contact_id,nombre,nombre_contacto,nombre_empresa,email,telefono,cargo,"
        "industria,pais,sdr_slug,ghl_owner_user_id,cliente_slug,"
        "informacion_reunion,bant_sdr,custom_fields,raw_data",
    )
    return {row["ghl_contact_id"]: row for row in rows if row.get("ghl_contact_id")}


EXCLUDED_DOMAINS = {
    "clickie.io", "ecosmartlog.com", "ecosmart-logistics.com",
    "just4u.cl", "tiresias.cl", "latam-tiresias.com",
    "bambutech.cl", "gbslogistics.com", "gbslogistics.cl",
}


def _is_excluded_email(email: str) -> bool:
    e = (email or "").lower().strip()
    return any(e.endswith(f"@{d}") for d in EXCLUDED_DOMAINS)


def normalize_event(
    event: dict[str, Any],
    calendar: dict[str, Any],
    client: dict[str, Any],
    owner_by_user: dict[tuple[str, str], str],
    contacts: dict[str, dict[str, Any]],
    ghl: GHLClient,
) -> dict[str, Any] | None:
    event_id = pick(event, "id", "eventId", "appointmentId")
    if not event_id:
        return None

    contact_id = pick(event, "contactId", "contact_id")
    contact = contacts.get(contact_id or "", {})
    if contact_id and not contact:
        try:
            contact = normalize_ghl_contact(ghl.get_contact(contact_id))
            contacts[contact_id] = contact
        except httpx.HTTPStatusError:
            contact = {}

    # Excluir contactos con dominios internos de clientes
    raw_email = pick(event, "email") or contact.get("email") or ""
    if _is_excluded_email(raw_email):
        return None
    owner_id = pick(event, "assignedUserId", "assignedTo", "userId", "ownerId") or contact.get("ghl_owner_user_id")

    # Priority 1: contact's assigned SDR (most reliable — explicitly set in CRM)
    sdr_slug = contact.get("sdr_slug")

    # Priority 2: secondary calendar member (handles admin-as-primary pattern)
    if not sdr_slug:
        for member in (calendar.get("team_members") or []):
            if not member.get("isPrimary") and member.get("userId"):
                secondary_sdr = owner_by_user.get((client["slug"], member["userId"]))
                if secondary_sdr:
                    sdr_slug = secondary_sdr
                    break

    # Priority 3: event owner_id (fallback when contact has no assigned SDR)
    if not sdr_slug:
        sdr_slug = owner_by_user.get((client["slug"], owner_id)) if owner_id else None

    start_value = pick(event, "startTime", "startDate", "start", "appointmentStartTime")
    end_value = pick(event, "endTime", "endDate", "end", "appointmentEndTime")
    created_value = pick(event, "dateAdded", "createdAt", "created_at")
    start_dt = parse_datetime(start_value)
    end_dt = parse_datetime(end_value)
    created_dt = parse_datetime(created_value)

    row: dict[str, Any] = {
        "ghl_appointment_id": event_id,
        "ghl_calendar_id": calendar.get("ghl_calendar_id"),
        "cliente_slug": client["slug"],
        "ghl_contact_id": contact_id,
        "ghl_owner_user_id": owner_id,
        "location_id": pick(event, "locationId") or client["ghl_location_id"],
        "titulo": pick(event, "title", "eventTitle", "name"),
        "empresa": pick(event, "companyName") or contact.get("nombre_empresa") or company_from_title(pick(event, "title", "eventTitle", "name"), client["nombre"]),
        "contacto": pick(event, "contactName", "contact_name") or contact.get("nombre_contacto") or contact.get("nombre") or contact_name_from_email(raw_email),
        "telefono": pick(event, "phone") or contact.get("telefono"),
        "email": pick(event, "email") or contact.get("email"),
        "cargo": contact.get("cargo"),
        "industria": contact.get("industria"),
        "pais": contact.get("pais"),
        "informacion_reunion": contact.get("informacion_reunion"),
        "bant_sdr": contact.get("bant_sdr"),
        "fecha_agendada": created_dt.date().isoformat() if created_dt else None,
        "fecha_reunion": start_dt.date().isoformat() if start_dt else None,
        "hora_reunion": start_dt.time().replace(tzinfo=None).isoformat() if start_dt else None,
        "starts_at": start_value,
        "ends_at": end_value,
        "estado_reunion": pick(event, "appointmentStatus", "status"),
        "es_valida": None,
        "motivo_rechazo": None,
        "observacion": pick(event, "notes", "description"),
        "direccion_reunion": pick(event, "address", "meetingLocation"),
        "notas": pick(event, "notes"),
        "raw_data": {
            "appointment": event,
            "contact": contact.get("raw_data") or {},
            "contact_custom_fields": contact.get("custom_fields") or [],
        },
        "synced_at": iso_now(),
    }
    # Solo incluir sdr_slug cuando se determinó — evita pisar valores correctos con null en re-syncs
    if sdr_slug is not None:
        row["sdr_slug"] = sdr_slug
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="Sincroniza calendarios y reuniones desde GHL hacia Supabase.")
    parser.add_argument("--client-slug")
    parser.add_argument("--start-date", help="YYYY-MM-DD. Por defecto 90 dias atras.")
    parser.add_argument("--end-date", help="YYYY-MM-DD. Por defecto 90 dias adelante.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    setup_logging()
    settings = get_settings()
    supabase = SupabaseRestClient(settings.supabase_url, settings.supabase_secret_key)
    clients = active_clients(supabase)
    if args.client_slug:
        clients = [client for client in clients if client["slug"] == args.client_slug]

    start_day = date.fromisoformat(args.start_date) if args.start_date else date.today() - timedelta(days=90)
    end_day = date.fromisoformat(args.end_date) if args.end_date else date.today() + timedelta(days=90)
    # GHL /calendars/events espera timestamps en milisegundos, no ISO strings
    start_time = int(datetime.combine(start_day, time.min, tzinfo=timezone.utc).timestamp() * 1000)
    end_time = int(datetime.combine(end_day, time.max, tzinfo=timezone.utc).timestamp() * 1000)

    owner_by_user = owner_maps(supabase)
    contacts = contact_lookup(supabase)
    stats: dict[str, Any] = {"clients": {}, "dry_run": args.dry_run}
    errors: list[dict[str, Any]] = []

    for client in clients:
        try:
            ghl = GHLClient(token_for_client(client))
            calendars_payload = ghl.list_calendars(client["ghl_location_id"])
            calendars = [normalize_calendar(cal, client) for cal in calendars_payload.get("calendars", []) if cal.get("id")]
            stats["clients"][client["slug"]] = {"calendarios": len(calendars), "reuniones": 0}
            logging.info("%s calendarios: %s", client["nombre"], len(calendars))
            if calendars and not args.dry_run:
                supabase.upsert("ghl_calendars", calendars, "ghl_calendar_id")

            meetings: list[dict[str, Any]] = []
            for calendar in calendars:
                events_payload = ghl.list_calendar_events(
                    client["ghl_location_id"],
                    start_time,
                    end_time,
                    calendar_id=calendar["ghl_calendar_id"],
                )
                events = events_payload.get("events") or []
                logging.info("%s | %s eventos: %s", client["nombre"], calendar.get("nombre"), len(events))
                for event in events:
                    row = normalize_event(event, calendar, client, owner_by_user, contacts, ghl)
                    if row:
                        meetings.append(row)

            # Deduplicar: mismo contacto+hora en distintos calendarios → mantener el que tiene sdr_slug
            deduped: dict[tuple[str, str], dict[str, Any]] = {}
            for row in meetings:
                starts = str(row.get("starts_at") or "")
                try:
                    hour_key = datetime.fromisoformat(starts.replace("Z", "+00:00")).strftime("%Y-%m-%dT%H")
                except Exception:
                    hour_key = starts[:13]
                key = (row.get("ghl_contact_id") or "", hour_key)
                existing = deduped.get(key)
                if existing is None or (not existing.get("sdr_slug") and row.get("sdr_slug")):
                    deduped[key] = row
            meetings = list(deduped.values())

            stats["clients"][client["slug"]]["reuniones"] = len(meetings)
            if meetings and not args.dry_run:
                supabase.upsert("reuniones", meetings, "ghl_appointment_id")
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
                "entity": "reuniones",
                "status": "success" if not errors else "partial_error",
                "stats": stats,
                "errors": errors,
            },
        )
    logging.info("Sync reuniones terminado: %s", stats)


if __name__ == "__main__":
    main()
