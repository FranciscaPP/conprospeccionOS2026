"""Tablero interno de pendientes semanales."""
from __future__ import annotations

import html
import json
import sys
import tempfile
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
from work_board_component import render_work_board_component

st.set_page_config(page_title="Work and Project Management - ConprospeccionOS", layout="wide", page_icon="")
if not require_master_auth():
    st.stop()

SB_URL = supabase_url()
SB_KEY = supabase_key()
SB_HEADERS = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"}
SB_WRITE_HEADERS = {**SB_HEADERS, "Content-Type": "application/json", "Prefer": "return=representation"}

LOCAL_STORE = ROOT / "dashboard" / "data" / "pendientes_semanales_local.json"
CP_MARK_PATH = DASHBOARD_DIR / "assets" / "cp_mark_dark.png"
BOARD_COMPONENT_DIR = Path(tempfile.gettempdir()) / "cp_work_board_component"

STATUSES = ["Pendiente", "En proceso", "Revisión", "Terminado"]
OWNERS = ["Yanina", "Francisca"]
PRIORITIES = ["Alta", "Media", "Baja"]
CLIENTS = ["Interno", "GBS", "BambuTech"]

CLIENT_LABELS = {
    "Interno": "Interno",
    "GBS": "GBS",
    "BambuTech": "Bambu Tech",
}

STATUS_META = {
    "Pendiente": {"color": "#A66A00", "bg": "#FFF3D8", "border": "#F0D28D"},
    "En proceso": {"color": "#2563EB", "bg": "#EAF1FE", "border": "#BFD2FB"},
    "Revisión": {"color": "#6D28D9", "bg": "#F1EDFF", "border": "#CDBDFF"},
    "Terminado": {"color": "#15803D", "bg": "#EAF6EF", "border": "#BFE6CC"},
}

PRIORITY_META = {
    "Alta": {"color": "#C92B2B", "bg": "#FDECEA", "border": "#F3B7B3"},
    "Media": {"color": "#A66A00", "bg": "#FFF3D8", "border": "#F0D28D"},
    "Baja": {"color": "#15803D", "bg": "#EAF6EF", "border": "#BFE6CC"},
}

OWNER_META = {
    "Yanina": {"initial": "Y", "color": "#2563EB", "bg": "#EAF1FE", "border": "#BFD2FB"},
    "Francisca": {"initial": "F", "color": "#A66A00", "bg": "#FFF3D8", "border": "#F0D28D"},
}

CLIENT_META = {
    "Interno": {"color": "#333333", "bg": "#F4F4F2", "border": "#D8D8D5"},
    "GBS": {"color": "#6D28D9", "bg": "#F1EDFF", "border": "#CDBDFF"},
    "BambuTech": {"color": "#15803D", "bg": "#EAF6EF", "border": "#BFE6CC"},
}

