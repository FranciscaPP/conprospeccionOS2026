import datetime
import json
import re

import requests
import streamlit as st
import streamlit.components.v1 as components

from shared.config import supabase_key, supabase_url
from shared.meeting_scope import ACTIVE_MEETING_CLIENT_SLUGS
from shared.metas import meta_de


st.set_page_config(page_title="Seguimiento Reuniones V5 POC", layout="wide")

st.markdown(
    """
<style>
[data-testid="stSidebar"], header, [data-testid="stToolbar"] { display:none !important; }
.block-container { max-width:100% !important; padding:0 !important; }
iframe { display:block; }
</style>
    """,
    unsafe_allow_html=True,
)


SUPABASE_URL = supabase_url()
SUPABASE_KEY = supabase_key()
SUPABASE_HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}


def _txt(value, default=""):
    if value is None:
        return default
    text = str(value).strip()
    return default if text.lower() in {"", "none", "nan", "nat", "<na>"} else text


def _client_label(slug, raw):
    labels = {"clickie": "Clickie", "gbs": "GBS", "bambutech": "BambuTech"}
    return labels.get(_txt(slug).lower(), _txt(raw, "Cliente"))


def _date_es(value):
    try:
        d = datetime.date.fromisoformat(str(value)[:10])
        return d.strftime("%d/%m/%Y")
    except Exception:
        return ""


def _time_12(value):
    raw = _txt(value)
    if not raw:
        return ""
    try:
        parts = raw.split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        suffix = "PM" if h >= 12 else "AM"
        h12 = h % 12 or 12
        return f"{h12:02d}:{m:02d} {suffix}"
    except Exception:
        return raw[:5]


def _status_label(row, seg):
    raw = f"{_txt(seg.get('status_reunion'))} {_txt(row.get('estado_reunion'))}".lower()
    if "reagend" in raw:
        return "Reagendar reunion"
    if "cancel" in raw or "no_asist" in raw:
        return "Reunion cancelada"
    if "realiz" in raw or "completed" in raw or "válid" in raw or "valid" in raw:
        return "Reunion realizada"
    try:
        d = datetime.date.fromisoformat(str(row.get("fecha") or "")[:10])
        return "Reunion futura" if d >= datetime.date.today() else "Reunion realizada"
    except Exception:
        return "Reunion futura"


def _cp_label(row, seg):
    value = _txt(seg.get("val_estado_cp")) or _txt(row.get("estado_validacion"))
    value = value.lower()
    if value in {"valida", "reunion_valida"}:
        return "Valida"
    if value in {"no_valida", "reunion_no_valida", "cancelacion"}:
        return "No valida"
    return "Pendiente"


def _client_val_label(seg):
    value = _txt(seg.get("val_estado_cli")).lower()
    if value in {"valida", "confirmar", "confirmada", "confirmado"}:
        return "Confirmar"
    if value in {"requiere_revision", "solicitar_revision", "solicita_revision"}:
        return "Solicitar revision"
    return "Pendiente"


def _final_label(seg):
    value = _txt(seg.get("val_estado_final")).lower()
    if value in {"valida", "reunion_valida"}:
        return "Reunion valida"
    if value in {"no_valida", "reunion_no_valida"}:
        return "Reunion no valida"
    if value in {"cancelacion", "cancelada"}:
        return "Reunion cancelada"
    if value in {"reagendar", "reagendada"}:
        return "Reagendar reunion"
    return "Pendiente"


def _case_status(cp, client_val, final):
    if final != "Pendiente":
        return "Cerrado"
    if client_val == "Solicitar revision":
        return "En revision"
    if cp == "Pendiente":
        return "En evaluacion CP"
    if client_val == "Pendiente":
        return "Esperando cliente"
    return "Abierto"


def _bant(value):
    items = {x.strip().upper() for x in _txt(value).split(",") if x.strip()}
    return {
        "Budget": "B" in items,
        "Authority": "A" in items,
        "Need": "N" in items,
        "Timeline": "T" in items,
    }


def _evidence(row, seg):
    ev = []
    if _txt(row.get("recording_url")) or _txt(seg.get("recording_url")):
        ev.append({"type": "Grabacion", "name": "Grabacion disponible", "valid": True})
    if _txt(row.get("transcript_url")) or _txt(seg.get("transcript_url")):
        ev.append({"type": "Transcripcion", "name": "Transcripcion disponible", "valid": True})
    if _txt(row.get("ai_summary")) or _txt(seg.get("ai_summary")) or _txt(row.get("ai_evidence")) or _txt(seg.get("ai_evidence")):
        ev.append({"type": "Resumen IA", "name": "Resumen disponible", "valid": True})
    return ev


@st.cache_data(ttl=30)
def cargar_reuniones_reales_poc():
    slugs = ",".join(ACTIVE_MEETING_CLIENT_SLUGS)
    meetings_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/vw_reuniones_semana?select=*&cliente_slug=in.({slugs})",
        headers=SUPABASE_HEADERS,
        timeout=15,
    )
    if not meetings_response.ok:
        return []
    tracking_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/seguimiento_reuniones?select=*&cliente_slug=in.({slugs})",
        headers=SUPABASE_HEADERS,
        timeout=15,
    )
    history_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/meeting_status_history?select=*&order=changed_at.desc&limit=10000",
        headers=SUPABASE_HEADERS,
        timeout=15,
    )
    tracking = {}
    if tracking_response.ok:
        tracking = {int(x["reunion_id"]): x for x in tracking_response.json() if x.get("reunion_id")}
    histories = {}
    if history_response.ok:
        for event in history_response.json():
            try:
                mid = int(event.get("meeting_id"))
            except Exception:
                continue
            histories.setdefault(mid, []).append(
                {
                    "when": _txt(event.get("changed_at"))[:16].replace("T", " "),
                    "user": _txt(event.get("changed_by"), "Conprospeccion"),
                    "field": _txt(event.get("field_changed"), "Actualizacion"),
                    "from": event.get("old_value"),
                    "to": event.get("new_value"),
                    "visibility": "Solo uso interno",
                }
            )
    rows = []
    for row in meetings_response.json():
        rid = row.get("id")
        if not rid:
            continue
        seg = tracking.get(int(rid), {})
        slug = _txt(row.get("cliente_slug")).lower()
        cp = _cp_label(row, seg)
        client_val = _client_val_label(seg)
        final = _final_label(seg)
        meta = meta_de(slug)
        rows.append(
            {
                "id": int(rid),
                "date": _date_es(row.get("fecha")),
                "time": _time_12(row.get("hora")),
                "client": _client_label(slug, row.get("cliente")),
                "company": _txt(row.get("empresa"), "-").title(),
                "contact": _txt(row.get("contacto"), "-").title(),
                "role": _txt(row.get("cargo"), "-").title(),
                "sdr": _txt(seg.get("sdr_override")) or _txt(row.get("sdr"), "Sin asignar"),
                "status": _status_label(row, seg),
                "cp": cp,
                "clientVal": client_val,
                "final": final,
                "caseStatus": _case_status(cp, client_val, final),
                "email": _txt(row.get("email")),
                "phone": _txt(row.get("telefono")),
                "country": _txt(row.get("pais")),
                "industry": _txt(row.get("industria")),
                "website": "",
                "linkedin": "",
                "ghlContact": _txt(row.get("ghl_contact_id")),
                "ghlOpp": _txt(row.get("opportunity_id")),
                "meet": "",
                "info": _txt(seg.get("informacion_reunion_manual")) or _txt(row.get("informacion_reunion")),
                "icp": "Cumple" if seg.get("icp_cumple") is True else "No cumple" if seg.get("icp_cumple") is False else "No evaluado",
                "bant": _bant(seg.get("bant_cp") or row.get("bant_sdr")),
                "just": _txt(seg.get("comentario_cp")),
                "next": _txt(seg.get("proximo_paso")),
                "notes": _txt(seg.get("notas_internas")),
                "finalReason": _txt(seg.get("comentario_final")),
                "finalClientText": _txt(seg.get("comentario_cp")),
                "finalInternalNote": _txt(seg.get("notas_internas")),
                "evidence": _evidence(row, seg),
                "clientReason": _txt(seg.get("motivo_no_validez")),
                "clientComment": _txt(seg.get("comentario_cli")),
                "clientDate": _txt(seg.get("validated_cli_at"))[:16].replace("T", " "),
                "clientActor": _txt(seg.get("validated_by_cli"), _txt(row.get("contacto"), "Cliente")),
                "clientEvidence": "",
                "cpResponse": "",
                "history": histories.get(int(rid), []),
                "goal": int(meta["validas"]) if meta else 0,
            }
        )
    rows.sort(key=lambda x: (x.get("date", ""), x.get("time", "")), reverse=True)
    return rows


