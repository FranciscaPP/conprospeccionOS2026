"""Tablero interno de pendientes semanales."""
from __future__ import annotations

import html
import json
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from master_auth import get_current_user, render_master_user_sidebar, require_master_auth
from shared.config import supabase_key, supabase_url

st.set_page_config(page_title="Work and Project Management - ConprospeccionOS", layout="wide", page_icon="")
if not require_master_auth():
    st.stop()

SB_URL = supabase_url()
SB_KEY = supabase_key()
SB_HEADERS = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"}
SB_WRITE_HEADERS = {**SB_HEADERS, "Content-Type": "application/json", "Prefer": "return=representation"}

LOCAL_STORE = ROOT / "dashboard" / "data" / "pendientes_semanales_local.json"
CP_MARK_PATH = DASHBOARD_DIR / "assets" / "cp_mark_dark.png"

STATUSES = ["Pendiente", "En proceso", "Terminado"]
OWNERS = ["Yanina", "Francisca"]
PRIORITIES = ["Alta", "Media", "Baja"]

STATUS_META = {
    "Pendiente": {"color": "#A66A00", "bg": "#FFF3D8", "border": "#F0D28D"},
    "En proceso": {"color": "#2563EB", "bg": "#EAF1FE", "border": "#BFD2FB"},
    "Terminado": {"color": "#15803D", "bg": "#EAF6EF", "border": "#BFE6CC"},
}

PRIORITY_META = {
    "Alta": {"color": "#C92B2B", "bg": "#FDECEA", "border": "#F3B7B3"},
    "Media": {"color": "#A66A00", "bg": "#FFF3D8", "border": "#F0D28D"},
    "Baja": {"color": "#15803D", "bg": "#EAF6EF", "border": "#BFE6CC"},
}


def _today() -> date:
    return date.today()


def _week_bounds(base: date) -> tuple[date, date]:
    start = base - timedelta(days=base.weekday())
    return start, start + timedelta(days=6)


