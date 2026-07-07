"""Intelligence Insight de GBS Logistics: estrategia comercial y resultados.

Panel INTERNO de Conprospeccion (colores del design system del panel de
Seguimiento de Reuniones). Lee el snapshot sin PII generado por
dashboard/data/build_gbs_snapshot.py + reuniones reales de Supabase.
"""
from __future__ import annotations

import html
import json
import sys
from datetime import date
from pathlib import Path

import altair as alt
import pandas as pd
import requests
import streamlit as st
from fpdf import FPDF

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from master_auth import require_master_auth
from shared.config import supabase_key, supabase_url
from shared.cp_design import (
    CP_BG, CP_BLUE, CP_BLUE_BG, CP_CARBON, CP_GOLD, CP_GOLD_SOFT, CP_GRAY, CP_GRAY_BG,
    CP_GREEN, CP_GREEN_BG, CP_HEAT, CP_INK, CP_LINE, CP_LINE_STRONG, CP_MUTED,
    CP_MUTED_SURFACE, CP_ORANGE, CP_ORANGE_BG, CP_PURPLE, CP_PURPLE_BG, CP_RED,
    CP_RED_BG, CP_SURFACE, FONT_BODY, FONT_HEAD, FONT_IMPORT, FONT_MONO,
)

try:
    from shared.metas import meta_de
except Exception:  # pragma: no cover
    meta_de = None

st.set_page_config(page_title="GBS — Intelligence Insight", layout="wide")
if not require_master_auth():
    st.stop()

st.markdown(
    """<style>
    [data-testid="stSidebar"], [data-testid="stToolbar"] { display:none !important; }
    .block-container{max-width:1380px;padding-top:1rem!important}
    </style>""",
    unsafe_allow_html=True,
)
st.markdown(f"<style>{FONT_IMPORT} .stApp{{font-family:{FONT_BODY}}}</style>", unsafe_allow_html=True)

SB_URL, SB_KEY = supabase_url().rstrip("/"), supabase_key()
HEADERS = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"}
SLUG = "gbs"


@st.cache_data(ttl=45, show_spinner=False)
def reuniones_reales():
    meetings = requests.get(
        f"{SB_URL}/rest/v1/reuniones?select=id&cliente_slug=eq.{SLUG}",
        headers=HEADERS, timeout=15,
    ).json()
    tracking = requests.get(
        f"{SB_URL}/rest/v1/seguimiento_reuniones"
        "?select=val_estado_final,flag_meta_countable,status_reunion"
        f"&cliente_slug=eq.{SLUG}",
        headers=HEADERS, timeout=15,
    ).json()
    meetings = meetings if isinstance(meetings, list) else []
    tracking = tracking if isinstance(tracking, list) else []
    validas = sum(1 for x in tracking if x.get("flag_meta_countable") is True)
    reagendar = sum(1 for x in tracking if x.get("status_reunion") in {"reagendada", "reagendar"})
    no_validas = sum(1 for x in tracking if x.get("val_estado_final") == "no_valida")
    return {"total": len(meetings), "validas": validas, "reagendar": reagendar, "no_validas": no_validas}


@st.cache_data(ttl=120, show_spinner=False)
def cargar_snapshot():
    p = DASHBOARD_DIR / "data" / "gbs_intelligence.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def meta_gbs() -> int:
    if meta_de:
        try:
            value = (meta_de(SLUG) or {}).get("validas")
            if value:
                return int(float(value))
        except Exception:
            pass
    try:
        rows = requests.get(
            f"{SB_URL}/rest/v1/cliente_metas?select=reuniones_validas_meta&cliente_slug=eq.{SLUG}",
            headers=HEADERS, timeout=15,
        ).json()
        if rows:
            return int(float(rows[0]["reuniones_validas_meta"]))
    except Exception:
        pass
    return 30


REAL = reuniones_reales()
META = meta_gbs()
SNAP = cargar_snapshot()
if not SNAP:
    st.error("Aun no se ha generado el consolidado del mes. Corre dashboard/data/build_gbs_snapshot.py")
    st.stop()

REG = pd.DataFrame(SNAP["registros"])
REG["fecha"] = pd.to_datetime(REG["fecha"], errors="coerce").dt.date
CORREO = SNAP["correo"]
OBJ = SNAP["objetivo"]
EMPRESAS_POSITIVAS = SNAP.get("empresas_positivas", [])
RES_LABEL = {
    "positiva": "Pidieron reunion o informacion", "deriva": "Derivan / refieren a un decisor",
    "negativa": "No interesado / no califica", "reagendar": "Reagendar",
    "no_contesta": "En seguimiento (sin respuesta aun)", "numero_malo": "Contacto no valido",
}
EXCLUIR_SEG = {"Sin clasificar", "Otros"}


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
        f'<div style="display:grid;grid-template-columns:230px 1fr 42px;gap:10px;align-items:center;margin:7px 0">'
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
        conv = int((~sub.resultado.isin(["no_contesta", "numero_malo"])).sum())
        tasa = pos / conv if conv else 0
        rows.append((key, len(sub), conv, pos, tasa))
    rows.sort(key=lambda r: (-r[3], -r[2], -r[1]))
    rows = rows[:5]
    body = (
        '<div style="display:grid;grid-template-columns:1fr 72px 82px 62px 58px;gap:8px;'
        f'padding:0 4px 7px;border-bottom:1px solid {CP_LINE};font-size:10px;font-weight:700;'
        f'text-transform:uppercase;color:{CP_MUTED}">'
        '<span>Segmento</span><span>Gestiones</span><span>Conversaciones</span>'
        '<span>Positivas</span><span>Tasa</span></div>'
    )
    for name, gest, conv, pos, tasa in rows:
        body += (
            '<div style="display:grid;grid-template-columns:1fr 72px 82px 62px 58px;gap:8px;'
            f'padding:9px 4px;border-bottom:1px solid {CP_LINE};font-size:11.5px;align-items:center">'
            f'<b style="color:{CP_CARBON}">{name}</b><span>{gest}</span><span>{conv}</span>'
            f'<span style="color:{CP_GREEN};font-weight:800">{pos}</span>'
            f'<span style="color:{CP_GREEN};font-weight:800">{tasa:.0%}</span></div>'
        )
    empty = (
        f"<span style='font-size:12px;color:{CP_MUTED}'>"
        "Todavia no hay muestra suficiente para comparar este segmento."
        "</span>"
    )
    content = body if rows else empty
    return (f'<div style="background:{CP_SURFACE};border:1px solid {CP_LINE};border-radius:11px;'
            f'padding:14px 16px">{content}</div>'), rows


