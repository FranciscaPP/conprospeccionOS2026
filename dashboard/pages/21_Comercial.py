"""Modulo Comercial interno de ConprospeccionOS.

Implementacion visual/funcional inicial con datos demo locales. Las
integraciones reales (Supabase, IA, Gmail, Fathom/Granola y PDF) quedan
separadas para fases posteriores.
"""
from __future__ import annotations

import base64
import copy
import sys
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from comercial_components import (  # noqa: E402
    band,
    badge,
    field_grid,
    hero,
    inject_commercial_css,
    kpi_grid,
    panel,
    timeline,
)
from master_auth import render_master_user_sidebar, require_master_auth  # noqa: E402
from shared.comercial import (  # noqa: E402
    COMMERCIAL_STATES,
    active_proposal,
    calculate_price,
    money,
    opportunity_amount_label,
    scenario_prices,
)
from shared.comercial_demo_data import (  # noqa: E402
    BRIEFING_DEMO,
    DEMO_DATA_VERSION,
    DEMO_OPPORTUNITIES,
    DEMO_SETTINGS,
    STANDARD_PRESENTATION,
)


st.set_page_config(page_title="Comercial - ConprospeccionOS", layout="wide", page_icon="")
if not require_master_auth():
    st.stop()


STAGE_DEFINITIONS = [
    ("Agenda y preparacion", "#A66A00", ["Reunion agendada", "Preparacion pendiente", "Preparacion lista"]),
    ("Reunion y analisis", "#2563EB", ["Reunion realizada", "Diagnostico procesado"]),
    (
        "Propuesta y seguimiento",
        "#6D28D9",
        ["Investigacion de mercado", "Propuesta en preparacion", "Propuesta enviada", "En seguimiento"],
    ),
    ("Cierre", "#15803D", ["Aceptada", "Perdida", "Pausada"]),
]

TAB_LABELS = [
    "Resumen",
    "Preparacion",
    "Reunion",
    "Investigacion",
    "Propuesta",
    "Correos y seguimiento",
    "Historial",
]


def _inject_layout_css(presentation_mode: bool = False) -> None:
    inject_commercial_css()
    sidebar_css = """
    <style>
    [data-testid="stSidebar"] {
      background:#1f1f1f !important;
      border-right:1px solid #111 !important;
    }
    [data-testid="stSidebar"] * { color:#F4F4F2; }
    [data-testid="stSidebar"] button {
      border-radius:8px !important;
      font-weight:800 !important;
    }
    .block-container { max-width:1450px; padding-top:1rem !important; }
    .cp-work-area {
      display:grid;
      grid-template-columns:minmax(0,1fr) 430px;
      gap:16px;
      align-items:start;
    }
    .cp-work-area.panel-closed { grid-template-columns:1fr; }
    .cp-work-board {
      display:grid;
      grid-template-columns:repeat(4,minmax(0,1fr));
      gap:12px;
      align-items:start;
    }
    .cp-work-column {
      background:#FAFAF8;
      border:1px solid #C9C9C4;
      border-radius:10px;
      padding:10px;
      min-height:460px;
    }
    .cp-work-title {
      background:#fff;
      border:1px solid #C9C9C4;
      border-left:4px solid var(--stage-color,#FFD700);
      border-radius:8px;
      color:#1A1A1A;
      font-family:Saira,"IBM Plex Sans",sans-serif;
      font-size:14px;
      font-weight:800;
      margin:0 0 10px;
      padding:10px 12px;
    }
    .cp-task-card {
      background:#fff;
      border:1px solid #EDECEA;
      border-radius:8px;
      padding:11px 12px 10px;
      margin:8px 0 10px;
      transition:border-color .12s ease, background .12s ease;
    }
    .cp-task-card.selected {
      border-color:#FFD700;
      box-shadow:inset 3px 0 0 #FFD700;
      background:#FFFDF0;
    }
    .cp-task-head {
      display:flex;
      align-items:flex-start;
      justify-content:space-between;
      gap:8px;
      margin-bottom:8px;
    }
    .cp-chip-row { display:flex; flex-wrap:wrap; gap:6px; min-width:0; }
    .cp-chip {
      border:1px solid;
      border-radius:6px;
      display:inline-flex;
      font-size:11px;
      font-weight:800;
      line-height:1;
      padding:5px 8px;
    }
    .cp-chip.blue { color:#2563EB; background:#EAF1FE; border-color:#BFD2FB; }
    .cp-chip.green { color:#15803D; background:#EAF6EF; border-color:#BFE6CC; }
    .cp-chip.orange { color:#A66A00; background:#FFF3D8; border-color:#F0D28D; }
    .cp-chip.purple { color:#6D28D9; background:#F1EDFF; border-color:#CDBDFF; }
    .cp-chip.red { color:#C92B2B; background:#FDECEA; border-color:#F3B7B3; }
    .cp-owner {
      align-items:center;
      border:1px solid #F0D28D;
      background:#FFF3D8;
      border-radius:8px;
      color:#A66A00;
      display:flex;
      gap:6px;
      flex-shrink:0;
      font-size:12px;
      font-weight:800;
      min-height:30px;
      padding:4px 7px 4px 5px;
    }
    .cp-owner span {
      background:#FFFFFFAA;
      border-radius:6px;
      display:grid;
      font-family:"IBM Plex Mono",monospace;
      font-size:12px;
      height:21px;
      place-items:center;
      width:21px;
    }
    .cp-task-title {
      color:#1A1A1A;
      font-size:14px;
      font-weight:800;
      line-height:1.25;
      margin-bottom:7px;
    }
    .cp-task-desc {
      color:#6B6B6B;
      font-size:12px;
      line-height:1.35;
      margin-bottom:8px;
    }
    .cp-task-meta {
      color:#6B6B6B;
      display:grid;
      gap:4px;
      font-size:11px;
    }
    .cp-task-meta b { color:#1A1A1A; }
    .cp-drawer {
      background:#fff;
      border:1px solid #C9C9C4;
      border-radius:12px;
      box-shadow:0 18px 40px rgba(0,0,0,.13);
      overflow:hidden;
      position:sticky;
      top:56px;
    }
    .cp-drawer-top {
      background:#fff;
      border-bottom:1px solid #EDECEA;
      padding:14px 16px;
    }
    .cp-drawer-title {
      color:#1A1A1A;
      font-family:Saira,"IBM Plex Sans",sans-serif;
      font-size:20px;
      font-weight:800;
      line-height:1.1;
    }
    .cp-drawer-sub { color:#6B6B6B; font-size:12px; margin-top:4px; }
    .cp-mini-grid {
      display:grid;
      grid-template-columns:1fr 1fr;
      gap:8px;
      margin-top:12px;
    }
    .cp-mini {
      border:1px solid #EDECEA;
      border-radius:8px;
      background:#FAFAF8;
      padding:9px;
    }
    .cp-mini span {
      color:#6B6B6B;
      display:block;
      font-size:9px;
      font-weight:900;
      text-transform:uppercase;
    }
    .cp-mini b {
      color:#1A1A1A;
      display:block;
      font-size:12px;
      margin-top:4px;
      overflow-wrap:anywhere;
    }
    .cp-drawer-body {
      max-height:760px;
      overflow:auto;
      padding:14px 16px 16px;
    }
    .cp-inline-tabs {
      display:flex;
      gap:6px;
      overflow:auto;
      padding:10px 12px;
      border-bottom:1px solid #EDECEA;
      background:#fff;
    }
    .cp-section-grid {
      display:grid;
      grid-template-columns:repeat(2,minmax(0,1fr));
      gap:10px;
    }
    .cp-proposal-table {
      width:100%;
      border-collapse:separate;
      border-spacing:0 8px;
      font-size:12px;
    }
    .cp-proposal-table th {
      color:#6B6B6B;
      font-size:10px;
      font-weight:900;
      text-align:left;
      text-transform:uppercase;
      padding:0 10px 4px;
    }
    .cp-proposal-table td {
      background:#fff;
      border-top:1px solid #EDECEA;
      border-bottom:1px solid #EDECEA;
      padding:12px 10px;
      vertical-align:middle;
    }
    .cp-proposal-table td:first-child {
      border-left:1px solid #EDECEA;
      border-radius:8px 0 0 8px;
      font-weight:800;
    }
    .cp-proposal-table td:last-child {
      border-right:1px solid #EDECEA;
      border-radius:0 8px 8px 0;
    }
    .cp-presentation-shell {
      background:#FAFAF8;
      color:#1A1A1A;
      border-radius:0;
      min-height:calc(100vh - 2rem);
      padding:0 0 28px;
    }
    .cp-presentation-brand {
      align-items:center;
      background:#FFFFFF;
      border:1px solid #EDECEA;
      border-radius:12px;
      display:flex;
      justify-content:space-between;
      gap:16px;
      margin-bottom:20px;
      padding:14px 18px;
    }
    .cp-presentation-brand img {
      display:block;
      max-height:42px;
      object-fit:contain;
    }
    .cp-presentation-count {
      color:#6B6B6B;
      font-size:12px;
      font-weight:800;
      text-transform:uppercase;
    }
    .cp-presentation-frame {
      background:#FFFFFF;
      border:1px solid #EDECEA;
      border-radius:12px;
      box-shadow:0 16px 40px rgba(0,0,0,.08);
      min-height:620px;
      padding:30px 34px;
    }
    .cp-presentation-top,
    .cp-presentation-bottom {
      align-items:center;
      display:flex;
      justify-content:space-between;
    }
    .cp-presentation-top { color:#EDECEA; font-size:13px; }
    .cp-presentation-main {
      align-items:center;
      display:grid;
      flex:1;
      gap:26px;
      grid-template-columns:1fr 1fr;
    }
    .cp-presentation-main h1 {
      color:#1A1A1A;
      font-family:Saira,"IBM Plex Sans",sans-serif;
      font-size:42px;
      line-height:1.05;
      margin:0 0 16px;
    }
    .cp-presentation-main p {
      color:#3A3A37;
      font-size:17px;
      line-height:1.55;
    }
    .cp-white-card {
      background:#FAFAF8;
      border:1px solid #EDECEA;
      border-radius:10px;
      color:#1A1A1A;
      padding:18px;
    }
    .cp-white-card h3 {
      color:#1A1A1A;
      font-family:Saira,"IBM Plex Sans",sans-serif;
      font-size:21px;
      line-height:1.15;
      margin-top:0;
    }
    .cp-white-card p {
      color:#3A3A37;
      font-size:13px;
      line-height:1.45;
      margin:0 0 11px;
    }
    .cp-present-chip {
      background:#FFF7BF;
      border:1px solid #F0D28D;
      border-radius:999px;
      color:#1A1A1A;
      display:inline-flex;
      font-size:11px;
      font-weight:900;
      margin-bottom:12px;
      padding:5px 10px;
    }
    .cp-present-slide {
      background:#FFFFFF;
      border:1px solid #EDECEA;
      border-radius:12px;
      box-shadow:0 16px 40px rgba(0,0,0,.08);
      display:grid;
      gap:28px;
      grid-template-columns:minmax(0,.95fr) minmax(0,1.05fr);
      margin:12px 0 22px;
      min-height:610px;
      padding:32px 34px;
    }
    .cp-present-copy h1 {
      color:#1A1A1A;
      font-family:Saira,"IBM Plex Sans",sans-serif;
      font-size:42px;
      line-height:1.05;
      margin:0 0 18px;
    }
    .cp-present-copy p {
      color:#3A3A37;
      font-size:17px;
      line-height:1.55;
      margin:0;
    }
    .cp-present-detail {
      background:#FAFAF8;
      border:1px solid #EDECEA;
      border-radius:10px;
      padding:22px;
    }
    .cp-present-detail h3 {
      color:#1A1A1A;
      font-family:Saira,"IBM Plex Sans",sans-serif;
      font-size:22px;
      line-height:1.15;
      margin:0 0 16px;
    }
    .cp-present-detail p {
      color:#3A3A37;
      font-size:13px;
      line-height:1.45;
      margin:0 0 12px;
    }
    .cp-present-detail strong { color:#1A1A1A; }
    .cp-config-grid {
      display:grid;
      grid-template-columns:250px minmax(0,1fr);
      gap:14px;
    }
    .cp-config-menu {
      background:#fff;
      border:1px solid #EDECEA;
      border-radius:8px;
      padding:10px;
    }
    .cp-config-menu div {
      border-radius:7px;
      color:#1A1A1A;
      font-weight:800;
      padding:11px;
    }
    .cp-config-menu .active {
      background:#FFF7BF;
      border:1px solid #F0D28D;
    }
    @media(max-width:1180px) {
      .cp-work-area { grid-template-columns:1fr; }
      .cp-work-board, .cp-grid, .cp-module-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
      .cp-drawer { position:relative; top:0; }
      .cp-presentation-main, .cp-config-grid, .cp-section-grid, .cp-present-slide { grid-template-columns:1fr; }
    }
    @media(max-width:720px) {
      .block-container { padding-left:1rem !important; padding-right:1rem !important; }
      .cp-work-board, .cp-grid, .cp-module-grid, .cp-mini-grid { grid-template-columns:1fr; }
      .cp-presentation-shell { min-height:auto; padding:22px; }
      .cp-presentation-main h1 { font-size:32px; }
      .cp-presentation-main p { font-size:15px; }
    }
    </style>
    """
    presentation_css = """
    <style>
    [data-testid="stSidebar"], [data-testid="collapsedControl"], [data-testid="stHeader"], [data-testid="stToolbar"] {
      display:none !important;
    }
    .block-container { max-width:100vw !important; padding:1rem !important; }
    .stApp { background:#FAFAF8 !important; }
    </style>
    """
    st.markdown(sidebar_css + (presentation_css if presentation_mode else ""), unsafe_allow_html=True)


def _init_state() -> None:
    if (
        "commercial_opportunities" not in st.session_state
        or st.session_state.get("commercial_demo_data_version") != DEMO_DATA_VERSION
    ):
        st.session_state["commercial_opportunities"] = copy.deepcopy(DEMO_OPPORTUNITIES)
        st.session_state["commercial_selected_opp"] = DEMO_OPPORTUNITIES[0]["id"]
        st.session_state["commercial_demo_data_version"] = DEMO_DATA_VERSION
    st.session_state.setdefault("commercial_view", "hub")
    st.session_state.setdefault("commercial_selected_opp", DEMO_OPPORTUNITIES[0]["id"])
    st.session_state.setdefault("commercial_panel_open", False)
    st.session_state.setdefault("commercial_tab", "Resumen")
    st.session_state.setdefault("commercial_tab_choice", st.session_state["commercial_tab"])
    st.session_state.setdefault("commercial_slide", 0)
    st.session_state.setdefault("commercial_prev_tab", "Resumen")
    st.session_state.setdefault("commercial_config_tab", "Enlaces")


def _opportunities() -> list[dict[str, Any]]:
    return st.session_state["commercial_opportunities"]


def _current_opp() -> dict[str, Any]:
    selected = st.session_state.get("commercial_selected_opp")
    return next((opp for opp in _opportunities() if opp["id"] == selected), _opportunities()[0])


def _set_view(view: str) -> None:
    st.session_state["commercial_view"] = view
    if view != "opportunities":
        st.session_state["commercial_panel_open"] = False
    st.rerun()


