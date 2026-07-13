"""Intelligence Insight DEMO: estrategia comercial y resultados, con datos ficticios.

Replica de la pagina interna de Intelligence Insight, en la paleta de
Conprospeccion. Se alimenta de shared/demo_intelligence.py en vez de Supabase.
Un unico "Cliente Demo"; empresas "Empresa Demo N". Ningun cliente real.

AISLAMIENTO: no importa requests, supabase, shared.config ni master_auth.
"""
from __future__ import annotations

import base64
import html
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from xhtml2pdf import pisa

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = ROOT / "dashboard"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from portal_auth import render_client_nav, require_auth_client
from shared.demo_intelligence import (
    META_VALIDAS,
    reuniones_detalle,
    reuniones_reales,
    snapshot,
)
from shared.cp_design import (
    CP_BG, CP_CARBON, CP_GOLD, CP_GOLD_SOFT, CP_GRAY, CP_GREEN, CP_GREEN_BG,
    CP_HEAT, CP_INK, CP_LINE, CP_LINE_STRONG, CP_MUTED, CP_MUTED_SURFACE,
    CP_ORANGE, CP_ORANGE_BG, CP_PURPLE, CP_PURPLE_BG, CP_RED, CP_RED_BG,
    CP_SURFACE, FONT_BODY, FONT_HEAD, FONT_IMPORT, FONT_MONO,
)

st.set_page_config(page_title="Demo — Intelligence Insight", layout="wide")
if not require_auth_client("demo"):
    st.stop()
render_client_nav("demo_intelligence.py", "demo")

st.markdown(
    """<style>
    header, [data-testid="stToolbar"], [data-testid="stDecoration"] { display:none !important; }
    .block-container{max-width:100%;padding:1rem 32px 2rem!important}
    </style>""",
    unsafe_allow_html=True,
)
st.markdown(f"<style>{FONT_IMPORT} .stApp{{font-family:{FONT_BODY}}}</style>", unsafe_allow_html=True)

SLUG = "demo"
ASSETS_DIR = DASHBOARD_DIR / "assets"


def _logo_b64(fname: str = "cp_mark_dark.png") -> str:
    p = ASSETS_DIR / fname
    if not p.exists():
        return ""
    ext = p.suffix.lstrip(".")
    d = base64.b64encode(p.read_bytes()).decode()
    return f'<img src="data:image/{ext};base64,{d}" height="28" style="object-fit:contain">'


_ESTADO_FINAL_LABEL = {
    "valida": "Válida", "reunion_valida": "Válida",
    "no_valida": "No válida", "reunion_no_valida": "No válida",
    "cancelacion": "Cancelada", "cancelada": "Cancelada",
    "reagendar": "Reagendar", "reagendada": "Reagendar",
    "pendiente": "Pendiente",
}

# El campo motivo_no_valida en Supabase trae texto generico ("ICP y Variables
# BANT") que no es claro para el reporte. Se reemplaza por una redaccion
# curada y consistente para las reuniones ya revisadas manualmente en el
# panel de Seguimiento (2026-07-07), sin mencionar BANT.
REAL = reuniones_reales()
META = META_VALIDAS
SNAP = snapshot()

REG = pd.DataFrame(SNAP["registros"])
REG["fecha"] = pd.to_datetime(REG["fecha"], errors="coerce").dt.date
CORREO = SNAP["correo"]
CANAL_ACTIVIDAD = pd.DataFrame(SNAP["canal_actividad"])
OBJ = SNAP["objetivo"]
POSITIVA_DESGLOSE = SNAP.get("positiva_desglose", {})
REUNIONES_SEGMENTO = SNAP.get("reuniones_por_segmento", [])
RES_LABEL = {
    "positiva": "Piden información o reunión", "deriva": "Derivan / refieren a un decisor",
    "negativa": "No interesado", "no_califica": "No cumple ICP objetivo",
    "reagendar": "Reagendar",
    "no_contesta": "En seguimiento (sin respuesta aún)", "numero_malo": "Contacto no válido (teléfono inexistente)",
}
EXCLUIR_SEG = {"Sin clasificar", "Otros"}


def subtipo_positiva(estado_raw: str) -> str:
    s = str(estado_raw or "").lower()
    if "reunión agendada" in s or "reunion agendada" in s:
        return "reunion_agendada"
    if "coordinando" in s:
        return "coordinando_reunion"
    return "informacion_adicional"


