from __future__ import annotations

import unicodedata
from datetime import datetime

from report_calls_live import to_chile


TARGET_STAGES = {
    "informacion adicional": "Información adicional",
    "coordinando reunion": "Coordinando reunión",
}


def _norm(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join(text.encode("ascii", "ignore").decode().lower().split())


def _status_field_id(ghl, location_id: str) -> str | None:
    for field in ghl.list_custom_fields(location_id).get("customFields") or []:
        if _norm(field.get("name")) == "status prospecto":
            return field.get("id")
    return None


def _empty_stage() -> dict[str, int]:
    return {"total": 0, "up_to_3": 0, "over_3": 0, "over_6": 0, "over_14": 0, "no_date": 0}


def followup_age_summary(
    ghl,
    location_id: str,
    now: datetime,
    *,
    unit_for_contact,
) -> dict[str, dict[str, dict[str, int]]]:
    """Cuenta estados activos por unidad y antigüedad de ``lastActivity``.

    Los umbrales son acumulados: un contacto con 20 días cuenta en >3, >6 y >14.
    ``unit_for_contact`` devuelve el slug atribuible o ``None`` para excluirlo.
    """
    field_id = _status_field_id(ghl, location_id)
    if not field_id:
        return {}
    result: dict[str, dict[str, dict[str, int]]] = {}
    search_after = None
    for _ in range(200):
        payload = ghl.search_contacts_page(location_id, search_after=search_after, page_limit=100)
        contacts = payload.get("contacts") or []
        if not contacts:
            break
        for contact in contacts:
            status = _norm(next((
                field.get("value")
                for field in contact.get("customFields") or []
                if field.get("id") == field_id
            ), ""))
            if status not in TARGET_STAGES:
                continue
            unit = unit_for_contact(contact)
            if not unit:
                continue
            row = result.setdefault(unit, {}).setdefault(status, _empty_stage())
            row["total"] += 1
            last_activity = to_chile(contact.get("lastActivity"))
            if last_activity is None:
                row["no_date"] += 1
                continue
            days = max(0, (now.date() - last_activity.date()).days)
            if days <= 3:
                row["up_to_3"] += 1
            if days > 3:
                row["over_3"] += 1
            if days > 6:
                row["over_6"] += 1
            if days > 14:
                row["over_14"] += 1
        search_after = contacts[-1].get("searchAfter")
        if len(contacts) < 100 or not search_after:
            break
    return result
