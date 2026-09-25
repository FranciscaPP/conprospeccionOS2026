from __future__ import annotations

"""Update por HORA de la SDR a un bot de Telegram (llamadas + etapas).

Cada envio trae, en 3 vistas (Total 2 clientes / BambuTech / GBS):

  CANTIDADES  llamadas totales | contestadas | no contestadas (no-answer+ocupado)
              | contestadas + marcadas
  TIEMPOS     total llamadas | hablando (contestadas) | solo tono (marcadas)
              | contestadas + marcadas

  ...en dos vistas: ACUMULADO HOY y bloque de la ULTIMA HORA.

En el ultimo envio del dia (>=19h, o --cierre) se agrega el bloque de pipeline:
  - Actualizados hoy en INFORMACION ADICIONAL / COORDINANDO REUNION /
    REUNION AGENDADA, con detalle nombre - cargo - empresa - cliente.
  - Dias sin gestion (contacto mas antiguo) en INFORMACION ADICIONAL /
    COORDINANDO REUNION / REAGENDAR REUNION.

Config (.env):
   TELEGRAM_SDR_TOKEN=<token del bot de @BotFather>
   TELEGRAM_SDR_CHAT_ID=<chat id destino>

Uso:
   python report_sdr_telegram.py            # calcula y ENVIA a Telegram
   python report_sdr_telegram.py --dry-run  # solo imprime (sin enviar)
   python report_sdr_telegram.py --cierre    # fuerza el bloque de pipeline
   python report_sdr_telegram.py --chat-discovery   # lista chat_ids del bot
"""

import argparse
import sys
from collections import Counter, defaultdict
from datetime import datetime, date, time, timedelta

import httpx

from config import get_optional_env
from report_calls_live import (
    GHLClient, token_for, fetch_calls, classify, LOCATION, CHILE, to_chile,
)
from report_stages_live import norm, parse_dt, all_open_opps, stage_names
from report_sdr_lists import universe_snapshot
from report_tareas import compute_tareas

CLIENTS = ["bambutech", "gbs"]
NOMBRE_CORTO = {"bambutech": "BambuTech", "gbs": "GBS"}
# Ventanas que NO cuentan como ocio (reunion diaria con Norma). El almuerzo NO va
# aca: se maneja como credito flexible de 1h/dia (LUNCH_CREDIT) porque la SDR puede
# almorzar a otra hora si llama durante el 14-15.
EXCLUDE_WINDOWS = [
    (time(11, 0), time(11, 30)),  # reunion diaria Francisca-Norma
]
LUNCH_CREDIT = 3600   # 1h/dia de almuerzo que no cuenta como ocio (acumulado), donde sea


def hm(seconds: float) -> str:
    seconds = int(seconds)
    h, r = divmod(seconds, 3600)
    m, _ = divmod(r, 60)
    return f"{h}h{m:02d}m" if h else f"{m}m"


def _excluded_overlap(w0: datetime, w1: datetime, day: date) -> float:
    """Segundos de [w0,w1] que caen en colacion (14-15) o reunion Norma (11-11:30)."""
    total = 0.0
    for ws, we in EXCLUDE_WINDOWS:
        ls = datetime.combine(day, ws, tzinfo=CHILE)
        le = datetime.combine(day, we, tzinfo=CHILE)
        total += max(0.0, (min(w1, le) - max(w0, ls)).total_seconds())
    return total


GAP_MIN = 300   # un silencio >= 5 min entre llamadas cuenta como hueco "sin llamar"


def call_gaps(calls: list[dict], day: date) -> tuple[list[tuple[datetime, datetime, float]], float]:
    """Huecos entre llamadas consecutivas (todas las de la SDR, cualquier cliente).

    Devuelve ([(desde, hasta, seg)] de los huecos >= GAP_MIN, sin la reunion diaria),
    y los segundos "entre llamadas" cortos (< GAP_MIN: marcar, anotar, cerrar tarea).
    """
    cs = sorted(calls, key=lambda c: c["ini"])
    largos, cortos = [], 0.0
    fin = None
    for c in cs:
        if fin is not None:
            gap = (c["ini"] - fin).total_seconds()
            if gap >= GAP_MIN:
                gap -= _excluded_overlap(fin, c["ini"], day)
                if gap > 0:
                    largos.append((fin, c["ini"], gap))
            elif gap > 0:
                cortos += gap
        fin = c["fin"] if fin is None else max(fin, c["fin"])
    return largos, cortos


def idle_seconds(calls: list[dict], w0: datetime, w1: datetime, day: date) -> float:
    """Tiempo SIN gestionar dentro de [w0,w1]: ventana - tiempo al telefono - excluidas."""
    if w1 <= w0:
        return 0.0
    busy = sum(c["intento"] for c in calls)               # repique + conversacion
    excl = _excluded_overlap(w0, w1, day)
    return max(0.0, (w1 - w0).total_seconds() - busy - excl)


# --------------------------------------------------------------------------- #
# Metricas de llamadas
# --------------------------------------------------------------------------- #
def call_metrics(calls: list[dict]) -> dict:
    """Cuenta y tiempos para un subconjunto de llamadas (ya con 'cls')."""
    contest = [c for c in calls if c["cls"] == "contestada"]
    marcadas = [c for c in calls if c["cls"] in ("no_contesta", "ocupado")]
    t_hablar = sum(c["dur"] for c in contest)
    t_tono = sum(c["intento"] for c in marcadas)
    return {
        "total": len(calls),
        "contest": len(contest),
        "no_contest": len(marcadas),
        "cont_marc": len(contest) + len(marcadas),
        "t_total": sum(c["intento"] for c in calls),   # repique + conversacion, todas
        "t_hablar": t_hablar,                           # talk time real (contestadas)
        "t_tono": t_tono,                               # timbrando sin respuesta
        "t_cont_marc": t_hablar + t_tono,
    }


