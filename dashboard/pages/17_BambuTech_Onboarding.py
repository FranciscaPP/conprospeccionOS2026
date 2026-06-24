"""Onboarding comercial de BambuTech Services."""
from __future__ import annotations

import html
import sys
from pathlib import Path

import requests
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from portal_auth import img_b64, render_client_nav, require_auth_client
from shared.bambutech_brand import (
    BAMBU_BG,
    BAMBU_BORDER,
    BAMBU_DARK,
    BAMBU_GREEN,
    BAMBU_GREEN_DARK,
    ICP_DEFAULT,
)
from shared.config import supabase_key, supabase_url
from shared.icp_summary import lista_onboarding, perfil_icp

st.set_page_config(page_title="BambuTech Services — Onboarding", layout="wide", page_icon="")
if not require_auth_client("bambutech"):
    st.stop()
render_client_nav("17_BambuTech_Onboarding", "bambutech")

SB_URL, SB_KEY = supabase_url(), supabase_key()
HEADERS = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"}


@st.cache_data(ttl=60, show_spinner=False)
def cargar_onboarding():
    try:
        response = requests.get(
            f"{SB_URL}/rest/v1/gbs_onboarding?select=*&cliente=eq.bambutech&limit=1",
            headers=HEADERS,
            timeout=12,
        )
        if response.ok and response.json():
            return {**ICP_DEFAULT, **response.json()[0]}
    except requests.RequestException:
        pass
    return {
        **ICP_DEFAULT,
        "web": "https://www.bambu-techservices.com",
        "linkedin_empresa": "https://www.linkedin.com/company/bambutechservices/",
        "diferenciadores": (
            "Profundo entendimiento del negocio, soluciones personalizadas, capacidades "
            "end-to-end y acompañamiento desde consultoría hasta operación y evolución."
        ),
        "presentacion_servicio": (
            "BambuTech actúa como socio tecnológico para transformar procesos, datos y "
            "experiencias mediante soluciones digitales medibles y escalables."
        ),
        "casos_exito": (
            "Plataformas de e-commerce y lealtad, logística y trazabilidad, soluciones "
            "financieras, automatización, software empresarial, IoT y aplicaciones móviles."
        ),
        "tono_lenguaje": "Consultivo, ejecutivo y orientado a impacto de negocio",
        "objeciones": "Proveedor actual, prioridad presupuestaria, integración con sistemas existentes y tiempo de implementación.",
        "nombre_ejecutivo": "Roberto Esparza",
        "cargo_ejecutivo": "Director de Crecimiento",
        "email_ejecutivo": "roberto.esparza@bambu-techservices.com",
        "proceso_comercial": "Discovery inicial → diagnóstico → propuesta de solución → validación técnica y comercial → cierre.",
        "duracion_reunion": "30 minutos",
        "intervalo_reunion": "30 minutos",
        "anticipacion_agenda": "48 horas",
        "notificaciones": "Equipo comercial BambuTech",
        "tiempo_cierre": 45,
        "ticket_promedio": "A: $1M · AA: $3M · AAA: $5M · One Off: hasta $20M MXN",
        "plan_contratado": "Plan Éxito",
        "preguntas_discovery": (
            "¿Qué proceso limita hoy el crecimiento? ¿Qué sistemas necesitan integrarse? "
            "¿Qué impacto tendría reducir tiempos, errores o costos?"
        ),
    }


