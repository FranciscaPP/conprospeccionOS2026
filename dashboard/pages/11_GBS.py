"""Portal cliente GBS Logistics — Plataforma de Revenue Intelligence.

Estructura:
  1. Avance de meta (40 reuniones válidas en 5 meses) — live desde Supabase
  2. KPIs de validación (válidas / no válidas / reagendar / avance comercial) — live
  3. ICP del cliente
  4. Filtros (chips eliminables + restablecer)
  5. Métricas del reporte con KPIs y gráficos (recorte filtrado, demo)
  6. Hallazgos clave
  7. Recomendaciones
  8. Análisis de mercado y proyección

Sin gráficos JS (Plotly/Altair fallan en Streamlit Cloud) — todo HTML/CSS puro.
El bloque superior (1-2) lee data real de Supabase y hoy está en 0: se completa
a medida que el cliente valida reuniones en la página de Validación.
"""
import sys
import random
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

import requests
import pandas as pd
import streamlit as st
from shared.config import supabase_url, supabase_key
from shared.gbs_brand import (
    GBS_PURPLE, GBS_PINK, GBS_YELLOW, GBS_DARK, GBS_BG, GBS_BORDER,
    C_GREEN, C_RED, C_AMBER, C_SLATE,
    TOP_CARGOS, TOP_INDUSTRIAS, W_CARGO as BRAND_W_CARGO, W_IND as BRAND_W_IND,
)
from portal_auth import require_auth_client, render_client_nav, img_b64

st.set_page_config(page_title="GBS Logistics — Intelligence Insight", layout="wide", page_icon="")

if not require_auth_client("gbs"):
    st.stop()

# El módulo permanece visible; el contenido completo requiere plan premium.
# El equipo interno conserva siempre la vista operativa completa.
from shared.planes import plan_de as _plan_de
if _plan_de("gbs") != "premium" and not st.session_state.get("admin_mode"):
    render_client_nav("11_GBS", "gbs")
    st.markdown(
        f'<div style="max-width:760px;margin:72px auto;background:#fff;border:1px solid {GBS_BORDER};'
        f'border-left:6px solid {GBS_PURPLE};border-radius:14px;padding:30px 32px;'
        f'box-shadow:0 8px 24px rgba(91,33,182,.08)">'
        f'<div style="font-size:11px;font-weight:850;letter-spacing:.9px;text-transform:uppercase;'
        f'color:{GBS_PURPLE};margin-bottom:9px">Intelligence Insight</div>'
        f'<div style="font-size:22px;font-weight:850;color:{GBS_DARK};margin-bottom:9px">'
        f'Dashboard disponible para clientes premium</div>'
        f'<div style="font-size:14px;color:#475569;line-height:1.65">'
        f'GBS puede ver este módulo en su portal, pero el análisis completo de desempeño, '
        f'segmentos, ICP real, hallazgos y recomendaciones todavía no está habilitado '
        f'para su plan actual.</div>'
        f'<div style="margin-top:15px;font-size:12px;color:#64748b">'
        f'Conprospección puede activarlo cuando se actualice el plan del cliente.</div></div>',
        unsafe_allow_html=True,
    )
    st.stop()

render_client_nav("11_GBS", "gbs")

# Paleta y tokens semánticos viven en shared/gbs_brand.py (fuente única).

META_VALIDAS = 40 # reuniones válidas garantizadas
DIAS_CAMPANA = 150 # 5 meses
CAMPANA_INICIO = date(2026, 5, 1)

SUPABASE_URL = supabase_url()
SUPABASE_KEY = supabase_key()
_SB_H = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}

# ── Iconos SVG inline (sin emojis como íconos) ────────────────────────
def _svg(path, color, size=16):
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round">{path}</svg>'
    )

IC_INSIGHT = '<path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.7c.6.5 1 1.3 1 2.1h6c0-.8.4-1.6 1-2.1A7 7 0 0 0 12 2z"/>'
IC_REC = '<circle cx="12" cy="12" r="9"/><path d="m9 12 2 2 4-4"/>'
IC_UP = '<line x1="7" y1="17" x2="17" y2="7"/><polyline points="7 7 17 7 17 17"/>'
IC_RISK = '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>'
IC_GLOBE = '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"/>'
IC_MAIL = '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/>'
IC_CHAT = '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>'

# ═══════════════════════════════════════════════════════════════════════
# BLOQUE SUPERIOR — DATA REAL DE VALIDACIÓN (live Supabase, hoy en 0)
# ═══════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=60, show_spinner=False)
def cargar_validacion_gbs():
    def _norm(v):
        return str(v or "").lower()

    rows, seg = [], []
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/reuniones"
            f"?select=estado_validacion&cliente_slug=eq.gbs",
            headers=_SB_H, timeout=12)
        if r.ok:
            rows = r.json()
    except Exception:
        rows = []
    try:
        r2 = requests.get(
            f"{SUPABASE_URL}/rest/v1/gbs_seguimiento"
            f"?select=reunion_id,etapa_comercial",
            headers=_SB_H, timeout=12)
        if r2.ok:
            seg = r2.json()
    except Exception:
        seg = []

    nv = sum(1 for x in rows if _norm(x.get("estado_validacion")) in ("no_valida", "reunion_no_valida"))
    reag = sum(1 for x in rows if _norm(x.get("estado_validacion")) in ("reagendar", "reagendada"))
    # Avance oficial: solo reuniones con flag_meta_countable = true (validez final confirmada)
    _r_seg2 = None
    try:
        _r_seg2 = requests.get(
            f"{SUPABASE_URL}/rest/v1/seguimiento_reuniones"
            f"?cliente_slug=eq.gbs&flag_meta_countable=eq.true&select=reunion_id",
            headers=_SB_H, timeout=15)
    except Exception:
        pass
    val = len(_r_seg2.json()) if _r_seg2 and _r_seg2.ok else 0
    # Avance comercial: reuniones que avanzaron en pipeline
    avanzan = sum(1 for x in seg if str(x.get("etapa_comercial") or "")
                  in ("envio_propuesta", "seguimiento_propuesta", "avanzando_post"))
    return {
        "total": len(rows), "validas": val, "no_validas": nv, "reagendar": reag,
        "con_seguimiento": len(seg), "avanzan": avanzan,
    }


# ═══════════════════════════════════════════════════════════════════════
# DATASET A NIVEL DE REGISTRO (demo, estable por seed) — para el reporte
# ═══════════════════════════════════════════════════════════════════════
def _pick(rng, weighted):
    r = rng.random()
    acc = 0.0
    for val, w in weighted:
        acc += w
        if r <= acc:
            return val
    return weighted[-1][0]


# Sub-estados del embudo de respuestas positivas (mes 1)
SUBEST_LABEL = {
    "info_adicional": "Información adicional",
    "coordinando": "Coordinando reunión",
    "agendada": "Reunión agendada",
}
# Opciones de los filtros que provienen del panel "Validación de Reuniones"
TIPO_RESP_OPTS = ["Espera validación", "Reunión válida", "Reunión no válida", "Reagendar"]
ETAPA_OPTS = ["Propuesta enviada", "Seguimiento de respuesta", "Sin respuesta post propuesta",
              "Avanzando propuesta", "Cliente ganado", "Cliente perdido"]
BANT_OPTS = ["B", "A", "N", "T"]
BANT_LABEL = {"B": "Budget", "A": "Authority", "N": "Need", "T": "Time"}
# Interés del lead y motivo de rechazo (también provienen de "Validación de Reuniones")
INTERES_OPTS = ["Reunión", "Cotización", "Reunión + Cotización"]
MOTIVO_OPTS = ["Ya tienen proveedor", "Sin respuesta", "No interesado"]

# TOP_CARGOS / TOP_INDUSTRIAS provienen de shared/gbs_brand.py (fuente única):
# se reutilizan en filtros superiores, ICP y segmento de campañas para coherencia total.


