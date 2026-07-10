"""Portal DEMO - Formulario de Onboarding, en blanco.

Replica del formulario de intake que el cliente completa antes de iniciar el
proyecto, recuperado de `14_GBS_Onboarding.py` (eliminado en 0dab1f0).

Diferencias con el original:
  * Todos los campos vienen vacios. El prospecto ve la forma, no los datos de nadie.
  * Paleta de Conprospeccion (shared/cp_design.py), la misma del panel de
    Seguimiento de Reuniones, en vez del morado de GBS.
  * Sin Supabase y sin Telegram. El envio no persiste nada.
  * Los textos de ayuda no mencionan a ningun cliente real.

AISLAMIENTO: no importa requests, supabase ni shared.config.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from portal_auth import img_b64, render_client_nav, require_auth_client
from shared.cp_design import (
    CP_BG,
    CP_GOLD,
    CP_GOLD_SOFT,
    CP_INK,
    CP_LINE,
    CP_MUTED,
)

# Dorado oscuro accesible para texto sobre fondos claros. El dorado puro (#FFD700)
# sobre blanco es ilegible; el panel usa este mismo tono para sus etiquetas.
CP_GOLD_TEXT = "#7A6400"

st.set_page_config(page_title="Demo - Onboarding", layout="wide")

if not require_auth_client("demo"):
    st.stop()

render_client_nav("22_Demo_Onboarding", "demo")

st.markdown(
    f"""
<style>
header, [data-testid="stToolbar"], [data-testid="stDecoration"] {{ display:none !important; }}
.block-container {{ max-width:1180px !important; padding-top:1rem !important; }}
.stApp {{ background:{CP_BG}; }}

/* Boton primario: dorado con texto tinta. Blanco sobre dorado no se lee. */
button[kind="primary"] {{
    background:{CP_GOLD} !important; border:none !important;
    color:{CP_INK} !important; font-weight:800 !important;
}}
button[kind="primary"]:hover {{ filter:brightness(1.06); }}

