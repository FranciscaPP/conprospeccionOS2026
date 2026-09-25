from __future__ import annotations

"""Reporte RÁPIDO de llamadas EN VIVO desde GHL (no lee Supabase).

Uso:
  python report_calls_live.py                 # hoy, bambutech + gbs
  python report_calls_live.py --date 2026-08-11
  python report_calls_live.py --clients bambutech,gbs --days 1

Mide el trabajo real de la SDR por cliente/dia:
  - Total de llamadas (salientes)
  - Contestadas (talk time real) / No contesta / Ocupado / Fallida / Otras
  - Minutos reales de conversacion (GHL NO expone tiempo de repique)
  - Ventana de trabajo (primera -> ultima llamada, hora Chile)
  - Distribucion por hora
"""

import argparse
import sys
from collections import defaultdict
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo

from config import get_optional_env
from ghl_client import GHLClient

CHILE = ZoneInfo("America/Santiago")
UTC = ZoneInfo("UTC")

TOKEN_ENV = {
    "gbs": "GHL_TOKEN_GBS_LOGISTICS",
    "bambutech": "GHL_TOKEN_BAMBUTECH",
    "balia": "GHL_TOKEN_BALIA",
}
LOCATION = {
    "bambutech": "FJ1YCwi4UVvwcBb8qlOb",
    "gbs": "u9b8KkJXhM8lqJfzxa7G",
    "balia": get_optional_env("GHL_LOCATION_BALIA") or "",
}
NOMBRE = {"bambutech": "BAMBU TECH", "gbs": "GBS", "balia": "BALIA"}


def token_for(slug: str) -> str:
    env_key = TOKEN_ENV.get(slug, f"GHL_TOKEN_{slug.upper()}")
    tok = get_optional_env(env_key) or get_optional_env(f"GHL_TOKEN_{slug.upper()}")
    if not tok:
        raise RuntimeError(f"Falta token {env_key} en .env")
    return tok


def to_chile(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(CHILE)


def classify(status: str | None, dur: int) -> str:
    s = (status or "").lower()
    if s == "completed" and dur > 0:
        return "contestada"
    if s == "completed":            # completed sin talk time -> contesto pero 0s (raro)
        return "contestada"
    if s == "no-answer":
        return "no_contesta"
    if s == "busy":
        return "ocupado"
    if s in ("failed", "canceled"):
        return "fallida"
    return "otras"                  # ringing / in-progress / initiated / null


def call_duration(msg: dict) -> int:
    dur = ((msg.get("meta") or {}).get("call") or {}).get("duration")
    try:
        return int(round(float(dur))) if dur is not None else 0
    except (TypeError, ValueError):
        return 0


def call_status(msg: dict) -> str | None:
    return msg.get("status") or (((msg.get("meta") or {}).get("call") or {}).get("status"))


def fetch_calls(ghl: GHLClient, location_id: str, win_start: datetime, win_end: datetime) -> list[dict]:
    """Trae mensajes TYPE_CALL cuya fecha (Chile) cae dentro de [win_start, win_end)."""
    calls: list[dict] = []
    start_after_date = None
    start_after_id = None
    win_start_ms = int(win_start.astimezone(UTC).timestamp() * 1000)
    pages = 0
    while pages < 60:  # tope de seguridad
        pages += 1
        payload = ghl.search_conversations(
            location_id, limit=100,
            start_after_date=start_after_date, start_after_id=start_after_id,
        )
        convs = payload.get("conversations") or []
        if not convs:
            break
        stop = False
        for conv in convs:
            last_ms = conv.get("lastMessageDate")
            # conversaciones vienen de mas nuevo a mas viejo; si ya pasamos la ventana, cortar
            if isinstance(last_ms, (int, float)) and last_ms < win_start_ms:
                stop = True
                break
            if conv.get("lastMessageType") != "TYPE_CALL" and conv.get("type") != "TYPE_PHONE":
                continue
            msgs = fetch_messages(ghl, conv["id"])
            for m in msgs:
                if m.get("messageType") != "TYPE_CALL":
                    continue
                dt = to_chile(m.get("dateAdded"))
                if dt is None or not (win_start <= dt < win_end):
                    continue
                added = to_chile(m.get("dateAdded"))
                updated = to_chile(m.get("dateUpdated"))
                dur = call_duration(m)
                intento = 0
                if added and updated:
                    intento = max(0, int(round((updated - added).total_seconds())))
                # Tope realista: dateUpdated a veces se actualiza horas despues (workflow /
                # llamada que queda "en curso"), inflando el "solo tono". Una llamada real no
                # dura mas que su conversacion + ~90s de repique/setup; no contesta <= 120s.
                intento = min(intento, (dur + 90) if dur > 0 else 60)
                calls.append({
                    "id": m.get("id"),
                    "dt": dt,
                    "date_added": m.get("dateAdded"),
                    "date_updated": m.get("dateUpdated"),
                    "status": call_status(m),
                    "dur": dur,
                    "intento": intento,          # dateUpdated - dateAdded (repique + conversacion), con tope
                    "direction": m.get("direction"),
                    "contact_id": conv.get("contactId") or m.get("contactId"),
                    "user_id": m.get("userId"),
                })
        last = convs[-1]
        start_after_date = last.get("lastMessageDate")
        start_after_id = last.get("id")
        if stop or len(convs) < 100 or not start_after_date:
            break
    return calls


def fetch_messages(ghl: GHLClient, conversation_id: str) -> list[dict]:
    out: list[dict] = []
    last_id = None
    for _ in range(20):
        payload = ghl.list_conversation_messages(conversation_id, limit=100, last_message_id=last_id)
        wrapper = payload.get("messages") or {}
        page = wrapper.get("messages") or []
        out.extend(page)
        if not wrapper.get("nextPage") or not page:
            break
        last_id = wrapper.get("lastMessageId") or page[-1].get("id")
        if not last_id:
            break
    return out


def fmt_min(seconds: int) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s:02d}s"


