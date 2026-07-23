"""GBS Logistics - indicadores."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from portal_auth import render_client_nav, require_auth_client
from shared.cp_design import CP_GOLD, CP_GOLD_SOFT, CP_INK, CP_LINE, CP_MUTED, CP_MUTED_SURFACE


st.set_page_config(page_title="GBS Logistics - Indicadores", layout="wide", page_icon="")
if not require_auth_client("gbs"):
    st.stop()

render_client_nav("11_GBS", "gbs")

st.markdown(
    f"""
<style>
.block-container{{max-width:1180px;padding-top:1rem!important}}
.gbs-hero{{background:{CP_MUTED_SURFACE};border:1px solid {CP_LINE};border-top:5px solid {CP_GOLD};
border-radius:8px;padding:24px 28px;margin-bottom:16px}}
.gbs-hero h1{{margin:0;color:{CP_INK};font-size:24px}}
.gbs-hero p,.gbs-card p{{margin:6px 0 0;color:{CP_MUTED};font-size:13px;line-height:1.55}}
.gbs-grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}}
.gbs-card{{background:#fff;border:1px solid {CP_LINE};border-radius:8px;padding:18px 20px;margin-bottom:14px}}
.gbs-card h3{{margin:0 0 8px;color:{CP_INK};font-size:16px}}
@media(max-width:900px){{.gbs-grid{{grid-template-columns:1fr}}}}
</style>
<div class="gbs-hero">
  <h1>Indicadores GBS Logistics</h1>
  <p>Accesos principales del portal cliente. El reporte Intelligence Insight completo se mantiene
  en el panel interno de Conprospeccion.</p>
</div>
<div class="gbs-grid">
  <div class="gbs-card"><h3>Validacion de reuniones</h3><p>Revision contractual de reuniones agendadas y estado final.</p></div>
  <div class="gbs-card"><h3>Onboarding</h3><p>ICP, criterios comerciales y fuentes del proyecto.</p></div>
  <div class="gbs-card"><h3>Playbook SDR</h3><p>Material operativo disponible en la carpeta oficial del cliente.</p></div>
</div>
<div class="gbs-card" style="background:{CP_GOLD_SOFT};border-color:#F0D28D">
  <h3>Reporte ejecutivo</h3>
  <p>El dashboard Intelligence Insight de GBS esta disponible para el equipo interno desde el menu principal.</p>
</div>
    """,
    unsafe_allow_html=True,
)
