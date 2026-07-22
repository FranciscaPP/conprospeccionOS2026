import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from master_auth import require_master_auth, render_master_user_sidebar

st.set_page_config(
    page_title="ConprospeccionOS",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

if not require_master_auth():
    st.stop()

# ── CSS global ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stSidebar"] { background: #1e1e2e !important; }
  [data-testid="stSidebar"] * { color: #e2e8f0 !important; }
  [data-testid="stSidebarNav"] a {
    border-radius: 8px;
    padding: 7px 12px;
    font-weight: 700 !important;
    font-size: 13.5px !important;
    letter-spacing: 0.1px;
  }
  [data-testid="stSidebarNav"] a:hover { background: rgba(255,255,255,0.10) !important; }
  [data-testid="stSidebarNav"] a[aria-current="page"] {
    background: rgba(109,40,217,0.35) !important;
    border-left: 3px solid #a78bfa;
  }
  [data-testid="stSidebarNav"] span { font-weight: 700 !important; }
  .module-card {
    background: white;
    border-radius: 14px;
    padding: 24px 28px;
    border-left: 5px solid #6d28d9;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    margin-bottom: 4px;
    transition: box-shadow .2s;
  }
  .module-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.13); }
  .module-card h3 { margin: 0 0 6px; font-size: 17px; color: #1e1e2e; }
  .module-card p { margin: 0; font-size: 13px; color: #64748b; }
  .tag {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    margin-top: 10px;
  }
  .tag-live { background: #dcfce7; color: #166534; }
  .tag-soon { background: #fef9c3; color: #854d0e; }
  .tag-beta { background: #dbeafe; color: #1e40af; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(135deg,#1e1e2e 0%,#2d1f5e 100%);
            padding:40px 48px;border-radius:16px;margin-bottom:32px;">
  <div style="display:flex;align-items:center;gap:16px;margin-bottom:12px">
    <div style="background:#6d28d9;border-radius:12px;padding:10px 16px;
                font-size:28px;line-height:1"></div>
    <div>
      <div style="color:white;font-size:30px;font-weight:800;letter-spacing:-0.5px">
        ConprospecciónOS
      </div>
      <div style="color:#a78bfa;font-size:14px;font-weight:500;margin-top:2px">
        Plataforma operativa de prospección comercial
      </div>
    </div>
  </div>
  <div style="color:#cbd5e1;font-size:14px;max-width:640px;line-height:1.6;margin-top:8px">
    Sistema central para gestionar reuniones, validar resultados con clientes
    y coordinar el trabajo de los SDRs — todo conectado con las fuentes comerciales y Supabase.
  </div>
</div>
""", unsafe_allow_html=True)

# ── Módulos disponibles ───────────────────────────────────────────────────────
st.markdown("### Módulos disponibles")
st.markdown("Selecciona un módulo en el menú de la izquierda o explóralos aquí:")
st.markdown("")

MODULOS = [
    {
        "icon": "",
        "nombre": "Client Setup OS",
        "desc": "Centro operativo interno para intake, ICP, segmentos, dominios, correos, warmup, BBDD, campañas, SDR y checklist de lanzamiento.",
        "tag": "beta", "tag_label": "GBS piloto",
        "color": "#6d28d9",
    },
    {
        "icon": "",
        "nombre": "BBDD Maestras",
        "desc": "Pool único de prospectos (Apollo · Snov · GHL) deduplicado por correo. Reutiliza contactos según el ICP de cada cliente: correo verificado a Snov, con teléfono a GHL.",
        "tag": "beta", "tag_label": "Prospección",
        "color": "#6d28d9",
    },
    {
        "icon": "",
        "nombre": "Seguimiento Reuniones",
        "desc": "Vista en vivo de todas las reuniones del mes por cliente. Filtros por SDR, día y cliente. Incluye estado de validación.",
        "tag": "live", "tag_label": "En vivo",
        "color": "#6d28d9",
    },
    {
        "icon": "",
        "nombre": "Work and Project Management",
        "desc": "Tablero interno para asignar tareas a Yanina o Francisca, ordenar prioridades, fechas limite y avance semanal.",
        "tag": "beta", "tag_label": "Interno",
        "color": "#6d28d9",
    },
    {
        "icon": "",
        "nombre": "Portal Cliente",
        "desc": "Cada cliente revisa sus reuniones y las marca como Válida, No válida o Reagendar. El cambio se sincroniza automáticamente con el sistema comercial.",
        "tag": "live", "tag_label": "En vivo",
        "color": "#0e7490",
    },
    {
        "icon": "",
        "nombre": "MVP Setup Cliente",
        "desc": "Onboarding operativo de nuevos clientes: crea la estructura de carpetas, archivos, firma de email y estado del proyecto.",
        "tag": "beta", "tag_label": "Beta",
        "color": "#b45309",
    },
    {
        "icon": "",
        "nombre": "Dashboard Ejecutivo",
        "desc": "KPIs globales: reuniones totales, tasa de validación, rendimiento por SDR y comparativa entre clientes.",
        "tag": "soon", "tag_label": "Próximamente",
        "color": "#166534",
    },
    {
        "icon": "",
        "nombre": "Pipeline comercial",
        "desc": "Visualización del estado de oportunidades por cliente, directamente desde Supabase.",
        "tag": "soon", "tag_label": "Próximamente",
        "color": "#9a3412",
    },
    {
        "icon": "",
        "nombre": "Reportes Clientes",
        "desc": "Genera reportes mensuales automáticos con el resumen de actividad para enviar a cada cliente.",
        "tag": "soon", "tag_label": "Próximamente",
        "color": "#5b21b6",
    },
]

cols = st.columns(3)
for i, m in enumerate(MODULOS):
    tag_cls = f"tag-{m['tag']}"
    with cols[i % 3]:
        st.markdown(f"""
        <div class="module-card" style="border-left-color:{m['color']}">
          <div style="font-size:28px;margin-bottom:8px">{m['icon']}</div>
          <h3>{m['nombre']}</h3>
          <p>{m['desc']}</p>
          <span class="tag {tag_cls}">{m['tag_label']}</span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("")

st.markdown("---")
st.markdown("### Accesos rápidos por cliente")
st.markdown("BambuTech Services")

bt_cols = st.columns(5)
with bt_cols[0]:
    if st.button("Portal BambuTech", use_container_width=True, type="primary", key="home_bambu_portal"):
        st.switch_page("pages/15_BambuTech.py")
with bt_cols[1]:
    if st.button("Onboarding", use_container_width=True, key="home_bambu_onboarding"):
        st.switch_page("pages/17_BambuTech_Onboarding.py")
with bt_cols[2]:
    if st.button("Validación reuniones", use_container_width=True, key="home_bambu_validacion"):
        st.switch_page("pages/18_BambuTech_Validacion_Reuniones.py")
with bt_cols[3]:
    if st.button("Intelligence Insight", use_container_width=True, key="home_bambu_intelligence"):
        st.switch_page("pages/19_BambuTech_Intelligence_Insight.py")
with bt_cols[4]:
    if st.button("Playbook SDR", use_container_width=True, key="home_bambu_playbook"):
        st.switch_page("pages/20_BambuTech_Playbook_SDR.py")

# ── Estado del sistema ────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### Estado del sistema")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown("""
    <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:10px;padding:14px 18px">
      <div style="font-size:11px;color:#166534;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Supabase</div>
      <div style="font-size:18px;font-weight:700;color:#166534;margin-top:4px">Conectado</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown("""
    <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:10px;padding:14px 18px">
      <div style="font-size:11px;color:#166534;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Sincronización comercial</div>
      <div style="font-size:18px;font-weight:700;color:#166534;margin-top:4px">08:00 / 20:00</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown("""
    <div style="background:#eff6ff;border:1px solid #93c5fd;border-radius:10px;padding:14px 18px">
      <div style="font-size:11px;color:#1e40af;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Clientes activos</div>
      <div style="font-size:18px;font-weight:700;color:#1e40af;margin-top:4px">5 subcuentas</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown("""
    <div style="background:#faf5ff;border:1px solid #c4b5fd;border-radius:10px;padding:14px 18px">
      <div style="font-size:11px;color:#6d28d9;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Versión</div>
      <div style="font-size:18px;font-weight:700;color:#6d28d9;margin-top:4px">MVP v1.0</div>
    </div>""", unsafe_allow_html=True)

render_master_user_sidebar()

st.markdown("")
st.caption("ConprospecciónOS · Plataforma interna · Solo uso interno del equipo")
