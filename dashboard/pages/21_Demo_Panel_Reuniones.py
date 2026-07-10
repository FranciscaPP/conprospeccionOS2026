"""Portal DEMO - panel de Seguimiento de Reuniones con datos ficticios.

Misma interfaz que el panel interno (pages/1_Seguimiento_Reuniones.py): ambas
paginas montan el HTML de seguimiento_poc_template.py. La diferencia es de donde
salen las reuniones y que pasa cuando el usuario guarda.

  panel interno -> cargar_reuniones_reales_poc()  -> escribe en Supabase
  portal demo   -> cargar_reuniones_demo()        -> descarta el guardado

AISLAMIENTO: esta pagina no importa requests, supabase, shared.config ni
meeting_shared. Es incapaz de leer o escribir en produccion.

El prospecto puede filtrar, abrir reuniones y cambiar estados. Los cambios viven
en memoria y se pierden al recargar, asi el portal se auto-resetea para el
siguiente prospecto.
"""
from __future__ import annotations

import base64
import sys
import tempfile
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from meeting_component import render_meeting_component
from portal_auth import render_client_nav, require_auth_client
from seguimiento_poc_template import PlantillaDesincronizada, construir_html_demo
from shared.demo_data import cargar_reuniones_demo

st.set_page_config(page_title="Demo - Seguimiento Reuniones", layout="wide")

if not require_auth_client("demo"):
    st.stop()

render_client_nav("21_Demo_Panel_Reuniones", "demo")


def _asset_data_uri(relative_path: str, mime: str = "image/png") -> str:
    path = DASHBOARD_DIR / relative_path
    try:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    except Exception:
        return ""
    return f"data:{mime};base64,{encoded}"


try:
    html = construir_html_demo(
        cargar_reuniones_demo(),
        _asset_data_uri("assets/cp_mark_dark.png"),
    )
except PlantillaDesincronizada as error:
    st.error(f"El portal demo no se pudo construir. {error}")
    st.stop()

COMPONENT_DIR = Path(tempfile.gettempdir()) / "cp_demo_panel_reuniones_component"
COMPONENT_DIR.mkdir(parents=True, exist_ok=True)
(COMPONENT_DIR / "index.html").write_text(html, encoding="utf-8")

# El componente devuelve payloads cuando el usuario guarda, crea o elimina.
# El demo los ignora deliberadamente: no hay backend al que escribir.
render_meeting_component(COMPONENT_DIR, key="demo_panel_reuniones")
