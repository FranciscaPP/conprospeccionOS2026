"""Portal cliente BambuTech - Playbook SDR oficial."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from portal_auth import render_bambutech_page_header, render_client_nav, require_auth_client
from shared.cp_design import CP_GOLD, CP_GOLD_SOFT, CP_INK, CP_LINE, CP_MUTED


PLAYBOOK_URL = "https://bambutechservices.playbook.report-conprospeccion.com/ruta"

st.set_page_config(page_title="Bamboo Touch - Playbook SDR", layout="wide", page_icon="")
if not require_auth_client("bambutech"):
    st.stop()

render_client_nav("20_BambuTech_Playbook_SDR", "bambutech")

st.markdown(
    f"""
<style>
.block-container{{max-width:1280px;padding-top:1rem!important}}
.pb-shell{{background:#fff;border:1px solid {CP_LINE};border-radius:8px;padding:14px 16px;margin-bottom:12px}}
.pb-shell p{{margin:0;color:{CP_MUTED};font-size:13px;line-height:1.5}}
.pb-link{{display:inline-flex;align-items:center;justify-content:center;border-radius:8px;
background:{CP_GOLD};color:{CP_INK}!important;font-weight:850;text-decoration:none;
padding:9px 14px;border:1px solid #F0D28D}}
</style>
    """,
    unsafe_allow_html=True,
)

render_bambutech_page_header(
    "Playbook SDR",
    "Playbook comercial oficial alojado por Conprospeccion",
)

st.markdown(
    f"""
<div class="pb-shell" style="border-left:5px solid {CP_GOLD};background:{CP_GOLD_SOFT}">
  <p>Este modulo muestra el Playbook SDR oficial de BambooTech. Si el navegador no permite verlo
  embebido, abre el link publico en una pestaña nueva.</p>
  <div style="height:10px"></div>
  <a class="pb-link" href="{PLAYBOOK_URL}" target="_blank" rel="noopener">Abrir playbook oficial</a>
</div>
    """,
    unsafe_allow_html=True,
)

components.iframe(PLAYBOOK_URL, height=900, scrolling=True)