def segment_matrix(df):
    rows = []
    quality = {
        "Comercio Exterior / COMEX": 1.0,
        "Abastecimiento / Compras": 1.0,
        "Logistica / Supply Chain": .95,
        "Direccion / Gerencia": .9,
        "Operaciones": .8,
        "Finanzas / Administracion": .6,
        "Comercial / Ventas": .6,
        "Otros": .5,
    }
    for (industry, area), sub in df.groupby(["industria", "area"]):
        if industry in EXCLUIR_SEG or area in EXCLUIR_SEG:
            continue
        accounts = int(sub["empresa"].replace("", pd.NA).nunique())
        conversations = int((~sub.resultado.isin(["no_contesta", "numero_malo"])).sum())
        positive = conteo(sub, "positiva", "deriva")
        meetings = int(sub["estado_raw"].str.contains("Reunion Agendada|Reunión Agendada", case=False, na=False).sum())
        rate = positive / conversations if conversations else 0
        volume_factor = .4 + .6 * min(accounts / 30, 1)
        stage_factor = .7 + .3 * min(meetings / 2, 1)
        score = round(100 * rate * volume_factor * quality.get(area, .65) * stage_factor)
        if conversations >= 15 and accounts >= 25:
            confidence = "Alta"
        elif conversations >= 8 or accounts >= 25:
            confidence = "Media"
        else:
            confidence = "Baja"
        if conversations < 8 and accounts < 25:
            signal, decision = "Muestra insuficiente", "Ampliar muestra"
        elif score >= 26:
            signal, decision = "Alta oportunidad", "Aumentar cobertura"
        elif score >= 14:
            signal, decision = "Oportunidad media", "Mantener y ampliar"
        elif score >= 7:
            signal, decision = "Exploratorio", "Testear segunda muestra"
        else:
            signal, decision = "Baja senal", "Ajustar mensaje"
        rows.append({
            "Macroindustria": industry, "Macrocargo": area, "Cuentas activadas": accounts,
            "Conversaciones": conversations, "Positivas": positive,
            "Tasa positiva": rate, "Reuniones": meetings, "Score": score,
            "Confianza": confidence, "Senal": signal, "Decision": decision,
        })
    return pd.DataFrame(rows).sort_values(
        ["Cuentas activadas", "Conversaciones", "Positivas", "Score"], ascending=False
    ) if rows else pd.DataFrame()


def insight_row(insight, evidence, implication, action):
    return {"Insight": insight, "Evidencia": evidence,
            "Implicancia": implication, "Accion recomendada": action}


def _lat(value) -> str:
    return (
        str(value)
        .replace("—", "-").replace("–", "-").replace("→", "->")
        .replace("×", "x").replace("ó", "o").replace("á", "a")
        .replace("é", "e").replace("í", "i").replace("ú", "u")
        .replace("ñ", "n")
        .encode("latin-1", "replace").decode("latin-1")
    )


def html_table(df: pd.DataFrame, *, small: bool = True) -> str:
    if df is None or df.empty:
        return (
            f'<div style="padding:13px;background:{CP_MUTED_SURFACE};color:{CP_MUTED};'
            f'border:1px dashed {CP_LINE_STRONG};border-radius:10px">Sin registros para la seleccion activa.</div>'
        )
    font = "11px" if small else "12px"
    out = [
        '<div style="overflow-x:auto;width:100%">',
        '<table style="width:100%;border-collapse:collapse;background:#fff;table-layout:fixed;'
        f'font-size:{font};line-height:1.38;border:1px solid {CP_LINE};border-radius:9px;overflow:hidden">',
        "<thead><tr>",
    ]
    for col in df.columns:
        out.append(
            f'<th style="background:{CP_MUTED_SURFACE};color:{CP_MUTED};text-align:left;padding:9px 8px;'
            f'border:1px solid {CP_LINE};font-weight:700;white-space:normal;word-break:normal">'
            f"{html.escape(str(col))}</th>"
        )
    out.append("</tr></thead><tbody>")
    for _, row in df.iterrows():
        out.append("<tr>")
        for value in row:
            out.append(
                f'<td style="padding:8px;border:1px solid {CP_LINE};vertical-align:top;'
                'white-space:normal;overflow-wrap:anywhere;word-break:normal">'
                f"{html.escape(str(value))}</td>"
            )
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


# ================= HEADER =================
_ini = pd.to_datetime(SNAP["periodo"]["inicio"]).date()
st.markdown(
    f'<div style="background:{CP_CARBON};color:#fff;border-radius:0 0 12px 12px;padding:16px 22px;'
    f'display:flex;align-items:center;justify-content:space-between;box-shadow:0 10px 24px rgba(26,26,26,.14)">'
    f'<div style="display:flex;align-items:center;gap:14px">'
    f'<div style="width:26px;height:26px;border-radius:7px;background:linear-gradient(135deg,{CP_CARBON} 0 52%,{CP_GOLD} 52% 100%);box-shadow:inset 0 0 0 2px #fff"></div>'
    f'<div><div style="font-family:{FONT_HEAD};font-size:19px;font-weight:800;line-height:1.1">Intelligence Insight · GBS Logistics</div>'
    f'<div style="font-size:12px;color:#C9C9C6;margin-top:2px">Prospeccion multicanal (WhatsApp + correo) · se actualiza 1x/mes</div></div></div>'
    f'<div style="font-size:11px;color:#C9C9C6;text-align:right;font-family:{FONT_HEAD};font-weight:600">Conprospeccion<br>Panel interno</div></div>',
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
    f'<b>{REAL["total"]} reuniones registradas</b> · {REAL["validas"]} validas para la meta. '
    f'La evaluacion contractual se consulta en el panel de Seguimiento de Reuniones.</div>',
    unsafe_allow_html=True,
)
if mc2.button("Ver seguimiento →", key="goto_seg", use_container_width=True):
    st.switch_page("pages/1_Seguimiento_Reuniones.py")