def _split_metrics(calls: list[dict]) -> tuple[dict, dict, dict]:
    """Devuelve (total, bambutech, gbs) para un set de llamadas."""
    return (
        call_metrics(calls),
        call_metrics([c for c in calls if c["slug"] == "bambutech"]),
        call_metrics([c for c in calls if c["slug"] == "gbs"]),
    )


def _render_table_solo(m: dict) -> str:
    """Tabla de una sola columna (modo --solo <cliente>)."""
    rows = [
        ("Llamadas", m["total"]), ("Contest.", m["contest"]), ("No cont.", m["no_contest"]),
        None,
        ("Hablando", hm(m["t_hablar"])), ("Repique", hm(m["t_tono"])), ("Total tel", hm(m["t_total"])),
    ]
    lines = ["-" * 18 if r is None else f"{r[0]:<10}{str(r[1]):>8}" for r in rows]
    return "```\n" + "\n".join(lines) + "\n```"


def _table(calls: list[dict], solo: str | None) -> str:
    if solo:
        return _render_table_solo(call_metrics([c for c in calls if c["slug"] == solo]))
    return _render_table(*_split_metrics(calls))


def _render_table(mt: dict, mb: dict, mg: dict) -> str:
    """Recuadro monoespaciado angosto y alineado (se ve ordenado en movil)."""
    LW, CW = 10, 6   # ancho etiqueta / columna -> 10+18 = 28 chars, cabe en vertical
    def r(lbl, a, b, c) -> str:
        return f"{lbl:<{LW}}{str(a):>{CW}}{str(b):>{CW}}{str(c):>{CW}}"
    lines = [
        r("", "TOTAL", "Bambu", "GBS"),
        r("Llamadas", mt["total"], mb["total"], mg["total"]),
        r("Contest.", mt["contest"], mb["contest"], mg["contest"]),
        r("No cont.", mt["no_contest"], mb["no_contest"], mg["no_contest"]),
        "-" * (LW + CW * 3),
        r("Hablando", hm(mt["t_hablar"]), hm(mb["t_hablar"]), hm(mg["t_hablar"])),
        r("Repique", hm(mt["t_tono"]), hm(mb["t_tono"]), hm(mg["t_tono"])),
        r("Total tel", hm(mt["t_total"]), hm(mb["t_total"]), hm(mg["t_total"])),
    ]
    return "```\n" + "\n".join(lines) + "\n```"


# --------------------------------------------------------------------------- #
# Bloque de cierre (pipeline)
# --------------------------------------------------------------------------- #
# key canonica -> etiqueta legible
ACT_LABEL = {
    "info": "Informacion adicional",
    "coord": "Coordinando reunion",
    "agendada": "Reunion agendada",
}
SIN_LABEL = {
    "info": "Informacion adicional",
    "coord": "Coordinando reunion",
    "reagendar": "Reagendar reunion",
}
MAX_DETALLE = 15   # tope de contactos listados por etapa (Telegram cap 4096)


def stage_key(name: str) -> str | None:
    n = norm(name)
    if "informacion adicional" in n:
        return "info"
    if "coordinando reunion" in n:
        return "coord"
    if "reagendar" in n:
        return "reagendar"
    if "reunion agendada" in n:
        return "agendada"
    return None


def _cargo_field_id(ghl: GHLClient, location_id: str) -> str | None:
    """Resuelve el custom field 'Cargo' por NOMBRE (IDs difieren por subcuenta).

    Prioriza el nombre EXACTO 'Cargo': hay varios campos que contienen la palabra
    (CARGO MACRO, Cargo de quien publica, CARGO DEL REFERIDO...) y solo 'Cargo' es
    el titulo real del contacto.
    """
    try:
        data = ghl.list_custom_fields(location_id)
    except Exception:
        return None
    fields = data.get("customFields", []) or []
    for f in fields:                                  # 1) match exacto
        if norm(f.get("name", "")) == "cargo":
            return f.get("id")
    for f in fields:                                  # 2) fallback: contiene "cargo"
        if "cargo" in norm(f.get("name", "")):
            return f.get("id")
    return None


def _clean(s: str | None) -> str:
    return (str(s or "").replace("`", "").strip()) or "—"


def _contact_detail(ghl: GHLClient, contact_id: str | None, cargo_fid: str | None,
                    fallback: str) -> dict:
    if not contact_id:
        return {"nombre": _clean(fallback), "cargo": "—", "empresa": "—"}
    try:
        c = (ghl.get_contact(contact_id) or {}).get("contact", {}) or {}
    except Exception:
        return {"nombre": _clean(fallback), "cargo": "—", "empresa": "—"}
    nombre = (c.get("contactName")
              or " ".join(x for x in [c.get("firstName"), c.get("lastName")] if x)
              or fallback)
    cargo = "—"
    if cargo_fid:
        for f in c.get("customFields", []) or []:
            if f.get("id") == cargo_fid:
                cargo = f.get("value")
                break
    return {"nombre": _clean(nombre), "cargo": _clean(cargo), "empresa": _clean(c.get("companyName"))}


