"""Intelligence Insight de GBS Logistics: estrategia comercial y resultados.

Panel INTERNO de Conprospección (colores del design system del panel de
Seguimiento de Reuniones). Lee el snapshot sin PII generado por
dashboard/data/build_gbs_snapshot.py + reuniones reales de Supabase.
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
    CP_BG, CP_CARBON, CP_GOLD, CP_GOLD_SOFT, CP_GRAY, CP_GREEN, CP_GREEN_BG,
    CP_HEAT, CP_INK, CP_LINE, CP_LINE_STRONG, CP_MUTED, CP_MUTED_SURFACE,
    CP_ORANGE, CP_ORANGE_BG, CP_PURPLE, CP_PURPLE_BG, CP_RED, CP_RED_BG,
    CP_SURFACE, FONT_BODY, FONT_HEAD, FONT_IMPORT, FONT_MONO,
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
ASSETS_DIR = DASHBOARD_DIR / "assets"


def _logo_b64(fname: str = "cp_mark_dark.png") -> str:
    p = ASSETS_DIR / fname
    if not p.exists():
        return ""
    ext = p.suffix.lstrip(".")
    d = base64.b64encode(p.read_bytes()).decode()
    return f'<img src="data:image/{ext};base64,{d}" height="28" style="object-fit:contain">'


@st.cache_data(ttl=45, show_spinner=False)
def reuniones_reales():
    meetings = requests.get(
        f"{SB_URL}/rest/v1/reuniones?select=id&cliente_slug=eq.{SLUG}",
        headers=HEADERS, timeout=15,
    ).json()
    tracking = requests.get(
        f"{SB_URL}/rest/v1/seguimiento_reuniones"
        "?select=reunion_id,val_estado_final,flag_meta_countable,status_reunion"
        f"&cliente_slug=eq.{SLUG}",
        headers=HEADERS, timeout=15,
    ).json()
    meetings = meetings if isinstance(meetings, list) else []
    tracking = tracking if isinstance(tracking, list) else []
    validas = sum(1 for x in tracking if x.get("flag_meta_countable") is True)
    reagendar = sum(1 for x in tracking if x.get("status_reunion") in {"reagendada", "reagendar"})
    no_validas = sum(1 for x in tracking if x.get("val_estado_final") == "no_valida")
    return {"total": len(meetings), "validas": validas, "reagendar": reagendar, "no_validas": no_validas}


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
_MOTIVO_CURADO = {
    "fundicion ferrosa": "ICP incorrecto (empresa de Perú)",
    "autorel": "ICP incorrecto (empresa de Perú)",
    "hot express s.a.": "ICP incorrecto (competencia)",
    "minera colquisiri s.a.": "ICP incorrecto (competencia)",
    "baika fruit": "Sin información suficiente para evaluar",
    "dysmar soluciones industriales": "ICP incorrecto (empresa de Perú)",
    "santibañez customs broker": "ICP incorrecto (competencia)",
}


def _sin_acentos(x: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFKD", str(x or "")).encode("ascii", "ignore").decode().lower().strip()


_MOTIVO_CURADO_NORM = {_sin_acentos(k): v for k, v in _MOTIVO_CURADO.items()}


def _motivo_de(empresa: str, motivo_raw: str) -> str:
    curado = _MOTIVO_CURADO_NORM.get(_sin_acentos(empresa))
    return curado if curado else (motivo_raw or "")


@st.cache_data(ttl=45, show_spinner=False)
def reuniones_detalle():
    """Detalle real de las reuniones/cotizaciones del ciclo (empresa, fecha,
    tipo, estado final y motivo cuando aplica), cruzando reuniones con la
    validacion definitiva de seguimiento_reuniones."""
    meetings = requests.get(
        f"{SB_URL}/rest/v1/reuniones"
        "?select=id,empresa,fecha_reunion,observacion,motivo_no_valida"
        f"&cliente_slug=eq.{SLUG}",
        headers=HEADERS, timeout=15,
    ).json()
    tracking = requests.get(
        f"{SB_URL}/rest/v1/seguimiento_reuniones"
        "?select=reunion_id,val_estado_final"
        f"&cliente_slug=eq.{SLUG}",
        headers=HEADERS, timeout=15,
    ).json()
    meetings = meetings if isinstance(meetings, list) else []
    tracking = tracking if isinstance(tracking, list) else []
    estado_por_id = {t.get("reunion_id"): t.get("val_estado_final") for t in tracking}

    rows = []
    for m in meetings:
        estado_raw = estado_por_id.get(m.get("id"))
        if estado_raw == "excluida":
            continue  # registro de seguimiento huerfano, no corresponde a esta reunion
        observacion = str(m.get("observacion") or "")
        tipo = "Cotización" if "cotiz" in observacion.lower() else "Reunión"
        fecha = pd.to_datetime(m.get("fecha_reunion"), errors="coerce")
        empresa = m.get("empresa") or "-"
        estado_final = _ESTADO_FINAL_LABEL.get(estado_raw, "Pendiente")
        motivo = _motivo_de(empresa, m.get("motivo_no_valida")) if estado_final != "Válida" else ""
        rows.append({
            "Empresa": empresa,
            "Fecha": fecha.date() if not pd.isna(fecha) else None,
            "Tipo": tipo,
            "Estado final": estado_final,
            "Motivo": motivo,
        })
    df = pd.DataFrame(rows)
    return df.sort_values("Fecha", ascending=False) if not df.empty else df


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
    return 45


REAL = reuniones_reales()
META = meta_gbs()
SNAP = cargar_snapshot()
if not SNAP:
    st.error("Aún no se ha generado el consolidado del mes. Corre dashboard/data/build_gbs_snapshot.py")
    st.stop()

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


def _lat(value) -> str:
    """Solo repara mojibake (UTF-8 leido como Latin-1); Helvetica/Latin-1 SI
    soporta tildes y ene espanola, asi que no se eliminan acentos reales."""
    return (
        str(value)
        .replace("â€”", "-").replace("â€“", "-").replace("â†’", "->")
        .replace("Ã—", "x")
        .encode("latin-1", "replace").decode("latin-1")
    )


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
    f'<div><div style="font-family:{FONT_HEAD};font-size:19px;font-weight:800;line-height:1.1">Intelligence Insight · GBS Logistics</div>'
    f'<div style="font-size:12px;color:#C9C9C6;margin-top:2px">Prospección multicanal · Ciclo de junio 2026</div></div></div>'
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
    st.switch_page("pages/1_Seguimiento_Reuniones.py")

st.markdown(
    f'<div style="background:{CP_GOLD_SOFT};border:1px solid #F0D28D;border-left:5px solid {CP_GOLD};'
    f'border-radius:10px;padding:11px 17px;margin:12px 0;font-size:13px;color:#5A4A00">'
    f'<b>Este ciclo fue de estrategia.</b> Probamos prospección multicanal sobre '
    f'importadores/exportadores en Chile, Perú y Colombia para detectar industrias, áreas y mensajes '
    f'con mejor respuesta para el servicio logístico integral de GBS. Se ajustó el ICP durante el ciclo '
    f'(se retiraron cuentas peruanas fuera de perfil), por eso el universo total de este consolidado '
    f'es más acotado y las tasas de respuesta se ven más nítidas que en el ciclo anterior.</div>',
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
    "contacto no calza con el perfil buscado (tamaño, país, flujo de importación), no que haya rechazado "
    "la propuesta; por eso se excluye del cálculo de tasa positiva junto con contacto no válido y sin respuesta."
)

# ===== Reuniones y cotizaciones del ciclo =====
section(
    "Reuniones y cotizaciones del ciclo",
    "Las 17 reuniones/cotizaciones registradas, con su estado final y motivo cuando aplica",
)
reuniones_df = reuniones_detalle()
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
        st.caption("Agrupamos los cientos de cargos en áreas funcionales (COMEX, Abastecimiento, "
                   "Logística, Dirección, Operaciones, Finanzas, Comercial) para definir estrategia por área.")
st.markdown(
    f'<div style="background:{CP_MUTED_SURFACE};border:1px solid {CP_LINE};border-radius:10px;'
    f'padding:11px 14px;margin-top:10px;font-size:12px;color:{CP_CARBON};line-height:1.55">'
    f'<b>Por qué avanzamos más en Minería y Metales / Alimentos, Bebidas y Agro:</b> La cartera de '
    'inversión minera en Chile llegó a USD 104.500 millones proyectados a 2034, con 13 proyectos de cobre '
    'acelerados para 2026 — más actividad minera implica más equipos, insumos y repuestos que mover. '
    'En paralelo, Chile y Perú están ampliando bodegas de cadena de frío para vino y alimentos, el '
    'diferenciador específico de GBS en carga temperada. Es coherente con la experiencia previa de '
    'Conprospección en servicios similares: estos sectores tienden a responder mejor cuando el mensaje '
    'es de visibilidad y continuidad operativa, no de precio.</div>',
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
    "La compra logística la decide la gerencia, pero la operan otras áreas",
    f"La vista contiene {REGf['area'].nunique()} áreas funcionales con actividad; Dirección/Gerencia concentra el volumen.",
    "Importar con regularidad involucra a Gerencia (decide), COMEX/Abastecimiento y Logística (operan).",
    "Buscar 2-3 perfiles por cuenta prioritaria y comparar respuesta por área.",
))
learning_rows.append(insight_row(
    "El ajuste de ICP redujo el universo pero mejoró la calidad de respuesta",
    "Se retiraron del ciclo cuentas peruanas fuera de perfil (tamaño o flujo de importación insuficiente).",
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
        "Lectura": "Ya cuenta con proveedor logístico vigente o no es prioridad en este momento.",
        "Acción": "Reforzar la propuesta de valor diferenciada (servicio integral, un solo interlocutor, "
                  "carga temperada) y programar un recontacto en el próximo trimestre.",
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
        "Tendencia": "La cartera de inversión minera en Chile sigue en expansión",
        "Por qué importa para GBS": "USD 104.500 millones proyectados a 2034 y 13 proyectos de cobre "
                                    "acelerados para 2026 significan más equipos, insumos y repuestos por mover.",
        "Segmentos conectados": "Minería y Metales, Maquinaria e Industria",
        "Fuente": "EY / Mining.com — Cartera de Inversión Minera Chile 2026",
    },
    {
        "Tendencia": "Chile se consolida como plataforma logística regional",
        "Por qué importa para GBS": "Más de 65 acuerdos comerciales y mejoras en ventanilla única aduanera "
                                    "refuerzan a Chile como corredor de reexportación hacia Perú, Bolivia y Colombia.",
        "Segmentos conectados": "Importación / Exportación, Retail y Consumo",
        "Fuente": "Mordor Intelligence — Chile & Peru Freight and Logistics Market",
    },
    {
        "Tendencia": "Expansión de bodegas de cadena de frío en Chile y Perú",
        "Por qué importa para GBS": "Ambos países están sumando bodegas Clase A de cadena de frío; "
                                    "encaja directo con el diferenciador de GBS en carga temperada para vino y alimentos.",
        "Segmentos conectados": "Alimentos, Bebidas y Agro",
        "Fuente": "Mordor Intelligence — Chile & Peru Freight and Logistics Market",
    },
])
st.markdown(html_table(market_context), unsafe_allow_html=True)
st.caption(
    "Fuentes: EY / Mining.com (cartera de inversión minera en Chile 2026) y Mordor Intelligence "
    "(mercado de carga y logística Chile-Perú), cruzadas con la respuesta observada en el ciclo."
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
        "Acción Conprospección": "Sumar COMEX/Abastecimiento y Logística además de Gerencia en cada cuenta prioritaria.",
        "Indicador": "2-3 áreas activadas por cuenta",
    },
    {
        "Decisión": "Blindar la lista de exclusión de clientes activos",
        "Acción Conprospección": "Revisar y cruzar la lista de clientes activos de GBS contra cada nueva carga "
                                  "de contactos antes de lanzar campaña, para que no vuelva a ocurrir.",
        "Indicador": "Cero clientes activos recontactados por campaña",
    },
    {
        "Decisión": "Retomar el listado de cuentas objetivo",
        "Acción Conprospección": f"Priorizar la prospección de la lista de cuentas objetivo entregada por GBS "
                                  f"({OBJ['total']} empresas) en el próximo lote.",
        "Indicador": "Cuentas objetivo activadas",
    },
    {
        "Decisión": "Vender dolor, no flete",
        "Acción Conprospección": "Separar copy por servicio integral, visibilidad de carga, asesoría aduanera y carga temperada.",
        "Indicador": "Tasa positiva por tema de mensaje",
    },
])
st.markdown(html_table(next_steps), unsafe_allow_html=True)
st.markdown(
    f'<div style="background:{CP_GOLD_SOFT};border:1px solid #F0D28D;border-left:5px solid {CP_GOLD};'
    f'border-radius:11px;padding:15px 18px;margin-top:12px;font-size:13px;line-height:1.65;color:#5A4A00">'
    f'<b>Hipótesis del ciclo 2:</b> Los importadores de minería, maquinaria y alimentos contactados desde '
    f'Gerencia y luego COMEX/Abastecimiento responderán mejor a mensajes de servicio integral y visibilidad '
    f'de carga que a un mensaje genérico de flete.<br><b>Cómo lo vamos a validar:</b> En el próximo ciclo '
    f'compararemos la tasa positiva y las reuniones agendadas de este segmento contra el resto, una vez que '
    f'acumule más volumen de conversaciones.</div>',
    unsafe_allow_html=True,
)


# ===== Descargas =====
def report_table(df):
    if df is None or df.empty:
        return '<div class="empty">Sin registros para la selección activa.</div>'
    return df.to_html(index=False, border=0, classes="report-table", escape=True)


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
.report-table th{{background:{CP_MUTED_SURFACE};color:{CP_CARBON};text-align:left;padding:9px;border:1px solid {CP_LINE};white-space:normal;overflow-wrap:break-word}}
.report-table td{{padding:8px;border:1px solid {CP_LINE};vertical-align:top;white-space:normal;overflow-wrap:break-word}}
.note{{background:{CP_GOLD_SOFT};border-left:5px solid {CP_GOLD};padding:14px 17px;border-radius:8px}}
.method{{font-size:11px;color:{CP_MUTED};background:#fff;padding:14px;border:1px solid {CP_LINE};border-radius:9px}}
.empty{{padding:14px;background:{CP_MUTED_SURFACE};color:{CP_MUTED};border:1px dashed {CP_LINE_STRONG}}}
a{{color:{CP_ORANGE}}}@media print{{body{{padding:0}} .hero{{break-inside:avoid}}}}
</style></head><body>
<div class="hero"><h1>Intelligence Insight - GBS Logistics</h1>
<p>Reporte del ciclo comercial - generado desde el panel interno de Conprospección</p></div>
<div class="filter"><b>Selección exportada:</b> {start_date:%d/%m/%Y}-{end_date:%d/%m/%Y} ·
Macroindustria: {f_ind} · Macrocargo: {f_area}</div>
<h2>Resumen ejecutivo</h2>
<div class="kpis">{kpi_html}</div>
<div class="note"><b>Avance contractual:</b> {REAL['validas']} de {META} reuniones válidas ({pct_meta}%).</div>
<h2>Volumen de gestión por canal</h2>{report_table(CANAL_ACTIVIDAD.rename(columns={"canal": "Canal", "gestiones": "Gestiones"}))}
<div class="method">Un mismo contacto puede haber sido gestionado por más de un canal; estos volúmenes no son mutuamente excluyentes.</div>
<h2>Resultados de conversación</h2>{report_table(results_report)}
<div class="method">Positivas = información adicional + coordinando reunión + reunión agendada ({pos_desglose_txt}).</div>
<h2>Reuniones y cotizaciones del ciclo</h2>{report_table(reuniones_df)}
<h2>Respuesta por segmento</h2>{report_table(segment_report if not segments.empty else pd.DataFrame())}
<h2>Qué aprendimos del mercado</h2>{report_table(pd.DataFrame(learning_rows))}
<h2>Mensajes y dolores que están resonando</h2>{report_table(theme_df)}
<h2>Negativas y objeciones</h2>{report_table(pd.DataFrame(objection_rows))}
<h2>Contexto de mercado relevante</h2>{report_table(market_context)}
<h2>Próximos pasos</h2>{report_table(next_steps)}
<div class="note"><b>Hipótesis del ciclo 2:</b> los importadores de minería, maquinaria y alimentos contactados desde
Gerencia y luego COMEX/Abastecimiento responderán mejor a mensajes de servicio integral y visibilidad de carga.</div>
</body></html>"""


