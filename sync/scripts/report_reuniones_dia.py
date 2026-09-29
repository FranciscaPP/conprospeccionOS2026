from __future__ import annotations

"""Reporte de reuniones por cliente -> Telegram (10:00 y 21:00 hora Chile).

Fuente principal = la plataforma (Supabase: vw_reuniones_semana + seguimiento_reuniones),
con las MISMAS reglas de estado que el panel Seguimiento (dashboard/meeting_shared.py).
Para HOY ademas cruza EN VIVO los calendarios GHL: agrega citas agendadas despues del
ultimo sync y marca las que se cancelaron en GHL.

Secciones:
  1. Reuniones de hoy por cliente (hora Chile, nombre, cargo, empresa, industria)
  2. Resumen por cliente: semana / mes / historico -> total, validas, no validas,
     reagendar-reagendadas, canceladas, futuras, sin actualizar CP
  3. Reuniones que ya pasaron y NO tienen validacion CP (para actualizar)

Uso:
  python report_reuniones_dia.py              # envia a Telegram
  python report_reuniones_dia.py --dry-run    # solo imprime
  python report_reuniones_dia.py --date 2026-09-25

Lo disparan las tareas de Windows 'Reuniones_Dia_Telegram' (10:00) y
'Reuniones_Cierre_Telegram' (21:00).
"""

import argparse
import sys
import unicodedata
from datetime import datetime, date, time, timedelta

from config import get_optional_env
from report_calls_live import GHLClient, CHILE, to_chile
from report_stages_live import norm
from supabase_rest import SupabaseRestClient
import httpx
from zoneinfo import ZoneInfo

PERU = ZoneInfo("America/Lima")


# Bot propio de reuniones (separado de @equipo_alicia_bot, que es el de medicion SDR).
# TELEGRAM_REUNIONES_TOKEN en .env.local. Destinatarios: Francisca (TELEGRAM_REUNIONES_CHAT_ID o
# TELEGRAM_SDR_CHAT_ID) + Nora (TELEGRAM_REUNIONES_CHAT_ID_NORA). En Telegram el id de un chat
# privado es el id de la persona, igual para cualquier bot, pero cada una debe darle /start al bot.
def _token() -> str:
    token = get_optional_env("TELEGRAM_REUNIONES_TOKEN")
    if not token:
        raise RuntimeError("Falta TELEGRAM_REUNIONES_TOKEN en .env.local")
    return token


def destinatarios() -> list[tuple[str, str]]:
    out = [("Francisca", get_optional_env("TELEGRAM_REUNIONES_CHAT_ID") or get_optional_env("TELEGRAM_SDR_CHAT_ID"))]
    out.append(("Nora", get_optional_env("TELEGRAM_REUNIONES_CHAT_ID_NORA")))
    return [(n, c) for n, c in out if c]


def send_telegram(text: str, chat: str) -> None:
    r = httpx.post(f"https://api.telegram.org/bot{_token()}/sendMessage",
                   json={"chat_id": chat, "text": text, "parse_mode": "Markdown"}, timeout=30)
    r.raise_for_status()


def send_telegram_photo(png: bytes, caption: str, chat: str) -> None:
    r = httpx.post(f"https://api.telegram.org/bot{_token()}/sendPhoto",
                   data={"chat_id": chat, "caption": caption},
                   files={"photo": ("resumen.png", png, "image/png")}, timeout=60)
    r.raise_for_status()

# Clientes activos (orden del mensaje). Balia aun no tiene reuniones/GHL en la plataforma.
CLIENTES = {
    "bambutech": "BambuTech",
    "gbs": "GBS Logistics",
    "balia": "Balia",
}
GHL = {  # slug -> (env token, env location) para el cruce en vivo de HOY
    "bambutech": ("GHL_TOKEN_BAMBUTECH", "GHL_LOCATION_BAMBUTECH"),
    "gbs": ("GHL_TOKEN_GBS_LOGISTICS", "GHL_LOCATION_GBS"),
}
MAX_LISTA = 20


