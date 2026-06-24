"""Intelligence Insight de BambuTech: estrategia comercial y resultados del mes."""
from __future__ import annotations

import json
import html
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

from portal_auth import render_bambutech_page_header, render_client_nav, require_auth_client
from shared.bambutech_brand import BAMBU_BORDER, BAMBU_DARK, BAMBU_GREEN, BAMBU_GREEN_DARK
from shared.config import supabase_key, supabase_url
from shared.metas import meta_de
from shared.planes import plan_de

st.set_page_config(page_title="BambuTech — Intelligence Insight", layout="wide", page_icon="")
if not require_auth_client("bambutech"):
    st.stop()
render_client_nav("19_BambuTech_Intelligence", "bambutech")

if plan_de("bambutech") != "premium":
    st.markdown(
        '<div style="max-width:760px;margin:80px auto;padding:34px;border:1px solid #d9dfda;'
        'border-left:6px solid #208d25;border-radius:14px;background:#fff">'
        '<div style="font-size:23px;font-weight:850;color:#171918">Intelligence Insight</div>'
        '<div style="font-size:16px;color:#59615c;margin-top:10px">No disponible en este plan.</div></div>',
        unsafe_allow_html=True,
    )
    st.stop()

SB_URL, SB_KEY = supabase_url(), supabase_key()
HEADERS = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"}


@st.cache_data(ttl=45, show_spinner=False)
def reuniones_reales():
    meetings = requests.get(
        f"{SB_URL}/rest/v1/reuniones?select=id,ghl_contact_id,estado_validacion,excluida"
        "&cliente_slug=eq.bambutech&excluida=eq.false",
        headers=HEADERS, timeout=15,
    ).json()
    tracking = requests.get(
        f"{SB_URL}/rest/v1/seguimiento_reuniones"
        "?select=reunion_id,val_estado_final,flag_meta_countable,status_reunion"
        "&cliente_slug=eq.bambutech",
        headers=HEADERS, timeout=15,
    ).json()
    validas = sum(1 for x in tracking if x.get("flag_meta_countable") is True)
    reagendar = sum(1 for x in tracking if x.get("status_reunion") in {"reagendada", "reagendar"})
    no_validas = sum(1 for x in tracking if x.get("val_estado_final") == "no_valida")
    return {"total": len(meetings), "validas": validas, "reagendar": reagendar, "no_validas": no_validas}


@st.cache_data(ttl=120, show_spinner=False)
def cargar_snapshot():
    p = DASHBOARD_DIR / "data" / "bambutech_intelligence.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


REAL = reuniones_reales()
META = int((meta_de("bambutech") or {}).get("validas") or 100)
SNAP = cargar_snapshot()
if not SNAP:
    st.error("Aún no se ha generado el consolidado del mes.")
    st.stop()

REG = pd.DataFrame(SNAP["registros"])
REG["canal"] = REG["canal"].replace({"Llamadas/WhatsApp": "Llamadas", "Llamada": "Llamadas"})
REG["fecha"] = pd.to_datetime(REG["fecha"], errors="coerce").dt.date
CORREO = SNAP["correo"]
OBJ = SNAP["objetivo"]
EMPRESAS_POSITIVAS = SNAP.get("empresas_positivas", [])
RES_LABEL = {
    "positiva": "Pidieron información o reunión", "deriva": "Derivan / refieren a un decisor",
    "negativa": "No interesado / no califica", "reagendar": "Reagendar",
    "no_contesta": "En seguimiento (sin respuesta aún)", "numero_malo": "Contacto no válido",
}
EXCLUIR_SEG = {"Sin clasificar", "Otros"}


