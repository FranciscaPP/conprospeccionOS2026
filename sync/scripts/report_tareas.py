from __future__ import annotations

"""Cumplimiento de TAREAS diarias de la SDR (EN VIVO desde GHL).

El workflow de GHL genera tareas automaticas segun el estado que marca la SDR
(ej: "Informacion adicional" hoy -> tarea de seguimiento en 2 dias; contactos
sin trabajar -> "INICIAR PROSPECCION"). Este reporte mide, para un dia:

  - Tareas que vencen ese dia, por TIPO (titulo + descripcion): total,
    completadas, pendientes, % cumplimiento.
  - Atrasadas: tareas de dias anteriores que siguen abiertas.
  - Cruce con llamadas del dia: de las tareas, cuantos contactos se llamaron
    y cuantos tuvieron conversacion real (>= --min-talk s). Detecta tareas
    marcadas como completadas SIN llamada al contacto.
  - Foco: % de llamadas del dia que fueron a contactos con tarea, y contactos
    llamados muchas veces en el dia (insistencia sobre el mismo contacto).

Uso:
   python report_tareas.py                       # bambutech, hoy (Chile)
   python report_tareas.py --client gbs --date 2026-09-23
   python report_tareas.py --no-calls            # solo tareas (rapido)
"""

import argparse
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta

from report_calls_live import GHLClient, token_for, fetch_calls, LOCATION, CHILE, to_chile

# (clave, etiqueta, palabras clave normalizadas). Orden = prioridad de match.
TIPOS = [
    ("reagendar", "Reagendar reunion", ("reagend",)),
    ("coordinando", "Coordinando reunion", ("coordinand",)),
    ("info_adicional", "Informacion adicional", ("informacion adicional", "info adicional")),
    ("avanzado", "Avanzado", ("avanzad",)),
    ("volver_llamar", "Volver a llamar", ("volver a llamar", "rellamar", "llamar de nuevo")),
    ("seguimiento", "Seguimiento", ("seguimiento",)),
    ("iniciar", "Iniciar prospeccion", ("iniciar", "prospeccion", "prspeccion")),
]
ETIQUETA = {k: lbl for k, lbl, _ in TIPOS} | {"otro": "Otro"}


def norm(s: str | None) -> str:
    s = re.sub(r"<[^>]+>|&nbsp;", " ", s or "")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


def tipo_de(task: dict) -> str:
    # El titulo manda; la descripcion solo desempata si el titulo no matchea.
    for texto in (norm(task.get("title")), norm(task.get("body"))):
        for key, _, kws in TIPOS:
            if any(kw in texto for kw in kws):
                return key
    return "otro"


def fetch_tasks(ghl: GHLClient, location_id: str) -> list[dict]:
    out: list[dict] = []
    skip = 0
    while skip <= 20000:
        r = ghl.client.post(f"/locations/{location_id}/tasks/search", json={"limit": 100, "skip": skip})
        r.raise_for_status()
        page = r.json().get("tasks") or []
        out += [t for t in page if not t.get("deleted")]
        if len(page) < 100:
            break
        skip += 100
    return out


def pct(a: int, b: int) -> str:
    return f"{round(100 * a / b)}%" if b else "-"


