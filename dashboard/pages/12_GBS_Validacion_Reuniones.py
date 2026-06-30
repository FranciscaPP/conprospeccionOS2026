"""Portal cliente GBS Logistics — validación contractual de reuniones."""

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from client_meeting_portal import render_client_meeting_portal
from portal_auth import render_client_nav, require_auth_gbs

st.set_page_config(
    page_title="GBS Logistics - Validación Reuniones",
    layout="wide",
    page_icon="",
)

if not require_auth_gbs():
    st.stop()

render_client_nav("12_GBS_Validacion", "gbs")
render_client_meeting_portal(
    client_slug="gbs",
    page_key="12_GBS_Validacion",
    title="Validación de reuniones",
    brand="GBS Logistics · Portal cliente",
    user_label="Usuario GBS",
    user_subtitle="Validación contractual",
)
