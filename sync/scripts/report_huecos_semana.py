from __future__ import annotations

"""Analisis de HUECOS de la semana: ¿hay un horario muerto que se repite?

Junta la linea de tiempo combinada (ambas cuentas) de varios dias, calcula
los huecos entre llamadas (excluyendo colacion 14-15 Chile) y los agrupa por
HORA DEL DIA para ver si hay una franja que se repite dia a dia.

Uso: python report_huecos_semana.py --dates 2026-08-11,2026-08-12,2026-08-13,2026-08-14
"""

import argparse
import sys
from collections import defaultdict
from datetime import datetime, date, time, timedelta

from report_calls_live import (
    GHLClient, token_for, fetch_calls, LOCATION, CHILE,
)

CLIENTS = ["bambutech", "gbs"]
LUNCH_START = time(14, 0)
LUNCH_END = time(15, 0)
BIG = 15 * 60      # hueco "grande" = 15 min


def hm(seconds: float) -> str:
    seconds = int(seconds)
    h, r = divmod(seconds, 3600)
    m, s = divmod(r, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m"


def lunch_overlap(a: datetime, b: datetime, day: date) -> float:
    ls = datetime.combine(day, LUNCH_START, tzinfo=CHILE)
    le = datetime.combine(day, LUNCH_END, tzinfo=CHILE)
    return max(0.0, (min(b, le) - max(a, ls)).total_seconds())


def hour_overlaps(a: datetime, b: datetime) -> dict[int, float]:
    """Reparte los segundos del hueco [a,b] entre las horas del dia que toca."""
    out: dict[int, float] = defaultdict(float)
    cur = a
    while cur < b:
        nxt = (cur.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
        seg_end = min(b, nxt)
        out[cur.hour] += (seg_end - cur).total_seconds()
        cur = seg_end
    return out


def day_gaps(day: date):
    win_start = datetime.combine(day, time.min, tzinfo=CHILE)
    win_end = win_start + timedelta(days=1)
    calls = []
    for slug in CLIENTS:
        ghl = GHLClient(token_for(slug))
        cs = [c for c in fetch_calls(ghl, LOCATION[slug], win_start, win_end)
              if (c["direction"] or "outbound") == "outbound"]
        for c in cs:
            c["ini"] = c["dt"]
            c["fin"] = c["dt"] + timedelta(seconds=c["intento"])
        calls.extend(cs)
    calls.sort(key=lambda c: c["ini"])
    gaps = []
    if len(calls) < 2:
        return calls, gaps
    for a, b in zip(calls, calls[1:]):
        raw = (b["ini"] - a["fin"]).total_seconds()
        if raw <= 0:
            continue
        real = raw - lunch_overlap(a["fin"], b["ini"], day)
        if real > 60:
            gaps.append((a["fin"], b["ini"], real))
    return calls, gaps


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dates", default="2026-08-11,2026-08-12,2026-08-13,2026-08-14")
    args = ap.parse_args()
    days = [date.fromisoformat(d.strip()) for d in args.dates.split(",") if d.strip()]

    per_hour_idle: dict[int, list[float]] = defaultdict(list)   # min ociosos por hora, por dia
    per_hour_bigdays: dict[int, int] = defaultdict(int)         # dias con hueco grande tocando esa hora
    day_summaries = []

    for day in days:
        calls, gaps = day_gaps(day)
        hour_idle: dict[int, float] = defaultdict(float)
        big = [g for g in gaps if g[2] >= BIG]
        big_hours = set()
        for a, b, _ in gaps:
            for h, sec in hour_overlaps(a, b).items():
                hour_idle[h] += sec
        for a, b, sec in big:
            for h in hour_overlaps(a, b):
                big_hours.add(h)
        for h in range(9, 20):
            per_hour_idle[h].append(hour_idle.get(h, 0) / 60)
        for h in big_hours:
            per_hour_bigdays[h] += 1
        first = calls[0]["ini"].astimezone(CHILE).strftime("%H:%M") if calls else "-"
        last = calls[-1]["fin"].astimezone(CHILE).strftime("%H:%M") if calls else "-"
        big_txt = "; ".join(f"{a.astimezone(CHILE).strftime('%H:%M')}-{b.astimezone(CHILE).strftime('%H:%M')} ({hm(s)})"
                            for a, b, s in sorted(big, key=lambda g: g[0]))
        day_summaries.append((day, first, last, len(calls), sum(g[2] for g in gaps), big_txt))

    L = []
    L.append("=" * 70)
    L.append(" HUECOS DE LA SEMANA — ¿hay un horario muerto que se repite?")
    L.append(" (linea de tiempo combinada, colacion 14-15 excluida)")
    L.append("=" * 70)
    L.append("")
    for day, first, last, n, idle, big_txt in day_summaries:
        L.append(f"{day.strftime('%a %d-%b')}  jornada {first}-{last}  |  {n} llam  |  ocioso {hm(idle)}")
        L.append(f"     huecos grandes (>=15m): {big_txt or 'ninguno'}")
    L.append("")
    L.append("-" * 70)
    L.append(" MAPA POR HORA (promedio de minutos ociosos + dias con hueco grande)")
    L.append("-" * 70)
    L.append(f" {'Hora':<8}{'min ociosos prom':<20}{'dias con hueco grande':<24}")
    ndays = len(days)
    for h in range(9, 20):
        vals = per_hour_idle.get(h, [])
        avg = sum(vals) / len(vals) if vals else 0
        bd = per_hour_bigdays.get(h, 0)
        marca = "  <<< SE REPITE" if bd >= max(2, ndays - 1) else ("  <-- frecuente" if bd >= 2 else "")
        lunch = "  (colacion)" if h == 14 else ""
        bar = "#" * int(round(avg))
        L.append(f" {h:02d}h     {avg:4.0f} min  {bar:<12} {bd}/{ndays} dias{marca}{lunch}")
    L.append("")
    L.append(" Lectura: '<<< SE REPITE' = hueco grande en esa hora en casi todos los dias.")

    text = "\n".join(L)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(text)
    out = "reporte_huecos_semana.txt"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(f"\n[archivo guardado: {out}]")


if __name__ == "__main__":
    main()
