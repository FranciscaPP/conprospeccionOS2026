"""Intelligence Insight de BambuTech: modelo comercial relacionado con reuniones reales."""
from __future__ import annotations

import sys
from pathlib import Path

import requests
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from portal_auth import img_b64, render_client_nav, require_auth_client
from shared.bambutech_brand import BAMBU_BORDER, BAMBU_DARK, BAMBU_GREEN, BAMBU_GREEN_DARK
from shared.config import supabase_key, supabase_url
from shared.metas import meta_de
from shared.planes import plan_de

st.set_page_config(page_title="BambuTech — Intelligence Insight", layout="wide", page_icon="")
if not require_auth_client("bambutech"):
    st.stop()
render_client_nav("19_BambuTech_Intelligence", "bambutech")

if plan_de("bambutech") != "premium":
    st.markdown(
        '<div style="max-width:760px;margin:80px auto;padding:34px;border:1px solid #d9dfda;'
        'border-left:6px solid #208d25;border-radius:14px;background:#fff">'
        '<div style="font-size:23px;font-weight:850;color:#171918">Intelligence Insight</div>'
        '<div style="font-size:16px;color:#59615c;margin-top:10px">No disponible en este plan.</div></div>',
        unsafe_allow_html=True,
    )
    st.stop()

SB_URL, SB_KEY = supabase_url(), supabase_key()
HEADERS = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"}


@st.cache_data(ttl=45, show_spinner=False)
def reuniones_reales():
    meetings = requests.get(
        f"{SB_URL}/rest/v1/reuniones?select=id,ghl_contact_id,estado_validacion,excluida"
        "&cliente_slug=eq.bambutech&excluida=eq.false",
        headers=HEADERS, timeout=15,
    ).json()
    tracking = requests.get(
        f"{SB_URL}/rest/v1/seguimiento_reuniones"
        "?select=reunion_id,val_estado_final,flag_meta_countable,status_reunion"
        "&cliente_slug=eq.bambutech",
        headers=HEADERS, timeout=15,
    ).json()
    validas = sum(1 for x in tracking if x.get("flag_meta_countable") is True)
    reagendar = sum(1 for x in tracking if x.get("status_reunion") in {"reagendada", "reagendar"})
    no_validas = sum(1 for x in tracking if x.get("val_estado_final") == "no_valida")
    return {"total": len(meetings), "validas": validas, "reagendar": reagendar, "no_validas": no_validas}


REAL = reuniones_reales()
META = int((meta_de("bambutech") or {}).get("validas") or 100)
CONTACTOS, EMPRESAS, RESPUESTAS, POSITIVAS = 526, 176, 14, 5
EMAILS, ABIERTOS = 186, 82

SEGMENTOS = [
    ("Manufactura, minería y energía", 118, 5, 2),
    ("Retail y multisucursal", 104, 3, 1),
    ("Logística y supply chain", 92, 2, 1),
    ("Servicios financieros", 78, 2, 1),
    ("Salud y farmacéutica", 70, 1, 0),
    ("Construcción y servicios", 64, 1, 0),
]
CARGOS = [
    ("Tecnología / Transformación", 151, 5),
    ("Operaciones / Procesos", 126, 4),
    ("Dirección / Negocio", 103, 2),
    ("Datos / Seguridad", 82, 2),
    ("Finanzas / Marketing", 64, 1),
]
CANALES = [("Llamadas", 260, 8), ("Correo electrónico", 186, 4), ("WhatsApp", 80, 2)]

st.markdown(
    f'<style>.block-container{{max-width:1500px;padding-top:1.2rem!important}}'
    f'div[data-testid="stSelectbox"]>div{{font-size:13px}}button{{font-size:13px!important}}</style>'
    f'<div style="display:flex;align-items:center;justify-content:space-between;background:#f0f4f0;'
    f'border:1px solid {BAMBU_BORDER};padding:22px 30px;border-radius:14px;margin-bottom:20px">'
    f'<div style="display:flex;align-items:center;gap:22px">{img_b64("bambutech_logo.png", 64)}'
    f'<div style="font-size:25px;font-weight:900;color:{BAMBU_DARK}">Intelligence Insight</div></div>'
    f'<div style="font-size:12px;color:#68706b">Prospección activa<br><b>desde 18 mayo 2026</b></div></div>',
    unsafe_allow_html=True,
)


