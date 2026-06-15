"""SDRs — módulo en construcción."""
import sys
from pathlib import Path

DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DASHBOARD_DIR))

import streamlit as st
from master_auth import require_master_auth, render_master_user_sidebar

st.set_page_config(page_title="SDRs — ConprospecciónOS", layout="wide", page_icon="")
if not require_master_auth():
    st.stop()

st.markdown("""
<div style="background:linear-gradient(135deg,#1e1e2e 0%,#2d1f5e 100%);
            padding:32px 40px;border-radius:16px;margin-bottom:32px;">
  <div style="display:flex;align-items:center;gap:14px">
    <div style="background:#6d28d9;border-radius:10px;padding:10px 14px;font-size:24px;line-height:1"></div>
    <div>
      <div style="color:white;font-size:26px;font-weight:800">SDRs</div>
      <div style="color:#a78bfa;font-size:13px;margin-top:3px">
        Métricas y gestión del equipo de prospección
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown(
    '<div style="text-align:center;padding:80px 20px">'
    '<div style="font-size:64px;margin-bottom:20px"></div>'
    '<div style="font-size:24px;font-weight:800;color:#1e293b;margin-bottom:10px">Próximamente</div>'
    '<div style="font-size:15px;color:#64748b;max-width:520px;margin:0 auto">'
    'Estamos preparando el módulo de SDRs con métricas individuales, '
    'ranking de rendimiento, historial de actividad y comparativas por cliente.<br><br>'
    'SDRs activos: Florencia Ravizza, Mariana Figueroa, Mariela Tello, '
    'Yanina, Zoe Olmedo, Eugenia Marañón, Luciana Acuña.'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)
render_master_user_sidebar()
