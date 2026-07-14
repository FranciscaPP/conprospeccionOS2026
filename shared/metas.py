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


def _mes_actual() -> str:
    from datetime import date

    return date.today().strftime("%Y-%m")


def avance_meta(slug: str, validas_por_mes: dict[str, int], mes_actual: str | None = None) -> dict | None:
    """Avance de reuniones válidas contra la meta. FUENTE ÚNICA de la regla.

    - tipo "contrato" (GBS, BambuTech, Just4U, Ecosmart): se ACUMULAN todas las
      válidas de todos los meses hacia la meta total del contrato. Las válidas de
      junio siguen contando en julio, agosto, etc.
    - tipo "mensual" (Clickie): solo cuentan las válidas del mes en curso; la meta
      reinicia cada mes.

    ``validas_por_mes``: {"YYYY-MM": n_validas}. Cada pantalla decide qué es una
    reunión válida (según su fuente) y arma este diccionario; la regla de suma
    vive solo aquí.
    """
    meta = meta_de(slug)
    if not meta:
        return None
    mes_actual = mes_actual or _mes_actual()
    validas_por_mes = {m: int(v or 0) for m, v in (validas_por_mes or {}).items()}
    if meta["tipo"] == "mensual":
        avance = validas_por_mes.get(mes_actual, 0)
    else:
        avance = sum(validas_por_mes.values())
    objetivo = int(meta["validas"])
    return {
        "avance": avance,
        "meta": objetivo,
        "tipo": meta["tipo"],
        "cumplida": avance >= objetivo,
        "pct": round(100 * avance / objetivo) if objetivo else 0,
    }


def avance_acumulado_por_mes(slug: str, validas_por_mes: dict[str, int]) -> dict[str, int]:
    """Serie por mes ya acumulada, para mostrar el progreso mes a mes.

    Contrato: total corrido (junio incluye enero..junio, julio incluye ..julio).
    Mensual: el valor de cada mes tal cual (reinicia cada mes).
    """
    meta = meta_de(slug)
    mensual = bool(meta and meta["tipo"] == "mensual")
    salida: dict[str, int] = {}
    corrido = 0
    for mes in sorted(validas_por_mes):
        v = int(validas_por_mes.get(mes) or 0)
        if mensual:
            salida[mes] = v
        else:
            corrido += v
            salida[mes] = corrido
    return salida
