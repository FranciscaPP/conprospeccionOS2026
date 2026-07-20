"""Portal cliente BambooTech: entrada publica con acceso a todos los modulos."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from portal_auth import render_bambutech_page_header, render_client_nav, require_auth_client
from shared.cp_design import CP_CARBON, CP_GOLD, CP_GOLD_SOFT, CP_INK, CP_LINE, CP_MUTED, CP_MUTED_SURFACE, CP_ORANGE
from shared.planes import plan_de


st.set_page_config(page_title="BambooTech - Portal Cliente", layout="wide", page_icon="")
if not require_auth_client("bambutech"):
    st.stop()

render_client_nav("15_BambooTech", "bambutech")

st.markdown(
    """
<style>
.block-container{max-width:1180px;padding-top:1rem!important}
.portal-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-top:14px}
.portal-card{background:#fff;border:1px solid #EDECEA;border-radius:8px;padding:18px;min-height:156px}
.portal-card h3{margin:0 0 8px;color:#1A1A1A;font-size:16px}
.portal-card p{margin:0;color:#6B6B6B;font-size:13px;line-height:1.52}
.portal-pill{display:inline-flex;margin-top:14px;padding:5px 10px;border-radius:999px;background:#FFF7BF;border:1px solid #F0D28D;color:#1A1A1A;font-size:11px;font-weight:850}
div[class*="st-key-bamboo_"] button{border-radius:9px!important;font-weight:800!important}
@media(max-width:1050px){.portal-grid{grid-template-columns:1fr 1fr}}
@media(max-width:720px){.portal-grid{grid-template-columns:1fr}}
</style>
    """,
    unsafe_allow_html=True,
)

render_bambutech_page_header(
    "Portal cliente",
    "Validacion de reuniones, Intelligence Insight, onboarding y Playbook SDR",
)

premium_note = "Habilitado" if plan_de("bambutech") == "premium" else "No disponible en este plan"

st.markdown(
    f"""
<div style="background:{CP_GOLD_SOFT};border:1px solid #F0D28D;border-left:5px solid {CP_GOLD};
border-radius:8px;padding:14px 18px;color:{CP_INK};font-size:13px;line-height:1.55">
Este es el punto de entrada publico del portal BambooTech. Desde aqui el cliente puede revisar
sus reuniones, consultar el avance comercial y acceder al material operativo del proyecto.
</div>
<div class="portal-grid">
  <div class="portal-card">
    <h3>Validacion de reuniones</h3>
    <p>Revision contractual de reuniones para confirmar validez o solicitar revision con motivo y comentario.</p>
    <span class="portal-pill">Modulo principal</span>
  </div>
  <div class="portal-card">
    <h3>Intelligence Insight</h3>
    <p>Dashboard de estrategia comercial, resultados por canal, segmentos, aprendizajes y siguientes pasos.</p>
    <span class="portal-pill">{premium_note}</span>
  </div>
  <div class="portal-card">
    <h3>Onboarding</h3>
    <p>Resumen ICP acordado, paises, industrias, cargos objetivo, propuesta de valor y criterios de descarte.</p>
    <span class="portal-pill">Base del proyecto</span>
  </div>
  <div class="portal-card">
    <h3>Playbook SDR</h3>
    <p>Guia comercial para mensajes, calificacion, objeciones y evidencia que debe levantar el equipo SDR.</p>
    <span class="portal-pill">Operacion comercial</span>
  </div>
</div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
cols = st.columns(4)
with cols[0]:
    if st.button("Abrir validacion", key="bamboo_open_validation", use_container_width=True, type="primary"):
        st.switch_page("pages/18_BambuTech_Validacion_Reuniones.py")
with cols[1]:
    if st.button("Abrir Intelligence", key="bamboo_open_intelligence", use_container_width=True):
        st.switch_page("pages/19_BambuTech_Intelligence_Insight.py")
with cols[2]:
    if st.button("Abrir onboarding", key="bamboo_open_onboarding", use_container_width=True):
        st.switch_page("pages/17_BambuTech_Onboarding.py")
with cols[3]:
    if st.button("Abrir playbook", key="bamboo_open_playbook", use_container_width=True):
        st.switch_page("pages/20_BambuTech_Playbook_SDR.py")