POC_HTML = r"""
<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root{
  --bg:#f8fafc;--surface:#fff;--muted-surface:#f3f5f8;--ink:#162033;--muted:#667085;
  --line:#e4e7ec;--primary:#5b2eea;--primary-soft:#f1ecff;
  --green:#15803d;--green-bg:#dcfce7;--orange:#c56a09;--orange-bg:#fff3d8;
  --red:#dc2626;--red-bg:#fee2e2;--blue:#2563eb;--blue-bg:#dbeafe;
  --purple:#6d28d9;--purple-bg:#ede9fe;--gray:#475467;--gray-bg:#f2f4f7;
}
*{box-sizing:border-box}
html{font-size:16px;-webkit-font-smoothing:antialiased}
body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,sans-serif;font-size:14px}body.detail-open{overflow:hidden}
button,input,select,textarea{font:inherit}
.app{min-width:1320px;min-height:940px;padding:16px 20px 24px;background:var(--bg)}
.top{height:50px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line);margin-bottom:14px}
.brand{display:flex;align-items:center;gap:14px}.hamb{font-size:20px;color:var(--muted)}.mark{width:22px;height:22px;border-radius:50%;background:conic-gradient(from 20deg,#5b2eea,#16a34a,#0ea5e9,#5b2eea)}
.title h1{font-size:18px;line-height:1.2;margin:0;font-weight:600;text-transform:none}.title p{font-size:12px;margin:2px 0 0;color:#475467}
.user{display:flex;align-items:center;gap:14px}.bell{position:relative;width:32px;height:32px;border:0;background:transparent;border-radius:8px;display:grid;place-items:center;cursor:pointer}.bell:before{content:"";width:13px;height:15px;border:1.8px solid #344054;border-radius:8px 8px 4px 4px;display:block}.bell[data-count]:after{content:attr(data-count);position:absolute;top:-4px;right:-2px;min-width:16px;height:16px;padding:0 4px;border-radius:99px;background:#ef4444;color:white;font-size:10px;display:grid;place-items:center;font-weight:700}.avatar{width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,#101828,#d97706)}.usertext{font-size:12px;line-height:1.15}.usertext b{display:block}
.notif{position:absolute;right:18px;top:62px;width:360px;max-height:420px;overflow:auto;background:var(--surface);border:1px solid var(--line);border-radius:10px;box-shadow:0 12px 32px rgba(16,24,40,.16);z-index:50;padding:10px}.notif[hidden]{display:none}.notif h3{font-size:13px;margin:2px 4px 8px}.notif-item{border-top:1px solid var(--line);padding:9px 4px;font-size:12px}.notif-item b{display:block}
.layout{display:grid;grid-template-columns:1fr;gap:12px;align-items:start}.layout.open{grid-template-columns:minmax(0,70fr) minmax(430px,30fr)}
.main{display:flex;flex-direction:column;gap:12px;min-width:0}.card{background:var(--surface);border:1px solid var(--line);border-radius:10px;box-shadow:0 1px 2px rgba(16,24,40,.025)}
.filters{padding:12px;display:grid;grid-template-columns:2.1fr .95fr 1.45fr .95fr .75fr;gap:10px}.extra{display:none;grid-template-columns:repeat(6,1fr);gap:10px;padding:0 12px 12px}.extra.open{display:grid}
.field{height:38px;border:1px solid var(--line);border-radius:8px;background:var(--surface);display:flex;align-items:center;gap:8px;padding:0 11px;min-width:0;position:relative}.field label{position:absolute;top:-8px;left:9px;background:var(--surface);font-size:10px;color:var(--muted);font-weight:600;padding:0 4px}.field input,.field select{border:0;outline:0;background:transparent;width:100%;height:100%;color:var(--ink);font-size:12px}.field button{border:0;background:transparent;width:100%;height:100%;display:flex;align-items:center;justify-content:center;gap:7px;font-weight:600;font-size:12px;color:var(--ink);cursor:pointer}.date-range{display:grid;grid-template-columns:1fr 1fr auto;gap:4px;align-items:center}.date-range input{font-size:11px}.clear-date{border:0;background:transparent;color:var(--muted);cursor:pointer}
.active-filters{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:0 12px 12px}.filter-chip{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);background:var(--muted-surface);border-radius:999px;padding:5px 8px;font-size:11px}.filter-chip button{border:0;background:transparent;cursor:pointer;color:var(--muted)}.clear-all{border:1px solid var(--line);background:#fff;border-radius:8px;padding:6px 9px;font-size:12px;cursor:pointer;color:var(--primary)}
.kpis{display:grid;grid-template-columns:repeat(7,1fr);overflow:hidden}.kpi{min-height:88px;padding:14px;border-right:1px solid var(--line);display:flex;gap:12px;align-items:center;cursor:pointer}.kpi:last-child{border-right:0}.kpi.active{box-shadow:inset 0 0 0 2px var(--primary);background:var(--primary-soft)}
.ico{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;font-weight:700}.ico.blue{background:var(--blue-bg);color:var(--blue)}.ico.green{background:var(--green-bg);color:var(--green)}.ico.orange{background:var(--orange-bg);color:var(--orange)}.ico.purple{background:var(--purple-bg);color:var(--purple)}.ico.red{background:var(--red-bg);color:var(--red)}
.kpi span{display:block;font-size:12px;font-weight:600}.kpi b{display:block;font-size:24px;line-height:1.1;margin-top:2px}.kpi small{display:block;font-size:11px;color:var(--muted);margin-top:5px}
.progress{padding:14px}.section-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}.section-head b{font-size:14px}.section-head small{color:var(--primary);font-weight:600}.client-row{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.client{padding:12px 14px}.client-top{display:flex;justify-content:space-between;align-items:center;font-weight:600}.bar{height:7px;background:var(--muted-surface);border-radius:99px;margin:10px 0 8px;overflow:hidden}.fill{height:100%;background:#22c55e;border-radius:99px}
.table-card{overflow:hidden}.table-head{display:flex;justify-content:space-between;align-items:end;padding:12px 14px 8px}.table-head h2{font-size:14px;margin:0}.table-head p{font-size:11px;color:var(--muted);margin:3px 0 0}
.table-wrap{max-height:480px;overflow:auto;border-top:1px solid var(--line)}table{width:100%;border-collapse:separate;border-spacing:0;font-size:12px}thead th{position:sticky;top:0;z-index:3;background:var(--muted-surface);border-bottom:1px solid var(--line);text-align:left;color:var(--muted);font-size:11px;font-weight:600;padding:8px 10px;white-space:nowrap}.sort{border:0;background:transparent;color:inherit;font-weight:700;cursor:pointer;padding:0}.quick{margin-top:5px;width:100%;height:26px;border:1px solid var(--line);border-radius:6px;background:#fff;font-size:11px;color:var(--ink)}
tbody td{border-bottom:1px solid var(--line);padding:9px 10px;vertical-align:middle;white-space:nowrap;height:52px}tbody tr{cursor:pointer}tbody tr:hover{background:#fafbfc}tbody tr.selected{background:#f4f1ff}.sub{display:block;color:var(--muted);font-size:11px;margin-top:3px}.company{font-weight:600}.avatar-sm{width:24px;height:24px;border-radius:50%;display:inline-grid;place-items:center;margin-right:8px;background:var(--gray-bg);color:var(--gray);font-size:11px;font-weight:700}.avatar-sm.gbs{background:var(--purple-bg);color:var(--purple)}.avatar-sm.clickie{background:#fef3c7;color:#b45309}.avatar-sm.bambutech{background:var(--green-bg);color:var(--green)}
.chip,.pill{display:inline-flex;align-items:center;justify-content:center;gap:6px;border-radius:7px;padding:6px 10px;min-width:104px;font-size:12px;font-weight:600;border:1px solid transparent}.chip:before{content:"";width:7px;height:7px;border-radius:99px;background:currentColor}.pill{appearance:none;outline:0;cursor:pointer}.green{background:var(--green-bg);color:var(--green)}.orange{background:var(--orange-bg);color:var(--orange)}.red{background:var(--red-bg);color:var(--red)}.purple{background:var(--purple-bg);color:var(--purple)}.blue{background:var(--blue-bg);color:var(--blue)}.gray{background:var(--gray-bg);color:var(--gray)}
.action{border:0;background:transparent;color:var(--primary);font-size:18px;font-weight:700;cursor:pointer}.drawer{padding:0;position:sticky;top:10px;height:calc(100vh - 20px);min-height:0;max-height:calc(100vh - 20px);display:flex;flex-direction:column;overflow:hidden}.drawer.hidden{display:none}.drawer-fixed{flex:0 0 auto;padding:12px 14px 0;background:var(--surface);border-bottom:1px solid var(--line)}.drawer-top{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:8px}.drawer h2{font-size:15px;margin:0;line-height:1.2}.drawer-title-sub{font-size:11px;color:var(--muted);margin-top:2px}.close{border:0;background:transparent;color:var(--muted);font-size:20px;cursor:pointer}
.summary{display:grid;grid-template-columns:1.18fr 1fr 1fr 1fr;gap:6px;margin:8px 0}.sum{border:1px solid var(--line);border-radius:8px;padding:6px 7px;min-width:0;background:#fff}.sum.final-state{border-color:#d8cffd;background:var(--primary-soft)}.sum small{display:block;font-size:9.5px;color:var(--muted);font-weight:700;text-transform:uppercase;margin-bottom:3px}.sum.final-state small{color:var(--primary)}.sum .chip{min-width:0;width:100%;padding:4px 6px;font-size:11px;justify-content:flex-start}.meta{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin:0 0 10px}.meta div{border:0;border-top:1px solid var(--line);padding:6px 0 0;min-width:0}.meta small{display:block;color:var(--muted);font-size:10px;font-weight:600}.meta b,.meta select{display:block;margin-top:2px;font-size:12px;font-weight:600;max-width:100%;overflow:hidden;text-overflow:ellipsis}.meta select{border:0;background:transparent;outline:0}.alertline{grid-column:1/-1;border-top:1px solid #fed7aa!important;background:#fff7ed;border-radius:7px;padding:6px 8px!important}.alertline small{color:var(--orange)}.alertline.final{background:#f5f3ff;border-top-color:#ddd6fe!important}.alertline.final small{color:var(--primary)}
.tabs{display:grid;grid-template-columns:repeat(5,1fr);gap:4px;background:var(--muted-surface);border:1px solid var(--line);border-radius:10px;padding:4px;margin:8px 0 10px}.tabs button{border:1px solid transparent;background:transparent;border-radius:7px;padding:8px 5px;font-size:12px;font-weight:650;color:var(--muted);cursor:pointer}.tabs button.active{color:var(--primary);background:#fff;border-color:#d8cffd;box-shadow:0 1px 2px rgba(16,24,40,.08)}.panel{overflow:auto;padding:12px 14px 14px;flex:1}.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.field2 label{display:block;font-size:10.5px;color:var(--muted);font-weight:600;margin-bottom:3px}.field2 input,.field2 select,.field2 textarea{width:100%;border:1px solid var(--line);border-radius:8px;background:var(--surface);min-height:34px;padding:7px 9px;font-size:13px;outline:0}.field2 textarea{min-height:68px;resize:vertical}.wide{grid-column:1/-1}.context{background:var(--orange-bg);border:1px solid #fde2a8;border-radius:10px;padding:9px;margin-bottom:9px}.block-title{display:block;font-size:13px;margin-bottom:7px}.info-section{border-top:1px solid var(--line);padding-top:10px;margin-top:10px}.info-section:first-child{border-top:0;padding-top:0;margin-top:0}.section-title{font-size:13px;font-weight:700;margin:0 0 8px;color:var(--ink)}.btn-row{display:flex;gap:8px;justify-content:flex-end;margin-top:10px}.primary,.ghost{border-radius:8px;padding:8px 11px;font-size:12.5px;font-weight:600;cursor:pointer}.primary{border:0;background:var(--primary);color:white}.ghost{border:1px dashed var(--line);background:white;color:var(--primary)}
.evidence{display:grid;grid-template-columns:1fr 1fr;gap:8px}.evi{border:1px solid var(--line);border-radius:8px;padding:9px;background:white;font-size:12px;font-weight:600}.evi small{display:block;color:var(--muted);font-weight:500;margin-top:3px}.read{border:1px solid var(--line);border-radius:10px;padding:9px;background:white}.read p{margin:6px 0;font-size:13px}.history,.timeline{border-left:2px solid var(--line);padding-left:12px;margin-left:6px}.hist,.tl{position:relative;margin-bottom:12px}.hist small,.tl small{color:var(--muted)}.hist b,.tl b{display:block;font-size:13px;margin:2px 0}.hist:before,.tl:before{content:"";position:absolute;left:-17px;top:3px;width:8px;height:8px;border-radius:99px;background:var(--primary)}.event-meta{font-size:11px;color:var(--muted);margin-top:2px}.event-badge{display:inline-flex;border-radius:999px;padding:2px 6px;font-size:10.5px;font-weight:700;background:var(--gray-bg);color:var(--gray);margin-left:4px}.event-badge.manual{background:var(--purple-bg);color:var(--purple)}.event-badge.client{background:var(--blue-bg);color:var(--blue)}.manual-form{border:1px solid var(--line);border-radius:10px;background:#fff;padding:10px;margin-bottom:12px}.manual-actions{display:flex;gap:6px;margin-top:5px}.mini{border:1px solid var(--line);background:#fff;border-radius:6px;padding:4px 7px;font-size:11px;cursor:pointer;color:var(--primary)}.save-note{position:fixed;right:24px;bottom:18px;background:#101828;color:white;border-radius:8px;padding:10px 12px;font-size:12px;font-weight:600;box-shadow:0 8px 24px rgba(16,24,40,.22);z-index:20}
@media(max-width:1200px){.layout.open{grid-template-columns:minmax(0,1fr) 420px}.summary{grid-template-columns:1fr 1fr}.grid,.meta{grid-template-columns:1fr}.tabs button{font-size:11px;padding:7px 3px}}
@media(max-width:760px){.app{min-width:0}.layout.open{grid-template-columns:1fr}.drawer{position:relative;height:auto;max-height:none}.summary{grid-template-columns:1fr}.tabs{grid-template-columns:1fr 1fr}.panel{max-height:none}}
</style>
</head>
<body>
<div class="app">
  <header class="top">
    <div class="brand"><div class="hamb">&#9776;</div><span class="mark"></span><div class="title"><h1>Seguimiento de reuniones</h1><p>Panel operativo</p></div></div>
    <div class="user"><button class="bell" id="bell" onclick="toggleNotifications()" aria-label="Notificaciones"></button><div class="avatar"></div><div class="usertext"><b>Francisca / Yanina</b>Panel interno</div></div>
  </header>
  <div class="notif" id="notifications" hidden></div>
  <div class="layout" id="layout">
    <main class="main">
      <section class="card">
        <div class="filters">
          <div class="field"><span>&#8981;</span><input id="q" placeholder="Buscar empresa, contacto, cargo, correo..." oninput="setFilter('q',this.value)"></div>
          <div class="field"><label>Cliente</label><select id="fClient" onchange="setFilter('client',this.value)"></select></div>
          <div class="field date-range"><label>Rango de fechas</label><input id="fDateFrom" type="date" onchange="setFilter('dateFrom',this.value)"><input id="fDateTo" type="date" onchange="setFilter('dateTo',this.value)"><button class="clear-date" onclick="resetDateRange()" title="Restablecer rango">x</button></div>
          <div class="field"><label>SDR</label><select id="fSdr" onchange="setFilter('sdr',this.value)"></select></div>
          <div class="field"><button id="moreBtn" onclick="toggleMore()">Mas filtros</button></div>
        </div>
        <div class="extra" id="extraFilters">
          <div class="field"><label>Etapa Agenda</label><select id="fStatus" onchange="setFilter('status',this.value)"></select></div>
          <div class="field"><label>Evaluacion CP</label><select id="fCp" onchange="setFilter('cp',this.value)"></select></div>
          <div class="field"><label>Evaluacion Cliente</label><select id="fClientVal" onchange="setFilter('clientVal',this.value)"></select></div>
          <div class="field"><label>Estado Final</label><select id="fFinal" onchange="setFilter('final',this.value)"></select></div>
          <div class="field"><label>Pais</label><select id="fCountry" onchange="setFilter('country',this.value)"></select></div>
          <div class="field"><label>Estado del Caso</label><select id="fCaseStatus" onchange="setFilter('caseStatus',this.value)"></select></div>
        </div>
        <div class="active-filters" id="activeFilters"></div>
      </section>
      <section class="card kpis" id="kpis"></section>
      <section class="card progress">
        <div class="section-head"><b>Avance por cliente <span class="sub" style="display:inline">reuniones validas CP / meta contractual</span></b><small>Ver todos los clientes</small></div>
        <div class="client-row" id="clientProgress"></div>
      </section>
      <section class="card table-card">
        <div class="table-head"><div><h2>Tabla principal</h2><p>Filtros, KPIs, avance y tabla usan el mismo estado central.</p></div></div>
        <div class="table-wrap"><table><thead id="thead"></thead><tbody id="rows"></tbody></table></div>
      </section>
    </main>
    <aside class="card drawer hidden" id="drawer">
      <div class="drawer-fixed">
        <div class="drawer-top"><div><h2 id="detailTitle">Detalle de reunion</h2><div class="drawer-title-sub" id="detailSubtitle"></div></div><button class="close" onclick="closeDetail()" aria-label="Cerrar">&times;</button></div>
        <div class="summary" id="summary"></div>
        <div class="meta" id="meta"></div>
        <div class="tabs" id="tabs"></div>
      </div>
      <div class="panel" id="panel"></div>
    </aside>
  </div>
</div>
<script>
const statuses=["Reunion futura","Reunion realizada","Reunion cancelada","Reagendar reunion"];
const cps=["Pendiente","Valida","No valida"];
const clientVals=["Pendiente","Confirmar","Solicitar revision"];
const finalOptions=["Pendiente","Reunion valida","Reunion no valida","Reunion cancelada","Reagendar reunion"];
const caseStatusOptions=["Abierto","En evaluacion CP","Esperando cliente","En revision","Cerrado"];
const cancellationActors=["Cliente","Prospecto","SDR","Conprospeccion"];
const rescheduleReasons=["Conflicto de agenda","Vacaciones","Enfermedad","Problema tecnico","Esperando informacion","Cambio interno","Otro"];
const clientRevisionReasons=["No corresponde al ICP","Cargo incorrecto","Empresa incorrecta","Competencia","Sin interes comercial","BANT insuficiente","Informacion incorrecta","Informacion incompleta","Otro"];
const clientGoals={GBS:45,Clickie:6,BambuTech:100};
let meetings=[
 {id:1,date:"23/06/2026",time:"11:00 AM",client:"GBS",company:"TechNova S.A.",contact:"Juan Perez",role:"CTO",sdr:"Mariana R.",status:"Reunion realizada",cp:"Valida",clientVal:"Confirmar",final:"Reunion valida",caseStatus:"Cerrado",email:"juan.perez@technova.cl",phone:"+56 9 1111 2222",country:"Chile",industry:"Tecnologia",website:"technova.cl",linkedin:"",ghlContact:"https://app.gohighlevel.com/contact/101",ghlOpp:"https://app.gohighlevel.com/opportunity/101",meet:"https://meet.google.com/demo-gbs",info:"Prospecto con necesidad activa de automatizar seguimiento comercial.",icp:"Cumple",bant:{Budget:true,Authority:true,Need:true,Timeline:false},just:"La reunion cumplio con el objetivo de validacion de necesidad y autoridad.",next:"Enviar propuesta inicial.",notes:"Validar presupuesto con finanzas.",finalReason:"Cumple ICP y BANT suficiente.",finalClientText:"Reunion marcada como valida por Conprospeccion.",finalInternalNote:"Cierre aprobado.",evidence:[{type:"Grabacion",name:"Grabacion disponible",valid:true},{type:"Resumen IA",name:"Resumen ejecutivo",valid:true}],clientReason:"Confirmada por cliente.",clientComment:"La reunion corresponde a una oportunidad valida.",clientDate:"24/06/2026 15:10",clientActor:"Juan Perez",clientEvidence:"",cpResponse:"",history:[{when:"24/06/2026 15:10",user:"Cliente GBS",field:"Evaluacion Cliente",from:"Pendiente",to:"Confirmar"}]},
 {id:2,date:"23/06/2026",time:"09:30 AM",client:"Clickie",company:"Clickie Media",contact:"Ana Gomez",role:"Marketing Manager",sdr:"Sebastian L.",status:"Reunion realizada",cp:"Pendiente",clientVal:"Pendiente",final:"Pendiente",caseStatus:"En evaluacion CP",email:"ana@clickie.cl",phone:"+56 9 3333 4444",country:"Chile",industry:"Marketing",website:"clickie.cl",linkedin:"",ghlContact:"",ghlOpp:"",meet:"",info:"Agencia interesada en automatizar prospeccion outbound.",icp:"No evaluado",bant:{Budget:false,Authority:true,Need:true,Timeline:false},just:"",next:"",notes:"",finalReason:"",finalClientText:"",finalInternalNote:"",evidence:[],clientReason:"",clientComment:"",clientDate:"",clientActor:"Ana Gomez",clientEvidence:"",cpResponse:"",history:[]},
 {id:3,date:"22/06/2026",time:"04:00 PM",client:"BambuTech",company:"BambuTech Services",contact:"Luis Ramirez",role:"CEO",sdr:"Valentina G.",status:"Reunion realizada",cp:"Pendiente",clientVal:"Solicitar revision",final:"Pendiente",caseStatus:"En revision",email:"luis@bambutech.com",phone:"+52 55 1234 5678",country:"Mexico",industry:"Tecnologia",website:"bambutech.com",linkedin:"",ghlContact:"",ghlOpp:"",meet:"https://meet.google.com/demo-bambu",info:"Empresa prioritaria con preparacion registrada.",icp:"Cumple",bant:{Budget:false,Authority:true,Need:true,Timeline:false},just:"Falta evidencia completa de presupuesto y timeline.",next:"Responder solicitud de revision.",notes:"El cliente pidio revisar correo de confirmacion.",finalReason:"",finalClientText:"",finalInternalNote:"",evidence:[{type:"Transcripcion",name:"Transcripcion disponible",valid:true}],clientReason:"Informacion incompleta",clientComment:"Solicitan ver el correo donde se confirmo la nueva fecha.",clientDate:"23/06/2026 10:15",clientActor:"Luis Ramirez",clientEvidence:"Correo reenviado por cliente",cpResponse:"",history:[{when:"23/06/2026 10:15",user:"Luis Ramirez",field:"Evaluacion Cliente",from:"Pendiente",to:"Solicitar revision"}]},
 {id:4,date:"22/06/2026",time:"02:30 PM",client:"GBS",company:"Industrias del Norte",contact:"Carla Mendez",role:"Gerente Financiero",sdr:"Mariana R.",status:"Reunion futura",cp:"Pendiente",clientVal:"Pendiente",final:"Pendiente",caseStatus:"Abierto",email:"",phone:"",country:"Chile",industry:"Industrial",website:"",linkedin:"",ghlContact:"",ghlOpp:"",meet:"https://meet.google.com/demo-futura",info:"Preparar preguntas de presupuesto.",icp:"No evaluado",bant:{Budget:false,Authority:false,Need:false,Timeline:false},just:"",next:"",notes:"",finalReason:"",finalClientText:"",finalInternalNote:"",evidence:[],clientReason:"",clientComment:"",clientDate:"",clientActor:"Carla Mendez",clientEvidence:"",cpResponse:"",history:[]},
 {id:5,date:"21/06/2026",time:"10:00 AM",client:"GBS",company:"Grupo Andino",contact:"Diego Torres",role:"Gerente Operaciones",sdr:"Sebastian L.",status:"Reunion cancelada",cp:"Pendiente",clientVal:"Pendiente",final:"Pendiente",caseStatus:"Abierto",email:"",phone:"",country:"Peru",industry:"Logistica",website:"",linkedin:"",ghlContact:"",ghlOpp:"",meet:"",info:"",icp:"No evaluado",bant:{Budget:false,Authority:false,Need:false,Timeline:false},just:"",next:"",notes:"",finalReason:"",finalClientText:"",finalInternalNote:"",evidence:[],clientReason:"",clientComment:"",clientDate:"",clientActor:"Diego Torres",clientEvidence:"",cpResponse:"",cancelWho:"Cliente",cancelReason:"Cliente no asistio",cancelComment:"Cliente indico no continuar.",history:[]},
 {id:6,date:"20/06/2026",time:"03:00 PM",client:"BambuTech",company:"Constructora Alfa",contact:"Rodrigo Silva",role:"Gerente General",sdr:"Valentina G.",status:"Reagendar reunion",cp:"Pendiente",clientVal:"Pendiente",final:"Pendiente",caseStatus:"Esperando cliente",email:"",phone:"",country:"Argentina",industry:"Construccion",website:"",linkedin:"",ghlContact:"",ghlOpp:"",meet:"",info:"",icp:"No evaluado",bant:{Budget:false,Authority:true,Need:true,Timeline:false},just:"",next:"",notes:"",finalReason:"",finalClientText:"",finalInternalNote:"",evidence:[],clientReason:"",clientComment:"",clientDate:"",clientActor:"Rodrigo Silva",clientEvidence:"",cpResponse:"",rescheduleWho:"Cliente",rescheduleReason:"Conflicto de agenda",rescheduleOld:"20/06/2026 03:00 PM",rescheduleNew:"28/06/2026 03:00 PM",history:[]},
 {id:7,date:"19/06/2026",time:"11:30 AM",client:"Clickie",company:"Publicidad Plus",contact:"Sofia Vargas",role:"Directora Comercial",sdr:"Mariana R.",status:"Reunion realizada",cp:"Valida",clientVal:"Pendiente",final:"Pendiente",caseStatus:"Esperando cliente",email:"sofia@pubplus.cl",phone:"",country:"Chile",industry:"Publicidad",website:"",linkedin:"",ghlContact:"",ghlOpp:"",meet:"",info:"Buen fit, timeline por confirmar.",icp:"Cumple",bant:{Budget:true,Authority:true,Need:true,Timeline:false},just:"Buen fit, timeline por confirmar.",next:"Enviar propuesta.",notes:"",finalReason:"",finalClientText:"",finalInternalNote:"",evidence:[{type:"Resumen IA",name:"Disponible",valid:true}],clientReason:"",clientComment:"",clientDate:"",clientActor:"Sofia Vargas",clientEvidence:"",cpResponse:"",history:[]}
];
const storageKey="cp_meetings_v5_poc_detail_v2";
let savedMeetings=null;try{savedMeetings=JSON.parse(localStorage.getItem(storageKey)||"null")}catch(e){savedMeetings=null}
if(Array.isArray(savedMeetings)){meetings=savedMeetings}
meetings=meetings.map(m=>({...m,caseStatus:m.caseStatus||"Abierto",clientActor:m.clientActor||m.contact||"",clientTimeline:m.clientTimeline||buildClientTimeline(m)}));
let selected=null, tab="Evaluacion CP", panelOpen=false, more=false, notifOpen=false;
let filters=defaultFilters();
let sortState={key:"dateTime",dir:"desc"};
function defaultRange(){const now=new Date();const first=new Date(now.getFullYear(),now.getMonth(),1);const last=new Date(now.getFullYear(),now.getMonth()+1,0);return {dateFrom:iso(first),dateTo:iso(last)}}
function defaultFilters(){return {q:"",client:"Todos",sdr:"Todos",status:"Todos",cp:"Todos",clientVal:"Todos",final:"Todos",country:"Todos",caseStatus:"Todos",...defaultRange()}}
function iso(d){return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`}
function esc(s){return String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[m]))}
function opt(values,current){return values.map(v=>`<option value="${esc(v)}" ${v===current?"selected":""}>${esc(v)}</option>`).join("")}
function parseDate(s){const [d,m,y]=String(s).split("/");return y&&m&&d?`${y}-${m.padStart(2,"0")}-${d.padStart(2,"0")}`:""}
function dtValue(m){const d=parseDate(m.date);const hour=m.time.includes("PM")&&m.time.slice(0,2)!=="12"?Number(m.time.slice(0,2))+12:Number(m.time.slice(0,2));return `${d} ${String(hour).padStart(2,"0")}${m.time.slice(2,5)}`}
function finalStatus(m){return m.final||"Pendiente"}
function finalDisplay(m){return finalStatus(m)==="Pendiente"?"Pendiente de cierre":finalStatus(m)}
function persist(){localStorage.setItem(storageKey,JSON.stringify(meetings))}
function notify(msg){let n=document.getElementById("saveNote");if(!n){n=document.createElement("div");n.id="saveNote";n.className="save-note";document.body.appendChild(n)}n.textContent=msg;clearTimeout(window.__saveNoteTimer);window.__saveNoteTimer=setTimeout(()=>n.remove(),1800)}
function saveSection(section){const m=current();addHistory(m,`Guardar ${section}`,"Pendiente","Guardado");persist();notify(`${section} guardado`);render()}
function buildClientTimeline(m){const items=[{when:"Pendiente inicial",actor:"Portal cliente",status:"Pendiente",reason:"",comment:"Esperando accion del cliente"}];if(m.clientVal&&m.clientVal!=="Pendiente"){items.push({when:m.clientDate||"Sin fecha registrada",actor:m.clientActor||m.contact||"Cliente",status:m.clientVal,reason:m.clientReason||"",comment:m.clientComment||""})}if(m.cpResponse){items.push({when:"Respuesta interna",actor:"Conprospeccion",status:"Respuesta enviada",reason:"",comment:m.cpResponse})}return items}
function finalAlert(m){if(finalStatus(m)==="Pendiente")return"Estado final pendiente de cierre administrativo por Conprospeccion";return""}
function operationalAlert(m){if(m.clientVal==="Solicitar revision")return"Cliente solicito revision: requiere respuesta interna";if(m.status==="Reunion cancelada")return"Registrar motivo de cancelacion y evaluar CP si corresponde";if(m.status==="Reagendar reunion")return"Registrar nueva fecha y evaluar CP si corresponde";if(m.cp!=="Pendiente"&&finalStatus(m)==="Pendiente")return"Evaluacion lista, caso aun sin cierre administrativo";return"Sin alertas operativas"}
function tone(v){if(["Valida","Confirmar","Reunion realizada","Cumple","Reunion valida"].includes(v))return"green";if(["Pendiente","Pendiente de cierre","Reagendar reunion"].includes(v))return"orange";if(["Reunion futura"].includes(v))return"blue";if(["Solicitar revision","En revision"].includes(v))return"purple";if(["No valida","Reunion cancelada","Reunion no valida"].includes(v))return"red";return"gray"}
function current(){return meetings.find(m=>m.id===selected)||meetings[0]}
function addHistory(m,field,from,to){if(JSON.stringify(from)===JSON.stringify(to))return;m.history=m.history||[];m.history.unshift({when:new Date().toLocaleString("es-CL"),user:"Francisca / Yanina",field,from,to})}
function labelField(f){return {status:"Etapa Agenda",cp:"Evaluacion CP",clientVal:"Evaluacion Cliente",final:"Estado Final",caseStatus:"Estado del Caso",sdr:"SDR asignada",icp:"ICP",info:"Informacion reunion",just:"Justificacion CP",notes:"Notas internas",cpResponse:"Respuesta CP"}[f]||f}
function recordClientEvent(m,field,from,to){if(JSON.stringify(from)===JSON.stringify(to))return;const status=field==="clientVal"?to:m.clientVal;const reason=field==="clientReason"?to:m.clientReason;const comment=field==="clientComment"?to:(field==="cpResponse"?`Respuesta CP: ${to}`:m.clientComment);m.clientTimeline=m.clientTimeline||[];m.clientTimeline.unshift({when:new Date().toLocaleString("es-CL"),actor:field==="cpResponse"?"Conprospeccion":(m.clientActor||m.contact||"Cliente"),status,reason:reason||"",comment:comment||""})}
function setField(id,field,value){const m=meetings.find(x=>x.id===id);const old=m[field];m[field]=value;addHistory(m,labelField(field),old,value);if(["clientVal","clientReason","clientComment","clientEvidence","cpResponse"].includes(field)){recordClientEvent(m,field,old,value)}selected=id;panelOpen=true;if(field==="cp"&&value!=="Pendiente")tab="Evaluacion CP";if(field==="status"&&["Reunion cancelada","Reagendar reunion"].includes(value))tab="Informacion";if(field==="final")tab="Estado Final";if(field==="clientVal")tab="Evaluacion Cliente";persist();render()}
function setFilter(k,v){filters[k]=v;syncDependent(k);render()}
function syncDependent(k){if(k==="client"){const opts=optionSets(applyFilters({ignore:["sdr","country","status","cp","clientVal","final","caseStatus"]}));["sdr","country","status","cp","clientVal","final","caseStatus"].forEach(f=>{if(filters[f]!=="Todos"&&!opts[f].includes(filters[f]))filters[f]="Todos"})}}
function toggleMore(){more=!more;render()}
function resetDateRange(){Object.assign(filters,defaultRange());render()}
function clearFilter(k){if(k==="date"){Object.assign(filters,defaultRange())}else{filters[k]=k==="q"?"":"Todos"}render()}
function clearAll(){filters=defaultFilters();render()}
function applyFilters(options={}){const ignore=options.ignore||[];return meetings.filter(m=>{const hay=`${m.company} ${m.contact} ${m.role} ${m.email} ${m.phone}`.toLowerCase();const md=parseDate(m.date);if(!ignore.includes("q")&&filters.q&&!hay.includes(filters.q.toLowerCase()))return false;if(!ignore.includes("date")&&filters.dateFrom&&md<filters.dateFrom)return false;if(!ignore.includes("date")&&filters.dateTo&&md>filters.dateTo)return false;if(!ignore.includes("client")&&filters.client!=="Todos"&&m.client!==filters.client)return false;if(!ignore.includes("sdr")&&filters.sdr!=="Todos"&&m.sdr!==filters.sdr)return false;if(!ignore.includes("status")&&filters.status!=="Todos"&&m.status!==filters.status)return false;if(!ignore.includes("cp")&&filters.cp!=="Todos"&&m.cp!==filters.cp)return false;if(!ignore.includes("clientVal")&&filters.clientVal!=="Todos"&&m.clientVal!==filters.clientVal)return false;if(!ignore.includes("final")&&filters.final!=="Todos"&&finalStatus(m)!==filters.final)return false;if(!ignore.includes("country")&&filters.country!=="Todos"&&m.country!==filters.country)return false;if(!ignore.includes("caseStatus")&&filters.caseStatus!=="Todos"&&m.caseStatus!==filters.caseStatus)return false;return true})}
function sortRows(rows){const dir=sortState.dir==="asc"?1:-1;return [...rows].sort((a,b)=>{const av=sortState.key==="dateTime"?dtValue(a):String(sortValue(a,sortState.key));const bv=sortState.key==="dateTime"?dtValue(b):String(sortValue(b,sortState.key));return av>bv?dir:av<bv?-dir:0})}
function sortValue(m,k){return k==="final"?finalStatus(m):m[k]||""}
function setSort(k){if(sortState.key===k)sortState.dir=sortState.dir==="asc"?"desc":"asc";else sortState={key:k,dir:k==="dateTime"?"desc":"asc"};render()}
function optionSets(baseRows=meetings){const uniq=k=>[...new Set(baseRows.map(m=>k==="final"?finalStatus(m):m[k]).filter(Boolean))];return {client:[...new Set(baseRows.map(m=>m.client))],sdr:uniq("sdr"),country:uniq("country"),status:uniq("status"),cp:uniq("cp"),clientVal:uniq("clientVal"),final:uniq("final"),caseStatus:uniq("caseStatus")}}
function activeFilterCount(){let c=0;["status","cp","clientVal","final","country","caseStatus"].forEach(k=>{if(filters[k]!=="Todos")c++});return c}
function filterActive(){const d=defaultRange();return filters.q||filters.client!=="Todos"||filters.sdr!=="Todos"||filters.dateFrom!==d.dateFrom||filters.dateTo!==d.dateTo||["status","cp","clientVal","final","country","caseStatus"].some(k=>filters[k]!=="Todos")}
function renderFilters(rows){const opts=optionSets(applyFilters({ignore:["sdr","country","status","cp","clientVal","final","caseStatus"]}));document.getElementById("q").value=filters.q;document.getElementById("fClient").innerHTML=opt(["Todos",...optionSets(meetings).client],filters.client);document.getElementById("fDateFrom").value=filters.dateFrom;document.getElementById("fDateTo").value=filters.dateTo;document.getElementById("fSdr").innerHTML=opt(["Todos",...opts.sdr],filters.sdr);document.getElementById("fStatus").innerHTML=opt(["Todos",...opts.status],filters.status);document.getElementById("fCp").innerHTML=opt(["Todos",...opts.cp],filters.cp);document.getElementById("fClientVal").innerHTML=opt(["Todos",...opts.clientVal],filters.clientVal);document.getElementById("fFinal").innerHTML=opt(["Todos",...opts.final],filters.final);document.getElementById("fCountry").innerHTML=opt(["Todos",...opts.country],filters.country);document.getElementById("fCaseStatus").innerHTML=opt(["Todos",...opts.caseStatus],filters.caseStatus);document.getElementById("extraFilters").classList.toggle("open",more);document.getElementById("moreBtn").textContent=`Mas filtros${activeFilterCount()?` (${activeFilterCount()})`:""}`;renderActiveFilters()}
function renderActiveFilters(){const d=defaultRange();const labels={q:"Buscar",client:"Cliente",sdr:"SDR",status:"Etapa",cp:"CP",clientVal:"Cliente",final:"Final",country:"Pais",caseStatus:"Caso"};const chips=[];Object.keys(labels).forEach(k=>{if((k==="q"&&filters.q)||(k!=="q"&&filters[k]&&filters[k]!=="Todos"))chips.push(`<span class="filter-chip">${labels[k]}: ${esc(filters[k])}<button onclick="clearFilter('${k}')">x</button></span>`)});if(filters.dateFrom!==d.dateFrom||filters.dateTo!==d.dateTo)chips.push(`<span class="filter-chip">Fecha: ${filters.dateFrom} / ${filters.dateTo}<button onclick="clearFilter('date')">x</button></span>`);if(chips.length)chips.push(`<button class="clear-all" onclick="clearAll()">Limpiar filtros</button>`);document.getElementById("activeFilters").innerHTML=chips.join("")}
function renderKpis(rows){const total=rows.length||1;const cards=[["Total reuniones",rows.length,"Todas las reuniones","blue","T",()=>{filters.status="Todos";filters.cp="Todos";filters.clientVal="Todos";filters.final="Todos"}],["Pendiente CP",rows.filter(x=>x.cp==="Pendiente").length,pct(rows.filter(x=>x.cp==="Pendiente").length,total),"orange","P",()=>toggleFilter("cp","Pendiente")],["CP valida",rows.filter(x=>x.cp==="Valida").length,pct(rows.filter(x=>x.cp==="Valida").length,total),"green","V",()=>toggleFilter("cp","Valida")],["Solicita revision",rows.filter(x=>x.clientVal==="Solicitar revision").length,pct(rows.filter(x=>x.clientVal==="Solicitar revision").length,total),"purple","R",()=>toggleFilter("clientVal","Solicitar revision")],["Final valida",rows.filter(x=>finalStatus(x)==="Reunion valida").length,pct(rows.filter(x=>finalStatus(x)==="Reunion valida").length,total),"green","F",()=>toggleFilter("final","Reunion valida")],["Reagendar",rows.filter(x=>x.status==="Reagendar reunion").length,pct(rows.filter(x=>x.status==="Reagendar reunion").length,total),"orange","A",()=>toggleFilter("status","Reagendar reunion")],["No validas final",rows.filter(x=>finalStatus(x)==="Reunion no valida").length,pct(rows.filter(x=>finalStatus(x)==="Reunion no valida").length,total),"red","X",()=>toggleFilter("final","Reunion no valida")]];window.__kpiActions=cards.map(c=>c[5]);document.getElementById("kpis").innerHTML=cards.map((i,idx)=>`<div class="kpi ${kpiActive(i[0])?"active":""}" onclick="__kpiActions[${idx}]();render()"><div class="ico ${i[3]}">${i[4]}</div><div><span>${i[0]}</span><b>${i[1]}</b><small>${i[2]}</small></div></div>`).join("")}
function kpiActive(label){return label==="Pendiente CP"&&filters.cp==="Pendiente"||label==="CP valida"&&filters.cp==="Valida"||label==="Solicita revision"&&filters.clientVal==="Solicitar revision"||label==="Final valida"&&filters.final==="Reunion valida"||label==="Reagendar"&&filters.status==="Reagendar reunion"||label==="No validas final"&&filters.final==="Reunion no valida"}
function toggleFilter(k,v){filters[k]=filters[k]===v?"Todos":v}
function pct(n,total){return total?`${((n/total)*100).toFixed(1)}% del total`:"0% del total"}
function renderProgress(rows){let codes=[...new Set(rows.map(m=>m.client))];if(filters.client!=="Todos")codes=[filters.client];document.getElementById("clientProgress").innerHTML=codes.map(code=>{const goal=clientGoals[code]||0;const valid=rows.filter(m=>m.client===code&&m.cp==="Valida").length;const p=goal?Math.round(valid/goal*100):0;return `<div class="card client"><div class="client-top"><span>${code}</span><span>${valid} / ${goal}</span></div><div class="bar"><div class="fill" style="width:${Math.min(p,100)}%"></div></div><div style="text-align:right;font-weight:700;font-size:12px">${p}%</div></div>`}).join("")||`<div class="sub">Sin reuniones para los filtros aplicados.</div>`}
function renderHead(){const cols=[["dateTime","Fecha y Hora"],["client","Cliente"],["company","Empresa"],["sdr","SDR"],["contact","Contacto"],["status","Etapa Agenda"],["cp","Evaluacion CP"],["clientVal","Evaluacion Cliente"],["final","Estado Final"],["actions","Acciones"]];const q=(k,id,opts)=>["client","sdr","status","cp","clientVal","final"].includes(k)?`<select class="quick" onchange="setFilter('${k}',this.value)">${opt(["Todos",...opts],filters[k])}</select>`:"";const allOpts=optionSets(applyFilters({ignore:["client","sdr","status","cp","clientVal","final"]}));document.getElementById("thead").innerHTML=`<tr>${cols.map(c=>`<th>${c[0]==="actions"?c[1]:`<button class="sort" onclick="setSort('${c[0]}')">${c[1]} ${sortState.key===c[0]?(sortState.dir==="asc"?"↑":"↓"):""}</button>`}${q(c[0],c[0],allOpts[c[0]]||[])}</th>`).join("")}</tr>`}
function renderRows(rows){document.getElementById("rows").innerHTML=sortRows(rows).map(m=>`<tr class="${m.id===selected?"selected":""}" onclick="openDetail(${m.id})"><td><b>${m.date}</b><span class="sub">${m.time}</span></td><td><span class="avatar-sm ${m.client.toLowerCase()}">${m.client[0]}</span><span class="company">${m.client}</span></td><td>${esc(m.company)}</td><td>${esc(m.sdr)||"<span class='sub'>Sin asignar</span>"}</td><td>${esc(m.contact)}<span class="sub">${esc(m.role)}</span></td><td onclick="event.stopPropagation()"><select class="pill ${tone(m.status)}" onchange="setField(${m.id},'status',this.value)">${opt(statuses,m.status)}</select></td><td onclick="event.stopPropagation()"><select class="pill ${tone(m.cp)}" onchange="setField(${m.id},'cp',this.value)">${opt(cps,m.cp)}</select></td><td onclick="event.stopPropagation()"><select class="pill ${tone(m.clientVal)}" onchange="setField(${m.id},'clientVal',this.value)">${opt(clientVals,m.clientVal)}</select></td><td onclick="event.stopPropagation()"><select class="pill ${tone(finalStatus(m))}" onchange="setField(${m.id},'final',this.value)">${opt(finalOptions,finalStatus(m))}</select></td><td><button class="action" onclick="event.stopPropagation();openDetail(${m.id})">›</button></td></tr>`).join("")}
function openDetail(id){selected=id;panelOpen=true;render()}
function closeDetail(){panelOpen=false;document.body.classList.remove("detail-open");render()}
function field(k,label,type="input"){const m=current();const val=esc(m[k]);return `<div class="field2 ${type==="textarea"?"wide":""}"><label>${label}</label>${type==="textarea"?`<textarea onchange="setField(${m.id},'${k}',this.value)">${val}</textarea>`:`<input value="${val}" onchange="setField(${m.id},'${k}',this.value)">`}</div>`}
function selectField(k,label,values){const m=current();return `<div class="field2"><label>${label}</label><select onchange="setField(${m.id},'${k}',this.value)">${opt(values,m[k])}</select></div>`}
function renderPanel(){if(!panelOpen)return;const m=current();document.getElementById("detailTitle").textContent=m.company||m.contact||"Detalle de reunion";document.getElementById("detailSubtitle").textContent=`${m.contact||"Sin contacto"} - ${m.client||"Sin cliente"}`;const states=[["Estado final",finalDisplay(m),"final-state"],["Agenda",m.status,""],["CP",m.cp,""],["Cliente",m.clientVal,""]];document.getElementById("summary").innerHTML=states.map(i=>`<div class="sum ${i[2]}"><small>${i[0]}</small><span class="chip ${tone(i[1])}" title="${esc(i[1])}">${esc(i[1])}</span></div>`).join("");const alert=operationalAlert(m);const fAlert=finalAlert(m);document.getElementById("meta").innerHTML=`<div><small>Cliente</small><b>${esc(m.client)}</b></div><div><small>Fecha y hora</small><b>${esc(m.date)} ${esc(m.time)}</b></div><div><small>SDR asignada</small><select onchange="setField(${m.id},'sdr',this.value)">${opt([...new Set(meetings.map(x=>x.sdr).filter(Boolean))],m.sdr)}</select></div><div><small>Estado del Caso</small><select onchange="setField(${m.id},'caseStatus',this.value)">${opt(caseStatusOptions,m.caseStatus)}</select></div>${fAlert?`<div class="alertline final"><small>Alerta final</small><b>${esc(fAlert)}</b></div>`:""}${alert&&alert!=="Sin alertas operativas"?`<div class="alertline"><small>Alerta operativa</small><b>${esc(alert)}</b></div>`:""}`;const tabs=["Informacion","Evaluacion CP","Evaluacion Cliente","Estado Final","Historial"];document.getElementById("tabs").innerHTML=tabs.map(t=>`<button class="${tab===t?"active":""}" onclick="tab='${t}';renderPanel()">${t}</button>`).join("");let html="";if(tab==="Informacion")html=infoTab(m);if(tab==="Evaluacion CP")html=cpTab(m);if(tab==="Evaluacion Cliente")html=clientTab(m);if(tab==="Estado Final")html=finalTab(m);if(tab==="Historial")html=historyTab(m);document.getElementById("panel").innerHTML=html}
function infoSection(title,body){return `<section class="info-section"><h3 class="section-title">${title}</h3><div class="grid">${body}</div></section>`}
function infoTab(m){let ctx="";if(m.status==="Reunion cancelada")ctx=`<div class="context"><b>Cancelacion</b><div class="grid">${selectField("cancelWho","Quien cancelo",cancellationActors)}${field("cancelReason","Motivo")}${field("cancelComment","Comentario","textarea")}</div><div class="btn-row"><button class="primary" onclick="saveSection('Cancelacion')">Guardar cancelacion</button></div></div>`;if(m.status==="Reagendar reunion")ctx=`<div class="context"><b>Reagendar reunion</b><div class="grid">${selectField("rescheduleWho","Quien solicita",cancellationActors)}${selectField("rescheduleReason","Motivo",rescheduleReasons)}${field("rescheduleOld","Fecha anterior")}${field("rescheduleNew","Nueva fecha")}${field("rescheduleComment","Comentario","textarea")}</div><div class="btn-row"><button class="primary" onclick="saveSection('Reagendamiento')">Guardar reagendamiento</button></div></div>`;return ctx+infoSection("Empresa",`${field("company","Nombre de empresa")}${field("industry","Industria")}${field("country","Pais")}${field("website","Sitio web")}${field("linkedinCompany","LinkedIn empresa")}${field("companyInfo","Informacion adicional empresa","textarea")}`)+infoSection("Contacto",`${field("contact","Nombre del contacto")}${field("role","Cargo")}${field("email","Correo electronico")}${field("phone","Telefono")}${field("linkedin","LinkedIn")}${field("contactInfo","Informacion adicional contacto","textarea")}`)+infoSection("Reunion",`${field("date","Fecha")}${field("time","Hora")}${field("sdr","SDR asignada")}${field("sourceChannel","Canal de origen")}${field("meet","Enlace reunion")}${field("ghlContact","Contacto GHL")}${field("ghlOpp","Oportunidad GHL")}${field("info","Informacion de preparacion","textarea")}${field("operationalNotes","Observaciones operativas","textarea")}`)+`<div class="btn-row"><button class="primary" onclick="saveSection('Informacion')">Guardar informacion</button></div>`}
function cpTab(m){return `<div class="grid"><div class="field2"><label>Evaluacion CP</label><select onchange="setField(${m.id},'cp',this.value)">${opt(cps,m.cp)}</select></div><div class="field2"><label>ICP</label><select onchange="setField(${m.id},'icp',this.value)">${opt(["No evaluado","Cumple","No cumple"],m.icp)}</select></div><div class="wide"><span class="block-title">BANT</span><div class="evidence">${Object.keys(m.bant).map(k=>`<label class="evi"><input type="checkbox" ${m.bant[k]?"checked":""} onchange="const m=current();const old={...m.bant};m.bant['${k}']=this.checked;addHistory(m,'BANT',old,{...m.bant});persist();render()"> ${k}<small>${m.bant[k]?"Si":"No"}</small></label>`).join("")}</div></div>${field("just","Justificacion visible al cliente","textarea")}${field("notes","Nota interna Conprospeccion","textarea")}</div><span class="block-title" style="margin-top:12px">Evidencias</span><div class="evidence">${m.evidence.map(e=>`<div class="evi">${e.valid?"✓ ":""}${esc(e.type)}<small>${esc(e.name)}</small></div>`).join("")||""}<button class="ghost" onclick="addEvidence('Archivo')">Subir archivo</button><button class="ghost" onclick="addEvidence('Enlace')">Pegar enlace</button><button class="ghost" onclick="addEvidence('Comentario')">Agregar comentario</button></div><div class="btn-row"><button class="primary" onclick="saveSection('Evaluacion CP')">Guardar Evaluacion CP</button></div>`}
function clientTimeline(m){const items=(m.clientTimeline&&m.clientTimeline.length?m.clientTimeline:buildClientTimeline(m));return `<span class="block-title" style="margin-top:12px">Seguimiento cliente</span><div class="timeline">${items.map(i=>`<div class="tl"><small>${esc(i.when)} - ${esc(i.actor||"Cliente")}</small><b>${esc(i.status||"Pendiente")}</b>${i.reason?`<div>Motivo: ${esc(i.reason)}</div>`:""}${i.comment?`<div>${esc(i.comment)}</div>`:""}</div>`).join("")}</div>`}
function clientTab(m){const revision=m.clientVal==="Solicitar revision";return `<div class="read"><p><b>Estado actual:</b> ${esc(m.clientVal)}</p><p><b>Ultima accion:</b> ${esc(m.clientDate)||"Sin fecha registrada"}</p><p><b>Contacto cliente:</b> ${esc(m.clientActor||m.contact)||"Sin contacto registrado"}</p><p><b>Motivo:</b> ${esc(m.clientReason)||"Sin motivo registrado"}</p><p><b>Comentario:</b> ${esc(m.clientComment)||"Sin comentario registrado"}</p></div><div class="grid" style="margin-top:12px"><div class="field2"><label>Evaluacion Cliente</label><select onchange="setField(${m.id},'clientVal',this.value)">${opt(clientVals,m.clientVal)}</select></div><div class="field2"><label>Contacto que acciono</label><input value="${esc(m.clientActor||m.contact||"")}" onchange="setField(${m.id},'clientActor',this.value)"></div>${revision?`<div class="field2"><label>Motivo revision</label><select onchange="setField(${m.id},'clientReason',this.value)">${opt(clientRevisionReasons,m.clientReason)}</select></div>`:""}${field("clientComment","Comentario cliente","textarea")}${field("clientEvidence","Evidencia cliente")}</div>${clientTimeline(m)}<div class="field2 wide" style="margin-top:12px"><label>Respuesta de Conprospeccion</label><textarea onchange="setField(${m.id},'cpResponse',this.value)">${esc(m.cpResponse)}</textarea></div><div class="btn-row"><button class="primary" onclick="saveSection('Evaluacion Cliente')">Guardar Evaluacion Cliente</button></div>`}
function finalTab(m){const alert=operationalAlert(m);const fAlert=finalAlert(m);return `<div class="grid"><div class="field2"><label>Estado Final</label><select onchange="setField(${m.id},'final',this.value)">${opt(finalOptions,finalStatus(m))}</select><span class="sub">Vista actual: ${esc(finalDisplay(m))}</span></div><div class="field2"><label>Estado del Caso</label><select onchange="setField(${m.id},'caseStatus',this.value)">${opt(caseStatusOptions,m.caseStatus)}</select></div>${fAlert?`<div class="field2 wide"><label>Alerta final</label><input value="${esc(fAlert)}" readonly></div>`:""}${alert&&alert!=="Sin alertas operativas"?`<div class="field2 wide"><label>Alerta operativa</label><input value="${esc(alert)}" readonly></div>`:""}${field("finalReason","Motivo Final","textarea")}${field("finalClientText","Texto visible al cliente","textarea")}${field("finalInternalNote","Nota interna","textarea")}</div><div class="btn-row"><button class="primary" onclick="saveSection('Estado Final')">Guardar Estado Final</button></div>`}
function historySource(h){if(h.manual)return"Nota manual";if(String(h.user||"").toLowerCase().includes("cliente"))return"Cliente";if(String(h.user||"").toLowerCase().includes("ghl")||String(h.user||"").toLowerCase().includes("sistema"))return"Sistema";return"Conprospeccion"}
function historyText(h){if(h.description)return esc(h.description);const from=typeof h.from==="undefined"?"":JSON.stringify(h.from);const to=typeof h.to==="undefined"?"":JSON.stringify(h.to);return `${esc(from)} -> ${esc(to)}`}
function historyTab(m){const items=m.history||[];const form=`<div class="manual-form"><span class="block-title">Agregar actualizacion manual</span><div class="grid"><div class="field2"><label>Tipo de actualizacion</label><select id="manualType">${opt(["Etapa de agenda","Evaluacion CP","Evaluacion cliente","Estado final","Seguimiento","Informacion adicional","Nota para el cliente"],"Seguimiento")}</select></div><div class="field2"><label>Visibilidad</label><select id="manualVisibility">${opt(["Solo uso interno","Visible para el cliente"],"Solo uso interno")}</select></div><div class="field2 wide"><label>Descripcion</label><textarea id="manualText" placeholder="Escribe una actualizacion breve"></textarea></div></div><div class="btn-row"><button class="primary" onclick="addManualHistory()">Agregar actualizacion</button></div><small class="sub">Esta nota no modifica Etapa Agenda, Evaluacion CP, Evaluacion Cliente ni Estado Final.</small></div>`;return form+`<div class="history">${items.length?items.map((h,idx)=>{const source=historySource(h);const cls=h.manual?"manual":source==="Cliente"?"client":"";return `<div class="hist"><small>${esc(h.when)} - ${esc(h.user||"Sistema")} <span class="event-badge ${cls}">${source}</span><span class="event-badge">${esc(h.visibility||"Solo uso interno")}</span></small><b>${esc(h.field||"Actualizacion")}</b><div>${historyText(h)}</div><div class="event-meta">${esc(h.status||h.stage||"")}</div>${h.manual?`<div class="manual-actions"><button class="mini" onclick="editManualHistory(${idx})">Editar</button><button class="mini" onclick="deleteManualHistory(${idx})">Eliminar</button></div>`:""}</div>`}).join(""):"<span class='sub'>Sin cambios durante esta sesion.</span>"}</div>`}
function addManualHistory(){const m=current();const text=(document.getElementById("manualText").value||"").trim();if(!text)return;const type=document.getElementById("manualType").value;const visibility=document.getElementById("manualVisibility").value;m.history=m.history||[];m.history.unshift({when:new Date().toLocaleString("es-CL"),user:"Francisca / Yanina",field:type,description:text,manual:true,visibility,client:m.client,meetingId:m.id});persist();renderPanel();notify("Actualizacion agregada al historial")}
function editManualHistory(idx){const m=current();const h=(m.history||[])[idx];if(!h||!h.manual)return;const next=prompt("Corregir actualizacion manual",h.description||"");if(next===null)return;const old=h.description||"";h.description=next;m.history.unshift({when:new Date().toLocaleString("es-CL"),user:"Francisca / Yanina",field:"Auditoria nota manual",description:`Nota manual editada: ${old} -> ${next}`,manual:false,visibility:"Solo uso interno",client:m.client,meetingId:m.id});persist();renderPanel()}
function deleteManualHistory(idx){const m=current();const h=(m.history||[])[idx];if(!h||!h.manual)return;if(!confirm("Eliminar esta actualizacion manual?"))return;const old=h.description||"";m.history.splice(idx,1);m.history.unshift({when:new Date().toLocaleString("es-CL"),user:"Francisca / Yanina",field:"Auditoria nota manual",description:`Nota manual eliminada: ${old}`,manual:false,visibility:"Solo uso interno",client:m.client,meetingId:m.id});persist();renderPanel()}
function addEvidence(type="Manual"){const m=current();const name=prompt(type==="Enlace"?"Pega el enlace":"Nombre, archivo o comentario de evidencia");if(!name)return;m.evidence.push({type,name,valid:true});addHistory(m,`Carga ${type}`,"",name);persist();render()}
function buildNotifications(){return meetings.flatMap(m=>(m.history||[]).slice(0,3).map(h=>({client:m.client,company:m.company,contact:m.contact,type:h.field,when:h.when,state:h.to}))).filter(n=>n.type!=="Guardar Historial").slice(0,9)}
function toggleNotifications(){notifOpen=!notifOpen;renderNotifications()}
function renderNotifications(){const box=document.getElementById("notifications");const events=buildNotifications();document.getElementById("bell").toggleAttribute("data-count",events.length>0);if(events.length>0)document.getElementById("bell").setAttribute("data-count",events.length);box.hidden=!notifOpen;box.innerHTML=`<h3>Notificaciones operativas</h3>${events.length?events.map(e=>`<div class="notif-item"><b>${esc(e.type)}</b><span>${esc(e.client)} · ${esc(e.company)} · ${esc(e.contact)}</span><br><small>${esc(e.when)} · ${esc(e.state)}</small></div>`).join(""):`<div class="notif-item">Sin novedades pendientes.</div>`}`}
function render(){const rows=applyFilters();document.body.classList.toggle("detail-open",panelOpen);document.getElementById("layout").classList.toggle("open",panelOpen);document.getElementById("drawer").classList.toggle("hidden",!panelOpen);renderFilters(rows);renderKpis(rows);renderProgress(rows);renderHead();renderRows(rows);renderNotifications();if(panelOpen)renderPanel()}
render();
</script>
</body>
</html>
"""


