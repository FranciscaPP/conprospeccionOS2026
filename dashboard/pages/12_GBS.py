"""Portal cliente GBS Logistics — validación contractual de reuniones."""

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from client_meeting_portal import render_client_meeting_portal
from portal_auth import logout_client, require_auth_client

st.set_page_config(
    page_title="GBS Logistics - Validación Reuniones",
    layout="wide",
    page_icon="",
)

if not require_auth_client("gbs"):
    st.stop()

st.markdown(
    """
<style>
[data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
header[data-testid="stHeader"] { display: none !important; }
div[class*="st-key-gbs_logout"] {
  position: fixed; top: 16px; right: 18px; z-index: 1001; width: auto;
}
div[class*="st-key-gbs_logout"] button {
  background: rgba(255,255,255,.08) !important;
  color: #ececea !important;
  border: 1px solid rgba(255,255,255,.2) !important;
  font-size: 12px !important;
  padding: 5px 12px !important;
  min-height: 0 !important;
}
</style>
    """,
    unsafe_allow_html=True,
)

if st.button("Cerrar sesión", key="gbs_logout"):
    logout_client("gbs")
    st.rerun()

render_client_meeting_portal(
    client_slug="gbs",
    page_key="12_GBS_Validacion",
    title="Validación de reuniones",
    brand="GBS Logistics · Portal cliente",
    user_label="Usuario GBS",
    user_subtitle="Validación contractual",
)