def appointments_today(day: date) -> dict:
    """Citas AGENDADAS hoy (dateAdded == day) en el calendario de cada cliente.

    Esta es la señal REAL de 'se agendó una reunión' — no depende de que muevan
    la tarjeta del pipeline a 'Reunión Agendada'.
    """
    now = datetime.now(CHILE)
    win_start = datetime.combine(day, time.min, tzinfo=CHILE)
    st = int((win_start - timedelta(days=1)).timestamp() * 1000)
    en = int((now + timedelta(days=180)).timestamp() * 1000)   # la reunion puede ser a futuro
    out = {"bambutech": [], "gbs": []}
    for slug in CLIENTS:
        ghl = GHLClient(token_for(slug))
        try:
            cals = ghl.list_calendars(LOCATION[slug]).get("calendars", []) or []
        except Exception:
            cals = []
        seen = set()
        for c in cals:
            try:
                ev = ghl.list_calendar_events(LOCATION[slug], str(st), str(en),
                                              calendar_id=c.get("id")).get("events", []) or []
            except Exception:
                continue
            for e in ev:
                eid = e.get("id")
                if eid in seen:
                    continue
                da = to_chile(e.get("dateAdded"))
                if not (da and da.date() == day):
                    continue
                if (e.get("appointmentStatus") or "").lower() in ("cancelled", "canceled", "noshow"):
                    continue
                seen.add(eid)
                out[slug].append({
                    "title": e.get("title") or "(sin título)",
                    "when": to_chile(e.get("startTime")),
                })
    return out


def _status_field_id(ghl: GHLClient, location_id: str) -> str | None:
    """Resuelve el custom field 'STATUS PROSPECTO' por nombre (IDs difieren por subcuenta)."""
    try:
        data = ghl.list_custom_fields(location_id)
    except Exception:
        return None
    for f in data.get("customFields", []) or []:
        if norm(f.get("name", "")) == "status prospecto":
            return f.get("id")
    return None


# valor del campo STATUS PROSPECTO -> key canonica
STATUS_TO_KEY = {
    "informacion adicional": "info",
    "coordinando reunion": "coord",
    "reagendar reunion": "reagendar",
}


def pipeline_data(day: date, with_detail: bool) -> dict:
    """Embudo + dias sin gestion leyendo el campo STATUS PROSPECTO del CONTACTO.

    La SDR trabaja moviendo ese campo a diario (no la tarjeta del pipeline). Se
    recorren todos los contactos (contacts/search) y se lee su STATUS PROSPECTO +
    dateUpdated. 'Agendadas' viene de las citas reales del calendario.
    """
    now = datetime.now(CHILE)
    entered = {k: {"bambutech": 0, "gbs": 0} for k in ACT_LABEL}   # tocados HOY en ese status
    current = {k: {"bambutech": 0, "gbs": 0} for k in ACT_LABEL}   # total actual en ese status
    detalle = {k: [] for k in ACT_LABEL}
    singestion = {k: [] for k in SIN_LABEL}                        # (dias, nombre, cli) con dias > 3

    for slug in CLIENTS:
        ghl = GHLClient(token_for(slug))
        sfid = _status_field_id(ghl, LOCATION[slug])
        cfid = _cargo_field_id(ghl, LOCATION[slug])
        if not sfid:
            continue
        search_after = None
        for _ in range(80):   # tope de seguridad (~8000 contactos)
            payload = ghl.search_contacts_page(LOCATION[slug], search_after=search_after, page_limit=100)
            cs = payload.get("contacts") or []
            if not cs:
                break
            for c in cs:
                val = None; cargo = "—"
                for cf in (c.get("customFields") or []):
                    if cf.get("id") == sfid:
                        val = cf.get("value")
                    elif cfid and cf.get("id") == cfid:
                        cargo = cf.get("value") or "—"
                key = STATUS_TO_KEY.get(norm(val or ""))
                if not key:
                    continue
                du = to_chile(c.get("dateUpdated"))
                nombre = c.get("contactName") or c.get("companyName") or "(sin nombre)"
                empresa = c.get("companyName") or "—"
                if key in current:
                    current[key][slug] += 1
                if key in ACT_LABEL and du and du.date() == day:
                    entered[key][slug] += 1
                    detalle[key].append({"nombre": _clean(nombre), "cargo": _clean(cargo),
                                         "empresa": _clean(empresa), "cli": NOMBRE_CORTO[slug]})
                if key in SIN_LABEL:
                    dias = (now - du).days if du else -1
                    if dias > 3:
                        singestion[key].append((dias, _clean(nombre), NOMBRE_CORTO[slug]))
            search_after = cs[-1].get("searchAfter")
            if len(cs) < 100 or not search_after:
                break

    # 'Agendadas' = citas REALES del calendario agendadas hoy (no el status ni el pipeline).
    appts = appointments_today(day)
    detalle["agendada"] = []
    for slug in CLIENTS:
        entered["agendada"][slug] = len(appts[slug])
        current["agendada"][slug] = len(appts[slug])
        for a in appts[slug]:
            when = a["when"].strftime("%d-%b %H:%M") if a["when"] else "?"
            detalle["agendada"].append({
                "nombre": f"{_clean(a['title'])} · {when}",
                "cargo": "—", "empresa": "—", "cli": NOMBRE_CORTO[slug],
            })
    return {"entered": entered, "current": current, "detalle": detalle, "singestion": singestion}