def report_client(slug: str, day: date, min_talk: int = 20) -> dict:
    ghl = GHLClient(token_for(slug))
    win_start = datetime.combine(day, time.min, tzinfo=CHILE)
    win_end = win_start + timedelta(days=1)
    calls = fetch_calls(ghl, LOCATION[slug], win_start, win_end)
    outbound = [c for c in calls if (c["direction"] or "outbound") == "outbound"]

    buckets: dict[str, list[dict]] = defaultdict(list)
    for c in outbound:
        buckets[classify(c["status"], c["dur"])].append(c)

    # Una "contestada" de GHL (status=completed) incluye buzon/contestador de pocos
    # segundos que la SDR dejo pasar. Solo cuenta como CONVERSACION REAL si supera el
    # umbral (default 20s). El resto es buzon/corte y no vale como contacto logrado.
    reales = [c for c in buckets["contestada"] if c["dur"] >= min_talk]
    buzon = [c for c in buckets["contestada"] if c["dur"] < min_talk]

    talk = sum(c["dur"] for c in buckets["contestada"])                # talk time bruto (todo completed)
    talk_real = sum(c["dur"] for c in reales)                          # talk time de conversaciones reales
    intento_total = sum(c["intento"] for c in outbound)               # tiempo total al telefono
    timbrando = sum(c["intento"] for c in buckets["no_contesta"] + buckets["ocupado"])  # repique sin respuesta
    total = len(outbound)
    contest = len(buckets["contestada"])
    n_real = len(reales)
    horas = defaultdict(int)
    horas_real = defaultdict(int)
    for c in outbound:
        horas[c["dt"].hour] += 1
    for c in reales:
        horas_real[c["dt"].hour] += 1
    primeras = sorted(c["dt"] for c in outbound)

    return {
        "slug": slug, "nombre": NOMBRE.get(slug, slug.upper()),
        "min_talk": min_talk,
        "total": total,
        "contestada": contest,
        "real": n_real,
        "buzon": len(buzon),
        "no_contesta": len(buckets["no_contesta"]),
        "ocupado": len(buckets["ocupado"]),
        "fallida": len(buckets["fallida"]),
        "otras": len(buckets["otras"]),
        "talk_seg": talk,
        "talk_real_seg": talk_real,
        "intento_seg": intento_total,
        "timbrando_seg": timbrando,
        "avg_seg": round(talk / contest) if contest else 0,
        "avg_real": round(talk_real / n_real) if n_real else 0,
        "pct_contest": round(100 * contest / total) if total else 0,
        "pct_real": round(100 * n_real / total) if total else 0,
        "primera": primeras[0] if primeras else None,
        "ultima": primeras[-1] if primeras else None,
        "horas": dict(sorted(horas.items())),
        "horas_real": dict(sorted(horas_real.items())),
    }