# ---------------- helpers de UI ----------------
def section(title, subtitle=""):
    st.markdown(
        f'<div style="border-left:4px solid {BAMBU_GREEN};padding-left:13px;margin:24px 0 12px">'
        f'<div style="font-size:17px;font-weight:900;color:{BAMBU_DARK}">{title}</div>'
        + (f'<div style="font-size:12px;color:#64748b;margin-top:2px">{subtitle}</div>' if subtitle else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def scard(label, value, sub="", color=BAMBU_GREEN_DARK, tip=""):
    t = f' title="{tip}"' if tip else ""
    return (
        f'<div{t} style="background:#fff;border:1px solid {BAMBU_BORDER};border-top:3px solid {color};'
        f'border-radius:10px;padding:12px 14px;text-align:center;min-height:84px">'
        f'<div style="font-size:22px;font-weight:900;color:{color}">{value}</div>'
        f'<div style="font-size:10.5px;font-weight:800;color:{BAMBU_DARK};text-transform:uppercase;'
        f'letter-spacing:.3px;margin-top:5px">{label}</div>'
        + (f'<div style="font-size:10px;color:#94a3b8;margin-top:3px;line-height:1.3">{sub}</div>' if sub else "")
        + "</div>"
    )


def bars(rows, color):
    mx = max((v for _, v in rows), default=0) or 1
    return "".join(
        f'<div style="display:grid;grid-template-columns:210px 1fr 42px;gap:10px;align-items:center;margin:7px 0">'
        f'<span style="font-size:12px;text-align:right;color:#334155">{n}</span>'
        f'<div style="height:22px;background:#edf1ee;border-radius:7px;overflow:hidden">'
        f'<div style="height:100%;width:{max(4, round(v / mx * 100))}%;background:{color};border-radius:7px"></div></div>'
        f'<b style="font-size:12px;color:{color}">{v}</b></div>'
        for n, v in rows
    )


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
        'padding:0 4px 7px;border-bottom:1px solid #e5e7eb;font-size:10px;font-weight:800;'
        'text-transform:uppercase;color:#64748b">'
        '<span>Segmento</span><span>Gestiones</span><span>Conversaciones</span>'
        '<span>Positivas</span><span>Tasa</span></div>'
    )
    for name, gest, conv, pos, tasa in rows:
        body += (
            '<div style="display:grid;grid-template-columns:1fr 72px 82px 62px 58px;gap:8px;'
            'padding:9px 4px;border-bottom:1px solid #edf1ee;font-size:11.5px;align-items:center">'
            f'<b style="color:#334155">{name}</b><span>{gest}</span><span>{conv}</span>'
            f'<span style="color:#16a34a;font-weight:800">{pos}</span>'
            f'<span style="color:#16a34a;font-weight:800">{tasa:.0%}</span></div>'
        )
    empty = (
        "<span style='font-size:12px;color:#64748b'>"
        "Primer mes de estrategia: todavía no hay muestra suficiente para comparar este segmento."
        "</span>"
    )
    content = body if rows else empty
    return (f'<div style="background:#fff;border:1px solid {BAMBU_BORDER};border-radius:11px;'
            f'padding:14px 16px">{content}</div>'), rows


def _opts(col):
    return ["Todas"] + sorted([x for x in REG[col].dropna().unique() if str(x).strip()])


def conteo(df, *res):
    return int(df.resultado.isin(res).sum())


def segment_matrix(df):
    rows = []
    quality = {
        "Tecnología / Transformación": 1.0,
        "Operaciones / Procesos": 1.0,
        "Dirección / Negocio": .95,
        "Riesgo / Seguridad": .85,
        "Finanzas": .8,
        "Comercial / Marketing": .72,
        "Recursos Humanos": .65,
        "Otros": .55,
    }
    for (industry, area), sub in df.groupby(["industria", "area"]):
        if industry in EXCLUIR_SEG or area in EXCLUIR_SEG:
            continue
        accounts = int(sub["empresa"].replace("", pd.NA).nunique())
        conversations = int((~sub.resultado.isin(["no_contesta", "numero_malo"])).sum())
        positive = conteo(sub, "positiva", "deriva")
        meetings = int(sub["estado_raw"].str.contains("Reunión Agendada", case=False, na=False).sum())
        rate = positive / conversations if conversations else 0
        fit = 1.0 if industry not in {"Tecnología / Telecom"} else .8
        volume_factor = .4 + .6 * min(accounts / 30, 1)
        stage_factor = .7 + .3 * min(meetings / 2, 1)
        score = round(100 * rate * volume_factor * fit * quality.get(area, .65) * stage_factor)
        if conversations >= 20 and accounts >= 30:
            confidence = "Alta"
        elif conversations >= 10 or accounts >= 30:
            confidence = "Media"
        else:
            confidence = "Baja"
        if conversations < 10 and accounts < 30:
            signal, decision = "Muestra insuficiente", "Ampliar muestra"
        elif score >= 28:
            signal, decision = "Alta oportunidad", "Aumentar cobertura"
        elif score >= 16:
            signal, decision = "Oportunidad media", "Mantener y ampliar"
        elif score >= 8:
            signal, decision = "Exploratorio", "Testear segunda muestra"
        else:
            signal, decision = "Baja señal", "Ajustar mensaje"
        rows.append({
            "Macroindustria": industry, "Macrocargo": area, "Cuentas activadas": accounts,
            "Conversaciones": conversations, "Positivas": positive,
            "Tasa positiva": rate, "Reuniones": meetings, "Score": score,
            "Confianza": confidence, "Señal": signal, "Decisión": decision,
        })
    return pd.DataFrame(rows).sort_values(
        ["Cuentas activadas", "Conversaciones", "Positivas", "Score"], ascending=False
    ) if rows else pd.DataFrame()


def insight_row(insight, evidence, implication, action):
    return {
        "Insight": insight, "Evidencia": evidence,
        "Implicancia": implication, "Acción recomendada": action,
    }


def _lat(value) -> str:
    return (
        str(value)
        .replace("â€”", "-")
        .replace("â€“", "-")
        .replace("â†’", "->")
        .replace("Ã—", "x")
        .encode("latin-1", "replace")
        .decode("latin-1")
    )


def html_table(df: pd.DataFrame, *, small: bool = True) -> str:
    if df is None or df.empty:
        return (
            '<div style="padding:13px;background:#f8faf8;color:#64748b;'
            'border:1px dashed #cbd5cc;border-radius:10px">Sin registros para la selecciÃ³n activa.</div>'
        )
    font = "11px" if small else "12px"
    out = [
        '<div style="overflow-x:auto;width:100%">',
        '<table style="width:100%;border-collapse:collapse;background:#fff;table-layout:fixed;'
        f'font-size:{font};line-height:1.38;border:1px solid #e2e8e4;border-radius:9px;overflow:hidden">',
        "<thead><tr>",
    ]
    for col in df.columns:
        out.append(
            '<th style="background:#f8faf8;color:#64748b;text-align:left;padding:9px 8px;'
            'border:1px solid #e5e7eb;font-weight:750;white-space:normal;word-break:normal">'
            f"{html.escape(str(col))}</th>"
        )
    out.append("</tr></thead><tbody>")
    for _, row in df.iterrows():
        out.append("<tr>")
        for value in row:
            out.append(
                '<td style="padding:8px;border:1px solid #edf1ee;vertical-align:top;'
                'white-space:normal;overflow-wrap:anywhere;word-break:normal">'
                f"{html.escape(str(value))}</td>"
            )
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


# ================= HEADER =================
st.markdown(
    '<style>.block-container{max-width:1380px;padding-top:1rem!important}</style>',
    unsafe_allow_html=True,
)
render_bambutech_page_header(
    "Intelligence Insight",
    "Prospección activa desde el 18 de mayo 2026 · el mes previo fue configuración · se actualiza 1×/mes",
)

# ===== ① Avance de meta (arriba, compacto) =====
pct_meta = round(REAL["validas"] / META * 100) if META else 0
st.markdown(
    f'<div style="display:flex;align-items:center;gap:14px;background:#fff;border:1px solid {BAMBU_BORDER};'
    f'border-radius:11px;padding:11px 18px;margin-bottom:10px">'
    f'<span style="font-size:12px;font-weight:850;color:{BAMBU_GREEN_DARK};white-space:nowrap">AVANCE DE LA META</span>'
    f'<div style="flex:1;height:14px;background:#edf1ee;border-radius:8px;overflow:hidden">'
    f'<div style="height:100%;width:{max(pct_meta, 2)}%;background:linear-gradient(90deg,#208d25,#38d430)"></div></div>'
    f'<span style="font-size:14px;font-weight:900;color:{BAMBU_GREEN_DARK};white-space:nowrap">'
    f'{REAL["validas"]} / {META} <span style="color:#94a3b8;font-weight:600">({pct_meta}%)</span></span></div>',
    unsafe_allow_html=True,
)

# ===== ② Lectura del ciclo + acceso a validación =====
mc1, mc2 = st.columns([4, 1])
mc1.markdown(
    f'<div style="font-size:12px;color:#475569;padding:7px 2px">'
    f'<b>{REAL["total"]} reuniones registradas</b> · {REAL["validas"]} válidas para la meta. '
    f'La evaluación contractual se consulta en el módulo especializado.</div>',
    unsafe_allow_html=True,
)
if mc2.button("Ver validación →", key="goto_val", use_container_width=True):
    st.switch_page("pages/18_BambuTech_Validacion_Reuniones.py")

st.markdown(
    f'<div style="background:#ecf9ec;border:1px solid #b8dfba;border-left:5px solid #38d430;'
    f'border-radius:10px;padding:11px 17px;margin:12px 0;font-size:13px;color:#36513b">'
    f'<b>Este mes se trató de la estrategia.</b> Probamos un enfoque multicanal completo '
    f'(correo, llamadas y WhatsApp) para detectar industrias, áreas y mensajes con mejor respuesta.</div>',
    unsafe_allow_html=True,
)

# ===== ③ Panel maestro de filtros cruzados =====
valid_dates = REG["fecha"].dropna()
min_date = valid_dates.min() if not valid_dates.empty else date(2026, 5, 18)
max_date = valid_dates.max() if not valid_dates.empty else date.today()
campaign_start = pd.to_datetime(SNAP["periodo"]["inicio"]).date()
min_date = max(min_date, campaign_start)
with st.container(border=True):
    st.markdown(
        '<div style="display:flex;justify-content:space-between;gap:14px;align-items:center;margin-bottom:5px">'
        '<div><div style="font-size:17px;font-weight:900;color:#171918">Control del análisis</div>'
        '<div style="font-size:12px;color:#64748b">Cada ajuste recalcula todas las métricas, tablas, '
        'heatmaps, insights y recomendaciones que aparecen debajo.</div></div>'
        '<span style="background:#dcfce7;color:#166534;border:1px solid #86efac;border-radius:999px;'
        'padding:5px 11px;font-size:10px;font-weight:850;white-space:nowrap">FILTROS GLOBALES</span></div>',
        unsafe_allow_html=True,
    )
    fc = st.columns([1.08, 1, 1.35, 1.25])
    period = fc[0].date_input(
        "Período",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        format="DD/MM/YYYY",
    )
    start_date, end_date = (
        period if isinstance(period, (tuple, list)) and len(period) == 2
        else (min_date, max_date)
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
        "Macrocargo (área)",
        ["Todas"] + sorted(x for x in base_area["area"].dropna().unique() if str(x).strip()),
    )
    st.markdown(
        f'<div style="font-size:11px;color:#64748b;margin-top:2px">'
        f'Vista activa: <b>{start_date:%d/%m/%Y}–{end_date:%d/%m/%Y}</b> · '
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

# ===== ④ Resumen filtrado =====
section("Resumen del mes", "Las métricas responden a los filtros seleccionados")
tasa = fpostot / fconv if fconv else 0
rs = st.columns(4)
rs[0].markdown(scard("Gestiones", len(REGf), "Registros dentro del filtro"), unsafe_allow_html=True)
rs[1].markdown(scard("Conversaciones", fconv, "Excluye sin respuesta y contacto inválido"),
               unsafe_allow_html=True)
rs[2].markdown(scard("Respuestas positivas", fpostot, f"{fp} interés directo + {fd} derivaciones", "#16a34a"),
               unsafe_allow_html=True)
rs[3].markdown(scard("Tasa positiva", f"{tasa:.0%}", "Positivas / conversaciones", "#16a34a"),
               unsafe_allow_html=True)
st.caption(
    f"Base multicanal total: {SNAP['universo_unico']:,} contactos únicos. "
    "Las métricas superiores corresponden al detalle disponible para el filtro."
)

# ===== ⑤ Actividad por canal filtrada =====
section("Actividad por canal", "Distribución de gestiones, conversaciones y positivas dentro del filtro")
channel_rows = []
for channel, sub in REGf.groupby("canal"):
    conv = len(sub) - conteo(sub, "no_contesta") - conteo(sub, "numero_malo")
    channel_rows.append((channel, len(sub), conv, conteo(sub, "positiva", "deriva")))
channel_rows.sort(key=lambda row: (-row[1], row[0]))
if channel_rows:
    activity_df = pd.DataFrame(
        channel_rows, columns=["Canal", "Gestiones", "Conversaciones", "Positivas"]
    )
    activity_df["Tasa positiva"] = activity_df.apply(
        lambda row: f"{row['Positivas'] / row['Conversaciones']:.0%}" if row["Conversaciones"] else "0%",
        axis=1,
    )
    st.dataframe(activity_df, hide_index=True, use_container_width=True)
if (
    start_date == min_date and end_date == max_date
    and f_canal in {"Todos", "Correo"} and f_ind == "Todas" and f_area == "Todas"
):
    st.caption(
        f"Volumen agregado de correo del período: {CORREO['enviados']:,} enviados · "
        f"{CORREO['entregados']:,} entregados · {CORREO['contactados']:,} contactados · "
        f"{CORREO['respuestas']} respuestas. Este volumen no se distribuye artificialmente por segmento."
    )

# ===== ⑤ Resultados de conversación =====
section("Resultados de conversación", "Cómo respondió el mercado en llamadas, WhatsApp y correo")
res_rows = [(RES_LABEL[k], conteo(REGf, k)) for k in
            ["positiva", "deriva", "reagendar", "negativa", "no_contesta", "numero_malo"]]
res_rows_sorted = sorted([(n, v) for n, v in res_rows if v > 0], key=lambda row: row[1], reverse=True)
st.caption(
    "Ordenado de mayor a menor por cantidad de respuestas dentro de la vista activa. "
    "Incluye llamadas, WhatsApp y las respuestas de correo presentes en el consolidado."
)
st.markdown(bars(res_rows_sorted, "#208d25"), unsafe_allow_html=True)
st.markdown(
    f'<div style="display:flex;gap:9px;flex-wrap:wrap;margin-top:9px;font-size:12px;font-weight:700">'
    f'<span style="background:#dcfce7;color:#166534;padding:4px 11px;border-radius:9px">'
    f'Positivas: {fpostot}{f" ({fpostot / fconv:.0%})" if fconv else ""}</span>'
    f'<span style="background:#ede9fe;color:#5b21b6;padding:4px 11px;border-radius:9px">Derivaciones: {fd}</span>'
    f'<span style="background:#fee2e2;color:#991b1b;padding:4px 11px;border-radius:9px">Negativas: {fn}</span>'
    f'<span style="background:#fef9c3;color:#854d0e;padding:4px 11px;border-radius:9px">En seguimiento: {fnoc}</span>'
    f'</div>',
    unsafe_allow_html=True,
)

# ===== Empresas que respondieron =====
section(
    "Empresas que respondieron",
    "Cuentas con información adicional, coordinando reunión o reunión agendada",
)
if EMPRESAS_POSITIVAS:
    empresas_df = pd.DataFrame(EMPRESAS_POSITIVAS)
    empresas_df["fecha"] = pd.to_datetime(empresas_df["fecha"], errors="coerce").dt.date
    empresas_df = empresas_df[empresas_df["fecha"].between(start_date, end_date, inclusive="both")]
    if f_canal != "Todos":
        empresas_df = empresas_df[empresas_df["canal"] == f_canal]
    if f_ind != "Todas":
        empresas_df = empresas_df[empresas_df["industria"] == f_ind]
    if f_area != "Todas":
        empresas_df = empresas_df[empresas_df["area"] == f_area]
    if empresas_df.empty:
        st.info("Primer mes de estrategia: este segmento todavía no registra empresas con respuesta positiva.")
    else:
        st.dataframe(
            empresas_df.rename(columns={
                "empresa": "Empresa",
                "estado": "Estado",
                "industria": "Macro-industria",
                "area": "Macro-cargo (área)",
                "canal": "Canal",
            }),
            hide_index=True,
            use_container_width=True,
            column_order=["Empresa", "Estado", "Macro-industria", "Macro-cargo (área)", "Canal"],
        )
else:
    st.info("Primer mes de estrategia: el detalle de empresas se incorporará en el próximo consolidado.")

# ===== ⑦ Respuesta por segmento =====
section("Respuesta por segmento", "¿Dónde está respondiendo mejor el mercado?")
segments = segment_matrix(REGf)
if segments.empty:
    st.info(
        "Todavía no hay muestra suficiente para concluir. Se requieren al menos 10 conversaciones "
        "efectivas o 30 cuentas activadas en un segmento para generar una lectura confiable."
    )
else:
    area_short = {
        "Comercial / Marketing": "Comercial",
        "Dirección / Negocio": "Dirección",
        "Operaciones / Procesos": "Operaciones",
        "Riesgo / Seguridad": "Riesgo",
        "Tecnología / Transformación": "Tecnología",
        "Recursos Humanos": "RR. HH.",
        "Finanzas": "Finanzas",
    }
    heat_segments = segments.copy()
    heat_segments["Macrocargo visible"] = heat_segments["Macrocargo"].map(area_short).fillna(
        heat_segments["Macrocargo"]
    )
    heat = alt.Chart(heat_segments).mark_rect(cornerRadius=4).encode(
        x=alt.X(
            "Macrocargo visible:N",
            title="Macrocargo (área)",
            axis=alt.Axis(labelAngle=0, labelLimit=130, labelPadding=8),
        ),
        y=alt.Y("Macroindustria:N", title="Macroindustria"),
        color=alt.Color(
            "Score:Q", title="Score",
            scale=alt.Scale(domain=[0, 15, 30, 50], range=["#f1f5f2", "#c8f2ca", "#65d66a", "#167b2d"]),
        ),
        tooltip=[
            "Macroindustria", "Macrocargo", "Cuentas activadas", "Conversaciones",
            "Positivas", alt.Tooltip("Tasa positiva:Q", format=".0%"),
            "Reuniones", "Score", "Confianza", "Señal", "Decisión",
        ],
    ).properties(height=max(260, 38 * segments["Macroindustria"].nunique()))
    st.altair_chart(heat, use_container_width=True)
    st.caption(
        "Score de oportunidad = tasa positiva × volumen de cuentas × fit ICP × calidad del cargo × "
        "avance de etapa. Los segmentos pequeños se marcan como muestra insuficiente aunque tengan una tasa alta."
    )
    st.caption(
        "Orden de la tabla: mayor cantidad de cuentas activadas, luego conversaciones, positivas y score. "
        "Asi se prioriza donde ya existe cobertura suficiente antes de comparar tasas."
    )
    segment_view = segments.copy()
    segment_view["Segmento"] = segment_view["Macroindustria"] + " + " + segment_view["Macrocargo"]
    segment_view["Tasa positiva"] = segment_view["Tasa positiva"].map(lambda x: f"{x:.0%}")
    segment_view = segment_view.rename(columns={
        next((c for c in segment_view.columns if c.startswith("Se")), "Señal"): "Señal",
        next((c for c in segment_view.columns if c.startswith("Decisi")), "Decisión"): "Decisión",
    })
    segment_view = segment_view[[
        "Segmento", "Cuentas activadas", "Conversaciones", "Positivas", "Tasa positiva",
        "Reuniones", "Score", "Confianza", "Señal", "Decisión",
    ]]
    st.markdown(html_table(segment_view), unsafe_allow_html=True)

# ===== ⑧ Rankings =====
section("Top industrias y cargos", "Rankings recalculados según los filtros superiores")
si, sa = st.columns(2)
with si:
    st.markdown("<b style='font-size:12.5px'>Top macro-industrias</b>", unsafe_allow_html=True)
    html_i, rows_i = top_tabla(REGf, "industria")
    st.markdown(html_i, unsafe_allow_html=True)
with sa:
    st.markdown("<b style='font-size:12.5px'>Top macro-cargos (áreas)</b>", unsafe_allow_html=True)
    html_a, rows_a = top_tabla(REGf, "area")
    st.markdown(html_a, unsafe_allow_html=True)
    with st.expander("¿Qué es un macro-cargo (área)?"):
        st.caption("Agrupamos los cientos de cargos en **áreas funcionales** (Tecnología, Operaciones, "
                   "Dirección, Comercial, Finanzas, RRHH, Riesgo) para definir estrategia por área, no cargo a cargo.")

# ===== ⑨ Qué aprendimos del mercado =====
section("Qué aprendimos del mercado", "Cada lectura conecta evidencia, implicancia y una acción")
learning_rows = []
if not segments.empty:
    reliable = segments[(segments["Conversaciones"] >= 10) | (segments["Cuentas activadas"] >= 30)]
    lead = (reliable if not reliable.empty else segments).iloc[0]
    learning_rows.append(insight_row(
        f"Mayor señal en {lead['Macroindustria']} + {lead['Macrocargo']}",
        f"{lead['Conversaciones']} conversaciones, {lead['Positivas']} positivas y "
        f"{lead['Reuniones']} reuniones; confianza {lead['Confianza'].lower()}.",
        "La oportunidad depende de combinar contexto industrial y área compradora, no solo de una tasa aislada.",
        lead["Decisión"],
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
        f"{best_channel[0]} genera la mejor señal dentro de la vista",
        f"{best_channel[1]} conversaciones y {best_channel[2]} positivas ({best_channel[3]:.0%}).",
        "El canal debe evaluarse por calidad de conversación y no solo por volumen de impactos.",
        "Mantenerlo dentro de una cadencia multicanal y ampliar muestra antes de reasignar esfuerzo.",
    ))
learning_rows.append(insight_row(
    "La cobertura de cuentas priorizadas sigue incompleta",
    f"{OBJ['prospectadas']} de {OBJ['total']} cuentas objetivo activadas ({OBJ['pct']}%).",
    "Todavía existe mercado priorizado por BambuTech que no ha recibido prospección.",
    "Activar el siguiente lote por score ICP y señal del segmento.",
))
learning_rows.append(insight_row(
    "La compra consultiva requiere múltiples áreas",
    f"La vista contiene {REGf['area'].nunique()} áreas funcionales con actividad.",
    "Integración y automatización suelen involucrar Dirección, Operaciones y TI.",
    "Buscar 2–3 perfiles por cuenta prioritaria y comparar respuesta por área.",
))
st.markdown(html_table(pd.DataFrame(learning_rows)), unsafe_allow_html=True)

# ===== ⑩ Mensajes y dolores =====
section(
    "Mensajes y dolores que están resonando",
    "Tema asociado a campaña; es una inferencia analítica, no una transcripción del prospecto",
)
theme_rows = []
for theme, sub in REGf.groupby("tema"):
    accounts = int(sub["empresa"].replace("", pd.NA).nunique())
    conversations = int((~sub.resultado.isin(["no_contesta", "numero_malo"])).sum())
    positives = conteo(sub, "positiva", "deriva")
    best_industry = (
        sub[sub.resultado.isin(["positiva", "deriva"])]["industria"].value_counts().index[0]
        if positives else "Sin señal suficiente"
    )
    rate = positives / conversations if conversations else 0
    recommendation = (
        "Usar como mensaje principal" if conversations >= 10 and rate >= .3
        else "Mantener y ampliar muestra" if positives >= 2
        else "Testear con mayor especificidad"
    )
    theme_rows.append({
        "Tema": theme, "Cuentas impactadas": accounts, "Conversaciones": conversations,
        "Positivas": positives, "Tasa positiva": f"{rate:.0%}",
        "Mejor industria": best_industry, "Recomendación": recommendation,
    })
theme_df = pd.DataFrame(theme_rows).sort_values(
    ["Cuentas impactadas", "Positivas", "Conversaciones"], ascending=False
) if theme_rows else pd.DataFrame()
if theme_df.empty:
    st.info("Todavía no hay muestra suficiente para comparar mensajes dentro de esta selección.")
else:
    st.caption(
        "Orden: mayor cantidad de cuentas impactadas, luego positivas y conversaciones. "
        "El objetivo es distinguir primero los mensajes con mayor cobertura real antes de comparar rendimiento."
    )
    st.markdown(html_table(theme_df), unsafe_allow_html=True)
    theme_lead = theme_df.iloc[0]
    st.success(
        f"Insight: **{theme_lead['Tema']}** concentra la mayor señal observable "
        f"({theme_lead['Positivas']} positivas). Conviene validar este aprendizaje con copy etiquetado "
        "por tema en el próximo ciclo."
    )

# ===== ⑪ Negativas y objeciones =====
section("Negativas y objeciones", "Las respuestas negativas también orientan segmentación y copy")
negative = REGf[REGf.resultado == "negativa"].copy()
objection_rows = []
for objection, sub in negative.groupby("estado_raw"):
    common_industry = sub["industria"].value_counts().index[0] if not sub.empty else "—"
    if "No Califica" in objection:
        reading = "Puede ser desajuste de cuenta, cargo o necesidad."
        action = "Revisar ICP y enriquecer Operaciones/TI antes de descartar."
    else:
        reading = "Falta de prioridad o valor percibido en el momento."
        action = "Reformular desde dolor operativo y programar recontacto."
    objection_rows.append({
        "Objeción": objection, "Cantidad": len(sub), "Industria más frecuente": common_industry,
        "Lectura": reading, "Acción": action,
    })
if objection_rows:
    st.dataframe(pd.DataFrame(objection_rows), hide_index=True, use_container_width=True)
else:
    st.info("No hay negativas registradas dentro de la combinación de filtros seleccionada.")

# ===== ⑫ Contexto de mercado =====
section("Contexto externo relevante", "Fuentes externas para interpretar las señales; no sustituyen los datos de campaña")
market_context = pd.DataFrame([
    {
        "Tendencia": "Nearshoring en México",
        "Por qué importa para BambuTech": "Aumenta la presión por integración, trazabilidad y escalabilidad operativa.",
        "Segmentos conectados": "Manufactura, logística e industrial",
        "Fuente": "Deloitte Insights",
    },
    {
        "Tendencia": "Inversión en smart manufacturing",
        "Por qué importa para BambuTech": "Deloitte reportó que 78% de 600 ejecutivos destinaba más de 20% del presupuesto de mejora a estas iniciativas.",
        "Segmentos conectados": "Manufactura, Operaciones y TI",
        "Fuente": "Deloitte 2025 Smart Manufacturing Survey",
    },
    {
        "Tendencia": "Compra B2B omnicanal",
        "Por qué importa para BambuTech": "McKinsey observó un promedio de diez canales usados durante el proceso de compra.",
        "Segmentos conectados": "Todos; especialmente cuentas medianas y grandes",
        "Fuente": "McKinsey B2B Pulse 2024",
    },
])
st.markdown(html_table(market_context), unsafe_allow_html=True)
st.markdown(
    "[Deloitte: Nearshoring in Mexico](https://www.deloitte.com/us/en/insights/topics/economy/"
    "issues-by-the-numbers/advantages-of-nearshoring-mexico.html) · "
    "[Deloitte: 2025 Smart Manufacturing Survey](https://www.deloitte.com/us/en/insights/industry/"
    "manufacturing/2025-smart-manufacturing-survey.html) · "
    "[McKinsey: B2B Pulse 2024](https://www.mckinsey.com/capabilities/growth-marketing-and-sales/"
    "our-insights/five-fundamental-truths-how-b2b-winners-keep-growing)"
)

# ===== ⑬ Cuentas objetivo =====
section(
    "Cuentas objetivo",
    "Funnel de empresas objetivo proporcionadas por BambuTech dentro de la combinacion activa de filtros",
)
active_accounts = int(REGf["empresa"].replace("", pd.NA).nunique())
conversation_accounts = int(
    REGf[~REGf.resultado.isin(["no_contesta", "numero_malo"])]["empresa"].replace("", pd.NA).nunique()
)
positive_accounts = int(
    REGf[REGf.resultado.isin(["positiva", "deriva"])]["empresa"].replace("", pd.NA).nunique()
)
meeting_accounts = int(
    REGf[REGf["estado_raw"].str.contains("Reunión Agendada", case=False, na=False)]["empresa"]
    .replace("", pd.NA).nunique()
)
o = st.columns(5)
for col, item in zip(o, [
    ("Universo objetivo", OBJ["total"], "Definido por BambuTech", "#208d25"),
    ("Activadas en vista", active_accounts, "Según filtros y período", "#208d25"),
    ("Con conversación", conversation_accounts, "Respuesta efectiva", "#7c3aed"),
    ("Con señal positiva", positive_accounts, "Interés o derivación", "#16a34a"),
    ("Con reunión", meeting_accounts, "Reunión agendada", "#0f7a2e"),
]):
    col.markdown(scard(*item), unsafe_allow_html=True)
st.caption(
    f"Las cuentas objetivo corresponden al universo de empresas priorizado/proporcionado por BambuTech para prospeccion. "
    f"Cobertura global del consolidado: {OBJ['prospectadas']} de {OBJ['total']} cuentas objetivo "
    f"activadas ({OBJ['pct']}%); quedan {OBJ['pendientes']} por activar."
)

# ===== ⑭ Próximos pasos =====
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
        "Acción BambuTech": "Validar industrias prioritarias y restricciones comerciales.",
        "Indicador": "≥10 conversaciones o ≥30 cuentas por segmento",
    },
    {
        "Decisión": "Vender dolor, no servicio",
        "Acción Conprospección": "Separar copy por integración, automatización, visibilidad de datos, productividad y escalabilidad.",
        "Acción BambuTech": "Entregar casos concretos y resultados por problema resuelto.",
        "Indicador": "Tasa positiva por tema de mensaje",
    },
    {
        "Decisión": "Aumentar multithreading",
        "Acción Conprospección": "Buscar Dirección, Operaciones y TI en cada cuenta prioritaria.",
        "Acción BambuTech": "Definir objeciones y propuesta de valor por área.",
        "Indicador": "2–3 áreas activadas por cuenta",
    },
    {
        "Decisión": "Activar siguiente lote",
        "Acción Conprospección": f"Priorizar las {OBJ['pendientes']} cuentas pendientes usando score ICP + señal del segmento.",
        "Acción BambuTech": "Confirmar exclusiones y cuentas estratégicas.",
        "Indicador": "Cobertura de cuentas objetivo",
    },
    {
        "Decisión": "Crear activos comerciales",
        "Acción Conprospección": "Incorporar activos a secuencias y seguimiento.",
        "Acción BambuTech": "Caso de integración, automatización, IA aplicada y cloud/ciberseguridad; one-pager por industria.",
        "Indicador": "Respuesta y reunión por activo utilizado",
    },
])
st.markdown(html_table(next_steps), unsafe_allow_html=True)
st.markdown(
    f'<div style="background:#ecf9ec;border:1px solid #b8dfba;border-left:5px solid {BAMBU_GREEN};'
    f'border-radius:11px;padding:15px 18px;margin-top:12px;font-size:13px;line-height:1.65;color:#29452f">'
    f'<b>Hipótesis del ciclo 2:</b> las cuentas industriales y logísticas contactadas desde Operaciones '
    f'o TI responderán mejor a mensajes sobre integración y automatización que a mensajes genéricos '
    f'de desarrollo de software.<br><b>Criterio de validación:</b> comparar tasa positiva y reuniones '
    f'con al menos 10 conversaciones efectivas o 30 cuentas activadas por combinación.</div>',
    unsafe_allow_html=True,
)