def embudo_line(pdata: dict) -> list[str]:
    """KPI de agendadas + trabajados hoy + cartera actual (STATUS PROSPECTO)."""
    e = pdata["entered"]
    c = pdata.get("current", {})
    ag = e["agendada"]["bambutech"] + e["agendada"]["gbs"]
    info = e["info"]["bambutech"] + e["info"]["gbs"]
    coord = e["coord"]["bambutech"] + e["coord"]["gbs"]
    def tot(d, k):
        return d.get(k, {}).get("bambutech", 0) + d.get(k, {}).get("gbs", 0)
    return [
        f"🎯 *Agendadas hoy: {ag}*  (Bambu {e['agendada']['bambutech']} · GBS {e['agendada']['gbs']})",
        f"Trabajados hoy → Info {info} · Coord {coord} · Agend {ag}",
        f"En cartera (status actual) → Info {tot(c,'info')} · Coord {tot(c,'coord')}",
    ]


def render_cierre(pdata: dict) -> str:
    L = ["", "*CIERRE DEL DIA · Pipeline*", "", "*Actualizados hoy*"]
    body = []
    e = pdata["entered"]
    for key, label in ACT_LABEL.items():
        body.append(f"{label} — Bambu {e[key]['bambutech']} · GBS {e[key]['gbs']}")
        items = pdata["detalle"][key]
        for d in items[:MAX_DETALLE]:
            body.append(f"  • {d['nombre']} · {d['cargo']} · {d['empresa']} [{d['cli']}]")
        if len(items) > MAX_DETALLE:
            body.append(f"  … y {len(items) - MAX_DETALLE} más")
    L.append("```\n" + "\n".join(body) + "\n```")

    L += ["", "*Días sin gestión (> 3 días)*"]
    sg = []
    for key, label in SIN_LABEL.items():
        items = sorted(pdata["singestion"][key], key=lambda t: -t[0])
        sg.append(f"{label}: {len(items)}")
        for dias, nombre, cli in items[:MAX_DETALLE]:
            sg.append(f"  • {dias}d — {nombre} [{cli}]")
        if len(items) > MAX_DETALLE:
            sg.append(f"  … y {len(items) - MAX_DETALLE} más")
    L.append("```\n" + "\n".join(sg) + "\n```")
    return "\n".join(L)


# --------------------------------------------------------------------------- #
# Cumplimiento de bloques horarios asignados a la SDR
# --------------------------------------------------------------------------- #
# (start, end, cliente_asignado). 14-15 = almuerzo (no se evalua).
BLOCKS = [
    (time(10, 0), time(11, 0), "gbs"),
    (time(11, 0), time(14, 0), "bambutech"),
    (time(15, 0), time(17, 30), "gbs"),
    (time(17, 30), time(19, 0), "bambutech"),
]


def bloques_line(allc: list[dict], day: date, now: datetime) -> list[str]:
    out = ["*Cumplimiento de bloques*", "```"]
    for ws, we, cli in BLOCKS:
        bs = datetime.combine(day, ws, tzinfo=CHILE)
        be = datetime.combine(day, we, tzinfo=CHILE)
        if now < bs:
            continue                       # bloque aun no empieza
        en_curso = now < be
        calls = [c for c in allc if bs <= c["ini"] < be]
        n = len(calls)
        asign = sum(1 for c in calls if c["slug"] == cli)
        pct = round(100 * asign / n) if n else 0
        tag = NOMBRE_CORTO[cli]
        hh = f"{ws.strftime('%H:%M')}–{we.strftime('%H:%M')}"
        if n == 0:
            mark = "🟡 en curso" if en_curso else "🔴 sin llamadas"
            out.append(f"{hh} {tag:<9} {n:>3}  {mark}")
        else:
            mark = "🟢" if pct >= 70 else "🟠"
            suf = " (en curso)" if en_curso else ""
            out.append(f"{hh} {tag:<9} {asign}/{n} ({pct}%) {mark}{suf}")
    out.append("```")
    return out


def contest_hora_line(allc: list[dict]) -> str:
    """% de contestacion por hora (contestadas/total)."""
    tot = defaultdict(int); con = defaultdict(int)
    for c in allc:
        tot[c["ini"].hour] += 1
        if c["cls"] == "contestada":
            con[c["ini"].hour] += 1
    parts = []
    for h in sorted(tot):
        pct = round(100 * con[h] / tot[h]) if tot[h] else 0
        parts.append(f"{h:02d}h {pct}%")
    return "Contest% por hora: " + " · ".join(parts)


# --------------------------------------------------------------------------- #
# Mensaje principal
# --------------------------------------------------------------------------- #
def fetch_day_calls(day: date) -> list[dict]:
    """Trae las llamadas salientes del dia (ambos clientes), ya clasificadas."""
    win_start = datetime.combine(day, time.min, tzinfo=CHILE)
    win_end = win_start + timedelta(days=1)
    allc: list[dict] = []
    for slug in CLIENTS:
        ghl = GHLClient(token_for(slug))
        cs = [c for c in fetch_calls(ghl, LOCATION[slug], win_start, win_end)
              if (c["direction"] or "outbound") == "outbound"]
        for c in cs:
            c["slug"] = slug
            c["cls"] = classify(c["status"], c["dur"])
            c["ini"] = c["dt"]
            c["fin"] = c["dt"] + timedelta(seconds=c["intento"])
        allc.extend(cs)
    allc.sort(key=lambda c: c["ini"])
    return allc


def agendada_banner(pdata: dict | None) -> list[str]:
    """Banner destacado cada vez que hay reunion(es) agendada(s) hoy."""
    if not pdata:
        return []
    e = pdata["entered"]["agendada"]
    ag = e["bambutech"] + e["gbs"]
    if ag <= 0:
        return []
    plural = ag > 1
    out = [f"🎉🎉 *¡{ag} REUNIÓN{'ES' if plural else ''} "
           f"AGENDADA{'S' if plural else ''} HOY!* 🎉🎉"]
    names = [f"{d['nombre']} [{d['cli']}]" for d in pdata["detalle"]["agendada"]]
    if names:
        out.append("   " + " · ".join(names))
    return out


