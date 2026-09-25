from __future__ import annotations

"""Reporte de ACTIVIDAD REAL de la SDR por dia (EN VIVO desde GHL).

Va mas alla de las llamadas. Por cliente y dia entrega:
  - Llamadas: total / contestadas / no contesta
  - WhatsApp: enviados MANUAL (app/bulk) vs AUTOMATICO (workflow) vs RESPUESTAS (inbound)
  - Correo:   enviados MANUAL (app/bulk) vs AUTOMATICO (workflow) vs RESPUESTAS (inbound)
  - Movimientos de etapa ese dia: -> Informacion Adicional / Coordinando Reunion / Reunion Agendada
  - Contactos creados ese dia: CARGADOS POR TI (con etiqueta) vs SIN ETIQUETA (posible Apollo/ella)

OJO honesto:
  - Los correos de campana de SNOV viven en Snov, no en GHL. Los correos 'app'
    de aqui son envios por la plataforma (personalizados/plantilla) + capa IA SAM.
  - 'manual' = source app/bulk_actions ; 'auto' = source workflow.

Uso: python report_actividad.py [--date YYYY-MM-DD] [--clients bambutech,gbs]
"""

import argparse
import re
import sys
from collections import defaultdict
from datetime import datetime, date, time, timedelta

from report_calls_live import (
    GHLClient, token_for, to_chile, classify, call_status, call_duration,
    LOCATION, NOMBRE, CHILE,
)
from report_stages_live import stage_names, norm, all_open_opps, parse_dt

MANUAL_SRC = {"app", "bulk_actions"}
STAGE_INTEREST = {
    "informacion adicional": "Info Adicional",
    "coordinando reunion": "Coordinando Reunion",
    "reunion agendada": "Reunion Agendada",
}
# etiquetas de carga masiva (las pone Francisca al subir bases)
BULK_TAG_RE = re.compile(
    r"(bbdd|base|nuevos|carga|import|foco|test|enero|febrero|marzo|abril|mayo|junio|"
    r"julio|agosto|septiembre|octubre|noviembre|diciembre)", re.I)


def in_day(iso: str | None, win_start: datetime, win_end: datetime) -> bool:
    dt = to_chile(iso)
    return dt is not None and win_start <= dt < win_end


def scan_conversations(ghl: GHLClient, location_id: str, win_start: datetime, win_end: datetime) -> dict:
    """Un solo barrido: llamadas + whatsapp + correo del dia, clasificados."""
    win_start_ms = int(win_start.timestamp() * 1000)
    tally = {
        "call_total": 0, "call_ok": 0, "call_no": 0,
        "wa_manual": 0, "wa_auto": 0, "wa_reply": 0,
        "em_manual": 0, "em_auto": 0, "em_reply": 0,
        "sms_manual": 0,
    }
    sa_date = None; sa_id = None; pages = 0
    while pages < 60:
        pages += 1
        payload = ghl.search_conversations(location_id, limit=100, start_after_date=sa_date, start_after_id=sa_id)
        convs = payload.get("conversations") or []
        if not convs:
            break
        stop = False
        for conv in convs:
            last_ms = conv.get("lastMessageDate")
            if isinstance(last_ms, (int, float)) and last_ms < win_start_ms:
                stop = True
                break
            msgs = fetch_all_messages(ghl, conv["id"])
            for m in msgs:
                mt = m.get("messageType")
                if not in_day(m.get("dateAdded"), win_start, win_end):
                    continue
                direction = m.get("direction")
                src = m.get("source")
                if mt == "TYPE_CALL":
                    tally["call_total"] += 1
                    k = classify(call_status(m), call_duration(m))
                    if k == "contestada": tally["call_ok"] += 1
                    elif k == "no_contesta": tally["call_no"] += 1
                elif mt == "TYPE_WHATSAPP":
                    if direction == "inbound": tally["wa_reply"] += 1
                    elif src in MANUAL_SRC: tally["wa_manual"] += 1
                    else: tally["wa_auto"] += 1
                elif mt == "TYPE_EMAIL":
                    if direction == "inbound": tally["em_reply"] += 1
                    elif src in MANUAL_SRC: tally["em_manual"] += 1
                    else: tally["em_auto"] += 1
                elif mt == "TYPE_SMS" and direction == "outbound":
                    tally["sms_manual"] += 1
        last = convs[-1]
        sa_date = last.get("lastMessageDate"); sa_id = last.get("id")
        if stop or len(convs) < 100 or not sa_date:
            break
    return tally


def fetch_all_messages(ghl: GHLClient, conversation_id: str) -> list[dict]:
    out = []; last_id = None
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


def stage_moves(ghl: GHLClient, location_id: str, win_start: datetime, win_end: datetime) -> dict:
    names = stage_names(ghl, location_id)
    moves = defaultdict(int)
    for o in all_open_opps(ghl, location_id):
        changed = parse_dt(o.get("lastStageChangeAt"))
        if not changed:
            continue
        c = changed.astimezone(CHILE)
        if not (win_start <= c < win_end):
            continue
        n = norm(names.get(o.get("pipelineStageId"), ""))
        if n in STAGE_INTEREST:
            moves[STAGE_INTEREST[n]] += 1
    return dict(moves)