st.markdown(
    f'<div style="background:{CP_GOLD_SOFT};border:1px solid #F0D28D;border-left:5px solid {CP_GOLD};'
    f'border-radius:10px;padding:11px 17px;margin:12px 0;font-size:13px;color:#5A4A00">'
    f'<b>Este ciclo fue de estrategia.</b> Probamos prospeccion multicanal (WhatsApp y correo) sobre '
    f'importadores/exportadores en Chile, Peru y Colombia para detectar industrias, areas y mensajes '
    f'con mejor respuesta para el servicio logistico integral de GBS.</div>',
    unsafe_allow_html=True,
)

# ===== Panel maestro de filtros cruzados =====
valid_dates = REG["fecha"].dropna()
min_date = valid_dates.min() if not valid_dates.empty else _ini
max_date = valid_dates.max() if not valid_dates.empty else date.today()
min_date = max(min_date, _ini)
with st.container(border=True):
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;gap:14px;align-items:center;margin-bottom:5px">'
        f'<div><div style="font-family:{FONT_HEAD};font-size:17px;font-weight:800;color:{CP_INK}">Control del analisis</div>'
        f'<div style="font-size:12px;color:{CP_MUTED}">Cada ajuste recalcula todas las metricas, tablas, '
        'heatmaps, insights y recomendaciones que aparecen debajo.</div></div>'
        f'<span style="background:{CP_GOLD_SOFT};color:#7A6400;border:1px solid #F0D28D;border-radius:999px;'
        'padding:5px 11px;font-size:10px;font-weight:800;white-space:nowrap">FILTROS GLOBALES</span></div>',
        unsafe_allow_html=True,
    )
    fc = st.columns([1.08, 1, 1.35, 1.25])
    period = fc[0].date_input(
        "Periodo", value=(min_date, max_date), min_value=min_date, max_value=max_date, format="DD/MM/YYYY",
    )
    start_date, end_date = (
        period if isinstance(period, (tuple, list)) and len(period) == 2 else (min_date, max_date)
    )
    date_base = REG[REG["fecha"].between(start_date, end_date, inclusive="both")]
    f_canal = fc[1].selectbox("Canal", ["Todos"] + sorted(date_base["canal"].dropna().unique()))
    base_ind = date_base if f_canal == "Todos" else date_base[date_base["canal"] == f_canal]
    f_ind = fc[2].selectbox(
        "Macroindustria",
        ["Todas"] + sorted(x for x in base_ind["industria"].dropna().unique() if str(x).strip()),
    )
    base_area = base_ind if f_ind == "Todas" else base_ind[base_ind["industria"] == f_ind]
    f_area = fc[3].selectbox(
        "Macrocargo (area)",
        ["Todas"] + sorted(x for x in base_area["area"].dropna().unique() if str(x).strip()),
    )
    st.markdown(
        f'<div style="font-size:11px;color:{CP_MUTED};margin-top:2px">'
        f'Vista activa: <b>{start_date:%d/%m/%Y}-{end_date:%d/%m/%Y}</b> · '
        f'<b>{f_canal}</b> · <b>{f_ind}</b> · <b>{f_area}</b></div>',
        unsafe_allow_html=True,
    )

REGf = date_base.copy()
if f_canal != "Todos": REGf = REGf[REGf.canal == f_canal]
if f_ind != "Todas": REGf = REGf[REGf.industria == f_ind]
if f_area != "Todas": REGf = REGf[REGf.area == f_area]

fp, fd = conteo(REGf, "positiva"), conteo(REGf, "deriva")
fn, fr = conteo(REGf, "negativa"), conteo(REGf, "reagendar")
fnoc, fmalo = conteo(REGf, "no_contesta"), conteo(REGf, "numero_malo")
fconv = len(REGf) - fnoc - fmalo
fpostot = fp + fd

# ===== Resumen filtrado =====
section("Resumen del ciclo", "Las metricas responden a los filtros seleccionados")
tasa = fpostot / fconv if fconv else 0
rs = st.columns(4)
rs[0].markdown(scard("Gestiones", len(REGf), "Registros dentro del filtro"), unsafe_allow_html=True)
rs[1].markdown(scard("Conversaciones", fconv, "Excluye sin respuesta y contacto invalido"), unsafe_allow_html=True)
rs[2].markdown(scard("Respuestas positivas", fpostot, f"{fp} interes directo + {fd} derivaciones", CP_GREEN), unsafe_allow_html=True)
rs[3].markdown(scard("Tasa positiva", f"{tasa:.0%}", "Positivas / conversaciones", CP_GREEN), unsafe_allow_html=True)
st.caption(
    f"Base multicanal total: {SNAP['universo_unico']:,} contactos unicos (WhatsApp + correo). "
    "Las metricas superiores corresponden a la gestion con resultado registrado."
)

# ===== Actividad por canal =====
section("Actividad por canal", "Distribucion de gestiones, conversaciones y positivas dentro del filtro")
channel_rows = []
for channel, sub in REGf.groupby("canal"):
    conv = len(sub) - conteo(sub, "no_contesta") - conteo(sub, "numero_malo")
    channel_rows.append((channel, len(sub), conv, conteo(sub, "positiva", "deriva")))
channel_rows.sort(key=lambda row: (-row[1], row[0]))
activity_df = pd.DataFrame(channel_rows, columns=["Canal", "Gestiones", "Conversaciones", "Positivas"]) if channel_rows else pd.DataFrame()
if channel_rows:
    activity_df["Tasa positiva"] = activity_df.apply(
        lambda row: f"{row['Positivas'] / row['Conversaciones']:.0%}" if row["Conversaciones"] else "0%", axis=1,
    )
    st.dataframe(activity_df, hide_index=True, use_container_width=True)