def _pdf_df_segmentos() -> pd.DataFrame:
    if segments.empty:
        return pd.DataFrame()
    df = segments.copy()
    df["Segmento"] = df["Macroindustria"] + " + " + df["Macrocargo"]
    df["Tasa positiva"] = df["Tasa positiva"].map(lambda x: f"{x:.0%}")
    return df[["Segmento", "Cuentas activadas", "Conversaciones", "Positivas", "Tasa positiva",
               "Reuniones", "Señal", "Decisión"]].head(10)


def _pdf_table_cards(pdf: FPDF, df: pd.DataFrame, *, max_rows: int | None = None) -> None:
    if df is None or df.empty:
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(100, 116, 139)
        pdf.multi_cell(0, 5, _lat("Sin registros para la selección activa."))
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
    pdf.cell(0, 5, _lat(f"{start_date:%d/%m/%Y}-{end_date:%d/%m/%Y} | Industria: {f_ind} | Área: {f_area}"), ln=1)
    pdf.set_y(38)

    _pdf_section(pdf, "Resumen ejecutivo", "Estado del ciclo y avance contractual")
    resumen = pd.DataFrame([
        {"Métrica": "Avance meta", "Valor": f"{REAL['validas']} / {META} ({pct_meta}%)"},
        {"Métrica": "Gestiones", "Valor": len(REGf)},
        {"Métrica": "Conversaciones", "Valor": fconv},
        {"Métrica": "Respuestas positivas", "Valor": fpostot},
        {"Métrica": "Tasa positiva", "Valor": f"{tasa:.0%}"},
    ])
    _pdf_table_cards(pdf, resumen)

    _pdf_section(pdf, "Volumen de gestión por canal")
    _pdf_table_cards(pdf, CANAL_ACTIVIDAD.rename(columns={"canal": "Canal", "gestiones": "Gestiones"}))

    _pdf_section(pdf, "Reuniones y cotizaciones del ciclo")
    _pdf_table_cards(pdf, reuniones_df)

    _pdf_section(pdf, "Resultados de conversación")
    _pdf_table_cards(pdf, pd.DataFrame([
        {"Resultado": RES_LABEL[key], "Cantidad": conteo(REGf, key)}
        for key in ["positiva", "deriva", "negativa", "no_califica", "no_contesta", "numero_malo"]
    ]).sort_values("Cantidad", ascending=False))

    _pdf_section(pdf, "Respuesta por segmento", "Top 10 por reuniones, positivas y conversaciones")
    _pdf_table_cards(pdf, _pdf_df_segmentos(), max_rows=10)

    _pdf_section(pdf, "Qué aprendimos del mercado")
    _pdf_table_cards(pdf, pd.DataFrame(learning_rows))

    _pdf_section(pdf, "Mensajes y dolores que están resonando")
    _pdf_table_cards(pdf, theme_df)

    _pdf_section(pdf, "Negativas y objeciones")
    _pdf_table_cards(pdf, pd.DataFrame(objection_rows))

    _pdf_section(pdf, "Contexto de mercado relevante")
    _pdf_table_cards(pdf, market_context)

    _pdf_section(pdf, "Próximos pasos")
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