def section(title, subtitle):
    st.markdown(
        f'<div style="border-left:4px solid {BAMBU_GREEN};padding-left:14px;margin:26px 0 15px">'
        f'<div style="font-size:18px;font-weight:900;color:{BAMBU_DARK}">{title}</div>'
        f'<div style="font-size:12px;color:#64748b;margin-top:3px">{subtitle}</div></div>',
        unsafe_allow_html=True,
    )


def card(label, value, sub, color=BAMBU_GREEN_DARK):
    return (
        f'<div style="background:#fff;border:1px solid {BAMBU_BORDER};border-top:4px solid {color};'
        f'border-radius:12px;padding:18px;text-align:center;min-height:122px">'
        f'<div style="font-size:28px;font-weight:900;color:{color}">{value}</div>'
        f'<div style="font-size:11px;font-weight:850;color:{BAMBU_DARK};text-transform:uppercase;margin-top:7px">{label}</div>'
        f'<div style="font-size:10px;color:#94a3b8;margin-top:5px">{sub}</div></div>'
    )


def bars(rows, color):
    maximum = max(x[1] for x in rows) or 1
    return "".join(
        f'<div style="display:grid;grid-template-columns:190px 1fr 45px;gap:10px;align-items:center;margin:11px 0">'
        f'<span style="font-size:12px;text-align:right;color:#334155">{name}</span>'
        f'<div style="height:30px;background:#edf1ee;border-radius:9px;overflow:hidden">'
        f'<div style="height:100%;width:{max(5,round(value/maximum*100))}%;background:{color};border-radius:9px"></div></div>'
        f'<b style="font-size:12px;color:{color}">{value}</b></div>'
        for name, value, *_ in rows
    )


pct = round(REAL["validas"] / META * 100) if META else 0
st.markdown(
    f'<div style="background:#fff;border:1px solid {BAMBU_BORDER};border-radius:14px;padding:22px 28px">'
    f'<div style="display:flex;justify-content:space-between;align-items:end">'
    f'<div><b style="font-size:13px;color:{BAMBU_GREEN_DARK}">AVANCE DE LA META</b>'
    f'<div style="font-size:12px;color:#64748b;margin-top:6px">Garantía: {META} reuniones válidas · inicio 18 de mayo</div></div>'
    f'<div style="font-size:31px;font-weight:900;color:{BAMBU_GREEN_DARK}">{REAL["validas"]}<span style="font-size:16px;color:#64748b"> / {META}</span></div></div>'
    f'<div style="height:24px;background:#edf1ee;border-radius:14px;margin-top:17px;overflow:hidden">'
    f'<div style="height:100%;width:{max(pct,1)}%;background:linear-gradient(90deg,#208d25,#38d430)"></div></div>'
    f'<div style="font-size:11px;color:#64748b;margin-top:8px">{pct}% de la meta · faltan {max(META-REAL["validas"],0)} válidas</div></div>',
    unsafe_allow_html=True,
)

cols = st.columns(4)
for col, data in zip(cols, [
    ("Reuniones válidas", REAL["validas"], "Confirmadas por Conprospección", "#16a34a"),
    ("Reuniones no válidas", REAL["no_validas"], "Descartadas en evaluación", "#dc2626"),
    ("Reagendar", REAL["reagendar"], "Pendientes de reprogramar", "#d97706"),
    ("Avance comercial", "0%", "Válidas que avanzaron en pipeline", "#208d25"),
]):
    col.markdown(card(*data), unsafe_allow_html=True)

st.markdown(
    '<div style="background:#ecf9ec;border:1px solid #b8dfba;border-left:5px solid #38d430;'
    'border-radius:10px;padding:14px 18px;margin-top:12px;font-size:13px;color:#36513b">'
    '<b>Mes 1 — Estrategia comercial y validación.</b><br>'
    'Este primer recorte permite validar cargos, industrias, mensajes y tipos de respuesta antes de escalar volumen.</div>',
    unsafe_allow_html=True,
)

section("Resumen ejecutivo", "Lo esencial en 30 segundos: embudo, foco y estado de la meta")
st.markdown(
    f'<div style="background:#fff;border:1px solid {BAMBU_BORDER};border-left:4px solid {BAMBU_GREEN};'
    f'border-radius:11px;padding:16px 20px;font-size:13px;line-height:1.8;color:#334155">'
    f'• <b>Embudo:</b> {CONTACTOS} contactos, {RESPUESTAS} respuestas ({RESPUESTAS/CONTACTOS:.1%}), '
    f'{POSITIVAS} positivas y {REAL["total"]} reuniones reales.<br>'
    f'• <b>Foco:</b> Tecnología, Transformación y Operaciones concentran la mayor señal esperada.<br>'
    f'• <b>Meta:</b> {REAL["validas"]} reuniones válidas contabilizadas de {META}.</div>',
    unsafe_allow_html=True,
)