if start_date == min_date and end_date == max_date and f_canal in {"Todos", "Correo"} and f_ind == "Todas" and f_area == "Todas":
    st.caption(
        f"Volumen agregado de correo (Snov) del periodo: {CORREO['enviados']:,} enviados · "
        f"{CORREO['entregados']:,} entregados · {CORREO['contactados']:,} contactados · "
        f"{CORREO['respuestas']} respuestas rastreadas. Estas campanas no tenian tracking de apertura activo, "
        "por eso el correo aporta alcance pero la conversacion se concentra en WhatsApp."
    )

# ===== Resultados de conversacion =====
section("Resultados de conversacion", "Como respondio el mercado en WhatsApp, llamadas y correo")
res_rows = [(RES_LABEL[k], conteo(REGf, k)) for k in
            ["positiva", "deriva", "reagendar", "negativa", "no_contesta", "numero_malo"]]
res_rows_sorted = sorted([(n, v) for n, v in res_rows if v > 0], key=lambda row: row[1], reverse=True)
st.caption("Ordenado de mayor a menor por cantidad de respuestas dentro de la vista activa.")
st.markdown(bars(res_rows_sorted, CP_CARBON), unsafe_allow_html=True)
st.markdown(
    f'<div style="display:flex;gap:9px;flex-wrap:wrap;margin-top:9px;font-size:12px;font-weight:700">'
    f'<span style="background:{CP_GREEN_BG};color:{CP_GREEN};padding:4px 11px;border-radius:9px">'
    f'Positivas: {fpostot}{f" ({fpostot / fconv:.0%})" if fconv else ""}</span>'
    f'<span style="background:{CP_PURPLE_BG};color:{CP_PURPLE};padding:4px 11px;border-radius:9px">Derivaciones: {fd}</span>'
    f'<span style="background:{CP_RED_BG};color:{CP_RED};padding:4px 11px;border-radius:9px">Negativas: {fn}</span>'
    f'<span style="background:{CP_ORANGE_BG};color:{CP_ORANGE};padding:4px 11px;border-radius:9px">En seguimiento: {fnoc}</span>'
    f'</div>',
    unsafe_allow_html=True,
)

# ===== Empresas que respondieron =====
section("Empresas que respondieron", "Cuentas con informacion adicional, coordinando o reunion agendada")
empresas_df = pd.DataFrame(EMPRESAS_POSITIVAS)
if EMPRESAS_POSITIVAS:
    empresas_df["fecha"] = pd.to_datetime(empresas_df["fecha"], errors="coerce").dt.date
    empresas_df = empresas_df[empresas_df["fecha"].between(start_date, end_date, inclusive="both")]
    if f_canal != "Todos":
        empresas_df = empresas_df[empresas_df["canal"] == f_canal]
    if f_ind != "Todas":
        empresas_df = empresas_df[empresas_df["industria"] == f_ind]
    if f_area != "Todas":
        empresas_df = empresas_df[empresas_df["area"] == f_area]
    if empresas_df.empty:
        st.info("Este segmento todavia no registra empresas con respuesta positiva.")
    else:
        st.dataframe(
            empresas_df.rename(columns={
                "empresa": "Empresa", "estado": "Estado", "industria": "Macro-industria",
                "area": "Macro-cargo (area)", "canal": "Canal",
            }),
            hide_index=True, use_container_width=True,
            column_order=["Empresa", "Estado", "Macro-industria", "Macro-cargo (area)", "Canal"],
        )
else:
    st.info("El detalle de empresas se incorporara en el proximo consolidado.")

# ===== Respuesta por segmento =====
section("Respuesta por segmento", "Donde esta respondiendo mejor el mercado?")
segments = segment_matrix(REGf)
if segments.empty:
    st.info(
        "Todavia no hay muestra suficiente para concluir. Se requieren al menos 8 conversaciones "
        "efectivas o 25 cuentas activadas en un segmento para una lectura confiable."
    )
else:
    heat = alt.Chart(segments).mark_rect(cornerRadius=4).encode(
        x=alt.X("Macrocargo:N", title="Macrocargo (area)", axis=alt.Axis(labelAngle=0, labelLimit=130, labelPadding=8)),
        y=alt.Y("Macroindustria:N", title="Macroindustria"),
        color=alt.Color("Score:Q", title="Score",
                        scale=alt.Scale(domain=[0, 12, 25, 45], range=CP_HEAT)),
        tooltip=["Macroindustria", "Macrocargo", "Cuentas activadas", "Conversaciones", "Positivas",
                 alt.Tooltip("Tasa positiva:Q", format=".0%"), "Reuniones", "Score", "Confianza", "Senal", "Decision"],
    ).properties(height=max(260, 38 * segments["Macroindustria"].nunique()))
    st.altair_chart(heat, use_container_width=True)
    st.caption(
        "Score de oportunidad = tasa positiva x volumen de cuentas x calidad del cargo x avance de etapa. "
        "Los segmentos pequenos se marcan como muestra insuficiente aunque tengan una tasa alta."
    )
    segment_view = segments.copy()
    segment_view["Segmento"] = segment_view["Macroindustria"] + " + " + segment_view["Macrocargo"]
    segment_view["Tasa positiva"] = segment_view["Tasa positiva"].map(lambda x: f"{x:.0%}")
    segment_view = segment_view[[
        "Segmento", "Cuentas activadas", "Conversaciones", "Positivas", "Tasa positiva",
        "Reuniones", "Score", "Confianza", "Senal", "Decision",
    ]]
    st.markdown(html_table(segment_view), unsafe_allow_html=True)

# ===== Rankings =====
section("Top industrias y cargos", "Rankings recalculados segun los filtros superiores")
si, sa = st.columns(2)
with si:
    st.markdown("<b style='font-size:12.5px'>Top macro-industrias</b>", unsafe_allow_html=True)
    html_i, rows_i = top_tabla(REGf, "industria")
    st.markdown(html_i, unsafe_allow_html=True)
with sa:
    st.markdown("<b style='font-size:12.5px'>Top macro-cargos (areas)</b>", unsafe_allow_html=True)
    html_a, rows_a = top_tabla(REGf, "area")
    st.markdown(html_a, unsafe_allow_html=True)
    with st.expander("Que es un macro-cargo (area)?"):
        st.caption("Agrupamos los cientos de cargos en areas funcionales (COMEX, Abastecimiento, "
                   "Logistica, Direccion, Operaciones, Finanzas, Comercial) para definir estrategia por area.")