# ----------------------------------------------------------------- utilidades
def _txt(v) -> str:
    s = str(v or "").strip()
    return "" if s.lower() in ("none", "null", "nan") else s


def _fix(v) -> str:
    """Limpia texto para Telegram Markdown y arregla doble encoding ('MÃ©xico')."""
    if isinstance(v, list):
        v = ", ".join(str(x) for x in v if x)
    s = _txt(v)
    if "Ã" in s:
        try:
            s = s.encode("latin-1").decode("utf-8")
        except UnicodeError:
            pass
    s = s.replace("*", "").replace("_", " ").replace("`", "").replace("[", "(").replace("]", ")").strip()
    return s or "—"


def _nombre(v) -> str:
    s = _fix(v)
    return s.title() if s != "—" and (s.islower() or s.isupper()) else s


def _plain(v) -> str:
    v = unicodedata.normalize("NFD", _txt(v).lower())
    return "".join(ch for ch in v if unicodedata.category(ch) != "Mn")


# ------------------------------------------- estado (mismas reglas del panel)
def _status_manual(v) -> str:
    v = _plain(v).replace("ã³", "o").replace("ãº", "u").replace("ã©", "e")
    if "cancel" in v:
        return "cancelada"
    if "reagendada" in v:
        return "reagendada"
    if "reagend" in v:
        return "reagendar"
    if "realizada" in v:
        return "realizada"
    return ""


def _cp(seg: dict, row: dict) -> str:
    v = _plain(seg.get("val_estado_cp") or row.get("estado_validacion"))
    if v in ("valida", "reunion_valida"):
        return "valida"
    if v in ("no_valida", "reunion_no_valida"):
        return "no_valida"
    if v in ("no_necesaria", "no necesaria", "cancelacion"):
        return "no_necesaria"
    if "reagend" in v:
        return "reagendar"
    return ""


def _final(seg: dict) -> str:
    v = _plain(seg.get("val_estado_final"))
    if v in ("valida", "reunion_valida"):
        return "valida"
    if v in ("no_valida", "reunion_no_valida"):
        return "no_valida"
    if v in ("cancelacion", "cancelada"):
        return "cancelada"
    if "reagend" in v:
        return "reagendar"
    return ""


def clasificar(r: dict, now: datetime) -> str:
    """Un solo balde por reunion: valida / no_valida / reagendar / cancelada / futura / sin_cp."""
    fin = r["final"]
    if fin:
        return fin
    st = r["status"]
    if st == "cancelada":
        return "cancelada"
    if st in ("reagendar", "reagendada"):
        return "reagendar"
    cp = r["cp"]
    if cp in ("valida", "no_valida", "reagendar"):
        return cp
    if cp == "no_necesaria":
        return "cancelada"
    if r["inicio"] > now:
        return "futura"
    return "sin_cp"


# ------------------------------------------------------------------- datos
def cargar(now: datetime) -> list[dict]:
    url, key = get_optional_env("SUPABASE_URL"), get_optional_env("SUPABASE_SECRET_KEY")
    if not url or not key:
        raise RuntimeError("Falta SUPABASE_URL o SUPABASE_SECRET_KEY en .env.local")
    sb = SupabaseRestClient(url, key)
    slugs = ",".join(CLIENTES)
    rows = sb.select_all("vw_reuniones_semana",
                         "id,cliente_slug,ghl_contact_id,fecha,hora,contacto,cargo,empresa,industria,"
                         "estado_reunion,estado_validacion",
                         cliente_slug=f"in.({slugs})")
    seg = {int(s["reunion_id"]): s for s in sb.select_all(
        "seguimiento_reuniones", "reunion_id,status_reunion,val_estado_cp,val_estado_final",
        cliente_slug=f"in.({slugs})") if s.get("reunion_id")}
    out = []
    for row in rows:
        try:
            d = date.fromisoformat(str(row.get("fecha"))[:10])
        except ValueError:
            continue
        hh = _txt(row.get("hora")) or "00:00"
        try:
            t = time(int(hh.split(":")[0]), int(hh.split(":")[1]))
        except (ValueError, IndexError):
            t = time(0, 0)
        s = seg.get(int(row["id"]), {})
        r = {
            "id": row["id"],
            "slug": _txt(row.get("cliente_slug")).lower(),
            "contact_id": _txt(row.get("ghl_contact_id")),
            "inicio": datetime.combine(d, t, tzinfo=CHILE),
            "nombre": _nombre(row.get("contacto")),
            "cargo": _fix(row.get("cargo")),
            "empresa": _fix(row.get("empresa")),
            "industria": _fix(row.get("industria")),
            "status": _status_manual(s.get("status_reunion")) or _status_manual(row.get("estado_reunion")),
            "cp": _cp(s, row),
            "final": _final(s),
            "nueva": False,
        }
        r["balde"] = clasificar(r, now)
        out.append(r)
    return out


