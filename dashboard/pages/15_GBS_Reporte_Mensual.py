"""Portal GBS — Generar Reporte Mensual (tier base): elegir hasta 5 KPIs y exportar PDF."""
import sys
from pathlib import Path

import requests
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from shared.config import supabase_url, supabase_key
from shared.gbs_brand import GBS_PURPLE, GBS_BORDER
from shared.gbs_data import cargar_dataset
from shared.kpis import KPI_CATALOGO, KPI_LABEL, compute_kpis
from shared.pdf_report import construir_pdf
from shared.seguimiento import cargar as cargar_seg
from portal_auth import require_auth_client, render_client_nav, img_b64

st.set_page_config(page_title="GBS Logistics — Reporte Mensual", layout="wide", page_icon="")

if not require_auth_client("gbs"):
    st.stop()
render_client_nav("15_GBS_Reporte", "gbs")

SB_URL = supabase_url()
SB_KEY = supabase_key()
_H = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"}
_HW = {**_H, "Content-Type": "application/json"}
MAX_KPIS = 5

st.markdown(
    f'<style>button[kind="primary"]{{background:{GBS_PURPLE}!important;border:none!important;'
    f'color:#fff!important;font-weight:700!important}}'
    f'span[data-baseweb="tag"]{{background:#ede9fe!important;color:#5b21b6!important}}'
    f'span[data-baseweb="tag"] span{{color:#5b21b6!important}}'
    f'span[data-baseweb="tag"] svg{{fill:#5b21b6!important}}</style>',
    unsafe_allow_html=True)

if not st.session_state.get("admin_mode"):
    st.markdown(
        f'<div style="max-width:720px;margin:56px auto;background:#fff;border:1px solid {GBS_BORDER};'
        f'border-left:6px solid {GBS_PURPLE};border-radius:14px;padding:28px 30px;'
        f'box-shadow:0 8px 24px rgba(91,33,182,.08)">'
        f'<div style="font-size:20px;font-weight:850;color:#1e293b;margin-bottom:8px">'
        f'Reportes para tu equipo</div>'
        f'<div style="font-size:14px;color:#475569;line-height:1.6">'
        f'Este módulo ya forma parte de tu portal, pero todavía no tiene datos habilitados. '
        f'Conprospección lo activará cuando el reporte operativo de GBS esté listo para publicación.'
        f'</div><div style="margin-top:14px;font-size:12px;font-weight:750;color:{GBS_PURPLE};">'
        f'No necesitas realizar ninguna acción.</div></div>',
        unsafe_allow_html=True,
    )
    st.stop()

# ── Header (mismo estilo que el resto de GBS) ──
g = img_b64("gbs_logo.png", 52) or ""
c = img_b64("conprospeccion_logo.png", 42) or ""
st.markdown(
    f'<div style="display:flex;align-items:center;justify-content:space-between;'
    f'background:linear-gradient(135deg,#faf5ff,#ede9fe);padding:18px 28px;border-radius:14px;'
    f'border:1px solid {GBS_BORDER};margin-bottom:14px;box-shadow:0 2px 8px rgba(0,0,0,.06)">'
    f'<div style="display:flex;align-items:center;gap:18px">{g}'
    f'<div><div style="font-size:22px;font-weight:800;color:#1e293b">Generar Reporte Mensual</div>'
    f'<div style="font-size:13px;color:#64748b;margin-top:3px">'
    f'Elegir hasta 5 KPIs y exportar el reporte del mes en PDF</div></div></div>{c}</div>',
    unsafe_allow_html=True)


def _load_sel():
    r = requests.get(f"{SB_URL}/rest/v1/reporte_config?cliente_slug=eq.gbs&select=kpis",
                     headers=_H, timeout=10)
    if r.ok and r.json():
        ids = [x for x in (r.json()[0].get("kpis") or "").split(",") if x]
        if ids:
            return ids
    return ["contactos", "respuestas", "positivas", "agendadas", "avance_meta"]


def _save_sel(ids):
    requests.post(
        f"{SB_URL}/rest/v1/reporte_config",
        json={"cliente_slug": "gbs", "kpis": ",".join(ids), "updated_at": "now()"},
        headers={**_HW, "Prefer": "resolution=merge-duplicates,return=minimal"}, timeout=10)


if "rep_sel" not in st.session_state:
    st.session_state["rep_sel"] = _load_sel()

c1, _ = st.columns([2, 3])
with c1:
    periodo = st.selectbox("Período", ["Todos", "Mayo 2026", "Junio 2026"], key="rep_periodo")

st.markdown(
    f'<div style="font-size:14px;font-weight:700;color:#1e293b;margin:8px 0 4px">'
    f'Elegir los KPIs del reporte (máximo {MAX_KPIS})</div>', unsafe_allow_html=True)
sel = st.multiselect(
    "KPIs del reporte", [k["id"] for k in KPI_CATALOGO],
    default=st.session_state["rep_sel"], format_func=lambda x: KPI_LABEL[x],
    key="rep_ms", placeholder="Seleccionar opciones",
    label_visibility="collapsed")
if len(sel) > MAX_KPIS:
    st.warning(f"Máximo {MAX_KPIS} KPIs. Se toman los primeros {MAX_KPIS}.")
    sel = sel[:MAX_KPIS]

cb1, _ = st.columns([1, 4])
with cb1:
    if st.button("Guardar selección", key="rep_save"):
        _save_sel(sel)
        st.session_state["rep_sel"] = sel
        st.toast("Selección guardada")

# ── Datos + cómputo ──
df = cargar_dataset()
if periodo != "Todos":
    df = df[df.periodo == periodo]
seg = cargar_seg("gbs")
validas_final = sum(1 for v in seg.values()
                    if str(v.get("val_estado_final", "")).lower() in ("valida", "reunion_valida"))
comp = compute_kpis(df, "gbs", validas_final)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    '<div style="font-size:14px;font-weight:700;color:#1e293b;margin-bottom:6px">Vista previa</div>',
    unsafe_allow_html=True)

if not sel:
    st.info("Elegir al menos un KPI para ver la vista previa y generar el PDF.")
else:
    cols = st.columns(min(len(sel), 3))
    for i, kid in enumerate(sel):
        valor, sub = comp.get(kid, ("—", ""))
        with cols[i % len(cols)]:
            st.markdown(
                f'<div style="background:#fff;border:1px solid {GBS_BORDER};border-radius:12px;'
                f'padding:14px 16px;margin-bottom:10px">'
                f'<div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.5px">'
                f'{KPI_LABEL[kid]}</div>'
                f'<div style="font-size:22px;font-weight:800;color:{GBS_PURPLE};margin-top:2px">{valor}</div>'
                f'<div style="font-size:11px;color:#64748b">{sub}</div></div>',
                unsafe_allow_html=True)

    pdf_bytes = construir_pdf("GBS Logistics", periodo, sel, comp)
    st.download_button(
        "Generar y exportar PDF", data=pdf_bytes,
        file_name=f"reporte_gbs_{periodo.replace(' ', '_').lower()}.pdf",
        mime="application/pdf", type="primary")

st.caption("Reporte mensual: los 5 KPIs que elijas se exportan en PDF. El análisis completo "
           "(efectividad por segmento, ICP real, recomendaciones) está disponible en el plan premium.")
