"""GBS Logistics - Playbook SDR."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from portal_auth import render_client_nav, require_auth_client
from shared.cp_design import CP_GOLD, CP_GOLD_SOFT, CP_INK, CP_LINE, CP_MUTED

PLAYBOOK_PATH = ROOT / "CLIENTES" / "GBS_LOGISTICS" / "06_PLAYBOOK_SDR" / "brief_playbook_para_codex.md"


st.set_page_config(page_title="GBS Logistics - Playbook SDR", layout="wide", page_icon="")
if not require_auth_client("gbs"):
    st.stop()

render_client_nav("13_GBS_Playbook_SDR", "gbs")

st.markdown(
    f"""
<style>
.block-container{{max-width:1180px;padding-top:1rem!important}}
.gbs-card{{background:#fff;border:1px solid {CP_LINE};border-radius:8px;padding:18px 20px;margin-bottom:14px}}
.gbs-card p{{color:{CP_MUTED};font-size:13px;line-height:1.55}}
</style>
<div class="gbs-card" style="border-left:5px solid {CP_GOLD};background:{CP_GOLD_SOFT}">
  <h2 style="margin:0 0 6px;color:{CP_INK};font-size:22px">Playbook SDR</h2>
  <p style="margin:0">Material operativo disponible en la carpeta oficial del cliente.</p>
</div>
    """,
    unsafe_allow_html=True,
)

if PLAYBOOK_PATH.exists():
    st.markdown(PLAYBOOK_PATH.read_text(encoding="utf-8", errors="replace"))
else:
    st.info("Playbook pendiente de cargar en la carpeta oficial de GBS.")