def _field_ids(ghl: GHLClient, location_id: str) -> tuple[str | None, str | None]:
    """IDs de 'Cargo' e 'Industria' por NOMBRE (difieren por subcuenta)."""
    try:
        fields = ghl.list_custom_fields(location_id).get("customFields", []) or []
    except Exception:
        return None, None

    def pick(exact: tuple[str, ...], contains: str) -> str | None:
        for f in fields:
            if norm(f.get("name", "")) in exact:
                return f.get("id")
        for f in fields:
            n = norm(f.get("name", ""))
            if contains in n and not any(x in n for x in ("macro", "referido", "publica")):
                return f.get("id")
        return None

    return pick(("cargo",), "cargo"), pick(("industria", "industry", "rubro"), "industri")


def ghl_hoy(slug: str, day: date) -> list[dict]:
    """Citas GHL cuyo inicio es HOY (incluye canceladas, con su estado)."""
    tok_env, loc_env = GHL[slug]
    token, location = get_optional_env(tok_env), get_optional_env(loc_env)
    if not token or not location:
        return []
    ghl = GHLClient(token)
    d0 = datetime.combine(day, time.min, tzinfo=CHILE)
    st, en = int(d0.timestamp() * 1000), int((d0 + timedelta(days=1)).timestamp() * 1000)
    try:
        cals = ghl.list_calendars(location).get("calendars", []) or []
    except Exception as e:
        print(f"[{slug}] GHL sin calendarios: {type(e).__name__}: {e}")
        return []
    fids = None
    seen, out = set(), []
    for cal in cals:
        try:
            evs = ghl.list_calendar_events(location, str(st), str(en),
                                           calendar_id=cal.get("id")).get("events", []) or []
        except Exception:
            continue
        for e in evs:
            ini = to_chile(e.get("startTime"))
            if e.get("id") in seen or not ini or ini.date() != day:
                continue
            seen.add(e.get("id"))
            out.append({"contact_id": _txt(e.get("contactId")), "inicio": ini,
                        "estado": _plain(e.get("appointmentStatus")), "title": e.get("title"),
                        "_ghl": ghl, "_loc": location})
    return out


def _detalle_ghl(ev: dict, cache: dict) -> dict:
    ghl, loc = ev["_ghl"], ev["_loc"]
    if loc not in cache:
        cache[loc] = _field_ids(ghl, loc)
    cargo_fid, ind_fid = cache[loc]
    c = {}
    if ev["contact_id"]:
        try:
            c = (ghl.get_contact(ev["contact_id"]) or {}).get("contact", {}) or {}
        except Exception:
            c = {}
    cf = {f.get("id"): f.get("value") for f in c.get("customFields", []) or []}
    nombre = " ".join(x for x in [c.get("firstName"), c.get("lastName")] if x) or ev.get("title")
    return {"nombre": _nombre(nombre), "cargo": _fix(cf.get(cargo_fid)),
            "empresa": _fix(c.get("companyName")), "industria": _fix(cf.get(ind_fid))}