real_meetings = cargar_reuniones_reales_poc()
POC_HTML = re.sub(
    r"let meetings=\[[\s\S]*?\];\nconst storageKey=",
    "let meetings=" + json.dumps(real_meetings, ensure_ascii=False) + ";\nconst storageKey=",
    POC_HTML,
    count=1,
)
POC_HTML = POC_HTML.replace(
    'const storageKey="cp_meetings_v5_poc_detail_v2";',
    'const storageKey="cp_meetings_v5_real_data_v1";',
)
POC_HTML = POC_HTML.replace(
    'if(Array.isArray(savedMeetings)){meetings=savedMeetings}\n',
    '',
)
POC_HTML = POC_HTML.replace(
    'function defaultRange(){const now=new Date();const first=new Date(now.getFullYear(),now.getMonth(),1);const last=new Date(now.getFullYear(),now.getMonth()+1,0);return {dateFrom:iso(first),dateTo:iso(last)}}',
    'function defaultRange(){const ds=meetings.map(m=>parseDate(m.date)).filter(Boolean).sort();if(ds.length)return {dateFrom:ds[0],dateTo:ds[ds.length-1]};const now=new Date();const first=new Date(now.getFullYear(),now.getMonth(),1);const last=new Date(now.getFullYear(),now.getMonth()+1,0);return {dateFrom:iso(first),dateTo:iso(last)}}',
)
POC_HTML = POC_HTML.replace(
    "const goal=clientGoals[code]||0;",
    "const goal=clientGoals[code]||((rows.find(m=>m.client===code)||meetings.find(m=>m.client===code)||{}).goal||0);",
)

components.html(POC_HTML, height=960, scrolling=True)