# ===== Que aprendimos del mercado =====
section("Que aprendimos del mercado", "Cada lectura conecta evidencia, implicancia y una accion")
learning_rows = []
if not segments.empty:
    reliable = segments[(segments["Conversaciones"] >= 8) | (segments["Cuentas activadas"] >= 25)]
    lead = (reliable if not reliable.empty else segments).iloc[0]
    learning_rows.append(insight_row(
        f"Mayor senal en {lead['Macroindustria']} + {lead['Macrocargo']}",
        f"{lead['Conversaciones']} conversaciones, {lead['Positivas']} positivas y "
        f"{lead['Reuniones']} reuniones; confianza {lead['Confianza'].lower()}.",
        "La oportunidad depende de combinar contexto industrial y area compradora, no solo de una tasa aislada.",
        lead["Decision"],
    ))
channel_summary = []
for channel, sub in REGf.groupby("canal"):
    conv = int((~sub.resultado.isin(["no_contesta", "numero_malo"])).sum())
    positives = conteo(sub, "positiva", "deriva")
    if conv:
        channel_summary.append((channel, conv, positives, positives / conv))
if channel_summary:
    best_channel = max(channel_summary, key=lambda row: (row[3], row[1]))
    learning_rows.append(insight_row(
        f"{best_channel[0]} genera la mejor senal dentro de la vista",
        f"{best_channel[1]} conversaciones y {best_channel[2]} positivas ({best_channel[3]:.0%}).",
        "El canal debe evaluarse por calidad de conversacion y no solo por volumen de impactos.",
        "Mantenerlo dentro de una cadencia multicanal y ampliar muestra antes de reasignar esfuerzo.",
    ))
learning_rows.append(insight_row(
    "La compra logistica la decide la gerencia, pero la operan otras areas",
    f"La vista contiene {REGf['area'].nunique()} areas funcionales con actividad; Direccion concentra el volumen.",
    "Importar con regularidad involucra a Gerencia (decide), COMEX/Abastecimiento (operan) y Logistica.",
    "Buscar 2-3 perfiles por cuenta prioritaria y comparar respuesta por area.",
))
learning_rows.append(insight_row(
    "El correo aporta alcance; WhatsApp aporta la conversacion",
    f"{CORREO['enviados']:,} correos enviados sin tracking de apertura vs. gestion conversacional en WhatsApp.",
    "El correo abre la puerta pero la respuesta calificada de GBS ocurre en WhatsApp.",
    "Activar tracking de apertura/respuesta en Snov para medir el correo de punta a punta.",
))
st.markdown(html_table(pd.DataFrame(learning_rows)), unsafe_allow_html=True)

# ===== Mensajes y dolores =====
section("Mensajes y dolores que estan resonando",
        "Tema asociado a la campana; es una inferencia analitica, no una transcripcion del prospecto")
theme_rows = []
for theme, sub in REGf.groupby("tema"):
    accounts = int(sub["empresa"].replace("", pd.NA).nunique())
    conversations = int((~sub.resultado.isin(["no_contesta", "numero_malo"])).sum())
    positives = conteo(sub, "positiva", "deriva")
    best_industry = (
        sub[sub.resultado.isin(["positiva", "deriva"])]["industria"].value_counts().index[0]
        if positives else "Sin senal suficiente"
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
        "Mejor industria": best_industry, "Recomendacion": recommendation,
    })
theme_df = pd.DataFrame(theme_rows).sort_values(
    ["Cuentas impactadas", "Positivas", "Conversaciones"], ascending=False
) if theme_rows else pd.DataFrame()
if theme_df.empty:
    st.info("Todavia no hay muestra suficiente para comparar mensajes dentro de esta seleccion.")
else:
    st.markdown(html_table(theme_df), unsafe_allow_html=True)
    theme_lead = theme_df.iloc[0]
    st.success(
        f"Insight: **{theme_lead['Tema']}** concentra la mayor senal observable "
        f"({theme_lead['Positivas']} positivas). Conviene validar con copy etiquetado por tema en el proximo ciclo."
    )

# ===== Negativas y objeciones =====
section("Negativas y objeciones", "Las respuestas negativas tambien orientan segmentacion y copy")
negative = REGf[REGf.resultado == "negativa"].copy()
objection_rows = []
for objection, sub in negative.groupby("estado_raw"):
    common_industry = sub["industria"].value_counts().index[0] if not sub.empty else "-"
    if "califica" in objection.lower():
        reading = "Puede ser desajuste de ICP: sin flujo de importacion recurrente o fuera de mercado."
        action = "Revisar ICP (importador mensual) y priorizar mineria/maquinaria/alimentos."
    else:
        reading = "Falta de prioridad o proveedor logistico vigente."
        action = "Reformular desde dolor operativo (visibilidad, aduana, un solo interlocutor) y recontactar."
    objection_rows.append({
        "Objecion": objection, "Cantidad": len(sub), "Industria mas frecuente": common_industry,
        "Lectura": reading, "Accion": action,
    })
if objection_rows:
    st.dataframe(pd.DataFrame(objection_rows), hide_index=True, use_container_width=True)
else:
    st.info("No hay negativas registradas dentro de la combinacion de filtros seleccionada.")