# ---------------- helpers de UI ----------------
def section(title, subtitle=""):
    st.markdown(
        f'<div style="border-left:4px solid {CP_GOLD};padding-left:13px;margin:24px 0 12px">'
        f'<div style="font-family:{FONT_HEAD};font-size:17px;font-weight:800;color:{CP_INK}">{title}</div>'
        + (f'<div style="font-size:12px;color:{CP_MUTED};margin-top:2px">{subtitle}</div>' if subtitle else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def scard(label, value, sub="", color=CP_CARBON, tip=""):
    t = f' title="{tip}"' if tip else ""
    return (
        f'<div{t} style="background:{CP_SURFACE};border:1px solid {CP_LINE};border-top:3px solid {color};'
        f'border-radius:10px;padding:12px 14px;text-align:center;min-height:84px">'
        f'<div style="font-family:{FONT_MONO};font-size:23px;font-weight:700;color:{color}">{value}</div>'
        f'<div style="font-size:10.5px;font-weight:700;color:{CP_INK};text-transform:uppercase;'
        f'letter-spacing:.3px;margin-top:5px">{label}</div>'
        + (f'<div style="font-size:10px;color:{CP_GRAY};margin-top:3px;line-height:1.3">{sub}</div>' if sub else "")
        + "</div>"
    )


def bars(rows, color):
    mx = max((v for _, v in rows), default=0) or 1
    return "".join(
        f'<div style="display:grid;grid-template-columns:250px 1fr 42px;gap:10px;align-items:center;margin:7px 0">'
        f'<span style="font-size:12px;text-align:right;color:{CP_CARBON}">{n}</span>'
        f'<div style="height:22px;background:{CP_MUTED_SURFACE};border-radius:7px;overflow:hidden">'
        f'<div style="height:100%;width:{max(4, round(v / mx * 100))}%;background:{color};border-radius:7px"></div></div>'
        f'<b style="font-size:12px;color:{CP_CARBON}">{v}</b></div>'
        for n, v in rows
    )


def conteo(df, *res):
    return int(df.resultado.isin(res).sum())


def top_tabla(df, dim):
    rows = []
    for key, sub in df.groupby(dim):
        if key in EXCLUIR_SEG:
            continue
        pos = int(sub.resultado.isin(["positiva", "deriva"]).sum())
        conv = int((~sub.resultado.isin(["no_contesta", "numero_malo", "no_califica"])).sum())
        tasa = pos / conv if conv else 0
        rows.append((key, len(sub), conv, pos, tasa))
    rows.sort(key=lambda r: (-r[3], -r[2], -r[1]))
    rows = rows[:5]
    body = (
        '<div style="display:grid;grid-template-columns:1fr 72px 100px 62px 58px;gap:8px;'
        f'padding:0 4px 7px;border-bottom:1px solid {CP_LINE};font-size:10px;font-weight:700;'
        f'text-transform:uppercase;color:{CP_MUTED}">'
        '<span>Segmento</span><span>Gestiones</span><span>Conversaciones</span>'
        '<span>Positivas</span><span>Tasa</span></div>'
    )
    for name, gest, conv, pos, tasa in rows:
        body += (
            '<div style="display:grid;grid-template-columns:1fr 72px 100px 62px 58px;gap:8px;'
            f'padding:9px 4px;border-bottom:1px solid {CP_LINE};font-size:11.5px;align-items:center">'
            f'<b style="color:{CP_CARBON}">{name}</b><span>{gest}</span><span>{conv}</span>'
            f'<span style="color:{CP_GREEN};font-weight:800">{pos}</span>'
            f'<span style="color:{CP_GREEN};font-weight:800">{tasa:.0%}</span></div>'
        )
    empty = (
        f"<span style='font-size:12px;color:{CP_MUTED}'>"
        "Todavía no hay muestra suficiente para comparar este segmento."
        "</span>"
    )
    content = body if rows else empty
    return (f'<div style="background:{CP_SURFACE};border:1px solid {CP_LINE};border-radius:11px;'
            f'padding:14px 16px">{content}</div>'), rows


def segment_matrix(df, reuniones_conteo: Counter):
    rows = []
    for (industry, area), sub in df.groupby(["industria", "area"]):
        if industry in EXCLUIR_SEG or area in EXCLUIR_SEG:
            continue
        accounts = int(sub["empresa"].replace("", pd.NA).nunique())
        conversations = int((~sub.resultado.isin(["no_contesta", "numero_malo", "no_califica"])).sum())
        positive = conteo(sub, "positiva", "deriva")
        meetings = reuniones_conteo.get((industry, area), 0)
        rate = positive / conversations if conversations else 0
        if meetings >= 2:
            signal, decision = "Alta oportunidad", "Aumentar cobertura"
        elif meetings == 1 or positive >= 2:
            signal, decision = "Oportunidad media", "Mantener y ampliar"
        elif conversations >= 5:
            signal, decision = "Exploratorio", "Testear segunda muestra"
        else:
            signal, decision = "Muestra insuficiente", "Ampliar muestra"
        rows.append({
            "Macroindustria": industry, "Macrocargo": area, "Cuentas activadas": accounts,
            "Conversaciones": conversations, "Positivas": positive,
            "Tasa positiva": rate, "Reuniones": meetings,
            "Señal": signal, "Decisión": decision,
        })
    return pd.DataFrame(rows).sort_values(
        ["Reuniones", "Positivas", "Conversaciones"], ascending=False
    ) if rows else pd.DataFrame()


def insight_row(insight, evidence, implication, action):
    return {"Insight": insight, "Evidencia": evidence,
            "Implicancia": implication, "Acción recomendada": action}


def html_table(df: pd.DataFrame, *, small: bool = True) -> str:
    if df is None or df.empty:
        return (
            f'<div style="padding:13px;background:{CP_MUTED_SURFACE};color:{CP_MUTED};'
            f'border:1px dashed {CP_LINE_STRONG};border-radius:10px">Sin registros para la selección activa.</div>'
        )
    font = "11px" if small else "12px"
    out = [
        '<div style="overflow-x:auto;width:100%">',
        '<table style="width:100%;border-collapse:collapse;background:#fff;table-layout:fixed;'
        f'font-size:{font};line-height:1.4;border:1px solid {CP_LINE};border-radius:9px;overflow:hidden">',
        "<thead><tr>",
    ]
    for col in df.columns:
        out.append(
            f'<th style="background:{CP_MUTED_SURFACE};color:{CP_MUTED};text-align:left;padding:9px 8px;'
            f'border:1px solid {CP_LINE};font-weight:700;white-space:normal;word-break:normal;overflow-wrap:break-word">'
            f"{html.escape(str(col))}</th>"
        )
    out.append("</tr></thead><tbody>")
    for _, row in df.iterrows():
        out.append("<tr>")
        for value in row:
            out.append(
                f'<td style="padding:8px;border:1px solid {CP_LINE};vertical-align:top;'
                'white-space:normal;overflow-wrap:break-word;word-break:break-word">'
                f"{html.escape(str(value))}</td>"
            )
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


# ================= HEADER =================
_ini = pd.to_datetime(SNAP["periodo"]["inicio"]).date()
_fin_periodo = pd.to_datetime(SNAP["periodo"]["fin"]).date()
_logo = _logo_b64()
st.markdown(
    f'<div style="background:{CP_CARBON};color:#fff;border-radius:0 0 12px 12px;padding:16px 22px;'
    f'display:flex;align-items:center;justify-content:space-between;box-shadow:0 10px 24px rgba(26,26,26,.14)">'
    f'<div style="display:flex;align-items:center;gap:14px">'
    f'{_logo}'
    f'<div><div style="font-family:{FONT_HEAD};font-size:19px;font-weight:800;line-height:1.1">Intelligence Insight · Cliente Demo</div>'
    f'<div style="font-size:12px;color:#C9C9C6;margin-top:2px">Prospección multicanal · Ciclo del mes en curso</div></div></div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ===== Avance de meta =====
pct_meta = round(REAL["validas"] / META * 100) if META else 0
st.markdown(
    f'<div style="display:flex;align-items:center;gap:14px;background:{CP_SURFACE};border:1px solid {CP_LINE};'
    f'border-radius:11px;padding:11px 18px;margin:14px 0 10px">'
    f'<span style="font-size:12px;font-weight:800;color:{CP_CARBON};white-space:nowrap">AVANCE DE LA META</span>'
    f'<div style="flex:1;height:14px;background:{CP_MUTED_SURFACE};border-radius:8px;overflow:hidden">'
    f'<div style="height:100%;width:{max(pct_meta, 2)}%;background:linear-gradient(90deg,{CP_GOLD},{CP_ORANGE})"></div></div>'
    f'<span style="font-family:{FONT_MONO};font-size:14px;font-weight:700;color:{CP_CARBON};white-space:nowrap">'
    f'{REAL["validas"]} / {META} <span style="color:{CP_GRAY};font-weight:600">({pct_meta}%)</span></span></div>',
    unsafe_allow_html=True,
)

mc1, mc2 = st.columns([4, 1])
mc1.markdown(
    f'<div style="font-size:12px;color:{CP_CARBON};padding:7px 2px">'
    f'<b>{REAL["total"]} reuniones registradas</b> · {REAL["validas"]} válidas para la meta. '
    f'La evaluación contractual definitiva se consulta en el panel de Seguimiento de Reuniones.</div>',
    unsafe_allow_html=True,
)
if mc2.button("Ver seguimiento →", key="goto_seg", use_container_width=True):
    st.switch_page("pages/demo_reuniones.py")

st.markdown(
    f'<div style="background:{CP_GOLD_SOFT};border:1px solid #F0D28D;border-left:5px solid {CP_GOLD};'
    f'border-radius:10px;padding:11px 17px;margin:12px 0;font-size:13px;color:#5A4A00">'
    f'<b>Este ciclo fue de estrategia.</b> Probamos prospección multicanal sobre '
    f'empresas de distintas industrias y áreas para detectar dónde y con qué mensaje '
    f'responde mejor el mercado al servicio del Cliente Demo. Se ajustó el ICP durante el ciclo '
    f'(se retiraron cuentas fuera de perfil), por eso el universo total de este consolidado '
    f'es más acotado y las tasas de respuesta se ven más nítidas.</div>',
    unsafe_allow_html=True,
)

# ===== Panel maestro de filtros cruzados =====
valid_dates = REG["fecha"].dropna()
min_date = _ini
max_date = _fin_periodo
with st.container(border=True):
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;gap:14px;align-items:center;margin-bottom:5px">'
        f'<div><div style="font-family:{FONT_HEAD};font-size:17px;font-weight:800;color:{CP_INK}">Control del análisis</div>'
        f'<div style="font-size:12px;color:{CP_MUTED}">Cada ajuste recalcula todas las métricas, tablas, '
        'heatmaps, insights y recomendaciones que aparecen debajo.</div></div>'
        f'<span style="background:{CP_GOLD_SOFT};color:#7A6400;border:1px solid #F0D28D;border-radius:999px;'
        'padding:5px 11px;font-size:10px;font-weight:800;white-space:nowrap">FILTROS GLOBALES</span></div>',
        unsafe_allow_html=True,
    )
    fc = st.columns([1.2, 1.4, 1.4])
    period = fc[0].date_input(
        "Período", value=(min_date, max_date), min_value=min_date, max_value=max_date, format="DD/MM/YYYY",
    )
    start_date, end_date = (
        period if isinstance(period, (tuple, list)) and len(period) == 2 else (min_date, max_date)
    )
    date_base = REG[REG["fecha"].between(start_date, end_date, inclusive="both")]
    f_ind = fc[1].selectbox(
        "Macroindustria",
        ["Todas"] + sorted(x for x in date_base["industria"].dropna().unique() if str(x).strip()),
    )
    base_area = date_base if f_ind == "Todas" else date_base[date_base["industria"] == f_ind]
    f_area = fc[2].selectbox(
        "Macrocargo (área)",
        ["Todas"] + sorted(x for x in base_area["area"].dropna().unique() if str(x).strip()),
    )
    st.markdown(
        f'<div style="font-size:11px;color:{CP_MUTED};margin-top:2px">'
        f'Vista activa: <b>{start_date:%d/%m/%Y}-{end_date:%d/%m/%Y}</b> · '
        f'<b>{f_ind}</b> · <b>{f_area}</b></div>',
        unsafe_allow_html=True,
    )

REGf = date_base.copy()
if f_ind != "Todas": REGf = REGf[REGf.industria == f_ind]
if f_area != "Todas": REGf = REGf[REGf.area == f_area]

fp, fd = conteo(REGf, "positiva"), conteo(REGf, "deriva")
fneg = conteo(REGf, "negativa")
fnocalifica = conteo(REGf, "no_califica")
fnoc, fmalo = conteo(REGf, "no_contesta"), conteo(REGf, "numero_malo")
fconv = len(REGf) - fnoc - fmalo - fnocalifica
fpostot = fp + fd

# ===== Resumen filtrado =====
section("Resumen del ciclo", "Las métricas responden a los filtros seleccionados")
tasa = fpostot / fconv if fconv else 0
rs = st.columns(4)
rs[0].markdown(scard("Gestiones", len(REGf), "Registros dentro del filtro"), unsafe_allow_html=True)
rs[1].markdown(scard("Conversaciones", fconv, "Excluye sin respuesta, contacto no válido y fuera de ICP"), unsafe_allow_html=True)
rs[2].markdown(scard("Respuestas positivas", fpostot, f"{fp} interés directo + {fd} derivaciones", CP_GREEN), unsafe_allow_html=True)
rs[3].markdown(scard("Tasa positiva", f"{tasa:.0%}", "Positivas / conversaciones", CP_GREEN), unsafe_allow_html=True)
st.caption(
    f"Base de gestión del ciclo: {SNAP['universo_unico']:,} contactos únicos. "
    "Las métricas superiores corresponden a la gestión con resultado registrado."
)

# ===== Volumen de gestión por canal =====
section("Volumen de gestión por canal", "Un mismo contacto puede haber sido gestionado por más de un canal")
st.dataframe(CANAL_ACTIVIDAD.rename(columns={"canal": "Canal", "gestiones": "Gestiones"}),
             hide_index=True, use_container_width=True)
st.caption(
    "Estos volúmenes no son mutuamente excluyentes: una misma empresa puede haber sido contactada "
    "por más de un canal durante el ciclo. Los resultados de conversación (más abajo) se analizan "
    "de forma agregada, sin desglosar conversión por canal."
)

# ===== Resultados de conversación =====
section("Resultados de conversación", "Cómo respondió el mercado durante el ciclo")
pos_desglose_txt = (
    f"Información adicional: {POSITIVA_DESGLOSE.get('informacion_adicional', 0)} · "
    f"Coordinando reunión: {POSITIVA_DESGLOSE.get('coordinando_reunion', 0)} · "
    f"Reunión agendada: {POSITIVA_DESGLOSE.get('reunion_agendada', 0)}"
)
res_rows = [(RES_LABEL[k], conteo(REGf, k)) for k in
            ["positiva", "deriva", "negativa", "no_califica", "no_contesta", "numero_malo"]]
res_rows_sorted = sorted([(n, v) for n, v in res_rows if v > 0], key=lambda row: row[1], reverse=True)
st.caption("Ordenado de mayor a menor por cantidad de respuestas dentro de la vista activa.")
st.markdown(bars(res_rows_sorted, CP_CARBON), unsafe_allow_html=True)
st.markdown(
    f'<div style="display:flex;gap:9px;flex-wrap:wrap;margin-top:9px;font-size:12px;font-weight:700">'
    f'<span style="background:{CP_GREEN_BG};color:{CP_GREEN};padding:4px 11px;border-radius:9px">'
    f'Positivas: {fpostot}{f" ({fpostot / fconv:.0%})" if fconv else ""}</span>'
    f'<span style="background:{CP_PURPLE_BG};color:{CP_PURPLE};padding:4px 11px;border-radius:9px">Derivaciones: {fd}</span>'
    f'<span style="background:{CP_RED_BG};color:{CP_RED};padding:4px 11px;border-radius:9px">No interesado: {fneg}</span>'
    f'<span style="background:{CP_ORANGE_BG};color:{CP_ORANGE};padding:4px 11px;border-radius:9px">No cumple ICP: {fnocalifica}</span>'
    f'<span style="background:{CP_MUTED_SURFACE};color:{CP_GRAY};padding:4px 11px;border-radius:9px">En seguimiento: {fnoc}</span>'
    f'</div>',
    unsafe_allow_html=True,
)
st.caption(
    f"Positivas = piden información adicional, están coordinando reunión o ya tienen reunión agendada "
    f"({pos_desglose_txt}). 'No cumple ICP objetivo' es distinto de 'no interesado': significa que el "
    "contacto no calza con el perfil buscado (tamaño, país, industria), no que haya rechazado "
    "la propuesta; por eso se excluye del cálculo de tasa positiva junto con contacto no válido y sin respuesta."
)

# ===== Reuniones y cotizaciones del ciclo =====
reuniones_df = reuniones_detalle()
section(
    "Reuniones y cotizaciones del ciclo",
    f"Las {len(reuniones_df)} reuniones/cotizaciones registradas, con su estado final y motivo cuando aplica",
)
if reuniones_df.empty:
    st.info("Aún no hay reuniones registradas para este ciclo.")
else:
    st.dataframe(reuniones_df, hide_index=True, use_container_width=True)
    st.caption(
        "Estado final validado en el panel de Seguimiento de Reuniones. \"Motivo\" solo aparece "
        "cuando la reunión no fue válida o se canceló (por ejemplo, ICP incorrecto)."
    )

# ===== Reuniones por segmento =====
section(
    "Reuniones por segmento",
    "Cantidad de reuniones agendadas por cruce de industria del prospecto y área que decide la compra",
)
reuniones_counter = Counter(
    (r["industria"], r["area"]) for r in REUNIONES_SEGMENTO
    if (f_ind == "Todas" or r["industria"] == f_ind) and (f_area == "Todas" or r["area"] == f_area)
)
segments = segment_matrix(REGf, reuniones_counter)
segments = segments[segments["Reuniones"] >= 1] if not segments.empty else segments
if segments.empty:
    st.info("Todavía no hay segmentos con reunión agendada en esta combinación de filtros.")
else:
    heat = alt.Chart(segments).mark_rect(cornerRadius=4).encode(
        x=alt.X("Macrocargo:N", title="Macrocargo (área)", axis=alt.Axis(labelAngle=0, labelLimit=160, labelPadding=8)),
        y=alt.Y("Macroindustria:N", title="Macroindustria"),
        color=alt.Color("Reuniones:Q", title="Reuniones",
                        scale=alt.Scale(domain=[0, 1, 2, 4], range=CP_HEAT)),
        tooltip=["Macroindustria", "Macrocargo", "Reuniones"],
    ).properties(height=max(260, 38 * segments["Macroindustria"].nunique()))
    st.altair_chart(heat, use_container_width=True)

# ===== Top industrias y cargos =====
section("Top 5 industrias y cargos", "Rankings recalculados según los filtros superiores, ordenados por respuestas positivas")
si, sa = st.columns(2)
with si:
    st.markdown("<b style='font-size:12.5px'>Top 5 macro-industrias</b>", unsafe_allow_html=True)
    html_i, rows_i = top_tabla(REGf, "industria")
    st.markdown(html_i, unsafe_allow_html=True)
with sa:
    st.markdown("<b style='font-size:12.5px'>Top 5 macro-cargos (áreas)</b>", unsafe_allow_html=True)
    html_a, rows_a = top_tabla(REGf, "area")
    st.markdown(html_a, unsafe_allow_html=True)
    with st.expander("¿Qué es un macro-cargo (área)?"):
        st.caption("Agrupamos los cientos de cargos en áreas funcionales (Abastecimiento, "
                   "Operaciones, Dirección, Finanzas, Comercial, Logística, TI) para definir estrategia por área.")
st.markdown(
    f'<div style="background:{CP_MUTED_SURFACE};border:1px solid {CP_LINE};border-radius:10px;'
    f'padding:11px 14px;margin-top:10px;font-size:12px;color:{CP_CARBON};line-height:1.55">'
    f'<b>Por qué avanzamos más en ciertas industrias:</b> Las industrias con mayor '
    'inversión y crecimiento en el período concentran más iniciativas nuevas, y con ellas más '
    'necesidad de proveedores. Es coherente con la experiencia previa de Conprospección: estos '
    'sectores tienden a responder mejor cuando el mensaje es de eficiencia y continuidad operativa, '
    'no de precio.</div>',
    unsafe_allow_html=True,
)

# ===== Qué aprendimos del mercado =====
section("Qué aprendimos del mercado", "Cada lectura conecta evidencia, implicancia y una acción")
learning_rows = []
if not segments.empty:
    reliable = segments[(segments["Reuniones"] >= 1) | (segments["Conversaciones"] >= 5)]
    lead = (reliable if not reliable.empty else segments).iloc[0]
    learning_rows.append(insight_row(
        f"Mayor señal en {lead['Macroindustria']} + {lead['Macrocargo']}",
        f"{lead['Conversaciones']} conversaciones, {lead['Positivas']} positivas y "
        f"{lead['Reuniones']} reuniones agendadas en este segmento.",
        "La oportunidad depende de combinar contexto industrial y área compradora, no solo de una tasa aislada.",
        lead["Decisión"],
    ))
learning_rows.append(insight_row(
    "La decisión la toma la gerencia, pero la operan otras áreas",
    f"La vista contiene {REGf['area'].nunique()} áreas funcionales con actividad; Dirección/Gerencia concentra el volumen.",
    "La compra involucra a Gerencia (decide), Abastecimiento/Operaciones y las áreas técnicas (operan).",
    "Buscar 2-3 perfiles por cuenta prioritaria y comparar respuesta por área.",
))
learning_rows.append(insight_row(
    "El ajuste de ICP redujo el universo pero mejoró la calidad de respuesta",
    "Se retiraron del ciclo cuentas fuera de perfil (tamaño o encaje insuficiente).",
    "Un universo más chico y mejor calificado concentra la conversación en cuentas con más probabilidad real de avanzar.",
    "Mantener el ICP ajustado y aplicar el mismo filtro antes de cargar el próximo lote.",
))
st.markdown(html_table(pd.DataFrame(learning_rows)), unsafe_allow_html=True)

# ===== Mensajes y dolores =====
section("Mensajes y dolores que están resonando",
        "Tema asociado a la campaña; es una inferencia analítica, no una transcripción del prospecto")
theme_rows = []
for theme, sub in REGf.groupby("tema"):
    accounts = int(sub["empresa"].replace("", pd.NA).nunique())
    conversations = int((~sub.resultado.isin(["no_contesta", "numero_malo", "no_califica"])).sum())
    positives = conteo(sub, "positiva", "deriva")
    best_industry = (
        sub[sub.resultado.isin(["positiva", "deriva"])]["industria"].value_counts().index[0]
        if positives else "Sin señal suficiente"
    )
    rate = positives / conversations if conversations else 0
    recommendation = (
        "Usar como mensaje principal" if conversations >= 8 and rate >= .3
        else "Mantener y ampliar muestra" if positives >= 2
        else "Testear con mayor especificidad"
    )
    theme_rows.append({
        "Tema": theme, "Cuentas impactadas": accounts, "Conversaciones": conversations,
        "Positivas": positives, "Tasa positiva": f"{rate:.0%}",
        "Mejor industria": best_industry, "Recomendación": recommendation,
    })
theme_df = pd.DataFrame(theme_rows).sort_values(
    ["Positivas", "Cuentas impactadas", "Conversaciones"], ascending=False
) if theme_rows else pd.DataFrame()
st.caption("Ordenado por respuestas positivas, luego cuentas impactadas y conversaciones.")
if theme_df.empty:
    st.info("Todavía no hay muestra suficiente para comparar mensajes dentro de esta selección.")
else:
    st.markdown(html_table(theme_df), unsafe_allow_html=True)
    theme_lead = theme_df.iloc[0]
    st.success(
        f"Insight: **{theme_lead['Tema']}** concentra la mayor señal observable "
        f"({theme_lead['Positivas']} positivas). Conviene validar con copy etiquetado por tema en el próximo ciclo."
    )

# ===== Negativas y objeciones =====
section("Negativas y objeciones", "Las respuestas de \"no interesado\" también orientan segmentación y copy")
negative = REGf[REGf.resultado == "negativa"].copy()
objection_rows = []
for objection, sub in negative.groupby("estado_raw"):
    top_industrias = sub["industria"].value_counts().head(3)
    industrias_txt = ", ".join(f"{ind} ({n})" for ind, n in top_industrias.items()) if not sub.empty else "-"
    objection_rows.append({
        "Objeción": objection, "Cantidad": len(sub), "Industrias más frecuentes": industrias_txt,
        "Lectura": "Ya cuenta con un proveedor vigente o no es prioridad en este momento.",
        "Acción": "Reforzar la propuesta de valor diferenciada y programar un recontacto "
                  "en el próximo trimestre.",
    })
if objection_rows:
    st.caption(
        "Se muestran hasta 3 industrias por objeción para no atribuirla solo a la industria con más volumen."
    )
    st.dataframe(pd.DataFrame(objection_rows), hide_index=True, use_container_width=True)
else:
    st.info("No hay contactos de \"no interesado\" dentro de la combinación de filtros seleccionada.")

# ===== Contexto de mercado =====
section("Contexto de mercado relevante", "Señales del rubro para interpretar los datos; no sustituyen los de campaña")
market_context = pd.DataFrame([
    {
        "Tendencia": "La inversión en las industrias objetivo sigue en expansión",
        "Por qué importa para el cliente": "Más iniciativas y proyectos nuevos significan más "
                                           "necesidad de proveedores y más ventanas de decisión abiertas.",
        "Segmentos conectados": "Minería y Metales, Manufactura",
        "Fuente": "Datos de mercado del período (ejemplo ilustrativo)",
    },
    {
        "Tendencia": "La digitalización acelera en el mercado medio",
        "Por qué importa para el cliente": "Las empresas medianas están profesionalizando "
                                           "procesos, lo que abre conversación sobre eficiencia y control.",
        "Segmentos conectados": "Tecnología, Servicios Financieros, Retail y Consumo",
        "Fuente": "Datos de mercado del período (ejemplo ilustrativo)",
    },
    {
        "Tendencia": "Presión por eficiencia operativa en industrias tradicionales",
        "Por qué importa para el cliente": "Los sectores con márgenes ajustados priorizan "
                                           "reducir costos y ganar visibilidad, el ángulo que mejor responde.",
        "Segmentos conectados": "Alimentos y Bebidas, Construcción",
        "Fuente": "Datos de mercado del período (ejemplo ilustrativo)",
    },
])
st.markdown(html_table(market_context), unsafe_allow_html=True)
st.caption(
    "Contexto de mercado ilustrativo (datos de demostración), cruzado con la respuesta "
    "observada durante el ciclo."
)

# ===== Próximos pasos =====
section("Próximos pasos", "Plan ejecutivo conectado con los datos y la hipótesis del próximo ciclo")
lead_segment = None if segments.empty else segments.iloc[0]
lead_text = (
    f"{lead_segment['Macroindustria']} + {lead_segment['Macrocargo']}"
    if lead_segment is not None else "los segmentos que alcancen muestra suficiente"
)
next_steps = pd.DataFrame([
    {
        "Decisión": "Concentrar prospección",
        "Acción Conprospección": f"Ampliar la muestra de {lead_text} sin declarar ganador hasta superar el umbral de confianza.",
        "Indicador": "Reuniones agendadas y positivas por segmento",
    },
    {
        "Decisión": "Multithreading por cuenta",
        "Acción Conprospección": "Sumar Abastecimiento/Operaciones y el área técnica además de Gerencia en cada cuenta prioritaria.",
        "Indicador": "2-3 áreas activadas por cuenta",
    },
    {
        "Decisión": "Blindar la lista de exclusión de clientes activos",
        "Acción Conprospección": "Revisar y cruzar la lista de clientes activos del cliente contra cada nueva carga "
                                  "de contactos antes de lanzar campaña, para que no vuelva a ocurrir.",
        "Indicador": "Cero clientes activos recontactados por campaña",
    },
    {
        "Decisión": "Retomar el listado de cuentas objetivo",
        "Acción Conprospección": f"Priorizar la prospección de la lista de cuentas objetivo entregada por el cliente "
                                  f"({OBJ['total']} empresas) en el próximo lote.",
        "Indicador": "Cuentas objetivo activadas",
    },
    {
        "Decisión": "Vender el dolor, no el producto",
        "Acción Conprospección": "Separar el copy por tema de valor (eficiencia, visibilidad, integración) y medir cuál convierte.",
        "Indicador": "Tasa positiva por tema de mensaje",
    },
])
st.markdown(html_table(next_steps), unsafe_allow_html=True)
st.markdown(
    f'<div style="background:{CP_GOLD_SOFT};border:1px solid #F0D28D;border-left:5px solid {CP_GOLD};'
    f'border-radius:11px;padding:15px 18px;margin-top:12px;font-size:13px;line-height:1.65;color:#5A4A00">'
    f'<b>Hipótesis del ciclo 2:</b> Las empresas de las industrias con mayor señal, contactadas desde '
    f'Gerencia y luego Abastecimiento/Operaciones, responderán mejor a mensajes de eficiencia y visibilidad '
    f'que a un mensaje genérico de producto.<br><b>Cómo lo vamos a validar:</b> En el próximo ciclo '
    f'compararemos la tasa positiva y las reuniones agendadas de este segmento contra el resto, una vez que '
    f'acumule más volumen de conversaciones.</div>',
    unsafe_allow_html=True,
)


# ===== Descargas =====
def report_table(df):
    if df is None or df.empty:
        return '<div class="empty">Sin registros para la selección activa.</div>'
    # xhtml2pdf calcula el ancho de columna por contenido e ignora tanto
    # table-layout:fixed como el width por CSS en <col>; solo respeta el
    # atributo HTML width (no el style), asi que se usa ese para forzar un
    # ancho parejo y que ninguna columna se salga de la pagina. Ademas, si
    # una columna tiene celdas realmente vacias, xhtml2pdf ignora el ancho
    # fijado y comprime esa columna por contenido (se ve recortada); por eso
    # se rellenan las vacias con un espacio duro antes de generar la tabla.
    df = df.replace("", "-").fillna("-")
    width_pct = round(100 / len(df.columns), 2)
    colgroup = "<colgroup>" + "".join(f'<col width="{width_pct}%">' for _ in df.columns) + "</colgroup>"
    table_html = df.to_html(index=False, border=0, classes="report-table", escape=True)
    return table_html.replace('<table class="dataframe report-table">',
                              f'<table class="dataframe report-table">{colgroup}', 1)


def _pdf_css() -> str:
    # xhtml2pdf no soporta grid/flexbox: layout con tablas y bloques simples.
    # "-pdf-keep-with-next" evita que un titulo quede solo al final de pagina.
    return f"""
@page {{ size: A4; margin: 1.7cm 1.4cm; }}
*{{box-sizing:border-box}}
body{{font-family:Helvetica,Arial,sans-serif;color:{CP_INK};line-height:1.45;font-size:10.5px;margin:0}}
.hero{{background:{CP_CARBON};color:#fff;padding:16px 20px;border-radius:8px;margin-bottom:12px}}
.hero h1{{margin:0;font-size:19px}} .hero p{{margin:5px 0 0;color:#C9C9C6;font-size:10px}}
.filter{{margin:0 0 12px;padding:9px 13px;border:1.4px solid {CP_GOLD};background:{CP_GOLD_SOFT};border-radius:7px;font-size:10px}}
.kpis-table{{width:100%;border-collapse:separate;border-spacing:6px 0;margin:8px 0 4px}}
.kpi{{background:#fff;border:1px solid {CP_LINE};border-top:3px solid {CP_GOLD};border-radius:7px;padding:9px;text-align:center}}
.kpi strong{{display:block;font-size:16px;color:{CP_CARBON}}}
.kpi span{{font-size:8px;text-transform:uppercase;font-weight:700;color:{CP_INK}}}
h2{{font-size:13.5px;border-left:4px solid {CP_GOLD};padding-left:8px;margin:14px 0 6px;-pdf-keep-with-next:true}}
.report-table{{width:100%;table-layout:fixed;border-collapse:collapse;background:#fff;font-size:9px;margin:0 0 10px}}
.report-table th{{background:{CP_MUTED_SURFACE};color:{CP_CARBON};text-align:left;padding:5px;border:1px solid {CP_LINE};word-wrap:break-word;overflow-wrap:break-word}}
.report-table td{{padding:5px;border:1px solid {CP_LINE};vertical-align:top;word-wrap:break-word;overflow-wrap:break-word}}
.note{{background:{CP_GOLD_SOFT};border-left:4px solid {CP_GOLD};padding:9px 11px;border-radius:6px;font-size:9.5px;margin-bottom:10px}}
.method{{font-size:8.5px;color:{CP_MUTED};background:#fff;padding:7px 9px;border:1px solid {CP_LINE};border-radius:6px;margin-bottom:10px}}
.empty{{padding:8px;background:{CP_MUTED_SURFACE};color:{CP_MUTED};border:1px dashed {CP_LINE_STRONG};font-size:9px}}
a{{color:{CP_ORANGE}}}
"""


def informe_html():
    segment_report = segments.copy()
    if not segment_report.empty:
        segment_report["Segmento"] = segment_report["Macroindustria"] + " + " + segment_report["Macrocargo"]
        segment_report["Tasa positiva"] = segment_report["Tasa positiva"].map(lambda x: f"{x:.0%}")
        segment_report = segment_report[[
            "Segmento", "Cuentas activadas", "Conversaciones", "Positivas",
            "Tasa positiva", "Reuniones", "Señal", "Decisión",
        ]].head(10)
    results_report = pd.DataFrame([
        {"Resultado": RES_LABEL[key], "Cantidad": conteo(REGf, key)}
        for key in ["positiva", "deriva", "negativa", "no_califica", "no_contesta", "numero_malo"]
    ]).sort_values("Cantidad", ascending=False)
    kpis = [
        ("Gestiones", len(REGf)), ("Conversaciones", fconv),
        ("Respuestas positivas", fpostot), ("Tasa positiva", f"{tasa:.0%}"),
    ]
    kpi_html = "<table class='kpis-table'><tr>" + "".join(
        f"<td style='width:25%'><div class='kpi'><strong>{value}</strong><span>{label}</span></div></td>"
        for label, value in kpis
    ) + "</tr></table>"
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<title>Cliente Demo - Intelligence Insight</title>
<style>{_pdf_css()}</style></head><body>
<div class="hero"><h1>Intelligence Insight - Cliente Demo</h1>
<p>Reporte del ciclo comercial - vista de demostración de Conprospección</p></div>
<div class="filter"><b>Selección exportada:</b> {start_date:%d/%m/%Y}-{end_date:%d/%m/%Y} ·
Macroindustria: {f_ind} · Macrocargo: {f_area}</div>
<h2>Resumen ejecutivo</h2>
{kpi_html}
<div class="note"><b>Avance contractual:</b> {REAL['validas']} de {META} reuniones válidas ({pct_meta}%).</div>
<h2>Volumen de gestión por canal</h2>{report_table(CANAL_ACTIVIDAD.rename(columns={"canal": "Canal", "gestiones": "Gestiones"}))}
<div class="method">Un mismo contacto puede haber sido gestionado por más de un canal; estos volúmenes no son mutuamente excluyentes.</div>
<h2>Resultados de conversación</h2>{report_table(results_report)}
<div class="method">Positivas = información adicional + coordinando reunión + reunión agendada ({pos_desglose_txt}).</div>
<h2>Reuniones y cotizaciones del ciclo</h2>{report_table(reuniones_df)}
<h2>Reuniones por segmento</h2>{report_table(segment_report if not segments.empty else pd.DataFrame())}
<h2>Qué aprendimos del mercado</h2>{report_table(pd.DataFrame(learning_rows))}
<h2>Mensajes y dolores que están resonando</h2>{report_table(theme_df)}
<h2>Negativas y objeciones</h2>{report_table(pd.DataFrame(objection_rows))}
<h2>Contexto de mercado relevante</h2>{report_table(market_context)}
<h2>Próximos pasos</h2>{report_table(next_steps)}
<div class="note"><b>Hipótesis del ciclo 2:</b> las empresas de las industrias con mayor señal, contactadas desde
Gerencia y luego Abastecimiento/Operaciones, responderán mejor a mensajes de eficiencia y visibilidad.</div>
</body></html>"""


def construir_pdf() -> bytes:
    """Genera el PDF a partir del MISMO HTML del informe (mismos colores y
    layout), en vez de reconstruir el diseño a mano con FPDF."""
    import io
    buffer = io.BytesIO()
    pisa.CreatePDF(informe_html(), dest=buffer)
    return buffer.getvalue()


st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
section("Descargas del reporte", "Exporta la misma lectura ejecutiva en HTML o PDF")
st.markdown(
    f'<style>div[class*="st-key-dl_demo_html"] button,div[class*="st-key-dl_demo_pdf"] button{{background:{CP_GOLD}!important;'
    f'border-color:{CP_GOLD}!important;color:{CP_INK}!important;font-weight:800!important}}</style>',
    unsafe_allow_html=True,
)
dl1, dl2 = st.columns(2)
with dl1:
    st.download_button("Descargar informe HTML", data=informe_html(),
                       file_name=f"Demo_Intelligence_{date.today():%Y-%m}.html", mime="text/html", key="dl_demo_html")
with dl2:
    st.download_button("Descargar informe PDF", data=construir_pdf(),
                       file_name=f"Demo_Intelligence_{date.today():%Y-%m}.pdf", mime="application/pdf", key="dl_demo_pdf")