# ===== Descargar informe =====
def informe_html_resumido():
    seg_i, _ = top_tabla(REG, "industria")
    seg_a, _ = top_tabla(REG, "area")
    total_conv = len(REG) - conteo(REG, "no_contesta") - conteo(REG, "numero_malo")
    total_pos = conteo(REG, "positiva", "deriva")
    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<title>BambuTech · Intelligence Insight</title></head>
<body style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#f4f6f4;color:#0f172a;max-width:980px;margin:0 auto;padding:24px">
<div style="background:linear-gradient(135deg,#07110c,#0e1b15);color:#fff;padding:22px 26px;border-radius:14px">
<div style="font-size:24px;font-weight:900">Intelligence Insight · BambuTech</div>
<div style="font-size:12px;color:#baf8d0;margin-top:4px">Prospección activa desde el 18 de mayo 2026 · informe mensual</div></div>
<h3 style="color:{BAMBU_GREEN_DARK}">Resumen</h3><ul>
<li>Avance de la meta: <b>{REAL['validas']} / {META}</b> ({pct_meta}%)</li>
<li>Contactos únicos: <b>{SNAP['universo_unico']:,}</b></li>
<li>Conversaciones: <b>{total_conv}</b> · Positivas: <b>{total_pos}</b>
({total_pos / total_conv:.0%})</li>
<li>Correo: {CORREO['enviados']} enviados → {CORREO['contactados']} contactados → {CORREO['respuestas']} respuestas</li>
<li>Cuentas objetivo activadas: <b>{OBJ['prospectadas']} / {OBJ['total']}</b> ({OBJ['pct']}%)</li></ul>
<h3 style="color:{BAMBU_GREEN_DARK}">Respuesta por macro-industria (top 5)</h3>{seg_i}
<h3 style="color:{BAMBU_GREEN_DARK}">Respuesta por área (top 5)</h3>{seg_a}
</body></html>"""


def report_table(df):
    if df is None or df.empty:
        return '<div class="empty">Sin registros para la selección activa.</div>'
    return df.to_html(index=False, border=0, classes="report-table", escape=True)


def informe_html():
    segment_report = segments.copy()
    if not segment_report.empty:
        segment_report["Segmento"] = (
            segment_report["Macroindustria"] + " + " + segment_report["Macrocargo"]
        )
        segment_report["Tasa positiva"] = segment_report["Tasa positiva"].map(lambda x: f"{x:.0%}")
        segment_report = segment_report[[
            "Segmento", "Cuentas activadas", "Conversaciones", "Positivas",
            "Tasa positiva", "Reuniones", "Score", "Confianza", "Señal", "Decisión",
        ]].head(10)
    results_report = pd.DataFrame([
        {"Resultado": RES_LABEL[key], "Cantidad": conteo(REGf, key)}
        for key in ["positiva", "deriva", "reagendar", "negativa", "no_contesta", "numero_malo"]
    ]).sort_values("Cantidad", ascending=False)
    def ranking_report(dimension):
        rows = []
        for name, sub in REGf.groupby(dimension):
            if name in EXCLUIR_SEG:
                continue
            conversations = int((~sub.resultado.isin(["no_contesta", "numero_malo"])).sum())
            positives = conteo(sub, "positiva", "deriva")
            rows.append({
                dimension: name, "Gestiones": len(sub), "Conversaciones": conversations,
                "Positivas": positives,
                "Tasa positiva": f"{positives / conversations:.0%}" if conversations else "0%",
            })
        return pd.DataFrame(rows).sort_values(
            ["Positivas", "Conversaciones"], ascending=False
        ).head(5) if rows else pd.DataFrame()
    top_industries_report = ranking_report("industria").rename(columns={"industria": "Macroindustria"})
    top_areas_report = ranking_report("area").rename(columns={"area": "Macrocargo"})
    company_report = empresas_df.rename(columns={
        "empresa": "Empresa", "estado": "Estado", "industria": "Macroindustria",
        "area": "Macrocargo", "canal": "Canal", "fecha": "Fecha",
    }) if EMPRESAS_POSITIVAS else pd.DataFrame()
    if not company_report.empty:
        company_report = company_report[[
            "Empresa", "Estado", "Macroindustria", "Macrocargo", "Canal", "Fecha",
        ]]
    kpis = [
        ("Gestiones", len(REGf)), ("Conversaciones", fconv),
        ("Respuestas positivas", fpostot), ("Tasa positiva", f"{tasa:.0%}"),
        ("Cuentas activadas", active_accounts), ("Cuentas con reunión", meeting_accounts),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><strong>{value}</strong><span>{label}</span></div>'
        for label, value in kpis
    )
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BambuTech · Intelligence Insight</title>
<style>
body{{font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f4f6f4;color:#17211a;max-width:1280px;margin:0 auto;padding:28px;line-height:1.5}}
.hero{{background:linear-gradient(135deg,#07110c,#15251b);color:#fff;padding:28px 32px;border-radius:16px}}
.hero h1{{margin:0;font-size:28px}} .hero p{{margin:7px 0 0;color:#c8f7d1}}
.filter{{margin:18px 0;padding:15px 18px;border:2px solid #38d430;background:#f4fff5;border-radius:12px}}
.kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:18px 0}}
.kpi{{background:#fff;border:1px solid #d9e2db;border-top:4px solid #208d25;border-radius:11px;padding:15px;text-align:center}}
.kpi strong{{display:block;font-size:24px;color:#208d25}} .kpi span{{font-size:11px;text-transform:uppercase;font-weight:800}}
h2{{font-size:19px;border-left:5px solid #38d430;padding-left:12px;margin-top:30px}}
.question{{font-size:12px;color:#64748b;margin-top:-8px;margin-bottom:12px}}
.report-table{{width:100%;border-collapse:collapse;background:#fff;font-size:10.5px;margin:10px 0 18px;table-layout:fixed}}
.report-table th{{background:#edf5ee;color:#24342a;text-align:left;padding:9px;border:1px solid #dce6de;white-space:normal;overflow-wrap:anywhere}}
.report-table td{{padding:8px;border:1px solid #e4ebe5;vertical-align:top;white-space:normal;overflow-wrap:anywhere}}
.note{{background:#ecf9ec;border-left:5px solid #38d430;padding:14px 17px;border-radius:8px}}
.method{{font-size:11px;color:#64748b;background:#fff;padding:14px;border:1px solid #dce6de;border-radius:9px}}
.empty{{padding:14px;background:#f8faf8;color:#64748b;border:1px dashed #cbd5cc}}
a{{color:#167b2d}} @media print{{body{{padding:0}} .hero{{break-inside:avoid}}}}
</style></head><body>
<div class="hero"><h1>Intelligence Insight · BambuTech</h1>
<p>Reporte completo del ciclo comercial · generado desde el dashboard parametrizado</p></div>
<div class="filter"><b>Selección exportada:</b> {start_date:%d/%m/%Y}–{end_date:%d/%m/%Y} ·
Canal: {f_canal} · Macroindustria: {f_ind} · Macrocargo: {f_area}</div>
<h2>Resumen ejecutivo</h2><div class="question">¿Cuál es el estado del ciclo?</div>
<div class="kpis">{kpi_html}</div>
<div class="note"><b>Avance contractual:</b> {REAL['validas']} de {META} reuniones válidas ({pct_meta}%).</div>
<h2>Actividad por canal</h2>{report_table(activity_df if channel_rows else pd.DataFrame())}
<div class="method">Correo agregado: {CORREO['enviados']:,} enviados · {CORREO['entregados']:,} entregados ·
{CORREO['contactados']:,} contactados · {CORREO['respuestas']} respuestas. No se distribuye artificialmente por segmento.</div>
<h2>Resultados de conversación</h2>{report_table(results_report)}
<div class="method">Ordenado de mayor a menor por cantidad. Incluye llamadas, WhatsApp y respuestas de correo disponibles en el consolidado.</div>
<h2>Empresas que respondieron</h2>{report_table(company_report)}
<h2>Respuesta por segmento</h2>{report_table(segment_report)}
<div class="method">Score = tasa positiva × volumen de cuentas × fit ICP × calidad del cargo × avance de etapa.
Menos de 10 conversaciones y menos de 30 cuentas se marca como muestra insuficiente.</div>
<h2>Top industrias</h2>{report_table(top_industries_report)}
<h2>Top cargos</h2>{report_table(top_areas_report)}
<h2>Qué aprendimos del mercado</h2>{report_table(pd.DataFrame(learning_rows))}
<h2>Mensajes y dolores que están resonando</h2>
<div class="question">Tema asociado a campaña; inferencia analítica, no transcripción del prospecto.</div>
{report_table(theme_df)}
<h2>Negativas y objeciones</h2>{report_table(pd.DataFrame(objection_rows))}
<h2>Contexto externo relevante</h2>{report_table(market_context)}
<p><a href="https://www.deloitte.com/us/en/insights/topics/economy/issues-by-the-numbers/advantages-of-nearshoring-mexico.html">Deloitte · Nearshoring</a> ·
<a href="https://www.deloitte.com/us/en/insights/industry/manufacturing/2025-smart-manufacturing-survey.html">Deloitte · Smart Manufacturing</a> ·
<a href="https://www.mckinsey.com/capabilities/growth-marketing-and-sales/our-insights/five-fundamental-truths-how-b2b-winners-keep-growing">McKinsey · B2B Pulse</a></p>
<h2>Cuentas objetivo</h2>
<div class="kpis">
<div class="kpi"><strong>{OBJ['total']}</strong><span>Universo objetivo</span></div>
<div class="kpi"><strong>{active_accounts}</strong><span>Activadas en vista</span></div>
<div class="kpi"><strong>{conversation_accounts}</strong><span>Con conversación</span></div>
<div class="kpi"><strong>{positive_accounts}</strong><span>Con señal positiva</span></div>
<div class="kpi"><strong>{meeting_accounts}</strong><span>Con reunión</span></div>
<div class="kpi"><strong>{OBJ['pendientes']}</strong><span>Globales por activar</span></div></div>
<h2>Próximos pasos</h2>{report_table(next_steps)}
<div class="note"><b>Hipótesis del ciclo 2:</b> las cuentas industriales y logísticas contactadas desde
Operaciones o TI responderán mejor a mensajes de integración y automatización. Validar con al menos
10 conversaciones o 30 cuentas activadas.</div>
</body></html>"""


