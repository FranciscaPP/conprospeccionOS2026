from __future__ import annotations

import unicodedata
from enum import Enum
from typing import Any


def normalize_name(name: str | None) -> str:
    if not name:
        return ""
    stripped = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return " ".join(stripped.lower().split())


def names_match(snov_name: str | None, ghl_first_name: str | None, ghl_last_name: str | None) -> bool:
    """True si no hay choque de identidad: no hay suficiente informacion para
    comparar, o los nombres comparten al menos un token (nombre o apellido)."""
    ghl_name = " ".join(part for part in [ghl_first_name, ghl_last_name] if part)
    ghl_norm = normalize_name(ghl_name)
    snov_norm = normalize_name(snov_name)
    if not ghl_norm or not snov_norm:
        return True
    return bool(set(snov_norm.split()) & set(ghl_norm.split()))


def extract_snov_enrichment(prospect_data: dict[str, Any]) -> dict[str, Any]:
    """prospect_data es el dict 'data' de SnovClient.prospect_by_id()."""
    current_job = (prospect_data.get("currentJob") or [{}])[0]

    linkedin_personal = None
    for entry in prospect_data.get("social") or []:
        if entry.get("type") in ("linkedinProfile", "linkedIn") and entry.get("link"):
            linkedin_personal = entry["link"]
            break

    phones = prospect_data.get("phones") or []
    phone = None
    if phones:
        first_phone = phones[0]
        phone = first_phone if isinstance(first_phone, str) else (first_phone or {}).get("number")

    return {
        "first_name": prospect_data.get("firstName"),
        "last_name": prospect_data.get("lastName"),
        "name": prospect_data.get("name"),
        "country": current_job.get("country") or prospect_data.get("country"),
        "city": current_job.get("city") or prospect_data.get("locality"),
        "company_name": current_job.get("companyName"),
        "cargo": current_job.get("position"),
        "industria": current_job.get("industry") or prospect_data.get("industry"),
        "website": current_job.get("site"),
        "tamano_empresa": current_job.get("size"),
        "linkedin_empresa": current_job.get("socialLink"),
        "linkedin_personal": linkedin_personal,
        "phone": phone,
    }


CUSTOM_FIELD_ALIASES: dict[str, list[str]] = {
    "cargo": ["cargo"],
    "industria": ["industria"],
    "tamano_empresa": ["tamano empresa", "tamano de la empresa"],
    "linkedin_personal": ["linkedin personal"],
    "linkedin_empresa": ["linkedin empresa"],
    "status_prospecto": ["status prospecto"],
}


def resolve_custom_field_ids(raw_fields: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for field in raw_fields:
        normalized = normalize_name(field.get("name"))
        for key, aliases in CUSTOM_FIELD_ALIASES.items():
            if key in result:
                continue
            if normalized in aliases:
                result[key] = field.get("id")
    return result


CUSTOM_FIELD_KEYS = ("cargo", "industria", "tamano_empresa", "linkedin_personal", "linkedin_empresa")


def build_ghl_contact_payload(
    enrichment: dict[str, Any],
    email: str,
    cliente_slug: str,
    custom_field_ids: dict[str, str],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "email": email,
        "source": f"snov-{cliente_slug}",
        "tags": [cliente_slug],
    }
    if enrichment.get("first_name"):
        payload["firstName"] = enrichment["first_name"]
    if enrichment.get("last_name"):
        payload["lastName"] = enrichment["last_name"]
    if enrichment.get("company_name"):
        payload["companyName"] = enrichment["company_name"]
    if enrichment.get("website"):
        payload["website"] = enrichment["website"]
    if enrichment.get("country"):
        payload["country"] = enrichment["country"]
    if enrichment.get("phone"):
        payload["phone"] = enrichment["phone"]

    custom_fields = [
        {"id": custom_field_ids[key], "value": enrichment[key]}
        for key in CUSTOM_FIELD_KEYS
        if custom_field_ids.get(key) and enrichment.get(key)
    ]
    if custom_fields:
        payload["customFields"] = custom_fields
    return payload


class GhlAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    SKIP_MISMATCH = "skip_mismatch"
    SKIP_COMPLETE = "skip_complete"


def decide_action(
    existing_contact: dict[str, Any] | None,
    enrichment: dict[str, Any],
    custom_field_ids: dict[str, str],
) -> GhlAction:
    if existing_contact is None:
        return GhlAction.CREATE

    if not names_match(enrichment.get("name"), existing_contact.get("firstName"), existing_contact.get("lastName")):
        return GhlAction.SKIP_MISMATCH

    update_payload = build_update_payload(existing_contact, enrichment, custom_field_ids)
    return GhlAction.UPDATE if update_payload else GhlAction.SKIP_COMPLETE


def build_update_payload(
    existing_contact: dict[str, Any],
    enrichment: dict[str, Any],
    custom_field_ids: dict[str, str],
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if not existing_contact.get("companyName") and enrichment.get("company_name"):
        payload["companyName"] = enrichment["company_name"]
    if not existing_contact.get("website") and enrichment.get("website"):
        payload["website"] = enrichment["website"]
    if not existing_contact.get("phone") and enrichment.get("phone"):
        payload["phone"] = enrichment["phone"]

    existing_with_value = {
        cf.get("id") for cf in (existing_contact.get("customFields") or [])
        if cf.get("value") not in (None, "")
    }
    custom_fields = [
        {"id": custom_field_ids[key], "value": enrichment[key]}
        for key in CUSTOM_FIELD_KEYS
        if custom_field_ids.get(key) and enrichment.get(key)
        and custom_field_ids[key] not in existing_with_value
    ]
    if custom_fields:
        payload["customFields"] = custom_fields
    return payload
