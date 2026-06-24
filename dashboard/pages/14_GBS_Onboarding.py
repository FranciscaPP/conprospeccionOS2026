"""Portal GBS Logistics — Formulario de Onboarding Comercial.

Formulario de intake que el cliente completa antes del inicio del proyecto.
Incluye ICP, proceso comercial, propuesta de valor, restricciones y configuración de agenda.
"""
import html
import sys
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

import requests
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client
from shared.config import supabase_url, supabase_key, telegram_token, telegram_chat_id
from shared.gbs_brand import GBS_PURPLE, GBS_PURPLE_BG, GBS_BORDER_2
from shared.icp_summary import perfil_icp
from portal_auth import require_auth_client, render_client_nav, img_b64

_sb = create_client(supabase_url(), supabase_key())


def _notify_telegram(nombre_ej: str, email_ej: str) -> None:
    token = telegram_token()
    chat_id = telegram_chat_id()
    if not token or not chat_id:
        return
    msg = (
        "*Onboarding GBS Logistics recibido*\n\n"
        f"Ejecutivo: {nombre_ej or '(sin nombre)'}\n"
        f"Email: {email_ej or '(sin email)'}\n\n"
        "El formulario quedó guardado en Supabase tabla `gbs\\_onboarding`."
    )
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
            timeout=8,
        )
    except Exception:
        pass

st.set_page_config(page_title="GBS Logistics — Onboarding", layout="wide", page_icon="")

if not require_auth_client("gbs"):
    st.stop()

render_client_nav("14_GBS_Onboarding", "gbs")

# Paleta GBS desde shared/gbs_brand (fuente única, morado de marca).
GBS_BLUE = GBS_PURPLE # alias retrocompatible
GBS_LIGHT = GBS_PURPLE_BG # #f5f3ff
GBS_BORDER = GBS_BORDER_2 # #ddd6fe

