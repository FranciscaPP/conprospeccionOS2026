from __future__ import annotations

"""Bot de Telegram INTERACTIVO: responde preguntas sobre la SDR en vivo.

Escucha mensajes (long-polling) y contesta con datos reales de GHL.
Reusa el mismo bot que los updates horarios (TELEGRAM_SDR_TOKEN).

Preguntas que entiende (lenguaje natural, por palabras clave):
  - "hoy" / "como va"            -> resumen del dia (llamadas, ritmo, bloques)
  - "ayer"                       -> resumen de ayer
  - "comparativo" / "ayer vs hoy"-> tabla ayer vs hoy por cliente
  - "no contesta"               -> no contestadas por cliente
  - "info adicional" / "etapa" / "coordinando" -> movimientos + antiguedad en etapa
  - "minutos" / "efectivos" / "tiempo real" -> minutos conversacion + tiempo real al telefono
  - "contactos"                 -> contactos nuevos hoy (tuyos vs sin etiqueta)
  - "ayuda"                     -> menu

Uso: python report_sdr_bot.py   (queda escuchando; Ctrl+C para parar)
"""

import json
import os
import sys
import time as _time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date, time as dtime, timedelta

import httpx

from config import get_optional_env
from report_calls_live import GHLClient, token_for, fetch_calls, classify, LOCATION, NOMBRE, CHILE

CLIENTS = ["bambutech", "gbs"]
API = "https://api.telegram.org/bot{token}/{method}"

# Usuarios GHL que hacen llamadas -> nombre para el reporte
USER_NAMES = {
    "rTuQbq9oiZ5EFrTzzbcQ": "Francisca",
    "VtRhXhRCd8e7CMSKHbTq": "Norma",   # BambuTech
    "oD4JP7w42qu7HirNnXEx": "Nora",    # GBS (hace todo GBS)
}


def user_label(uid: str | None) -> str:
    if not uid:
        return "sin usuario"
    return USER_NAMES.get(uid, f"otro ({uid[:6]}…)")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return s.strip()


def fmt_min(sec: float) -> str:
    sec = int(sec); m, s = divmod(sec, 60); h, m = divmod(m, 60)
    return (f"{h}h " if h else "") + f"{m}m {s:02d}s"


# ---------- datos (con cache en disco + paralelo) ----------
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sdr_cache")
TODAY_TTL = 600  # segundos que vale el cache del dia en curso


def _cache_path(day: date) -> str:
    return os.path.join(CACHE_DIR, f"day_{day.isoformat()}.json")


def _fast_fetch_calls(ghl: GHLClient, location_id: str, ws: datetime, we: datetime) -> list[dict]:
    """Como fetch_calls pero baja los mensajes de las conversaciones EN PARALELO."""
    from report_calls_live import to_chile, call_status, call_duration, fetch_messages
    ws_ms = int(ws.timestamp() * 1000)
    conv_ids = []
    sa_date = sa_id = None
    for _ in range(60):
        payload = ghl.search_conversations(location_id, limit=100, start_after_date=sa_date, start_after_id=sa_id)
        convs = payload.get("conversations") or []
        if not convs:
            break
        stop = False
        for conv in convs:
            last_ms = conv.get("lastMessageDate")
            if isinstance(last_ms, (int, float)) and last_ms < ws_ms:
                stop = True
                break
            if conv.get("lastMessageType") == "TYPE_CALL" or conv.get("type") == "TYPE_PHONE":
                conv_ids.append((conv["id"], conv.get("contactId")))
        last = convs[-1]
        sa_date = last.get("lastMessageDate"); sa_id = last.get("id")
        if stop or len(convs) < 100 or not sa_date:
            break

    calls: list[dict] = []
    def grab(item):
        cid, contact_id = item
        out = []
        for m in fetch_messages(ghl, cid):
            if m.get("messageType") != "TYPE_CALL":
                continue
            dt = to_chile(m.get("dateAdded"))
            if dt is None or not (ws <= dt < we):
                continue
            added = to_chile(m.get("dateAdded")); updated = to_chile(m.get("dateUpdated"))
            dur = call_duration(m)
            intento = max(0, int(round((updated - added).total_seconds()))) if added and updated else 0
            intento = min(intento, (dur + 90) if dur > 0 else 60)   # tope: dateUpdated a veces se actualiza horas despues
            out.append({"id": m.get("id"), "dt": dt, "status": call_status(m), "dur": dur,
                        "intento": intento, "direction": m.get("direction"), "user": m.get("userId"),
                        "contact_id": m.get("contactId") or contact_id})
        return out
    with ThreadPoolExecutor(max_workers=8) as ex:
        for res in ex.map(grab, conv_ids):
            calls.extend(res)
    return calls


