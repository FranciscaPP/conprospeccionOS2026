"""Hub interno de clientes — acceso al portal y datos de cada cliente."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

import requests
import streamlit as st
from portal_auth import img_b64
from master_auth import require_master_auth, render_master_user_sidebar
from shared.config import supabase_url, supabase_key
from shared.planes import plan_de, invalidar_cache

st.set_page_config(page_title="Clientes — ConprospecciónOS", layout="wide", page_icon="")
if not require_master_auth():
    st.stop()

_SB_URL, _SB_KEY = supabase_url(), supabase_key()


def _set_tier(slug: str, tier: str) -> None:
    requests.patch(
        f"{_SB_URL}/rest/v1/clientes?slug=eq.{slug}", json={"tier": tier},
        headers={"apikey": _SB_KEY, "Authorization": f"Bearer {_SB_KEY}",
                 "Content-Type": "application/json", "Prefer": "return=minimal"}, timeout=10)
    invalidar_cache()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(135deg,#1e1e2e 0%,#2d1f5e 100%);
            padding:32px 40px;border-radius:16px;margin-bottom:32px;">
  <div style="display:flex;align-items:center;gap:14px">
    <div style="background:#6d28d9;border-radius:10px;padding:10px 14px;font-size:24px;line-height:1"></div>
    <div>
      <div style="color:white;font-size:26px;font-weight:800">Clientes</div>
      <div style="color:#a78bfa;font-size:13px;margin-top:3px">
        Acceso al portal y datos de cada cliente activo
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Configuración de clientes ─────────────────────────────────────────────────
CLIENTES = [
    {
        "slug": "tiresias",
        "nombre": "Tiresias",
        "logo": "tiresias_logo.png",
        "color": "#1e40af",
        "bg": "#eff6ff",
        "border": "#bfdbfe",
        "pages": [
            ("Indicadores", "pages/3_Tiresias.py"),
            ("Validación Reuniones", "pages/4_Tiresias_Validacion_Reuniones.py"),
            ("Playbook SDR", "pages/5_Tiresias_Playbook_SDR.py"),
        ],
    },
    {
        "slug": "clickie",
        "nombre": "Clickie",
        "logo": "clickie_logo.png",
        "color": "#6d28d9",
        "bg": "#f5f3ff",
        "border": "#ddd6fe",
        "pages": [
            ("Indicadores", "pages/6_Clickie.py"),
            ("Validación Reuniones", "pages/7_Clickie_Validacion_Reuniones.py"),
            ("Playbook SDR", "pages/8_Clickie_Playbook_SDR.py"),
        ],
    },
    {
        "slug": "gbs",
        "nombre": "GBS Logistics",
        "logo": "gbs_logo.png",
        "color": "#1a56db",
        "bg": "#eff6ff",
        "border": "#bfdbfe",
        "pages": [
            ("Indicadores", "pages/11_GBS.py"),
            ("Validación Reuniones", "pages/12_GBS_Validacion_Reuniones.py"),
            ("Playbook SDR", "pages/13_GBS_Playbook_SDR.py"),
            ("Onboarding", "pages/14_GBS_Onboarding.py"),
        ],
    },
]

# ── Tarjetas de cliente ───────────────────────────────────────────────────────
for cliente in CLIENTES:
    slug = cliente["slug"]
    nombre = cliente["nombre"]
    color = cliente["color"]
    bg = cliente["bg"]
    border = cliente["border"]

    logo_html = img_b64(cliente["logo"], 52) or (
        f'<div style="background:{color};color:#fff;padding:10px 20px;'
        f'border-radius:10px;font-size:20px;font-weight:800;letter-spacing:1px">'
        f'{nombre.upper()}</div>'
    )

    st.markdown(
        f'<div style="background:{bg};border:1px solid {border};border-radius:16px;'
        f'border-top:5px solid {color};padding:24px 28px;margin-bottom:20px;'
        f'box-shadow:0 2px 8px rgba(0,0,0,.05)">'
        f'<div style="display:flex;align-items:center;gap:16px;margin-bottom:20px">'
        f'{logo_html}'
        f'<div style="font-size:20px;font-weight:800;color:#1e293b">{nombre}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(len(cliente["pages"]))
    for i, (label, page_path) in enumerate(cliente["pages"]):
        with cols[i]:
            if st.button(label, use_container_width=True, key=f"btn_{slug}_{i}",
                         type="primary" if i == 1 else "secondary"):
                st.switch_page(page_path)

    # Interruptor de plan: habilita/deshabilita el dashboard premium (Intelligence Insight).
    actual = plan_de(slug)
    tc1, tc2 = st.columns([2, 6])
    with tc1:
        nuevo = st.selectbox(
            "Plan del cliente", ["base", "premium"],
            index=1 if actual == "premium" else 0, key=f"tier_{slug}",
            help="premium habilita el dashboard Intelligence Insight en vivo para este cliente.")
    if nuevo != actual:
        _set_tier(slug, nuevo)
        st.toast(f"{nombre}: plan «{nuevo}» guardado")
        st.rerun()
    with tc2:
        estado = ("Dashboard Intelligence Insight HABILITADO para el cliente"
                  if nuevo == "premium" else
                  "El cliente ve Validación + Reporte Mensual (Intelligence Insight oculto)")
        st.markdown(
            f'<div style="font-size:12px;color:#64748b;padding-top:34px">{estado}</div>',
            unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

render_master_user_sidebar()

st.markdown("---")
st.caption("Los portales de cliente requieren credenciales de acceso del cliente.")
