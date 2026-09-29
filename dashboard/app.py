import sys
from pathlib import Path
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from master_auth import require_master_auth, render_master_user_sidebar, _img_b64

# Paleta oficial Conprospeccion (fuente: shared/cp_design.py)
CP_GOLD = "#FFD700"
CP_GOLD_SOFT = "#FFF7BF"
CP_CARBON = "#333333"
CP_INK = "#1A1A1A"
CP_BG = "#FAFAF8"
CP_SURFACE = "#FFFFFF"
CP_MUTED = "#6B6B6B"
CP_LINE = "#EDECEA"

st.set_page_config(
    page_title="ConprospeccionOS",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if not require_master_auth():
    st.stop()

# ── CSS global (paleta Conprospeccion: dorado + carbon) ────────────────────────
st.markdown("""
<style>
  [data-testid="stSidebar"] { background: #1A1A1A !important; }
  [data-testid="stSidebar"] * { color: #f4f4f2 !important; }
  /* Ocultar la lista automatica de paginas: la navegacion se hace por tarjetas */
  [data-testid="stSidebarNav"] { display: none !important; }
  /* Tarjeta clicable: un boton transparente cubre toda la tarjeta,
     asi el clic navega DENTRO de la sesion (no recarga, no cierra login).
     Se posiciona por la clase st-key- del contenedor y del boton. */
  [class*="st-key-modcard"] { position: relative !important; margin-bottom: 16px; }
  /* inset:0 estira el boton a TODO el alto de la tarjeta (height:100% no sirve
     si el padre no tiene alto fijo). Asi el clic funciona en toda la tarjeta. */
  [class*="st-key-modbtn"] {
    position: absolute !important; inset: 0 !important; margin: 0 !important; z-index: 3;
  }
  [class*="st-key-modbtn"] button {
    width: 100% !important; height: 100% !important; min-height: 0 !important;
    opacity: 0 !important; border: none !important; cursor: pointer !important;
  }
  [class*="st-key-modcard"]:hover .module-card {
    box-shadow: 0 8px 22px rgba(0,0,0,0.13);
    border-left-color: #FFCC00;
    transform: translateY(-2px);
  }
  .module-card {
    background: #FFFFFF;
    border-radius: 14px;
    padding: 22px 26px 20px;
    border: 1px solid #EDECEA;
    border-left: 5px solid #FFD700;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    min-height: 172px;
    transition: box-shadow .18s, transform .18s, border-color .18s;
  }
  a.card-link .module-card { cursor: pointer; }
  .module-card.is-soon { opacity: .92; border-left-color: #C9C9C4; cursor: default; }
  .module-card h3 { margin: 0 0 6px; font-size: 17px; color: #1A1A1A; }
  .module-card p { margin: 0; font-size: 13px; color: #6B6B6B; line-height: 1.5; }
  .tag {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    margin-top: 10px;
  }
  .tag-live { background: #EAF6EF; color: #15803D; }
  .tag-soon { background: #FFF3D8; color: #A66A00; }
  .tag-beta { background: #FFF7BF; color: #8A6D00; }
  .cp-client-head {
    font-size: 15px; font-weight: 800; color: #1A1A1A;
    margin: 10px 0 6px; letter-spacing: -0.2px;
  }
  /* Botones dorados de Conprospeccion */
  div.stButton > button[kind="primary"] {
    background: #FFD700 !important;
    color: #1A1A1A !important;
    border: 1px solid #E6C200 !important;
    font-weight: 700 !important;
  }
  div.stButton > button[kind="primary"]:hover {
    background: #FFCC00 !important;
    border-color: #C9A800 !important;
  }
  div.stButton > button[kind="secondary"] {
    border: 1px solid #C9C9C4 !important;
    color: #1A1A1A !important;
    font-weight: 600 !important;
  }
  div.stButton > button[kind="secondary"]:hover {
    border-color: #FFD700 !important;
    color: #1A1A1A !important;
  }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
_logo = _img_b64("cp_mark_dark.png", 46)
_logo_html = _logo if _logo else (
    '<div style="background:#FFD700;border-radius:12px;padding:10px 16px;'
    'color:#1A1A1A;font-weight:800;font-size:22px;line-height:1">CP</div>'
)
st.markdown(f"""
<div style="background:linear-gradient(135deg,#1A1A1A 0%,#333333 100%);
            padding:40px 48px;border-radius:16px;margin-bottom:32px;">
  <div style="display:flex;align-items:center;gap:16px;margin-bottom:12px">
    {_logo_html}
    <div>
      <div style="color:white;font-size:30px;font-weight:800;letter-spacing:-0.5px">
        ConprospecciónOS
      </div>
      <div style="color:#FFD700;font-size:14px;font-weight:500;margin-top:2px">
        Plataforma operativa de prospección comercial
      </div>
    </div>
  </div>
  <div style="color:#d4d4d2;font-size:14px;max-width:640px;line-height:1.6;margin-top:8px">
    Sistema central para gestionar reuniones, validar resultados con clientes
    y coordinar el trabajo de los SDRs — todo conectado con las fuentes comerciales y Supabase.
  </div>
</div>
""", unsafe_allow_html=True)

# ── Módulos disponibles (internos, clicables) ──────────────────────────────────
st.markdown("### Módulos disponibles")
st.markdown("Haz clic en cualquier tarjeta para abrir su módulo.")
st.markdown("")

MODULOS = [
    {
        "nombre": "Client Setup OS",
        "desc": "Centro operativo interno para intake, ICP, segmentos, dominios, correos, warmup, BBDD, campañas, SDR y checklist de lanzamiento.",
        "tag": "beta", "tag_label": "Piloto",
        "page": "pages/16_Client_Setup_OS.py",
    },
    {
        "nombre": "Seguimiento Reuniones",
        "desc": "Vista en vivo de todas las reuniones del mes por cliente. Filtros por SDR, día y cliente. Incluye estado de validación.",
        "tag": "live", "tag_label": "En vivo",
        "page": "pages/1_Seguimiento_Reuniones.py",
    },
    {
        "nombre": "Project Management",
        "desc": "Tablero interno para asignar tareas del equipo, ordenar prioridades, fechas límite y avance semanal.",
        "tag": "beta", "tag_label": "Interno",
        "page": "pages/3_Work_and_Project_Management.py",
    },
    {
        "nombre": "Comercial",
        "desc": "Mini CRM interno para tus reuniones comerciales de Conprospección: oportunidades, presentación, propuestas y seguimiento.",
        "tag": "beta", "tag_label": "MVP visual",
        "page": "pages/21_Comercial.py",
    },
    {
        "nombre": "Portal Cliente",
        "desc": "Hub de cada cliente activo. Abre GBS o BambuTech y accede a todos sus paneles: reuniones, indicadores, Intelligence Insight, validación, playbook e incorporación.",
        "tag": "live", "tag_label": "En vivo",
        "page": "pages/2_Clientes.py",
    },
    {
        "nombre": "MVP Setup Cliente",
        "desc": "Plataforma que desde la segmentación integra bases y fuentes, extrae contexto para generar mensajes personalizados, enruta contactos (llamadas y correo) a su plataforma y produce el reporte. Incluye el pipeline de setup: ICP y Apollo, firma, mensajería y brief. App independiente (puerto 8501).",
        "tag": "soon", "tag_label": "En desarrollo",
        "page": None,
    },
]

cols = st.columns(3)
for i, m in enumerate(MODULOS):
    tag_cls = f"tag-{m['tag']}"
    card_html = f"""
        <div class="module-card{'' if m['page'] else ' is-soon'}">
          <h3>{m['nombre']}</h3>
          <p>{m['desc']}</p>
          <span class="tag {tag_cls}">{m['tag_label']}</span>
        </div>
    """
    with cols[i % 3]:
        if m["page"]:
            with st.container(key=f"modcard{i}"):
                st.markdown(card_html, unsafe_allow_html=True)
                if st.button(m["nombre"], key=f"modbtn{i}", use_container_width=True):
                    st.switch_page(m["page"])
        else:
            st.markdown(f'<div style="margin-bottom:16px">{card_html}</div>',
                        unsafe_allow_html=True)

# ── Estado del sistema ────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### Estado del sistema")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown("""
    <div style="background:#EAF6EF;border:1px solid #BEE3CD;border-radius:10px;padding:14px 18px">
      <div style="font-size:11px;color:#15803D;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Supabase</div>
      <div style="font-size:18px;font-weight:700;color:#15803D;margin-top:4px">Conectado</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown("""
    <div style="background:#EAF6EF;border:1px solid #BEE3CD;border-radius:10px;padding:14px 18px">
      <div style="font-size:11px;color:#15803D;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Sincronización comercial</div>
      <div style="font-size:18px;font-weight:700;color:#15803D;margin-top:4px">08:00 / 20:00</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown("""
    <div style="background:#F4F4F2;border:1px solid #C9C9C4;border-radius:10px;padding:14px 18px">
      <div style="font-size:11px;color:#333333;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Clientes activos</div>
      <div style="font-size:18px;font-weight:700;color:#1A1A1A;margin-top:4px">5 subcuentas</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown("""
    <div style="background:#FFF7BF;border:1px solid #F0D875;border-radius:10px;padding:14px 18px">
      <div style="font-size:11px;color:#8A6D00;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Versión</div>
      <div style="font-size:18px;font-weight:700;color:#8A6D00;margin-top:4px">MVP v1.0</div>
    </div>""", unsafe_allow_html=True)

render_master_user_sidebar()

st.markdown("")
st.caption("ConprospecciónOS · Plataforma interna · Solo uso interno del equipo")