def guardar(payload):
    response = requests.post(
        f"{SB_URL}/rest/v1/gbs_onboarding?on_conflict=cliente",
        json=payload,
        headers={
            **HEADERS,
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
        timeout=15,
    )
    return response.ok


data = cargar_onboarding()
st.markdown(
    f"""
<style>
button[kind="primary"]{{background:{BAMBU_GREEN_DARK}!important;border:none!important}}
span[data-baseweb="tag"]{{background:#ecf9ec!important;color:{BAMBU_GREEN_DARK}!important}}
</style>
<div style="display:flex;align-items:center;justify-content:space-between;background:linear-gradient(135deg,#202321,#343936);
padding:20px 27px;border-radius:14px;margin-bottom:16px;color:white">
  <div style="display:flex;align-items:center;gap:20px">{img_b64("bambutech_logo.png", 58)}
    <div><div style="font-size:23px;font-weight:850">Onboarding comercial</div>
    <div style="font-size:12px;color:#c8d0ca;margin-top:4px">Perfil confirmado para configurar prospección, mensajes y validación</div></div>
  </div>
  <div style="text-align:right;font-size:12px;color:#c8d0ca"><b style="color:{BAMBU_GREEN}">Setup</b><br>18 abril 2026</div>
</div>
""",
    unsafe_allow_html=True,
)

with st.expander("Documentos, enlaces y respaldos del proyecto", expanded=False):
    docs = [
        ("Contrato Bambu Tech - Conprospección.pdf", ROOT.parent / "BambuTech Services" / "Contrato Bambu Tech - Conprospección.pdf"),
        ("ICP BambuTech.pdf", ROOT.parent / "BambuTech Services" / "ICP BambuTech.pdf"),
    ]
    for label, path in docs:
        if path.exists():
            st.download_button(label, path.read_bytes(), file_name=path.name, key=f"bambu_doc_{path.stem}")
    st.markdown(
        "- [Sitio web oficial](https://www.bambu-techservices.com)\n"
        "- [LinkedIn oficial](https://www.linkedin.com/company/bambutechservices/)\n"
        "- [Playbook SDR](https://bambutechservices.playbook.report-conprospeccion.com/ruta)\n"
        "- [Carpeta del proyecto](https://drive.google.com/drive/folders/1KRScLKdU72d9dsunMxvukq2ty_he1j96?usp=sharing)\n"
        "- [Nota de seguimiento](https://notes.granola.ai/t/f66d4a65-daaa-4495-b183-a1da51166b15-009c2hma)\n"
        "- [Calendario comercial](https://calendar.google.com/calendar/embed?src=michelle.hernandez%40bambutech-services.com&ctz=America%2FArgentina%2FMendoza)"
    )

PAISES = ["México", "Estados Unidos", "Panamá", "Colombia", "Chile", "Guatemala", "Perú", "Argentina"]
TAMANOS = ["35-99 empleados", "100-999 empleados", "1000+ empleados"]
CARGOS = ["CEO", "CIO", "CISO", "CFO", "CMO", "COO", "CTO", "Director de Transformación Digital", "Director de Operaciones"]
INDUSTRIAS = [
    "Retail y consumo", "Servicios financieros", "Alimentos y bebidas", "Logística y transporte",
    "Seguros", "Automotriz", "Construcción", "Salud y farmacéutica", "Manufactura",
    "Minería", "Energía", "Telecomunicaciones",
]

with st.form("bambutech_onboarding"):
    st.markdown("### 1. Perfil de Cliente Ideal")
    c1, c2 = st.columns(2)
    with c1:
        paises = st.multiselect("Mercados objetivo", PAISES, default=[x for x in lista_onboarding(data.get("icp_pais")) if x in PAISES])
        tamanos = st.multiselect("Tamaño de empresa", TAMANOS, default=[x for x in lista_onboarding(data.get("icp_tamano")) if x in TAMANOS])
        cargos = st.multiselect("Decision makers", CARGOS, default=[x for x in lista_onboarding(data.get("icp_cargos")) if x in CARGOS])
    with c2:
        industrias = st.multiselect("Industrias prioritarias", INDUSTRIAS, default=[x for x in lista_onboarding(data.get("icp_industrias")) if x in INDUSTRIAS])
        ticket = st.text_area("Ticket estimado", value=data.get("ticket_promedio") or "", height=95)
        descarte = st.text_area("Criterios de exclusión", value=data.get("icp_descarte") or "", height=92)
    adicional = st.text_area("Criterio adicional ICP", value=data.get("icp_adicional") or "", height=82)

    st.markdown("### 2. Empresa, oferta y mensajes")
    c3, c4 = st.columns(2)
    with c3:
        web = st.text_input("Sitio web", value=data.get("web") or "")
        linkedin = st.text_input("LinkedIn empresa", value=data.get("linkedin_empresa") or "")
        propuesta = st.text_area("Propuesta de valor", value=data.get("propuesta_valor") or "", height=150)
        diferenciadores = st.text_area("Diferenciadores", value=data.get("diferenciadores") or "", height=140)
    with c4:
        presentacion = st.text_area("Presentación del servicio", value=data.get("presentacion_servicio") or "", height=150)
        casos = st.text_area("Casos de éxito y prueba social", value=data.get("casos_exito") or "", height=140)
        tono = st.text_input("Tono", value=data.get("tono_lenguaje") or "")

    st.markdown("### 3. Proceso comercial y agenda")
    c5, c6, c7 = st.columns(3)
    nombre = c5.text_input("Ejecutivo responsable", value=data.get("nombre_ejecutivo") or "")
    cargo = c6.text_input("Cargo", value=data.get("cargo_ejecutivo") or "")
    email = c7.text_input("Email", value=data.get("email_ejecutivo") or "")
    proceso = st.text_area("Proceso comercial", value=data.get("proceso_comercial") or "", height=80)
    c8, c9, c10 = st.columns(3)
    duracion = c8.selectbox("Duración", ["30 minutos", "45 minutos", "60 minutos"], index=0)
    intervalo = c9.selectbox("Intervalo", ["15 minutos", "30 minutos", "45 minutos", "60 minutos"], index=1)
    anticipacion = c10.selectbox("Anticipación mínima", ["24 horas", "48 horas", "1 semana"], index=1)

    st.markdown("### 4. Inteligencia comercial")
    dolores = st.text_area("Dolores frecuentes", value=data.get("dolores_clientes") or "", height=90)
    gatillos = st.text_area("Gatillos de compra", value=data.get("gatillos_compra") or "", height=90)
    keywords = st.text_area("Palabras clave", value=data.get("keywords_prospecto") or "", height=75)
    discovery = st.text_area("Preguntas de discovery", value=data.get("preguntas_discovery") or "", height=85)

    submitted = st.form_submit_button("Guardar onboarding", type="primary", use_container_width=True)
    if submitted:
        payload = {
            "cliente": "bambutech",
            "icp_pais": ", ".join(paises), "icp_tamano": ", ".join(tamanos),
            "icp_cargos": "\n".join(cargos), "icp_industrias": "\n".join(industrias),
            "icp_adicional": adicional, "icp_descarte": descarte, "web": web,
            "linkedin_empresa": linkedin,
            "propuesta_valor": propuesta, "diferenciadores": diferenciadores,
            "presentacion_servicio": presentacion, "casos_exito": casos,
            "tono_lenguaje": tono, "nombre_ejecutivo": nombre, "cargo_ejecutivo": cargo,
            "email_ejecutivo": email, "proceso_comercial": proceso,
            "duracion_reunion": duracion, "intervalo_reunion": intervalo,
            "anticipacion_agenda": anticipacion, "ticket_promedio": ticket,
            "plan_contratado": "Plan Éxito", "dolores_clientes": dolores,
            "gatillos_compra": gatillos, "keywords_prospecto": keywords,
            "preguntas_discovery": discovery, "updated_at": "now()",
        }
        if guardar(payload):
            cargar_onboarding.clear()
            st.success("Onboarding guardado correctamente.")
        else:
            st.error("No fue posible guardar el onboarding.")

profile = perfil_icp({**data, "icp_pais": paises, "icp_tamano": tamanos, "icp_cargos": cargos, "icp_industrias": industrias})
st.markdown(
    f'<div id="resumen-icp" style="background:{BAMBU_BG};border:1px solid {BAMBU_BORDER};'
    f'border-left:5px solid {BAMBU_GREEN_DARK};border-radius:12px;padding:16px 19px;margin-top:18px">'
    f'<div style="font-size:15px;font-weight:850;color:{BAMBU_DARK}">Resumen ICP acordado</div>'
    f'<div style="font-size:13px;color:#4f5852;margin-top:7px">{html.escape(profile["resumen"])}</div></div>',
    unsafe_allow_html=True,
)
