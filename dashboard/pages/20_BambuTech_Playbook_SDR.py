"""Playbook SDR embebido en el portal de BambuTech Services."""
import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from portal_auth import render_bambutech_page_header, render_client_nav, require_auth_client

st.set_page_config(page_title="BambuTech — Playbook SDR", layout="wide", page_icon="")
if not require_auth_client("bambutech"):
    st.stop()
render_client_nav("20_BambuTech_Playbook", "bambutech")

st.markdown(
    '<style>.block-container{max-width:1500px;padding-top:1.2rem!important}</style>',
    unsafe_allow_html=True,
)
render_bambutech_page_header(
    "Playbook SDR",
    "Ruta comercial interactiva de BambuTech Services",
)
components.iframe(
    "https://bambutechservices.playbook.report-conprospeccion.com/ruta",
    height=1700,
    scrolling=True,
)
