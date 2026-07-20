"""Portal cliente BambuTech - Playbook SDR embebido."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from portal_auth import render_bambutech_page_header, render_client_nav, require_auth_client
from shared.bambutech_brand import BAMBU_GREEN, BAMBU_GREEN_BG, ICP_DEFAULT


st.set_page_config(page_title="Bamboo Touch - Playbook SDR", layout="wide", page_icon="")
if not require_auth_client("bambutech"):
    st.stop()

render_client_nav("20_BambuTech_Playbook_SDR", "bambutech")

st.markdown(
    """
<style>
.block-container{max-width:1180px;padding-top:1rem!important}
.pb-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
.pb-card{background:#fff;border:1px solid #d9dfda;border-radius:12px;padding:17px 18px;min-height:144px}
.pb-card h3{margin:0 0 8px;color:#171918;font-size:15px}
.pb-card p,.pb-card li{color:#475569;font-size:13px;line-height:1.55}
.pb-section{background:#fff;border:1px solid #d9dfda;border-radius:12px;padding:18px 20px;margin:14px 0}
.pb-section h3{margin:0 0 10px;color:#171918;font-size:16px}
@media(max-width:1000px){.pb-grid{grid-template-columns:1fr}}
</style>
    """,
    unsafe_allow_html=True,
)

render_bambutech_page_header(
    "Playbook SDR",
    "Guia comercial viva para prospeccion, mensajes, objeciones y aprendizaje del ciclo",
)

st.markdown(
    f'<div class="pb-section" style="border-left:5px solid {BAMBU_GREEN}">'
    '<h3>Posicionamiento comercial</h3>'
    f'<p>{ICP_DEFAULT["propuesta_valor"]}</p></div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="pb-grid">
  <div class="pb-card">
    <h3>1. Apertura</h3>
    <p>Conectar con transformacion digital, eficiencia operativa, integracion de sistemas o modernizacion tecnologica.</p>
  </div>
  <div class="pb-card">
    <h3>2. Calificacion</h3>
    <p>Validar necesidad, autoridad, urgencia, stack actual, impacto del problema y disposicion a explorar una solucion.</p>
  </div>
  <div class="pb-card">
    <h3>3. Proxima accion</h3>
    <p>Buscar reunion diagnostica con el decisor o derivacion clara al area responsable de tecnologia/operaciones.</p>
  </div>
</div>
    """,
    unsafe_allow_html=True,
)

tabs = st.tabs(["Mensajes", "ICP", "Objeciones", "Evidencia"])
with tabs[0]:
    st.markdown(
        f"""
<div class="pb-section">
  <h3>Angulos de mensaje</h3>
  <ul>
    <li>Reducir procesos manuales y tiempos operativos con automatizacion.</li>
    <li>Integrar datos dispersos para mejorar visibilidad y toma de decisiones.</li>
    <li>Modernizar plataformas sin depender de soluciones genericas que no calzan con el negocio.</li>
    <li>Fortalecer seguridad, continuidad operacional y escalabilidad tecnologica.</li>
  </ul>
</div>
        """,
        unsafe_allow_html=True,
    )
with tabs[1]:
    st.markdown(
        f"""
<div class="pb-section">
  <h3>Criterio ICP</h3>
  <p><b>Paises:</b> {ICP_DEFAULT["icp_pais"]}</p>
  <p><b>Industrias:</b> {ICP_DEFAULT["icp_industrias"]}</p>
  <p><b>Cargos:</b> {ICP_DEFAULT["icp_cargos"]}</p>
  <p><b>Descarte:</b> {ICP_DEFAULT["icp_descarte"]}</p>
</div>
        """,
        unsafe_allow_html=True,
    )
with tabs[2]:
    st.markdown(
        """
<div class="pb-section">
  <h3>Manejo de objeciones</h3>
  <ul>
    <li><b>Ya tenemos proveedor:</b> preguntar que parte del stack actual sigue generando friccion o deuda operativa.</li>
    <li><b>No es prioridad:</b> conectar con costo de oportunidad, riesgos y backlog tecnologico.</li>
    <li><b>No hay presupuesto:</b> proponer diagnostico acotado y priorizacion por impacto.</li>
    <li><b>Mandar informacion:</b> pedir contexto para enviar un caso o enfoque relevante, no un brochure generico.</li>
  </ul>
</div>
        """,
        unsafe_allow_html=True,
    )
with tabs[3]:
    st.markdown(
        f"""
<div class="pb-section" style="background:{BAMBU_GREEN_BG}">
  <h3>Evidencia que debe levantar el SDR</h3>
  <ul>
    <li>Problema operativo o tecnologico mencionado por el prospecto.</li>
    <li>Area responsable y decisor involucrado.</li>
    <li>Sistema, proceso o iniciativa actual relacionada.</li>
    <li>Motivo de interes, urgencia o ventana de evaluacion.</li>
  </ul>
</div>
        """,
        unsafe_allow_html=True,
    )
