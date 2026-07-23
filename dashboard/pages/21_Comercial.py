"""Modulo Comercial interno de ConprospeccionOS.

Implementacion visual/funcional inicial con datos demo locales. Las
integraciones reales (Supabase, IA, Gmail, Fathom/Granola y PDF) quedan
separadas para fases posteriores.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

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
      background:#333333;
      color:#fff;
      border-radius:14px;
      min-height:760px;
      padding:28px 34px;
      display:flex;
      flex-direction:column;
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
      gap:42px;
      grid-template-columns:1fr .9fr;
    }
    .cp-presentation-main h1 {
      color:#FFD700;
      font-family:Saira,"IBM Plex Sans",sans-serif;
      font-size:48px;
      line-height:1.05;
      margin:0 0 16px;
    }
    .cp-presentation-main p {
      color:#F4F4F2;
      font-size:18px;
      line-height:1.55;
    }
    .cp-white-card {
      background:#fff;
      border:1px solid #EDECEA;
      border-radius:10px;
      color:#1A1A1A;
      padding:22px;
    }
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
      .cp-presentation-main, .cp-config-grid, .cp-section-grid { grid-template-columns:1fr; }
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
    </style>
    """
    st.markdown(sidebar_css + (presentation_css if presentation_mode else ""), unsafe_allow_html=True)


def _init_state() -> None:
    if "commercial_opportunities" not in st.session_state:
        st.session_state["commercial_opportunities"] = copy.deepcopy(DEMO_OPPORTUNITIES)
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
    return [
        {
            "title": "Lo que investigamos antes de reunirnos",
            "headline": f"{opp['company']} - {opp['industry']}",
            "body": opp.get("preparation", {}).get("content", "Evaluacion previa pendiente."),
            "sections": [
                ("Contacto", f"{opp['contact']} - {opp['role']}"),
                ("Pais", opp["country"]),
                ("Proximo paso", opp["next_followup"]),
            ],
        },
        *STANDARD_PRESENTATION,
    ]


def render_presentation_mode() -> None:
    opp = _current_opp()
    slides = _presentation_slides(opp)
    slide_idx = max(0, min(st.session_state.get("commercial_slide", 0), len(slides) - 1))
    slide = slides[slide_idx]
    st.markdown('<div class="cp-presentation-shell">', unsafe_allow_html=True)
    top_left, top_right = st.columns([1, 1])
    with top_left:
        if st.button("Salir de presentacion", use_container_width=False):
            st.session_state["commercial_view"] = "opportunities"
            st.session_state["commercial_panel_open"] = True
            st.session_state["commercial_tab"] = st.session_state.get("commercial_prev_tab", "Resumen")
            st.rerun()
    with top_right:
        st.markdown(f"<div style='text-align:right;color:#EDECEA'>{slide_idx + 1} de {len(slides)}</div>", unsafe_allow_html=True)
    left, right = st.columns([1.05, 0.95])
    with left:
        st.markdown(
            f"<h1 style='color:#FFD700;font-family:Saira,sans-serif;font-size:44px;line-height:1.05'>{slide['title']}</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(f"<p style='color:#F4F4F2;font-size:18px;line-height:1.55'>{slide['body']}</p>", unsafe_allow_html=True)
    with right:
        st.markdown('<div class="cp-white-card">', unsafe_allow_html=True)
        st.markdown(f"### {slide['headline']}")
        for title, body in slide.get("sections", []):
            st.markdown(f"**{title}**  \n{body}")
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("#### Accesos demo")
    demo_cols = st.columns(4)
    for idx, (label, url) in enumerate(DEMO_SETTINGS["links"].items()):
        with demo_cols[idx % 4]:
            if url and "conprospeccion.com" not in url:
                st.link_button(label, url, use_container_width=True)
            else:
                if st.button(label, use_container_width=True, key=f"presentation_demo_{label}"):
                    st.toast("Demo pendiente de configuracion.")
    prev_col, next_col = st.columns(2)
    with prev_col:
        if st.button("Anterior", use_container_width=True, disabled=slide_idx == 0):
            st.session_state["commercial_slide"] = slide_idx - 1
            st.rerun()
    with next_col:
        if st.button("Siguiente", type="primary", use_container_width=True, disabled=slide_idx == len(slides) - 1):
            st.session_state["commercial_slide"] = slide_idx + 1
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


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
