"""Intelligence Insight de BambuTech: estrategia comercial y resultados del mes."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
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


@st.cache_data(ttl=120, show_spinner=False)
def cargar_snapshot():
    p = DASHBOARD_DIR / "data" / "bambutech_intelligence.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


REAL = reuniones_reales()
META = int((meta_de("bambutech") or {}).get("validas") or 100)
SNAP = cargar_snapshot()
if not SNAP:
    st.error("Aún no se ha generado el consolidado del mes.")
    st.stop()

REG = pd.DataFrame(SNAP["registros"])
REG["canal"] = REG["canal"].replace({"Llamadas/WhatsApp": "Llamadas", "Llamada": "Llamadas"})
CORREO = SNAP["correo"]
OBJ = SNAP["objetivo"]
EMPRESAS_POSITIVAS = SNAP.get("empresas_positivas", [])
RES_LABEL = {
    "positiva": "Pidieron información o reunión", "deriva": "Derivan / refieren a un decisor",
    "negativa": "No interesado / no califica", "reagendar": "Reagendar",
    "no_contesta": "En seguimiento (sin respuesta aún)", "numero_malo": "Contacto no válido",
}
EXCLUIR_SEG = {"Sin clasificar", "Otros"}


# ---------------- helpers de UI ----------------
def section(title, subtitle=""):
    st.markdown(
        f'<div style="border-left:4px solid {BAMBU_GREEN};padding-left:13px;margin:24px 0 12px">'
        f'<div style="font-size:17px;font-weight:900;color:{BAMBU_DARK}">{title}</div>'
        + (f'<div style="font-size:12px;color:#64748b;margin-top:2px">{subtitle}</div>' if subtitle else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def scard(label, value, sub="", color=BAMBU_GREEN_DARK, tip=""):
    t = f' title="{tip}"' if tip else ""
    return (
        f'<div{t} style="background:#fff;border:1px solid {BAMBU_BORDER};border-top:3px solid {color};'
        f'border-radius:10px;padding:12px 14px;text-align:center;min-height:84px">'
        f'<div style="font-size:22px;font-weight:900;color:{color}">{value}</div>'
        f'<div style="font-size:10.5px;font-weight:800;color:{BAMBU_DARK};text-transform:uppercase;'
        f'letter-spacing:.3px;margin-top:5px">{label}</div>'
        + (f'<div style="font-size:10px;color:#94a3b8;margin-top:3px;line-height:1.3">{sub}</div>' if sub else "")
        + "</div>"
    )


def bars(rows, color):
    mx = max((v for _, v in rows), default=0) or 1
    return "".join(
        f'<div style="display:grid;grid-template-columns:210px 1fr 42px;gap:10px;align-items:center;margin:7px 0">'
        f'<span style="font-size:12px;text-align:right;color:#334155">{n}</span>'
        f'<div style="height:22px;background:#edf1ee;border-radius:7px;overflow:hidden">'
        f'<div style="height:100%;width:{max(4, round(v / mx * 100))}%;background:{color};border-radius:7px"></div></div>'
        f'<b style="font-size:12px;color:{color}">{v}</b></div>'
        for n, v in rows
    )


def top_tabla(df, dim):
    rows = []
    for key, sub in df.groupby(dim):
        if key in EXCLUIR_SEG:
            continue
        pos = int(sub.resultado.isin(["positiva", "deriva"]).sum())
        conv = int((~sub.resultado.isin(["no_contesta", "numero_malo"])).sum())
        tasa = pos / conv if conv else 0
        rows.append((key, len(sub), conv, pos, tasa))
    rows.sort(key=lambda r: (-r[3], -r[2], -r[1]))
    rows = rows[:5]
    body = (
        '<div style="display:grid;grid-template-columns:1fr 72px 82px 62px 58px;gap:8px;'
        'padding:0 4px 7px;border-bottom:1px solid #e5e7eb;font-size:10px;font-weight:800;'
        'text-transform:uppercase;color:#64748b">'
        '<span>Segmento</span><span>Gestiones</span><span>Conversaciones</span>'
        '<span>Positivas</span><span>Tasa</span></div>'
    )
    for name, gest, conv, pos, tasa in rows:
        body += (
            '<div style="display:grid;grid-template-columns:1fr 72px 82px 62px 58px;gap:8px;'
            'padding:9px 4px;border-bottom:1px solid #edf1ee;font-size:11.5px;align-items:center">'
            f'<b style="color:#334155">{name}</b><span>{gest}</span><span>{conv}</span>'
            f'<span style="color:#16a34a;font-weight:800">{pos}</span>'
            f'<span style="color:#16a34a;font-weight:800">{tasa:.0%}</span></div>'
        )
    empty = (
        "<span style='font-size:12px;color:#64748b'>"
        "Primer mes de estrategia: todavía no hay muestra suficiente para comparar este segmento."
        "</span>"
    )
    content = body if rows else empty
    return (f'<div style="background:#fff;border:1px solid {BAMBU_BORDER};border-radius:11px;'
            f'padding:14px 16px">{content}</div>'), rows


def _opts(col):
    return ["Todas"] + sorted([x for x in REG[col].dropna().unique() if str(x).strip()])


def conteo(df, *res):
    return int(df.resultado.isin(res).sum())


# ================= HEADER =================
st.markdown(
    f'<style>.block-container{{max-width:1380px;padding-top:1rem!important}}</style>'
    f'<div style="display:flex;align-items:center;gap:18px;background:#f0f4f0;border:1px solid {BAMBU_BORDER};'
    f'padding:15px 24px;border-radius:14px;margin-bottom:10px">'
    f'<div style="background:linear-gradient(135deg,#07110c,#0e1b15);padding:8px 14px;border-radius:12px;'
    f'display:inline-flex;align-items:center">{img_b64("bambutech_logo.png", 46)}</div>'
    f'<div><div style="font-size:23px;font-weight:900;color:{BAMBU_DARK}">Intelligence Insight</div>'
    f'<div style="font-size:12px;color:#68706b">Prospección activa desde el <b>18 de mayo 2026</b> · '
    f'el mes previo fue configuración · se actualiza 1×/mes</div></div></div>',
    unsafe_allow_html=True,
)

# ===== ① Avance de meta (arriba, compacto) =====
pct_meta = round(REAL["validas"] / META * 100) if META else 0
st.markdown(
    f'<div style="display:flex;align-items:center;gap:14px;background:#fff;border:1px solid {BAMBU_BORDER};'
    f'border-radius:11px;padding:11px 18px;margin-bottom:10px">'
    f'<span style="font-size:12px;font-weight:850;color:{BAMBU_GREEN_DARK};white-space:nowrap">AVANCE DE LA META</span>'
    f'<div style="flex:1;height:14px;background:#edf1ee;border-radius:8px;overflow:hidden">'
    f'<div style="height:100%;width:{max(pct_meta, 2)}%;background:linear-gradient(90deg,#208d25,#38d430)"></div></div>'
    f'<span style="font-size:14px;font-weight:900;color:{BAMBU_GREEN_DARK};white-space:nowrap">'
    f'{REAL["validas"]} / {META} <span style="color:#94a3b8;font-weight:600">({pct_meta}%)</span></span></div>',
    unsafe_allow_html=True,
)

# ===== ② Reuniones (tarjetas chicas + acceso a validación) =====
rc = st.columns(4)
for c, d in zip(rc, [
    ("Reuniones totales", REAL["total"], "Agendadas en el período", "#208d25"),
    ("Válidas", REAL["validas"], "Confirmadas", "#16a34a"),
    ("No válidas", REAL["no_validas"], "Descartadas", "#dc2626"),
    ("Reagendar", REAL["reagendar"], "A reprogramar", "#d97706"),
]):
    c.markdown(scard(*d), unsafe_allow_html=True)
if st.button("Ver detalle en Validación de Reuniones →", key="goto_val"):
    st.switch_page("pages/18_BambuTech_Validacion_Reuniones.py")

st.markdown(
    f'<div style="background:#ecf9ec;border:1px solid #b8dfba;border-left:5px solid #38d430;'
    f'border-radius:10px;padding:11px 17px;margin:12px 0;font-size:13px;color:#36513b">'
    f'<b>Este mes se trató de la estrategia.</b> Probamos un enfoque multicanal completo '
    f'(correo, llamadas y WhatsApp) para detectar industrias, áreas y mensajes con mejor respuesta.</div>',
    unsafe_allow_html=True,
)

# ===== ③ Filtros cruzados =====
section("Análisis por canal y segmento", "Los tres filtros se cruzan y actualizan todo el análisis")
fc = st.columns(3)
f_canal = fc[0].selectbox("Canal", ["Todos"] + sorted(REG["canal"].dropna().unique()))
base_ind = REG if f_canal == "Todos" else REG[REG["canal"] == f_canal]
f_ind = fc[1].selectbox(
    "Macro-industria",
    ["Todas"] + sorted(x for x in base_ind["industria"].dropna().unique() if str(x).strip()),
)
base_area = base_ind if f_ind == "Todas" else base_ind[base_ind["industria"] == f_ind]
f_area = fc[2].selectbox(
    "Macro-cargo (área)",
    ["Todas"] + sorted(x for x in base_area["area"].dropna().unique() if str(x).strip()),
)
REGf = REG.copy()
if f_canal != "Todos": REGf = REGf[REGf.canal == f_canal]
if f_ind != "Todas": REGf = REGf[REGf.industria == f_ind]
if f_area != "Todas": REGf = REGf[REGf.area == f_area]

fp, fd = conteo(REGf, "positiva"), conteo(REGf, "deriva")
fn, fr = conteo(REGf, "negativa"), conteo(REGf, "reagendar")
fnoc, fmalo = conteo(REGf, "no_contesta"), conteo(REGf, "numero_malo")
fconv = len(REGf) - fnoc - fmalo
fpostot = fp + fd

# ===== ④ Resumen filtrado =====
section("Resumen del mes", "Las métricas responden a los filtros seleccionados")
tasa = fpostot / fconv if fconv else 0
rs = st.columns(4)
rs[0].markdown(scard("Gestiones", len(REGf), "Registros dentro del filtro"), unsafe_allow_html=True)
rs[1].markdown(scard("Conversaciones", fconv, "Excluye sin respuesta y contacto inválido"),
               unsafe_allow_html=True)
rs[2].markdown(scard("Respuestas positivas", fpostot, f"{fp} interés directo + {fd} derivaciones", "#16a34a"),
               unsafe_allow_html=True)
rs[3].markdown(scard("Tasa positiva", f"{tasa:.0%}", "Positivas / conversaciones", "#16a34a"),
               unsafe_allow_html=True)
st.caption(
    f"Base multicanal total: {SNAP['universo_unico']:,} contactos únicos. "
    "Las métricas superiores corresponden al detalle disponible para el filtro."
)

# ===== ⑤ Actividad por canal filtrada =====
section("Actividad por canal", "Distribución de gestiones, conversaciones y positivas dentro del filtro")
channel_rows = []
for channel, sub in REGf.groupby("canal"):
    conv = len(sub) - conteo(sub, "no_contesta") - conteo(sub, "numero_malo")
    channel_rows.append((channel, len(sub), conv, conteo(sub, "positiva", "deriva")))
channel_rows.sort(key=lambda row: (-row[1], row[0]))
if channel_rows:
    activity_df = pd.DataFrame(
        channel_rows, columns=["Canal", "Gestiones", "Conversaciones", "Positivas"]
    )
    activity_df["Tasa positiva"] = activity_df.apply(
        lambda row: f"{row['Positivas'] / row['Conversaciones']:.0%}" if row["Conversaciones"] else "0%",
        axis=1,
    )
    st.dataframe(activity_df, hide_index=True, use_container_width=True)
if f_canal in {"Todos", "Correo"} and f_ind == "Todas" and f_area == "Todas":
    st.caption(
        f"Volumen agregado de correo del período: {CORREO['enviados']:,} enviados · "
        f"{CORREO['entregados']:,} entregados · {CORREO['contactados']:,} contactados · "
        f"{CORREO['respuestas']} respuestas. Este volumen no se distribuye artificialmente por segmento."
    )

# ===== ⑤ Resultados de conversación =====
section("Resultados de conversación", "Cómo respondió el mercado en llamadas y WhatsApp")
res_rows = [(RES_LABEL[k], conteo(REGf, k)) for k in
            ["positiva", "deriva", "reagendar", "negativa", "no_contesta", "numero_malo"]]
st.markdown(bars([(n, v) for n, v in res_rows if v > 0], "#208d25"), unsafe_allow_html=True)
st.markdown(
    f'<div style="display:flex;gap:9px;flex-wrap:wrap;margin-top:9px;font-size:12px;font-weight:700">'
    f'<span style="background:#dcfce7;color:#166534;padding:4px 11px;border-radius:9px">'
    f'Positivas: {fpostot}{f" ({fpostot / fconv:.0%})" if fconv else ""}</span>'
    f'<span style="background:#ede9fe;color:#5b21b6;padding:4px 11px;border-radius:9px">Derivaciones: {fd}</span>'
    f'<span style="background:#fee2e2;color:#991b1b;padding:4px 11px;border-radius:9px">Negativas: {fn}</span>'
    f'<span style="background:#fef9c3;color:#854d0e;padding:4px 11px;border-radius:9px">En seguimiento: {fnoc}</span>'
    f'</div>',
    unsafe_allow_html=True,
)

# ===== Empresas que respondieron =====
section(
    "Empresas que respondieron",
    "Cuentas con información adicional, coordinando reunión o reunión agendada",
)
if EMPRESAS_POSITIVAS:
    empresas_df = pd.DataFrame(EMPRESAS_POSITIVAS)
    if f_canal != "Todos":
        empresas_df = empresas_df[empresas_df["canal"] == f_canal]
    if f_ind != "Todas":
        empresas_df = empresas_df[empresas_df["industria"] == f_ind]
    if f_area != "Todas":
        empresas_df = empresas_df[empresas_df["area"] == f_area]
    if empresas_df.empty:
        st.info("Primer mes de estrategia: este segmento todavía no registra empresas con respuesta positiva.")
    else:
        st.dataframe(
            empresas_df.rename(columns={
                "empresa": "Empresa",
                "estado": "Estado",
                "industria": "Macro-industria",
                "area": "Macro-cargo (área)",
                "canal": "Canal",
            }),
            hide_index=True,
            use_container_width=True,
            column_order=["Empresa", "Estado", "Macro-industria", "Macro-cargo (área)", "Canal"],
        )
else:
    st.info("Primer mes de estrategia: el detalle de empresas se incorporará en el próximo consolidado.")

# ===== ⑦ Rankings =====
section("Top industrias y cargos", "Rankings recalculados según los filtros superiores")
si, sa = st.columns(2)
with si:
    st.markdown("<b style='font-size:12.5px'>Top macro-industrias</b>", unsafe_allow_html=True)
    html_i, rows_i = top_tabla(REGf, "industria")
    st.markdown(html_i, unsafe_allow_html=True)
with sa:
    st.markdown("<b style='font-size:12.5px'>Top macro-cargos (áreas)</b>", unsafe_allow_html=True)
    html_a, rows_a = top_tabla(REGf, "area")
    st.markdown(html_a, unsafe_allow_html=True)
    with st.expander("¿Qué es un macro-cargo (área)?"):
        st.caption("Agrupamos los cientos de cargos en **áreas funcionales** (Tecnología, Operaciones, "
                   "Dirección, Comercial, Finanzas, RRHH, Riesgo) para definir estrategia por área, no cargo a cargo.")

# ===== ⑦ Cuentas objetivo =====
section("Cuentas objetivo del cliente", "Cobertura de las empresas que BambuTech priorizó")
o = st.columns(3)
o[0].markdown(scard("Cuentas objetivo", OBJ["total"], "Definidas por BambuTech"), unsafe_allow_html=True)
o[1].markdown(scard("Activadas", f'{OBJ["prospectadas"]} ({OBJ["pct"]}%)', "Contactadas este ciclo", "#16a34a"),
              unsafe_allow_html=True)
o[2].markdown(scard("Por activar", OBJ["pendientes"], "Para la siguiente campaña", "#d97706"), unsafe_allow_html=True)

# ===== ⑧ Próximos pasos (narrativa + mercado) =====
section("Próximos pasos", "Lectura estratégica del mes y plan para el siguiente ciclo")
st.markdown(
    f'<div style="background:#fff;border:1px solid {BAMBU_BORDER};border-left:4px solid {BAMBU_GREEN};'
    f'border-radius:11px;padding:16px 20px;font-size:13px;line-height:1.75;color:#334155">'
    f'El <b>primer mes fue de estrategia comercial</b>: cruzamos las industrias y áreas que BambuTech '
    f'priorizó con la respuesta real del mercado. Detectamos que <b>Industrial / Manufactura</b> y '
    f'<b>Logística</b> son las que mejor responden — y, según la investigación de mercado, también las que '
    f'<b>más crecen por el nearshoring</b>: México concentra más del <b>72% de la relocalización de '
    f'Latinoamérica</b>, con logística e infraestructura industrial entre los sectores ganadores. '
    f'Salud y Retail completan el foco, con inversión digital acelerada (Retail crece 7–8% anual en TIC).'
    f'<br><br><b>Plan para el siguiente ciclo:</b><br>'
    f'1. Concentrar la <b>estrategia híbrida</b> (correo + llamadas + WhatsApp) en Industrial y Logística, '
    f'los sectores que más responden y más crecen.<br>'
    f'2. Reforzar <b>WhatsApp como canal de cierre</b> tras el primer contacto.<br>'
    f'3. Activar las <b>{OBJ["pendientes"]} cuentas objetivo</b> aún sin trabajar, con cadencia más larga '
    f'para las cuentas grandes.<br>'
    f'4. Dirigir el mensaje a <b>Tecnología/Transformación y Operaciones</b>, donde está la decisión '
    f'de integración y automatización.</div>',
    unsafe_allow_html=True,
)

# ===== Descargar informe =====
def informe_html():
    seg_i, _ = top_tabla(REG, "industria")
    seg_a, _ = top_tabla(REG, "area")
    total_conv = len(REG) - conteo(REG, "no_contesta") - conteo(REG, "numero_malo")
    total_pos = conteo(REG, "positiva", "deriva")
    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<title>BambuTech · Intelligence Insight</title></head>
<body style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#f4f6f4;color:#0f172a;max-width:980px;margin:0 auto;padding:24px">
<div style="background:linear-gradient(135deg,#07110c,#0e1b15);color:#fff;padding:22px 26px;border-radius:14px">
<div style="font-size:24px;font-weight:900">Intelligence Insight · BambuTech</div>
<div style="font-size:12px;color:#baf8d0;margin-top:4px">Prospección activa desde el 18 de mayo 2026 · informe mensual</div></div>
<h3 style="color:{BAMBU_GREEN_DARK}">Resumen</h3><ul>
<li>Avance de la meta: <b>{REAL['validas']} / {META}</b> ({pct_meta}%)</li>
<li>Contactos únicos: <b>{SNAP['universo_unico']:,}</b></li>
<li>Conversaciones: <b>{total_conv}</b> · Positivas: <b>{total_pos}</b>
({total_pos / total_conv:.0%})</li>
<li>Correo: {CORREO['enviados']} enviados → {CORREO['contactados']} contactados → {CORREO['respuestas']} respuestas</li>
<li>Cuentas objetivo activadas: <b>{OBJ['prospectadas']} / {OBJ['total']}</b> ({OBJ['pct']}%)</li></ul>
<h3 style="color:{BAMBU_GREEN_DARK}">Respuesta por macro-industria (top 5)</h3>{seg_i}
<h3 style="color:{BAMBU_GREEN_DARK}">Respuesta por área (top 5)</h3>{seg_a}
</body></html>"""


st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
st.markdown(
    f'<style>div[class*="st-key-dl_informe"] button{{background:{BAMBU_GREEN_DARK}!important;'
    f'border-color:{BAMBU_GREEN_DARK}!important;color:#fff!important;font-weight:800!important}}</style>',
    unsafe_allow_html=True,
)
st.download_button("⬇  Descargar informe", data=informe_html(),
                   file_name="BambuTech_Intelligence_2026-06.html", mime="text/html", key="dl_informe")