SOURCE_TAG_RE = re.compile(r"(linkedin|publicaci|responde|inbound|formulario|web|instagram|facebook|meta ads|anuncio)", re.I)


def contacts_created(ghl: GHLClient, location_id: str, win_start: datetime, win_end: datetime) -> dict:
    cargado_ti = 0        # con etiqueta de carga masiva (bbdd/nuevos/mes)
    otra_fuente = 0       # tag de origen conocido (linkedin/web/responde)
    sin_nada = 0          # sin NINGUNA etiqueta -> candidato Apollo/manual de ella
    otra_tags = defaultdict(int)
    sin_list = []
    sa = None; sid = None
    for _ in range(40):
        p = ghl.list_contacts_page(location_id, limit=100, start_after=sa, start_after_id=sid)
        cs = p.get("contacts") or []
        if not cs:
            break
        stop = False
        for c in cs:
            dt = to_chile(c.get("dateAdded"))
            if dt is None:
                continue
            if dt < win_start:
                stop = True
                break
            if dt >= win_end:
                continue
            tags = c.get("tags") or []
            if any(BULK_TAG_RE.search(t) for t in tags):
                cargado_ti += 1
            elif any(SOURCE_TAG_RE.search(t) for t in tags):
                otra_fuente += 1
                for t in tags:
                    if SOURCE_TAG_RE.search(t):
                        otra_tags[t] += 1
            elif not tags:
                sin_nada += 1
                nm = c.get("contactName") or c.get("companyName") or c.get("email") or c.get("id")
                sin_list.append((nm, c.get("phone")))
            else:
                # tiene solo tags de estado (no califica, etc.) -> lo trato como carga tuya vieja
                cargado_ti += 1
        meta = p.get("meta") or {}
        sa = meta.get("startAfter"); sid = meta.get("startAfterId")
        if stop or len(cs) < 100 or not sid:
            break
    return {"cargado_ti": cargado_ti, "otra_fuente": otra_fuente, "sin_nada": sin_nada,
            "otra_tags": dict(otra_tags), "sin_list": sin_list}


def build(slug: str, day: date) -> str:
    ghl = GHLClient(token_for(slug))
    win_start = datetime.combine(day, time.min, tzinfo=CHILE)
    win_end = win_start + timedelta(days=1)
    t = scan_conversations(ghl, LOCATION[slug], win_start, win_end)
    mv = stage_moves(ghl, LOCATION[slug], win_start, win_end)
    cc = contacts_created(ghl, LOCATION[slug], win_start, win_end)

    L = []
    L.append(f"# {NOMBRE.get(slug, slug.upper())}")
    L.append(f"  LLAMADAS ...... {t['call_total']} total | {t['call_ok']} contestadas | {t['call_no']} no contesta")
    L.append(f"  WHATSAPP ...... {t['wa_manual']} enviados MANUAL | {t['wa_auto']} automatico | {t['wa_reply']} RESPUESTAS")
    L.append(f"  CORREO ........ {t['em_manual']} enviados MANUAL | {t['em_auto']} automatico | {t['em_reply']} RESPUESTAS")
    if t["sms_manual"]:
        L.append(f"  SMS ........... {t['sms_manual']} enviados")
    mv_txt = " | ".join(f"{k}: {v}" for k, v in mv.items()) or "ninguno"
    L.append(f"  PASO A ETAPA .. {mv_txt}")
    L.append(f"  CONTACTOS NUEVOS HOY:")
    L.append(f"     - Cargados por TI (etiqueta carga) ...... {cc['cargado_ti']}")
    fuente_txt = ", ".join(f"{t}:{n}" for t, n in cc["otra_tags"].items()) or "-"
    L.append(f"     - Entrantes / otra fuente ............... {cc['otra_fuente']}  ({fuente_txt})")
    L.append(f"     - SIN NINGUNA etiqueta (Apollo/ella?) ... {cc['sin_nada']}")
    for nm, phone in cc["sin_list"][:15]:
        L.append(f"          * {str(nm)[:40]:<40} {phone or ''}")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--clients", default="bambutech,gbs")
    args = ap.parse_args()
    day = date.fromisoformat(args.date) if args.date else datetime.now(CHILE).date()
    slugs = [s.strip() for s in args.clients.split(",") if s.strip()]
    parts = [build(s, day) for s in slugs]
    header = ("=" * 66 + f"\n ACTIVIDAD REAL DE LA SDR — {day.isoformat()} (hora Chile)\n"
              + " MANUAL = lo hizo ella (source app/bulk) · automatico = workflow/IA\n" + "=" * 66)
    footer = ("\nNota: correos de campana SNOV NO estan aqui (viven en Snov). Los correos\n"
              "'automatico' son confirmaciones/flujos. 'SIN etiqueta' = contactos que\n"
              "no cargaste tu -> candidatos a que ella los agrego (Apollo/manual).")
    text = header + "\n\n" + "\n\n".join(parts) + "\n" + footer
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(text)
    out = f"reporte_actividad_{day.isoformat()}.txt"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(f"\n[archivo guardado: {out}]")


if __name__ == "__main__":
    main()