BOARD_HTML = r"""
<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
@import url('https://fonts.googleapis.com/css2?family=Saira:wght@400;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
:root{--gold:#FFD700;--ink:#1A1A1A;--line:#EDECEA;--muted:#6B6B6B;--surface:#FFFFFF;--red:#C92B2B}
*{box-sizing:border-box}
body{margin:0;background:transparent;color:var(--ink);font-family:"IBM Plex Sans",ui-sans-serif,system-ui,sans-serif;font-size:12px}
.board{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;align-items:start}
.column{background:#FAFAF8;border:1px solid #D8D8D5;border-radius:10px;min-height:220px;padding:10px}
.column.drag-over{outline:2px solid var(--gold);outline-offset:2px;background:#FFFDF0}
.board-title{background:white;border:1px solid #D8D8D5;border-radius:8px;color:var(--ink);font-family:Saira,"IBM Plex Sans",sans-serif;font-size:14px;font-weight:700;margin:0 0 10px;padding:10px 10px 10px 12px}
.empty{background:#EAF1FE;border-radius:8px;color:#0B5CAD;font-size:13px;padding:14px}
.task-card{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:11px 12px 10px;margin:8px 0;box-shadow:none;cursor:grab;transition:border-color .12s ease,background .12s ease,opacity .12s ease}
.task-card:active{cursor:grabbing}
.task-card:hover{border-color:var(--gold);background:#FFFDF0}
.task-card.selected-task{border-color:var(--gold);box-shadow:inset 3px 0 0 var(--gold);background:#FFFDF0}
.task-card.dragging{opacity:.45}
.task-head{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:8px}
.task-topline{display:flex;gap:6px;flex-wrap:wrap;min-width:0;flex:1}
.pill{border:1px solid;border-radius:6px;display:inline-flex;font-size:11px;font-weight:700;line-height:1;padding:5px 8px}
.owner-badge{align-items:center;border:1px solid;border-radius:8px;display:flex;flex:0 0 auto;gap:6px;min-height:30px;padding:4px 7px 4px 5px}
.owner-badge span{border-radius:6px;display:grid;font-family:"IBM Plex Mono",monospace;font-size:12px;font-weight:700;height:21px;place-items:center;width:21px;background:#FFFFFFAA}
.owner-badge b{font-size:12px;line-height:1}
.task-title{color:var(--ink);font-size:14px;font-weight:700;line-height:1.25;margin-bottom:7px}
.task-desc{color:var(--muted);font-size:12px;line-height:1.35;white-space:pre-wrap;margin-bottom:8px;max-height:48px;overflow:hidden}
.task-meta{color:var(--muted);display:grid;gap:4px;font-size:11px}
.overdue{color:var(--red)}
@media(max-width:900px){.board{grid-template-columns:1fr}.column{min-height:120px}}
</style>
</head>
<body>
<div id="root"></div>
<script>
function send(type,data={}){window.parent.postMessage({isStreamlitMessage:true,type,...data},"*")}
function ready(){send("streamlit:componentReady",{apiVersion:1})}
function setHeight(){send("streamlit:setFrameHeight",{height:Math.max(520,document.documentElement.scrollHeight)})}
function setValue(value){send("streamlit:setComponentValue",{value,dataType:"json"})}
function esc(s){return String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[m]))}
function pill(label,meta){return `<span class="pill" style="color:${meta.color};background:${meta.bg};border-color:${meta.border}">${esc(label)}</span>`}
let dragId=null;
function cardHtml(t){
  const ref=t.reference_url?`<span>Referencia: <b>${esc(t.reference_url)}</b></span>`:"";
  return `<div class="task-card ${t.selected?"selected-task":""}" draggable="true" data-id="${esc(t.id)}" role="button" tabindex="0">
    <div class="task-head">
      <div class="task-topline">${pill(t.client_label,t.client_meta)}${pill(t.priority,t.priority_meta)}${pill(t.status,t.status_meta)}</div>
      <div class="owner-badge" style="color:${t.owner_meta.color};background:${t.owner_meta.bg};border-color:${t.owner_meta.border}">
        <span>${esc(t.owner_meta.initial)}</span><b>${esc(t.owner)}</b>
      </div>
    </div>
    <div class="task-title">${esc(t.title)}</div>
    <div class="task-desc">${esc(t.description||"Sin detalle adicional.")}</div>
    <div class="task-meta">
      <span class="${t.overdue?"overdue":""}">Fecha limite: <b>${esc(t.due_text)}</b></span>
      <span>Semana: <b>${esc(t.week_label)}</b></span>${ref}
    </div>
  </div>`
}
function render(args){
  const statuses=args.statuses||[], meta=args.status_meta||{}, tasks=args.tasks||[];
  const grouped=Object.fromEntries(statuses.map(s=>[s,[]]));
  tasks.forEach(t=>{(grouped[t.status]||grouped[statuses[0]]||[]).push(t)});
  document.getElementById("root").innerHTML=`<div class="board">${statuses.map(status=>{
    const list=grouped[status]||[];
    const color=(meta[status]||{}).color||"#333";
    return `<section class="column" data-status="${esc(status)}">
      <div class="board-title" style="border-left:4px solid ${color}">${esc(status)} · ${list.length}</div>
      <div class="cards">${list.length?list.map(cardHtml).join(""):`<div class="empty">Sin tareas en esta columna.</div>`}</div>
    </section>`;
  }).join("")}</div>`;
  document.querySelectorAll(".task-card").forEach(card=>{
    card.addEventListener("click",()=>setValue({action:"open",task_id:card.dataset.id,nonce:String(Date.now())}));
    card.addEventListener("keydown",event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();setValue({action:"open",task_id:card.dataset.id,nonce:String(Date.now())})}});
    card.addEventListener("dragstart",event=>{dragId=card.dataset.id;card.classList.add("dragging");event.dataTransfer.effectAllowed="move";event.dataTransfer.setData("text/plain",dragId)});
    card.addEventListener("dragend",()=>{card.classList.remove("dragging");dragId=null;document.querySelectorAll(".column").forEach(c=>c.classList.remove("drag-over"))});
  });
  document.querySelectorAll(".column").forEach(col=>{
    col.addEventListener("dragover",event=>{event.preventDefault();col.classList.add("drag-over")});
    col.addEventListener("dragleave",()=>col.classList.remove("drag-over"));
    col.addEventListener("drop",event=>{
      event.preventDefault();col.classList.remove("drag-over");
      const id=event.dataTransfer.getData("text/plain")||dragId;
      const status=col.dataset.status;
      if(id&&status)setValue({action:"move",task_id:id,status,nonce:String(Date.now())});
    });
  });
  setTimeout(setHeight,0);
}
ready();
window.addEventListener("message",event=>{if(event.data&&event.data.type==="streamlit:render")render(event.data.args||{})});
</script>
</body>
</html>
"""


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
    clean["client"] = clean.get("client") if clean.get("client") in CLIENTS else "Interno"
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
    elif clean_changes.get("status") in {"Pendiente", "En proceso", "Revisión"}:
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


