"""Portal cliente BambuTech - onboarding e ICP acordado."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from portal_auth import render_bambutech_page_header, render_client_nav, require_auth_client
from shared.bambutech_brand import ICP_DEFAULT
from shared.cp_design import CP_GOLD, CP_GOLD_SOFT, CP_INK, CP_LINE, CP_MUTED, CP_MUTED_SURFACE


st.set_page_config(page_title="BambuTech - Onboarding", layout="wide", page_icon="")
if not require_auth_client("bambutech"):
    st.stop()

render_client_nav("17_BambuTech_Onboarding", "bambutech")

st.markdown(
    """
<style>
.block-container{max-width:1180px;padding-top:1rem!important}
.bambu-card{background:#fff;border:1px solid #EDECEA;border-radius:8px;padding:18px 20px;margin-bottom:14px}
.bambu-card h3{margin:0 0 10px;color:#1A1A1A;font-size:16px}
.bambu-card p,.bambu-card li{color:#6B6B6B;font-size:13px;line-height:1.55}
.bambu-chip{display:inline-flex;margin:4px 5px 4px 0;padding:5px 9px;border-radius:999px;background:#FFF7BF;border:1px solid #F0D28D;color:#1A1A1A;font-size:11px;font-weight:800}
.bambu-line{display:flex;justify-content:space-between;gap:14px;border-bottom:1px solid #EDECEA;padding:9px 0;font-size:13px}
.bambu-line span:first-child{color:#6B6B6B}.bambu-line span:last-child{color:#1A1A1A;font-weight:800;text-align:right}
</style>
    """,
    unsafe_allow_html=True,
)

render_bambutech_page_header(
    "Onboarding",
    "Resumen ICP acordado, alcance comercial y criterios de validacion del proyecto",
)

st.markdown(
    f'<div class="bambu-card" style="border-left:5px solid {CP_GOLD}">'
    f'<h3>Resumen ICP acordado</h3>'
    f'<p>Esta es la referencia que usa Conprospeccion para evaluar fit comercial '
    f'en reuniones, campanas y analisis. La definicion queda centralizada para que '
    f'el equipo de BambuTech y Conprospeccion miren el mismo criterio.</p></div>',
    unsafe_allow_html=True,
)


def _chips(value: str) -> str:
    return "".join(
        f'<span class="bambu-chip">{item.strip()}</span>'
        for item in str(value or "").split(",")
        if item.strip()
    )


cols = st.columns(2)
with cols[0]:
    st.markdown(
        '<div class="bambu-card"><h3>Paises objetivo</h3>'
        + _chips(ICP_DEFAULT["icp_pais"])
        + "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="bambu-card"><h3>Tamano de empresa</h3>'
        + _chips(ICP_DEFAULT["icp_tamano"])
        + "</div>",
        unsafe_allow_html=True,
    )
with cols[1]:
    st.markdown(
        '<div class="bambu-card"><h3>Cargos objetivo</h3>'
        + _chips(ICP_DEFAULT["icp_cargos"])
        + "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="bambu-card"><h3>Industrias objetivo</h3>'
        + _chips(ICP_DEFAULT["icp_industrias"])
        + "</div>",
        unsafe_allow_html=True,
    )

st.markdown(
    f"""
<div class="bambu-card">
  <h3>Oferta y criterios comerciales</h3>
  <div class="bambu-line"><span>Propuesta de valor</span><span>{ICP_DEFAULT["propuesta_valor"]}</span></div>
  <div class="bambu-line"><span>Dolores prioritarios</span><span>{ICP_DEFAULT["dolores_clientes"]}</span></div>
  <div class="bambu-line"><span>Gatillos de compra</span><span>{ICP_DEFAULT["gatillos_compra"]}</span></div>
  <div class="bambu-line"><span>Exclusiones</span><span>{ICP_DEFAULT["icp_descarte"]}</span></div>
  <div class="bambu-line"><span>Keywords</span><span>{ICP_DEFAULT["keywords_prospecto"]}</span></div>
</div>
<div class="bambu-card" style="background:{CP_GOLD_SOFT};border-color:#F0D28D">
  <h3>Uso en validacion</h3>
  <p>El portal de reuniones muestra una sintesis del fit de cada prospecto. La
  evaluacion final combina este ICP, la informacion disponible de la reunion y
  la revision operativa de Conprospeccion.</p>
</div>
    """,
    unsafe_allow_html=True,
)