def hoy_con_ghl(rows: list[dict], day: date, now: datetime) -> dict[str, list[dict]]:
    hoy = {slug: [r for r in rows if r["slug"] == slug and r["inicio"].date() == day] for slug in CLIENTES}
    cache: dict = {}
    for slug in GHL:
        evs = ghl_hoy(slug, day)
        por_contacto = {r["contact_id"]: r for r in hoy[slug] if r["contact_id"]}
        for ev in evs:
            r = por_contacto.get(ev["contact_id"])
            cancel = ev["estado"] in ("cancelled", "canceled", "noshow", "invalid")
            if r:
                if cancel and r["balde"] in ("futura", "sin_cp"):
                    r["balde"] = "cancelada"          # cancelada en GHL despues del sync
                continue
            if cancel:
                continue
            nueva = {"slug": slug, "contact_id": ev["contact_id"], "inicio": ev["inicio"], "nueva": True,
                     "status": "", "cp": "", "final": "", **_detalle_ghl(ev, cache)}
            nueva["balde"] = clasificar(nueva, now)
            hoy[slug].append(nueva)
    for slug in hoy:
        hoy[slug].sort(key=lambda r: r["inicio"])
    return hoy


# ----------------------------------------------------------------- mensaje
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
ETIQUETA_HOY = {
    "valida": "✅ válida", "no_valida": "❌ no válida", "reagendar": "🔁 reagendar",
    "cancelada": "🚫 cancelada", "futura": "", "sin_cp": "⚠️ sin validar CP",
}
FILAS = [("Total", None), ("Válidas", "valida"), ("No válidas", "no_valida"),
         ("Reagendar / reagendadas", "reagendar"), ("Canceladas", "cancelada"),
         ("Futuras", "futura"), ("Sin actualizar CP", "sin_cp")]
ICONO = {"bambutech": "🟢", "gbs": "🟣", "balia": "🩷"}
COLOR = {"bambutech": (46, 125, 50), "gbs": (123, 47, 160), "balia": (216, 67, 130)}
MORADO = (74, 35, 110)           # titulos
GRIS = (110, 110, 120)
LINEA = (228, 228, 234)
VALIDA_BG = (232, 245, 233)      # fila "Válidas" destacada (es lo que se paga)


def _n(rs: list[dict], b: str | None) -> int:
    return len(rs) if b is None else sum(1 for r in rs if r["balde"] == b)


def _periodos(rows: list[dict], day: date) -> tuple[date, date]:
    lun = day - timedelta(days=day.weekday())
    return lun, lun + timedelta(days=6)


