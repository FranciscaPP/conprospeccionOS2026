"""Metas de reuniones válidas por cliente — fuente única (versionada en git).

tipo "contrato" = meta total del contrato.
tipo "mensual"  = meta por mes (se evalúa sobre el mes en curso).
Las claves son el cliente_slug tal como aparece en Supabase / vw_reuniones_semana.
"""

METAS = {
    "just4u":    {"validas": 40,  "tipo": "contrato"},
    "ecosmart":  {"validas": 30,  "tipo": "contrato"},
    "gbs":       {"validas": 45,  "tipo": "contrato"},
    "bambutech": {"validas": 100, "tipo": "contrato"},
    "clickie":   {"validas": 6,   "tipo": "mensual"},
    "demo":      {"validas": 12,  "tipo": "mensual"},  # portal demo para prospectos
}

# Mapa nombre visible (mayúsculas) -> slug, para dashboards que agrupan por nombre.
NOMBRE_A_SLUG = {
    "JUST4U": "just4u",
    "ECOSMART": "ecosmart",
    "GBS LOGISTICS": "gbs",
    "BAMBUTECH": "bambutech",
    "CLICKIE": "clickie",
    "TIRESIAS": "tiresias",
}


def meta_de(slug: str) -> dict | None:
    """Devuelve {'validas': int, 'tipo': str} o None si el cliente no tiene meta."""
    return METAS.get((slug or "").lower())
