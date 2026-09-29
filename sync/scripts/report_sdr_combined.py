from __future__ import annotations

"""Analisis COMBINADO de la SDR (una sola persona, ambas cuentas) EN VIVO desde GHL.

Fusiona las llamadas de BambuTech + GBS en UNA linea de tiempo para medir:
  - Ritmo real combinado (llamadas/hora) y por cuenta
  - Huecos reales cuando NO llamo a NINGUNA cuenta (excluye colacion pactada)
  - Reparto del dia entre cuentas
  - Distribucion por hora (Chile) separada por cuenta

Colacion pactada: 14:00-15:00 Chile (= 13:00-14:00 Peru = 12:00-13:00 Mexico).

Uso: python report_sdr_combined.py [--date YYYY-MM-DD] [--gap-min 8]
"""

import argparse
import sys
from collections import Counter
from datetime import datetime, date, time, timedelta

from report_calls_live import (
    GHLClient, token_for, fetch_calls, classify,
    LOCATION, NOMBRE, CHILE, fmt_min,
)

CLIENTS = ["bambutech", "gbs"]
LUNCH_START = time(14, 0)   # Chile
LUNCH_END = time(15, 0)     # Chile
# Ventanas que NO cuentan como ocio ademas de la colacion
EXCLUDE_EXTRA = [(time(11, 0), time(11, 30))]  # reunion diaria Francisca-Norma


def hm(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m {s:02d}s"


def lunch_overlap(a: datetime, b: datetime, day: date) -> float:
    total = 0.0
    for ws_t, we_t in [(LUNCH_START, LUNCH_END), *EXCLUDE_EXTRA]:
        ls = datetime.combine(day, ws_t, tzinfo=CHILE)
        le = datetime.combine(day, we_t, tzinfo=CHILE)
        total += max(0.0, (min(b, le) - max(a, ls)).total_seconds())
    return total


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--gap-min", type=int, default=8)
    args = ap.parse_args()
    day = date.fromisoformat(args.date) if args.date else datetime.now(CHILE).date()
    win_start = datetime.combine(day, time.min, tzinfo=CHILE)
    win_end = win_start + timedelta(days=1)

    allcalls = []
    per_client = {}
    for slug in CLIENTS:
        ghl = GHLClient(token_for(slug))
        cs = [c for c in fetch_calls(ghl, LOCATION[slug], win_start, win_end)
              if (c["direction"] or "outbound") == "outbound"]
        for c in cs:
            c["slug"] = slug
            c["ini"] = c["dt"]
            c["fin"] = c["dt"] + timedelta(seconds=c["intento"])
        per_client[slug] = cs
        allcalls.extend(cs)

    L: list[str] = []
    L.append("=" * 66)
    L.append(f" JORNADA COMBINADA DE LA SDR — {day.isoformat()}  (1 persona, 2 cuentas)")
    L.append(f" Colacion pactada excluida: 14:00-15:00 Chile")
    L.append("=" * 66)
    if not allcalls:
        L.append(" Sin llamadas este dia.")
        print("\n".join(L)); return

    allcalls.sort(key=lambda c: c["ini"])
    primera, ultima = allcalls[0]["ini"], allcalls[-1]["fin"]
    span = (ultima - primera).total_seconds()
    lunch_secs = lunch_overlap(primera, ultima, day)
    span_neto = span - lunch_secs
    phone = sum(c["intento"] for c in allcalls)
    n = len(allcalls)

    L.append("")
    L.append(f" Primera llamada .............. {primera.astimezone(CHILE).strftime('%H:%M')} Chile")
    L.append(f" Ultima llamada ............... {ultima.astimezone(CHILE).strftime('%H:%M')} Chile")
    L.append(f" Span jornada (bruto) ......... {hm(span)}")
    L.append(f" Span neto (sin colacion) ..... {hm(span_neto)}")
    L.append(f" Llamadas TOTALES ............. {n}   (BambuTech {len(per_client['bambutech'])} + GBS {len(per_client['gbs'])})")
    L.append(f" Ritmo combinado .............. {n/(span_neto/3600):.1f} llamadas/hora")
    L.append(f" Tiempo real al telefono ...... {hm(phone)}  ({100*phone/span_neto:.0f}% del tiempo neto)")
    L.append(f" Proyeccion a 8h netas ........ {round(n/(span_neto/3600)*8)} llamadas al ritmo actual")

    # huecos combinados (no llama a NINGUNA cuenta), descontando colacion
    gaps = []
    idle_total = 0.0
    for a, b in zip(allcalls, allcalls[1:]):
        raw = (b["ini"] - a["fin"]).total_seconds()
        if raw <= 0:
            continue
        real = raw - lunch_overlap(a["fin"], b["ini"], day)
        if real <= 0:
            continue
        idle_total += real
        if real >= args.gap_min * 60:
            gaps.append((a["fin"], b["ini"], real))
    gaps.sort(key=lambda t: -t[2])

    L.append(f" Tiempo MUERTO real ........... {hm(idle_total)}  ({100*idle_total/span_neto:.0f}% del tiempo neto)")
    L.append("")
    if gaps:
        L.append(f" HUECOS >= {args.gap_min} min SIN llamar a NINGUNA cuenta (fuera de colacion):")
        for ini, fin, g in gaps:
            L.append(f"   {ini.astimezone(CHILE).strftime('%H:%M')} -> {fin.astimezone(CHILE).strftime('%H:%M')} Chile   {hm(g):>8}")
        L.append(f" -> Suma de huecos largos: {hm(sum(g for *_ , g in gaps))}")
    else:
        L.append(f" Sin huecos >= {args.gap_min} min fuera de colacion. Ritmo continuo.")

    # por hora, separado por cuenta
    L.append("")
    L.append(" Llamadas por hora (Chile)   B=BambuTech  G=GBS:")
    cb = Counter(c["ini"].astimezone(CHILE).hour for c in per_client["bambutech"])
    cg = Counter(c["ini"].astimezone(CHILE).hour for c in per_client["gbs"])
    hrs = range(min(c["ini"].astimezone(CHILE).hour for c in allcalls),
                max(c["ini"].astimezone(CHILE).hour for c in allcalls) + 1)
    for h in hrs:
        b, g = cb.get(h, 0), cg.get(h, 0)
        lunch_mark = "  <- colacion" if h == 14 else ""
        L.append(f"   {h:02d}h  B:{b:3d} G:{g:3d}  total {b+g:3d}  {'B'*b}{'G'*g}{lunch_mark}")

    text = "\n".join(L)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(text)
    out = f"reporte_sdr_combinado_{day.isoformat()}.txt"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(f"\n[archivo guardado: {out}]")


if __name__ == "__main__":
    main()