@st.cache_data(show_spinner=False)
def cargar_dataset(base_n=776):
    """Datos demo de la campaña — coherentes con el mes 1 (validación de la base).

    Escenario inventado y fijo (se refresca una vez al mes):
      · 784 contactos trabajados · 148 empresas impactadas · 21 respuestas
      · 8 respuestas positivas = 6 Información adicional + 0 Coordinando reunión + 2 Agendada
      · 2 reuniones agendadas (pendientes de validación) avance de meta 0 % (válidas finales)
    """
    rng = random.Random(42)
    W_PAIS = [("Chile", .68), ("Perú", .20), ("Colombia", .12)]
    W_IND = BRAND_W_IND # pesos top-5 industrias (shared/gbs_brand.py)
    W_CARGO = BRAND_W_CARGO # pesos top-5 cargos (shared/gbs_brand.py)
    W_CANAL = [("Llamadas", .45), ("Correo electrónico", .30), ("WhatsApp", .25)]
    W_TAM = [("10–50 empleados", .45), ("50–200 empleados", .40), ("200+ empleados", .15)]
    W_PER = [("Mayo 2026", .58), ("Junio 2026", .42)]

    filas = []
    n_resp_neg = 13 # contactos que respondieron pero sin interés / fuera de perfil
    for i in range(base_n):
        respondio = i < n_resp_neg
        motivo = MOTIVO_OPTS[i % len(MOTIVO_OPTS)] if respondio else None
        # Mismo orden de picks que antes (no altera el dataset); apertura determinística.
        per = _pick(rng, W_PER); canal = _pick(rng, W_CANAL)
        pais = _pick(rng, W_PAIS); ind = _pick(rng, W_IND)
        cargo = _pick(rng, W_CARGO); tam = _pick(rng, W_TAM)
        enviado = canal == "Correo electrónico"   # la apertura solo aplica al canal correo
        abierto = enviado and (i % 9 < 4)          # ~44 % de tasa de apertura (demo)
        filas.append({
            "periodo": per, "canal": canal,
            "pais": pais, "industria": ind,
            "cargo": cargo, "tamano": tam,
            "empresa_id": (i % 148) + 1, # exactamente 148 empresas impactadas
            "respondio": respondio, "positiva": False, "reunion": False,
            "subestado": None,
            "tipo_respuesta": ("Reunión no válida" if respondio and i % 4 == 0 else None),
            "etapa": None, "bant": [],
            "interes_lead": None, "motivo_rechazo": motivo,
            "enviado": enviado, "abierto": abierto,
        })
    rng.shuffle(filas)

    # 8 respuestas positivas inventadas (6 info adicional + 2 coordinando + 0 agendada)
    POS = [
        ("Chile", "Minería y Metales", "Encargado de Importaciones", "Llamadas", "50–200 empleados", "Junio 2026", "info_adicional", ["B", "N"], "Cotización"),
        ("Chile", "Minería y Metales", "Encargado de Importaciones", "Llamadas", "200+ empleados", "Junio 2026", "info_adicional", ["B", "A", "N", "T"], "Reunión + Cotización"),
        ("Perú", "Minería y Metales", "Gerente de Operaciones", "Llamadas", "50–200 empleados", "Junio 2026", "info_adicional", ["B", "A", "N"], "Cotización"),
        ("Chile", "Retail", "Jefe COMEX", "Correo electrónico", "200+ empleados", "Mayo 2026", "info_adicional", ["A", "N"], "Reunión"),
        ("Chile", "Automotriz", "Encargado de Importaciones", "WhatsApp", "10–50 empleados", "Mayo 2026", "info_adicional", ["N", "T"], "Cotización"),
        ("Colombia", "Alimentos y Bebidas", "Supply Chain Manager", "Correo electrónico", "50–200 empleados", "Junio 2026", "info_adicional", ["B", "N"], "Reunión"),
        ("Chile", "Minería y Metales", "Encargado de Importaciones", "Llamadas", "50–200 empleados", "Junio 2026", "agendada", ["B", "N", "T"], "Reunión + Cotización"),
        ("Chile", "Retail", "Gerente de Operaciones", "Llamadas", "50–200 empleados", "Mayo 2026", "agendada", ["B", "A", "N", "T"], "Reunión"),
    ]
    for j, (pais, ind, cargo, canal, tam, per, sub, bant, interes) in enumerate(POS):
        enviado = canal == "Correo electrónico"
        abierto = enviado and (j % 2 == 0)
        filas.append({
            "periodo": per, "canal": canal, "pais": pais, "industria": ind,
            "cargo": cargo, "tamano": tam, "empresa_id": j + 1,
            "respondio": True, "positiva": True, "reunion": False,
            "subestado": sub, "tipo_respuesta": "Espera validación",
            "etapa": None, "bant": bant,
            "interes_lead": interes, "motivo_rechazo": None,
            "enviado": enviado, "abierto": abierto,
        })
    return pd.DataFrame(filas)


df_all = cargar_dataset()

# ── Formateo es-CL ────────────────────────────────────────────────────
def fmt(n):
    return f"{int(n):,}".replace(",", ".")

def fpct(x, dec=1):
    return f"{x:.{dec}f}".replace(".", ",") + "%"

def dias_transcurridos(periodos_sel):
    if periodos_sel == ["Junio 2026"]:
        return 18
    if periodos_sel == ["Mayo 2026"]:
        return 31
    return 34

# ═══════════════════════════════════════════════════════════════════════
# HELPERS UI
# ═══════════════════════════════════════════════════════════════════════
def section_header(title, sub=None):
    s = (f'<div style="font-size:12px;color:{C_SLATE};margin-top:2px">{sub}</div>') if sub else ""
    st.markdown(
        f'<div style="border-left:4px solid {GBS_PURPLE};padding-left:12px;margin:8px 0 16px">'
        f'<div style="font-size:16px;font-weight:800;color:{GBS_DARK};letter-spacing:.3px">{title}</div>'
        f'{s}</div>',
        unsafe_allow_html=True,
    )