# --------------------------------------------------------------------------- #
# Panel de avance de listas (lo que DEBE hacer) con semaforo
# --------------------------------------------------------------------------- #
# META = suma de estas listas (SIN los No Contesta viejos, que se descuentan solos)
META_LISTS = [
    ("coord", "🔥 Coordinando"),
    ("info", "📋 Info Adicional"),
    ("reagendar", "♻️ Reagendar"),
    ("atiq", "🆕 ATIQ (L/X/V)"),
]


def _semaforo(pct: int) -> str:
    return "🟢" if pct >= 80 else ("🟡" if pct >= 50 else "🔴")


def avance_section(day: date, allc: list[dict], now: datetime, solo: str | None = None) -> list[str]:
    """Avance por lista con semaforo: hecho/total, acumulado + lo de la ultima hora."""
    try:
        uni = universe_snapshot(day)
    except Exception as e:
        return [f"_Avance de listas no disponible ({type(e).__name__})._"]
    called_acc = {c["contact_id"] for c in allc if c.get("contact_id")}
    be = now.replace(minute=0, second=0, microsecond=0)
    bs = be - timedelta(hours=1)
    called_hr = {c["contact_id"] for c in allc
                 if bs <= c["ini"] < be and c.get("contact_id")}

    def ids(k):
        d = uni.get(k, {})
        if solo:
            return set(d.get(solo, []))
        return set(d.get("bambutech", [])) | set(d.get("gbs", []))

    L = ["🎯 *AVANCE — lo que debe hacer hoy*  _(hecho / total)_"]
    tt = ta = th = 0
    for k, label in META_LISTS:
        u = ids(k)
        total = len(u)
        if total == 0:
            continue
        acc = len(u & called_acc)
        hr = len(u & called_hr)
        tt += total; ta += acc; th += hr
        pct = round(100 * acc / total)
        extra = f"   (+{hr} esta hora)" if hr else ""
        L.append(f"{_semaforo(pct)} {label}:  *{acc}/{total}*  ({pct}%){extra}")
    pct = round(100 * ta / tt) if tt else 0
    L.append("────────────────────")
    L.append(f"{_semaforo(pct)} *META DÍA:  {ta}/{tt}  ({pct}%)*   ·  +{th} en la última hora")
    return L


def tareas_section(td: dict, now: datetime) -> list[str]:
    """Cumplimiento de tareas GHL del dia (workflow) + cruce con llamadas."""
    tot, done = td["total"], td["done"]
    pct = round(100 * done / tot) if tot else 0
    be = now.replace(minute=0, second=0, microsecond=0)
    ult = sum(1 for t in td["hoy"] if t["_done_at"] and be - timedelta(hours=1) <= t["_done_at"] < be)
    L = [f"✅ *TAREAS DEL DÍA · {NOMBRE_CORTO.get(td['slug'], td['slug'])}*",
         f"{_semaforo(pct)} *Cumplidas: {done}/{tot}  ({pct}%)*  ·  pendientes {tot - done}"
         f"  ·  +{ult} última hora"]
    body = []
    for f in td["filas"]:
        fp = round(100 * f["done"] / f["total"]) if f["total"] else 0
        body.append(f"{f['label'][:19]:<19}{f['done']:>4}/{f['total']:<4}{fp:>3}%")
    if body:
        L.append("```\n" + "\n".join(body) + "\n```")
    if td["atrasadas"]:
        L.append(f"⏰ Atrasadas de días anteriores: {len(td['atrasadas'])}")
    L.append(f"📞 Tareas con llamada hoy: {td['tareas_llamadas']}/{tot}"
             f"  ·  llamadas que fueron a tareas: {td['calls_a_tareas']}/{td['n_calls']}")
    if td["done_sin_llamada"]:
        L.append(f"⚠ Completadas SIN llamada hoy: {td['done_sin_llamada']}")
    if td["sin_datos"]:
        L.append(f"📇 Tareas de contactos solo con teléfono (sin empresa aún): {td['sin_datos']}/{tot}"
                 f"  ·  cumplidas {td['sin_datos_done']}")
    return L


