"""Alcance operativo activo para seguimiento de reuniones.

Estos slugs son los únicos clientes que deben alimentar el panel interno y la
sincronización inmediata/operativa de reuniones mientras el resto de clientes
no esté activado para este módulo.
"""

ACTIVE_MEETING_CLIENT_SLUGS = ("gbs", "bambutech", "balia")
ACTIVE_MEETING_CLIENT_NAMES = {
    "gbs": "GBS Logistics",
    "bambutech": "BambuTech",
    "balia": "Valia",
}


def is_active_meeting_client(slug: str | None) -> bool:
    return str(slug or "").strip().lower() in ACTIVE_MEETING_CLIENT_SLUGS
