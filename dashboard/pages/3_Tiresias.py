"""Portal cliente Tiresias — Indicadores (en construcción)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

import streamlit as st
from portal_auth import require_auth_tiresias, render_client_nav, img_b64

st.set_page_config(page_title="Tiresias — Indicadores", layout="wide", page_icon="")

if not require_auth_tiresias():
    st.stop()

render_client_nav("3_Tiresias", "tiresias")

# ── Header ───────────────────────────────────────────────────────────────────
t = img_b64("tiresias_logo.png", 56) or (
    '<div style="background:#1e3a5f;color:#fff;padding:10px 22px;border-radius:8px;'
    'font-size:19px;font-weight:700;letter-spacing:1.5px">tiresias</div>')
c = img_b64("conprospeccion_logo.png", 44) or (
    '<div style="background:#111827;padding:8px 18px;border-radius:8px;'
    'font-size:13px;font-weight:700;color:#fbbf24">Conprospección</div>')

st.markdown(
    f'<div style="display:flex;align-items:center;justify-content:space-between;'
    f'background:linear-gradient(135deg,#f8fafc,#eef2ff);padding:18px 28px;'
    f'border-radius:14px;border:1px solid #c7d2fe;margin-bottom:28px;'
    f'box-shadow:0 2px 8px rgba(0,0,0,.06)">'
    f'<div style="display:flex;align-items:center;gap:18px">{t}'
    f'<div><div style="font-size:22px;font-weight:800;color:#1e293b">Indicadores</div>'
    f'<div style="font-size:13px;color:#64748b;margin-top:3px">'
    f'Resumen ejecutivo de la campaña de prospección</div></div></div>{c}</div>',
    unsafe_allow_html=True,
)

# ── En construcción ───────────────────────────────────────────────────────────
st.markdown(
    '<div style="text-align:center;padding:80px 20px">'
    '<div style="font-size:64px;margin-bottom:20px"></div>'
    '<div style="font-size:24px;font-weight:800;color:#1e293b;margin-bottom:10px">'
    'Próximamente</div>'
    '<div style="font-size:15px;color:#64748b;max-width:480px;margin:0 auto">'
    'Estamos preparando el dashboard de indicadores con métricas de reuniones, '
    'industrias, cargos e insights de campaña.<br><br>'
    'Por ahora la validación de reuniones está disponible en el menú lateral.'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)