def _pdf_df_segmentos() -> pd.DataFrame:
    if segments.empty:
        return pd.DataFrame()
    df = segments.copy()
    df["Segmento"] = df["Macroindustria"] + " + " + df["Macrocargo"]
    df["Tasa positiva"] = df["Tasa positiva"].map(lambda x: f"{x:.0%}")
    df = df.rename(columns={
        next((c for c in df.columns if c.startswith("Se")), "Señal"): "Señal",
        next((c for c in df.columns if c.startswith("Decisi")), "Decisión"): "Decisión",
    })
    return df[[
        "Segmento", "Cuentas activadas", "Conversaciones", "Positivas", "Tasa positiva",
        "Reuniones", "Score", "Confianza", "Señal", "Decisión",
    ]].head(10)


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
        pdf.set_text_color(23, 33, 26)
        pdf.cell(0, 4, _lat(f"Registro {idx + 1}"), ln=1)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(45, 55, 48)
        for col in use.columns:
            value = row.get(col, "")
            pdf.set_x(16)
            pdf.set_font("Helvetica", "B", 7.5)
            pdf.multi_cell(35, 4, _lat(f"{col}:"), border=0)
            y_after_label = pdf.get_y()
            pdf.set_xy(52, y_after_label - 4)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.multi_cell(140, 4, _lat(value), border=0)
        pdf.ln(2)


