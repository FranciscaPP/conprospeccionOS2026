"""Portal cliente BambuTech - onboarding comercial editable."""
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
from shared.cp_design import CP_GOLD, CP_GOLD_SOFT, CP_INK, CP_ORANGE


st.set_page_config(page_title="BambuTech - Onboarding", layout="wide", page_icon="")
if not require_auth_client("bambutech"):
    st.stop()

render_client_nav("17_BambuTech_Onboarding", "bambutech")

render_onboarding_form(
    {
        "slug": "bambutech",
        "client_name": "BambuTech Services",
        "logo_file": "bambutech_logo.png",
        "accent": CP_GOLD,
        "accent_2": CP_ORANGE,
        "soft": CP_GOLD_SOFT,
        "border": "#F0D28D",
        "ink": CP_INK,
        "cargo_opts": [
            "CEO", "CIO", "CISO", "CFO", "CMO", "COO", "CTO",
            "Director de Tecnología", "Director de Operaciones", "Director de Transformación Digital",
            "Gerente General", "Gerente de Innovación", "Gerente de Sistemas",
            "Gerente de Supply Chain", "Gerente de Logística", "Gerente de Retail",
        ],
        "industria_opts": [
            "Abierto", "Retail y consumo", "Servicios financieros", "Alimentos y bebidas",
            "Logística y transporte", "Seguros", "Automotriz", "Construcción",
            "Salud y farmacéutica", "Manufactura", "Minería", "Energía",
            "Telecomunicaciones", "Tecnología", "Gobierno / sector público",
        ],
        "descarte_opts": [
            "Competidores de desarrollo de software", "Empresas sin necesidad tecnológica identificable",
            "Empresas sin capacidad de inversión", "Empresas fuera de los mercados objetivo",
            "Cuentas sin decisor C-Level accesible", "Microempresas sin presupuesto de transformación",
        ],
        "tono_opts": [
            "Consultivo - preguntar antes de proponer",
            "Directo y ejecutivo (C-Suite)",
            "Profesional pero cercano",
            "Formal y técnico (tecnología / transformación digital)",
        ],
        "defaults": {
            "icp_pais": ["México", "Estados Unidos", "Panamá", "Colombia", "Chile"],
            "icp_cargos": ["CEO", "CIO", "CISO", "CFO", "CMO", "COO"],
            "icp_tamano": ["35-99 empleados", "100-999 empleados", "1000+ empleados"],
            "icp_industrias": ["Abierto", "Retail y consumo", "Logística y transporte", "Salud y farmacéutica", "Manufactura"],
            "icp_adicional": (
                "Empresas que buscan ganar más, ser más rentables, gastar menos, concentrar proveedores, "
                "optimizar inversiones, asegurar escalabilidad, reducir tiempos, ganar mercado, innovar, "
                "crear productos o mejorar la experiencia de clientes y usuarios."
            ),
            "icp_descarte": [
                "Competidores de desarrollo de software",
                "Empresas sin necesidad tecnológica identificable",
                "Empresas sin capacidad de inversión",
                "Microempresas sin presupuesto de transformación",
            ],
            "web": "https://bambutech.com",
            "propuesta_valor": (
                "BambuTech diseña, desarrolla e integra soluciones digitales a la medida: software, "
                "automatización, Data & AI, cloud, ciberseguridad, UX/UI, IoT e integración de APIs."
            ),
            "diferenciadores": (
                "Horizonte integral de servicios: consultoría, diseño, desarrollo, testing, deployment y growth.\n"
                "Capacidad de assessment, benchmarking, UX/UI, prototipado, RPA, integración de APIs, IA, cloud, QA, pentesting y mantenimiento Bambú Care.\n"
                "Casos en C5/911, e-commerce, mCommerce, SAP Commerce Cloud, apps móviles y soluciones de operación crítica."
            ),
            "presentacion_servicio": (
                "BambuTech ayuda a empresas a dar el salto digital mediante soluciones tecnológicas personalizadas, "
                "modernización de sistemas, automatización e integración para mejorar eficiencia, escalabilidad y experiencia del cliente."
            ),
            "casos_exito": (
                "Sistema de traducción para operadores 911/C5 del Estado de Baja California Sur.\n"
                "Célula de soporte e implementación de mejoras para app de e-commerce/mCommerce con Kotlin, Swift, Angular, OAuth2, Firebase, Emarsys, Dynatrace y SAP Commerce Cloud."
            ),
            "mensajes_funcionan": (
                "Mensajes orientados a eficiencia operativa, reducción de costos/tiempos, modernización tecnológica, "
                "integración de sistemas, automatización y mejora de experiencia de cliente."
            ),
            "objeciones": (
                "Ya tenemos proveedor tecnológico; no es prioridad ahora; tenemos equipo interno; falta presupuesto; "
                "necesitamos validar alcance antes de avanzar."
            ),
            "proceso_comercial": "1. Reunión exploratoria\n2. Diagnóstico / assessment\n3. Propuesta de solución\n4. Cotización y alcance\n5. Cierre e inicio de proyecto",
            "tiempo_cierre": 45,
            "ticket_promedio": "A: $1,000,000 MXP · AA: $3,000,000 MXP · AAA: $5,000,000 MXP · One Off: $20,000,000 MXP",
            "plan_contratado": "Growth",
            "preguntas_discovery": (
                "¿Qué proceso crítico quieren digitalizar o automatizar?\n"
                "¿Qué sistemas hoy no conversan entre sí?\n"
                "¿Qué impacto financiero u operativo tiene el problema?\n"
                "¿Quién decide el proveedor tecnológico y quién usa la solución?"
            ),
            "dolores_clientes": (
                "Fragmentación de la información, obsolescencia tecnológica, necesidad de middleware, "
                "vulnerabilidad, riesgo operativo, procesos manuales, baja analítica y digitalización pendiente."
            ),
            "gatillos_compra": (
                "Reducir costos y tiempos, concentrar proveedores, escalar, innovar, mejorar CX, lanzar nuevos productos, "
                "resolver vulnerabilidades o integrar datos/sistemas críticos."
            ),
            "keywords_prospecto": (
                "transformación digital, software a la medida, automatización, Data & AI, integración, middleware, "
                "cloud, ciberseguridad, UX/UI, IoT, RPA, APIs, modernización tecnológica"
            ),
            "notas_adicionales": (
                "ICP base extraído de Perfil de clientes y Master Comercial BambuTech. "
                "Links de reuniones pendientes de transcripción completa en Granola/Fathom."
            ),
        },
        "sources": [
            {
                "title": "Perfil de clientes",
                "detail": "PDF: ICP con industria abierta, C-Level, ubicaciones CDMX/GDL/MTY/QRO/Chihuahua/Houston/Panamá/Colombia/Chile, pain points, tamaño y ticket.",
            },
            {
                "title": "Master Comercial",
                "detail": "PDF: horizonte de servicios, Bambú Care, casos de software/PaaS, C5/911, e-commerce y enfoque de salto digital.",
            },
            {
                "title": "Granola",
                "detail": "https://notes.granola.ai/t/f66d4a65-daaa-4495-b183-a1da51166b15-008umkv4",
            },
            {
                "title": "Fathom",
                "detail": "https://fathom.video/share/8qQ9ES9z8o-FHGYExrSrXdVcebT_ZPbv",
            },
        ],
    }
)
