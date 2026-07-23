"""Portal GBS Logistics - Formulario de Onboarding Comercial."""
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


st.set_page_config(page_title="GBS Logistics - Onboarding", layout="wide", page_icon="")
if not require_auth_client("gbs"):
    st.stop()

render_client_nav("14_GBS_Onboarding", "gbs")

render_onboarding_form(
    {
        "slug": "gbs",
        "client_name": "GBS Logistics",
        "logo_file": "gbs_logo.png",
        "accent": "#7c3aed",
        "accent_2": "#4c1d95",
        "soft": "#f5f3ff",
        "border": "#ddd6fe",
        "cargo_opts": [
            "Gerente General / Dueño", "Director Comercial", "Gerente de Operaciones",
            "Gerente de Logística", "Supply Chain Manager", "Gerente de Abastecimiento",
            "Gerente de Compras", "Jefe COMEX", "Encargado de Importaciones",
            "Coordinador de Importaciones / Exportaciones", "Analista de Comercio Exterior",
            "Jefe de Bodega / Almacén", "Gerente de Planta",
        ],
        "industria_opts": [
            "Minería y Metales", "Retail", "Automotriz", "Alimentos y Bebidas",
            "Dispositivos Médicos", "Electrónica", "Maquinaria Industrial", "Vinos y Licores",
            "Agroindustria", "Construcción", "Farmacéutica", "Química",
            "Textil y Calzado", "Tecnología", "Energía", "Manufactura", "Consumo Masivo",
        ],
        "descarte_opts": [
            "Freight forwarders", "Agentes de aduana", "Navieras", "Aerolíneas de carga",
            "Exportadores de commodities (cobre, fruta, pescado)",
            "Empresas con departamento logístico interno robusto",
            "Couriers / paquetería", "Transporte terrestre local",
        ],
        "tono_opts": [
            "Formal y técnico (sector logístico, COMEX)",
            "Profesional pero cercano",
            "Directo y ejecutivo (C-Suite)",
            "Consultivo - preguntar antes de proponer",
        ],
        "defaults": {
            "icp_pais": ["Chile", "Colombia", "Perú"],
            "icp_cargos": [
                "Gerente de Abastecimiento", "Supply Chain Manager", "Gerente de Logística",
                "Encargado de Importaciones", "Gerente General / Dueño",
            ],
            "icp_tamano": ["1-10 empleados", "11-20 empleados", "21-50 empleados", "51-100 empleados", "101-200 empleados"],
            "icp_industrias": [
                "Minería y Metales", "Retail", "Automotriz", "Alimentos y Bebidas",
                "Dispositivos Médicos", "Electrónica", "Maquinaria Industrial", "Vinos y Licores",
            ],
            "icp_descarte": [
                "Freight forwarders", "Agentes de aduana", "Navieras", "Aerolíneas de carga",
                "Exportadores de commodities (cobre, fruta, pescado)",
                "Empresas con departamento logístico interno robusto",
            ],
            "web": "https://www.gbslogistics.cl",
            "diferenciadores": (
                "Servicio puerta a puerta integral (flete + aduana + seguro + transporte local)\n"
                "Especialización en carga temperada para industria del vino (thermoliner)\n"
                "Red internacional GAA/WCA\nPO Management\nTrato personalizado para pymes"
            ),
            "tiempo_cierre": 45,
            "plan_contratado": "Growth",
        },
    }
)
