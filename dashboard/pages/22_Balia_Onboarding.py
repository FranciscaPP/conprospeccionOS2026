"""Portal cliente Balia - onboarding comercial editable."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from onboarding_form import render_onboarding_form
from portal_auth import render_client_nav, require_auth_client

st.set_page_config(page_title="Balia - Onboarding", layout="wide", page_icon="")
if not require_auth_client("balia"):
    st.stop()

render_client_nav("22_Balia_Onboarding", "balia")

render_onboarding_form(
    {
        "slug": "balia",
        "client_name": "Balia",
        "logo_file": "balia_logo.png",
        # Acento azul (default del portal para clientes nuevos).
        "accent": "#1e40af",
        "accent_2": "#2563eb",
        "soft": "#eff6ff",
        "border": "#bfdbfe",
        "ink": "#0f172a",
        # Listas de opciones genéricas B2B LATAM. El cliente elige lo que aplique;
        # ajústalas cuando tengas su perfil comercial definido.
        "cargo_opts": [
            "CEO", "CFO", "CMO", "COO", "CTO", "CIO",
            "Gerente General", "Gerente Comercial", "Gerente de Marketing",
            "Gerente de Operaciones", "Gerente de Ventas", "Gerente de Finanzas",
            "Gerente de Compras", "Director Comercial", "Director de Operaciones",
            "Dueño / Fundador", "Subgerente Comercial", "Jefe de Proyectos",
        ],
        "industria_opts": [
            "Abierto", "Retail y consumo", "Servicios financieros", "Alimentos y bebidas",
            "Logística y transporte", "Seguros", "Automotriz", "Construcción",
            "Salud y farmacéutica", "Manufactura", "Minería", "Energía",
            "Telecomunicaciones", "Tecnología", "Educación", "Turismo y hotelería",
            "Servicios profesionales", "Gobierno / sector público",
        ],
        "descarte_opts": [
            "Competidores directos",
            "Empresas sin capacidad de inversión",
            "Empresas fuera de los mercados objetivo",
            "Cuentas sin decisor accesible",
            "Microempresas sin presupuesto",
            "Rubros no rentables para el servicio",
        ],
        "tono_opts": [
            "Consultivo - preguntar antes de proponer",
            "Directo y ejecutivo (C-Suite)",
            "Profesional pero cercano",
            "Formal y técnico",
        ],
        # Sin datos precargados: el cliente completa todo desde cero.
        "defaults": {},
    }
)