def build_message(day: date, allc: list[dict], pdata: dict | None = None,
                  cierre: bool = False, audience: str = "manager",
                  solo: str | None = None, tdata: dict | None = None,
                  allc_all: list[dict] | None = None) -> str:
    """audience='manager' (Francisca, todo) | 'sdr' (Nora, sin cumplimiento de bloques).
    allc_all: llamadas de la SDR en TODOS los clientes (modo solo) para jornada y huecos."""
    now = datetime.now(CHILE)
    head = f"📞 *SDR update{' · ' + NOMBRE_CORTO[solo] if solo else ''}* · {now.strftime('%H:%M')} · {day.strftime('%d-%b')}"
    banner = agendada_banner(pdata)
    if not allc:
        lines = [head]
        if banner:
            lines += ["", *banner]
        lines.append("\n_Sin llamadas aun hoy._")
        if tdata:
            lines += ["", *tareas_section(tdata, now)]
        if pdata:
            lines += ["", *embudo_line(pdata)]
        msg = "\n".join(lines)
        return (msg + "\n" + render_cierre(pdata)) if (cierre and pdata) else msg

    # Acumulado
    mt, mb, mg = _split_metrics(allc)
    if solo:
        mt = call_metrics([c for c in allc if c["slug"] == solo])

    # Bloque ultima hora completa: [hora-1, hora)
    block_end = now.replace(minute=0, second=0, microsecond=0)
    block_start = block_end - timedelta(hours=1)
    block = [c for c in allc if block_start <= c["ini"] < block_end]
    hlabel = f"{block_start.hour:02d}–{block_end.hour:02d}h"

    # La SDR es una sola: jornada y huecos se miden con TODAS sus llamadas (todos los clientes).
    sdr = sorted(allc_all or allc, key=lambda c: c["ini"])
    primera = sdr[0]["ini"]
    ultima_fin = max(c["fin"] for c in sdr)

    # Huecos reales sin llamar (>= 5 min). El mayor, hasta 1h, se toma como almuerzo.
    largos, entre = call_gaps(sdr, day)
    almuerzo = max(largos, key=lambda g: g[2]) if largos else None
    if almuerzo and almuerzo[2] < 1800:
        almuerzo = None                      # < 30 min no es almuerzo
    lunch_cred = min(LUNCH_CREDIT, almuerzo[2]) if almuerzo else 0
    idle_acc = max(0.0, sum(g[2] for g in largos) - lunch_cred)
    al_tel = sum(c["intento"] for c in sdr)
    # Ultima hora: huecos recortados a la ventana + hueco abierto si dejo de llamar
    abiertos = largos + ([(ultima_fin, now, (now - ultima_fin).total_seconds())]
                         if not cierre and (now - ultima_fin).total_seconds() >= GAP_MIN else [])
    idle_blk = sum(max(0.0, (min(e, block_end) - max(s, block_start)).total_seconds())
                   for s, e, _ in abiertos if not (almuerzo and s == almuerzo[0]))

    # Calidad del volumen: contactos unicos vs remarcaciones + contestadas reales (>=20s)
    unicos = len({c["contact_id"] for c in allc if c.get("contact_id")})
    reales = sum(1 for c in allc if c["cls"] == "contestada" and c["dur"] >= 20)

    ag = 0
    if pdata:
        ag = pdata["entered"]["agendada"]["bambutech"] + pdata["entered"]["agendada"]["gbs"]

    jornada = f"_Jornada {primera.strftime('%H:%M')} → {ultima_fin.strftime('%H:%M')} · {mt['total']} llamadas"
    if solo and len(sdr) != mt["total"]:
        jornada += f" {NOMBRE_CORTO[solo]} de {len(sdr)} totales"
    parts = [head, jornada + "_"]
    if banner:
        parts += ["", *banner]

    # 0) TAREAS del workflow (cumplimiento) — la metrica principal
    if tdata:
        parts += ["", *tareas_section(tdata, now)]

    # 1) AVANCE por lista (lo que debe hacer) con semaforo
    parts += ["", *avance_section(day, allc, now, solo)]

    # 2) Ociosidad — lo mas importante para medir si esta trabajando
    parts += ["", f"🕓 *Huecos sin llamar (≥5 min): {hm(idle_acc)}*"
                  + ("  _(sin contar almuerzo)_" if almuerzo else "")]
    top = sorted(largos, key=lambda g: -g[2])[:4]
    if top:
        parts.append("   " + " · ".join(
            f"{s:%H:%M}–{e:%H:%M} ({hm(sec)}{', almuerzo' if almuerzo and s == almuerzo[0] else ''})"
            for s, e, sec in sorted(top)))
    parts.append(f"⏱ Entre llamadas (<5 min: marcar, anotar, tareas): {hm(entre)}  ·  al teléfono {hm(al_tel)}")
    if not cierre and (now - ultima_fin).total_seconds() >= GAP_MIN and now.date() == day:
        parts.append(f"⚠ Última llamada hace {hm((now - ultima_fin).total_seconds())}")
    if reales is not None:
        parts.append(f"🎯 Agendadas hoy: {ag}  ·  contestadas reales ≥20s: {reales}")
        if reales:
            parts.append(f"💬 1 conversación real cada {round(mt['total'] / reales, 1)} llamadas"
                         f"  ·  {unicos} contactos distintos")
        else:
            parts.append(f"💬 Sin conversaciones reales aún  ·  {unicos} contactos distintos")

    # 3) Llamadas acumuladas (por cliente)
    parts += ["", "*LLAMADAS · acumulado hoy*", _table(allc, solo)]

    # 4) La ultima hora cerrada
    parts += ["", f"*ÚLTIMA HORA · {hlabel}*"]
    if block:
        parts.append(_table(block, solo))
        parts.append(f"🕓 huecos ≥5 min esta hora: {hm(idle_blk)}")
    else:
        parts.append("_Sin llamadas en la última hora._")

    # Banderas
    flags = []
    if primera.time() > time(10, 5):
        flags.append(f"⚠ arrancó {primera.strftime('%H:%M')}")
    if flags:
        parts += ["", " · ".join(flags)]

    if cierre and pdata:
        parts.append(render_cierre(pdata))

    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# Envio
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# Grafico de avance por hora (Pillow, sin dependencias pesadas)
# --------------------------------------------------------------------------- #
COL_BAMBU = (46, 125, 50)     # verde
COL_GBS = (123, 47, 160)      # morado


def _font(size: int):
    from PIL import ImageFont
    for name in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


COL_REAL = (21, 101, 192)     # azul
COL_TAREA = (239, 108, 0)     # naranjo