def _open_panel(opp_id: str, tab: str = "Resumen", view: str = "opportunities") -> None:
    st.session_state["commercial_selected_opp"] = opp_id
    st.session_state["commercial_tab"] = tab
    st.session_state["commercial_tab_choice"] = tab
    st.session_state["commercial_panel_open"] = True
    st.session_state["commercial_view"] = view
    st.rerun()


def _close_panel() -> None:
    st.session_state["commercial_panel_open"] = False
    st.rerun()


def _start_presentation(opp_id: str) -> None:
    st.session_state["commercial_selected_opp"] = opp_id
    st.session_state["commercial_prev_tab"] = st.session_state.get("commercial_tab", "Resumen")
    st.session_state["commercial_slide"] = 0
    st.session_state["commercial_view"] = "presentation"
    st.rerun()


def _flatten_proposals() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for opp in _opportunities():
        for proposal in opp.get("proposals", []):
            rows.append(
                {
                    **proposal,
                    "company": opp["company"],
                    "contact": opp["contact"],
                    "owner": opp["owner"],
                    "next_followup": opp["next_followup"],
                    "opportunity_id": opp["id"],
                }
            )
    return rows


def _stage_for_status(status: str) -> str:
    for stage, _color, statuses in STAGE_DEFINITIONS:
        if status in statuses:
            return stage
    return STAGE_DEFINITIONS[0][0]


def _stage_status(stage: str) -> str:
    return next((statuses[0] for title, _color, statuses in STAGE_DEFINITIONS if title == stage), COMMERCIAL_STATES[0])


def _move_to_stage(opp_id: str, stage: str) -> None:
    for opp in _opportunities():
        if opp["id"] == opp_id:
            opp["status"] = _stage_status(stage)
            opp["history"].append(("2026-07-23 12:00", "manual", f"Etapa movida a {stage} en demo local"))
            break
    st.session_state["commercial_selected_opp"] = opp_id
    st.session_state["commercial_panel_open"] = True
    st.rerun()


def _proposal_amount(opp: dict[str, Any]) -> str:
    proposal = active_proposal(opp)
    if not proposal:
        return "Pendiente"
    return f'{money(proposal.get("monthly_amount"))} mensual'


def _logo_html() -> str:
    logo_path = DASHBOARD_DIR / "assets" / "conprospeccion_logo.png"
    if not logo_path.exists():
        return '<strong style="font-family:Saira,sans-serif">Conprospeccion</strong>'
    encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    return f'<img src="data:image/png;base64,{encoded}" alt="Conprospeccion">'


def _logo_data_uri() -> str:
    logo_path = DASHBOARD_DIR / "assets" / "conprospeccion_logo.png"
    if not logo_path.exists():
        return ""
    encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _chip(text: str, tone: str = "orange") -> str:
    return f'<span class="cp-chip {tone}">{text}</span>'


def _owner_badge(owner: str) -> str:
    initial = (owner or "F")[:1].upper()
    return f'<div class="cp-owner"><span>{initial}</span>{owner}</div>'


def _card_html(opp: dict[str, Any], selected: bool) -> str:
    css = " selected" if selected else ""
    score_tone = "blue" if int(opp.get("score") or 0) >= 75 else "orange"
    return f"""
    <div class="cp-task-card{css}">
      <div class="cp-task-head">
        <div class="cp-chip-row">
          {_chip(opp.get("industry", "Sin industria"), "green")}
          {_chip(opp.get("status", "Sin estado"), "orange")}
          {_chip(f"Score {opp.get('score', '-')}", score_tone)}
        </div>
        {_owner_badge(opp.get("owner", "Francisca"))}
      </div>
      <div class="cp-task-title">{opp["company"]}</div>
      <div class="cp-task-desc">{opp["contact"]} - {opp["role"]}</div>
      <div class="cp-task-meta">
        <span>Fecha reunion: <b>{opp.get("meeting_at") or "Pendiente"}</b></span>
        <span>Propuesta: <b>{_proposal_amount(opp)}</b></span>
        <span>Proximo paso: <b>{opp.get("next_followup") or "Pendiente"}</b></span>
      </div>
    </div>
    """


def _kpis() -> list[tuple[str, str]]:
    opportunities = _opportunities()
    return [
        ("Oportunidades activas", str(sum(1 for opp in opportunities if opp["status"] not in {"Aceptada", "Perdida"}))),
        ("Reuniones agendadas", str(sum(1 for opp in opportunities if opp["meeting_at"]))),
        ("Propuestas enviadas", str(sum(1 for opp in opportunities if opp.get("proposal_sent_at")))),
        ("Proximos seguimientos", str(sum(1 for opp in opportunities for f in opp.get("followups", []) if f[2] == "Pendiente"))),
    ]


def render_hub() -> None:
    hero("Comercial", "Oportunidades, propuestas y configuracion comercial interna.")
    band(
        "Punto de entrada interno para gestionar prospectos comerciales desde la primera reunion hasta propuesta, seguimiento, aceptacion o perdida."
    )
    st.markdown(
        """
<div class="cp-module-grid" style="grid-template-columns:repeat(3,minmax(0,1fr))">
  <div class="cp-module-card"><h3>Oportunidades</h3><p>Mini CRM interno para gestionar prospectos, reuniones, etapas comerciales, propuestas y proximos seguimientos.</p><span class="cp-module-pill">CRM interno</span></div>
  <div class="cp-module-card"><h3>Propuestas</h3><p>Vista general de propuestas, versiones, montos, vigencia, estado y seguimiento.</p><span class="cp-module-pill">Consolidado</span></div>
  <div class="cp-module-card"><h3>Configuracion Comercial</h3><p>Configuracion de costos, margenes, score, plantillas, enlaces y secuencias de seguimiento.</p><span class="cp-module-pill">Administracion</span></div>
</div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("ABRIR OPORTUNIDADES", type="primary", use_container_width=True):
            _set_view("opportunities")
    with c2:
        if st.button("ABRIR PROPUESTAS", use_container_width=True):
            _set_view("proposals")
    with c3:
        if st.button("ABRIR CONFIGURACION", use_container_width=True):
            _set_view("settings")


def render_opportunities() -> None:
    if st.button("← Volver a Comercial", use_container_width=False):
        _set_view("hub")
    left, right = st.columns([5, 1])
    with left:
        st.markdown("## Oportunidades comerciales")
        st.caption("Tablero por columnas. El detalle se trabaja en el panel derecho, sin abandonar el CRM.")
    with right:
        st.button("Nueva oportunidad", type="primary", use_container_width=True, disabled=True)
    kpi_grid(_kpis())
    with st.expander("Filtros", expanded=False):
        f1, f2, f3, f4 = st.columns(4)
        f1.text_input("Buscar", key="commercial_filter_search")
        f2.selectbox("Estado", ["Todos", *COMMERCIAL_STATES], key="commercial_filter_status")
        f3.selectbox("Responsable", ["Todos", *sorted({o["owner"] for o in _opportunities()})], key="commercial_filter_owner")
        f4.date_input("Fecha reunion", value=(), key="commercial_filter_dates")
    rows = _filtered_opportunities()
    panel_open = st.session_state.get("commercial_panel_open", False)
    if panel_open:
        board_col, panel_col = st.columns([1, 0.42])
        with board_col:
            render_board(rows)
        with panel_col:
            render_opportunity_panel(_current_opp())
    else:
        render_board(rows)


def _filtered_opportunities() -> list[dict[str, Any]]:
    query = st.session_state.get("commercial_filter_search", "").strip().lower()
    status = st.session_state.get("commercial_filter_status", "Todos")
    owner = st.session_state.get("commercial_filter_owner", "Todos")
    rows = []
    for opp in _opportunities():
        haystack = " ".join([opp["company"], opp["contact"], opp["role"], opp["email"]]).lower()
        if query and query not in haystack:
            continue
        if status != "Todos" and opp["status"] != status:
            continue
        if owner != "Todos" and opp["owner"] != owner:
            continue
        rows.append(opp)
    return rows


def render_board(rows: list[dict[str, Any]]) -> None:
    columns = st.columns(4)
    selected = st.session_state.get("commercial_selected_opp")
    for column, (stage, color, statuses) in zip(columns, STAGE_DEFINITIONS):
        stage_rows = [opp for opp in rows if opp["status"] in statuses]
        with column:
            st.markdown(
                f'<div class="cp-work-column"><div class="cp-work-title" style="--stage-color:{color}">{stage} · {len(stage_rows)}</div>',
                unsafe_allow_html=True,
            )
            if not stage_rows:
                st.info("Sin oportunidades en esta etapa.")
            for opp in stage_rows:
                st.markdown(_card_html(opp, opp["id"] == selected), unsafe_allow_html=True)
                a1, a2 = st.columns(2)
                with a1:
                    if st.button("Ver detalle", key=f"detail_{opp['id']}", use_container_width=True):
                        _open_panel(opp["id"], "Resumen", "opportunities")
                with a2:
                    if opp["status"] in {"Aceptada"}:
                        st.button("Convertir", key=f"convert_{opp['id']}", use_container_width=True, disabled=True)
                    elif opp.get("proposals"):
                        if st.button("Abrir propuesta", key=f"openprop_{opp['id']}", use_container_width=True):
                            _open_panel(opp["id"], "Propuesta", "opportunities")
                    else:
                        if st.button("Presentacion", key=f"present_{opp['id']}", use_container_width=True):
                            _start_presentation(opp["id"])
                current_stage = _stage_for_status(opp["status"])
                stage_choice = st.selectbox(
                    "Mover etapa",
                    [s[0] for s in STAGE_DEFINITIONS],
                    index=[s[0] for s in STAGE_DEFINITIONS].index(current_stage),
                    key=f"move_{opp['id']}",
                    label_visibility="collapsed",
                )
                if stage_choice != current_stage:
                    _move_to_stage(opp["id"], stage_choice)
            st.markdown("</div>", unsafe_allow_html=True)


def render_opportunity_panel(opp: dict[str, Any]) -> None:
    st.markdown('<aside class="cp-drawer">', unsafe_allow_html=True)
    close_col, _ = st.columns([1, 4])
    with close_col:
        if st.button("Cerrar", key="close_commercial_panel", use_container_width=True):
            _close_panel()
    st.markdown(
        f"""
<div class="cp-drawer-top">
  <div class="cp-drawer-title">{opp['company']}</div>
  <div class="cp-drawer-sub">{opp['contact']} - {opp['role']}</div>
  <div class="cp-mini-grid">
    <div class="cp-mini"><span>Fecha reunion</span><b>{opp.get('meeting_at') or 'Pendiente'}</b></div>
    <div class="cp-mini"><span>Etapa</span><b>{opp.get('status')}</b></div>
    <div class="cp-mini"><span>Score</span><b>{opp.get('score')} - {opp.get('score_level')}</b></div>
    <div class="cp-mini"><span>Propuesta vigente</span><b>{opportunity_amount_label(opp)}</b></div>
    <div class="cp-mini"><span>Responsable</span><b>{opp.get('owner')}</b></div>
    <div class="cp-mini"><span>Proximo paso</span><b>{opp.get('next_followup') or 'Pendiente'}</b></div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )
    requested_tab = st.session_state.pop("commercial_requested_tab", None)
    if requested_tab in TAB_LABELS:
        st.session_state["commercial_tab_choice"] = requested_tab

    current_choice = st.session_state.get("commercial_tab_choice", "Resumen")
    if current_choice not in TAB_LABELS:
        current_choice = "Resumen"
        st.session_state["commercial_tab_choice"] = current_choice

    selected_tab = st.radio(
        "Seccion de oportunidad",
        TAB_LABELS,
        index=TAB_LABELS.index(current_choice),
        key="commercial_tab_choice",
        horizontal=True,
        label_visibility="collapsed",
    )
    st.session_state["commercial_tab"] = selected_tab
    st.markdown('<div class="cp-drawer-body">', unsafe_allow_html=True)
    if selected_tab == "Resumen":
        render_tab_summary(opp)
    elif selected_tab == "Preparacion":
        render_tab_preparation(opp)
    elif selected_tab == "Reunion":
        render_tab_meeting(opp)
    elif selected_tab == "Investigacion":
        render_tab_research(opp)
    elif selected_tab == "Propuesta":
        render_tab_proposal(opp)
    elif selected_tab == "Correos y seguimiento":
        render_tab_email_followup(opp)
    else:
        render_tab_history(opp)
    st.markdown("</div></aside>", unsafe_allow_html=True)


def render_tab_summary(opp: dict[str, Any]) -> None:
    panel("Datos de la empresa", "Informacion base de la oportunidad comercial.")
    field_grid(
        [
            ("Empresa", opp["company"]),
            ("Industria", opp["industry"]),
            ("Pais", opp["country"]),
            ("Web", opp["website"]),
            ("LinkedIn empresa", opp["linkedin_company"]),
            ("Contacto", opp["contact"]),
            ("Cargo", opp["role"]),
            ("Correo", opp["email"]),
            ("Telefono", opp["phone"]),
            ("LinkedIn persona", opp["linkedin_person"]),
            ("Estado comercial", opp["status"]),
            ("Score", f'{opp["score"]} - {opp["score_level"]}'),
            ("Fecha reunion", opp["meeting_at"]),
            ("Propuesta vigente", opportunity_amount_label(opp)),
            ("Proximo paso", opp["next_followup"]),
        ]
    )
    a1, a2 = st.columns(2)
    with a1:
        if st.button("Iniciar presentacion", type="primary", use_container_width=True):
            _start_presentation(opp["id"])
        st.button("Abrir propuesta enviada", use_container_width=True, disabled=not bool(opp.get("proposals")))
    with a2:
        st.button("Abrir correo", use_container_width=True, disabled=not bool(opp.get("emails")))
        st.button("Programar seguimiento", use_container_width=True, disabled=True)


def render_tab_preparation(opp: dict[str, Any]) -> None:
    prep = opp["preparation"]
    field_grid(
        [
            ("Estado", prep["state"]),
            ("Generada", prep["generated_at"] or "Pendiente"),
            ("Campana origen", opp["campaign"]),
            ("Contexto", prep["source_context"]),
            ("Observaciones", opp["notes"]),
        ]
    )
    st.text_area("Evaluacion previa", value=prep["content"], height=150, key=f"prep_{opp['id']}")
    if st.button("Preparar / actualizar briefing", use_container_width=True):
        st.toast("Demo local: briefing marcado como actualizado.")
        prep["state"] = "Editado"


def render_tab_meeting(opp: dict[str, Any]) -> None:
    field_grid(
        [
            ("Fecha reunion", opp["meeting_at"]),
            ("Calendar", opp["calendar_link"]),
            ("Videollamada", opp["meeting_link"]),
            ("Granola / Fathom", opp["recording_ref"] or "Pendiente"),
            ("Resumen", opp["meeting_summary"] or "Pendiente"),
        ]
    )
    st.text_area("Transcripcion", value=opp["transcript"], height=140, key=f"meeting_transcript_{opp['id']}")
    if opp["diagnostic"]["answers"]:
        st.markdown("#### Respuestas clave")
        for question, answer, source in opp["diagnostic"]["answers"]:
            field_grid([(question, answer), ("Origen", source)])
    if st.button("Procesar reunion", use_container_width=True):
        st.toast("Demo local: procesamiento pendiente de integracion real.")