def compute_tareas(slug: str, day: date, calls: list[dict] | None = None,
                   with_calls: bool = True, min_talk: int = 20) -> dict:
    """Calcula el cumplimiento de tareas. `calls` (salientes del dia, con contact_id/status/dur)
    se puede pasar ya descargado; si es None y with_calls, se baja de GHL."""
    ghl = GHLClient(token_for(slug))
    loc = LOCATION[slug]
    tasks = fetch_tasks(ghl, loc)
    for t in tasks:
        t["_due"] = to_chile(t.get("dueDate"))
        t["_tipo"] = tipo_de(t)
        t["_done_at"] = to_chile(t.get("dateUpdated")) if t.get("completed") else None

    if calls is None:
        calls = []
        if with_calls:
            w0 = datetime.combine(day, time(0), CHILE)
            calls = [c for c in fetch_calls(ghl, loc, w0, w0 + timedelta(days=1))
                     if (c["direction"] or "outbound") == "outbound"]
    calls = [c for c in calls if c.get("contact_id")]

    # Datos de cada contacto (tareas + llamados): calidad de base y excluir contactos TEST.
    info: dict[str, dict] = {}
    for cid in {t.get("contactId") for t in tasks} | {c["contact_id"] for c in calls}:
        if not cid:
            continue
        try:
            info[cid] = ghl.get_contact(cid).get("contact") or {}
        except Exception:
            info[cid] = {}

    def nombre_de(cid) -> str:
        c = info.get(cid, {})
        return norm(f"{c.get('firstName') or ''} {c.get('lastName') or ''}")

    tests = {cid for cid in info if "test" in nombre_de(cid).split()}
    for t in tasks:
        nombre = nombre_de(t.get("contactId"))
        t["_sin_datos"] = (not info.get(t.get("contactId"), {}).get("companyName") or not nombre
                           or nombre.lstrip("+").replace(" ", "").isdigit() or nombre.startswith("whatsapp"))
    tasks = [t for t in tasks if t.get("contactId") not in tests]
    calls = [c for c in calls if c["contact_id"] not in tests]

    hoy = [t for t in tasks if t["_due"] and t["_due"].date() == day]
    atrasadas = [t for t in tasks if t["_due"] and t["_due"].date() < day and not t.get("completed")]

    calls_by_contact: dict[str, list[dict]] = defaultdict(list)
    for c in calls:
        calls_by_contact[c["contact_id"]].append(c)

    def llamado(t):
        return bool(calls_by_contact.get(t.get("contactId")))

    def conversado(t):
        return any(c["status"] == "completed" and c["dur"] >= min_talk
                   for c in calls_by_contact.get(t.get("contactId"), []))

    by_tipo: dict[str, list[dict]] = defaultdict(list)
    for t in hoy:
        by_tipo[t["_tipo"]].append(t)
    filas = []
    for k in [k for k, _, _ in TIPOS] + ["otro"]:
        ts = by_tipo.get(k)
        if ts:
            filas.append({"tipo": k, "label": ETIQUETA[k], "total": len(ts),
                          "done": sum(1 for t in ts if t.get("completed")),
                          "llamados": sum(llamado(t) for t in ts),
                          "conv": sum(conversado(t) for t in ts)})

    task_contacts = {t.get("contactId") for t in hoy if t.get("contactId")}
    insist = sorted((len(cs) for cs in calls_by_contact.values() if len(cs) >= 3), reverse=True)
    sd = [t for t in hoy if t["_sin_datos"]]
    return {
        "slug": slug, "day": day, "min_talk": min_talk, "with_calls": bool(calls) or with_calls,
        "hoy": hoy, "atrasadas": atrasadas, "tests": tests, "filas": filas,
        "total": len(hoy), "done": sum(1 for t in hoy if t.get("completed")),
        "sin_datos": len(sd), "sin_datos_done": sum(1 for t in sd if t.get("completed")),
        "n_calls": len(calls), "n_contactos": len(calls_by_contact),
        "calls_a_tareas": sum(1 for c in calls if c["contact_id"] in task_contacts),
        "tareas_llamadas": len(task_contacts & set(calls_by_contact)),
        "done_sin_llamada": sum(1 for t in hoy if t.get("completed") and not llamado(t)),
        "insist": insist,
        "done_por_hora": Counter(t["_done_at"].hour for t in hoy if t["_done_at"]),
    }


def build_report(slug: str, day: date, with_calls: bool, min_talk: int) -> str:
    d = compute_tareas(slug, day, with_calls=with_calls, min_talk=min_talk)
    tot, done = d["total"], d["done"]
    L = [f"CUMPLIMIENTO DE TAREAS - {slug.upper()} - {day:%d-%m-%Y}", ""]
    L.append(f"Tareas del dia: {tot} | completadas {done} | pendientes {tot - done} | cumplimiento {pct(done, tot)}")
    L.append(f"Atrasadas (dias anteriores, abiertas): {len(d['atrasadas'])}")
    L.append(f"Contactos solo con telefono (sin empresa aun): {d['sin_datos']} de {tot} tareas "
             f"({pct(d['sin_datos'], tot)}) | completadas de esas: {d['sin_datos_done']}")
    L.append("")
    hdr = f"{'Tipo':<24}{'Total':>6}{'Hechas':>8}{'Pend':>6}{'%':>6}"
    if with_calls:
        hdr += f"{'Llamados':>10}{'Conv>=' + str(min_talk) + 's':>11}"
    L += [hdr, "-" * len(hdr)]
    for f in d["filas"]:
        row = f"{f['label']:<24}{f['total']:>6}{f['done']:>8}{f['total'] - f['done']:>6}{pct(f['done'], f['total']):>6}"
        if with_calls:
            row += f"{f['llamados']:>10}{f['conv']:>11}"
        L.append(row)
    if d["atrasadas"]:
        L += ["", "Atrasadas por tipo: " + ", ".join(
            f"{ETIQUETA[k]} {n}" for k, n in Counter(t["_tipo"] for t in d["atrasadas"]).most_common())]
    if with_calls:
        ins = d["insist"]
        L += ["", "CRUCE CON LLAMADAS DEL DIA",
              f"Llamadas salientes: {d['n_calls']} a {d['n_contactos']} contactos distintos",
              f"Llamadas a contactos con tarea hoy: {d['calls_a_tareas']} ({pct(d['calls_a_tareas'], d['n_calls'])})",
              f"Contactos con tarea llamados: {d['tareas_llamadas']} de {tot}",
              f"Tareas marcadas completadas SIN llamada hoy al contacto: {d['done_sin_llamada']}",
              f"Contactos llamados 3+ veces hoy: {len(ins)}" + (f" (max {ins[0]} llamadas a un mismo contacto)" if ins else "")]
    if d["done_por_hora"]:
        L += ["", "Tareas completadas por hora (Chile): "
              + "  ".join(f"{h}h:{n}" for h, n in sorted(d["done_por_hora"].items()))]
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--client", default="bambutech", choices=sorted(LOCATION))
    ap.add_argument("--date", help="YYYY-MM-DD (Chile). Default: hoy")
    ap.add_argument("--no-calls", action="store_true")
    ap.add_argument("--min-talk", type=int, default=20)
    a = ap.parse_args()
    day = date.fromisoformat(a.date) if a.date else datetime.now(CHILE).date()
    sys.stdout.reconfigure(encoding="utf-8")
    print(build_report(a.client, day, not a.no_calls, a.min_talk))


if __name__ == "__main__":
    main()