def _one_client(slug: str, ws: datetime, we: datetime) -> tuple[str, dict]:
    ghl = GHLClient(token_for(slug))
    cs = [c for c in _fast_fetch_calls(ghl, LOCATION[slug], ws, we) if (c["direction"] or "outbound") == "outbound"]
    ok = no = busy = 0; talk = 0; phone = 0
    by_user: dict[str, dict] = {}
    for c in cs:
        k = classify(c["status"], c["dur"])
        if k == "contestada": ok += 1; talk += c["dur"]
        elif k == "no_contesta": no += 1
        elif k == "ocupado": busy += 1
        phone += c["intento"]
        u = by_user.setdefault(c.get("user") or "", {"total": 0, "ok": 0, "no": 0, "talk": 0, "phone": 0})
        u["total"] += 1
        if k == "contestada": u["ok"] += 1; u["talk"] += c["dur"]
        elif k == "no_contesta": u["no"] += 1
        u["phone"] += c["intento"]
    return slug, {"total": len(cs), "ok": ok, "no": no, "busy": busy, "talk": talk, "phone": phone,
                  "by_user": by_user}


def day_stats(day: date) -> dict:
    """Por cliente: total/contestadas/no/ocupado/talk/phone. Cachea dias cerrados; hoy con TTL."""
    today = datetime.now(CHILE).date()
    path = _cache_path(day)
    if os.path.exists(path):
        try:
            obj = json.load(open(path, encoding="utf-8"))
            fresh = day != today or (_time.time() - obj.get("_ts", 0) < TODAY_TTL)
            if fresh:
                return obj["data"]
        except Exception:
            pass
    ws = datetime.combine(day, dtime.min, tzinfo=CHILE)
    we = ws + timedelta(days=1)
    out = {}
    with ThreadPoolExecutor(max_workers=len(CLIENTS)) as ex:
        for slug, data in ex.map(lambda s: _one_client(s, ws, we), CLIENTS):
            out[slug] = data
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        json.dump({"_ts": _time.time(), "data": out}, open(path, "w", encoding="utf-8"))
    except Exception:
        pass
    return out


def txt_hoy(day: date, label: str) -> str:
    st = day_stats(day)
    tot = sum(st[s]["total"] for s in CLIENTS)
    L = [f"*{label}* ({day.strftime('%d-%b')})", f"Total: {tot}"]
    for s in CLIENTS:
        d = st[s]
        L.append(f"• {NOMBRE[s]}: {d['total']} llam · {d['ok']} contestadas · {d['no']} no contesta")
    return "\n".join(L)


def txt_comparativo() -> str:
    hoy = datetime.now(CHILE).date()
    ayer = hoy - timedelta(days=1)
    a = day_stats(ayer); h = day_stats(hoy)
    L = [f"*Comparativo {ayer.strftime('%d-%b')} vs {hoy.strftime('%d-%b')}*"]
    for s in CLIENTS:
        L.append(f"\n{NOMBRE[s]}")
        L.append(f"  Llamadas:   {a[s]['total']} → {h[s]['total']}")
        L.append(f"  Contestadas:{a[s]['ok']} → {h[s]['ok']}")
        L.append(f"  No contesta:{a[s]['no']} → {h[s]['no']}")
        L.append(f"  Min conv:   {fmt_min(a[s]['talk'])} → {fmt_min(h[s]['talk'])}")
    ta = sum(a[s]['total'] for s in CLIENTS); th = sum(h[s]['total'] for s in CLIENTS)
    L.append(f"\nTOTAL: {ta} → {th}  ({'+' if th>=ta else ''}{th-ta})")
    return "\n".join(L)


