"""Plan/tier por cliente — controla qué páginas ve cada uno en el portal.

base    -> Validación de Reuniones + Generar Reporte Mensual + Onboarding + Playbook.
premium -> además, el dashboard "Intelligence Insight" (Indicadores) en vivo.

El tier vive en la tabla `clientes` (columna `tier`), así se puede cambiar desde el
panel interno de Clientes (o Supabase) SIN tocar código ni desplegar. Se cachea 60 s.
"""
import time

import requests

from shared.config import supabase_url, supabase_key

# Fallback por si la base no responde (o el cliente no está en la tabla).
PLANES_FALLBACK = {
    "gbs":      "base",
    "bambutech": "premium",
    "clickie":  "premium",
    "tiresias": "premium",
}

_TTL = 60
_CACHE = {"data": None, "ts": 0.0}


def _fetch_tiers() -> dict:
    now = time.time()
    if _CACHE["data"] is not None and now - _CACHE["ts"] < _TTL:
        return _CACHE["data"]
    data = {}
    try:
        url, key = supabase_url(), supabase_key()
        r = requests.get(
            f"{url}/rest/v1/clientes?select=slug,tier",
            headers={"apikey": key, "Authorization": f"Bearer {key}"}, timeout=8)
        if r.ok:
            data = {x["slug"]: (x.get("tier") or "base") for x in r.json() if x.get("slug")}
    except Exception:
        data = {}
    _CACHE["data"] = data
    _CACHE["ts"] = now
    return data


def invalidar_cache():
    """Forzar relectura del tier (tras cambiarlo en el panel)."""
    _CACHE["data"] = None
    _CACHE["ts"] = 0.0


def plan_de(slug: str) -> str:
    s = (slug or "").lower()
    return _fetch_tiers().get(s) or PLANES_FALLBACK.get(s, "base")


def ve_premium(slug: str) -> bool:
    return plan_de(slug) == "premium"
