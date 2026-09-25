from __future__ import annotations

"""Avance de las listas de trabajo diarias de la SDR (replica de smart lists GHL).

Replica los filtros de las smart lists que arma Francisca, recorriendo la base
de contactos (contacts/search). Por lista:

  universo (deben)  = contactos que calzan el filtro BASE (status/tag/telefono),
                      snapshot 1x/dia (primer envio) cacheado.
  trabajado (hecho) = contacto del universo al que se le LLAMO hoy (cruce por
                      contact_id con las llamadas del dia).
  pendiente         = deben - hecho.

Listas (segun filtros de Francisca, 14-sep-2026):
  1 Coordinando     telefono · STATUS PROSPECTO = Coordinando Reunion
  2 Info Adicional  telefono · STATUS PROSPECTO = Informacion Adicional
  3 Reagendar       telefono · STATUS PROSPECTO = Reagendar Reunion
  5 ATIQ nuevos     tag ~ 'atiq' · STATUS PROSPECTO vacio
  6 ATIQ no cont.   tag ~ 'atiq' · STATUS PROSPECTO = No Contesta
  7 No Cont. viejos telefono · STATUS PROSPECTO = No Contesta · sin actividad esta semana

Nota: la SDR usa 'ultima actividad != hoy' en GHL solo para ocultar de su vista
los ya trabajados; aca el 'hecho' se calcula con las llamadas reales del dia.
"""

import json
import os
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from report_calls_live import GHLClient, token_for, LOCATION, to_chile

CHILE = ZoneInfo("America/Santiago")
CLIENTS = ["bambutech", "gbs"]
_CACHE_DIR = os.path.join(os.path.dirname(__file__), "sdr_cache")

# custom field STATUS PROSPECTO por location
CF_STATUS = {"bambutech": "m3cYnSBB5t6WPArnU67e", "gbs": "73CZcGKJJr8hsSun2sV6"}

# key -> etiqueta corta (orden de despliegue = prioridad)
DISPLAY_ORDER = [
    ("coord", "🔥 Coordinando"),
    ("info", "🔥 Info Adic."),
    ("reagendar", "♻️ Reagendar"),
    ("atiq", "🆕 Lista ATIQ"),
    ("nc_viejos", "📞 NoCont viejos"),
]
LIST_KEYS = [k for k, _ in DISPLAY_ORDER]


def _norm(s) -> str:
    return (str(s or "")).lower().translate(str.maketrans("áéíóúñ", "aeioun")).strip()


def _status(contact: dict, slug: str) -> str:
    for f in contact.get("customFields", []) or []:
        if f.get("id") == CF_STATUS[slug]:
            return _norm(f.get("value"))
    return ""


def _week_start(day: date) -> datetime:
    monday = day - timedelta(days=day.weekday())
    return datetime.combine(monday, time.min, tzinfo=CHILE)


def contact_lists(contact: dict, slug: str, week_start: datetime) -> set[str]:
    """A que listas pertenece el contacto (universo base)."""
    if not contact.get("phone"):
        phone = False
    else:
        phone = True
    st = _status(contact, slug)
    tags = {_norm(t) for t in (contact.get("tags") or [])}
    is_atiq = any("atiq" in t for t in tags)
    out: set[str] = set()
    if phone and st == "coordinando reunion":
        out.add("coord")
    if phone and st == "informacion adicional":
        out.add("info")
    if phone and st == "reagendar reunion":
        out.add("reagendar")
    if is_atiq and phone:
        out.add("atiq")           # toda la lista ATIQ (por etiqueta), estable todo el dia
    if phone and st == "no contesta":
        du = to_chile(contact.get("dateUpdated"))
        if du and du < week_start:            # sin actividad esta semana
            out.add("nc_viejos")
    return out


def _fetch_all_contacts(ghl: GHLClient, location_id: str) -> list[dict]:
    out: list[dict] = []
    search_after = None
    for _ in range(200):  # tope de seguridad (~20k contactos)
        payload = ghl.search_contacts_page(location_id, search_after=search_after, page_limit=100)
        page = payload.get("contacts") or []
        if not page:
            break
        out.extend(page)
        search_after = page[-1].get("searchAfter")
        if len(page) < 100 or not search_after:
            break
    return out


def _compute_universe(day: date) -> dict:
    ws = _week_start(day)
    uni = {k: {"bambutech": [], "gbs": []} for k in LIST_KEYS}
    for slug in CLIENTS:
        ghl = GHLClient(token_for(slug))
        for c in _fetch_all_contacts(ghl, LOCATION[slug]):
            cid = c.get("id")
            if not cid:
                continue
            for k in contact_lists(c, slug, ws):
                uni[k][slug].append(cid)
    return uni


def universe_snapshot(day: date) -> dict:
    """Universo del dia (snapshot cacheado 1x/dia)."""
    os.makedirs(_CACHE_DIR, exist_ok=True)
    path = os.path.join(_CACHE_DIR, f"lists_{day.isoformat()}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    uni = _compute_universe(day)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(uni, fh, ensure_ascii=False)
    return uni


def lists_avance(day: date, allc: list[dict]) -> dict:
    uni = universe_snapshot(day)
    called: dict[str, set] = defaultdict(set)
    for c in allc:
        if c.get("contact_id"):
            called[c["slug"]].add(c["contact_id"])
    res: dict = {}
    for k in LIST_KEYS:
        res[k] = {}
        for slug in CLIENTS:
            ids = set(uni.get(k, {}).get(slug, []))
            res[k][slug] = {"trab": len(ids & called[slug]), "total": len(ids)}
    return res


def render_lists_section(day: date, allc: list[dict]) -> list[str]:
    try:
        av = lists_avance(day, allc)
    except Exception as e:
        return ["", f"_Avance de listas no disponible ({type(e).__name__})._"]
    LW, CW = 16, 10

    def cell(d):
        t, n = d["trab"], d["total"]
        if n == 0:
            return "—"
        return f"{t}/{n} {round(100 * t / n)}%"

    lines = [f"{'':<{LW}}{'Bambu':>{CW}}{'GBS':>{CW}}"]
    for k, label in DISPLAY_ORDER:
        b, g = av[k]["bambutech"], av[k]["gbs"]
        lines.append(f"{label:<{LW}}{cell(b):>{CW}}{cell(g):>{CW}}")
    return ["*Avance de listas* _(hecho/deben · hecho = la llamó hoy)_",
            "```\n" + "\n".join(lines) + "\n```",
            "_ATIQ (nuevos+no cont) es la lista L/X/V. NoCont viejos = relleno._"]