/* Etiquetas de los multiselect */
span[data-baseweb="tag"] {{ background:{CP_GOLD_SOFT} !important; color:{CP_GOLD_TEXT} !important; }}
span[data-baseweb="tag"] span {{ color:{CP_GOLD_TEXT} !important; }}
span[data-baseweb="tag"] svg {{ fill:{CP_GOLD_TEXT} !important; }}
</style>
    """,
    unsafe_allow_html=True,
)

# ── Encabezado ───────────────────────────────────────────────────────────────
# El isotipo, no el logo completo: el logo lleva el nombre en tinta oscura y
# sobre el encabezado negro no se lee. Es el mismo que usa el panel operativo.
logo = img_b64("cp_mark_dark.png", 34)
st.markdown(
    f'<div style="display:flex;align-items:center;justify-content:space-between;gap:20px;'
    f'background:{CP_INK};padding:18px 26px;border-radius:14px;margin-bottom:10px">'
    f'<div><div style="font-size:22px;font-weight:800;color:#fff;line-height:1.15">'
    f'Formulario de Onboarding</div>'
    f'<div style="font-size:12px;color:#B9B9B6;margin-top:4px">'
    f'Completar antes del inicio del proyecto · La información aquí definirá la '
    f'estrategia de prospección</div></div>'
    f'<div style="display:flex;align-items:center;gap:14px;flex-shrink:0">'
    f'<span style="font-size:11px;font-weight:800;color:{CP_GOLD};white-space:nowrap">'
    f'VISTA DE DEMOSTRACIÓN</span>{logo}</div></div>',
    unsafe_allow_html=True,
)


def seccion(titulo: str) -> None:
    st.markdown(
        f'<div style="background:{CP_INK};color:#fff;border-left:5px solid {CP_GOLD};'
        f'border-radius:10px;padding:12px 20px;margin:26px 0 16px;'
        f'font-size:15px;font-weight:800">{titulo}</div>',
        unsafe_allow_html=True,
    )


def nota(texto: str) -> None:
    st.markdown(
        f'<div style="background:{CP_GOLD_SOFT};border:1px solid {CP_LINE};'
        f'border-left:4px solid {CP_GOLD};border-radius:10px;padding:12px 16px;'
        f'margin-bottom:16px;font-size:13px;color:#334155">{texto}</div>',
        unsafe_allow_html=True,
    )


# ═════════════════════════════════════════════════════════════════════════════
# BLOQUE 1 — DEFINICIÓN ICP
# ═════════════════════════════════════════════════════════════════════════════
seccion("Definición del ICP (Perfil de Cliente Ideal)")

nota(
    f'<b style="color:{CP_GOLD_TEXT}">Primer paso — y el más importante.</b> '
    f'Aquí se define a quién se va a prospectar. El cliente completa estos filtros '
    f'antes de avanzar con el resto del setup.'
)

PAISES_LATAM_ES = [
    "Argentina", "Bolivia", "Brasil", "Chile", "Colombia", "Costa Rica", "Cuba",
    "Ecuador", "El Salvador", "España", "Guatemala", "Honduras", "México",
    "Nicaragua", "Panamá", "Paraguay", "Perú", "Puerto Rico",
    "República Dominicana", "Uruguay", "Venezuela",
]
CARGOS_OPTS = [
    "Gerente General / Dueño", "Director Comercial", "Gerente de Operaciones",
    "Gerente de Logística", "Supply Chain Manager", "Gerente de Abastecimiento",
    "Gerente de Compras", "Gerente de Finanzas", "Gerente de Tecnología",
    "Gerente de Marketing", "Gerente de Personas", "Jefe de Proyectos",
    "Gerente de Planta",
]
INDUSTRIAS_OPTS = [
    "Minería y Metales", "Retail", "Automotriz", "Alimentos y Bebidas",
    "Dispositivos Médicos", "Electrónica", "Maquinaria Industrial", "Vinos y Licores",
    "Agroindustria", "Construcción", "Farmacéutica", "Química",
    "Textil y Calzado", "Tecnología", "Energía", "Manufactura", "Consumo Masivo",
    "Servicios Financieros", "Salud", "Educación", "Telecomunicaciones",
]
TAMANO_OPTS = [
    "1-10 empleados", "11-20 empleados", "21-50 empleados", "51-100 empleados",
    "101-200 empleados", "201-500 empleados", "501-1000 empleados",
    "1001-2000 empleados", "2001-5000 empleados", "5001-10000 empleados",
    "10001+ empleados",
]
DESCARTE_OPTS = [
    "Competencia directa", "Clientes actuales", "Ex clientes",
    "Empresas sin capacidad de inversión", "Empresas fuera del mercado objetivo",
    "Empresas con el servicio resuelto internamente",
    "Intermediarios o revendedores", "Sector público",
]

col1, col2 = st.columns(2)
with col1:
    st.multiselect("País(es) objetivo", PAISES_LATAM_ES, default=[], key="icp_pais",
                   placeholder="Seleccionar opciones",
                   help="Uno o más mercados de LATAM o España")
    st.multiselect("Cargos objetivo", CARGOS_OPTS, default=[], key="icp_cargos",
                   placeholder="Seleccionar opciones",
                   help="Los cargos con los que busca reuniones")
    st.multiselect("Tamaño de empresa (n.º de empleados)", TAMANO_OPTS, default=[],
                   key="icp_tamano", placeholder="Seleccionar opciones",
                   help="Tramos de empleados de las empresas objetivo")
with col2:
    st.multiselect("Industrias objetivo", INDUSTRIAS_OPTS, default=[],
                   key="icp_industrias", placeholder="Seleccionar opciones",
                   help="Industrias donde buscan prospectar")
    st.text_area("Criterio adicional ICP (diferenciador de calidad)", height=100,
                 key="icp_adicional",
                 placeholder="Ej: empresa con operación recurrente, sin el servicio resuelto internamente...",
                 help="Qué hace que un prospecto sea especialmente bueno")

col3, col4 = st.columns(2)
with col3:
    st.multiselect("Industrias o segmentos a excluir de la prospección", DESCARTE_OPTS,
                   default=[], key="icp_descarte", placeholder="Seleccionar opciones",
                   help="Competidores, casos perdidos de antemano o segmentos que no aplican")
with col4:
    st.file_uploader("Clientes actuales (CSV o XLSX)", type=["csv", "xlsx"],
                     key="clientes_actuales",
                     help="Para no prospectar a clientes existentes ni a su competencia directa")

# ═════════════════════════════════════════════════════════════════════════════
# BLOQUE 2 — EMPRESA Y MARCA
# ═════════════════════════════════════════════════════════════════════════════
seccion("Empresa y Marca")

col5, col6 = st.columns(2)
with col5:
    st.text_input("Página web", key="web", placeholder="https://www.tuempresa.cl")
    st.text_input("LinkedIn empresa", key="linkedin_empresa",
                  placeholder="https://linkedin.com/company/tu-empresa")
    st.text_area("Propuesta de valor", height=120, key="propuesta_valor",
                 placeholder="¿Qué ofrece la empresa y por qué la eligen los clientes?")
with col6:
    st.text_area("Diferenciadores vs. la competencia", height=100, key="diferenciadores",
                 placeholder="Qué hace distinta a la empresa frente a sus competidores directos...")
    st.text_area("Presentación del servicio", height=100, key="presentacion_servicio",
                 placeholder="Cómo se explica el servicio en una reunión o llamada inicial...")

col7, col8 = st.columns(2)
with col7:
    st.file_uploader("Archivos de marca (logos, brochure, imagen corporativa)",
                     type=["png", "jpg", "pdf", "zip"], accept_multiple_files=True,
                     key="archivos_marca")
with col8:
    st.text_area("Casos de éxito", height=100, key="casos_exito",
                 placeholder="Describir 1–3 casos donde la empresa marcó una diferencia real...",
                 help="Industrias y resultados, aunque sea de forma anónima")

# ═════════════════════════════════════════════════════════════════════════════
# BLOQUE 3 — MENSAJERÍA Y TONO
# ═════════════════════════════════════════════════════════════════════════════
seccion("Mensajería y Tono de Comunicación")

col9, col10 = st.columns(2)
with col9:
    st.selectbox("Tipo de lenguaje a usar", [
        "Formal y técnico",
        "Profesional pero cercano",
        "Directo y ejecutivo (C-Suite)",
        "Consultivo — preguntar antes de proponer",
    ], key="tono_lenguaje", index=None, placeholder="Seleccionar opción")
    st.text_area("Ejemplos de mensajes que han funcionado", height=120,
                 key="mensajes_funcionan",
                 placeholder="Asuntos de email, mensajes de LinkedIn o scripts de llamada que hayan generado respuesta...")
with col10:
    st.text_area("Frases o mensajes a evitar", height=100, key="mensajes_no_decir",
                 placeholder="Ej: no mencionar precios en el primer contacto, no compararse con la competencia...",
                 help="Restricciones de mensaje o temas que el cliente prefiere evitar")
    st.text_area("Principales objeciones recibidas", height=100, key="objeciones",
                 placeholder="Ej: 'Ya tenemos proveedor', 'No es prioridad este año', 'El precio es muy alto'...")

# ═════════════════════════════════════════════════════════════════════════════
# BLOQUE 4 — PROCESO COMERCIAL
# ═════════════════════════════════════════════════════════════════════════════
seccion("Proceso Comercial y Configuración de Agenda")

col11, col12 = st.columns(2)
with col11:
    st.text_input("Nombre del ejecutivo que toma las reuniones", key="nombre_ejecutivo",
                  placeholder="Nombre y apellido")
    st.text_input("Cargo del ejecutivo", key="cargo_ejecutivo",
                  placeholder="Ej: Director Comercial")
    st.text_input("Email del ejecutivo", key="email_ejecutivo",
                  placeholder="nombre@tuempresa.cl")
    st.text_area("Proceso comercial paso a paso", height=100, key="proceso_comercial",
                 placeholder="Ej: 1. Reunión exploratoria 2. Cotización 3. Propuesta 4. Cierre\n"
                             "Indicar cuántos contactos hay entre el primer acercamiento y el cierre.")
with col12:
    st.selectbox("Duración de las reuniones", ["30 minutos", "45 minutos", "60 minutos"],
                 key="duracion_reunion", index=None, placeholder="Seleccionar opción")
    st.selectbox("Tiempo de preparación entre reuniones (intervalo mínimo)",
                 ["15 minutos", "30 minutos", "45 minutos", "60 minutos", "90 minutos"],
                 key="intervalo_reunion", index=None, placeholder="Seleccionar opción")
    st.selectbox("Tiempo máximo de anticipación para agendar",
                 ["24 horas", "48 horas", "1 semana", "2 semanas"],
                 key="anticipacion_agenda", index=None, placeholder="Seleccionar opción")
    st.text_area("Quiénes reciben la info del lead agendado", height=80,
                 key="notificaciones", placeholder="Correos que reciben la notificación...")

col13, col14 = st.columns(2)
with col13:
    st.number_input("Tiempo promedio de cierre (días)", min_value=7, max_value=365,
                    value=None, key="tiempo_cierre", placeholder="Ej: 45",
                    help="Desde la reunión inicial hasta la firma de contrato")
with col14:
    st.text_input("Costo promedio del servicio (ticket promedio)", key="ticket_promedio",
                  placeholder="Ej: USD 3.000 mensual por cliente activo",
                  help="Ayuda a calibrar el target de prospectos por volumen")

st.radio("Plan contratado con Conprospección", ["Starter", "Growth"],
         horizontal=True, key="plan_contratado", index=None)

# ═════════════════════════════════════════════════════════════════════════════
# BLOQUE 5 — INTELIGENCIA COMERCIAL ADICIONAL
# ═════════════════════════════════════════════════════════════════════════════
seccion("Inteligencia Comercial Adicional (Recomendado)")

st.markdown(
    f'<div style="font-size:13px;color:{CP_MUTED};margin-bottom:14px">'
    f'Esta información permite personalizar las secuencias de prospección a un nivel '
    f'mucho mayor. No es obligatoria, pero impacta directamente en los resultados.</div>',
    unsafe_allow_html=True,
)

col15, col16 = st.columns(2)
with col15:
    st.text_area("¿Qué preguntas de discovery funcionan mejor en las reuniones?",
                 height=100, key="preguntas_discovery",
                 placeholder="Las preguntas que mejor revelan si un prospecto califica...")
    st.text_area("¿Cuáles son los dolores más frecuentes que reportan los clientes actuales?",
                 height=100, key="dolores_clientes",
                 placeholder="Ej: falta de visibilidad, procesos manuales, coordinar varios proveedores...")
with col16:
    st.text_area("¿Qué gatillos de compra activan la decisión? (timing de prospección)",
                 height=100, key="gatillos_compra",
                 placeholder="Ej: cambio de proveedor por falla, crecimiento en volumen, nuevo ejecutivo a cargo...")
    st.text_area("¿Qué palabras clave usan los prospectos en LinkedIn / emails?",
                 height=100, key="keywords_prospecto",
                 placeholder="El vocabulario propio del rubro del prospecto...")

st.text_area("Notas adicionales para el equipo de Conprospección", height=100,
             key="notas_adicionales",
             placeholder="Cualquier contexto, restricción u oportunidad que debamos saber...")

# ── Envío ────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
col_send, _ = st.columns([1, 3])
with col_send:
    enviado = st.button("Enviar formulario a Conprospección", type="primary",
                        use_container_width=True)

if enviado:
    # En el producto real esto persiste en Supabase y notifica al equipo.
    # El portal demo no escribe en ninguna parte.
    st.markdown(
        f'<div style="background:{CP_GOLD_SOFT};border:1px solid {CP_GOLD};'
        f'border-radius:10px;padding:18px 20px;margin-top:12px">'
        f'<div style="font-size:15px;font-weight:800;color:{CP_INK};margin-bottom:6px">'
        f'Formulario enviado</div>'
        f'<div style="font-size:13px;color:#334155">'
        f'En el portal real la información queda guardada y el ejecutivo de cuenta de '
        f'Conprospección se pone en contacto dentro de 24 horas.<br><br>'
        f'<b>Próximo paso:</b> validación de ICP y configuración de las primeras campañas.'
        f'<br><br><i>Esta es una vista de demostración: nada de lo que escribas se almacena.</i>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

# ── Pie ──────────────────────────────────────────────────────────────────────
cp = img_b64("conprospeccion_logo.png", 18) or ""
st.markdown(
    f'<div style="text-align:center;color:{CP_MUTED};font-size:11px;margin-top:40px;padding:16px">'
    f'{cp}&nbsp;Formulario de Onboarding — <b style="color:{CP_INK}">Conprospección</b> · '
    f'Confidencial · {date.today().strftime("%B %Y").capitalize()}</div>',
    unsafe_allow_html=True,
)