# ===== Contexto de mercado =====
section("Contexto de mercado relevante", "Senales del rubro para interpretar los datos; no sustituyen los de campana")
market_context = pd.DataFrame([
    {
        "Tendencia": "Importadores pyme sin area logistica robusta",
        "Por que importa para GBS": "Es el corazon del ICP: empresas que delegan la cadena completa (flete, aduana, seguro, transporte local) a un solo interlocutor.",
        "Segmentos conectados": "Mineria, Maquinaria, Alimentos y Retail que importan de forma recurrente",
        "Senal": "Direccion/Gerencia concentra el volumen de respuesta",
    },
    {
        "Tendencia": "Reconfiguracion de cadenas de suministro (origenes USA/China/Europa)",
        "Por que importa para GBS": "Aumenta la necesidad de asesoria en rutas, consolidado y visibilidad de carga para importadores en Chile y Peru.",
        "Segmentos conectados": "Maquinaria e Industria, Importacion/Exportacion",
        "Senal": "COMEX y Abastecimiento muestran interes directo",
    },
    {
        "Tendencia": "Carga temperada para vino y alimentos",
        "Por que importa para GBS": "Diferenciador especifico de GBS (Thermoliner, control de humedad, registro de temperatura) frente a forwarders genericos.",
        "Segmentos conectados": "Alimentos, Bebidas y Agro",
        "Senal": "Segmento con derivaciones a decisor",
    },
])
st.markdown(html_table(market_context), unsafe_allow_html=True)
st.caption("Fuente: definicion de ICP y diferenciadores de GBS (onboarding) cruzada con la respuesta observada en campana.")

# ===== Cobertura de cuentas =====
section("Cobertura de cuentas", "Embudo de empresas alcanzadas dentro de la combinacion activa de filtros")
active_accounts = int(REGf["empresa"].replace("", pd.NA).nunique())
conversation_accounts = int(REGf[~REGf.resultado.isin(["no_contesta", "numero_malo"])]["empresa"].replace("", pd.NA).nunique())
positive_accounts = int(REGf[REGf.resultado.isin(["positiva", "deriva"])]["empresa"].replace("", pd.NA).nunique())
meeting_accounts = int(REGf[REGf["estado_raw"].str.contains("Reunion Agendada|Reunión Agendada", case=False, na=False)]["empresa"].replace("", pd.NA).nunique())
o = st.columns(5)
for col, item in zip(o, [
    ("Universo alcanzado", OBJ["total"], "Empresas en la base GBS", CP_CARBON),
    ("Activadas en vista", active_accounts, "Segun filtros y periodo", CP_CARBON),
    ("Con conversacion", conversation_accounts, "Respuesta efectiva", CP_PURPLE),
    ("Con senal positiva", positive_accounts, "Interes o derivacion", CP_GREEN),
    ("Con reunion", meeting_accounts, "Reunion agendada", CP_GREEN),
]):
    col.markdown(scard(*item), unsafe_allow_html=True)
st.caption(
    f"Universo de empresas prospectadas por GBS: {OBJ['total']}; "
    f"{OBJ['prospectadas']} con gestion registrada ({OBJ['pct']}%); quedan {OBJ['pendientes']} por activar."
)

# ===== Proximos pasos =====
section("Proximos pasos", "Plan ejecutivo conectado con los datos y la hipotesis del proximo ciclo")
lead_segment = None if segments.empty else segments.iloc[0]
lead_text = (
    f"{lead_segment['Macroindustria']} + {lead_segment['Macrocargo']}"
    if lead_segment is not None else "los segmentos que alcancen muestra suficiente"
)
next_steps = pd.DataFrame([
    {
        "Decision": "Concentrar prospeccion",
        "Accion Conprospeccion": f"Ampliar la muestra de {lead_text} sin declarar ganador hasta superar el umbral de confianza.",
        "Accion GBS": "Confirmar industrias prioritarias (mineria, maquinaria, alimentos) y cuentas a excluir.",
        "Indicador": ">=8 conversaciones o >=25 cuentas por segmento",
    },
    {
        "Decision": "Multithreading por cuenta",
        "Accion Conprospeccion": "Sumar COMEX/Abastecimiento y Logistica ademas de Gerencia en cada cuenta prioritaria.",
        "Accion GBS": "Definir objeciones y propuesta de valor por area (quien decide vs. quien opera).",
        "Indicador": "2-3 areas activadas por cuenta",
    },
    {
        "Decision": "Cerrar el loop del correo",
        "Accion Conprospeccion": "Activar tracking de apertura/respuesta en Snov y etiquetar copy por tema.",
        "Accion GBS": "Validar mensajes de valor agregado (aduana, visibilidad, un solo interlocutor).",
        "Indicador": "Tasa de apertura y respuesta por campana",
    },
    {
        "Decision": "Vender dolor, no flete",
        "Accion Conprospeccion": "Separar copy por servicio integral, visibilidad de carga, asesoria aduanera y carga temperada.",
        "Accion GBS": "Entregar casos concretos por problema resuelto (sin abrir con precio).",
        "Indicador": "Tasa positiva por tema de mensaje",
    },
])
st.markdown(html_table(next_steps), unsafe_allow_html=True)
st.markdown(
    f'<div style="background:{CP_GOLD_SOFT};border:1px solid #F0D28D;border-left:5px solid {CP_GOLD};'
    f'border-radius:11px;padding:15px 18px;margin-top:12px;font-size:13px;line-height:1.65;color:#5A4A00">'
    f'<b>Hipotesis del ciclo 2:</b> los importadores de mineria, maquinaria y alimentos contactados desde '
    f'Gerencia y luego COMEX/Abastecimiento responderan mejor a mensajes de servicio integral y visibilidad '
    f'de carga que a un mensaje generico de flete.<br><b>Criterio de validacion:</b> comparar tasa positiva '
    f'y reuniones con al menos 8 conversaciones efectivas o 25 cuentas activadas por combinacion.</div>',
    unsafe_allow_html=True,
)


# ===== Descargas =====
def report_table(df):
    if df is None or df.empty:
        return '<div class="empty">Sin registros para la seleccion activa.</div>'
    return df.to_html(index=False, border=0, classes="report-table", escape=True)


