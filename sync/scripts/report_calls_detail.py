from __future__ import annotations

"""Analisis DETALLADO de cadencia/productividad de la SDR (EN VIVO desde GHL).

Mide el trabajo real dentro de la jornada:
  - Ventana de trabajo (primera -> ultima llamada) en hora Chile y Mexico
  - Span total vs tiempo real al telefono -> % de ocupacion
  - Tiempo muerto total (huecos entre llamadas)
  - Huecos largos (>= umbral) con hora inicio-fin -> detecta colacion y tiempos muertos
  - Hueco mas largo (probable colacion)
  - Separacion promedio entre llamadas y llamadas por hora activa
  - Proyeccion a jornada de 8 horas al ritmo observado

Uso: python report_calls_detail.py [--date YYYY-MM-DD] [--clients bambutech,gbs] [--gap-min 8]
"""

import argparse
import sys
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo

from report_calls_live import (
    GHLClient, token_for, fetch_calls, classify,
    LOCATION, NOMBRE, CHILE, UTC, fmt_min,
)

MEXICO = ZoneInfo("America/Mexico_City")
# zona horaria "de referencia" para leer la jornada de cada cuenta
CLIENT_TZ = {"bambutech": MEXICO, "gbs": CHILE}
TZ_LABEL = {"bambutech": "Mexico", "gbs": "Chile"}


def hm(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m"
    return f"{m}m {s:02d}s"


def analyze(slug: str, day: date, gap_min: int) -> str:
    ghl = GHLClient(token_for(slug))
    win_start = datetime.combine(day, time.min, tzinfo=CHILE)
    win_end = win_start + timedelta(days=1)
    calls = fetch_calls(ghl, LOCATION[slug], win_start, win_end)
    calls = [c for c in calls if (c["direction"] or "outbound") == "outbound"]
    tz = CLIENT_TZ.get(slug, CHILE)
    tzlab = TZ_LABEL.get(slug, "Chile")

    L: list[str] = []
    L.append("=" * 64)
    L.append(f" DETALLE CADENCIA — {NOMBRE.get(slug, slug.upper())} — {day.isoformat()}")
    L.append("=" * 64)
    if not calls:
        L.append(" Sin llamadas este dia.")
        return "\n".join(L)

    # ordenar por inicio; construir (inicio, fin) por llamada
    for c in calls:
        c["ini"] = c["dt"]
        c["fin"] = c["dt"] + timedelta(seconds=c["intento"])
    calls.sort(key=lambda c: c["ini"])

    primera = calls[0]["ini"]
    ultima = calls[-1]["fin"]
    span = (ultima - primera).total_seconds()
    phone = sum(c["intento"] for c in calls)
    n = len(calls)

    # huecos entre fin de una y comienzo de la siguiente
    gaps = []
    idle_total = 0.0
    for a, b in zip(calls, calls[1:]):
        g = (b["ini"] - a["fin"]).total_seconds()
        if g > 0:
            idle_total += g
            if g >= gap_min * 60:
                gaps.append((a["fin"], b["ini"], g))
    gaps.sort(key=lambda t: -t[2])

    span_h = span / 3600 or 0.001
    L.append("")
    L.append(f" Jornada ({tzlab}): "
             f"{primera.astimezone(tz).strftime('%H:%M')} -> {ultima.astimezone(tz).strftime('%H:%M')}"
             f"   |  (Chile): {primera.astimezone(CHILE).strftime('%H:%M')} -> {ultima.astimezone(CHILE).strftime('%H:%M')}")
    L.append(f" Span total de jornada ........ {hm(span)}")
    L.append(f" Llamadas ..................... {n}")
    L.append(f" Ritmo ........................ {n / span_h:.1f} llamadas/hora activa")
    L.append(f" Tiempo REAL al telefono ...... {hm(phone)}  ({100*phone/span:.0f}% del span)")
    L.append(f" Tiempo MUERTO (entre llamadas) {hm(idle_total)}  ({100*idle_total/span:.0f}% del span)")
    L.append(f" Separacion promedio/llamada .. {hm((span - phone)/max(1, n-1))} entre una y otra")
    L.append(f" Proyeccion a 8h al mismo ritmo {round(n / span_h * 8)} llamadas")

    if gaps:
        L.append("")
        L.append(f" HUECOS >= {gap_min} min (posible colacion / tiempo muerto):")
        for ini, fin, g in gaps:
            L.append(f"   {ini.astimezone(tz).strftime('%H:%M')} -> {fin.astimezone(tz).strftime('%H:%M')}"
                     f"   {hm(g):>8}  sin llamar")
        biggest = gaps[0]
        L.append(f" -> Hueco mas largo: {hm(biggest[2])} "
                 f"({biggest[0].astimezone(tz).strftime('%H:%M')}-{biggest[1].astimezone(tz).strftime('%H:%M')}) "
                 f"= probable colacion")
    else:
        L.append(f"\n Sin huecos >= {gap_min} min (ritmo continuo).")

    # densidad por hora (llamadas iniciadas)
    L.append("")
    L.append(" Llamadas por hora (hora " + tzlab + "):")
    from collections import Counter
    ch = Counter(c["ini"].astimezone(tz).hour for c in calls)
    for h in range(min(ch), max(ch) + 1):
        bar = "#" * ch.get(h, 0)
        L.append(f"   {h:02d}h  {ch.get(h,0):3d}  {bar}")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--clients", default="bambutech,gbs")
    ap.add_argument("--gap-min", type=int, default=8, help="Umbral de hueco en minutos (default 8).")
    args = ap.parse_args()
    day = date.fromisoformat(args.date) if args.date else datetime.now(CHILE).date()
    slugs = [s.strip() for s in args.clients.split(",") if s.strip()]
    parts = [analyze(s, day, args.gap_min) for s in slugs]
    text = "\n\n".join(parts)
    text += ("\n\nNota: tiempo al telefono y huecos calculados con dateAdded/dateUpdated de cada llamada.\n"
             "El tiempo muerto NO incluye emails/WhatsApp/carga de bases (esta SDR trabaja solo por telefono).")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(text)
    out = f"reporte_cadencia_{day.isoformat()}.txt"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(f"\n[archivo guardado: {out}]")


if __name__ == "__main__":
    main()