def txt_no_contesta(day: date) -> str:
    st = day_stats(day)
    L = [f"*No contesta* ({day.strftime('%d-%b')})"]
    for s in CLIENTS:
        d = st[s]
        pct = round(100 * d["no"] / d["total"]) if d["total"] else 0
        L.append(f"• {NOMBRE[s]}: {d['no']} de {d['total']} ({pct}%) · ocupado {d['busy']}")
    return "\n".join(L)


def txt_minutos(day: date) -> str:
    st = day_stats(day)
    L = [f"*Minutos / tiempo real* ({day.strftime('%d-%b')})"]
    for s in CLIENTS:
        d = st[s]
        ring = d["phone"] - d["talk"]
        L.append(f"• {NOMBRE[s]}:")
        L.append(f"    conversación real: {fmt_min(d['talk'])}")
        L.append(f"    tiempo al teléfono (con repique): {fmt_min(d['phone'])}")
        L.append(f"    timbrando sin respuesta: {fmt_min(ring)}")
    return "\n".join(L)


def txt_usuarios(day: date) -> str:
    st = day_stats(day)
    L = [f"*Llamadas por usuario* ({day.strftime('%d-%b')})"]
    for s in CLIENTS:
        bu = st[s].get("by_user") or {}
        if not bu:
            continue
        L.append(f"\n{NOMBRE[s]} (total {st[s]['total']}):")
        for uid, d in sorted(bu.items(), key=lambda x: -x[1]["total"]):
            L.append(f"  • {user_label(uid)}: {d['total']} llam · {d['ok']} contest · {d['no']} no cont · {fmt_min(d['talk'])} conv")
    L.append("\n_Si aparece 'otro (…)', pásame el nombre de ese ID y lo agrego._")
    return "\n".join(L)


def txt_etapas() -> str:
    from report_stages_live import stage_names, all_open_opps, norm as snorm, parse_dt
    now = datetime.now(CHILE)
    L = ["*Etapas activas (en vivo)*"]
    targets = {"informacion adicional": "Info Adicional", "coordinando reunion": "Coordinando Reunión"}
    for s in CLIENTS:
        ghl = GHLClient(token_for(s))
        names = stage_names(ghl, LOCATION[s])
        cnt = {v: 0 for v in targets.values()}; viejos = []
        for o in all_open_opps(ghl, LOCATION[s]):
            n = snorm(names.get(o.get("pipelineStageId"), ""))
            if n in targets:
                cnt[targets[n]] += 1
                ch = parse_dt(o.get("lastStageChangeAt"))
                dias = (now - ch.astimezone(CHILE)).days if ch else 0
                if n == "coordinando reunion" and dias >= 30:
                    viejos.append((o.get("name") or "?", dias))
        L.append(f"\n{NOMBRE[s]}: " + " · ".join(f"{k} {v}" for k, v in cnt.items()))
        for nm, d in sorted(viejos, key=lambda x: -x[1])[:5]:
            L.append(f"    ⚠ {str(nm)[:32]} {d}d en coordinando")
    return "\n".join(L)


def txt_ayuda() -> str:
    return ("*Preguntas que puedo responder:*\n"
            "• `hoy` / `como va` — resumen del día\n"
            "• `ayer` — resumen de ayer\n"
            "• `comparativo` — ayer vs hoy por cliente\n"
            "• `no contesta` — no contestadas por cliente\n"
            "• `minutos` — conversación real + tiempo al teléfono (con repique)\n"
            "• `etapas` — info adicional / coordinando + deals viejos\n"
            "• `usuarios` / `quién` — llamadas por persona (Norma, Francisca…)\n"
            "Agrega `ayer` a cualquiera para el día anterior.")