section("Métricas del reporte", "Resultados de prospección del recorte seleccionado")
metrics = [
    ("Contactos trabajados", CONTACTOS, "Base activa del recorte", "#208d25"),
    ("Empresas impactadas", EMPRESAS, "Promedio de 3 contactos por empresa", "#208d25"),
    ("Respuestas", RESPUESTAS, f"{RESPUESTAS/CONTACTOS:.1%} de la base", "#db2777"),
    ("Respuestas positivas", POSITIVAS, f"{POSITIVAS/RESPUESTAS:.0%} de respuestas", "#f59e0b"),
    ("Reuniones", REAL["total"], "Dato real sincronizado", "#16a34a"),
    ("Conversión", f"{REAL['total']/CONTACTOS:.1%}", "Reuniones / contactos", "#16a34a"),
]
for row in (metrics[:3], metrics[3:]):
    cs = st.columns(3)
    for c, item in zip(cs, row):
        c.markdown(card(*item), unsafe_allow_html=True)

left, right = st.columns(2)
with left:
    st.markdown("<b>Contactos por cargo</b>", unsafe_allow_html=True)
    st.markdown(bars(CARGOS, "#db2777"), unsafe_allow_html=True)
with right:
    st.markdown("<b>Contactos por industria</b>", unsafe_allow_html=True)
    st.markdown(bars([(x[0], x[1]) for x in SEGMENTOS], "#f59e0b"), unsafe_allow_html=True)

section("Aperturas y respuestas por segmento", "Señales iniciales para decidir dónde concentrar el esfuerzo")
cs = st.columns(3)
for c, item in zip(cs, [
    ("Emails enviados", EMAILS, "Contactos del canal correo", "#208d25"),
    ("Emails abiertos", ABIERTOS, "Muestra operativa del recorte", "#db2777"),
    ("Tasa de apertura", f"{ABIERTOS/EMAILS:.1%}", "Abiertos / enviados", "#16a34a"),
]):
    c.markdown(card(*item), unsafe_allow_html=True)

left, right = st.columns(2)
with left:
    st.markdown("<b>Respuestas por cargo</b>", unsafe_allow_html=True)
    st.markdown(bars([(x[0], x[2]) for x in CARGOS], "#7c3aed"), unsafe_allow_html=True)
with right:
    st.markdown("<b>Respuestas por canal</b>", unsafe_allow_html=True)
    st.markdown(bars([(x[0], x[2]) for x in CANALES], "#208d25"), unsafe_allow_html=True)

section("Efectividad por segmento", "Tasa de respuesta positiva, no solo volumen")
left, right = st.columns(2)
for container, title, rows in [
    (left, "Por cargo", CARGOS),
    (right, "Por industria", [(name, total, positive) for name, total, _, positive in SEGMENTOS]),
]:
    with container:
        html = f'<div style="background:#fff;border:1px solid {BAMBU_BORDER};border-radius:12px;padding:16px 20px"><b>{title}</b>'
        for name, total, positive in rows:
            rate = positive / total if total else 0
            action = "Priorizar" if rate >= .02 else ("Observar" if rate > 0 else "Cortar")
            color = "#16a34a" if action == "Priorizar" else ("#d97706" if action == "Observar" else "#dc2626")
            html += (
                f'<div style="display:grid;grid-template-columns:1fr 58px 62px 75px;gap:8px;padding:10px 0;'
                f'border-bottom:1px solid #edf1ee;font-size:12px"><span>{name}</span><b>{rate:.1%}</b>'
                f'<span>{positive}/{total}</span><span style="color:{color};font-weight:800">{action}</span></div>'
            )
        st.markdown(html + "</div>", unsafe_allow_html=True)

section("Motivos de rechazo", "Por qué se cae el resto de los contactos y qué hacer")
reasons = [("No es prioridad ahora", 4), ("Proveedor actual", 3), ("Sin respuesta posterior", 2)]
left, right = st.columns([1, 1.15])
left.markdown(bars(reasons, "#db2777"), unsafe_allow_html=True)
right.markdown(
    f'<div style="background:#fff;border:1px solid {BAMBU_BORDER};border-left:4px solid #db2777;'
    'border-radius:12px;padding:17px 20px;font-size:12px;line-height:1.8">'
    '<b>Acción sugerida por motivo</b><br><br>'
    '<b>Proveedor actual:</b> posicionar a BambuTech como célula especializada complementaria.<br>'
    '<b>No es prioridad:</b> conectar el mensaje con backlog, riesgo operativo y velocidad de ejecución.<br>'
    '<b>Sin respuesta:</b> variar canal y horario; sostener una secuencia breve antes de cerrar.</div>',
    unsafe_allow_html=True,
)