# Botón primary en morado GBS (en Streamlit Cloud el primary sale rojo por defecto).
st.markdown(
    f'<style>'
    f'button[kind="primary"]{{background:{GBS_PURPLE}!important;border:none!important;'
    f'color:#fff!important;font-weight:700!important}}'
    f'button[kind="primary"]:hover{{filter:brightness(1.08)}}'
    f'span[data-baseweb="tag"]{{background:#ede9fe!important;color:#5b21b6!important}}'
    f'span[data-baseweb="tag"] span{{color:#5b21b6!important}}'
    f'span[data-baseweb="tag"] svg{{fill:#5b21b6!important}}'
    f'</style>',
    unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
g = img_b64("gbs_logo.png", 56) or (
    f'<div style="background:{GBS_BLUE};color:#fff;padding:10px 22px;border-radius:8px;'
    f'font-size:18px;font-weight:800;letter-spacing:2px">GBS</div>')
c = img_b64("conprospeccion_logo.png", 44) or (
    '<div style="background:#111827;padding:8px 18px;border-radius:8px;'
    'font-size:13px;font-weight:700;color:#fbbf24">Conprospección</div>')

st.markdown(
    f'<div style="display:flex;align-items:center;justify-content:space-between;'
    f'background:linear-gradient(135deg,#faf5ff,#ede9fe);padding:18px 28px;'
    f'border-radius:14px;border:1px solid {GBS_BORDER};margin-bottom:8px;'
    f'box-shadow:0 2px 8px rgba(0,0,0,.06)">'
    f'<div style="display:flex;align-items:center;gap:18px">{g}'
    f'<div><div style="font-size:22px;font-weight:800;color:#1e293b">Formulario de Onboarding</div>'
    f'<div style="font-size:13px;color:#64748b;margin-top:3px">'
    f'Completar antes del inicio del proyecto · La información aquí definirá la estrategia de prospección</div>'
    f'</div></div>{c}</div>',
    unsafe_allow_html=True,
)



def seccion(titulo, icono):
    # Todos los encabezados con el mismo gradiente morado de marca (consistencia GBS).
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#4c1d95,#7c3aed);color:#fff;'
        f'border-radius:10px;padding:12px 20px;margin:24px 0 16px;font-size:15px;font-weight:800">'
        f'{icono} {titulo}</div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# BLOQUE 1 — DEFINICIÓN ICP
# ═══════════════════════════════════════════════════════════════════════════════
seccion("Definición del ICP (Perfil de Cliente Ideal)", "")

st.markdown(
    f'<div style="background:{GBS_LIGHT};border:1px solid {GBS_BORDER};border-left:4px solid {GBS_PURPLE};'
    f'border-radius:10px;padding:12px 16px;margin-bottom:16px;font-size:13px;color:#334155">'
    f'<b style="color:{GBS_PURPLE}">Primer paso — y el más importante.</b> Aquí se define a quién se va a '
    f'prospectar. Los campos vienen pre-cargados con el ICP de GBS; ajustar los filtros según corresponda '
    f'antes de avanzar con el resto del setup.</div>',
    unsafe_allow_html=True,
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
    "Gerente de Compras", "Jefe COMEX", "Encargado de Importaciones",
    "Coordinador de Importaciones / Exportaciones", "Analista de Comercio Exterior",
    "Jefe de Bodega / Almacén", "Gerente de Planta",
]
INDUSTRIAS_OPTS = [
    "Minería y Metales", "Retail", "Automotriz", "Alimentos y Bebidas",
    "Dispositivos Médicos", "Electrónica", "Maquinaria Industrial", "Vinos y Licores",
    "Agroindustria", "Construcción", "Farmacéutica", "Química",
    "Textil y Calzado", "Tecnología", "Energía", "Manufactura", "Consumo Masivo",
]
TAMANO_OPTS = [
    "1-10 empleados", "11-20 empleados", "21-50 empleados", "51-100 empleados",
    "101-200 empleados", "201-500 empleados", "501-1000 empleados",
    "1001-2000 empleados", "2001-5000 empleados", "5001-10000 empleados",
    "10001+ empleados",
]
DESCARTE_OPTS = [
    "Freight forwarders", "Agentes de aduana", "Navieras", "Aerolíneas de carga",
    "Exportadores de commodities (cobre, fruta, pescado)",
    "Empresas con departamento logístico interno robusto",
    "Couriers / paquetería", "Transporte terrestre local",
]

col1, col2 = st.columns(2)
with col1:
    st.multiselect("País(es) objetivo", PAISES_LATAM_ES,
                   default=["Chile", "Colombia", "Perú"], key="icp_pais",
                   placeholder="Seleccionar opciones",
                   help="Seleccionar uno o más mercados de LATAM o España")
    st.multiselect("Cargos objetivo", CARGOS_OPTS,
                   default=["Gerente de Abastecimiento", "Supply Chain Manager",
                            "Gerente de Logística", "Encargado de Importaciones",
                            "Gerente General / Dueño"],
                   key="icp_cargos", placeholder="Seleccionar opciones",
                   help="Los cargos con los que busca reuniones")
    st.multiselect("Tamaño de empresa (n.º de empleados)", TAMANO_OPTS,
                   default=["1-10 empleados", "11-20 empleados", "21-50 empleados",
                            "51-100 empleados", "101-200 empleados"],
                   key="icp_tamano", placeholder="Seleccionar opciones",
                   help="Tramos de empleados de las empresas objetivo")

with col2:
    st.multiselect("Industrias objetivo", INDUSTRIAS_OPTS,
                   default=["Minería y Metales", "Retail", "Automotriz",
                            "Alimentos y Bebidas", "Dispositivos Médicos", "Electrónica",
                            "Maquinaria Industrial", "Vinos y Licores"],
                   key="icp_industrias", placeholder="Seleccionar opciones",
                   help="Industrias donde buscan prospectar")
    st.text_area("Criterio adicional ICP (diferenciador de calidad)", height=100, key="icp_adicional",
                 placeholder="Ej: empresa con importaciones mensuales recurrentes, sin depto logístico interno...",
                 help="Qué hace que un prospecto sea especialmente bueno")

col3, col4 = st.columns(2)
with col3:
    st.multiselect("Industrias o segmentos a excluir de la prospección", DESCARTE_OPTS,
                   default=["Freight forwarders", "Agentes de aduana", "Navieras",
                            "Aerolíneas de carga",
                            "Exportadores de commodities (cobre, fruta, pescado)",
                            "Empresas con departamento logístico interno robusto"],
                   key="icp_descarte", placeholder="Seleccionar opciones",
                   help="Competidores, casos perdidos de antemano o segmentos que no aplican")
with col4:
    clientes_file = st.file_uploader(
        "Clientes actuales (CSV o XLSX)", type=["csv","xlsx"],
        key="clientes_actuales",
        help="Para no prospectar a clientes existentes ni a su competencia directa")

# ═══════════════════════════════════════════════════════════════════════════════
# BLOQUE 2 — EMPRESA Y MARCA
# ═══════════════════════════════════════════════════════════════════════════════
seccion("Empresa y Marca", "")

col5, col6 = st.columns(2)
with col5:
    st.text_input("Página web", value="https://www.gbslogistics.cl", key="web")
    st.text_input("LinkedIn empresa", key="linkedin_empresa",
                  placeholder="https://linkedin.com/company/gbs-logistics")
    st.text_area("Propuesta de valor", height=120, key="propuesta_valor",
                 placeholder="¿Qué ofrece la empresa y por qué la eligen los clientes?")

with col6:
    st.text_area("Diferenciadores vs. la competencia", height=100, key="diferenciadores",
                 value="Servicio puerta a puerta integral (flete + aduana + seguro + transporte local)\nEspecialización en carga temperada para industria del vino (thermoliner)\nRed internacional GAA/WCA\nPO Management\nTrato personalizado — las pymes no son cuentas menores")
    st.text_area("Presentación del servicio", height=100, key="presentacion_servicio",
                 placeholder="Cómo se explica el servicio en una reunión o llamada inicial...")

col7, col8 = st.columns(2)
with col7:
    archivos = st.file_uploader(
        "Archivos de marca (logos, brochure, imagen corporativa)", type=["png","jpg","pdf","zip"],
        accept_multiple_files=True, key="archivos_marca")
with col8:
    st.text_area("Casos de éxito", height=100, key="casos_exito",
                 placeholder="Describir 1–3 casos donde GBS marcó una diferencia real para un cliente...",
                 help="Nombres, industrias y resultados (aunque sea de forma anónima)")

# ═══════════════════════════════════════════════════════════════════════════════
# BLOQUE 3 — MENSAJERÍA Y TONO
# ═══════════════════════════════════════════════════════════════════════════════
seccion("Mensajería y Tono de Comunicación", "")

col9, col10 = st.columns(2)
with col9:
    tono = st.selectbox("Tipo de lenguaje a usar", [
        "Formal y técnico (sector logístico, COMEX)",
        "Profesional pero cercano",
        "Directo y ejecutivo (C-Suite)",
        "Consultivo — preguntar antes de proponer",
    ], key="tono_lenguaje")
    st.text_area("Ejemplos de mensajes que han funcionado", height=120, key="mensajes_funcionan",
                 placeholder="Copiar aquí asuntos de email, mensajes de LinkedIn o scripts de llamada que hayan generado respuesta...")

with col10:
    st.text_area("Frases o mensajes a evitar", height=100, key="mensajes_no_decir",
                 placeholder="Ej: no mencionar precios en primer contacto, no compararse con DHL, no usar jerga de 'startup'...",
                 help="Restricciones de mensaje o temas que el cliente prefiere evitar")
    st.text_area("Principales objeciones recibidas", height=100, key="objeciones",
                 placeholder="Ej: 'Tenemos contrato con otro operador', 'Solo usamos freight forwarders asiáticos', 'El precio es muy alto'...")

# ═══════════════════════════════════════════════════════════════════════════════
# BLOQUE 4 — PROCESO COMERCIAL
# ═══════════════════════════════════════════════════════════════════════════════
seccion("Proceso Comercial y Configuración de Agenda", "")

col11, col12 = st.columns(2)
with col11:
    st.text_input("Nombre del ejecutivo que toma las reuniones", key="nombre_ejecutivo",
                  placeholder="Ej: Sam Miller")
    st.text_input("Cargo del ejecutivo", key="cargo_ejecutivo",
                  placeholder="Ej: Director Comercial")
    st.text_input("Email del ejecutivo", key="email_ejecutivo",
                  placeholder="sam@gbs-logistics.cl")
    st.text_area("Proceso comercial paso a paso", height=100, key="proceso_comercial",
                 placeholder="Ej: 1. Reunión exploratoria 2. Cotización 3. Propuesta 4. Cierre\nIndicar cuántos touchpoints hay entre el primer contacto y el cierre.")

with col12:
    duracion = st.selectbox("Duración de las reuniones", [
        "30 minutos", "45 minutos", "60 minutos"
    ], key="duracion_reunion")
    intervalo = st.selectbox("Tiempo de preparación entre reuniones (intervalo mínimo)", [
        "15 minutos", "30 minutos", "45 minutos", "60 minutos", "90 minutos"
    ], key="intervalo_reunion", index=1)
    anticipacion = st.selectbox("Tiempo máximo de anticipación para agendar", [
        "24 horas", "48 horas", "1 semana", "2 semanas"
    ], key="anticipacion_agenda", index=1)
    st.text_area("Quiénes reciben la info del lead agendado", height=80, key="notificaciones",
                 placeholder="Ej: sam@gbs-logistics.cl, gerencia@gbs-logistics.cl...")

col13, col14 = st.columns(2)
with col13:
    st.number_input("Tiempo promedio de cierre (días)", min_value=7, max_value=365,
                    value=45, key="tiempo_cierre",
                    help="Desde reunión inicial hasta firma de contrato / primera operación")
with col14:
    st.text_input("Costo promedio del servicio (ticket promedio)", key="ticket_promedio",
                  placeholder="Ej: USD 800 por embarque · USD 3.000 mensual por cliente activo",
                  help="Ayuda a calibrar el target de prospectos por volumen de operación")

plan = st.radio("Plan contratado con Conprospección", ["Starter", "Growth"],
                horizontal=True, key="plan_contratado")

# ═══════════════════════════════════════════════════════════════════════════════
# BLOQUE 5 — CAMPOS RECOMENDADOS (OUTBOUND AVANZADO)
# ═══════════════════════════════════════════════════════════════════════════════
seccion("Inteligencia Comercial Adicional (Recomendado)", "")

st.markdown(
    '<div style="font-size:13px;color:#64748b;margin-bottom:14px">'
    'Esta información nos permite personalizar las secuencias de prospección a un nivel mucho mayor. '
    'No es obligatoria, pero impacta directamente en los resultados.</div>',
    unsafe_allow_html=True,
)

col15, col16 = st.columns(2)
with col15:
    st.text_area("¿Qué preguntas de discovery funcionan mejor en las reuniones?", height=100,
                 key="preguntas_discovery",
                 placeholder="Ej: ¿Cuántos embarques manejan mensualmente? ¿Tienen problemas con documentación en aduana? ¿Quién decide el proveedor logístico?")
    st.text_area("¿Cuáles son los dolores más frecuentes que reportan los clientes actuales?", height=100,
                 key="dolores_clientes",
                 placeholder="Ej: retrasos sin previo aviso, falta de visibilidad, errores en documentación, tener que coordinar 3 proveedores distintos...")
with col16:
    st.text_area("¿Qué gatillos de compra activan la decisión? (timing de prospección)", height=100,
                 key="gatillos_compra",
                 placeholder="Ej: cambio de proveedor por falla, crecimiento en volumen de importaciones, nuevo ejecutivo de abastecimiento, peak de temporada...")
    st.text_area("¿Qué palabras clave usan los prospectos en LinkedIn / emails?", height=100,
                 key="keywords_prospecto",
                 placeholder="Ej: importaciones, COMEX, freight, supply chain, aduana, abastecimiento internacional, forwarder...")

st.text_area("Notas adicionales para el equipo de Conprospección", height=100,
             key="notas_adicionales",
             placeholder="Cualquier contexto, restricción, oportunidad o detalle que debamos saber para hacer una mejor prospección...")


def _onboarding_actual():
    return {
        "icp_pais": st.session_state.get("icp_pais", []),
        "icp_cargos": st.session_state.get("icp_cargos", []),
        "icp_industrias": st.session_state.get("icp_industrias", []),
        "icp_tamano": st.session_state.get("icp_tamano", []),
        "icp_adicional": st.session_state.get("icp_adicional", ""),
        "icp_descarte": st.session_state.get("icp_descarte", []),
        "propuesta_valor": st.session_state.get("propuesta_valor", ""),
        "dolores_clientes": st.session_state.get("dolores_clientes", ""),
        "gatillos_compra": st.session_state.get("gatillos_compra", ""),
        "keywords_prospecto": st.session_state.get("keywords_prospecto", ""),
    }


profile = perfil_icp(_onboarding_actual())
esc = lambda value: html.escape(str(value or ""))
highlight_icp = bool(st.session_state.pop("gbs_scroll_to_icp", False)) or (
    st.query_params.get("section") == "resumen_icp"
)
highlight_style = (
    f"box-shadow:0 0 0 4px {GBS_PURPLE}30,0 12px 30px rgba(91,33,182,.12);"
    if highlight_icp else ""
)
st.markdown(
    f'<div id="resumen-icp" style="scroll-margin-top:72px;background:#fff;'
    f'border:1px solid {GBS_BORDER};border-left:6px solid {GBS_PURPLE};'
    f'border-radius:12px;padding:18px 20px;margin:24px 0 18px;{highlight_style}">'
    f'<div style="font-size:16px;font-weight:850;color:#1e293b">Resumen ICP acordado</div>'
    f'<div style="font-size:12px;color:#64748b;margin:4px 0 14px">'
    f'Este perfil se construye con la definición ICP y las señales comerciales aportadas '
    f'en todo el onboarding.</div>'
    f'<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:9px;'
    f'padding:10px 13px;margin-bottom:12px;font-size:13px;font-weight:800;color:#166534">'
    f'{esc(profile["resumen"])}</div>'
    f'<div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px">'
    f'<div><b style="color:{GBS_PURPLE}">Países</b><br>'
    f'<span style="font-size:12px;color:#475569">{esc(", ".join(profile["paises"]) or "Por confirmar")}</span></div>'
    f'<div><b style="color:{GBS_PURPLE}">Tamaño de empresa</b><br>'
    f'<span style="font-size:12px;color:#475569">{esc(profile["tamano_resumido"])}</span></div>'
    f'<div><b style="color:{GBS_PURPLE}">Industrias</b><br>'
    f'<span style="font-size:12px;color:#475569">{esc(", ".join(profile["industrias"]) or "Por confirmar")}</span></div>'
    f'<div><b style="color:{GBS_PURPLE}">Cargos objetivo</b><br>'
    f'<span style="font-size:12px;color:#475569">{esc(", ".join(profile["cargos"]) or "Por confirmar")}</span></div>'
    f'</div>'
    + (
        f'<div style="margin-top:13px"><b style="font-size:12px;color:{GBS_PURPLE}">'
        f'Exclusiones</b><div style="font-size:12px;color:#475569;line-height:1.5">'
        f'{esc(", ".join(profile["exclusiones"]))}</div></div>'
        if profile["exclusiones"] else ""
    )
    + "".join(
        f'<div style="margin-top:10px"><b style="font-size:12px;color:{GBS_PURPLE}">{label}</b>'
        f'<div style="font-size:12px;color:#475569;line-height:1.5">{esc(value)}</div></div>'
        for label, value in profile["complementos"].items()
    )
    + f'<div style="font-size:11px;color:{GBS_PURPLE};font-weight:750;margin-top:14px">'
    f'Perfil confirmado con el cliente y utilizado como referencia de prospección.</div></div>',
    unsafe_allow_html=True,
)
if highlight_icp:
    components.html(
        """
        <script>
        setTimeout(() => {
          const target = window.parent.document.getElementById("resumen-icp");
          if (target) target.scrollIntoView({behavior: "smooth", block: "start"});
        }, 500);
        </script>
        """,
        height=0,
    )

# ── Botón de envío ─────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
col_send, _ = st.columns([1, 3])
with col_send:
    if st.button("Enviar formulario a Conprospección ", type="primary", use_container_width=True):
        payload = {
            "icp_pais": ", ".join(st.session_state.get("icp_pais", []) or []),
            "icp_cargos": "\n".join(st.session_state.get("icp_cargos", []) or []),
            "icp_industrias": "\n".join(st.session_state.get("icp_industrias", []) or []),
            "icp_tamano": ", ".join(st.session_state.get("icp_tamano", []) or []),
            "icp_adicional": st.session_state.get("icp_adicional", ""),
            "icp_descarte": "\n".join(st.session_state.get("icp_descarte", []) or []),
            "web": st.session_state.get("web", ""),
            "linkedin_empresa": st.session_state.get("linkedin_empresa", ""),
            "propuesta_valor": st.session_state.get("propuesta_valor", ""),
            "diferenciadores": st.session_state.get("diferenciadores", ""),
            "presentacion_servicio": st.session_state.get("presentacion_servicio", ""),
            "casos_exito": st.session_state.get("casos_exito", ""),
            "tono_lenguaje": st.session_state.get("tono_lenguaje", ""),
            "mensajes_funcionan": st.session_state.get("mensajes_funcionan", ""),
            "mensajes_no_decir": st.session_state.get("mensajes_no_decir", ""),
            "objeciones": st.session_state.get("objeciones", ""),
            "nombre_ejecutivo": st.session_state.get("nombre_ejecutivo", ""),
            "cargo_ejecutivo": st.session_state.get("cargo_ejecutivo", ""),
            "email_ejecutivo": st.session_state.get("email_ejecutivo", ""),
            "proceso_comercial": st.session_state.get("proceso_comercial", ""),
            "duracion_reunion": st.session_state.get("duracion_reunion", ""),
            "intervalo_reunion": st.session_state.get("intervalo_reunion", ""),
            "anticipacion_agenda": st.session_state.get("anticipacion_agenda", ""),
            "notificaciones": st.session_state.get("notificaciones", ""),
            "tiempo_cierre": int(st.session_state.get("tiempo_cierre", 45)),
            "ticket_promedio": st.session_state.get("ticket_promedio", ""),
            "plan_contratado": st.session_state.get("plan_contratado", ""),
            "preguntas_discovery": st.session_state.get("preguntas_discovery", ""),
            "dolores_clientes": st.session_state.get("dolores_clientes", ""),
            "gatillos_compra": st.session_state.get("gatillos_compra", ""),
            "keywords_prospecto": st.session_state.get("keywords_prospecto", ""),
            "notas_adicionales": st.session_state.get("notas_adicionales", ""),
        }
        payload["cliente"] = "gbs"
        payload["updated_at"] = "now()"
        try:
            _sb.table("gbs_onboarding").upsert(payload, on_conflict="cliente").execute()
            _notify_telegram(
                payload.get("nombre_ejecutivo", ""),
                payload.get("email_ejecutivo", ""),
            )
            st.markdown(
                f'<div style="background:#dcfce7;border:1px solid #86efac;border-radius:10px;'
                f'padding:18px 20px;margin-top:12px">'
                f'<div style="font-size:15px;font-weight:800;color:#166534;margin-bottom:6px">Formulario enviado</div>'
                f'<div style="font-size:13px;color:#15803d">'
                f'La información quedó guardada correctamente. El ejecutivo de cuenta de Conprospección '
                f'revisará los datos y se pondrá en contacto en las próximas 24 horas.<br><br>'
                f'<b>Próximo paso:</b> validación de ICP y configuración de primeras campañas.'
                f'</div></div>',
                unsafe_allow_html=True,
            )
        except Exception as e:
            st.error(f"Error al guardar el formulario: {e}")

# ── Footer ─────────────────────────────────────────────────────────────────────
cp = img_b64("conprospeccion_logo.png", 18) or ""
st.markdown(
    f'<div style="text-align:center;color:#94a3b8;font-size:11px;margin-top:40px;padding:16px">'
    f'{cp}&nbsp;Formulario de Onboarding — <b style="color:{GBS_BLUE}">Conprospección</b> · '
    f'Confidencial · {date.today().strftime("%B %Y").capitalize()}</div>',
    unsafe_allow_html=True,
)