def render_tab_research(opp: dict[str, Any]) -> None:
    research = opp["market_research"]
    field_grid(
        [
            ("Cliente ideal", "Empresas B2B con venta consultiva y ticket suficiente."),
            ("Industrias", opp["industry"]),
            ("Paises", opp["country"]),
            ("Cargos", "CEO, Gerencia Comercial, Operaciones, Tecnologia"),
            ("Mercado objetivo", research["summary"] or "Pendiente de generar"),
            ("Empresas estimadas", "850 - 1.400 cuentas"),
            ("Nivel dificultad", research["difficulty"] or "Pendiente"),
            ("Canales", "Correo, llamadas, LinkedIn y WhatsApp segun disponibilidad"),
            ("Riesgos", "Mercado reducido si no se amplian industrias o cargos."),
            ("Oportunidades", "Trabajar ICP y empresas definidas en paralelo."),
            ("Estimacion reuniones", "8-10 reuniones mensuales en escenario recomendado"),
            ("Servicio recomendado", "Gestion de Prospeccion + Implementacion"),
            ("Precio", "Usar calculadora de propuesta antes de comprometer objetivo."),
        ]
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Generar investigacion de mercado", use_container_width=True):
            research["state"] = "Generado"
            research["summary"] = research["summary"] or "Investigacion demo generada desde datos locales."
            st.toast("Investigacion demo generada.")
    with c2:
        if st.button("Aprobar investigacion", use_container_width=True):
            research["state"] = "Aprobado"
            st.toast("Investigacion demo aprobada.")
    with c3:
        if st.button("Usar investigacion en propuesta", use_container_width=True):
            st.session_state["commercial_requested_tab"] = "Propuesta"
            st.toast("La propuesta queda lista para usar esta investigacion.")
            st.rerun()


def render_tab_proposal(opp: dict[str, Any]) -> None:
    proposal = active_proposal(opp) or {
        "version": "Borrador",
        "status": "Borrador",
        "setup_amount": 490000,
        "monthly_amount": 0,
        "total_amount": 0,
        "expected_margin": 40,
        "valid_until": "Pendiente",
        "summary": "Propuesta por completar desde investigacion y diagnostico.",
        "sent_at": "",
        "pdf_ref": "",
        "is_current": True,
    }
    field_grid(
        [
            ("Diagnostico resumido", proposal["summary"]),
            ("Mercado recomendado", opp["market_research"]["summary"] or "Pendiente"),
            ("Servicio", "Gestion de Prospeccion + Implementacion de Sistema de Prospeccion"),
            ("Alcance", "ICP + empresas definidas en paralelo"),
            ("Implementacion", "2 a 4 semanas"),
            ("Duracion", "5 meses"),
            ("Setup", money(proposal["setup_amount"])),
            ("Mensualidad", money(proposal["monthly_amount"]) if proposal["monthly_amount"] else "Pendiente"),
            ("Total", money(proposal["total_amount"]) if proposal["total_amount"] else "Pendiente"),
            ("Condiciones", "Setup + mensualidad fija. Sin cobro por reunion valida."),
            ("Vigencia", proposal["valid_until"]),
            ("Estado", proposal["status"]),
            ("Version", proposal["version"]),
        ]
    )
    render_price_calculator(opp, proposal)
    a1, a2, a3, a4 = st.columns(4)
    a1.button("Generar PDF", use_container_width=True, disabled=True)
    a2.button("Preparar correo", use_container_width=True, disabled=True)
    a3.button("Enviar propuesta", use_container_width=True, disabled=True)
    a4.button("Programar seguimiento", use_container_width=True, disabled=True)


def render_price_calculator(opp: dict[str, Any], proposal: dict[str, Any]) -> None:
    st.markdown("#### Calculo privado")
    c1, c2, c3 = st.columns(3)
    with c1:
        fixed = st.number_input("Costos fijos", min_value=0, value=650000, step=50000, key=f"fixed_{opp['id']}")
        setup_cost = st.number_input("Costos implementacion", min_value=0, value=250000, step=50000, key=f"setup_cost_{opp['id']}")
        expected_meetings = st.number_input("Reuniones estimadas", min_value=1, value=10, step=1, key=f"meet_{opp['id']}")
    with c2:
        variable = st.number_input("Costos variables", min_value=0, value=250000, step=50000, key=f"var_{opp['id']}")
        months = st.number_input("Duracion meses", min_value=1, value=5, step=1, key=f"months_{opp['id']}")
        setup_amount = st.number_input("Setup sugerido", min_value=0, value=490000, step=50000, key=f"setup_amt_{opp['id']}")
    with c3:
        margin = st.number_input("Margen esperado (%)", min_value=0, max_value=95, value=40, step=5, key=f"margin_{opp['id']}")
        min_margin = st.number_input("Margen minimo (%)", min_value=0, max_value=95, value=30, step=5, key=f"min_margin_{opp['id']}")
        contingency = st.number_input("Contingencia", min_value=0, value=0, step=50000, key=f"cont_{opp['id']}")
    result = calculate_price(fixed, variable, setup_cost, margin, min_margin, months, setup_amount, contingency, 0, expected_meetings)
    kpi_grid(
        [
            ("Costo mensual total", money(result["monthly_cost"])),
            ("Costo total proyecto", money(result["total_project_cost"])),
            ("Precio sugerido mensual", money(result["final_monthly"])),
            ("Setup sugerido", money(setup_amount)),
            ("Utilidad estimada", money(result["total_profit"])),
            ("Margen real", f'{result["real_margin"]:.1f}%'),
            ("Precio minimo", money(result["minimum_monthly"])),
            ("Ingreso por reunion", money(result["revenue_per_meeting"])),
        ]
    )
    scenario_df = pd.DataFrame(scenario_prices(result["monthly_cost"]))
    scenario_df["Precio sugerido mensual"] = scenario_df["Precio sugerido mensual"].map(money)
    scenario_df["Utilidad bruta mensual"] = scenario_df["Utilidad bruta mensual"].map(money)
    st.dataframe(scenario_df, use_container_width=True, hide_index=True)
    sent = proposal.get("status") == "Enviada"
    confirm_key = f"apply_confirm_{opp['id']}"
    if st.button("APLICAR MONTO SUGERIDO", type="primary", use_container_width=True):
        st.session_state[confirm_key] = True
    if st.session_state.get(confirm_key):
        st.warning("Confirma aplicar el monto sugerido. Si ya fue enviada, se creara una nueva version demo.")
        y, n = st.columns(2)
        with y:
            if st.button("Confirmar aplicacion", key=f"confirm_apply_{opp['id']}", use_container_width=True):
                _apply_suggested_amount(opp, result, setup_amount, sent)
                st.session_state[confirm_key] = False
                st.rerun()
        with n:
            if st.button("Cancelar", key=f"cancel_apply_{opp['id']}", use_container_width=True):
                st.session_state[confirm_key] = False
                st.rerun()


def _apply_suggested_amount(opp: dict[str, Any], result: dict[str, float], setup_amount: float, sent: bool) -> None:
    proposals = opp.setdefault("proposals", [])
    for prop in proposals:
        prop["is_current"] = False
    version_number = len(proposals) + 1
    status = "Borrador" if sent else (proposals[-1]["status"] if proposals else "Borrador")
    proposals.append(
        {
            "id": f"{opp['id']}-demo-v{version_number}",
            "version": f"Version {version_number}",
            "status": status,
            "is_current": True,
            "setup_amount": setup_amount,
            "monthly_amount": round(result["final_monthly"]),
            "total_amount": round(result["final_monthly"] * 5 + setup_amount),
            "expected_margin": 40,
            "created_at": "2026-07-23",
            "sent_at": "",
            "valid_until": "Pendiente",
            "pdf_ref": "",
            "summary": "Version demo creada desde calculadora interna.",
        }
    )
    opp["status"] = "Propuesta en preparacion"
    opp["history"].append(("2026-07-23 12:10", "manual", "Monto sugerido aplicado en nueva version demo"))


def render_tab_email_followup(opp: dict[str, Any]) -> None:
    if opp["emails"]:
        timeline([(d, sender, subject) for d, sender, subject, _body in opp["emails"]])
    else:
        st.info("No hay correos registrados en la demo.")
    st.markdown("#### Seguimientos")
    if opp["followups"]:
        timeline([(date_value, status, title) for title, date_value, status, _body in opp["followups"]])
    st.button("Crear borrador de seguimiento", use_container_width=True, disabled=True)


def render_tab_history(opp: dict[str, Any]) -> None:
    timeline(opp["history"])


def _presentation_slides(opp: dict[str, Any]) -> list[dict[str, Any]]:
    intro_sections = opp.get("intro_sections") or [
        ("Contacto", f"{opp['contact']} - {opp['role']}"),
        ("Pais", opp["country"]),
        ("Industria", opp["industry"]),
        ("Proximo paso", opp["next_followup"]),
    ]
    return [
        {
            "title": f"Nuestra lectura de {opp['company']}",
            "headline": f"{opp['company']} - {opp['industry']}",
            "body": opp.get("preparation", {}).get("content", "Evaluacion previa pendiente."),
            "sections": intro_sections,
        },
        *STANDARD_PRESENTATION,
    ]


def _database_demo_url() -> str:
    rows = [
        {
            "segment": "Soporte e infraestructura TI",
            "signal": "Búsqueda activa de proveedor para soporte y mantenimiento TI.",
            "need": "Mantenimiento preventivo/correctivo, soporte a usuarios, equipos de cómputo e impresión.",
            "location": "México",
            "contact": "Área de tecnología / operaciones",
            "action": "Validar alcance y priorizar contacto consultivo.",
        },
        {
            "segment": "Equipamiento corporativo",
            "signal": "Evaluación de partners para leasing tecnológico.",
            "need": "Laptops corporativas, renovación, soporte, garantías y cobertura nacional.",
            "location": "Por validar",
            "contact": "Tecnología / administración de activos",
            "action": "Revisar fit comercial antes de activar campaña.",
        },
        {
            "segment": "Infraestructura y hardware",
            "signal": "Búsqueda de proveedores TI para requerimientos corporativos.",
            "need": "Laptops, PCs, servidores, monitores, accesorios y repuestos.",
            "location": "Latam",
            "contact": "Sistemas / servicios corporativos",
            "action": "Mantener en seguimiento si el mercado objetivo aplica.",
        },
        {
            "segment": "Conectividad y redes",
            "signal": "Empresa reforzando red de aliados tecnológicos.",
            "need": "Equipos de conectividad, redes, periféricos y accesorios tecnológicos.",
            "location": "Latam",
            "contact": "Compras / tecnología",
            "action": "Usar como cuenta objetivo o referencia lookalike.",
        },
        {
            "segment": "Soporte TI externo",
            "signal": "Necesidad de proveedor externo para atención de usuarios.",
            "need": "Incidencias, configuración de hardware/software y mantenimiento operativo.",
            "location": "México",
            "contact": "Operaciones / TI",
            "action": "Descartar o dejar en baja prioridad según alcance.",
        },
        {
            "segment": "Continuidad y respaldo",
            "signal": "Evaluación de solución de backup para bases de datos.",
            "need": "Automatización de respaldos, restauración confiable y monitoreo.",
            "location": "Por validar",
            "contact": "Dirección TI / infraestructura",
            "action": "Validar si calza con la línea priorizada.",
        },
    ]
    cards = "".join(
        f"""
        <article>
          <small>{escape(row["segment"])}</small>
          <h2>{escape(row["signal"])}</h2>
          <p>{escape(row["need"])}</p>
          <dl>
            <div><dt>Ubicación</dt><dd>{escape(row["location"])}</dd></div>
            <div><dt>Contacto sugerido</dt><dd>{escape(row["contact"])}</dd></div>
            <div><dt>Acción</dt><dd>{escape(row["action"])}</dd></div>
          </dl>
        </article>
        """
        for row in rows
    )
    html = f"""
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Base de datos de ejemplo - Conprospección</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700;800&family=Saira:wght@800;900&display=swap');
    * {{ box-sizing:border-box; }}
    body {{ background:#F7F6F3; color:#111; font-family:"IBM Plex Sans",Arial,sans-serif; margin:0; padding:32px; }}
    main {{ margin:0 auto; max-width:1180px; }}
    header {{ background:#111; border-radius:10px; color:#fff; margin-bottom:18px; padding:24px 28px; }}
    header small {{ color:#FFD200; font-weight:800; letter-spacing:.08em; text-transform:uppercase; }}
    h1 {{ font-family:Saira,"IBM Plex Sans",sans-serif; font-size:42px; line-height:1; margin:10px 0 8px; }}
    header p {{ color:#E9E9E4; font-size:16px; line-height:1.45; margin:0; max-width:860px; }}
    .note {{ background:#FFF6BF; border:1px solid #E2BF36; border-radius:8px; margin-bottom:18px; padding:14px 16px; }}
    .grid {{ display:grid; gap:14px; grid-template-columns:repeat(2,1fr); }}
    article {{ background:#fff; border:1px solid #DDDAD2; border-left:5px solid #FFD200; border-radius:9px; padding:18px; }}
    article small {{ color:#6B6B65; display:block; font-size:11px; font-weight:800; letter-spacing:.07em; margin-bottom:8px; text-transform:uppercase; }}
    h2 {{ font-size:18px; line-height:1.22; margin:0 0 8px; }}
    p {{ color:#34342F; font-size:14px; line-height:1.42; margin:0 0 12px; }}
    dl {{ display:grid; gap:8px; margin:0; }}
    dl div {{ border-top:1px solid #E6E3DC; padding-top:8px; }}
    dt {{ color:#777; font-size:10px; font-weight:800; letter-spacing:.07em; text-transform:uppercase; }}
    dd {{ font-size:13px; margin:2px 0 0; }}
    @media (max-width:760px) {{ body {{ padding:16px; }} .grid {{ grid-template-columns:1fr; }} h1 {{ font-size:30px; }} }}
  </style>
</head>
<body>
  <main>
    <header>
      <small>Base de datos de ejemplo</small>
      <h1>Señales de interés en infraestructura TI</h1>
      <p>Ejemplo anonimizado de cómo una estrategia de segmentación puede transformarse en oportunidades concretas para campañas de prospección multicanal.</p>
    </header>
    <section class="note">Esta vista no muestra clientes, fuentes internas, scores, herramientas ni nombres de campañas. Es una versión comercial para explicar el método.</section>
    <section class="grid">{cards}</section>
  </main>
</body>
</html>
    """
    encoded = base64.b64encode(html.encode("utf-8")).decode("ascii")
    return f"data:text/html;base64,{encoded}"


def render_database_demo_asset() -> None:
    _inject_layout_css(False)
    st.markdown("## Base de datos de ejemplo")
    st.caption("Vista comercial anonimizada para explicar cómo una estrategia de segmentación se transforma en oportunidades accionables.")
    st.info("No se muestran clientes reales, herramientas internas, scores, fuentes técnicas ni nombres de campañas.")
    rows = [
        {
            "Segmento": "Soporte e infraestructura TI",
            "Señal detectada": "Búsqueda activa de proveedor para soporte y mantenimiento TI.",
            "Necesidad": "Mantenimiento preventivo/correctivo, soporte a usuarios, equipos de cómputo e impresión.",
            "Ubicación": "México",
            "Contacto sugerido": "Área de tecnología / operaciones",
            "Acción recomendada": "Validar alcance y priorizar contacto consultivo.",
        },
        {
            "Segmento": "Equipamiento corporativo",
            "Señal detectada": "Evaluación de partners para leasing tecnológico.",
            "Necesidad": "Laptops corporativas, renovación, soporte, garantías y cobertura nacional.",
            "Ubicación": "Por validar",
            "Contacto sugerido": "Tecnología / administración de activos",
            "Acción recomendada": "Revisar fit comercial antes de activar campaña.",
        },
        {
            "Segmento": "Infraestructura y hardware",
            "Señal detectada": "Búsqueda de proveedores TI para requerimientos corporativos.",
            "Necesidad": "Laptops, PCs, servidores, monitores, accesorios y repuestos.",
            "Ubicación": "Latam",
            "Contacto sugerido": "Sistemas / servicios corporativos",
            "Acción recomendada": "Mantener en seguimiento si el mercado objetivo aplica.",
        },
        {
            "Segmento": "Conectividad y redes",
            "Señal detectada": "Empresa reforzando red de aliados tecnológicos.",
            "Necesidad": "Equipos de conectividad, redes, periféricos y accesorios tecnológicos.",
            "Ubicación": "Latam",
            "Contacto sugerido": "Compras / tecnología",
            "Acción recomendada": "Usar como cuenta objetivo o referencia lookalike.",
        },
        {
            "Segmento": "Soporte TI externo",
            "Señal detectada": "Necesidad de proveedor externo para atención de usuarios.",
            "Necesidad": "Incidencias, configuración de hardware/software y mantenimiento operativo.",
            "Ubicación": "México",
            "Contacto sugerido": "Operaciones / TI",
            "Acción recomendada": "Descartar o dejar en baja prioridad según alcance.",
        },
        {
            "Segmento": "Continuidad y respaldo",
            "Señal detectada": "Evaluación de solución de backup para bases de datos.",
            "Necesidad": "Automatización de respaldos, restauración confiable y monitoreo.",
            "Ubicación": "Por validar",
            "Contacto sugerido": "Dirección TI / infraestructura",
            "Acción recomendada": "Validar si calza con la línea priorizada.",
        },
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _presentation_iframe_html(opp: dict[str, Any], slide: dict[str, Any], slide_idx: int, total: int) -> str:
    sections = "".join(
        f"""
        <article class="detail-item">
          <strong>{escape(str(title))}</strong>
          <span>{escape(str(body))}</span>
        </article>
        """
        for title, body in slide.get("sections", [])
    )
    links = "".join(
        f'<a class="demo-link" href="{escape(str(url))}" target="_blank" rel="noopener">{escape(str(label))}</a>'
        if url
        else f'<span class="demo-link disabled">{escape(str(label))}<small>Pendiente</small></span>'
        for label, url in DEMO_SETTINGS["links"].items()
    )
    logo = _logo_data_uri()
    logo_html = f'<img src="{logo}" alt="Conprospeccion">' if logo else '<b>Conprospeccion</b>'
    return f"""
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700;800&family=Saira:wght@700;800;900&display=swap');
    :root {{
      --ink:#1A1A1A;
      --muted:#666661;
      --line:#E4E2DD;
      --paper:#FAFAF8;
      --gold:#FFD700;
      --gold-soft:#FFF7BF;
      --carbon:#333333;
    }}
    * {{ box-sizing:border-box; }}
    body {{
      margin:0;
      background:var(--paper);
      color:var(--ink);
      font-family:"IBM Plex Sans", Arial, sans-serif;
    }}
    .deck {{
      min-height:780px;
      padding:18px;
    }}
    .brand {{
      align-items:center;
      background:#fff;
      border:1px solid var(--line);
      border-radius:12px;
      display:flex;
      justify-content:space-between;
      gap:18px;
      padding:14px 18px;
      margin-bottom:16px;
    }}
    .brand img {{ max-height:42px; object-fit:contain; display:block; }}
    .count {{
      color:var(--muted);
      font-size:12px;
      font-weight:800;
      text-transform:uppercase;
    }}
    .slide {{
      background:#fff;
      border:1px solid var(--line);
      border-radius:14px;
      box-shadow:0 18px 46px rgba(0,0,0,.08);
      display:grid;
      gap:28px;
      grid-template-columns:minmax(0,.95fr) minmax(0,1.05fr);
      min-height:610px;
      padding:34px;
    }}
    .chip {{
      background:var(--gold-soft);
      border:1px solid #F0D28D;
      border-radius:999px;
      display:inline-flex;
      font-size:11px;
      font-weight:900;
      margin-bottom:14px;
      padding:6px 10px;
      text-transform:uppercase;
    }}
    h1 {{
      color:var(--ink);
      font-family:Saira, "IBM Plex Sans", sans-serif;
      font-size:42px;
      line-height:1.06;
      margin:0 0 18px;
      letter-spacing:0;
    }}
    .lead {{
      color:#363632;
      font-size:17px;
      line-height:1.55;
      margin:0;
    }}
    .detail {{
      align-self:stretch;
      background:var(--paper);
      border:1px solid var(--line);
      border-radius:12px;
      padding:22px;
    }}
    .detail h2 {{
      color:var(--ink);
      font-family:Saira, "IBM Plex Sans", sans-serif;
      font-size:23px;
      line-height:1.15;
      margin:0 0 16px;
      letter-spacing:0;
    }}
    .detail-grid {{
      display:grid;
      gap:10px;
    }}
    .detail-item {{
      background:#fff;
      border:1px solid var(--line);
      border-radius:9px;
      padding:11px 12px;
    }}
    .detail-item strong {{
      color:var(--ink);
      display:block;
      font-size:12px;
      margin-bottom:4px;
    }}
    .detail-item span {{
      color:#42423E;
      display:block;
      font-size:13px;
      line-height:1.42;
    }}
    .demo-row {{
      display:grid;
      gap:10px;
      grid-template-columns:repeat(6,minmax(0,1fr));
      margin-top:16px;
    }}
    .demo-link {{
      align-items:center;
      background:#fff;
      border:1px solid #C9C9C4;
      border-radius:8px;
      color:var(--ink);
      display:flex;
      font-size:13px;
      font-weight:800;
      justify-content:center;
      min-height:42px;
      padding:10px;
      text-align:center;
      text-decoration:none;
    }}
    .demo-link:hover {{
      background:var(--gold);
      border-color:var(--gold);
    }}
    .demo-link.disabled {{
      color:#8A8A84;
      flex-direction:column;
      font-weight:700;
    }}
    .demo-link small {{
      color:#9A9A94;
      display:block;
      font-size:10px;
      font-weight:700;
      margin-top:2px;
    }}
    @media(max-width:980px) {{
      .slide {{ grid-template-columns:1fr; padding:24px; }}
      .demo-row {{ grid-template-columns:repeat(2,minmax(0,1fr)); }}
      h1 {{ font-size:32px; }}
    }}
  </style>
</head>
<body>
  <main class="deck">
    <header class="brand">
      <div>{logo_html}</div>
      <div class="count">Presentacion comercial · {slide_idx + 1} de {total}</div>
    </header>
    <section class="slide">
      <div>
        <div class="chip">{escape(opp["company"])}</div>
        <h1>{escape(str(slide["title"]))}</h1>
        <p class="lead">{escape(str(slide["body"]))}</p>
      </div>
      <aside class="detail">
        <h2>{escape(str(slide["headline"]))}</h2>
        <div class="detail-grid">{sections}</div>
      </aside>
    </section>
    <nav class="demo-row" aria-label="Accesos demo">{links}</nav>
  </main>
</body>
</html>
    """


def _presentation_iframe_html_v2(opp: dict[str, Any], slide: dict[str, Any], slide_idx: int, total: int) -> str:
    layout = str(slide.get("layout", "analysis"))
    sections_data = [(str(title), str(body)) for title, body in slide.get("sections", [])]
    links = "".join(
        f'<a class="demo-link" href="{escape(str(url))}" target="_blank" rel="noopener">{escape(str(label))}</a>'
        if url
        else f'<span class="demo-link disabled">{escape(str(label))}<small>Pendiente</small></span>'
        for label, url in DEMO_SETTINGS["links"].items()
    )
    logo = _logo_data_uri()
    logo_html = f'<img src="{logo}" alt="Conprospeccion">' if logo else '<b>Conprospeccion</b>'

    def cards(class_name: str = "info-card") -> str:
        return "".join(
            f'<article class="{class_name}"><strong>{escape(title)}</strong><span>{escape(body)}</span></article>'
            for title, body in sections_data
        )

    def flow_bar(class_name: str = "black-flow") -> str:
        flow = slide.get("flow", [])
        items = "".join(f'<span>{escape(str(item))}</span>' for item in flow)
        return f'<section class="{class_name}">{items}</section>' if items else ""

    if layout == "analysis":
        body_html = f"""
        <section class="analysis-panel">
          <div class="eyebrow">{escape(opp["company"])}</div>
          <h1>{escape(str(slide["title"]))}</h1>
          <p>{escape(str(slide["body"]))}</p>
        </section>
        <section class="meta-row">
          <article><small>Empresa</small><strong>{escape(opp["company"])}</strong></article>
          <article><small>Industria</small><strong>{escape(opp["industry"])}</strong></article>
          <article><small>Pais</small><strong>{escape(opp["country"])}</strong></article>
          <article><small>Estado</small><strong>{escape(opp.get("preparation", {}).get("state", "Preparacion"))}</strong></article>
        </section>
        <section class="insight-grid">{cards()}</section>
        """
    elif layout == "cover":
        body_html = f"""
        <section class="cover-slide">
          <div class="cover-copy">
            <div class="logo-tile">{logo_html}</div>
            <h1>{escape(str(slide["title"]))}</h1>
            <p class="cover-sub">{escape(str(slide["headline"]))}</p>
            <p>{escape(str(slide["body"]))}</p>
            <small>Presentacion comercial 2026 · Confidencial · Conprospeccion</small>
          </div>
          <div class="cover-visual">
            <div class="signal-card">Mercado</div>
            <div class="signal-card">Conversaciones</div>
            <div class="signal-card">Oportunidades</div>
          </div>
        </section>
        """
    elif layout == "challenge":
        body_html = f"""
        <section class="title-panel">
          <div class="side-line"></div>
          <div><h1>{escape(str(slide["title"]))}</h1><p>{escape(str(slide["body"]))}</p></div>
        </section>
        <section class="question-grid">{cards("compact-card")}</section>
        {flow_bar("black-flow")}
        """
    elif layout == "services":
        first = sections_data[:2]
        rest = sections_data[2:]
        services = "".join(
            f'<article class="big-service"><div class="round-icon">{idx}</div><h2>{escape(title)}</h2><p>{escape(body)}</p></article>'
            for idx, (title, body) in enumerate(first, start=1)
        )
        notes = "".join(
            f'<article class="note-card"><strong>{escape(title)}</strong><span>{escape(body)}</span></article>'
            for title, body in rest
        )
        body_html = f"""
        <section class="title-panel hero-title">
          <div class="round-icon">CP</div>
          <div><h1>{escape(str(slide["title"]))}</h1><p>{escape(str(slide["headline"]))}</p></div>
        </section>
        <section class="service-grid">{services}</section>
        <section class="note-grid">{notes}</section>
        """
    elif layout == "operation":
        method_cards = "".join(
            f'<article class="service-card"><div class="service-icon">{idx}</div><strong>{escape(title)}</strong><span>{escape(body)}</span></article>'
            for idx, (title, body) in enumerate(sections_data, start=1)
        )
        body_html = f"""
        <section class="title-panel">
          <div class="round-icon">4</div>
          <div><h1>{escape(str(slide["title"]))}</h1><p>{escape(str(slide["body"]))}</p></div>
        </section>
        <section class="method-grid">{method_cards}</section>
        {flow_bar("yellow-flow")}
        """
    elif layout == "next":
        receive = "".join(
            f'<article class="receive-item"><strong>{escape(title)}</strong><span>{escape(body)}</span></article>'
            for title, body in sections_data
        )
        access_items = "".join(
            f'<a class="access-card" href="{escape(str(url))}" target="_blank" rel="noopener"><strong>{escape(str(label))}</strong><span>Acceso de revision</span></a>'
            if url
            else f'<div class="access-card disabled"><strong>{escape(str(label))}</strong><span>Pendiente de configurar</span></div>'
            for label, url in DEMO_SETTINGS["links"].items()
        )
        steps = "".join(
            f'<article><b>{i}</b><span>{escape(str(item))}</span></article>'
            for i, item in enumerate(slide.get("flow", []), start=1)
        )
        body_html = f"""
        <section class="title-panel">
          <div><h1>{escape(str(slide["title"]))}</h1><p>{escape(str(slide["body"]))}</p></div>
        </section>
        <section class="timeline-steps">{steps}</section>
        <section class="split-panel">
          <article class="white-box"><h2>Que recibiras</h2>{receive}</article>
          <article class="white-box"><h2>Accesos para revisar</h2>{access_items}</article>
        </section>
        <p class="foot-note">La propuesta comercial se genera aparte del brochure comercial.</p>
        """
    else:
        body_html = f"""
        <section class="title-panel">
          <div class="round-icon">CP</div>
          <div><h1>{escape(str(slide["title"]))}</h1><p>{escape(str(slide["body"]))}</p></div>
        </section>
        <section class="insight-grid">{cards()}</section>
        """

    return f"""
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700;800&family=Saira:wght@700;800;900&display=swap');
    :root {{ --ink:#1A1A1A; --muted:#666661; --line:#E4E2DD; --paper:#FAFAF8; --gold:#FFD700; --gold-soft:#FFF7BF; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--paper); color:var(--ink); font-family:"IBM Plex Sans", Arial, sans-serif; }}
    .deck {{ min-height:780px; padding:18px; }}
    .brand {{ align-items:center; background:#111; border:1px solid #222; border-radius:8px; display:flex; justify-content:space-between; gap:18px; padding:10px 18px; margin-bottom:16px; }}
    .brand img {{ max-height:34px; object-fit:contain; display:block; background:#fff; border-radius:6px; padding:4px 8px; }}
    .count {{ color:#fff; font-size:12px; font-weight:800; letter-spacing:.08em; text-transform:uppercase; }}
    h1 {{ color:var(--ink); font-family:Saira, "IBM Plex Sans", sans-serif; font-size:38px; line-height:1.06; margin:0 0 12px; letter-spacing:0; }}
    p {{ color:#363632; font-size:16px; line-height:1.48; margin:0; }}
    .analysis-panel, .cover-slide, .title-panel, .white-box {{ background:#fff; border:1px solid var(--line); border-radius:10px; box-shadow:0 10px 26px rgba(0,0,0,.06); }}
    .analysis-panel {{ border-top:5px solid var(--gold); padding:34px 42px; margin-bottom:14px; }}
    .eyebrow {{ background:var(--gold-soft); border:1px solid #F0D28D; border-radius:999px; display:inline-flex; font-size:11px; font-weight:900; margin-bottom:12px; padding:6px 10px; text-transform:uppercase; }}
    .meta-row {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin-bottom:14px; }}
    .meta-row article {{ background:#fff; border:1px solid var(--line); border-radius:8px; padding:14px 16px; }}
    .meta-row small {{ color:var(--muted); display:block; font-size:10px; font-weight:900; text-transform:uppercase; }}
    .meta-row strong {{ display:block; font-size:16px; margin-top:4px; }}
    .insight-grid, .method-grid, .question-grid, .note-grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; }}
    .question-grid {{ grid-template-columns:repeat(4,minmax(0,1fr)); }}
    .info-card, .compact-card, .service-card, .note-card {{ background:#fff; border:1px solid var(--line); border-radius:8px; min-height:112px; padding:16px; }}
    .info-card strong, .compact-card strong, .service-card strong, .note-card strong {{ color:var(--ink); display:block; font-size:15px; margin-bottom:7px; }}
    .info-card span, .compact-card span, .service-card span, .note-card span {{ color:#42423E; display:block; font-size:13px; line-height:1.42; }}
    .cover-slide {{ display:grid; grid-template-columns:1.05fr .95fr; min-height:570px; overflow:hidden; }}
    .cover-copy {{ padding:42px; }}
    .cover-copy h1 {{ font-size:44px; max-width:650px; }}
    .cover-sub {{ color:#666661; font-size:19px; margin-bottom:18px; }}
    .logo-tile {{ margin-bottom:38px; }}
    .logo-tile img {{ max-height:46px; }}
    .cover-copy small {{ color:#8A8A84; display:block; font-size:11px; font-weight:800; letter-spacing:.12em; margin-top:28px; text-transform:uppercase; }}
    .cover-visual {{ background:#1f1f1f; display:grid; gap:14px; padding:44px; place-content:center; }}
    .signal-card {{ border:1px solid rgba(255,215,0,.45); border-radius:8px; color:#fff; font-family:Saira, "IBM Plex Sans", sans-serif; font-size:24px; font-weight:900; min-width:330px; padding:22px 28px; }}
    .title-panel {{ align-items:center; display:flex; gap:18px; margin-bottom:18px; padding:26px 30px; }}
    .side-line {{ background:#111; height:58px; width:5px; }}
    .round-icon {{ align-items:center; background:var(--gold); border-radius:999px; display:flex; flex:0 0 62px; font-family:Saira, "IBM Plex Sans", sans-serif; font-weight:900; height:62px; justify-content:center; width:62px; }}
    .black-flow, .yellow-flow {{ align-items:center; background:#111; border-radius:4px; color:#fff; display:flex; font-family:Saira, "IBM Plex Sans", sans-serif; font-size:17px; font-weight:900; gap:18px; justify-content:center; margin-top:22px; padding:18px; text-transform:uppercase; }}
    .yellow-flow {{ background:var(--gold); color:#111; }}
    .black-flow span:not(:last-child)::after, .yellow-flow span:not(:last-child)::after {{ content:" ->"; margin-left:18px; }}
    .service-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:14px; }}
    .big-service {{ background:#fff; border:1px solid var(--line); border-left:5px solid var(--gold); border-radius:10px; padding:28px; }}
    .big-service h2, .white-box h2 {{ font-family:Saira, "IBM Plex Sans", sans-serif; font-size:25px; margin:12px 0 8px; }}
    .service-icon {{ align-items:center; background:var(--gold); border-radius:999px; display:flex; font-weight:900; height:34px; justify-content:center; margin-bottom:10px; width:34px; }}
    .timeline-steps {{ display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:0; margin:12px 0 20px; }}
    .timeline-steps article {{ background:#fff; border:1px solid var(--line); min-height:126px; padding:18px 14px; text-align:center; }}
    .timeline-steps b {{ align-items:center; background:var(--gold); border-radius:999px; display:flex; font-size:22px; height:44px; justify-content:center; margin:0 auto 12px; width:44px; }}
    .timeline-steps span {{ font-weight:800; }}
    .split-panel {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
    .white-box {{ padding:24px; }}
    .receive-item {{ border-top:1px solid var(--line); display:block; padding:12px 0; }}
    .receive-item strong, .access-card strong {{ display:block; font-size:16px; }}
    .receive-item span, .access-card span {{ color:var(--muted); display:block; font-size:13px; margin-top:4px; }}
    .access-card {{ background:#fff; border:1px solid var(--line); border-radius:8px; color:var(--ink); display:block; margin:10px 0; padding:15px 18px; text-decoration:none; }}
    .access-card:hover {{ border-color:var(--gold); background:#FFFDF0; }}
    .access-card.disabled {{ color:#777; }}
    .foot-note {{ border:1px solid #F0D28D; border-radius:8px; color:#6B5E00; display:inline-block; font-size:13px; margin:18px auto 0; padding:10px 14px; }}
    .demo-row {{ display:grid; gap:10px; grid-template-columns:repeat(3,minmax(0,1fr)); margin-top:16px; }}
    .demo-link {{ align-items:center; background:#fff; border:1px solid #C9C9C4; border-radius:8px; color:var(--ink); display:flex; font-size:13px; font-weight:800; justify-content:center; min-height:42px; padding:10px; text-align:center; text-decoration:none; }}
    .demo-link:hover {{ background:var(--gold); border-color:var(--gold); }}
    .demo-link.disabled {{ color:#8A8A84; flex-direction:column; font-weight:700; }}
    .demo-link small {{ color:#9A9A94; display:block; font-size:10px; font-weight:700; margin-top:2px; }}
    @media(max-width:980px) {{
      .meta-row, .insight-grid, .method-grid, .question-grid, .note-grid, .service-grid, .split-panel, .timeline-steps, .cover-slide {{ grid-template-columns:1fr; }}
      .demo-row {{ grid-template-columns:1fr; }}
      h1 {{ font-size:32px; }}
    }}
  </style>
</head>
<body>
  <main class="deck">
    <header class="brand">
      <div>{logo_html}</div>
      <div class="count">Presentacion comercial · {slide_idx + 1} de {total}</div>
    </header>
    {body_html}
    <nav class="demo-row" aria-label="Accesos demo">{links}</nav>
  </main>
</body>
</html>
    """


def _presentation_iframe_html_v3(opp: dict[str, Any], slide: dict[str, Any], slide_idx: int, total: int) -> str:
    layout = str(slide.get("layout", "analysis"))
    sections = [(str(title), str(body)) for title, body in slide.get("sections", [])]
    logo = _logo_data_uri()
    logo_img = f'<img src="{logo}" alt="Conprospeccion">' if logo else "<strong>Conprospeccion</strong>"
    brand = f'<div class="brand-left">{logo_img}<strong>ConprospeccionOS</strong></div>'
    links = "".join(
        f'<a class="demo-link" href="{escape(str(url))}" target="_blank" rel="noopener">{escape(str(label))}</a>'
        if url
        else f'<span class="demo-link disabled">{escape(str(label))}<small>Pendiente</small></span>'
        for label, url in DEMO_SETTINGS["links"].items()
    )

    def card_grid(class_name: str, numbered: bool = False) -> str:
        return "".join(
            (
                f'<article class="{class_name}"><b>{idx}</b><strong>{escape(title)}</strong><span>{escape(body)}</span></article>'
                if numbered
                else f'<article class="{class_name}"><strong>{escape(title)}</strong><span>{escape(body)}</span></article>'
            )
            for idx, (title, body) in enumerate(sections, start=1)
        )

    def flow(class_name: str) -> str:
        items = "".join(f"<span>{escape(str(item))}</span>" for item in slide.get("flow", []))
        return f'<section class="{class_name}">{items}</section>' if items else ""

    if layout == "analysis":
        body = f"""
        <section class="analysis-hero">
          <div class="pill">{escape(opp["company"])}</div>
          <h1>{escape(str(slide["title"]))}</h1>
          <p>{escape(str(slide["body"]))}</p>
        </section>
        <section class="meta-strip">
          <article><small>Empresa</small><strong>{escape(opp["company"])}</strong></article>
          <article><small>Industria</small><strong>{escape(opp["industry"])}</strong></article>
          <article><small>Pais</small><strong>{escape(opp["country"])}</strong></article>
          <article><small>Estado</small><strong>{escape(opp.get("preparation", {}).get("state", "Preparacion"))}</strong></article>
        </section>
        <section class="analysis-grid">{card_grid("signal", True)}</section>
        """
    elif layout == "cover":
        body = f"""
        <section class="cover">
          <div class="cover-copy">
            <div class="cover-logo">{logo_img}</div>
            <h1>{escape(str(slide["title"]))}</h1>
            <p class="subtitle">{escape(str(slide["headline"]))}</p>
            <p>{escape(str(slide["body"]))}</p>
            <small>Presentacion comercial 2026 &middot; Confidencial &middot; Conprospeccion</small>
          </div>
          <aside class="cover-dark">
            <article>Mercado</article>
            <article>Conversaciones</article>
            <article>Oportunidades</article>
          </aside>
        </section>
        """
    elif layout == "challenge":
        body = f"""
        <section class="headline-panel">
          <i></i>
          <div><h1>{escape(str(slide["title"]))}</h1><p>{escape(str(slide["body"]))}</p></div>
        </section>
        <section class="question-grid">{card_grid("question")}</section>
        {flow("black-flow")}
        """
    elif layout == "services":
        first = sections[:2]
        rest = sections[2:]
        service_cards = "".join(
            f'<article class="service"><b>{idx}</b><h2>{escape(title)}</h2><p>{escape(body)}</p></article>'
            for idx, (title, body) in enumerate(first, start=1)
        )
        note_cards = "".join(
            f'<article class="note"><strong>{escape(title)}</strong><span>{escape(body)}</span></article>'
            for title, body in rest
        )
        body = f"""
        <section class="headline-panel services-title">
          <b>CP</b>
          <div><h1>{escape(str(slide["title"]))}</h1><p>{escape(str(slide["headline"]))}</p></div>
        </section>
        <section class="services-grid">{service_cards}</section>
        <section class="notes-grid">{note_cards}</section>
        """
    elif layout == "operation":
        body = f"""
        <section class="headline-panel services-title">
          <b>4</b>
          <div><h1>{escape(str(slide["title"]))}</h1><p>{escape(str(slide["body"]))}</p></div>
        </section>
        <section class="method-grid">{card_grid("method", True)}</section>
        {flow("gold-flow")}
        """
    elif layout == "next":
        steps = "".join(
            f"<article><b>{idx}</b><span>{escape(str(item))}</span></article>"
            for idx, item in enumerate(slide.get("flow", []), start=1)
        )
        receive = "".join(
            f'<article><strong>{escape(title)}</strong><span>{escape(body)}</span></article>' for title, body in sections
        )
        access = "".join(
            f'<a href="{escape(str(url))}" target="_blank" rel="noopener"><strong>{escape(str(label))}</strong><span>Acceso de revision</span></a>'
            if url
            else f'<div><strong>{escape(str(label))}</strong><span>Pendiente de configurar</span></div>'
            for label, url in DEMO_SETTINGS["links"].items()
        )
        body = f"""
        <section class="headline-panel">
          <div><h1>{escape(str(slide["title"]))}</h1><p>{escape(str(slide["body"]))}</p></div>
        </section>
        <section class="steps">{steps}</section>
        <section class="next-grid">
          <article class="next-box"><h2>Que recibiras</h2>{receive}</article>
          <article class="next-box"><h2>Accesos para revisar</h2>{access}</article>
        </section>
        <p class="disclaimer">La propuesta comercial se genera aparte del brochure comercial.</p>
        """
    else:
        body = f"""
        <section class="headline-panel">
          <div><h1>{escape(str(slide["title"]))}</h1><p>{escape(str(slide["body"]))}</p></div>
        </section>
        <section class="analysis-grid">{card_grid("signal", True)}</section>
        """

    return f"""
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700;800&family=Saira:wght@700;800;900&display=swap');
    :root {{ --ink:#161616; --muted:#666661; --paper:#FAFAF8; --line:#E3E1DC; --gold:#FFD700; --gold-soft:#FFF5B7; --shadow:0 18px 44px rgba(22,22,20,.09); }}
    * {{ box-sizing:border-box; }}
    html, body {{ margin:0; width:100%; min-height:100%; overflow:hidden; }}
    body {{ background:var(--paper); color:var(--ink); font-family:"IBM Plex Sans", Arial, sans-serif; }}
    .deck {{ max-width:1600px; min-height:880px; margin:0 auto; padding:18px 24px 22px; }}
    .brand {{ align-items:center; background:#111; border-radius:8px; display:flex; justify-content:space-between; min-height:64px; padding:12px 22px; margin-bottom:18px; }}
    .brand-left {{ align-items:center; display:flex; gap:14px; }}
    .brand-left img {{ background:#fff; border-radius:6px; display:block; max-height:38px; object-fit:contain; padding:5px 9px; }}
    .brand-left strong {{ color:#fff; font-family:Saira,"IBM Plex Sans",sans-serif; font-size:24px; line-height:1; }}
    .brand .count {{ color:#fff; font-size:12px; font-weight:900; letter-spacing:.08em; text-transform:uppercase; }}
    h1 {{ font-family:Saira,"IBM Plex Sans",sans-serif; font-size:46px; line-height:1.04; margin:0 0 14px; letter-spacing:0; }}
    p {{ color:#363632; font-size:17px; line-height:1.5; margin:0; }}
    .pill {{ background:var(--gold-soft); border:1px solid #EBCB61; border-radius:999px; display:inline-flex; font-size:11px; font-weight:900; margin-bottom:16px; padding:7px 12px; text-transform:uppercase; }}
    .analysis-hero, .headline-panel, .cover, .next-box {{ background:#fff; border:1px solid var(--line); border-radius:12px; box-shadow:var(--shadow); }}
    .analysis-hero {{ border-top:7px solid var(--gold); min-height:245px; padding:38px 44px; margin-bottom:16px; }}
    .analysis-hero p {{ max-width:1370px; font-size:18px; line-height:1.56; }}
    .meta-strip {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin-bottom:16px; }}
    .meta-strip article {{ background:#fff; border:1px solid var(--line); border-radius:10px; box-shadow:0 9px 22px rgba(22,22,20,.045); min-height:86px; padding:18px 20px 18px 64px; position:relative; }}
    .meta-strip article:before {{ background:var(--gold-soft); border:1px solid #EBCB61; border-radius:999px; content:""; height:30px; left:20px; position:absolute; top:27px; width:30px; }}
    .meta-strip small {{ color:var(--muted); display:block; font-size:10px; font-weight:900; letter-spacing:.08em; text-transform:uppercase; }}
    .meta-strip strong {{ display:block; font-size:18px; margin-top:6px; }}
    .analysis-grid, .method-grid, .notes-grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; }}
    .signal, .method, .question, .note {{ background:#fff; border:1px solid var(--line); border-radius:10px; box-shadow:0 9px 22px rgba(22,22,20,.045); min-height:150px; position:relative; }}
    .signal, .method {{ padding:22px 22px 20px 88px; }}
    .signal b, .method b {{ align-items:center; background:var(--gold); border-radius:999px; display:flex; font-family:Saira,"IBM Plex Sans",sans-serif; font-size:18px; height:44px; justify-content:center; left:22px; position:absolute; top:24px; width:44px; }}
    .signal strong, .method strong, .question strong, .note strong {{ display:block; font-size:17px; line-height:1.2; margin-bottom:10px; }}
    .signal span, .method span, .question span, .note span {{ color:#44443F; display:block; font-size:14px; line-height:1.46; }}
    .cover {{ display:grid; grid-template-columns:.95fr 1.05fr; min-height:640px; overflow:hidden; }}
    .cover-copy {{ padding:66px 64px; }}
    .cover-logo img {{ max-height:50px; margin-bottom:58px; }}
    .cover-copy h1 {{ font-size:56px; max-width:660px; }}
    .cover-copy .subtitle {{ color:#696966; font-size:23px; margin-bottom:22px; }}
    .cover-copy small {{ color:#8A8A84; display:block; font-size:11px; font-weight:900; letter-spacing:.14em; margin-top:34px; text-transform:uppercase; }}
    .cover-dark {{ background:#202020; display:grid; gap:18px; padding:74px; place-content:center; }}
    .cover-dark article {{ border:1px solid rgba(255,215,0,.55); border-radius:8px; color:#fff; font-family:Saira,"IBM Plex Sans",sans-serif; font-size:29px; font-weight:900; min-width:360px; padding:28px 32px; }}
    .headline-panel {{ align-items:center; display:flex; gap:24px; margin-bottom:24px; min-height:150px; padding:34px 40px; }}
    .headline-panel i {{ background:#111; display:block; height:70px; width:5px; }}
    .headline-panel > b, .service > b {{ align-items:center; background:var(--gold); border-radius:999px; display:flex; flex:0 0 70px; font-family:Saira,"IBM Plex Sans",sans-serif; font-size:22px; font-weight:900; height:70px; justify-content:center; width:70px; }}
    .question-grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; }}
    .question {{ min-height:210px; padding:26px 22px; }}
    .black-flow, .gold-flow {{ align-items:center; background:#111; border-radius:4px; color:#fff; display:flex; font-family:Saira,"IBM Plex Sans",sans-serif; font-size:21px; font-weight:900; gap:20px; justify-content:center; margin-top:26px; padding:22px; text-transform:uppercase; }}
    .gold-flow {{ background:var(--gold); color:#111; }}
    .black-flow span:not(:last-child):after, .gold-flow span:not(:last-child):after {{ content:" ->"; margin-left:20px; }}
    .services-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-bottom:16px; }}
    .service {{ background:#fff; border:1px solid var(--line); border-left:7px solid var(--gold); border-radius:12px; box-shadow:var(--shadow); min-height:285px; padding:34px; position:relative; }}
    .service h2, .next-box h2 {{ font-family:Saira,"IBM Plex Sans",sans-serif; font-size:30px; margin:18px 0 12px; }}
    .note {{ min-height:126px; padding:22px; }}
    .steps {{ display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:0; margin:14px 0 24px; }}
    .steps article {{ background:#fff; border:1px solid var(--line); min-height:155px; padding:24px 12px; text-align:center; }}
    .steps b {{ align-items:center; background:var(--gold); border-radius:999px; display:flex; font-size:25px; height:52px; justify-content:center; margin:0 auto 16px; width:52px; }}
    .steps span {{ display:block; font-size:16px; font-weight:900; }}
    .next-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }}
    .next-box {{ padding:30px; }}
    .next-box article, .next-box a, .next-box div {{ border-top:1px solid var(--line); color:var(--ink); display:block; padding:14px 0; text-decoration:none; }}
    .next-box strong {{ display:block; font-size:17px; }}
    .next-box span {{ color:var(--muted); display:block; font-size:14px; margin-top:4px; }}
    .disclaimer {{ border:1px solid #EBCB61; border-radius:8px; color:#6B5E00; display:inline-block; font-size:13px; margin:18px 0 0; padding:10px 14px; }}
    .demo-row {{ display:grid; gap:14px; grid-template-columns:repeat(3,minmax(0,1fr)); margin-top:18px; }}
    .demo-link {{ align-items:center; background:#fff; border:1px solid #C9C9C4; border-radius:8px; color:var(--ink); display:flex; font-size:16px; font-weight:900; justify-content:center; min-height:62px; padding:14px 18px; text-align:center; text-decoration:none; }}
    .demo-link:hover {{ background:var(--gold); border-color:var(--gold); }}
    .demo-link.disabled {{ color:#777; flex-direction:column; }}
    .demo-link small {{ color:#999; display:block; font-size:10px; margin-top:3px; }}
    @media(max-width:1000px) {{
      html, body {{ overflow:auto; }}
      .cover, .meta-strip, .analysis-grid, .method-grid, .notes-grid, .question-grid, .services-grid, .steps, .next-grid, .demo-row {{ grid-template-columns:1fr; }}
      h1, .cover-copy h1 {{ font-size:34px; }}
    }}
  </style>
</head>
<body>
  <main class="deck">
    <header class="brand">
      {brand}
      <div class="count">Presentacion comercial &middot; {slide_idx + 1} de {total}</div>
    </header>
    {body}
    <nav class="demo-row">{links}</nav>
  </main>
</body>
</html>
    """


def _presentation_iframe_html_v4(opp: dict[str, Any], slide: dict[str, Any], slide_idx: int, total: int) -> str:
    layout = str(slide.get("layout", "analysis"))
    sections = [(str(title), str(body)) for title, body in slide.get("sections", [])]
    logo = _logo_data_uri()
    logo_img = f'<img src="{logo}" alt="Conprospección">' if logo else ""
    link_items = []
    for label, url in DEMO_SETTINGS["links"].items():
        final_url = _database_demo_url() if label == "Base de datos de ejemplo" and not url else str(url)
        if final_url:
            link_items.append(
                f'<a class="bottom-link" href="{escape(final_url)}" target="_blank" rel="noopener">{escape(str(label))}</a>'
            )
        else:
            link_items.append(f'<span class="bottom-link pending">{escape(str(label))}<small>Pendiente</small></span>')
    links = "".join(link_items)

    def flow_html(items: list[Any], class_name: str) -> str:
        if not items:
            return ""
        return f'<div class="{class_name}">' + "".join(f"<span>{escape(str(item))}</span>" for item in items) + "</div>"

    if layout == "analysis":
        main_cards = sections[:6]
        validate = sections[6:] or []
        cards = "".join(
            f'<article class="insight"><i></i><strong>{escape(title)}</strong><span>{escape(body)}</span></article>'
            for title, body in main_cards
        )
        validate_html = "".join(
            f'<article class="validate"><strong>{escape(title)}</strong><span>{escape(body)}</span></article>'
            for title, body in validate
        )
        body = f"""
        <section class="read-hero">
          <div class="pill">{escape(opp["company"])}</div>
          <h1>{escape(str(slide["title"]))}</h1>
          <p>{escape(str(slide["body"]))}</p>
        </section>
        <section class="meta">
          <article><small>Empresa</small><b>{escape(opp["company"])}</b></article>
          <article><small>Industria</small><b>{escape(opp["industry"])}</b></article>
          <article><small>País</small><b>{escape(opp["country"])}</b></article>
          <article><small>Estado</small><b>{escape(opp.get("preparation", {}).get("state", "Preparación"))}</b></article>
        </section>
        <section class="insights">{cards}</section>
        {validate_html}
        """
    elif layout == "cover":
        body = f"""
        <section class="cover2">
          <div class="cover-copy">
            <div class="cover-logo">{logo_img}</div>
            <h1>{escape(str(slide["title"]))}</h1>
            <p class="subtitle">{escape(str(slide["headline"]))}</p>
            <p>{escape(str(slide["body"]))}</p>
            <small>Presentación comercial 2026 · Confidencial · Conprospección</small>
          </div>
          <div class="cover-image" aria-hidden="true">
            <div class="desk-card"></div>
            <div class="yellow-mark"></div>
          </div>
        </section>
        """
    elif layout == "challenge":
        cards = "".join(
            f'<article class="challenge-card"><i></i><strong>{escape(title)}</strong><span>{escape(body)}</span></article>'
            for title, body in sections
        )
        body = f"""
        <section class="challenge-title">
          <i></i>
          <div><h1>{escape(str(slide["title"]))}</h1><p>{escape(str(slide["body"]))}</p></div>
        </section>
        <section class="challenge-grid">{cards}</section>
        {flow_html(slide.get("flow", []), "market-flow")}
        """
    elif layout == "services":
        service_cards = "".join(
            f'<article class="service2"><i>{idx}</i><h2>{escape(title)}</h2><p>{escape(body)}</p></article>'
            for idx, (title, body) in enumerate(sections, start=1)
        )
        body = f"""
        <section class="services-head">
          <i>CP</i>
          <div><h1>{escape(str(slide["title"]))}</h1><p>{escape(str(slide["headline"]))}</p></div>
        </section>
        <section class="services-two">{service_cards}</section>
        <section class="services-note">
          <strong>La estrategia define la base.</strong>
          <span>Primero decidimos a quién tiene sentido contactar y por qué. Después identificamos empresas, personas compradoras y datos de contacto para alimentar las campañas.</span>
        </section>
        """
    elif layout == "operation":
        method = "".join(
            f'<article class="orbit-card oc{idx}"><strong>{escape(title)}</strong><span>{escape(body)}</span></article>'
            for idx, (title, body) in enumerate(sections, start=1)
        )
        body = f"""
        <section class="operation-head">
          <h1>{escape(str(slide["title"]))}</h1>
          <p>{escape(str(slide["body"]))}</p>
        </section>
        <section class="orbit">
          <div class="orbit-center"><strong>Estrategia de segmentación</strong><span>Datos → campañas multicanal → seguimiento</span></div>
          {method}
        </section>
        {flow_html(slide.get("flow", []), "gold-flow2")}
        """
    elif layout == "next":
        steps = "".join(
            f'<article><b>{idx}</b><span>{escape(str(item))}</span></article>'
            for idx, item in enumerate(slide.get("flow", []), start=1)
        )
        receive = "".join(
            f'<article><strong>{escape(title)}</strong><span>{escape(body)}</span></article>'
            for title, body in sections
        )
        access = "".join(
            f'<a href="{escape(str(url))}" target="_blank" rel="noopener"><strong>{escape(str(label))}</strong><span>Acceso de revisión</span></a>'
            if url
            else f'<div><strong>{escape(str(label))}</strong><span>Pendiente de configurar</span></div>'
            for label, url in DEMO_SETTINGS["links"].items()
        )
        body = f"""
        <section class="next-title"><h1>{escape(str(slide["title"]))}</h1><p>{escape(str(slide["body"]))}</p></section>
        <section class="steps2">{steps}</section>
        <section class="next-two">
          <article><h2>Qué recibirás</h2>{receive}</article>
          <article><h2>Accesos para revisar</h2>{access}</article>
        </section>
        <p class="mini-note">La propuesta comercial se genera aparte del brochure comercial.</p>
        """
    else:
        cards = "".join(
            f'<article class="insight"><i></i><strong>{escape(title)}</strong><span>{escape(body)}</span></article>'
            for title, body in sections
        )
        body = f'<section class="read-hero"><h1>{escape(str(slide["title"]))}</h1><p>{escape(str(slide["body"]))}</p></section><section class="insights">{cards}</section>'

    return f"""
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700;800&family=Saira:wght@700;800;900&display=swap');
    :root {{ --paper:#FAFAF8; --ink:#171717; --muted:#666661; --line:#E2E0DA; --gold:#FFD700; --gold-soft:#FFF4B4; --shadow:0 16px 36px rgba(20,20,18,.08); }}
    * {{ box-sizing:border-box; }}
    html,body {{ margin:0; overflow:hidden; background:var(--paper); color:var(--ink); font-family:"IBM Plex Sans",Arial,sans-serif; }}
    .slide {{ width:1500px; height:800px; margin:0 auto; padding:16px 22px 18px; }}
    .topbar {{ align-items:center; background:#111; border-radius:8px; display:flex; justify-content:space-between; height:58px; padding:10px 20px; margin-bottom:14px; }}
    .brandmark {{ align-items:center; color:#fff; display:flex; gap:12px; font-family:Saira,"IBM Plex Sans",sans-serif; font-size:23px; font-weight:900; }}
    .brandmark img {{ display:block; max-height:34px; object-fit:contain; }}
    .brandmark span em {{ color:var(--gold); font-style:normal; }}
    .counter {{ color:#fff; font-size:12px; font-weight:900; letter-spacing:.08em; text-transform:uppercase; }}
    h1 {{ font-family:Saira,"IBM Plex Sans",sans-serif; font-size:42px; line-height:1.04; letter-spacing:0; margin:0 0 10px; }}
    h2 {{ font-family:Saira,"IBM Plex Sans",sans-serif; font-size:26px; line-height:1.08; margin:12px 0 10px; }}
    p {{ color:#33332F; font-size:16px; line-height:1.44; margin:0; }}
    .pill {{ background:var(--gold-soft); border:1px solid #EBC85B; border-radius:999px; display:inline-flex; font-size:11px; font-weight:900; margin-bottom:12px; padding:6px 10px; text-transform:uppercase; }}
    .read-hero,.challenge-title,.services-head,.operation-head,.next-title,.next-two>article {{ background:#fff; border:1px solid var(--line); border-radius:10px; box-shadow:var(--shadow); }}
    .read-hero {{ border-top:6px solid var(--gold); min-height:170px; padding:28px 36px; margin-bottom:12px; }}
    .read-hero p {{ font-size:17px; max-width:1320px; }}
    .meta {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:12px; }}
    .meta article {{ background:#fff; border:1px solid var(--line); border-radius:8px; min-height:68px; padding:14px 18px; }}
    .meta small {{ color:var(--muted); display:block; font-size:10px; font-weight:900; letter-spacing:.07em; text-transform:uppercase; }}
    .meta b {{ display:block; font-size:16px; margin-top:4px; }}
    .insights {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; }}
    .insight {{ background:#fff; border:1px solid var(--line); border-radius:10px; box-shadow:0 8px 20px rgba(20,20,18,.045); min-height:116px; padding:18px 18px 16px 70px; position:relative; }}
    .insight i,.challenge-card i {{ background:var(--gold-soft); border:1px solid #EBC85B; border-radius:999px; height:34px; left:18px; position:absolute; top:20px; width:34px; }}
    .insight strong,.challenge-card strong,.orbit-card strong {{ display:block; font-size:16px; line-height:1.18; margin-bottom:7px; }}
    .insight span,.challenge-card span,.orbit-card span {{ color:#44443F; display:block; font-size:13px; line-height:1.36; }}
    .validate {{ background:#fff; border:1px solid #EBC85B; border-radius:10px; margin-top:12px; padding:14px 18px; }}
    .validate strong {{ display:block; font-size:15px; margin-bottom:4px; }}
    .validate span {{ color:#44443F; font-size:13px; }}
    .cover2 {{ background:#fff; border:1px solid var(--line); border-radius:10px; box-shadow:var(--shadow); display:grid; grid-template-columns:.95fr 1.05fr; height:650px; overflow:hidden; }}
    .cover-copy {{ padding:58px 52px; }}
    .cover-logo img {{ max-height:48px; margin-bottom:48px; }}
    .cover-copy h1 {{ font-size:52px; max-width:620px; }}
    .cover-copy .subtitle {{ color:#696966; font-size:21px; margin-bottom:18px; }}
    .cover-copy small {{ color:#8A8A84; display:block; font-size:11px; font-weight:900; letter-spacing:.13em; margin-top:26px; text-transform:uppercase; }}
    .cover-image {{ background:linear-gradient(135deg,#151515,#3A3A3A); position:relative; overflow:hidden; }}
    .cover-image:before {{ background:radial-gradient(circle at 72% 35%,rgba(255,255,255,.22),transparent 32%); content:""; inset:0; position:absolute; }}
    .desk-card {{ border:1px solid rgba(255,255,255,.24); border-radius:14px; height:260px; left:26%; position:absolute; top:30%; transform:skewX(-12deg); width:420px; }}
    .yellow-mark {{ background:var(--gold); bottom:56px; height:18px; position:absolute; right:70px; transform:skewX(-24deg); width:120px; }}
    .challenge-title,.services-head,.operation-head,.next-title {{ align-items:center; display:flex; gap:20px; min-height:128px; padding:28px 34px; margin-bottom:18px; }}
    .challenge-title>i {{ background:#111; height:64px; width:5px; }}
    .challenge-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; }}
    .challenge-card {{ background:#F3F3F1; border:1px solid var(--line); min-height:190px; padding:72px 18px 18px; position:relative; }}
    .market-flow,.gold-flow2 {{ align-items:center; background:#111; color:#fff; display:flex; font-family:Saira,"IBM Plex Sans",sans-serif; font-size:20px; font-weight:900; gap:18px; justify-content:center; margin-top:24px; padding:18px; text-transform:uppercase; }}
    .gold-flow2 {{ background:var(--gold); color:#111; border-radius:6px; }}
    .market-flow span:not(:last-child):after,.gold-flow2 span:not(:last-child):after {{ content:" →"; margin-left:18px; }}
    .services-head>i {{ align-items:center; background:var(--gold); border-radius:999px; display:flex; flex:0 0 66px; font-family:Saira,"IBM Plex Sans",sans-serif; font-style:normal; font-weight:900; height:66px; justify-content:center; }}
    .services-two {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }}
    .service2 {{ background:#fff; border:1px solid var(--line); border-left:6px solid var(--gold); border-radius:10px; box-shadow:var(--shadow); min-height:285px; padding:34px; }}
    .service2 i {{ align-items:center; background:var(--gold); border-radius:999px; display:flex; font-style:normal; font-weight:900; height:54px; justify-content:center; margin-bottom:22px; width:54px; }}
    .service2 p {{ font-size:16px; }}
    .services-note {{ background:#fff; border:1px solid var(--line); border-radius:10px; margin-top:14px; padding:18px 22px; }}
    .services-note strong {{ display:block; font-size:17px; margin-bottom:5px; }}
    .services-note span {{ color:#44443F; font-size:14px; }}
    .operation-head {{ display:block; }}
    .orbit {{ height:420px; position:relative; }}
    .orbit-center {{ align-items:center; background:#111; border-radius:999px; color:#fff; display:flex; flex-direction:column; height:170px; justify-content:center; left:50%; padding:22px; position:absolute; text-align:center; top:50%; transform:translate(-50%,-50%); width:270px; }}
    .orbit-center strong {{ font-family:Saira,"IBM Plex Sans",sans-serif; font-size:22px; }}
    .orbit-center span {{ color:#DDD; font-size:13px; margin-top:6px; }}
    .orbit-card {{ background:#fff; border:1px solid var(--line); border-radius:10px; box-shadow:var(--shadow); min-height:132px; padding:18px; position:absolute; width:430px; }}
    .oc1 {{ left:40px; top:10px; }} .oc2 {{ right:40px; top:10px; }} .oc3 {{ left:40px; bottom:10px; }} .oc4 {{ right:40px; bottom:10px; }}
    .steps2 {{ display:grid; grid-template-columns:repeat(5,1fr); margin:10px 0 20px; }}
    .steps2 article {{ background:#fff; border:1px solid var(--line); min-height:124px; padding:18px 10px; text-align:center; }}
    .steps2 b {{ align-items:center; background:var(--gold); border-radius:999px; display:flex; font-size:23px; height:48px; justify-content:center; margin:0 auto 14px; width:48px; }}
    .steps2 span {{ font-size:15px; font-weight:900; }}
    .next-two {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }}
    .next-two>article {{ min-height:255px; padding:24px; }}
    .next-two article article,.next-two a,.next-two div {{ border-top:1px solid var(--line); color:var(--ink); display:block; padding:12px 0; text-decoration:none; }}
    .next-two strong {{ display:block; font-size:16px; }} .next-two span {{ color:var(--muted); display:block; font-size:13px; margin-top:4px; }}
    .mini-note {{ border:1px solid #EBC85B; border-radius:8px; color:#6B5E00; display:inline-block; font-size:12px; margin-top:12px; padding:8px 12px; }}
    .bottom {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin-top:14px; }}
    .bottom-link {{ align-items:center; background:#fff; border:1px solid #C9C9C4; border-radius:8px; color:var(--ink); display:flex; font-size:15px; font-weight:900; justify-content:center; min-height:54px; text-decoration:none; }}
    .bottom-link:hover {{ background:var(--gold); border-color:var(--gold); }} .bottom-link.pending {{ color:#777; flex-direction:column; }} .bottom-link small {{ font-size:10px; margin-top:2px; }}
  </style>
</head>
<body>
  <main class="slide">
    <header class="topbar">
      <div class="brandmark">{logo_img}<span>Conprospección<em>OS</em></span></div>
      <div class="counter">Presentación comercial · {slide_idx + 1} de {total}</div>
    </header>
    {body}
    <nav class="bottom">{links}</nav>
  </main>
</body>
</html>
    """


def _presentation_iframe_html_v5(opp: dict[str, Any], slide: dict[str, Any], slide_idx: int, total: int) -> str:
    layout = str(slide.get("layout", "analysis"))
    sections = [(str(title), str(body)) for title, body in slide.get("sections", [])]
    logo = _logo_data_uri()
    logo_img = f'<img src="{logo}" alt="Conprospección">' if logo else '<span class="logo-fallback">Conprospección</span>'
    link_items = []
    for label, url in DEMO_SETTINGS["links"].items():
        if label == "Brochure comercial":
            continue
        final_url = "/Comercial?asset=database_demo" if label == "Base de datos de ejemplo" and not url else str(url)
        link_items.append(
            f'<a class="bottom-link" href="{escape(final_url)}" target="_blank" rel="noopener">{escape(str(label))}</a>'
        )
    links = "".join(link_items)

    def flow_html(items: list[Any], class_name: str) -> str:
        return f'<div class="{class_name}">' + "".join(f"<span>{escape(str(item))}</span>" for item in items) + "</div>" if items else ""

    if layout == "analysis":
        main_cards = sections[:6]
        validate = sections[6:] or []
        cards = "".join(
            f"""
            <article class="analysis-card">
              <i></i>
              <div>
                <strong>{escape(title)}</strong>
                <span>{escape(body)}</span>
              </div>
            </article>
            """
            for title, body in main_cards
        )
        validate_html = "".join(
            f'<article class="validate-strip"><strong>{escape(title)}</strong><span>{escape(body)}</span></article>'
            for title, body in validate
        )
        body = f"""
        <section class="analysis-hero">
          <div class="pill">{escape(opp["company"])}</div>
          <h1>{escape(str(slide["title"]))}</h1>
          <p>{escape(str(slide["body"]))}</p>
        </section>
        <section class="client-meta">
          <article><small>Empresa</small><b>{escape(opp["company"])}</b></article>
          <article><small>Industria</small><b>{escape(opp["industry"])}</b></article>
          <article><small>País</small><b>{escape(opp["country"])}</b></article>
          <article><small>Estado</small><b>{escape(opp.get("preparation", {}).get("state", "Preparación"))}</b></article>
        </section>
        <section class="analysis-grid">{cards}</section>
        {validate_html}
        """
    elif layout == "cover":
        body = f"""
        <section class="cover-slide">
          <div class="cover-copy">
            <div class="logo-on-white">{logo_img}</div>
            <h1>{escape(str(slide["title"]))}</h1>
            <p class="subtitle">{escape(str(slide["headline"]))}</p>
            <p>{escape(str(slide["body"]))}</p>
            <small>Presentación comercial 2026 · Confidencial · Conprospección</small>
          </div>
          <div class="cover-visual">
            <div class="visual-mark"><span></span><span></span></div>
            <div class="visual-list">
              <strong>Estrategia</strong>
              <strong>Inteligencia comercial</strong>
              <strong>Activación multicanal</strong>
            </div>
            <div class="photo-line"></div>
          </div>
        </section>
        """
    elif layout == "challenge":
        cards = "".join(
            f"""
            <article class="challenge-card">
              <i>{idx}</i>
              <strong>{escape(title)}</strong>
              <span>{escape(body)}</span>
            </article>
            """
            for idx, (title, body) in enumerate(sections, start=1)
        )
        body = f"""
        <section class="headline-block">
          <i></i>
          <div>
            <h1>{escape(str(slide["title"]))}</h1>
            <p>{escape(str(slide["body"]))}</p>
          </div>
        </section>
        <section class="challenge-grid">{cards}</section>
        {flow_html(slide.get("flow", []), "black-flow")}
        """
    elif layout == "services":
        first_title, first_body = sections[0] if sections else ("Gestión de prospección", "")
        second_title, second_body = sections[1] if len(sections) > 1 else ("Inteligencia y bases", "")
        body = f"""
        <section class="services-layout">
          <div class="section-title">
            <i></i>
            <div>
              <h1>{escape(str(slide["title"]))}</h1>
              <small>{escape(str(slide["headline"]))}</small>
            </div>
          </div>
          <p class="services-intro">{escape(str(slide["body"]))}</p>
          <div class="services-cards">
            <article class="service-card selected">
              <div class="service-icon">●●</div>
              <span class="service-tag">Operamos</span>
              <h2>{escape(first_title)}</h2>
              <p>{escape(first_body)}</p>
              <b>Ejecución end-to-end</b>
            </article>
            <article class="service-card">
              <div class="service-icon">▰</div>
              <span class="service-tag">Entregamos</span>
              <h2>{escape(second_title)}</h2>
              <p>{escape(second_body)}</p>
              <b>Activos estratégicos</b>
            </article>
          </div>
          <div class="service-note">Ambas rutas convergen en un solo fin: <strong>generar oportunidades comerciales de alto valor.</strong></div>
        </section>
        """
    elif layout == "operation":
        method = "".join(
            f"""
            <article class="method-card m{idx}">
              <strong>{escape(title)}</strong>
              <span>{escape(body)}</span>
            </article>
            """
            for idx, (title, body) in enumerate(sections, start=1)
        )
        body = f"""
        <section class="operation-title">
          <h1>{escape(str(slide["title"]))}</h1>
          <p>{escape(str(slide["body"]))}</p>
        </section>
        <section class="method-map">
          <div class="method-center"><strong>Estrategia de segmentación</strong><span>Datos → campañas multicanal → seguimiento</span></div>
          {method}
        </section>
        {flow_html(slide.get("flow", []), "gold-flow")}
        """
    elif layout == "next":
        steps = "".join(
            f'<article><b>{idx}</b><span>{escape(str(item))}</span></article>'
            for idx, item in enumerate(slide.get("flow", []), start=1)
        )
        receive = "".join(
            f'<li><strong>{escape(title)}</strong><span>{escape(body)}</span></li>'
            for title, body in sections
        )
        body = f"""
        <section class="next-head">
          <h1>{escape(str(slide["title"]))}</h1>
          <p>{escape(str(slide["body"]))}</p>
        </section>
        <section class="next-steps">{steps}</section>
        <section class="next-content single">
          <article><h2>Qué recibirás</h2><ul>{receive}</ul></article>
        </section>
        <div class="proposal-note">La propuesta comercial se genera aparte del brochure comercial.</div>
        """
    else:
        cards = "".join(
            f'<article class="analysis-card"><i></i><div><strong>{escape(title)}</strong><span>{escape(body)}</span></div></article>'
            for title, body in sections
        )
        body = f'<section class="analysis-hero"><h1>{escape(str(slide["title"]))}</h1><p>{escape(str(slide["body"]))}</p></section><section class="analysis-grid">{cards}</section>'

    return f"""
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700;800&family=Saira:wght@700;800;900&display=swap');
    :root {{ --paper:#F7F6F3; --ink:#111111; --muted:#696966; --line:#DDDAD2; --soft:#FFFFFF; --gold:#FFD200; --gold-soft:#FFF1A7; --shadow:0 18px 42px rgba(17,17,17,.08); }}
    * {{ box-sizing:border-box; }}
    html,body {{ background:var(--paper); color:var(--ink); font-family:"IBM Plex Sans",Arial,sans-serif; height:100%; margin:0; overflow:hidden; }}
    .slide {{ height:675px; margin:0 auto; max-width:1320px; padding:8px 18px 10px; width:100%; }}
    .topbar {{ align-items:center; background:#101010; border-radius:7px; display:flex; height:46px; justify-content:space-between; margin-bottom:8px; padding:8px 18px; }}
    .brand {{ align-items:center; display:flex; gap:10px; height:32px; }}
    .brand:after {{ color:#fff; content:"Conprospección"; font-family:Saira,"IBM Plex Sans",sans-serif; font-size:20px; font-weight:900; line-height:1; }}
    .brand img {{ background:#fff; border-radius:4px; display:block; height:26px; max-width:120px; object-fit:contain; padding:3px 6px; width:auto; }}
    .brand .logo-fallback {{ color:#fff; font-family:Saira,"IBM Plex Sans",sans-serif; font-size:20px; font-weight:900; }}
    .counter {{ color:#fff; font-size:11px; font-weight:900; letter-spacing:.08em; text-transform:uppercase; }}
    h1 {{ font-family:Saira,"IBM Plex Sans",sans-serif; font-size:42px; letter-spacing:0; line-height:1.02; margin:0 0 9px; }}
    h2 {{ font-family:Saira,"IBM Plex Sans",sans-serif; font-size:24px; letter-spacing:0; line-height:1.06; margin:0 0 12px; }}
    p {{ color:#282824; font-size:15px; line-height:1.42; margin:0; }}
    .pill {{ background:var(--gold-soft); border:1px solid #E2BF36; border-radius:999px; display:inline-flex; font-size:10px; font-weight:900; margin-bottom:10px; padding:6px 10px; text-transform:uppercase; }}
    .bottom {{ display:grid; gap:12px; grid-template-columns:repeat(2,1fr); margin-top:8px; }}
    .bottom-link {{ align-items:center; background:#fff; border:1px solid #C9C6BE; border-radius:7px; color:var(--ink); display:flex; font-size:14px; font-weight:900; justify-content:center; min-height:39px; text-decoration:none; }}
    .bottom-link:hover {{ background:var(--gold); border-color:var(--gold); }}
    .bottom-link.pending {{ color:#777; flex-direction:column; }}
    .bottom-link small {{ font-size:9px; line-height:1; margin-top:3px; }}

    .analysis-hero,.headline-block,.operation-title,.next-head {{ background:#fff; border:1px solid var(--line); border-radius:9px; box-shadow:var(--shadow); }}
    .analysis-hero {{ border-top:5px solid var(--gold); min-height:138px; padding:20px 30px; }}
    .analysis-hero p {{ font-size:16px; max-width:1170px; }}
    .client-meta {{ display:grid; gap:10px; grid-template-columns:repeat(4,1fr); margin-top:10px; }}
    .client-meta article {{ background:#fff; border:1px solid var(--line); border-radius:8px; min-height:52px; padding:10px 14px; }}
    .client-meta small {{ color:var(--muted); display:block; font-size:9px; font-weight:900; letter-spacing:.08em; text-transform:uppercase; }}
    .client-meta b {{ display:block; font-size:15px; margin-top:3px; }}
    .analysis-grid {{ display:grid; gap:10px; grid-template-columns:repeat(3,1fr); margin-top:10px; }}
    .analysis-card {{ align-items:flex-start; background:#fff; border:1px solid var(--line); border-radius:9px; display:grid; gap:12px; grid-template-columns:36px 1fr; min-height:86px; padding:13px; }}
    .analysis-card i {{ background:var(--gold-soft); border:1px solid #E2BF36; border-radius:999px; height:28px; width:28px; }}
    .analysis-card strong,.challenge-card strong,.method-card strong {{ display:block; font-size:14px; line-height:1.15; margin-bottom:5px; }}
    .analysis-card span,.challenge-card span,.method-card span {{ color:#3D3D38; display:block; font-size:12px; line-height:1.34; }}
    .validate-strip {{ background:#fff; border:1px solid #E2BF36; border-radius:8px; margin-top:10px; padding:12px 14px; }}
    .validate-strip strong {{ display:block; font-size:14px; margin-bottom:4px; }}
    .validate-strip span {{ color:#3D3D38; font-size:12px; }}

    .cover-slide {{ background:#fff; border:1px solid var(--line); border-radius:9px; box-shadow:var(--shadow); display:grid; grid-template-columns:1fr 1fr; height:542px; overflow:hidden; }}
    .cover-copy {{ padding:54px 46px; }}
    .logo-on-white img {{ display:block; max-height:48px; max-width:190px; object-fit:contain; }}
    .logo-fallback {{ color:#111; font-family:Saira; font-size:22px; font-weight:900; }}
    .cover-copy h1 {{ font-size:48px; margin-top:42px; max-width:570px; }}
    .cover-copy .subtitle {{ color:#686862; font-size:20px; margin-bottom:18px; }}
    .cover-copy small {{ color:#83837C; display:block; font-size:10px; font-weight:900; letter-spacing:.13em; margin-top:25px; text-transform:uppercase; }}
    .cover-visual {{ align-items:center; background:#202020; display:flex; flex-direction:column; justify-content:center; min-height:100%; position:relative; }}
    .cover-visual:before {{ background:linear-gradient(120deg,rgba(255,210,0,.14),transparent 42%); content:""; inset:0; position:absolute; }}
    .visual-mark {{ height:108px; margin-bottom:34px; position:relative; width:150px; z-index:1; }}
    .visual-mark span {{ display:block; height:32px; position:absolute; transform:skewX(-25deg); width:92px; }}
    .visual-mark span:first-child {{ background:#fff; left:18px; top:18px; }}
    .visual-mark span:last-child {{ background:var(--gold); left:42px; top:58px; }}
    .visual-list {{ display:grid; gap:14px; position:relative; width:360px; z-index:1; }}
    .visual-list strong {{ border:1px solid rgba(255,210,0,.8); border-radius:8px; color:#fff; font-family:Saira,"IBM Plex Sans",sans-serif; font-size:24px; padding:17px 24px; }}
    .photo-line {{ background:var(--gold); bottom:50px; height:16px; position:absolute; right:62px; transform:skewX(-24deg); width:116px; }}

    .headline-block {{ align-items:flex-start; display:flex; gap:18px; min-height:112px; padding:24px 32px; }}
    .headline-block>i {{ background:#111; flex:0 0 4px; height:58px; margin-top:2px; }}
    .challenge-grid {{ display:grid; gap:14px; grid-template-columns:repeat(4,1fr); margin-top:18px; }}
    .challenge-card {{ background:#F0F0EE; border:1px solid var(--line); min-height:158px; padding:20px 18px 16px; }}
    .challenge-card i {{ align-items:center; background:#111; border-radius:999px; color:#fff; display:flex; font-style:normal; font-weight:900; height:28px; justify-content:center; margin-bottom:18px; width:28px; }}
    .black-flow {{ align-items:center; background:#101010; color:#fff; display:flex; font-family:Saira,"IBM Plex Sans",sans-serif; font-size:20px; font-weight:900; gap:16px; justify-content:center; margin-top:22px; min-height:58px; text-transform:uppercase; }}
    .black-flow span:not(:last-child):after {{ content:"→"; margin-left:16px; }}

    .services-layout {{ background:#fff; border:1px solid var(--line); border-radius:10px; box-shadow:var(--shadow); height:542px; padding:30px 42px 22px; }}
    .section-title {{ align-items:flex-start; display:flex; gap:18px; }}
    .section-title i {{ background:#111; display:block; height:52px; width:4px; }}
    .section-title small {{ color:#777771; font-size:13px; }}
    .services-intro {{ font-size:16px; margin:20px 0 22px; max-width:900px; }}
    .services-cards {{ display:grid; gap:24px; grid-template-columns:1fr 1fr; }}
    .service-card {{ background:#fff; border:1px solid var(--line); min-height:220px; padding:24px 30px; position:relative; }}
    .service-card.selected {{ border-left:6px solid var(--gold); box-shadow:0 16px 34px rgba(17,17,17,.08); }}
    .service-icon {{ align-items:center; background:var(--gold); border-radius:999px; color:#101010; display:flex; font-size:18px; font-weight:900; height:50px; justify-content:center; letter-spacing:-5px; margin-bottom:24px; width:50px; }}
    .service-tag {{ background:#111821; color:#fff; font-size:10px; font-weight:900; letter-spacing:.08em; padding:7px 10px; position:absolute; right:30px; text-transform:uppercase; top:28px; }}
    .service-card p {{ color:#42423D; font-size:15px; max-width:520px; }}
    .service-card b {{ color:#7B7B75; display:block; font-size:11px; letter-spacing:.06em; margin-top:14px; text-transform:uppercase; }}
    .service-note {{ border-top:1px solid var(--line); color:#696966; font-size:12px; font-style:italic; margin-top:24px; padding-top:13px; text-align:center; }}

    .operation-title {{ min-height:104px; padding:22px 30px; }}
    .method-map {{ height:348px; margin:12px 34px 0; position:relative; }}
    .method-center {{ align-items:center; background:#111; border-radius:999px; color:#fff; display:flex; flex-direction:column; height:150px; justify-content:center; left:50%; padding:20px; position:absolute; text-align:center; top:50%; transform:translate(-50%,-50%); width:260px; }}
    .method-center strong {{ font-family:Saira,"IBM Plex Sans",sans-serif; font-size:22px; line-height:1.12; }}
    .method-center span {{ color:#eee; font-size:12px; margin-top:8px; }}
    .method-card {{ background:#fff; border:1px solid var(--line); border-radius:8px; box-shadow:0 18px 42px rgba(17,17,17,.08); min-height:104px; padding:15px; position:absolute; width:360px; }}
    .m1 {{ left:0; top:6px; }} .m2 {{ right:0; top:6px; }} .m3 {{ bottom:6px; left:0; }} .m4 {{ bottom:6px; right:0; }}
    .gold-flow {{ align-items:center; background:var(--gold); border-radius:6px; color:#111; display:flex; font-family:Saira,"IBM Plex Sans",sans-serif; font-size:17px; font-weight:900; gap:13px; justify-content:center; min-height:48px; text-transform:uppercase; }}
    .gold-flow span:not(:last-child):after {{ content:"→"; margin-left:13px; }}

    .next-head {{ align-items:center; display:grid; gap:34px; grid-template-columns:.8fr 1fr; min-height:112px; padding:24px 32px; }}
    .next-steps {{ display:grid; grid-template-columns:repeat(5,1fr); margin:14px 0; }}
    .next-steps article {{ background:#fff; border:1px solid var(--line); min-height:92px; padding:13px 8px; text-align:center; }}
    .next-steps b {{ align-items:center; background:var(--gold); border-radius:999px; display:flex; font-size:21px; height:44px; justify-content:center; margin:0 auto 12px; width:44px; }}
    .next-steps span {{ display:block; font-size:14px; font-weight:900; }}
    .next-content {{ display:grid; gap:18px; grid-template-columns:1fr 1fr; }}
    .next-content.single {{ grid-template-columns:1fr; }}
    .next-content>article {{ background:#fff; border:1px solid var(--line); border-radius:9px; min-height:225px; padding:22px; }}
    .next-content ul {{ list-style:none; margin:8px 0 0; padding:0; }}
    .next-content li,.access-list a,.access-list div {{ border-top:1px solid var(--line); color:#111; display:block; min-height:48px; padding:10px 0; position:relative; text-decoration:none; }}
    .next-content li strong,.access-list strong {{ display:block; font-size:14px; }}
    .next-content li span,.access-list span {{ color:#696966; display:block; font-size:12px; margin-top:3px; }}
    .access-list i {{ align-items:center; background:var(--gold); border-radius:999px; display:flex; font-style:normal; font-weight:900; height:24px; justify-content:center; position:absolute; right:0; top:14px; width:24px; }}
    .proposal-note {{ border:1px solid #E2BF36; border-radius:7px; color:#6F6000; display:inline-flex; font-size:12px; margin-top:10px; padding:8px 12px; }}
  </style>
</head>
<body>
  <main class="slide">
    <header class="topbar">
      <div class="brand">{logo_img}</div>
      <div class="counter">Presentación comercial · {slide_idx + 1} de {total}</div>
    </header>
    {body}
    <nav class="bottom">{links}</nav>
  </main>
</body>
</html>
    """


def render_presentation_mode() -> None:
    opp = _current_opp()
    slides = _presentation_slides(opp)
    slide_idx = max(0, min(st.session_state.get("commercial_slide", 0), len(slides) - 1))
    slide = slides[slide_idx]
    top_left, spacer, prev_col, next_col = st.columns([1.2, 5, 0.42, 0.42])
    with top_left:
        if st.button("Salir de presentacion", use_container_width=False):
            st.session_state["commercial_view"] = "opportunities"
            st.session_state["commercial_panel_open"] = True
            st.session_state["commercial_tab"] = st.session_state.get("commercial_prev_tab", "Resumen")
            st.rerun()
    with spacer:
        st.markdown("", unsafe_allow_html=True)
    with prev_col:
        if st.button("←", use_container_width=True, disabled=slide_idx == 0, help="Lamina anterior"):
            st.session_state["commercial_slide"] = slide_idx - 1
            st.rerun()
    with next_col:
        if st.button("→", type="primary", use_container_width=True, disabled=slide_idx == len(slides) - 1, help="Lamina siguiente"):
            st.session_state["commercial_slide"] = slide_idx + 1
            st.rerun()
    components.html(
        _presentation_iframe_html_v5(opp, slide, slide_idx, len(slides)),
        height=690,
        scrolling=False,
    )


def render_proposals() -> None:
    if st.button("← Volver a Comercial", use_container_width=False):
        _set_view("hub")
    st.markdown("## Propuestas comerciales")
    st.caption("Consolidado general. Abrir propuesta abre el panel derecho de la oportunidad en la tab Propuesta.")
    status_filter = st.selectbox("Estado", ["Todos", "Borrador", "Enviada", "Aceptada", "Rechazada", "Vencida", "En seguimiento"])
    rows = [row for row in _flatten_proposals() if status_filter == "Todos" or row["status"] == status_filter]
    table_rows = [
        {
            "Empresa": row["company"],
            "Contacto": row["contact"],
            "Version": row["version"],
            "Setup": money(row["setup_amount"]),
            "Mensualidad": money(row["monthly_amount"]),
            "Total": money(row["total_amount"]),
            "Margen": f'{row["expected_margin"]}%',
            "Estado": row["status"],
            "Envio": row["sent_at"] or "Pendiente",
            "Vigencia": row["valid_until"],
            "Proximo seguimiento": row["next_followup"],
        }
        for row in rows
    ]
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
    st.markdown("#### Acciones")
    for row in rows:
        c1, c2, c3 = st.columns([2, 1, 1])
        c1.markdown(f"**{row['company']}** - {row['version']}")
        with c2:
            if st.button("Abrir propuesta", key=f"prop_tab_{row['id']}", use_container_width=True):
                _open_panel(row["opportunity_id"], "Propuesta", "proposals")
        with c3:
            if st.button("Ver oportunidad", key=f"opp_tab_{row['id']}", use_container_width=True):
                _open_panel(row["opportunity_id"], "Resumen", "proposals")
    if st.session_state.get("commercial_panel_open"):
        render_opportunity_panel(_current_opp())


def render_settings() -> None:
    if st.button("← Volver a Comercial", use_container_width=False):
        _set_view("hub")
    st.markdown("## Configuracion Comercial")
    st.caption("Vista demo local. Los cambios todavia no se guardan en Supabase.")
    tab = st.radio(
        "Configuracion",
        ["Enlaces", "Costos", "Score", "Seguimientos", "Plantillas"],
        key="commercial_config_tab",
        horizontal=True,
    )
    if tab == "Enlaces":
        panel("Enlaces y demos configurables", "Cada demo debe tener su propio destino. Si falta, se muestra pendiente.")
        for label, url in DEMO_SETTINGS["links"].items():
            st.text_input(label, value=url if url and "conprospeccion.com" not in url else "Demo pendiente de configuracion", key=f"setting_link_{label}")
    elif tab == "Costos":
        st.dataframe(pd.DataFrame({"Categoria": DEMO_SETTINGS["cost_categories"]}), use_container_width=True, hide_index=True)
    elif tab == "Score":
        st.dataframe(pd.DataFrame([{"Criterio": k, "Peso": v} for k, v in DEMO_SETTINGS["score_weights"].items()]), use_container_width=True, hide_index=True)
    elif tab == "Seguimientos":
        st.dataframe(pd.DataFrame({"Secuencia": DEMO_SETTINGS["defaults"]["followups"]}), use_container_width=True, hide_index=True)
    else:
        st.text_area("Plantilla correo", value="Hola {contacto}, te comparto la propuesta para {empresa}.", height=120)
        st.text_area("Plantilla propuesta", value="Resumen, mercado, alcance, inversion y proximos pasos.", height=120)


def render_sidebar_shell() -> None:
    with st.sidebar:
        st.markdown("### COMERCIAL")
        if st.button("Portada Comercial", use_container_width=True):
            _set_view("hub")
        if st.button("Oportunidades", use_container_width=True):
            _set_view("opportunities")
        if st.button("Propuestas", use_container_width=True):
            _set_view("proposals")
        if st.button("Configuracion", use_container_width=True):
            _set_view("settings")


_init_state()
if st.query_params.get("asset") == "database_demo":
    render_database_demo_asset()
    st.stop()

presentation_mode = st.session_state.get("commercial_view") == "presentation"
_inject_layout_css(presentation_mode)

if not presentation_mode:
    render_sidebar_shell()

view = st.session_state.get("commercial_view", "hub")
if view == "presentation":
    render_presentation_mode()
elif view == "opportunities":
    render_opportunities()
elif view == "proposals":
    render_proposals()
elif view == "settings":
    render_settings()
else:
    render_hub()

if not presentation_mode:
    render_master_user_sidebar()