def _pdf_section(pdf: FPDF, title: str, subtitle: str = "") -> None:
    if pdf.get_y() > 238:
        pdf.add_page()
    pdf.ln(4)
    pdf.set_draw_color(56, 212, 48)
    pdf.set_line_width(1.2)
    y = pdf.get_y()
    pdf.line(14, y, 14, y + 8)
    pdf.set_xy(17, y - 1)
    pdf.set_text_color(23, 33, 26)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 6, _lat(title), ln=1)
    if subtitle:
        pdf.set_x(17)
        pdf.set_text_color(100, 116, 139)
        pdf.set_font("Helvetica", "", 8)
        pdf.multi_cell(0, 4, _lat(subtitle))
    pdf.ln(2)


def construir_pdf_intelligence() -> bytes:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()
    pdf.set_fill_color(7, 17, 12)
    pdf.rect(0, 0, 210, 29, "F")
    pdf.set_xy(14, 8)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 7, _lat("Intelligence Insight - BambuTech"), ln=1)
    pdf.set_x(14)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(200, 247, 209)
    pdf.cell(0, 5, _lat(f"{start_date:%d/%m/%Y}-{end_date:%d/%m/%Y} | Canal: {f_canal} | Industria: {f_ind} | Area: {f_area}"), ln=1)
    pdf.set_y(38)

    _pdf_section(pdf, "Resumen ejecutivo", "Estado del ciclo y avance contractual")
    resumen = pd.DataFrame([
        {"Metrica": "Avance meta", "Valor": f"{REAL['validas']} / {META} ({pct_meta}%)"},
        {"Metrica": "Gestiones", "Valor": len(REGf)},
        {"Metrica": "Conversaciones", "Valor": fconv},
        {"Metrica": "Respuestas positivas", "Valor": fpostot},
        {"Metrica": "Tasa positiva", "Valor": f"{tasa:.0%}"},
        {"Metrica": "Cuentas objetivo activadas", "Valor": f"{OBJ['prospectadas']} / {OBJ['total']} ({OBJ['pct']}%)"},
    ])
    _pdf_table_cards(pdf, resumen)

    _pdf_section(pdf, "Actividad por canal", "Distribucion de gestiones, conversaciones y positivas")
    _pdf_table_cards(pdf, activity_df if channel_rows else pd.DataFrame())
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(100, 116, 139)
    pdf.multi_cell(0, 4, _lat(f"Correo agregado: {CORREO['enviados']:,} enviados, {CORREO['entregados']:,} entregados, {CORREO['contactados']:,} contactados y {CORREO['respuestas']} respuestas. No se distribuye artificialmente por segmento."))

    _pdf_section(pdf, "Resultados de conversacion")
    results_report = pd.DataFrame([
        {"Resultado": RES_LABEL[key], "Cantidad": conteo(REGf, key)}
        for key in ["positiva", "deriva", "reagendar", "negativa", "no_contesta", "numero_malo"]
    ]).sort_values("Cantidad", ascending=False)
    _pdf_table_cards(pdf, results_report)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(100, 116, 139)
    pdf.multi_cell(0, 4, _lat("Ordenado de mayor a menor por cantidad. Incluye llamadas, WhatsApp y respuestas de correo disponibles en el consolidado."))

    _pdf_section(pdf, "Empresas que respondieron")
    company_report = empresas_df.rename(columns={
        "empresa": "Empresa", "estado": "Estado", "industria": "Macroindustria",
        "area": "Macrocargo", "canal": "Canal", "fecha": "Fecha",
    }) if EMPRESAS_POSITIVAS else pd.DataFrame()
    if not company_report.empty:
        company_report = company_report[["Empresa", "Estado", "Macroindustria", "Macrocargo", "Canal", "Fecha"]]
    _pdf_table_cards(pdf, company_report)

    _pdf_section(pdf, "Respuesta por segmento", "Top 10 ordenado por cuentas activadas, conversaciones, positivas y score")
    _pdf_table_cards(pdf, _pdf_df_segmentos(), max_rows=10)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(100, 116, 139)
    pdf.multi_cell(0, 4, _lat("Score = tasa positiva x volumen de cuentas x fit ICP x calidad del cargo x avance de etapa. Los segmentos pequenos se marcan como muestra insuficiente aunque tengan tasa alta."))

    _pdf_section(pdf, "Que aprendimos del mercado")
    _pdf_table_cards(pdf, pd.DataFrame(learning_rows))

    _pdf_section(pdf, "Mensajes y dolores que estan resonando", "Ordenado por cuentas impactadas, luego positivas y conversaciones")
    _pdf_table_cards(pdf, theme_df)

    _pdf_section(pdf, "Negativas y objeciones")
    _pdf_table_cards(pdf, pd.DataFrame(objection_rows))

    _pdf_section(pdf, "Contexto externo relevante")
    _pdf_table_cards(pdf, market_context)

    _pdf_section(pdf, "Cuentas objetivo", "Empresas objetivo proporcionadas por BambuTech")
    cuentas = pd.DataFrame([
        {"Etapa": "Universo objetivo", "Cuentas": OBJ["total"], "Lectura": "Definido por BambuTech"},
        {"Etapa": "Activadas en vista", "Cuentas": active_accounts, "Lectura": "Segun filtros y periodo"},
        {"Etapa": "Con conversacion", "Cuentas": conversation_accounts, "Lectura": "Respuesta efectiva"},
        {"Etapa": "Con senal positiva", "Cuentas": positive_accounts, "Lectura": "Interes o derivacion"},
        {"Etapa": "Con reunion", "Cuentas": meeting_accounts, "Lectura": "Reuni?n agendada"},
        {"Etapa": "Pendientes globales", "Cuentas": OBJ["pendientes"], "Lectura": "Por activar"},
    ])
    _pdf_table_cards(pdf, cuentas)

    _pdf_section(pdf, "Proximos pasos")
    _pdf_table_cards(pdf, next_steps)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(22, 101, 52)
    pdf.multi_cell(0, 4, _lat("Hipotesis ciclo 2: cuentas industriales y logisticas contactadas desde Operaciones o TI responderan mejor a mensajes de integracion y automatizacion. Validar con al menos 10 conversaciones o 30 cuentas activadas."))

    out = pdf.output()
    return bytes(out)


st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
section("Descargas del reporte", "Exporta la misma lectura ejecutiva en HTML o PDF")
st.markdown(
    f'<style>div[class*="st-key-dl_informe"] button,div[class*="st-key-dl_pdf"] button{{background:{BAMBU_GREEN_DARK}!important;'
    f'border-color:{BAMBU_GREEN_DARK}!important;color:#fff!important;font-weight:800!important}}</style>',
    unsafe_allow_html=True,
)
dl1, dl2 = st.columns(2)
with dl1:
    st.download_button("Descargar informe HTML", data=informe_html(),
                       file_name="BambuTech_Intelligence_2026-06.html", mime="text/html", key="dl_informe")
with dl2:
    st.download_button("Descargar informe PDF", data=construir_pdf_intelligence(),
                       file_name="BambuTech_Intelligence_2026-06.pdf", mime="application/pdf", key="dl_pdf")
