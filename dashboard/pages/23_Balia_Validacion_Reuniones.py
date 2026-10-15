"""Portal cliente Balia - validacion contractual de reuniones."""
from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from client_meeting_portal import render_client_meeting_portal
from portal_auth import render_client_nav, require_auth_client


st.set_page_config(
    page_title="Balia - Validacion Reuniones",
    layout="wide",
    page_icon="",
)

if not require_auth_client("balia"):
    st.stop()

render_client_nav("23_Balia_Validacion_Reuniones", "balia")

render_client_meeting_portal(
    client_slug="balia",
    page_key="23_Balia_Validacion_Reuniones",
    title="Validacion de reuniones",
    brand="Balia - Portal cliente",
    user_label="Usuario Balia",
    user_subtitle="Validacion contractual",
    hide_chrome=False,
)