def _filter_tasks(
    tasks: list[dict[str, Any]],
    owner: str,
    client: str,
    priority: str,
    week_start: date,
    include_done: bool,
) -> list[dict[str, Any]]:
    filtered = []
    for task in tasks:
        task_week = _date_or_none(task.get("week_start")) or _week_bounds(_today())[0]
        if task_week != week_start:
            continue
        if owner != "Todas" and task.get("owner") != owner:
            continue
        if client != "Todos" and task.get("client") != client:
            continue
        if priority != "Todas" and task.get("priority") != priority:
            continue
        if not include_done and task.get("status") == "Terminado":
            continue
        filtered.append(task)
    priority_order = {"Alta": 0, "Media": 1, "Baja": 2}
    status_order = {"Pendiente": 0, "En proceso": 1, "Revisión": 2, "Terminado": 3}
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


def _write_board_component() -> None:
    BOARD_COMPONENT_DIR.mkdir(parents=True, exist_ok=True)
    target = BOARD_COMPONENT_DIR / "index.html"
    if not target.exists() or target.read_text(encoding="utf-8", errors="ignore") != BOARD_HTML:
        target.write_text(BOARD_HTML, encoding="utf-8")


def _board_tasks_payload(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected_id = str(st.session_state.get("selected_task_id") or "")
    payload = []
    for task in tasks:
        due = _date_or_none(task.get("due_date"))
        overdue = bool(due and due < _today() and task["status"] != "Terminado")
        payload.append(
            {
                **task,
                "client_label": CLIENT_LABELS.get(task["client"], task["client"]),
                "client_meta": CLIENT_META.get(task["client"], CLIENT_META["Interno"]),
                "priority_meta": PRIORITY_META.get(task["priority"], PRIORITY_META["Media"]),
                "status_meta": STATUS_META.get(task["status"], STATUS_META["Pendiente"]),
                "owner_meta": OWNER_META.get(task["owner"], OWNER_META["Yanina"]),
                "due_text": "Vencida" if overdue else _fmt_date(task.get("due_date")),
                "week_label": _task_week_label(task),
                "overdue": overdue,
                "selected": str(task.get("id")) == selected_id,
            }
        )
    return payload


def _open_editor(task_id: str) -> None:
    st.session_state["selected_task_id"] = task_id


def _clear_selected_task() -> None:
    st.session_state["selected_task_id"] = ""


def _consume_board_payload(payload: dict[str, Any]) -> bool:
    nonce = str(payload.get("nonce") or "")
    if not nonce:
        return True
    if st.session_state.get("_work_board_last_nonce") == nonce:
        return False
    st.session_state["_work_board_last_nonce"] = nonce
    return True


def _selected_task(tasks: list[dict[str, Any]]) -> dict[str, Any] | None:
    selected_id = st.session_state.get("selected_task_id")
    for task in tasks:
        if str(task.get("id")) == str(selected_id):
            return task
    return None


def _render_task_card(task: dict[str, Any], source: str) -> None:
    priority = PRIORITY_META.get(task["priority"], PRIORITY_META["Media"])
    status = STATUS_META.get(task["status"], STATUS_META["Pendiente"])
    owner_meta = OWNER_META.get(task["owner"], OWNER_META["Yanina"])
    client_meta = CLIENT_META.get(task["client"], CLIENT_META["Interno"])
    due = _date_or_none(task.get("due_date"))
    overdue = bool(due and due < _today() and task["status"] != "Terminado")
    due_text = "Vencida" if overdue else _fmt_date(task.get("due_date"))
    selected = str(st.session_state.get("selected_task_id") or "") == str(task["id"])
    selected_cls = " selected-task" if selected else ""
    reference_html = f'<span>Referencia: <b>{_esc(task.get("reference_url"))}</b></span>' if task.get("reference_url") else ""

    st.markdown(
        f"""
        <div class="task-card{selected_cls}">
          <div class="task-head">
            <div class="task-topline">
              <span class="pill" style="color:{client_meta['color']};background:{client_meta['bg']};border-color:{client_meta['border']}">
                {_esc(CLIENT_LABELS.get(task['client'], task['client']))}
              </span>
              <span class="pill" style="color:{priority['color']};background:{priority['bg']};border-color:{priority['border']}">
                {_esc(task['priority'])}
              </span>
              <span class="pill" style="color:{status['color']};background:{status['bg']};border-color:{status['border']}">
                {_esc(task['status'])}
              </span>
            </div>
            <div class="owner-badge" style="color:{owner_meta['color']};background:{owner_meta['bg']};border-color:{owner_meta['border']}">
              <span>{_esc(owner_meta['initial'])}</span><b>{_esc(task['owner'])}</b>
            </div>
          </div>
          <div class="task-title">{_esc(task['title'])}</div>
          <div class="task-desc">{_esc(task.get('description') or 'Sin detalle adicional.')}</div>
          <div class="task-meta">
            <span class="{ 'overdue' if overdue else '' }">Fecha limite: <b>{_esc(due_text)}</b></span>
            <span>Semana: <b>{_esc(_task_week_label(task))}</b></span>
            {reference_html}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Editar", key=f"edit_{task['id']}", use_container_width=True):
        _open_editor(task["id"])
        st.rerun()


def _render_editor(task: dict[str, Any], source: str) -> None:
    status = STATUS_META.get(task["status"], STATUS_META["Pendiente"])
    priority = PRIORITY_META.get(task["priority"], PRIORITY_META["Media"])
    owner = OWNER_META.get(task["owner"], OWNER_META["Yanina"])
    client = CLIENT_META.get(task["client"], CLIENT_META["Interno"])
    client_label = CLIENT_LABELS.get(task["client"], task["client"])

    def chip(label: str, meta: dict[str, str]) -> str:
        return (
            f'<span class="detail-chip" style="color:{meta["color"]};'
            f'background:{meta["bg"]};border-color:{meta["border"]}">{_esc(label)}</span>'
        )

    st.markdown(
        f"""
        <section class="cp-card drawer-card">
          <div class="detail-band">
            <div class="band-main">
              <div class="band-title">
                <b>{_esc(task['title'])}</b>
                <span>{_esc(client_label)} - {_esc(task['owner'])}</span>
              </div>
            </div>
            <div class="band-item">
              <small>Fecha limite</small>
              <b>{_esc(_fmt_date(task.get('due_date')))}</b>
            </div>
            <div class="band-item">
              <small>Responsable</small>
              <b>{_esc(task['owner'])}</b>
            </div>
          </div>
          <div class="summary-grid">
            <div class="sum-box"><small>Estado</small>{chip(task['status'], status)}</div>
            <div class="sum-box"><small>Prioridad</small>{chip(task['priority'], priority)}</div>
            <div class="sum-box"><small>Cliente</small>{chip(client_label, client)}</div>
            <div class="sum-box"><small>Asignada a</small>{chip(task['owner'], owner)}</div>
          </div>
          <div class="tabs-lite">
            <div class="active">Gestion</div>
            <div>Detalle</div>
            <div>Historial</div>
          </div>
          <div class="editor-copy">
            <b>Gestion de la tarea</b>
            <span>Actualiza los campos operativos y guarda los cambios.</span>
          </div>
          <div class="cp-form-shell compact-form drawer-form">
        """,
        unsafe_allow_html=True,
    )
    with st.form(f"edit_task_form_{task['id']}", clear_on_submit=False):
        edit_title = st.text_input("Tarea", value=task["title"], key=f"title_{task['id']}")

        row1_a, row1_b = st.columns(2)
        with row1_a:
            edit_status = st.selectbox(
                "Estado",
                STATUSES,
                index=STATUSES.index(task["status"]) if task["status"] in STATUSES else 0,
                key=f"status_{task['id']}",
            )
        with row1_b:
            edit_priority = st.selectbox(
                "Prioridad",
                PRIORITIES,
                index=PRIORITIES.index(task["priority"]) if task["priority"] in PRIORITIES else 1,
                key=f"priority_{task['id']}",
            )

        row2_a, row2_b = st.columns(2)
        with row2_a:
            edit_client = st.selectbox(
                "Cliente",
                CLIENTS,
                format_func=lambda value: CLIENT_LABELS.get(value, value),
                index=CLIENTS.index(task["client"]) if task["client"] in CLIENTS else 0,
                key=f"client_{task['id']}",
            )
        with row2_b:
            edit_owner = st.selectbox(
                "Asignada a",
                OWNERS,
                index=OWNERS.index(task["owner"]) if task["owner"] in OWNERS else 0,
                key=f"owner_{task['id']}",
            )

        row3_a, row3_b = st.columns([.9, 1.4])
        with row3_a:
            edit_due = st.date_input(
                "Fecha limite",
                value=_date_or_none(task.get("due_date")) or _today(),
                key=f"due_{task['id']}",
            )
        with row3_b:
            edit_ref = st.text_input(
                "Link / archivo",
                value=task.get("reference_url", ""),
                placeholder="URL, carpeta o documento de referencia",
                key=f"ref_{task['id']}",
            )

        edit_description = st.text_area(
            "Detalle",
            value=task.get("description", ""),
            height=118,
            key=f"description_{task['id']}",
        )
        save_col, close_col = st.columns([1, 1])
        with save_col:
            saved = st.form_submit_button("Guardar cambios", use_container_width=True, type="primary")
        with close_col:
            closed = st.form_submit_button("Cerrar", use_container_width=True)

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
                        "client": edit_client,
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
            _clear_selected_task()
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
      .drawer-card {
        position: sticky;
        top: 10px;
        overflow:hidden;
      }
      .detail-band {
        display:flex;
        align-items:center;
        gap:14px;
        border:1px solid #FFE6A3;
        background:#FFF7D0;
        border-radius:8px;
        padding:12px;
        margin:12px 12px 14px;
      }
      .band-main {
        flex:1;
        min-width:0;
        border-right:1px solid #F0D28D;
        padding-right:12px;
      }
      .band-title b {
        display:block;
        color:var(--ink);
        font-family:Saira,"IBM Plex Sans",sans-serif;
        font-size:16px;
        line-height:1.1;
        overflow:hidden;
        text-overflow:ellipsis;
        white-space:nowrap;
      }
      .band-title span {
        display:block;
        color:var(--muted);
        font-size:12px;
        margin-top:4px;
        overflow:hidden;
        text-overflow:ellipsis;
        white-space:nowrap;
      }
      .band-item {
        min-width:86px;
      }
      .band-item small {
        display:block;
        color:var(--muted);
        font-size:10px;
        line-height:1.05;
      }
      .band-item b {
        display:block;
        color:var(--ink);
        font-size:12px;
        line-height:1.15;
        margin-top:3px;
      }
      .summary-grid {
        display:grid;
        grid-template-columns:repeat(2,minmax(0,1fr));
        gap:10px;
        padding:0 12px 12px;
      }
      .sum-box {
        background:#fff;
        border:1px solid var(--line);
        border-radius:8px;
        min-width:0;
        padding:10px;
      }
      .sum-box small {
        color:var(--muted);
        display:block;
        font-size:10px;
        font-weight:700;
        margin-bottom:8px;
        text-transform:uppercase;
      }
      .detail-chip {
        align-items:center;
        border:1px solid;
        border-radius:6px;
        display:inline-flex;
        font-size:12px;
        font-weight:700;
        line-height:1.15;
        padding:7px 9px;
      }
      .tabs-lite {
        display:grid;
        grid-template-columns:repeat(3,1fr);
        background:#F6F6F4;
        border:1px solid var(--line);
        border-radius:8px;
        margin:0 12px 14px;
        overflow:hidden;
      }
      .tabs-lite div {
        color:var(--muted);
        font-size:12px;
        font-weight:700;
        padding:12px 4px 11px;
        text-align:center;
      }
      .tabs-lite .active {
        background:#fff;
        border-bottom:2px solid var(--gold);
        color:var(--ink);
      }
      .editor-copy {
        padding:0 18px 12px;
      }
      .editor-copy b {
        color:var(--ink);
        display:block;
        font-family:Saira,"IBM Plex Sans",sans-serif;
        font-size:18px;
        line-height:1.2;
      }
      .editor-copy span {
        color:var(--muted);
        display:block;
        font-size:13px;
        margin-top:3px;
      }
      .drawer-form {
        padding:0 18px 16px;
      }
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
        transition:border-color .12s ease, background .12s ease;
      }
      .task-head {
        display:flex;
        align-items:flex-start;
        justify-content:space-between;
        gap:8px;
        margin-bottom:8px;
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
        margin-bottom: 0;
        min-width:0;
        flex:1;
      }
      .owner-badge {
        align-items:center;
        border:1px solid;
        border-radius:8px;
        display:flex;
        flex:0 0 auto;
        gap:6px;
        min-height:30px;
        padding:4px 7px 4px 5px;
      }
      .owner-badge span {
        border-radius:6px;
        display:grid;
        font-family:"IBM Plex Mono",monospace;
        font-size:12px;
        font-weight:700;
        height:21px;
        place-items:center;
        width:21px;
        background:#FFFFFFAA;
      }
      .owner-badge b {
        font-size:12px;
        line-height:1;
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
    n1, n2, n3, n4, n5, n6 = st.columns([2.2, .8, .8, .9, .85, .85])
    with n1:
        title = st.text_input("Tarea", placeholder="Ej: Revisar leads nuevos de la semana")
    with n2:
        owner = st.selectbox("Asignada a", OWNERS, index=0)
    with n3:
        priority = st.selectbox("Prioridad", PRIORITIES, index=1)
    with n4:
        client = st.selectbox("Cliente", CLIENTS, format_func=lambda value: CLIENT_LABELS.get(value, value), index=0)
    with n5:
        due_date = st.date_input("Fecha limite", value=_today())
    with n6:
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
                    "client": client,
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
f1, f2, f3, f4, f5 = st.columns([1, 1, 1, 1, .85])
with f1:
    selected_owner = st.selectbox("Ver responsable", ["Todas", *OWNERS])
with f2:
    selected_client = st.selectbox(
        "Ver cliente",
        ["Todos", *CLIENTS],
        format_func=lambda value: CLIENT_LABELS.get(value, value),
    )
with f3:
    selected_priority = st.selectbox("Ver prioridad", ["Todas", *PRIORITIES])
with f4:
    selected_day = st.date_input("Semana a revisar", value=week_start, key="board_week")
    selected_week_start, selected_week_end = _week_bounds(selected_day)
with f5:
    include_done = st.toggle("Mostrar terminadas", value=True)
st.markdown("</div>", unsafe_allow_html=True)

visible_tasks = _filter_tasks(
    tasks,
    selected_owner,
    selected_client,
    selected_priority,
    selected_week_start,
    include_done,
)
active_tasks = [task for task in visible_tasks if task["status"] != "Terminado"]
overdue_tasks = [
    task
    for task in visible_tasks
    if task["status"] != "Terminado"
    and (due := _date_or_none(task.get("due_date")))
    and due < _today()
]

st.markdown('<section class="cp-card kpi-grid">', unsafe_allow_html=True)
m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    _summary_card("Pendientes activos", len(active_tasks), "#333333", "#FFFFFF")
with m2:
    _summary_card("Alta prioridad", sum(1 for task in active_tasks if task["priority"] == "Alta"), "#C92B2B", "#FFFFFF")
with m3:
    _summary_card("Vencidas", len(overdue_tasks), "#A66A00", "#FFFFFF")
with m4:
    _summary_card("En revisión", sum(1 for task in active_tasks if task["status"] == "Revisión"), "#6D28D9", "#FFFFFF")
with m5:
    _summary_card("Terminadas", sum(1 for task in visible_tasks if task["status"] == "Terminado"), "#15803D", "#FFFFFF")
st.markdown("</section>", unsafe_allow_html=True)

source_label = "Supabase" if source == "supabase" else "respaldo local"
st.caption(
    f"Semana {selected_week_start.strftime('%d/%m/%Y')} - {selected_week_end.strftime('%d/%m/%Y')} · Datos desde {source_label}"
)

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

board_area, editor_area = st.columns([2.25, 1], gap="medium")
with board_area:
    _write_board_component()
    board_payload = render_work_board_component(
        BOARD_COMPONENT_DIR,
        key=f"work_board_{selected_week_start.isoformat()}_{selected_owner}_{selected_client}_{selected_priority}_{include_done}",
        tasks=_board_tasks_payload(visible_tasks),
        statuses=STATUSES,
        status_meta=STATUS_META,
    )
    if isinstance(board_payload, dict) and _consume_board_payload(board_payload):
        action = board_payload.get("action")
        task_id = str(board_payload.get("task_id") or "")
        if action == "open" and task_id:
            if st.session_state.get("selected_task_id") != task_id:
                _open_editor(task_id)
                st.rerun()
        if action == "move" and task_id and board_payload.get("status") in STATUSES:
            target_status = board_payload["status"]
            current_task = next((task for task in visible_tasks if str(task.get("id")) == task_id), None)
            if not current_task or current_task.get("status") != target_status:
                update_task(task_id, {"status": target_status}, source)
                st.session_state["selected_task_id"] = task_id
                st.rerun()

with editor_area:
    selected_task = _selected_task(visible_tasks)
    if selected_task:
        _render_editor(selected_task, source)
    else:
        st.markdown(
            """
            <section class="cp-card">
              <div class="cp-section-head">
                <div><h2>Editar tarea</h2><p>Selecciona una tarjeta del tablero.</p></div>
              </div>
              <div class="cp-form-shell">
                <div style="color:#6B6B6B;font-size:13px;line-height:1.45">
                  Haz click en una tarjeta para editar cliente, responsable, prioridad,
                  estado, fecha limite, detalle y link/archivo. Tambien puedes arrastrarla
                  entre columnas para cambiar su estado.
                </div>
              </div>
            </section>
            """,
            unsafe_allow_html=True,
        )


with st.expander("Vista rápida en tabla"):
    if visible_tasks:
        df = pd.DataFrame(visible_tasks)
        st.dataframe(
            df[["title", "client", "owner", "priority", "status", "due_date", "week_start"]].rename(
                columns={
                    "title": "Tarea",
                    "client": "Cliente",
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