def render_hourly_chart(day: date, allc: list[dict], solo: str | None = None,
                        tdata: dict | None = None) -> bytes | None:
    """PNG de lineas por hora. Normal: BambuTech (verde) vs GBS (morado).
    Modo solo: llamadas del cliente, conversaciones reales >=20s y tareas cumplidas."""
    if solo:
        return _render_series_chart(day, allc, solo, tdata)
    if not allc:
        return None
    try:
        from io import BytesIO
        from PIL import Image, ImageDraw
    except Exception:
        return None

    h0 = min(c["ini"].hour for c in allc)
    h1 = max(c["ini"].hour for c in allc)
    hours = list(range(h0, h1 + 1))
    cb = {h: 0 for h in hours}
    cg = {h: 0 for h in hours}
    for c in allc:
        (cb if c["slug"] == "bambutech" else cg)[c["ini"].hour] += 1
    ymax = max([1] + [cb[h] for h in hours] + [cg[h] for h in hours])
    # techo "bonito"
    step = 1 if ymax <= 5 else (2 if ymax <= 10 else (5 if ymax <= 30 else 10))
    ytop = ((ymax + step - 1) // step) * step

    W, H = 1000, 560
    ml, mr, mt, mb = 70, 40, 90, 70
    pw, ph = W - ml - mr, H - mt - mb
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    f_title = _font(30); f_lbl = _font(20); f_leg = _font(22); f_val = _font(18)

    d.text((ml, 26), f"Avance por hora · llamadas · {day.strftime('%d-%b')}", fill=(30, 30, 30), font=f_title)
    # leyenda
    lx = W - mr - 300
    d.line([(lx, 40), (lx + 34, 40)], fill=COL_BAMBU, width=5)
    d.ellipse([lx + 13, 34, lx + 21, 42], fill=COL_BAMBU)
    d.text((lx + 44, 30), "BambuTech", fill=COL_BAMBU, font=f_leg)
    d.line([(lx, 68), (lx + 34, 68)], fill=COL_GBS, width=5)
    d.ellipse([lx + 13, 62, lx + 21, 70], fill=COL_GBS)
    d.text((lx + 44, 58), "GBS", fill=COL_GBS, font=f_leg)

    def X(i): return ml + (pw * i / max(1, len(hours) - 1))
    def Y(v): return mt + ph - (ph * v / ytop)

    # grilla + eje Y
    for gy in range(0, ytop + 1, step):
        y = Y(gy)
        d.line([(ml, y), (ml + pw, y)], fill=(230, 230, 230), width=1)
        d.text((ml - 34, y - 10), str(gy), fill=(120, 120, 120), font=f_lbl)
    # eje X (horas)
    for i, h in enumerate(hours):
        d.text((X(i) - 12, mt + ph + 12), f"{h:02d}h", fill=(120, 120, 120), font=f_lbl)

    def plot(counts, color):
        pts = [(X(i), Y(counts[h])) for i, h in enumerate(hours)]
        if len(pts) >= 2:
            d.line(pts, fill=color, width=4, joint="curve")
        for (px, py), h in zip(pts, hours):
            d.ellipse([px - 6, py - 6, px + 6, py + 6], fill=color)
            d.text((px - 6, py - 30), str(counts[h]), fill=color, font=f_val)

    plot(cg, COL_GBS)
    plot(cb, COL_BAMBU)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _render_series_chart(day: date, allc: list[dict], solo: str, tdata: dict | None) -> bytes | None:
    try:
        from io import BytesIO
        from PIL import Image, ImageDraw
    except Exception:
        return None
    calls = [c for c in allc if c["slug"] == solo]
    llam = Counter(c["ini"].hour for c in calls)
    real = Counter(c["ini"].hour for c in calls if c["cls"] == "contestada" and c["dur"] >= 20)
    tar = Counter(tdata["done_por_hora"]) if tdata else Counter()
    series = [("Llamadas", llam, COL_BAMBU), ("Conv. reales >=20s", real, COL_REAL),
              ("Tareas cumplidas", tar, COL_TAREA)]
    horas_all = set(llam) | set(tar)
    if not horas_all:
        return None
    hours = list(range(min(horas_all), max(horas_all) + 1))
    ymax = max([1] + [cnt[h] for _, cnt, _ in series for h in hours])
    step = 1 if ymax <= 5 else (2 if ymax <= 10 else (5 if ymax <= 30 else 10))
    ytop = ((ymax + step - 1) // step) * step

    W, H = 1000, 560
    ml, mr, mt, mb = 70, 40, 120, 70
    pw, ph = W - ml - mr, H - mt - mb
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    f_title = _font(30); f_lbl = _font(20); f_leg = _font(20); f_val = _font(18)
    d.text((ml, 22), f"Avance por hora · {NOMBRE_CORTO[solo]} · {day.strftime('%d-%b')}",
           fill=(30, 30, 30), font=f_title)
    lx = ml
    for name, _, col in series:
        d.line([(lx, 82), (lx + 30, 82)], fill=col, width=5)
        d.text((lx + 38, 70), name, fill=col, font=f_leg)
        lx += 60 + int(d.textlength(name, font=f_leg))

    def X(i): return ml + (pw * i / max(1, len(hours) - 1))
    def Y(v): return mt + ph - (ph * v / ytop)

    for gy in range(0, ytop + 1, step):
        y = Y(gy)
        d.line([(ml, y), (ml + pw, y)], fill=(230, 230, 230), width=1)
        d.text((ml - 34, y - 10), str(gy), fill=(120, 120, 120), font=f_lbl)
    for i, h in enumerate(hours):
        d.text((X(i) - 12, mt + ph + 12), f"{h:02d}h", fill=(120, 120, 120), font=f_lbl)
    for _, cnt, col in series:
        pts = [(X(i), Y(cnt[h])) for i, h in enumerate(hours)]
        if len(pts) >= 2:
            d.line(pts, fill=col, width=4, joint="curve")
        for (px, py), h in zip(pts, hours):
            d.ellipse([px - 6, py - 6, px + 6, py + 6], fill=col)
            if cnt[h]:
                d.text((px - 6, py - 30), str(cnt[h]), fill=col, font=f_val)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def send_telegram_photo(png: bytes, caption: str, chat_id: str | None = None) -> None:
    token = get_optional_env("TELEGRAM_SDR_TOKEN")
    chat_id = chat_id or get_optional_env("TELEGRAM_SDR_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("Falta TELEGRAM_SDR_TOKEN o TELEGRAM_SDR_CHAT_ID en .env")
    r = httpx.post(
        f"https://api.telegram.org/bot{token}/sendPhoto",
        data={"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"},
        files={"photo": ("avance.png", png, "image/png")},
        timeout=60,
    )
    r.raise_for_status()


def send_telegram(text: str, chat_id: str | None = None) -> None:
    token = get_optional_env("TELEGRAM_SDR_TOKEN")
    chat_id = chat_id or get_optional_env("TELEGRAM_SDR_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("Falta TELEGRAM_SDR_TOKEN o TELEGRAM_SDR_CHAT_ID en .env")
    r = httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        timeout=30,
    )
    r.raise_for_status()


def chat_discovery() -> None:
    token = get_optional_env("TELEGRAM_SDR_TOKEN")
    if not token:
        print("Falta TELEGRAM_SDR_TOKEN en .env"); return
    r = httpx.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=30)
    data = r.json()
    seen = {}
    for u in data.get("result", []):
        msg = u.get("message") or u.get("channel_post") or {}
        chat = msg.get("chat") or {}
        if chat.get("id"):
            seen[chat["id"]] = f"{chat.get('title') or chat.get('first_name') or ''} ({chat.get('type')})"
    if not seen:
        print("No hay mensajes aun. Enviale un mensaje al bot y reintenta.")
    for cid, label in seen.items():
        print(f"  chat_id={cid}  ->  {label}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--chat-discovery", action="store_true")
    ap.add_argument("--cierre", action="store_true", help="Forzar el bloque de pipeline (cierre del dia).")
    ap.add_argument("--force", action="store_true", help="Enviar aunque sea fuera de horario laboral.")
    ap.add_argument("--solo", choices=sorted(LOCATION),
                    help="Reporte de un solo cliente (llamadas, grafico y tareas solo de ese cliente).")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if args.chat_discovery:
        chat_discovery(); return
    # guardia horario para el modo automatico (Task Scheduler cada hora)
    now = datetime.now(CHILE)
    if not args.dry_run and not args.force and (now.weekday() >= 5 or not (10 <= now.hour < 22)):
        print(f"Fuera de horario laboral ({now:%a %H:%M}); no se envia. Usa --force para forzar.")
        return
    day = date.fromisoformat(args.date) if args.date else now.date()
    # El bloque de cierre se agrega en el ultimo envio del dia (21h Chile) o con --cierre
    cierre = args.cierre or now.hour >= 21
    solo = args.solo
    allc = fetch_day_calls(day)          # SIEMPRE todos los clientes: la SDR es una sola (huecos/jornada)
    allc_all = None
    tdata = None
    if solo:
        CLIENTS[:] = [solo]   # de aqui en adelante (pipeline, citas) solo ese cliente
        try:
            tdata = compute_tareas(solo, day, calls=[c for c in allc if c["slug"] == solo])
            allc = [c for c in allc if c.get("contact_id") not in tdata["tests"]]   # fuera contactos TEST
        except Exception as e:
            print(f"[tareas no disponibles: {type(e).__name__}: {e}]")
        allc_all = allc
        allc = [c for c in allc if c["slug"] == solo]
    pdata = pipeline_data(day, with_detail=cierre)   # embudo/agendadas cada hora; detalle solo en cierre
    text = build_message(day, allc, pdata=pdata, cierre=cierre, audience="manager", solo=solo, tdata=tdata,
                         allc_all=allc_all)
    png = render_hourly_chart(day, allc, solo=solo, tdata=tdata)
    caption = ("📈 Avance por hora · 🟢 llamadas · 🔵 conv. reales · 🟠 tareas cumplidas" if solo
               else "📈 Avance por hora · 🟢 BambuTech · 🟣 GBS")
    print(text)

    if args.dry_run:
        if png:
            with open("avance_por_hora.png", "wb") as fh:
                fh.write(png)
            print("\n[grafico guardado: avance_por_hora.png]")
        return

    # Destino 1: Francisca (manager) — todo
    send_telegram(text)
    print("\n[enviado a Telegram · Francisca]")
    if png:
        send_telegram_photo(png, caption)

    # Destino 2: Nora (SDR) — mismo reporte SIN cumplimiento de bloques.
    # Solo si esta configurado TELEGRAM_SDR_CHAT_ID_NORA (ella debe darle /start al bot).
    nora_chat = get_optional_env("TELEGRAM_SDR_CHAT_ID_NORA")
    if nora_chat:
        nora_text = build_message(day, allc, pdata=pdata, cierre=cierre, audience="sdr", solo=solo, tdata=tdata,
                                     allc_all=allc_all)
        send_telegram(nora_text, chat_id=nora_chat)
        if png:
            send_telegram_photo(png, caption, chat_id=nora_chat)
        print("[enviado a Telegram · Nora]")


if __name__ == "__main__":
    if "--operational" in sys.argv:
        from sdr_reporting.cli import main as operational_main

        raise SystemExit(operational_main([arg for arg in sys.argv[1:] if arg != "--operational"]))
    main()