def render_resumen_png(rows: list[dict], day: date) -> bytes:
    """Imagen con tablas alineadas y colores por cliente:
    1) resumen general del MES (columnas = clientes + total)  2) una tabla por cliente (Sem/Mes/Total)."""
    from io import BytesIO
    from PIL import Image, ImageDraw, ImageFont

    def f(size, bold=False):
        for name in (("segoeuib.ttf", "arialbd.ttf") if bold else ("segoeui.ttf", "arial.ttf")):
            try:
                return ImageFont.truetype(name, size)
            except Exception:
                continue
        return ImageFont.load_default()

    F_T, F_H, F_B, F_BB, F_S = f(40, True), f(30, True), f(28), f(28, True), f(24)
    W, PAD, ROW = 1000, 40, 50
    LBLW = 380                                 # ancho columna de etiquetas
    lun, dom = _periodos(rows, day)
    mes = [r for r in rows if (r["inicio"].year, r["inicio"].month) == (day.year, day.month)]
    por = {s: [r for r in rows if r["slug"] == s] for s in CLIENTES}

    n_tablas = 1 + len(CLIENTES)
    H = 130 + n_tablas * (70 + ROW * (len(FILAS) + 1) + 40) + 20
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)

    def right(x, y, txt, font, fill):
        w = d.textlength(txt, font=font)
        d.text((x - w, y), txt, font=font, fill=fill)

    def center(x, y, txt, font, fill):
        w = d.textlength(txt, font=font)
        d.text((x - w / 2, y), txt, font=font, fill=fill)

    y = PAD
    d.text((PAD, y), "Resumen de reuniones", font=F_T, fill=MORADO)
    y += 52
    d.text((PAD, y), f"{DIAS[day.weekday()].capitalize()} {day.day} de {MESES[day.month]} · "
                     f"semana {lun.day}/{lun.month}–{dom.day}/{dom.month}", font=F_S, fill=GRIS)
    y += 50

    def tabla(titulo: str, color, cols: list[tuple[str, tuple, list[dict]]]):
        nonlocal y
        # banda de titulo
        d.rounded_rectangle((PAD, y, W - PAD, y + 56), radius=12, fill=color)
        d.text((PAD + 20, y + 10), titulo, font=F_H, fill="white")
        y += 70
        colw = (W - 2 * PAD - LBLW) / len(cols)
        cx = [PAD + LBLW + colw * (i + 0.5) for i in range(len(cols))]
        for i, (lbl, ccol, _) in enumerate(cols):          # encabezados
            center(cx[i], y + 10, lbl, F_BB, ccol)
        y += ROW
        d.line((PAD, y - 4, W - PAD, y - 4), fill=color, width=3)
        for lbl, b in FILAS:
            if b == "valida":
                d.rectangle((PAD, y, W - PAD, y + ROW - 6), fill=VALIDA_BG)
            bold = b in (None, "valida")
            d.text((PAD + 14, y + 8), lbl, font=F_BB if bold else F_B,
                   fill=(27, 94, 32) if b == "valida" else (40, 40, 48))
            for i, (_, _, rs) in enumerate(cols):
                v = _n(rs, b)
                fill = (27, 94, 32) if b == "valida" else ((200, 40, 40) if b == "sin_cp" and v else
                                                           (40, 40, 48) if v else (185, 185, 195))
                center(cx[i], y + 8, str(v), F_BB if bold else F_B, fill)
            y += ROW
            d.line((PAD, y - 4, W - PAD, y - 4), fill=LINEA, width=1)
        y += 40

    # 1) general del mes: una columna por cliente + total
    cols = [(CLIENTES[s].split()[0], COLOR[s], [r for r in mes if r["slug"] == s]) for s in CLIENTES]
    cols.append(("TOTAL", MORADO, mes))
    tabla(f"GENERAL · {MESES[day.month].upper()} {day.year}", MORADO, cols)

    # 2) por cliente: Semana / Mes / Total
    for s, nombre in CLIENTES.items():
        rs = por[s]
        c = COLOR[s]
        if not rs:                                   # cliente aun sin reuniones: una linea, no tabla de ceros
            d.rounded_rectangle((PAD, y, W - PAD, y + 56), radius=12, fill=c)
            d.text((PAD + 20, y + 10), f"{nombre.upper()} · aún sin reuniones en la plataforma",
                   font=F_H, fill="white")
            y += 90
            continue
        tabla(nombre.upper(), c, [
            ("Semana", c, [r for r in rs if lun <= r["inicio"].date() <= dom]),
            ("Mes", c, [r for r in rs if (r["inicio"].year, r["inicio"].month) == (day.year, day.month)]),
            ("Total", c, rs),
        ])

    img = img.crop((0, 0, W, y))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def build_message(rows: list[dict], hoy: dict[str, list[dict]], day: date, now: datetime) -> str:
    cierre = now.hour >= 18
    L = [f"{'🌙 *Cierre de reuniones*' if cierre else '📅 *Reuniones de hoy*'} — "
         f"{DIAS[day.weekday()]} {day.day} de {MESES[day.month]}",
         "Horas 🇨🇱 Chile · 🇵🇪 Perú", ""]

    # Resumen general del mes (lo que se paga = validas)
    mes = [r for r in rows if (r["inicio"].year, r["inicio"].month) == (day.year, day.month)]
    L.append(f"💰 *VÁLIDAS {MESES[day.month].upper()}: {_n(mes, 'valida')}*  de {len(mes)} reuniones")
    L.append("   " + " · ".join(f"{ICONO[s]} {CLIENTES[s].split()[0]} {_n([r for r in mes if r['slug'] == s], 'valida')}"
                                for s in CLIENTES))
    L.append("")

    # 1. Hoy
    total_hoy = sum(len(v) for v in hoy.values())
    L.append(f"*1. HOY — {total_hoy} {'reunión' if total_hoy == 1 else 'reuniones'}*")
    for slug, nombre in CLIENTES.items():
        L.append("")                                   # espacio entre clientes
        rs = hoy.get(slug, [])
        if not rs:
            L.append(f"{ICONO[slug]} *{nombre}*: sin reuniones")
            continue
        L.append(f"{ICONO[slug]} *{nombre}* ({len(rs)})")
        for r in rs:
            L.append("")                               # espacio entre reuniones
            tag = ETIQUETA_HOY.get(r["balde"], "")
            if r["balde"] == "sin_cp" and r["inicio"] > now - timedelta(hours=1):
                tag = "⏳ en curso"
            extra = "  🆕 aún no en plataforma" if r.get("nueva") else ""
            pe = r["inicio"].astimezone(PERU)
            L.append(f"🕐 🇨🇱 *{r['inicio']:%H:%M}* · 🇵🇪 {pe:%H:%M} — {r['nombre']}{('  ' + tag) if tag else ''}{extra}")
            L.append(f"    {r['cargo']} · {r['empresa']}")
            L.append(f"    Industria: {r['industria']}")
    L.append("")

    # 2. Resumen por cliente -> va como IMAGEN (render_resumen_png)

    # 2. Pasadas sin validacion CP
    pend = sorted((r for r in rows if r["balde"] == "sin_cp" and r["inicio"] <= now - timedelta(hours=1)),
                  key=lambda r: r["inicio"], reverse=True)
    L.append(f"*2. YA PASARON Y SIN VALIDACIÓN CP — {len(pend)}*")
    if not pend:
        L.append("✅ Todo al día.")
    for slug, nombre in CLIENTES.items():
        ps = [r for r in pend if r["slug"] == slug]
        if not ps:
            continue
        L.append("")
        L.append(f"{ICONO[slug]} *{nombre}* ({len(ps)})")
        for r in ps[:MAX_LISTA]:
            dias = (now.date() - r["inicio"].date()).days
            cuando = "hoy" if dias == 0 else "ayer" if dias == 1 else f"hace {dias} días"
            L.append(f"• {r['inicio']:%d/%m %H:%M} ({cuando}) — {r['nombre']} · {r['empresa']}")
        if len(ps) > MAX_LISTA:
            L.append(f"  … y {len(ps) - MAX_LISTA} más")
    return "\n".join(L).rstrip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    now = datetime.now(CHILE)
    day = date.fromisoformat(args.date) if args.date else now.date()
    rows = cargar(now)
    hoy = hoy_con_ghl(rows, day, now)
    text = build_message(rows, hoy, day, now)
    png = render_resumen_png(rows, day)
    print(text)
    if args.dry_run:
        with open("resumen_reuniones.png", "wb") as fh:
            fh.write(png)
        print("\n[imagen guardada: resumen_reuniones.png]")
        return
    for quien, chat in destinatarios():
        try:
            send_telegram(text, chat)
            send_telegram_photo(png, "📊 Resumen por cliente · semana / mes / total", chat)
            print(f"\n[enviado a Telegram · {quien}]")
        except httpx.HTTPStatusError as e:   # p.ej. 403 si esa persona aun no le dio /start al bot
            print(f"\n[NO enviado a {quien}: {e.response.status_code} {e.response.text[:120]}]")


if __name__ == "__main__":
    main()