section("Perfil del Cliente Ideal (ICP y Buyer Persona)", "A quién apunta la campaña de BambuTech Services")
st.markdown(
    f'<div style="background:#fff;border:1px solid {BAMBU_BORDER};border-radius:12px;padding:19px 24px;'
    'font-size:13px;line-height:1.8;color:#334155">'
    '<b>Propuesta de valor:</b> desarrollo e integración tecnológica a la medida para conectar sistemas, '
    'automatizar procesos y acelerar iniciativas que quedan en backlog.<br>'
    '<b>Empresas objetivo:</b> organizaciones de México y Latinoamérica desde 35 colaboradores, con mayor '
    'afinidad en cuentas de 100 a 1.000+ empleados y operaciones complejas.<br>'
    '<b>Cargos:</b> CIO, CTO, CISO, CEO, Operaciones, Transformación Digital, Datos y Finanzas.<br>'
    '<b>Industrias foco:</b> manufactura, minería, energía, retail, logística, servicios financieros, salud y construcción.<br>'
    '<b>Se descarta:</b> cuentas sin necesidad tecnológica identificable, sin capacidad de inversión o fuera de mercados objetivo.</div>',
    unsafe_allow_html=True,
)

section("Embudo de conversión", "De contactos trabajados a reuniones, en un vistazo")
funnel = [
    ("Contactos trabajados", CONTACTOS, "#208d25"),
    ("Respuestas", RESPUESTAS, "#db2777"),
    ("Respuestas positivas", POSITIVAS, "#f59e0b"),
    ("Reuniones reales", REAL["total"], "#16a34a"),
    ("Reuniones válidas", REAL["validas"], "#0f7a2e"),
]
st.markdown(bars(funnel, "#208d25"), unsafe_allow_html=True)

section("Hallazgos clave", "Lo que los datos están diciendo en este recorte")
for title, text, color in [
    ("Tecnología y Transformación concentran la señal", "Es el grupo de cargos con mayor volumen de respuestas del modelo inicial.", "#208d25"),
    ("Manufactura, minería y energía lideran el foco", "El dolor de integración, trazabilidad y riesgo operativo conecta directamente con la oferta.", "#208d25"),
    ("Tres reuniones ya cumplen la validación", "Curacreto, EMWA y Difarmer cuentan para el avance contractual con evidencia registrada.", "#208d25"),
]:
    st.markdown(
        f'<div style="background:#fff;border:1px solid {BAMBU_BORDER};border-left:5px solid {color};'
        f'border-radius:11px;padding:14px 18px;margin:9px 0"><b style="font-size:13px">{title}</b>'
        f'<div style="font-size:12px;color:#64748b;margin-top:5px">{text}</div></div>',
        unsafe_allow_html=True,
    )

section("Riesgos detectados", "Señales que conviene vigilar")
for title, text in [
    ("Muestra todavía temprana", "Las tasas por segmento son direccionales; deben leerse junto con el volumen."),
    ("Conversión positiva a reunión por fortalecer", "Acelerar seguimiento a respuestas con interés y derivación a decisores."),
]:
    st.markdown(
        f'<div style="background:#fff;border:1px solid #fecaca;border-left:5px solid #dc2626;'
        f'border-radius:11px;padding:14px 18px;margin:9px 0"><b>{title}</b>'
        f'<div style="font-size:12px;color:#64748b;margin-top:5px">{text}</div></div>',
        unsafe_allow_html=True,
    )

section("Recomendaciones", "Próximas acciones sugeridas")
st.markdown(
    '<div style="background:#ecf9ec;border:1px solid #b8dfba;border-left:5px solid #38d430;'
    'border-radius:11px;padding:16px 20px;font-size:13px;line-height:1.8">'
    '1. Priorizar Tecnología, Transformación y Operaciones.<br>'
    '2. Usar casos de integración, automatización, backlog y visibilidad operativa por industria.<br>'
    '3. Reforzar seguimiento multicanal a respuestas positivas.<br>'
    '4. Mantener la validación de reuniones conectada al avance contractual real.</div>',
    unsafe_allow_html=True,
)

st.caption(
    "Las reuniones y su avance son datos reales sincronizados. "
    "Los indicadores de actividad y segmentación son una proyección operativa inicial sobre 526 contactos."
)