def kpi_card(col, label, value, sub, color):
    col.markdown(
        f'<div style="background:#fff;border:1px solid {GBS_BORDER};border-top:4px solid {color};'
        f'border-radius:10px;padding:16px 14px;text-align:center;height:118px;'
        f'display:flex;flex-direction:column;justify-content:center">'
        f'<div style="font-size:26px;font-weight:900;color:{color};'
        f'font-variant-numeric:tabular-nums">{value}</div>'
        f'<div style="font-size:11px;font-weight:700;color:#475569;margin-top:4px;'
        f'text-transform:uppercase;letter-spacing:.4px">{label}</div>'
        f'<div style="font-size:10px;color:#94a3b8;margin-top:3px;line-height:1.3">{sub}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def finding_card(icon_svg, color, titulo, detalle):
    st.markdown(
        f'<div style="display:flex;gap:14px;align-items:flex-start;background:#fff;'
        f'border:1px solid {GBS_BORDER};border-left:4px solid {color};border-radius:10px;'
        f'padding:14px 18px;margin-bottom:10px">'
        f'<div style="min-width:32px;height:32px;border-radius:8px;background:{color}14;'
        f'display:flex;align-items:center;justify-content:center;margin-top:1px">'
        f'{_svg(icon_svg, color, 17)}</div>'
        f'<div><div style="font-size:13.5px;font-weight:800;color:{GBS_DARK};margin-bottom:3px">'
        f'{titulo}</div>'
        f'<div style="font-size:12px;color:#64748b;line-height:1.6">{detalle}</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def css_hbar(rows, color, label_width=180, suffix=""):
    rows_pos = [(lbl, val) for lbl, val in rows if val > 0]
    if not rows_pos:
        return f'<div style="color:#94a3b8;font-size:13px;padding:12px">Sin datos en este recorte</div>'
    rows_sorted = sorted(rows_pos, key=lambda x: x[1])
    max_v = rows_sorted[-1][1]
    html = '<div style="padding:6px 0">'
    for lbl, val in rows_sorted:
        pct = max(int(val / max_v * 82), 3)
        html += (
            f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:10px">'
            f'<div style="min-width:{label_width}px;max-width:{label_width}px;font-size:12px;'
            f'color:#475569;text-align:right;overflow:hidden;text-overflow:ellipsis;'
            f'white-space:nowrap" title="{lbl}">{lbl}</div>'
            f'<div style="flex:1;background:#f1f5f9;border-radius:8px;height:24px;overflow:hidden">'
            f'<div style="background:linear-gradient(90deg,{color},{color}99);width:{pct}%;'
            f'height:100%;border-radius:8px;min-width:4px"></div></div>'
            f'<div style="min-width:50px;font-size:13px;font-weight:700;color:{color};'
            f'font-variant-numeric:tabular-nums">{fmt(val)}{suffix}</div>'
            f'</div>'
        )
    return html + '</div>'

# ═══════════════════════════════════════════════════════════════════════
# MOTOR DE ANÁLISIS — reglas sobre el recorte filtrado vs. baseline global
# ═══════════════════════════════════════════════════════════════════════
def _top_lift(dff, col, min_pos_total=8, min_pos_val=4, min_lift=1.3):
    pos = dff[dff.positiva]
    if len(pos) < min_pos_total:
        return None
    share_pos = pos[col].value_counts(normalize=True)
    share_base = dff[col].value_counts(normalize=True)
    cand = []
    for val in share_pos.index:
        npos = int((pos[col] == val).sum())
        sb = share_base.get(val, 0)
        if sb > 0 and npos >= min_pos_val:
            cand.append((val, share_pos[val], sb, share_pos[val] / sb, npos, len(pos)))
    if not cand:
        return None
    best = max(cand, key=lambda x: x[3])
    return best if best[3] >= min_lift else None


def _lift_txt(lift):
    return ('%.1f' % lift).replace('.', ',') + "x"


def generar_hallazgos(dff, activos):
    out = []
    pos = int(dff.positiva.sum())
    cont = len(dff)
    if pos < 5:
        return out

    if "cargo" not in activos:
        r = _top_lift(dff, "cargo")
        if r:
            out.append((f"{r[0]} concentra el {fpct(r[1]*100,0)} de las respuestas positivas",
                        f"Son {r[4]} de {r[5]} positivas — {_lift_txt(r[3])} su peso en la base. "
                        f"El cargo más receptivo del recorte y la puerta de entrada a priorizar."))

    base = df_all.positiva.mean()
    slice_rate = dff.positiva.mean()
    if base > 0 and slice_rate > 0 and cont >= 60 and pos >= 6:
        ratio = slice_rate / base
        if ratio >= 1.3:
            out.append((f"Este recorte convierte {_lift_txt(ratio)} mejor que el promedio",
                        f"La tasa de respuesta positiva es {fpct(slice_rate*100)} frente a {fpct(base*100)} "
                        f"del total de la campaña. Un foco de alto rendimiento para escalar volumen."))

    if "pais" not in activos:
        r = _top_lift(dff, "pais")
        if r:
            out.append((f"{r[0]} lidera con el {fpct(r[1]*100,0)} de las respuestas positivas",
                        f"Concentra {r[4]} de {r[5]} positivas — {_lift_txt(r[3])} su peso en la base. "
                        f"El mercado con mayor tracción del recorte."))

    if "tamano" not in activos:
        r = _top_lift(dff, "tamano", min_lift=1.25)
        if r:
            out.append((f"Las respuestas se concentran en empresas de {r[0].replace(' empleados','')} empleados",
                        f"Este tamaño aporta el {fpct(r[1]*100,0)} de las positivas ({_lift_txt(r[3])} su peso "
                        f"en la base): el perfil que más valora externalizar la logística."))

    if "industria" not in activos:
        r = _top_lift(dff, "industria")
        if r:
            out.append((f"{r[0]} es la industria que más responde",
                        f"Genera {r[4]} de {r[5]} positivas ({_lift_txt(r[3])} su peso en la base). "
                        f"El dolor logístico de este vertical conecta directo con la propuesta de GBS."))

    return out[:4]


def generar_riesgos(dff, activos):
    out = []
    cont = len(dff)
    pos = int(dff.positiva.sum())
    reun = int(dff.reunion.sum())

    for col, etiqueta in [("industria", "La industria"), ("pais", "El mercado"), ("cargo", "El cargo")]:
        if col in activos:
            continue
        g = dff.groupby(col).agg(c=("positiva", "size"), p=("positiva", "sum"))
        g = g[g.c >= max(40, cont * 0.08)]
        sin = g[g.p == 0]
        if len(sin) > 0:
            peor = sin.sort_values("c", ascending=False).index[0]
            n = int(sin.loc[peor, "c"])
            out.append((f"{etiqueta} {peor} no registra respuestas positivas",
                        f"Pese a {fmt(n)} contactos trabajados, no generó interés. Conviene revisar el "
                        f"mensaje o despriorizar el segmento."))
            break

    if dff.periodo.nunique() > 1:
        rm = dff[dff.periodo == "Mayo 2026"].positiva.mean()
        rj = dff[dff.periodo == "Junio 2026"].positiva.mean()
        if rm and rj and rj < rm * 0.85:
            out.append(("La tasa de respuesta positiva bajó respecto al período anterior",
                        f"Pasó de {fpct(rm*100)} en mayo a {fpct(rj*100)} en junio. Vale revisar fatiga de "
                        f"base o cambios en los mensajes."))

    if "canal" not in activos and cont >= 100:
        g = dff.groupby("canal").agg(c=("positiva", "size"), p=("positiva", "mean"))
        g = g[g.c >= 60]
        if len(g) >= 2:
            peor = g.sort_values("p").index[0]
            if g.loc[peor, "p"] < df_all.positiva.mean() * 0.7:
                out.append((f"{peor} rinde por debajo del promedio en este recorte",
                            f"Su tasa de respuesta positiva ({fpct(g.loc[peor,'p']*100)}) está bajo el "
                            f"promedio de campaña. Reasignar esfuerzo a canales más efectivos."))

    if pos > 0 and reun == 0:
        out.append(("Hay interés pero aún sin reuniones agendadas",
                    f"El recorte tiene {pos} respuestas positivas y 0 reuniones: el cuello de botella está "
                    f"en el paso de respuesta a agenda. Acelerar el follow-up."))

    return out[:3]


def generar_recomendaciones(dff, activos):
    out = []
    cont = len(dff)
    if cont < 30:
        return out

    base = df_all.positiva.mean()

    if "cargo" not in activos:
        g = dff.groupby("cargo").agg(c=("positiva", "size"), p=("positiva", "mean"))
        g = g[g.c >= 50]
        if len(g):
            mejor = g.sort_values("p", ascending=False).index[0]
            if g.loc[mejor, "p"] >= base:
                out.append((f"Priorizar {mejor} en la prospección",
                            f"Es el cargo de mayor conversión del recorte ({fpct(g.loc[mejor,'p']*100)}). "
                            f"Concentrar volumen aquí mejora el rendimiento global."))

    if "canal" not in activos:
        g = dff.groupby("canal").agg(c=("positiva", "size"), p=("positiva", "mean"))
        g = g[g.c >= 50]
        if len(g) >= 2:
            mejor = g.sort_values("p", ascending=False).index[0]
            out.append((f"Concentrar esfuerzo en {mejor}",
                        f"Es el canal con mejor tasa de respuesta positiva en este recorte "
                        f"({fpct(g.loc[mejor,'p']*100)}). Subir su cobertura tiene el mejor retorno."))

    if "industria" not in activos:
        g = dff.groupby("industria").agg(c=("positiva", "size"), p=("positiva", "mean"))
        g = g[(g.c >= 20) & (g.c <= cont * 0.30)]
        g = g[g.p >= base * 1.2]
        if len(g):
            nicho = g.sort_values("p", ascending=False).index[0]
            out.append((f"Ampliar cobertura en {nicho}",
                        f"Convierte por encima del promedio pero tiene base chica ({fmt(int(g.loc[nicho,'c']))} "
                        f"contactos). Hay volumen sin explotar en este vertical."))

    return out[:3]

# ═══════════════════════════════════════════════════════════════════════
# HEADER — solo "Revenue Intelligence"
# ═══════════════════════════════════════════════════════════════════════
g = img_b64("gbs_logo.png", 52) or (
    f'<div style="background:{GBS_PURPLE};color:#fff;padding:10px 22px;border-radius:8px;'
    f'font-size:18px;font-weight:800;letter-spacing:2px">GBS</div>')
c = img_b64("conprospeccion_logo.png", 42) or (
    f'<div style="background:#111827;padding:8px 18px;border-radius:8px;'
    f'font-size:13px;font-weight:700;color:#fbbf24">Conprospección</div>')

st.markdown(
    f'<div style="display:flex;align-items:center;justify-content:space-between;'
    f'background:linear-gradient(135deg,#faf5ff,#ede9fe);padding:18px 28px;'
    f'border-radius:14px;border:1px solid {GBS_BORDER};margin-bottom:20px;'
    f'box-shadow:0 2px 8px rgba(0,0,0,.06)">'
    f'<div style="display:flex;align-items:center;gap:18px">{g}'
    f'<div style="font-size:22px;font-weight:800;color:{GBS_DARK}">Intelligence Insight</div>'
    f'</div>{c}</div>',
    unsafe_allow_html=True,
)

# ═══════════════════════════════════════════════════════════════════════
# 1 — AVANCE DE META (live, fijo, no depende de filtros)
# ═══════════════════════════════════════════════════════════════════════
V = cargar_validacion_gbs()
dias_camp = max((date.today() - CAMPANA_INICIO).days, 0)
dias_camp = min(dias_camp, DIAS_CAMPANA)
validas_reales = V["validas"]
pct_meta = min(validas_reales / META_VALIDAS * 100, 100) if META_VALIDAS else 0
pct_tiempo = min(dias_camp / DIAS_CAMPANA * 100, 100)
faltan = max(META_VALIDAS - validas_reales, 0)

meta_color = C_GREEN if pct_meta >= pct_tiempo else (C_AMBER if pct_meta >= pct_tiempo * 0.6 else GBS_PURPLE)

st.markdown(
    f'<div style="background:linear-gradient(135deg,#fff,{GBS_BG});border:1px solid {GBS_BORDER};'
    f'border-radius:14px;padding:20px 26px;margin-bottom:18px;box-shadow:0 1px 4px rgba(0,0,0,.04)">'
    f'<div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:10px;flex-wrap:wrap;gap:8px">'
    f'<div><div style="font-size:13px;font-weight:800;color:{GBS_PURPLE};text-transform:uppercase;'
    f'letter-spacing:.5px">Avance de la meta</div>'
    f'<div style="font-size:12px;color:{C_SLATE};margin-top:2px">'
    f'Garantía: {META_VALIDAS} reuniones válidas en 5 meses · día {dias_camp} de {DIAS_CAMPANA}</div></div>'
    f'<div style="text-align:right"><span style="font-size:30px;font-weight:900;color:{meta_color};'
    f'font-variant-numeric:tabular-nums">{validas_reales}</span>'
    f'<span style="font-size:18px;font-weight:700;color:{C_SLATE}"> / {META_VALIDAS}</span></div></div>'
    f'<div style="position:relative;background:#f1f5f9;border-radius:10px;height:22px;overflow:hidden">'
    f'<div style="background:linear-gradient(90deg,{GBS_PURPLE},{GBS_PINK});width:{max(pct_meta,1.5):.1f}%;'
    f'height:100%;border-radius:10px"></div>'
    f'<div style="position:absolute;top:0;left:{pct_tiempo:.1f}%;width:2px;height:100%;'
    f'background:{GBS_DARK};opacity:.45"></div></div>'
    f'<div style="display:flex;justify-content:space-between;margin-top:6px">'
    f'<span style="font-size:11px;color:{C_SLATE}">{fpct(pct_meta,0)} de la meta · faltan {faltan} válidas</span>'
    f'<span style="font-size:11px;color:{C_SLATE}">La línea marca el avance del tiempo ({fpct(pct_tiempo,0)})</span>'
    f'</div></div>',
    unsafe_allow_html=True,
)

# ═══════════════════════════════════════════════════════════════════════
# 2 — KPIs DE VALIDACIÓN (live, fijos)
# ═══════════════════════════════════════════════════════════════════════
av_com = (V["avanzan"] / validas_reales * 100) if validas_reales else 0.0
k1, k2, k3, k4 = st.columns(4)
kpi_card(k1, "Reuniones válidas", fmt(V["validas"]), "Confirmadas por GBS", C_GREEN)
kpi_card(k2, "Reuniones no válidas", fmt(V["no_validas"]), "Descartadas en validación", C_RED)
kpi_card(k3, "Reagendar", fmt(V["reagendar"]), "Pendientes de reprogramar", C_AMBER)
kpi_card(k4, "Avance comercial", fpct(av_com, 0), "Válidas que avanzaron en pipeline", GBS_PURPLE)

if V["total"] == 0:
    st.markdown(
        f'<div style="font-size:12px;color:{C_SLATE};margin:8px 0 4px">'
        f'Estos indicadores se completan automáticamente a medida que el equipo de GBS evalúa cada '
        f'reunión en el panel <b>Validación de Reuniones</b>.</div>',
        unsafe_allow_html=True,
    )

# Nota de mes 1 — fase de estrategia y validación
st.markdown(
    f'<div style="background:{GBS_PURPLE}0d;border:1px solid {GBS_BORDER};border-left:4px solid '
    f'{GBS_PURPLE};border-radius:10px;padding:12px 16px;margin-top:10px">'
    f'<div style="font-size:12.5px;font-weight:800;color:{GBS_PURPLE};margin-bottom:3px">'
    f'Mes 1 — Estrategia comercial y validación</div>'
    f'<div style="font-size:12px;color:#475569;line-height:1.6">'
    f'El primer mes está enfocado en <b>validar la base de datos</b> y afinar la estrategia: qué '
    f'tipos de campaña, cargos, industrias y tipos de respuesta funcionan mejor. Los resultados de '
    f'reuniones válidas y avance comercial empiezan a acumularse a partir de esta etapa.</div></div>',
    unsafe_allow_html=True,
)
st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# 2c — RESUMEN EJECUTIVO (lectura CEO: embudo, dónde enfocar, estado de meta)
# ═══════════════════════════════════════════════════════════════════════
def _re_top(dim):
    """Valor con más respuestas positivas en la dimensión: (valor, n_pos, n_cont, tasa%)."""
    pos = df_all.groupby(dim).positiva.sum()
    if pos.sum() == 0:
        return None
    valor = pos.idxmax(); n_pos = int(pos.max())
    n_cont = int((df_all[dim] == valor).sum())
    return valor, n_pos, n_cont, (n_pos / n_cont * 100 if n_cont else 0)

_re_cont = len(df_all)
_re_resp = int(df_all.respondio.sum())
_re_pos = int(df_all.positiva.sum())
_re_agen = int((df_all.subestado == "agendada").sum())
_re_tasa = _re_resp / _re_cont * 100 if _re_cont else 0
_rt_pais, _rt_ind = _re_top("pais"), _re_top("industria")
_rt_cargo, _rt_canal = _re_top("cargo"), _re_top("canal")

_bullets = [
    f"<b>Embudo:</b> {fmt(_re_cont)} contactos {fmt(_re_resp)} respuestas ({fpct(_re_tasa,1)}) "
    f"{fmt(_re_pos)} positivas {fmt(_re_agen)} reuniones agendadas (pendientes de validación).",
]
if _rt_pais and _rt_ind:
    _bullets.append(
        f"<b>Dónde traccciona:</b> {_rt_pais[0]} e {_rt_ind[0]} concentran las respuestas positivas "
        f"— es donde el mercado pide logística con más fuerza.")
if _rt_cargo and _rt_canal:
    _bullets.append(
        f"<b>Qué priorizar:</b> el cargo <b>{_rt_cargo[0]}</b> es el que más engancha "
        f"({_rt_cargo[1]} de {fmt(_re_pos)} positivas) y <b>{_rt_canal[0]}</b> es el canal más efectivo. "
        f"Concentrar volumen ahí sube la tasa de éxito.")
_bullets.append(
    f"<b>Estado de meta:</b> garantía de {META_VALIDAS} reuniones válidas; hoy {fmt(V['validas'])} "
    f"validadas — en fase de validación, el avance arranca cuando GBS califique las reuniones.")
if _re_pos < 10:
    _bullets.append(
        "<b>Confianza:</b> muestra todavía chica. Leer como <b>señal direccional</b>, no como "
        "conclusión firme; se afina con más datos.")

section_header("Resumen ejecutivo", "Lo esencial en 30 segundos: embudo, dónde enfocar y estado de la meta")
st.markdown(
    f'<div style="background:#fff;border:1px solid {GBS_BORDER};border-left:4px solid {GBS_PURPLE};'
    f'border-radius:12px;padding:16px 20px;font-size:13px;color:#334155;line-height:1.7">'
    + "".join(f'<div style="margin-bottom:8px">• {b}</div>' for b in _bullets)
    + '</div>',
    unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# 2d — EFECTIVIDAD POR SEGMENTO (tasa de positivas, no volumen)
# ═══════════════════════════════════════════════════════════════════════
_overall_rate = (_re_pos / _re_cont * 100) if _re_cont else 0

def _efect_html(dim, titulo, top=6):
    g = df_all.groupby(dim).agg(pos=("positiva", "sum"), cont=("positiva", "size"))
    g["tasa"] = g.pos / g.cont * 100
    g = g.sort_values(["tasa", "pos"], ascending=False).head(top)
    filas = ""
    for val, r in g.iterrows():
        if r.pos == 0:
            lbl, col, bg = "Cortar", C_RED, "#fee2e2"
        elif r.tasa >= _overall_rate:
            lbl, col, bg = "Priorizar", C_GREEN, "#dcfce7"
        else:
            lbl, col, bg = "Observar", C_AMBER, "#fef3c7"
        filas += (
            f'<div style="display:flex;align-items:center;gap:8px;'
            f'padding:6px 0;border-bottom:1px solid #f1f5f9">'
            f'<div style="font-size:12px;color:{GBS_DARK};flex:1;white-space:nowrap;overflow:hidden;'
            f'text-overflow:ellipsis">{val}</div>'
            f'<div style="font-size:12px;font-weight:800;color:{GBS_DARK};width:48px;text-align:right">{fpct(r.tasa,1)}</div>'
            f'<div style="font-size:11px;color:{C_SLATE};width:56px;text-align:right">{int(r.pos)}/{fmt(int(r.cont))}</div>'
            f'<span style="background:{bg};color:{col};font-size:10px;font-weight:700;padding:2px 8px;'
            f'border-radius:8px;width:66px;text-align:center">{lbl}</span></div>')
    return (f'<div style="background:#fff;border:1px solid {GBS_BORDER};border-radius:12px;padding:14px 16px;'
            f'height:100%"><div style="font-size:13px;font-weight:700;color:{GBS_DARK};margin-bottom:6px">'
            f'{titulo}</div>{filas}</div>')

section_header("Efectividad por segmento",
               "Dónde conviene concentrar: tasa de respuesta positiva por segmento, no solo volumen")
ec1, ec2 = st.columns(2)
ec1.markdown(_efect_html("cargo", "Por cargo"), unsafe_allow_html=True)
ec2.markdown(_efect_html("industria", "Por industria"), unsafe_allow_html=True)
st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
ec3, ec4 = st.columns(2)
ec3.markdown(_efect_html("pais", "Por país"), unsafe_allow_html=True)
ec4.markdown(_efect_html("canal", "Por canal"), unsafe_allow_html=True)
st.caption(f"Tasa = respuestas positivas ÷ contactos del segmento. Semáforo vs. el promedio de campaña "
           f"({fpct(_overall_rate,1)}): Priorizar ≥ promedio · Observar < promedio · Cortar = 0. "
           f"Con muestra chica, leer como señal direccional.")
st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# 2e — MOTIVOS DE RECHAZO (por qué se cae el resto + acción)
# ═══════════════════════════════════════════════════════════════════════
section_header("Motivos de rechazo", "Por qué se cae el resto de los contactos — y qué hacer al respecto")
_mot = df_all[df_all.motivo_rechazo.notna()]
if len(_mot) == 0:
    st.markdown(
        f'<div style="font-size:13px;color:{C_SLATE};padding:4px 0 8px">'
        f'Aún no hay motivos de rechazo registrados. Se completan a medida que el cliente y el equipo '
        f'califican las respuestas negativas.</div>',
        unsafe_allow_html=True)
else:
    _ACCION = {
        "Ya tienen proveedor": "Reforzar el pitch de segunda opción: rutas, urgencias y puerta a puerta "
                               "donde el operador actual falla.",
        "Sin respuesta": "Ajustar la secuencia de seguimiento: variar canal y horario, sostener "
                               "4–5 toques antes de cerrar.",
        "No interesado": "Afinar el ICP y el mensaje: validar el fit (comercio exterior recurrente) "
                               "antes de insistir.",
    }
    _mc = df_all.groupby("motivo_rechazo").size().sort_values(ascending=False)
    _tot = int(_mc.sum())
    mc1, mc2 = st.columns([1, 1])
    with mc1:
        st.markdown(
            f'<div style="font-size:13px;font-weight:700;color:{GBS_DARK};margin-bottom:6px">'
            f'Distribución de motivos ({_tot} respuestas negativas)</div>'
            + css_hbar([(k, int(v)) for k, v in _mc.items()], GBS_PINK, label_width=170),
            unsafe_allow_html=True)
    with mc2:
        _filas_acc = ""
        for k, v in _mc.items():
            _share = v / _tot * 100 if _tot else 0
            _acc = _ACCION.get(k, "Revisar el segmento y ajustar el enfoque.")
            _filas_acc += (
                f'<div style="margin-bottom:10px">'
                f'<div style="font-size:12.5px;font-weight:800;color:{GBS_DARK}">{k} · {fpct(_share,0)}</div>'
                f'<div style="font-size:12px;color:#475569;line-height:1.5">{_acc}</div></div>')
        st.markdown(
            f'<div style="background:#fff;border:1px solid {GBS_BORDER};border-left:4px solid {GBS_PINK};'
            f'border-radius:12px;padding:14px 16px">'
            f'<div style="font-size:13px;font-weight:700;color:{GBS_DARK};margin-bottom:8px">'
            f'Acción sugerida por motivo</div>{_filas_acc}</div>',
            unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# 3 — ICP DEL CLIENTE
# ═══════════════════════════════════════════════════════════════════════
section_header("Perfil del Cliente ideal (ICP y Buyer Persona)", "A quién apunta la campaña de GBS Logistics")
st.markdown(
    f'<div style="background:#fff;border:1px solid {GBS_BORDER};border-radius:12px;padding:18px 22px;'
    f'font-size:13px;color:#334155;line-height:1.7;margin-bottom:8px">'
    f'<b>Propuesta de valor:</b> GBS elimina la carga de coordinar múltiples proveedores: un solo '
    f'interlocutor maneja flete internacional, aduana, transporte local, seguro y documentación.<br><br>'
    f'<b>Empresas objetivo:</b> Pymes de Chile, Perú y Colombia (10–200 empleados) con comercio exterior '
    f'recurrente.<br>'
    f'<b>Cargos:</b> Encargado de Importaciones · Jefe COMEX · Gerente de Operaciones · Supply Chain '
    f'Manager · Gerente de Abastecimiento.<br>'
    f'<b>Industrias foco:</b> Minería y Metales · Retail · Automotriz · Alimentos y Bebidas · '
    f'Dispositivos Médicos.<br>'
    f'<b>Se descarta:</b> Freight forwarders, agentes de aduana, navieras e import/export '
    f'(competencia directa).</div>',
    unsafe_allow_html=True,
)

# Cruce: ICP teórico (definido) vs. ICP que realmente convierte (datos)
_cargo_real = df_all.groupby("cargo").positiva.sum()
_ind_real = df_all.groupby("industria").positiva.sum()
if _cargo_real.sum() > 0:
    _cr_top = _cargo_real.idxmax()
    _ir_top = _ind_real.idxmax()
    _cargos_sin = [c for c in TOP_CARGOS if int(_cargo_real.get(c, 0)) == 0]
    _icp_txt = (f"Dentro del ICP definido, los que más convierten en los datos son "
                f"<b>{_cr_top}</b> (cargo) e <b>{_ir_top}</b> (industria). ")
    if _cargos_sin:
        _icp_txt += (f"Cargos del ICP aún sin tracción: {', '.join(_cargos_sin)} — revisar el mensaje "
                     f"o despriorizarlos si siguen sin responder.")
    else:
        _icp_txt += "Todos los cargos del ICP muestran al menos una respuesta positiva."
    finding_card(IC_INSIGHT, GBS_PURPLE,
                 "ICP real vs. teórico — dónde converge la demanda", _icp_txt)
st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# 4 — FILTROS (chips eliminables + restablecer)
# ═══════════════════════════════════════════════════════════════════════
def _opts(col):
    return ["Todos"] + sorted(df_all[col].unique().tolist())

# (key, label, opciones, columna, kind) kind: "select" | "multi"
FILTROS = [
    ("f_per", "Período", ["Todos", "Mayo 2026", "Junio 2026"], "periodo", "select"),
    ("f_can", "Canal", _opts("canal"), "canal", "select"),
    ("f_pais", "País", _opts("pais"), "pais", "select"),
    ("f_ind", "Industria", _opts("industria"), "industria", "select"),
    ("f_cargo", "Cargo", _opts("cargo"), "cargo", "select"),
    ("f_tipo", "Tipo de respuesta", ["Todos"] + TIPO_RESP_OPTS, "tipo_respuesta", "select"),
    ("f_etapa", "Etapa comercial", ["Todos"] + ETAPA_OPTS, "etapa", "select"),
    ("f_int", "Interés del lead", ["Todos"] + INTERES_OPTS, "interes_lead", "select"),
    ("f_mot", "Motivo de rechazo", ["Todos"] + MOTIVO_OPTS, "motivo_rechazo", "select"),
    ("f_bant", "Validación BANT", BANT_OPTS, "bant", "multi"),
]
_KIND = {k: kind for k, _, _, _, kind in FILTROS}

def _reset_one(key):
    st.session_state[key] = [] if _KIND.get(key) == "multi" else "Todos"

def _reset_all():
    for k, _, _, _, kind in FILTROS:
        st.session_state[k] = [] if kind == "multi" else "Todos"

st.markdown(
    f'<div style="font-size:11px;font-weight:800;color:{GBS_PURPLE};'
    f'text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">Filtros</div>',
    unsafe_allow_html=True,
)
# Estilo de las etiquetas (chips) de filtro activo — píldoras moradas pequeñas con
st.markdown(
    f'''<style>
    [class*="st-key-chip_"] button {{
        background:{GBS_PURPLE}14 !important; color:{GBS_PURPLE} !important;
        border:1px solid {GBS_PURPLE}40 !important; border-radius:20px !important;
        padding:2px 14px !important; font-size:12px !important; font-weight:700 !important;
        min-height:0 !important; height:auto !important; line-height:1.7 !important;
    }}
    [class*="st-key-chip_"] button:hover {{
        background:{GBS_PURPLE}26 !important; border-color:{GBS_PURPLE} !important;
    }}
    /* Botón Restablecer — morado GBS, nunca rojo */
    [class*="st-key-reset_all"] button,
    [class*="st-key-sug_reset"] button,
    [class*="st-key-reset_empty"] button {{
        background:{GBS_PURPLE} !important; color:#fff !important; border:none !important;
        border-radius:8px !important; font-weight:700 !important;
    }}
    [class*="st-key-reset_all"] button:hover,
    [class*="st-key-sug_reset"] button:hover,
    [class*="st-key-reset_empty"] button:hover {{ filter:brightness(1.08); }}
    /* Chips de multiselect (BANT) en lavanda claro, consistente con el Onboarding */
    span[data-baseweb="tag"] {{ background:#ede9fe !important; color:#5b21b6 !important; }}
    span[data-baseweb="tag"] span {{ color:#5b21b6 !important; }}
    span[data-baseweb="tag"] svg {{ fill:#5b21b6 !important; }}
    </style>''',
    unsafe_allow_html=True,
)

sel = {}
slots = []
while len(slots) < len(FILTROS):
    slots += st.columns(4)
for (key, label, opciones, _, kind), col in zip(FILTROS, slots):
    if kind == "multi":
        sel[key] = col.multiselect(label, opciones, key=key,
                                   placeholder="Seleccionar opciones",
                                   format_func=lambda x: f"{x} · {BANT_LABEL[x]}")
    else:
        sel[key] = col.selectbox(label, opciones, key=key)

# Aplicar filtros
dff = df_all.copy()
activos = set()
activos_keys = []
for key, label, _, columna, kind in FILTROS:
    val = sel[key]
    if kind == "multi":
        if val:
            req = set(val)
            dff = dff[dff["bant"].apply(lambda s: req.issubset(set(s)))]
            activos.add(columna)
            activos_keys.append((key, label, ", ".join(val)))
    elif val != "Todos":
        dff = dff[dff[columna] == val]
        activos.add(columna)
        activos_keys.append((key, label, val))

periodos_sel = [sel["f_per"]] if sel["f_per"] != "Todos" else ["Mayo 2026", "Junio 2026"]

# Chips eliminables (píldoras moradas con ) + restablecer
if activos_keys:
    st.markdown(
        f'<div style="font-size:12px;color:{C_SLATE};margin:8px 0 4px">Filtros aplicados:</div>',
        unsafe_allow_html=True,
    )
    chip_cols = st.columns(len(activos_keys) + 1)
    for (key, label, val), ccol in zip(activos_keys, chip_cols):
        ccol.button(f"{label}: {val} ", key=f"chip_{key}",
                    on_click=_reset_one, args=(key,), use_container_width=True)
    chip_cols[-1].button(" Restablecer", key="reset_all",
                         on_click=_reset_all, use_container_width=True)
else:
    st.markdown(
        f'<div style="margin:8px 0 2px"><span style="font-size:12px;color:{C_SLATE};margin-right:8px">'
        f'Mostrando:</span><span style="background:{GBS_PURPLE}12;color:{GBS_PURPLE};'
        f'border:1px solid {GBS_PURPLE}35;border-radius:20px;padding:3px 12px;font-size:12px;'
        f'font-weight:600;display:inline-block">Vista global — toda la campaña</span></div>',
        unsafe_allow_html=True,
    )
st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════
# Estado vacío — con sugerencias de filtros a quitar
# ═══════════════════════════════════════════════════════════════════════
contactos = len(dff)
if contactos == 0:
    # ¿Qué filtro, si se quita, devuelve datos?
    sugerencias = []
    for key, label, val in activos_keys:
        prueba = df_all.copy()
        for k2, _, _, col2, kind2 in FILTROS:
            if k2 == key:
                continue
            v2 = sel[k2]
            if kind2 == "multi":
                if v2:
                    req2 = set(v2)
                    prueba = prueba[prueba["bant"].apply(lambda s: req2.issubset(set(s)))]
            elif v2 != "Todos":
                prueba = prueba[prueba[col2] == v2]
        if len(prueba) > 0:
            sugerencias.append((key, label))

    st.markdown(
        f'<div style="background:#fff;border:1px dashed {GBS_BORDER};border-radius:12px;'
        f'padding:40px 24px 24px;text-align:center;color:{C_SLATE}">'
        f'<div style="font-size:15px;font-weight:700;color:{GBS_DARK};margin-bottom:6px">'
        f'No hay contactos con esta combinación de filtros</div>'
        f'<div style="font-size:13px;margin-bottom:14px">Quita uno de estos filtros para ver datos:</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if sugerencias:
        sug_cols = st.columns(min(len(sugerencias), 4) + 1)
        for (key, label), scol in zip(sugerencias, sug_cols):
            scol.button(f"Quitar {label}", key=f"sug_{key}",
                        on_click=_reset_one, args=(key,), use_container_width=True)
        sug_cols[len(sugerencias) if len(sugerencias) < 4 else 4].button(
            "Restablecer todo", key="sug_reset", on_click=_reset_all,
            use_container_width=True)
    else:
        st.button("Restablecer filtros", key="reset_empty", on_click=_reset_all)
    st.stop()

# ═══════════════════════════════════════════════════════════════════════
# 5 — MÉTRICAS DEL REPORTE (recorte filtrado) + GRÁFICOS
# ═══════════════════════════════════════════════════════════════════════
empresas = dff.empresa_id.nunique()
respuestas = int(dff.respondio.sum())
positivas = int(dff.positiva.sum())
n_info = int((dff.subestado == "info_adicional").sum())
n_coord = int((dff.subestado == "coordinando").sum())
n_agen = int((dff.subestado == "agendada").sum())
reuniones = n_agen
conv = reuniones / contactos * 100 if contactos else 0
tasa_pos = positivas / contactos * 100 if contactos else 0

dias = dias_transcurridos(periodos_sel)
reun_proy = round(reuniones / dias * DIAS_CAMPANA) if dias else 0
validas_proy = round(reun_proy * 0.6)

section_header("Métricas del reporte", "Resultados de prospección del recorte seleccionado")
m1, m2, m3 = st.columns(3)
kpi_card(m1, "Contactos trabajados", fmt(contactos), "Base activa del recorte", GBS_PURPLE)
kpi_card(m2, "Empresas impactadas", fmt(empresas), "Cuentas únicas alcanzadas", GBS_PURPLE)
kpi_card(m3, "Respuestas", fmt(respuestas),
         f"{fpct(respuestas/contactos*100,0)} de la base" if contactos else "—", GBS_PINK)

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
m4, m5, m6 = st.columns(3)
kpi_card(m4, "Respuestas positivas", fmt(positivas),
         f"Info. adicional {n_info} · Coordinando {n_coord} · Agendada {n_agen}", GBS_YELLOW)
kpi_card(m5, "Reuniones agendadas", fmt(reuniones), "Sub-estado «Reunión agendada»", C_GREEN)
kpi_card(m6, "Conversión", fpct(conv), "Reuniones / contactos", C_GREEN)

st.markdown("<br>", unsafe_allow_html=True)

cg1, cg2 = st.columns(2)
with cg1:
    gp = dff.groupby("pais").size().sort_values(ascending=False)
    st.markdown(
        f'<div style="font-size:13px;font-weight:700;color:{GBS_DARK};margin-bottom:6px">'
        f'Contactos por país</div>'
        + css_hbar(list(gp.items()), GBS_PURPLE, label_width=150),
        unsafe_allow_html=True,
    )
    gc = dff.groupby("cargo").size().sort_values(ascending=False)
    st.markdown(
        f'<div style="font-size:13px;font-weight:700;color:{GBS_DARK};margin:14px 0 6px">'
        f'Contactos por cargo</div>'
        + css_hbar(list(gc.items()), GBS_PINK, label_width=205),
        unsafe_allow_html=True,
    )
with cg2:
    gi = dff[dff.positiva].groupby("industria").size().sort_values(ascending=False)
    st.markdown(
        f'<div style="font-size:13px;font-weight:700;color:{GBS_DARK};margin-bottom:6px">'
        f'Respuestas positivas por industria</div>'
        + css_hbar(list(gi.items()), GBS_YELLOW, label_width=160),
        unsafe_allow_html=True,
    )
    gca = dff.groupby("canal").agg(p=("positiva", "sum"))
    st.markdown(
        f'<div style="font-size:13px;font-weight:700;color:{GBS_DARK};margin:14px 0 6px">'
        f'Respuestas positivas por canal</div>'
        + css_hbar([(k, int(v)) for k, v in gca.p.items()], GBS_PURPLE, label_width=160),
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# 5c — APERTURAS (email) Y RESPUESTAS POR SEGMENTO
# ═══════════════════════════════════════════════════════════════════════
section_header("Aperturas y respuestas por segmento",
               "Tasa de apertura de email y dónde responden más los prospectos")

_env = int(dff.enviado.sum()) if "enviado" in dff.columns else 0
_abi = int(dff.abierto.sum()) if "abierto" in dff.columns else 0
_tasa_ap = _abi / _env * 100 if _env else 0
ap1, ap2, ap3 = st.columns(3)
kpi_card(ap1, "Emails enviados",   fmt(_env), "Contactos por canal correo",            GBS_PURPLE)
kpi_card(ap2, "Emails abiertos",   fmt(_abi), f"Tasa de apertura {fpct(_tasa_ap, 0)}", GBS_PINK)
kpi_card(ap3, "Tasa de apertura",  fpct(_tasa_ap, 1), "Abiertos / enviados",           C_GREEN)
st.caption("Apertura de email (canal correo). Hoy con datos de muestra; se conecta a los eventos "
           "reales de campaña a medida que se envían correos.")

st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
st.markdown(
    f'<div style="font-size:13px;font-weight:700;color:{GBS_DARK};margin:2px 0 8px">'
    f'Respuestas por segmento (volumen de respuestas en el recorte)</div>',
    unsafe_allow_html=True)
_rdf = dff[dff.respondio]
rs1, rs2 = st.columns(2)
with rs1:
    gc = _rdf.groupby("cargo").size().sort_values(ascending=False)
    st.markdown(
        f'<div style="font-size:12px;font-weight:700;color:{C_SLATE};margin-bottom:4px">Por cargo</div>'
        + css_hbar(list(gc.items()), GBS_PURPLE, label_width=200), unsafe_allow_html=True)
    gp = _rdf.groupby("pais").size().sort_values(ascending=False)
    st.markdown(
        f'<div style="font-size:12px;font-weight:700;color:{C_SLATE};margin:12px 0 4px">Por país</div>'
        + css_hbar(list(gp.items()), GBS_YELLOW, label_width=200), unsafe_allow_html=True)
with rs2:
    gi = _rdf.groupby("industria").size().sort_values(ascending=False)
    st.markdown(
        f'<div style="font-size:12px;font-weight:700;color:{C_SLATE};margin-bottom:4px">Por industria</div>'
        + css_hbar(list(gi.items()), GBS_PINK, label_width=200), unsafe_allow_html=True)
    gca2 = _rdf.groupby("canal").size().sort_values(ascending=False)
    st.markdown(
        f'<div style="font-size:12px;font-weight:700;color:{C_SLATE};margin:12px 0 4px">Por canal (campaña)</div>'
        + css_hbar(list(gca2.items()), GBS_PURPLE, label_width=200), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# 5b — EMBUDO DE CONVERSIÓN (mini-funnel, HTML/CSS puro)
# ═══════════════════════════════════════════════════════════════════════
section_header("Embudo de conversión", "De contactos trabajados a reuniones, en un vistazo")
_etapas_funnel = [
    ("Contactos trabajados", contactos, GBS_PURPLE),
    ("Respuestas", respuestas, GBS_PINK),
    ("Respuestas positivas", positivas, GBS_YELLOW),
    ("Reuniones agendadas", reuniones, C_GREEN),
]
_base_funnel = contactos or 1
_funnel_html = '<div style="display:flex;flex-direction:column;gap:8px;padding:4px 0 8px">'
_prev_val = None
for _et_lbl, _et_val, _et_col in _etapas_funnel:
    _w = max(6, int(_et_val / _base_funnel * 100))
    _conv_prev = (f' · {fpct(_et_val / _prev_val * 100, 0)} del paso anterior'
                  if _prev_val not in (None, 0) else '')
    _funnel_html += (
        f'<div style="display:flex;align-items:center;gap:12px">'
        f'<div style="width:180px;font-size:12px;font-weight:600;color:{GBS_DARK};text-align:right">{_et_lbl}</div>'
        f'<div style="flex:1;background:#f1f5f9;border-radius:8px;height:30px;position:relative;overflow:hidden">'
        f'<div style="width:{_w}%;min-width:46px;background:{_et_col};height:30px;border-radius:8px;'
        f'display:flex;align-items:center;padding-left:12px;color:#fff;font-size:13px;font-weight:800">'
        f'{fmt(_et_val)}</div></div>'
        f'<div style="width:200px;font-size:11px;color:{C_SLATE}">{fpct(_et_val / _base_funnel * 100, 1)} de contactos{_conv_prev}</div>'
        f'</div>'
    )
    _prev_val = _et_val
_funnel_html += '</div>'
st.markdown(_funnel_html, unsafe_allow_html=True)
st.caption("La etapa final «Reuniones válidas» se sumará al embudo cuando el cliente valide las "
           "reuniones agendadas en el reporte «Validación de reuniones».")

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# 6 — HALLAZGOS CLAVE
# ═══════════════════════════════════════════════════════════════════════
hallazgos = generar_hallazgos(dff, activos)
section_header("Hallazgos clave", "Lo que los datos están diciendo de este recorte")
if hallazgos:
    for t, d in hallazgos:
        finding_card(IC_INSIGHT, GBS_PURPLE, t, d)
else:
    st.markdown(
        f'<div style="font-size:13px;color:{C_SLATE};padding:4px 0 8px">'
        f'Muestra pequeña: aún no hay suficientes respuestas positivas en este recorte '
        f'para extraer un patrón confiable. Se recomienda ampliar los filtros.</div>',
        unsafe_allow_html=True,
    )

riesgos = generar_riesgos(dff, activos)
if riesgos:
    section_header("Riesgos detectados", "Señales que conviene vigilar")
    for t, d in riesgos:
        finding_card(IC_RISK, C_RED, t, d)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# 7 — RECOMENDACIONES
# ═══════════════════════════════════════════════════════════════════════
recos = generar_recomendaciones(dff, activos)
section_header("Recomendaciones", "Próximas acciones sugeridas")
if recos:
    for t, d in recos:
        finding_card(IC_REC, GBS_PINK, t, d)
else:
    st.markdown(
        f'<div style="font-size:13px;color:{C_SLATE};padding:4px 0 8px">'
        f'El recorte es muy chico para recomendaciones confiables. Se recomienda ampliar los filtros para ver acciones '
        f'sugeridas.</div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# 8 — ANÁLISIS DE MERCADO Y PROYECCIÓN
# ═══════════════════════════════════════════════════════════════════════
section_header("Análisis de mercado y proyección", "Hacia dónde tracciona la demanda y qué esperar")

pos_df = dff[dff.positiva]
top_pais = pos_df.pais.value_counts()
top_ind = pos_df.industria.value_counts()

if len(pos_df) >= 5 and len(top_pais) and len(top_ind):
    pais_lider = top_pais.index[0]
    pais_share = top_pais.iloc[0] / top_pais.sum() * 100
    ind_lider = top_ind.index[0]
    ind_share = top_ind.iloc[0] / top_ind.sum() * 100
    finding_card(
        IC_GLOBE, GBS_PURPLE,
        f"La demanda traccciona en {pais_lider} y en {ind_lider}",
        f"{pais_lider} concentra el {fpct(pais_share,0)} de las respuestas positivas y "
        f"{ind_lider} el {fpct(ind_share,0)} entre las industrias. Es donde el mercado está "
        f"pidiendo externalizar logística con más fuerza: el foco natural para profundizar.")

# Proyección de campaña a partir del ritmo actual
if reuniones <= 2:
    # Arranque (mes 1): 2 reuniones agendadas pendientes de validación, base aún chica para proyectar
    finding_card(
        IC_UP, GBS_PURPLE,
        f"Fase de validación: {fmt(reuniones)} reuniones agendadas, pendientes de validación",
        f"El primer mes es de estrategia comercial y validación de la base de datos: se afinan "
        f"industrias, cargos, tipos de campaña y tipos de respuesta antes de escalar el agendamiento. "
        f"Con {fmt(reuniones)} reuniones agendadas (aún sin validar) la base es demasiado chica para "
        f"proyectar con confianza; la estimación hacia la garantía de {META_VALIDAS} reuniones válidas "
        f"se afina a medida que se agenden y validen más reuniones.")
else:
    on_track = validas_proy >= META_VALIDAS
    proy_color = C_GREEN if on_track else (C_AMBER if validas_proy >= META_VALIDAS * 0.7 else C_RED)
    proy_msg = ("por encima de la garantía" if on_track else
                "ajustada a la garantía" if validas_proy >= META_VALIDAS * 0.7 else
                "por debajo de la garantía")
    finding_card(
        IC_UP, proy_color,
        f"Proyección: ~{validas_proy} reuniones válidas a fin de campaña",
        f"Al ritmo de este recorte ({fmt(reuniones)} reuniones agendadas en {dias} días) se proyectan "
        f"~{fmt(reun_proy)} reuniones y ~{validas_proy} válidas en los 5 meses — {proy_msg} de "
        f"{META_VALIDAS}. La validación real del cliente irá ajustando esta estimación.")

st.caption("El bloque de avance de meta y los KPIs de validación se actualizan en tiempo real desde el "
           "reporte «Validación de reuniones» (hoy en 0; se completan a medida que el cliente califica). "
           "Las métricas del reporte, hallazgos y proyección se actualizan una vez al mes con el cierre "
           "del período.")

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# 9 — EJEMPLOS DE CAMPAÑA HIPERPERSONALIZADA
# ═══════════════════════════════════════════════════════════════════════
section_header("Ejemplos de campaña hiperpersonalizada",
               "El mensaje que recibe cada prospecto se adapta a su cargo, industria y canal")

st.markdown(
    f'<div style="background:#fff;border:1px solid {GBS_BORDER};border-radius:12px;'
    f'padding:16px 20px;font-size:13px;color:#334155;line-height:1.7;margin-bottom:14px">'
    f'Antes de escribir, cada prospecto se investiga uno por uno: <b>su perfil de LinkedIn</b>, '
    f'el <b>LinkedIn de la empresa</b>, el <b>sitio web</b>, la <b>industria</b> y el '
    f'<b>tipo de empresa</b>. Con eso el mensaje se arma a medida — no es una plantilla genérica. '
    f'Seleccionar un cargo, una industria y un canal para ver cómo cambia el mensaje.</div>',
    unsafe_allow_html=True,
)

# ── Filtros del segmento (mismos top 5 cargos e industrias que los filtros de arriba) ──
cc1, cc2, cc3 = st.columns(3)
with cc1:
    camp_cargo = st.selectbox("Cargo del prospecto", TOP_CARGOS, key="camp_cargo")
with cc2:
    camp_ind = st.selectbox("Industria del prospecto", TOP_INDUSTRIAS, key="camp_ind")
with cc3:
    camp_tipo = st.selectbox("Tipo de campaña", ["Ambas", "Correo", "WhatsApp"], key="camp_tipo")

# ── Contexto e identidad por industria (para hiperpersonalizar) ──
IND_HOOK = {
    "Minería y Metales": "importar maquinaria pesada y repuestos críticos con plazos que no admiten demoras",
    "Retail": "coordinar múltiples contenedores de varios orígenes y absorber los picos de temporada",
    "Automotriz": "traer autopartes con calendarios de producción que no toleran un solo día de retraso",
    "Alimentos y Bebidas": "mantener la cadena de frío y resolver los permisos sanitarios en cada importación",
    "Dispositivos Médicos":"asegurar la trazabilidad documental y los registros sanitarios de cada embarque",
}
IND_SAMPLE = {
    "Minería y Metales": ("Andina Metals", "Rodrigo Fuentes"),
    "Retail": ("Casa Bravo Retail", "Carolina Reyes"),
    "Automotriz": ("AutoPartes del Sur", "Diego Salinas"),
    "Alimentos y Bebidas": ("Frutos Andinos", "Valentina Ortiz"),
    "Dispositivos Médicos":("MediCare Import", "Felipe Cárdenas"),
}
hook = IND_HOOK[camp_ind]
empresa_pro, nombre_pro = IND_SAMPLE[camp_ind]
cargo_low = camp_cargo[0].lower() + camp_cargo[1:]

# ── Tarjeta CORREO ──
def _correo_card() -> str:
    asunto = f"{empresa_pro} + GBS — tu logística internacional en un solo punto"
    cuerpo = (
        f"Hola {nombre_pro},<br><br>"
        f"Vi en tu LinkedIn que lideras como <b>{cargo_low}</b> en {empresa_pro}, y revisando el sitio "
        f"web y el LinkedIn de la empresa noté que en <b>{camp_ind.lower()}</b> {hook}.<br><br>"
        f"Soy Sam Miller, de <b>GBS Logistics</b>, empresa de logística internacional. Ayudamos a Pymes "
        f"de {camp_ind.lower()} a manejar flete internacional, aduana, transporte local, seguro y "
        f"documentación con un <b>solo interlocutor</b> — sin perseguir a cinco proveedores distintos.<br><br>"
        f"¿Tendrías 15 minutos esta semana para mostrarte cómo lo resolvimos con empresas parecidas a "
        f"{empresa_pro}?<br><br>"
        f"Saludos,<br>Sam Miller · GBS Logistics"
    )
    return (
        f'<div style="background:#fff;border:1px solid {GBS_BORDER};border-radius:14px;overflow:hidden;'
        f'box-shadow:0 2px 8px rgba(124,58,237,.06)">'
        f'<div style="background:{GBS_PURPLE};color:#fff;padding:11px 18px;font-size:13px;font-weight:700;'
        f'display:flex;align-items:center;gap:8px">{_svg(IC_MAIL, "#fff", 16)} Correo electrónico</div>'
        f'<div style="padding:16px 20px">'
        f'<div style="font-size:11px;color:{C_SLATE};text-transform:uppercase;letter-spacing:.5px;'
        f'margin-bottom:2px">Asunto</div>'
        f'<div style="font-size:13px;font-weight:700;color:{GBS_DARK};margin-bottom:12px">{asunto}</div>'
        f'<div style="font-size:13px;color:#334155;line-height:1.65">{cuerpo}</div>'
        f'</div></div>'
    )

# ── Tarjeta WHATSAPP ──
def _whatsapp_card() -> str:
    cuerpo = (
        f"Hola {nombre_pro} Soy Sam Miller, de <b>GBS Logistics</b> (logística internacional).<br><br>"
        f"Vi tu perfil en LinkedIn como <b>{cargo_low}</b> en {empresa_pro} y, mirando la web y el "
        f"LinkedIn de la empresa, me imagino que en {camp_ind.lower()} {hook} les consume tiempo.<br><br>"
        f"Coordinamos flete, aduana, transporte local y seguro en un <b>solo punto de contacto</b>. "
        f"¿Te hace sentido una llamada corta esta semana?"
    )
    return (
        f'<div style="background:#fff;border:1px solid {GBS_BORDER};border-radius:14px;overflow:hidden;'
        f'box-shadow:0 2px 8px rgba(124,58,237,.06)">'
        f'<div style="background:#16a34a;color:#fff;padding:11px 18px;font-size:13px;font-weight:700;'
        f'display:flex;align-items:center;gap:8px">{_svg(IC_CHAT, "#fff", 16)} WhatsApp</div>'
        f'<div style="padding:16px 20px;background:#f0fdf4">'
        f'<div style="background:#dcfce7;border:1px solid #bbf7d0;border-radius:12px;border-top-left-radius:2px;'
        f'padding:12px 15px;font-size:13px;color:#14532d;line-height:1.6;max-width:96%">{cuerpo}'
        f'<div style="text-align:right;font-size:10px;color:#15803d;margin-top:6px">9:42 </div>'
        f'</div></div></div>'
    )

if camp_tipo == "Correo":
    st.markdown(_correo_card(), unsafe_allow_html=True)
elif camp_tipo == "WhatsApp":
    st.markdown(_whatsapp_card(), unsafe_allow_html=True)
else:
    colm, colw = st.columns(2)
    with colm:
        st.markdown(_correo_card(), unsafe_allow_html=True)
    with colw:
        st.markdown(_whatsapp_card(), unsafe_allow_html=True)

st.caption("Ejemplos ilustrativos: los nombres de contacto y empresa son de muestra. En la campaña real "
           "cada mensaje se genera con los datos verificados de cada prospecto.")