def _date_or_none(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return None


def _fmt_date(value: Any) -> str:
    parsed = _date_or_none(value)
    return parsed.strftime("%d/%m/%Y") if parsed else "Sin fecha"


def _iso_date(value: Any) -> str | None:
    if isinstance(value, date):
        return value.isoformat()
    parsed = _date_or_none(value)
    return parsed.isoformat() if parsed else None


def _esc(value: Any) -> str:
    return html.escape(str(value or "").strip())


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _asset_data_uri(path: Path, mime: str = "image/png") -> str:
    try:
        import base64

        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    except Exception:
        return ""
    return f"data:{mime};base64,{encoded}"


def _read_local_tasks() -> list[dict[str, Any]]:
    try:
        if LOCAL_STORE.exists():
            data = json.loads(LOCAL_STORE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
    except Exception:
        return []
    return []


def _write_local_tasks(tasks: list[dict[str, Any]]) -> None:
    LOCAL_STORE.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_STORE.write_text(
        json.dumps(tasks, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _normalize_task(task: dict[str, Any]) -> dict[str, Any]:
    clean = dict(task)
    clean["id"] = str(clean.get("id") or uuid.uuid4())
    clean["title"] = str(clean.get("title") or "").strip()
    clean["description"] = str(clean.get("description") or "").strip()
    clean["reference_url"] = str(clean.get("reference_url") or "").strip()
    clean["owner"] = clean.get("owner") if clean.get("owner") in OWNERS else "Yanina"
    clean["status"] = clean.get("status") if clean.get("status") in STATUSES else "Pendiente"
    clean["priority"] = clean.get("priority") if clean.get("priority") in PRIORITIES else "Media"
    clean["due_date"] = _iso_date(clean.get("due_date"))
    clean["week_start"] = _iso_date(clean.get("week_start")) or _week_bounds(_today())[0].isoformat()
    clean["created_by"] = str(clean.get("created_by") or "").strip()
    clean["created_at"] = str(clean.get("created_at") or _now_iso())
    clean["updated_at"] = str(clean.get("updated_at") or clean["created_at"])
    clean["completed_at"] = clean.get("completed_at")
    clean["is_archived"] = bool(clean.get("is_archived", False))
    return clean


def _sb_available() -> bool:
    return bool(SB_URL and SB_KEY)


def _fetch_supabase_tasks() -> tuple[list[dict[str, Any]], str]:
    if not _sb_available():
        return [], "local"
    try:
        query = (
            "select=*&is_archived=eq.false"
            "&order=status.asc&order=due_date.asc.nullslast&order=created_at.desc"
        )
        response = requests.get(
            f"{SB_URL}/rest/v1/internal_tasks?{query}",
            headers=SB_HEADERS,
            timeout=10,
        )
        if response.ok:
            return [_normalize_task(row) for row in response.json()], "supabase"
    except Exception:
        pass
    return [], "local"


def load_tasks() -> tuple[list[dict[str, Any]], str]:
    tasks, source = _fetch_supabase_tasks()
    if source == "supabase":
        return tasks, source
    return [_normalize_task(row) for row in _read_local_tasks()], "local"


def create_task(payload: dict[str, Any], source: str) -> bool:
    task = _normalize_task(payload)
    if source == "supabase" and _sb_available():
        try:
            response = requests.post(
                f"{SB_URL}/rest/v1/internal_tasks",
                headers=SB_WRITE_HEADERS,
                json=task,
                timeout=10,
            )
            if response.ok:
                return True
        except Exception:
            pass

    tasks = _read_local_tasks()
    tasks.append(task)
    _write_local_tasks([_normalize_task(row) for row in tasks])
    return True


def update_task(task_id: str, changes: dict[str, Any], source: str) -> bool:
    clean_changes = dict(changes)
    clean_changes["updated_at"] = _now_iso()
    if clean_changes.get("status") == "Terminado":
        clean_changes["completed_at"] = _now_iso()
    elif clean_changes.get("status") in {"Pendiente", "En proceso"}:
        clean_changes["completed_at"] = None

    if source == "supabase" and _sb_available():
        try:
            response = requests.patch(
                f"{SB_URL}/rest/v1/internal_tasks?id=eq.{task_id}",
                headers=SB_WRITE_HEADERS,
                json=clean_changes,
                timeout=10,
            )
            if response.ok:
                return True
        except Exception:
            pass

    tasks = []
    for row in _read_local_tasks():
        if str(row.get("id")) == str(task_id):
            row.update(clean_changes)
        tasks.append(_normalize_task(row))
    _write_local_tasks(tasks)
    return True


def _task_week_label(task: dict[str, Any]) -> str:
    start = _date_or_none(task.get("week_start")) or _week_bounds(_today())[0]
    end = start + timedelta(days=6)
    return f"{start.strftime('%d/%m')} - {end.strftime('%d/%m')}"


def _filter_tasks(tasks: list[dict[str, Any]], owner: str, week_start: date, include_done: bool) -> list[dict[str, Any]]:
    filtered = []
    for task in tasks:
        task_week = _date_or_none(task.get("week_start")) or _week_bounds(_today())[0]
        if task_week != week_start:
            continue
        if owner != "Todas" and task.get("owner") != owner:
            continue
        if not include_done and task.get("status") == "Terminado":
            continue
        filtered.append(task)
    priority_order = {"Alta": 0, "Media": 1, "Baja": 2}
    status_order = {"Pendiente": 0, "En proceso": 1, "Terminado": 2}
    return sorted(
        filtered,
        key=lambda task: (
            status_order.get(task.get("status"), 9),
            priority_order.get(task.get("priority"), 9),
            _date_or_none(task.get("due_date")) or date.max,
            str(task.get("title") or "").lower(),
        ),
    )


def _summary_card(label: str, value: int, color: str, bg: str) -> None:
    st.markdown(
        f"""
        <div class="cp-metric" style="background:{bg};border-color:{color}22">
          <div class="cp-metric-label">{_esc(label)}</div>
          <div class="cp-metric-value" style="color:{color}">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _open_editor(task_id: str) -> None:
    st.session_state["selected_task_id"] = task_id


def _selected_task(tasks: list[dict[str, Any]]) -> dict[str, Any] | None:
    selected_id = st.session_state.get("selected_task_id")
    for task in tasks:
        if str(task.get("id")) == str(selected_id):
            return task
    return None


def _render_task_card(task: dict[str, Any], source: str) -> None:
    priority = PRIORITY_META.get(task["priority"], PRIORITY_META["Media"])
    status = STATUS_META.get(task["status"], STATUS_META["Pendiente"])
    due = _date_or_none(task.get("due_date"))
    overdue = bool(due and due < _today() and task["status"] != "Terminado")
    due_text = "Vencida" if overdue else _fmt_date(task.get("due_date"))
    ref = task.get("reference_url")
    selected = str(st.session_state.get("selected_task_id") or "") == str(task["id"])
    selected_cls = " selected-task" if selected else ""
    reference_html = f'<span>Referencia: <b>{_esc(ref)}</b></span>' if ref else ""

    st.markdown(
        f"""
        <div class="task-card{selected_cls}">
          <div class="task-topline">
            <span class="pill" style="color:{priority['color']};background:{priority['bg']};border-color:{priority['border']}">
              {_esc(task['priority'])}
            </span>
            <span class="pill" style="color:{status['color']};background:{status['bg']};border-color:{status['border']}">
              {_esc(task['status'])}
            </span>
          </div>
          <div class="task-title">{_esc(task['title'])}</div>
          <div class="task-desc">{_esc(task.get('description') or 'Sin detalle adicional.')}</div>
          <div class="task-meta">
            <span>Responsable: <b>{_esc(task['owner'])}</b></span>
            <span class="{ 'overdue' if overdue else '' }">Fecha limite: <b>{_esc(due_text)}</b></span>
            <span>Semana: <b>{_esc(_task_week_label(task))}</b></span>
            {reference_html}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    states = [state for state in STATUSES if state != task["status"]]
    cols = st.columns([1.35, *([1] * len(states))])
    with cols[0]:
        if st.button("Abrir / editar", key=f"edit_{task['id']}", use_container_width=True):
            _open_editor(task["id"])
            st.rerun()
    for index, next_state in enumerate(states):
        with cols[index + 1]:
            if st.button(next_state, key=f"move_{task['id']}_{next_state}", use_container_width=True):
                update_task(task["id"], {"status": next_state}, source)
                st.rerun()


def _render_editor(task: dict[str, Any], source: str) -> None:
    st.markdown(
        """
        <section class="cp-card">
          <div class="cp-section-head">
            <div><h2>Editar tarea</h2><p>Actualizar detalle, responsable, prioridad, estado, fecha y referencia.</p></div>
          </div>
          <div class="cp-form-shell compact-form">
        """,
        unsafe_allow_html=True,
    )
    with st.form(f"edit_task_form_{task['id']}", clear_on_submit=False):
        e1, e2, e3 = st.columns([2.4, .85, .85])
        with e1:
            edit_title = st.text_input("Tarea", value=task["title"], key=f"title_{task['id']}")
        with e2:
            edit_owner = st.selectbox(
                "Asignada a",
                OWNERS,
                index=OWNERS.index(task["owner"]) if task["owner"] in OWNERS else 0,
                key=f"owner_{task['id']}",
            )
        with e3:
            edit_priority = st.selectbox(
                "Prioridad",
                PRIORITIES,
                index=PRIORITIES.index(task["priority"]) if task["priority"] in PRIORITIES else 1,
                key=f"priority_{task['id']}",
            )

        e4, e5, e6 = st.columns([.9, .9, 2.3])
        with e4:
            edit_status = st.selectbox(
                "Estado",
                STATUSES,
                index=STATUSES.index(task["status"]) if task["status"] in STATUSES else 0,
                key=f"status_{task['id']}",
            )
        with e5:
            edit_due = st.date_input(
                "Fecha limite",
                value=_date_or_none(task.get("due_date")) or _today(),
                key=f"due_{task['id']}",
            )
        with e6:
            edit_ref = st.text_input(
                "Link / archivo",
                value=task.get("reference_url", ""),
                placeholder="URL, carpeta o documento de referencia",
                key=f"ref_{task['id']}",
            )

        edit_description = st.text_area(
            "Detalle",
            value=task.get("description", ""),
            height=70,
            key=f"description_{task['id']}",
        )
        save_col, close_col = st.columns([1, 1])
        with save_col:
            saved = st.form_submit_button("Guardar cambios", use_container_width=True, type="primary")
        with close_col:
            closed = st.form_submit_button("Cerrar edicion", use_container_width=True)

        if saved:
            if not edit_title.strip():
                st.warning("La tarea necesita un nombre.")
            else:
                update_task(
                    task["id"],
                    {
                        "title": edit_title,
                        "description": edit_description,
                        "owner": edit_owner,
                        "priority": edit_priority,
                        "status": edit_status,
                        "due_date": edit_due.isoformat(),
                        "reference_url": edit_ref,
                    },
                    source,
                )
                st.session_state["selected_task_id"] = task["id"]
                st.success("Cambios guardados.")
                st.rerun()
        if closed:
            st.session_state["selected_task_id"] = ""
            st.rerun()
    st.markdown("</div></section>", unsafe_allow_html=True)


st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Saira:wght@400;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
      :root {
        --gold:#FFD700;--gold-hover:#FFCC00;--carbon:#333333;--ink:#1A1A1A;
        --bg:#FAFAF8;--surface:#FFFFFF;--muted-surface:#F4F4F2;--muted:#6B6B6B;
        --line:#EDECEA;--line-strong:#C9C9C4;--primary-soft:#FFF7BF;
        --green:#15803D;--green-bg:#EAF6EF;--orange:#A66A00;--orange-bg:#FFF3D8;
        --red:#C92B2B;--red-bg:#FDECEA;--blue:#2563EB;--blue-bg:#EAF1FE;
      }
      header, [data-testid="stToolbar"] { display:none !important; }
      .stApp { background:#ECECEA; color:var(--ink); }
      .block-container { max-width:100% !important; padding:0 12px 24px !important; }
      html, body, .stMarkdown, [data-testid="stWidgetLabel"] {
        font-family:"IBM Plex Sans",ui-sans-serif,system-ui,sans-serif;
      }
      .cp-top {
        height:64px;
        display:flex;
        align-items:center;
        justify-content:space-between;
        background:var(--carbon);
        color:#FFFFFF;
        border-radius:0 0 10px 10px;
        padding:0 18px;
        margin-bottom: 14px;
        box-shadow:0 10px 24px rgba(26,26,26,.14);
      }
      .cp-brand { display:flex; align-items:center; gap:14px; }
      .cp-hamb { font-size:22px; color:#9A9A98; line-height:1; }
      .cp-logo {
        width:32px;
        height:32px;
        object-fit:contain;
        border-radius:7px;
        background:#FFFFFF;
        box-shadow:0 0 0 1px #5C5C58;
      }
      .cp-title h1 {
        font-family:Saira,"IBM Plex Sans",sans-serif;
        color:#FFFFFF;
        font-size:18px;
        line-height:1.2;
        margin:0;
        font-weight:700;
      }
      .cp-title p { color:#C9C9C6; font-size:12px; margin:2px 0 0; }
      .cp-user { color:#ECECEA; font-size:12px; line-height:1.15; text-align:right; }
      .cp-user b { display:block; color:#FFFFFF; }
      .cp-card {
        background:var(--surface);
        border:1px solid #D8D8D5;
        border-radius:10px;
        box-shadow:0 8px 20px rgba(26,26,26,.05);
        margin-bottom:12px;
      }
      .cp-section-head {
        display:flex;
        justify-content:space-between;
        align-items:end;
        padding:11px 14px 7px;
        border-bottom:1px solid var(--line);
      }
      .cp-section-head h2 {
        font-family:Saira,"IBM Plex Sans",sans-serif;
        font-size:14px;
        margin:0;
      }
      .cp-section-head p { font-size:11px; color:var(--muted); margin:3px 0 0; }
      .cp-form-shell { padding:14px; background:#FAFAF8; border-radius:10px; }
      .compact-form { padding-bottom:10px; }
      .cp-toolbar {
        background:#FAFAF8;
        border:1px solid #D8D8D5;
        border-radius:10px;
        padding:14px;
        margin-bottom:12px;
      }
      div[data-testid="stForm"] {
        border:0;
        border-radius:0;
        padding:0;
        background:transparent;
      }
      div[data-testid="stTextInput"] input,
      div[data-testid="stTextArea"] textarea,
      div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
      div[data-testid="stDateInput"] input {
        border-color:#D8D8D5 !important;
        border-radius:9px !important;
        background:#FFFFFF !important;
        color:var(--ink) !important;
        font-size:12px !important;
        min-height:34px !important;
      }
      div[data-testid="stWidgetLabel"] label,
      div[data-testid="stWidgetLabel"] p {
        color:var(--muted) !important;
        font-size:10px !important;
        font-weight:700 !important;
        letter-spacing:.04em !important;
        text-transform:uppercase !important;
      }
      div.stButton > button,
      div[data-testid="stFormSubmitButton"] button {
        border-radius:9px !important;
        border:1px solid var(--line) !important;
        background:#FFFFFF !important;
        color:var(--carbon) !important;
        font-size:12px !important;
        font-weight:700 !important;
        min-height:34px !important;
      }
      div.stButton > button:hover {
        border-color:var(--gold) !important;
        background:#fffdf0 !important;
        color:var(--ink) !important;
      }
      div[data-testid="stFormSubmitButton"] button {
        border-color:var(--gold) !important;
        background:var(--gold) !important;
        color:var(--ink) !important;
      }
      div[data-testid="stFormSubmitButton"] button:hover { background:var(--gold-hover) !important; }
      .cp-metric {
        border: 1px solid;
        border-radius: 0;
        padding: 10px 12px;
        min-height:74px;
        background:#FFFFFF;
      }
      .cp-metric-label {
        color: var(--muted);
        font-size: 11px;
        font-weight: 700;
      }
      .cp-metric-value {
        font-family:"IBM Plex Mono",monospace;
        font-size: 28px;
        font-weight: 700;
        line-height: 1.05;
        margin-top: 4px;
      }
      .kpi-grid {
        display:grid;
        grid-template-columns:repeat(4,1fr);
        overflow:hidden;
      }
      .kpi-grid > div:not(:last-child) .cp-metric { border-right:0; }
      .board-column {
        background: #FAFAF8;
        border: 1px solid #D8D8D5;
        border-radius: 10px;
        padding: 12px 12px 2px;
        margin-bottom: 12px;
      }
      .board-title {
        color: var(--ink);
        font-family:Saira,"IBM Plex Sans",sans-serif;
        font-size: 14px;
        font-weight: 700;
        margin-bottom: 4px;
      }
      .task-card {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 11px 12px 10px;
        margin: 8px 0 8px;
        box-shadow:none;
      }
      .task-card.selected-task {
        border-color:var(--gold);
        box-shadow:inset 3px 0 0 var(--gold);
        background:#FFFDF0;
      }
      .task-topline {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
        margin-bottom: 8px;
      }
      .pill {
        border: 1px solid;
        border-radius: 6px;
        display: inline-flex;
        font-size: 11px;
        font-weight: 700;
        line-height: 1;
        padding: 5px 8px;
      }
      .task-title {
        color: var(--ink);
        font-size: 14px;
        font-weight: 700;
        line-height: 1.25;
        margin-bottom: 7px;
      }
      .task-desc {
        color: var(--muted);
        font-size: 12px;
        line-height: 1.35;
        white-space: pre-wrap;
        margin-bottom: 8px;
        max-height:48px;
        overflow:hidden;
      }
      .task-meta {
        color: var(--muted);
        display: grid;
        gap: 4px;
        font-size: 11px;
      }
      .overdue { color: var(--red); }
      [data-testid="stSidebar"] { background:#333333 !important; }
      [data-testid="stSidebar"] * { color:#ECECEA !important; }
      @media (max-width: 900px) {
        .kpi-grid { grid-template-columns:repeat(2,1fr); }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

cp_logo = _asset_data_uri(CP_MARK_PATH)
logo_html = (
    f'<img class="cp-logo" src="{cp_logo}" alt="Conprospeccion">'
    if cp_logo
    else '<div class="cp-logo"></div>'
)

st.markdown(
    f"""
    <div class="cp-top">
      <div class="cp-brand">
        <div class="cp-hamb">☰</div>
        {logo_html}
        <div class="cp-title"><h1>Work and Project Management</h1><p>Panel operativo</p></div>
      </div>
      <div class="cp-user"><b>Francisca / Yanina</b>Panel interno</div>
    </div>
    """,
    unsafe_allow_html=True,
)

tasks, source = load_tasks()
current_user = get_current_user() or "Francisca"
week_start, week_end = _week_bounds(_today())

st.markdown(
    """
    <section class="cp-card">
      <div class="cp-section-head">
        <div><h2>Nuevo pendiente</h2><p>Crear tarea semanal con responsable, prioridad y fecha límite.</p></div>
      </div>
      <div class="cp-form-shell">
    """,
    unsafe_allow_html=True,
)
with st.form("new_task_form", clear_on_submit=True):
    n1, n2, n3, n4, n5 = st.columns([2.4, .85, .85, .9, .9])
    with n1:
        title = st.text_input("Tarea", placeholder="Ej: Revisar leads nuevos de la semana")
    with n2:
        owner = st.selectbox("Asignada a", OWNERS, index=0)
    with n3:
        priority = st.selectbox("Prioridad", PRIORITIES, index=1)
    with n4:
        due_date = st.date_input("Fecha limite", value=_today())
    with n5:
        week_choice = st.date_input("Semana", value=week_start, help="Usa cualquier dia de la semana; se guardara como lunes.")

    d1, d2 = st.columns([2.2, 1])
    with d1:
        description = st.text_area("Detalle", placeholder="Que tiene que hacer, donde mirar y cuando avisar.", height=64)
    with d2:
        reference_url = st.text_input("Link / archivo", placeholder="URL, carpeta o documento")

    submitted = st.form_submit_button("Crear tarea", use_container_width=True, type="primary")
    if submitted:
        if not title.strip():
            st.warning("Escribe un nombre para la tarea.")
        else:
            selected_week, _ = _week_bounds(week_choice)
            create_task(
                {
                    "title": title,
                    "description": description,
                    "owner": owner,
                    "priority": priority,
                    "status": "Pendiente",
                    "due_date": due_date.isoformat(),
                    "week_start": selected_week.isoformat(),
                    "reference_url": reference_url,
                    "created_by": current_user,
                    "created_at": _now_iso(),
                    "updated_at": _now_iso(),
                    "is_archived": False,
                },
                source,
            )
            st.success("Tarea creada.")
            st.rerun()
st.markdown("</div></section>", unsafe_allow_html=True)

st.markdown('<div class="cp-toolbar">', unsafe_allow_html=True)
f1, f2, f3 = st.columns([1.1, 1.1, 1])
with f1:
    selected_owner = st.selectbox("Ver responsable", ["Todas", *OWNERS])
with f2:
    selected_day = st.date_input("Semana a revisar", value=week_start, key="board_week")
    selected_week_start, selected_week_end = _week_bounds(selected_day)
with f3:
    include_done = st.toggle("Mostrar terminadas", value=True)
st.markdown("</div>", unsafe_allow_html=True)

visible_tasks = _filter_tasks(tasks, selected_owner, selected_week_start, include_done)
active_tasks = [task for task in visible_tasks if task["status"] != "Terminado"]
overdue_tasks = [
    task
    for task in visible_tasks
    if task["status"] != "Terminado"
    and (due := _date_or_none(task.get("due_date")))
    and due < _today()
]

st.markdown('<section class="cp-card kpi-grid">', unsafe_allow_html=True)
m1, m2, m3, m4 = st.columns(4)
with m1:
    _summary_card("Pendientes activos", len(active_tasks), "#333333", "#FFFFFF")
with m2:
    _summary_card("Alta prioridad", sum(1 for task in active_tasks if task["priority"] == "Alta"), "#C92B2B", "#FFFFFF")
with m3:
    _summary_card("Vencidas", len(overdue_tasks), "#A66A00", "#FFFFFF")
with m4:
    _summary_card("Terminadas", sum(1 for task in visible_tasks if task["status"] == "Terminado"), "#15803D", "#FFFFFF")
st.markdown("</section>", unsafe_allow_html=True)

source_label = "Supabase" if source == "supabase" else "respaldo local"
st.caption(
    f"Semana {selected_week_start.strftime('%d/%m/%Y')} - {selected_week_end.strftime('%d/%m/%Y')} · Datos desde {source_label}"
)

selected_task = _selected_task(visible_tasks)
if selected_task:
    _render_editor(selected_task, source)

st.markdown(
    """
    <section class="cp-card">
      <div class="cp-section-head">
        <div><h2>Work and Project Management</h2><p>Avance semanal ordenado por estado.</p></div>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)
board_cols = st.columns(3)
for col, status in zip(board_cols, STATUSES):
    with col:
        status_tasks = [task for task in visible_tasks if task["status"] == status]
        meta = STATUS_META[status]
        st.markdown(
            f"""
            <div class="board-column">
              <div class="board-title" style="border-left:4px solid {meta['color']};padding-left:8px">
                {_esc(status)} · {len(status_tasks)}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if not status_tasks:
            st.info("Sin tareas en esta columna.")
        for task in status_tasks:
            _render_task_card(task, source)

with st.expander("Vista rápida en tabla"):
    if visible_tasks:
        df = pd.DataFrame(visible_tasks)
        st.dataframe(
            df[["title", "owner", "priority", "status", "due_date", "week_start"]].rename(
                columns={
                    "title": "Tarea",
                    "owner": "Responsable",
                    "priority": "Prioridad",
                    "status": "Estado",
                    "due_date": "Fecha límite",
                    "week_start": "Semana",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.write("No hay tareas para esta semana.")

render_master_user_sidebar()
