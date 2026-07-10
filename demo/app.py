"""Punto de entrada de la aplicacion DEMO para prospectos.

Aplicacion Streamlit independiente del panel interno. Se despliega como una
segunda app del mismo repositorio, con `demo/app.py` como Main file path.

Por que una app aparte y no una pagina mas del panel interno: Streamlit expone
TODAS las paginas de una app por URL. Mientras el demo vivia en dashboard/pages,
un prospecto que escribiera /Seguimiento_Reuniones aterrizaba en la pantalla de
login del equipo. Aqui esas paginas sencillamente no existen: no hay URL que
adivinar.

Rutas publicas:
    /                 -> redirige al Onboarding
    /demo             -> Formulario de Onboarding (entrada del recorrido)
    /demo_reuniones   -> Panel de Seguimiento de Reuniones

Credenciales: DEMO / DEMO2026 (ver shared/config.portal_passwords).

AISLAMIENTO: ninguna pagina de esta app importa requests, supabase, shared.config
ni meeting_shared. Es incapaz de leer o escribir en produccion.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_DIR = ROOT / "dashboard"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from portal_auth import require_auth_client

st.set_page_config(page_title="Conprospección — Demo", layout="wide")

# El login se dibuja aqui mismo. Solo tras autenticarse se entra al recorrido.
if not require_auth_client("demo"):
    st.stop()

st.switch_page("pages/demo.py")
