"""Playbook SDR embebido en el portal de BambuTech Services."""
import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from portal_auth import img_b64, render_client_nav, require_auth_client

st.set_page_config(page_title="BambuTech — Playbook SDR", layout="wide", page_icon="")
if not require_auth_client("bambutech"):
    st.stop()
render_client_nav("20_BambuTech_Playbook", "bambutech")

st.markdown(
    '<style>.block-container{max-width:1500px;padding-top:1.2rem!important}</style>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<div style="display:flex;align-items:center;gap:20px;background:linear-gradient(135deg,#07110c,#0e1b15);'
    f'padding:20px 27px;border-radius:14px;color:#fff;margin-bottom:14px">'
    f'{img_b64("bambutech_logo.png", 58)}'
    f'<div><div style="font-size:23px;font-weight:850">Playbook SDR</div>'
    f'<div style="font-size:12px;color:#baf8d0;margin-top:4px">'
    f'Ruta comercial interactiva de BambuTech Services</div></div></div>',
    unsafe_allow_html=True,
)
components.iframe(
    "https://bambutechservices.playbook.report-conprospeccion.com/ruta",
    height=1700,
    scrolling=True,
)