# ---------- routing ----------
def answer(text: str) -> str:
    t = norm(text)
    hoy = datetime.now(CHILE).date()
    day = hoy - timedelta(days=1) if "ayer" in t else hoy
    label = "Resumen ayer" if day != hoy else "Resumen hoy"
    if any(k in t for k in ("comparativ", "vs", "compara")):
        return txt_comparativo()
    if any(k in t for k in ("minuto", "efectiv", "tiempo real", "segundo", "repique")):
        return txt_minutos(day)
    if "no contest" in t or "no cont" in t:
        return txt_no_contesta(day)
    if any(k in t for k in ("usuario", "quien", "cada uno", "por persona", "norma", "francisca", "ejecutiv")):
        return txt_usuarios(day)
    if any(k in t for k in ("etapa", "info adicional", "informacion adicional", "coordinando", "reunion agendada")):
        return txt_etapas()
    if any(k in t for k in ("hoy", "como va", "resumen", "va la", "llamada", "ayer")):
        return txt_hoy(day, label)
    if any(k in t for k in ("ayuda", "help", "menu", "start", "hola")):
        return txt_ayuda()
    return "No te entendí. Escribe `ayuda` para ver qué puedo responder."


# ---------- registro de chats (para descubrir chat_ids, ej. Nora) ----------
_CHATS_FILE = os.path.join(os.path.dirname(__file__), "sdr_cache", "known_chats.json")


def register_chat(chat: dict, text: str) -> None:
    """Guarda/actualiza quien le escribe al bot en known_chats.json (best-effort)."""
    try:
        cid = str(chat.get("id"))
        if not cid:
            return
        os.makedirs(os.path.dirname(_CHATS_FILE), exist_ok=True)
        data = {}
        if os.path.exists(_CHATS_FILE):
            with open(_CHATS_FILE, encoding="utf-8") as fh:
                data = json.load(fh)
        nombre = chat.get("title") or " ".join(
            x for x in [chat.get("first_name"), chat.get("last_name")] if x
        ) or chat.get("username") or ""
        data[cid] = {
            "chat_id": chat.get("id"),
            "nombre": nombre,
            "type": chat.get("type"),
            "ultimo_texto": text[:60],
            "visto": datetime.now(CHILE).isoformat(timespec="seconds"),
        }
        with open(_CHATS_FILE, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
    except Exception as e:
        print("register_chat err:", e)


# ---------- telegram loop ----------
def send(token: str, chat_id, text: str) -> None:
    """Envia a Telegram. Si Markdown falla (400) reintenta en texto plano. Nunca lanza."""
    url = API.format(token=token, method="sendMessage")
    for parse in ("Markdown", None):
        payload = {"chat_id": chat_id, "text": text}
        if parse:
            payload["parse_mode"] = parse
        try:
            r = httpx.post(url, json=payload, timeout=30)
            if r.status_code == 200:
                return
            print(f"send {r.status_code}: {r.text[:120]}")
        except Exception as e:
            print("send err:", e)
            return
    # si Markdown dio 400, el loop ya reintento sin parse_mode


def main() -> None:
    token = get_optional_env("TELEGRAM_SDR_TOKEN")
    if not token:
        print("Falta TELEGRAM_SDR_TOKEN"); return
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("Bot escuchando... (Ctrl+C para parar)")
    offset = None
    while True:
        try:
            r = httpx.get(API.format(token=token, method="getUpdates"),
                          params={"timeout": 50, "offset": offset}, timeout=60)
            data = r.json()
        except Exception as e:
            print("poll err:", e); _time.sleep(3); continue
        for u in data.get("result", []):
            try:
                offset = u["update_id"] + 1
                msg = u.get("message") or {}
                chat = msg.get("chat") or {}
                text = msg.get("text") or ""
                if not chat.get("id") or not text:
                    continue
                register_chat(chat, text)
                print(f"pregunta de chat_id={chat.get('id')}: {text!r}", flush=True)
                send(token, chat["id"], "⏳ consultando…")
                try:
                    reply = answer(text)
                except Exception as e:
                    reply = f"No pude consultar ahora ({type(e).__name__}). Reintenta en un momento."
                    print("answer err:", repr(e), flush=True)
                send(token, chat["id"], reply)
                print("respondido", flush=True)
            except Exception as e:
                # nada puede matar el loop
                print("loop-item err:", repr(e), flush=True)
                continue


if __name__ == "__main__":
    main()