def build_report(rows: list[dict], day: date) -> str:
    L: list[str] = []
    L.append("=" * 64)
    L.append(f" REPORTE DE LLAMADAS - {day.isoformat()} (hora Chile)")
    L.append(f" Generado: {datetime.now(CHILE).strftime('%Y-%m-%d %H:%M')} - EN VIVO desde GHL")
    L.append("=" * 64)
    for r in rows:
        L.append(f"\n# {r['nombre']}")
        if r["total"] == 0:
            L.append("   Sin llamadas registradas este dia.")
            continue
        vent = "-"
        if r["primera"] and r["ultima"]:
            vent = f"{r['primera'].strftime('%H:%M')} -> {r['ultima'].strftime('%H:%M')}"
        L.append(f"   Total llamadas (salientes) ... {r['total']}")
        L.append(f"   [OK]  Contestadas (completed)  {r['contestada']}  ({r['pct_contest']}%)")
        L.append(f"   [>>]  CONVERSACIONES REALES .. {r['real']}  ({r['pct_real']}%)  >= {r['min_talk']}s")
        L.append(f"   [bz]  Buzon/corte (< {r['min_talk']}s) .... {r['buzon']}")
        L.append(f"   [X]   No contesta ........... {r['no_contesta']}")
        L.append(f"   [--]  Ocupado ............... {r['ocupado']}")
        L.append(f"   [!]   Fallida/cancelada ..... {r['fallida']}")
        if r["otras"]:
            L.append(f"   [.]   Otras (repique/en curso) {r['otras']}")
        L.append(f"   Min. CONVERSACION REAL ....... {fmt_min(r['talk_real_seg'])}  (prom {r['avg_real']}s/real)")
        L.append(f"   Min. brutos (todo completed) . {fmt_min(r['talk_seg'])}  (prom {r['avg_seg']}s, incl. buzon)")
        L.append(f"   Tiempo TOTAL al telefono ..... {fmt_min(r['intento_seg'])}  (repique + conversacion, todas)")
        L.append(f"   Tiempo TIMBRANDO sin respuesta {fmt_min(r['timbrando_seg'])}  (no contesta + ocupado)")
        L.append(f"   Ventana de trabajo .......... {vent}")
        hd = "  ".join(f"{h:02d}h:{n}({r['horas_real'].get(h, 0)})" for h, n in r["horas"].items())
        L.append(f"   Por hora: total(reales) ..... {hd}")

    L.append("\n" + "-" * 64)
    L.append(" COMPARATIVO")
    L.append("-" * 64)
    L.append(f" {'Metrica':<24}" + "".join(f"{r['nombre']:<18}" for r in rows))
    def line(label, key, fmt=str):
        L.append(f" {label:<24}" + "".join(f"{fmt(r[key]):<18}" for r in rows))
    line("Total llamadas", "total")
    line("Contestadas (completed)", "contestada")
    line("Conversaciones reales", "real")
    line("% conversacion real", "pct_real", lambda v: f"{v}%")
    line("Buzon/corte", "buzon")
    line("Min. conversacion real", "talk_real_seg", fmt_min)
    line("Tiempo total telefono", "intento_seg", fmt_min)
    line("Timbrando s/respuesta", "timbrando_seg", fmt_min)
    umbral = rows[0]["min_talk"] if rows else 20
    L.append(f"\nNota: 'conversacion real' = completed con duracion >= {umbral}s (excluye buzon/contestador).")
    L.append("'Contestadas (completed)' incluye buzon de pocos segundos; por eso se separa.")
    L.append("'Tiempo total al telefono' y 'timbrando' = dateUpdated - dateAdded de cada llamada.")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD (hora Chile). Default hoy.")
    ap.add_argument("--clients", default="bambutech,gbs")
    ap.add_argument("--min-talk", type=int, default=20,
                    help="Segundos minimos para contar como CONVERSACION REAL (excluye buzon). Default 20.")
    args = ap.parse_args()
    day = date.fromisoformat(args.date) if args.date else datetime.now(CHILE).date()
    slugs = [s.strip() for s in args.clients.split(",") if s.strip()]
    rows = [report_client(s, day, min_talk=args.min_talk) for s in slugs]
    text = build_report(rows, day)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(text)
    out_path = f"reporte_llamadas_{day.isoformat()}.txt"
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(f"\n[archivo guardado: {out_path}]")


if __name__ == "__main__":
    main()