def informe_html():
    segment_report = segments.copy()
    if not segment_report.empty:
        segment_report["Segmento"] = segment_report["Macroindustria"] + " + " + segment_report["Macrocargo"]
        segment_report["Tasa positiva"] = segment_report["Tasa positiva"].map(lambda x: f"{x:.0%}")
        segment_report = segment_report[[
            "Segmento", "Cuentas activadas", "Conversaciones", "Positivas",
            "Tasa positiva", "Reuniones", "Score", "Confianza", "Senal", "Decision",
        ]].head(10)
    results_report = pd.DataFrame([
        {"Resultado": RES_LABEL[key], "Cantidad": conteo(REGf, key)}
        for key in ["positiva", "deriva", "reagendar", "negativa", "no_contesta", "numero_malo"]
    ]).sort_values("Cantidad", ascending=False)
    company_report = empresas_df.rename(columns={
        "empresa": "Empresa", "estado": "Estado", "industria": "Macroindustria",
        "area": "Macrocargo", "canal": "Canal", "fecha": "Fecha",
    }) if EMPRESAS_POSITIVAS and not empresas_df.empty else pd.DataFrame()
    if not company_report.empty:
        company_report = company_report[["Empresa", "Estado", "Macroindustria", "Macrocargo", "Canal", "Fecha"]]
    kpis = [
        ("Gestiones", len(REGf)), ("Conversaciones", fconv),
        ("Respuestas positivas", fpostot), ("Tasa positiva", f"{tasa:.0%}"),
        ("Cuentas activadas", active_accounts), ("Cuentas con reunion", meeting_accounts),
    ]
    kpi_html = "".join(f'<div class="kpi"><strong>{value}</strong><span>{label}</span></div>' for label, value in kpis)
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GBS Logistics - Intelligence Insight</title>
<style>
{FONT_IMPORT}
body{{font-family:{FONT_BODY};background:{CP_BG};color:{CP_INK};max-width:1280px;margin:0 auto;padding:28px;line-height:1.5}}
.hero{{background:{CP_CARBON};color:#fff;padding:28px 32px;border-radius:16px}}
.hero h1{{margin:0;font-family:{FONT_HEAD};font-size:28px}} .hero p{{margin:7px 0 0;color:#C9C9C6}}
.filter{{margin:18px 0;padding:15px 18px;border:2px solid {CP_GOLD};background:{CP_GOLD_SOFT};border-radius:12px}}
.kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:18px 0}}
.kpi{{background:#fff;border:1px solid {CP_LINE};border-top:4px solid {CP_GOLD};border-radius:11px;padding:15px;text-align:center}}
.kpi strong{{display:block;font-family:{FONT_MONO};font-size:24px;color:{CP_CARBON}}} .kpi span{{font-size:11px;text-transform:uppercase;font-weight:800}}
h2{{font-family:{FONT_HEAD};font-size:19px;border-left:5px solid {CP_GOLD};padding-left:12px;margin-top:30px}}
.report-table{{width:100%;border-collapse:collapse;background:#fff;font-size:10.5px;margin:10px 0 18px;table-layout:fixed}}
.report-table th{{background:{CP_MUTED_SURFACE};color:{CP_CARBON};text-align:left;padding:9px;border:1px solid {CP_LINE};white-space:normal;overflow-wrap:anywhere}}
.report-table td{{padding:8px;border:1px solid {CP_LINE};vertical-align:top;white-space:normal;overflow-wrap:anywhere}}
.note{{background:{CP_GOLD_SOFT};border-left:5px solid {CP_GOLD};padding:14px 17px;border-radius:8px}}
.method{{font-size:11px;color:{CP_MUTED};background:#fff;padding:14px;border:1px solid {CP_LINE};border-radius:9px}}
.empty{{padding:14px;background:{CP_MUTED_SURFACE};color:{CP_MUTED};border:1px dashed {CP_LINE_STRONG}}}
a{{color:{CP_ORANGE}}}@media print{{body{{padding:0}} .hero{{break-inside:avoid}}}}
</style></head><body>
<div class="hero"><h1>Intelligence Insight - GBS Logistics</h1>
<p>Reporte del ciclo comercial - generado desde el panel interno de Conprospeccion</p></div>
<div class="filter"><b>Seleccion exportada:</b> {start_date:%d/%m/%Y}-{end_date:%d/%m/%Y} ·
Canal: {f_canal} · Macroindustria: {f_ind} · Macrocargo: {f_area}</div>
<h2>Resumen ejecutivo</h2>
<div class="kpis">{kpi_html}</div>
<div class="note"><b>Avance contractual:</b> {REAL['validas']} de {META} reuniones validas ({pct_meta}%).</div>
<h2>Actividad por canal</h2>{report_table(activity_df if channel_rows else pd.DataFrame())}
<div class="method">Correo agregado (Snov): {CORREO['enviados']:,} enviados · {CORREO['entregados']:,} entregados ·
{CORREO['contactados']:,} contactados · {CORREO['respuestas']} respuestas rastreadas (sin tracking de apertura).</div>
<h2>Resultados de conversacion</h2>{report_table(results_report)}
<h2>Empresas que respondieron</h2>{report_table(company_report)}
<h2>Respuesta por segmento</h2>{report_table(segment_report if not segments.empty else pd.DataFrame())}
<div class="method">Score = tasa positiva x volumen de cuentas x calidad del cargo x avance de etapa.</div>
<h2>Que aprendimos del mercado</h2>{report_table(pd.DataFrame(learning_rows))}
<h2>Mensajes y dolores que estan resonando</h2>{report_table(theme_df)}
<h2>Negativas y objeciones</h2>{report_table(pd.DataFrame(objection_rows))}
<h2>Contexto de mercado relevante</h2>{report_table(market_context)}
<h2>Cobertura de cuentas</h2>
<div class="kpis">
<div class="kpi"><strong>{OBJ['total']}</strong><span>Universo alcanzado</span></div>
<div class="kpi"><strong>{active_accounts}</strong><span>Activadas en vista</span></div>
<div class="kpi"><strong>{conversation_accounts}</strong><span>Con conversacion</span></div>
<div class="kpi"><strong>{positive_accounts}</strong><span>Con senal positiva</span></div>
<div class="kpi"><strong>{meeting_accounts}</strong><span>Con reunion</span></div>
<div class="kpi"><strong>{OBJ['pendientes']}</strong><span>Por activar</span></div></div>
<h2>Proximos pasos</h2>{report_table(next_steps)}
<div class="note"><b>Hipotesis del ciclo 2:</b> importadores de mineria, maquinaria y alimentos contactados desde
Gerencia y luego COMEX/Abastecimiento responderan mejor a mensajes de servicio integral y visibilidad de carga.</div>
</body></html>"""


def _pdf_df_segmentos() -> pd.DataFrame:
    if segments.empty:
        return pd.DataFrame()
    df = segments.copy()
    df["Segmento"] = df["Macroindustria"] + " + " + df["Macrocargo"]
    df["Tasa positiva"] = df["Tasa positiva"].map(lambda x: f"{x:.0%}")
    return df[["Segmento", "Cuentas activadas", "Conversaciones", "Positivas", "Tasa positiva",
               "Reuniones", "Score", "Confianza", "Senal", "Decision"]].head(10)


def _pdf_table_cards(pdf: FPDF, df: pd.DataFrame, *, max_rows: int | None = None) -> None:
    if df is None or df.empty:
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(100, 116, 139)
        pdf.multi_cell(0, 5, _lat("Sin registros para la seleccion activa."))
        return
    use = df.head(max_rows) if max_rows else df
    for idx, row in use.iterrows():
        if pdf.get_y() > 250:
            pdf.add_page()
        pdf.set_draw_color(217, 226, 219)
        pdf.set_fill_color(248, 250, 248)
        x, y = pdf.get_x(), pdf.get_y()
        pdf.rect(x, y, 182, 7, "DF")
        pdf.set_xy(x + 2, y + 1.5)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(26, 26, 26)
        pdf.cell(0, 4, _lat(f"Registro {idx + 1}"), ln=1)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(45, 55, 48)
        for col in use.columns:
            value = row.get(col, "")
            pdf.set_x(16)
            pdf.set_font("Helvetica", "B", 7.5)
            pdf.multi_cell(38, 4, _lat(f"{col}:"), border=0)
            y_after_label = pdf.get_y()
            pdf.set_xy(55, y_after_label - 4)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.multi_cell(137, 4, _lat(value), border=0)
        pdf.ln(2)


def _pdf_section(pdf: FPDF, title: str, subtitle: str = "") -> None:
    if pdf.get_y() > 238:
        pdf.add_page()
    pdf.ln(4)
    pdf.set_draw_color(255, 215, 0)
    pdf.set_line_width(1.2)
    y = pdf.get_y()
    pdf.line(14, y, 14, y + 8)
    pdf.set_xy(17, y - 1)
    pdf.set_text_color(26, 26, 26)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 6, _lat(title), ln=1)
    if subtitle:
        pdf.set_x(17)
        pdf.set_text_color(100, 116, 139)
        pdf.set_font("Helvetica", "", 8)
        pdf.multi_cell(0, 4, _lat(subtitle))
    pdf.ln(2)


def construir_pdf() -> bytes:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()
    pdf.set_fill_color(51, 51, 51)
    pdf.rect(0, 0, 210, 29, "F")
    pdf.set_xy(14, 8)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 7, _lat("Intelligence Insight - GBS Logistics"), ln=1)
    pdf.set_x(14)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(201, 201, 198)
    pdf.cell(0, 5, _lat(f"{start_date:%d/%m/%Y}-{end_date:%d/%m/%Y} | Canal: {f_canal} | Industria: {f_ind} | Area: {f_area}"), ln=1)
    pdf.set_y(38)

    _pdf_section(pdf, "Resumen ejecutivo", "Estado del ciclo y avance contractual")
    resumen = pd.DataFrame([
        {"Metrica": "Avance meta", "Valor": f"{REAL['validas']} / {META} ({pct_meta}%)"},
        {"Metrica": "Gestiones", "Valor": len(REGf)},
        {"Metrica": "Conversaciones", "Valor": fconv},
        {"Metrica": "Respuestas positivas", "Valor": fpostot},
        {"Metrica": "Tasa positiva", "Valor": f"{tasa:.0%}"},
        {"Metrica": "Cuentas activadas", "Valor": f"{OBJ['prospectadas']} / {OBJ['total']} ({OBJ['pct']}%)"},
    ])
    _pdf_table_cards(pdf, resumen)

    _pdf_section(pdf, "Actividad por canal")
    _pdf_table_cards(pdf, activity_df if channel_rows else pd.DataFrame())

    _pdf_section(pdf, "Resultados de conversacion")
    _pdf_table_cards(pdf, pd.DataFrame([
        {"Resultado": RES_LABEL[key], "Cantidad": conteo(REGf, key)}
        for key in ["positiva", "deriva", "reagendar", "negativa", "no_contesta", "numero_malo"]
    ]).sort_values("Cantidad", ascending=False))

    _pdf_section(pdf, "Respuesta por segmento", "Top 10 por cuentas, conversaciones, positivas y score")
    _pdf_table_cards(pdf, _pdf_df_segmentos(), max_rows=10)

    _pdf_section(pdf, "Que aprendimos del mercado")
    _pdf_table_cards(pdf, pd.DataFrame(learning_rows))

    _pdf_section(pdf, "Mensajes y dolores que estan resonando")
    _pdf_table_cards(pdf, theme_df)

    _pdf_section(pdf, "Negativas y objeciones")
    _pdf_table_cards(pdf, pd.DataFrame(objection_rows))

    _pdf_section(pdf, "Contexto de mercado relevante")
    _pdf_table_cards(pdf, market_context)

    _pdf_section(pdf, "Proximos pasos")
    _pdf_table_cards(pdf, next_steps)

    return bytes(pdf.output())


st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
section("Descargas del reporte", "Exporta la misma lectura ejecutiva en HTML o PDF")
st.markdown(
    f'<style>div[class*="st-key-dl_gbs_html"] button,div[class*="st-key-dl_gbs_pdf"] button{{background:{CP_GOLD}!important;'
    f'border-color:{CP_GOLD}!important;color:{CP_INK}!important;font-weight:800!important}}</style>',
    unsafe_allow_html=True,
)
dl1, dl2 = st.columns(2)
with dl1:
    st.download_button("Descargar informe HTML", data=informe_html(),
                       file_name=f"GBS_Intelligence_{date.today():%Y-%m}.html", mime="text/html", key="dl_gbs_html")
with dl2:
    st.download_button("Descargar informe PDF", data=construir_pdf(),
                       file_name=f"GBS_Intelligence_{date.today():%Y-%m}.pdf", mime="application/pdf", key="dl_gbs_pdf")
