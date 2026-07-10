import datetime
import base64
import json
import re
import tempfile
import unicodedata
from pathlib import Path

try:
    from zoneinfo import ZoneInfo

    _CHILE_TZ = ZoneInfo("America/Santiago")
except Exception:
    _CHILE_TZ = None

import requests
import streamlit as st
import streamlit.components.v1 as components

from shared.config import supabase_key, supabase_url
from shared.meeting_scope import ACTIVE_MEETING_CLIENT_SLUGS
from shared.metas import meta_de
from meeting_component import render_meeting_component
from meeting_shared import cargar_reuniones_reales_poc
from master_auth import require_master_auth

st.set_page_config(page_title="Seguimiento Reuniones", layout="wide")


SUPABASE_URL = supabase_url()
SUPABASE_KEY = supabase_key()
SUPABASE_HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
SUPABASE_WRITE_HEADERS = {**SUPABASE_HEADERS, "Content-Type": "application/json"}


def _asset_data_uri(relative_path, mime="image/png"):
    path = Path(__file__).resolve().parents[1] / relative_path
    try:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    except Exception:
        return ""
    return f"data:{mime};base64,{encoded}"


def _txt(value, default=""):
    if value is None:
        return default
    text = str(value).strip()
    return default if text.lower() in {"", "none", "nan", "nat", "<na>"} else text


def _country_label(value):
    raw = _txt(value)
    normalized = raw.lower()
    country_map = {
        "cl": "Chile",
        "chl": "Chile",
        "chile": "Chile",
    }
    return country_map.get(normalized, raw)


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


def _now_chile():
    """Hora actual en zona horaria de Chile.

    El servidor (Streamlit Cloud) corre en UTC; sin esto, las reuniones de
    hoy se comparan contra UTC (~4 h adelantado) y se marcan como realizadas
    antes de que ocurran en horario local.
    """
    if _CHILE_TZ is not None:
        return datetime.datetime.now(_CHILE_TZ)
    # Fallback si zoneinfo/tzdata no está disponible: Chile = UTC-4 (invierno).
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-4)))


def _manual_status_label(value):
    value = unicodedata.normalize("NFD", _txt(value).lower())
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.replace("ã³", "o").replace("ãº", "u").replace("ã©", "e")
    if "futura" in value:
        return "Reunión futura"
    if "cancel" in value:
        return "Reunión cancelada"
    if "reagend" in value:
        return "Reagendar reunión"
    if "realizada" in value:
        return "Reunión realizada"
    return ""


def _is_future_meeting(row):
    try:
        d = datetime.date.fromisoformat(str(row.get("fecha") or "")[:10])
    except Exception:
        return True
    now_local = _now_chile()
    today = now_local.date()
    if d > today:
        return True
    if d == today:
        raw_time = _txt(row.get("hora"))
        if not raw_time:
            return True
        try:
            parts = raw_time.split(":")
            meeting_time = datetime.time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
            return meeting_time > now_local.time()
        except Exception:
            return True
    return False


def _status_label(row, seg):
    # Regla vigente: solo "Reunión futura" se infiere por fecha/hora. El resto
    # de la etapa agenda debe venir de una decisión manual persistida.
    manual = _manual_status_label(seg.get("status_reunion")) or _manual_status_label(row.get("estado_reunion"))
    if manual:
        return manual
    if _is_future_meeting(row):
        return "Reunión futura"
    return "Reunión realizada"


def _cp_label(row, seg):
    value = _txt(seg.get("val_estado_cp")) or _txt(row.get("estado_validacion"))
    value = value.lower()
    if value in {"valida", "reunion_valida"}:
        return "Válida"
    if value in {"no_valida", "reunion_no_valida", "cancelacion"}:
        return "No válida"
    return "Pendiente"


def _client_val_label(seg):
    value = _txt(seg.get("val_estado_cli")).lower()
    if value in {"valida", "confirmar", "confirmada", "confirmado"}:
        return "Válida"
    if value in {"no_valida", "no valida", "rechazada"}:
        return "No válida"
    if value in {"requiere_revision", "solicitar_revision", "solicita_revision"}:
        return "Solicita revisión"
    return "Pendiente"


def _sdr_display(slug, sdr_names):
    value = _txt(slug)
    if not value:
        return ""
    return sdr_names.get(value, value.replace("_", " ").title())


def _final_label(seg):
    value = _txt(seg.get("val_estado_final")).lower()
    if value in {"valida", "reunion_valida"}:
        return "Reunión válida"
    if value in {"no_valida", "reunion_no_valida"}:
        return "Reunión no válida"
    if value in {"cancelacion", "cancelada"}:
        return "Reunión cancelada"
    if value in {"reagendar", "reagendada"}:
        return "Reagendar reunión"
    return "Pendiente"


def _case_status(cp, client_val, final):
    if final != "Pendiente":
        return "Cerrado"
    if client_val == "Solicita revisión":
        return "En revisión"
    if cp == "Pendiente":
        return "En evaluación CP"
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
    recording = _txt(row.get("recording_url")) or _txt(seg.get("recording_url"))
    transcript = _txt(row.get("transcript_url")) or _txt(seg.get("transcript_url"))
    summary = _txt(row.get("ai_summary")) or _txt(seg.get("ai_summary"))
    ai_evidence = _txt(row.get("ai_evidence")) or _txt(seg.get("ai_evidence"))
    if recording:
        ev.append({"type": "Grabación", "name": "Abrir grabación", "url": recording, "valid": True})
    if transcript:
        ev.append({"type": "Transcripción", "name": "Abrir transcripción", "url": transcript, "valid": True})
    if summary:
        ev.append({"type": "Resumen IA", "name": "Resumen disponible", "text": summary, "valid": True})
    if ai_evidence:
        ev.append({"type": "Evidencia IA", "name": "Evidencia detectada", "text": ai_evidence, "valid": True})
    return ev


def _json_obj(value, default):
    if isinstance(value, type(default)):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            if isinstance(parsed, type(default)):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
    if isinstance(default, dict):
        return {}
    if isinstance(default, list):
        return []
    return default


def _visibility_from_state(state: str) -> bool:
    raw = _txt(state).lower()
    return "visible" in raw and "solo" not in raw


def _apply_evidence_visibility(evidence, saved_visibility, history):
    visibility = _json_obj(saved_visibility, {}).copy()
    for event in reversed(history or []):
        if _txt(event.get("field")) != "Visibilidad evidencia":
            continue
        evidence_type = _txt(event.get("from"))
        state = _txt(event.get("to")) or _txt(event.get("description"))
        if evidence_type and state:
            visibility[evidence_type] = _visibility_from_state(state)
            continue
        if ":" not in state:
            continue
        evidence_type, state = [part.strip() for part in state.split(":", 1)]
        if evidence_type:
            visibility[evidence_type] = _visibility_from_state(state)
    for item in evidence:
        item["clientVisible"] = bool(visibility.get(item.get("type"), item.get("clientVisible", False)))
    return evidence


def _evidence_visibility_payload(evidence):
    return {str(item.get("type")): bool(item.get("clientVisible")) for item in evidence or [] if item.get("type")}


def _manual_evidence_payload(evidence):
    manual = []
    for item in evidence or []:
        if item.get("source") == "manual" or item.get("manual"):
            manual.append(item)
    return manual


def _manual_history_payload(history):
    manual = []
    for item in history or []:
        if item.get("manual"):
            manual.append(item)
    return manual


def _agenda_metadata_payload(meeting):
    keys = [
        "cancelWho",
        "cancelReason",
        "cancelComment",
        "rescheduleWho",
        "rescheduleReason",
        "rescheduleOld",
        "rescheduleNew",
        "rescheduleComment",
    ]
    return {key: _txt(meeting.get(key)) for key in keys if _txt(meeting.get(key))}


def _custom_field(custom_fields, *ids):
    wanted = set(ids)
    for field in custom_fields or []:
        if field.get("id") in wanted and _txt(field.get("value")):
            return _txt(field.get("value"))
    return ""


def _contact_enrichment(contact):
    raw = contact.get("raw_data") or {}
    fields = contact.get("custom_fields") or raw.get("customFields") or []
    return {
        "website": _txt(raw.get("website")),
        "linkedin": _custom_field(fields, "iimkT4RjJWRONU2HcwbN"),
        "linkedinCompany": _custom_field(fields, "SnRP2tiJlYfQOHBM3adE"),
        "companySize": _custom_field(fields, "3uQfRamZN2ruaNg367XL"),
        "sourceChannel": _custom_field(fields, "mipcTmLgax5URM1q3Mut") or _txt(raw.get("source")),
        "companyInfo": _custom_field(fields, "x8bV5PXJ0MgJcmdMk9Bd", "uWCMW4RCrWDGlu02nMkp"),
        "contactInfo": _custom_field(fields, "iZwhsMPoJZ5IgdcA3kYk", "Q6PFJIn4ETLXlgsKRwvx"),
    }


def _dt_sort_key(row):
    date_part = _date_db(row.get("date")) or ""
    time_part = _time_db(row.get("time")) or ""
    return f"{date_part} {time_part}"


def _dedupe_clickie_latest(rows):
    latest = {}
    output = []
    for row in rows:
        if row.get("clientSlug") != "clickie":
            output.append(row)
            continue
        key = (
            row.get("clientSlug"),
            _txt(row.get("ghlContact")).lower()
            or _txt(row.get("email")).lower()
            or f"{_txt(row.get('company')).lower()}|{_txt(row.get('contact')).lower()}",
        )
        current = latest.get(key)
        if current is None or _dt_sort_key(row) >= _dt_sort_key(current):
            latest[key] = row
    output.extend(latest.values())
    return output


def _db_cp(value):
    value = _txt(value).lower()
    if value in {"valida", "válida"}:
        return "valida"
    if value in {"no valida", "no válida"}:
        return "no_valida"
    if value in {"no necesaria", "no_necesaria"}:
        return "no_necesaria"
    return None


def _db_cliente(value):
    value = _txt(value).lower()
    if value in {"confirmar", "confirmada", "valida", "válida"}:
        return "valida"
    if value in {"no valida", "no válida"}:
        return "no_valida"
    if value in {"solicitar revision", "solicita revision", "solicita revisión"}:
        return "requiere_revision"
    if value in {"no necesaria", "no_necesaria"}:
        return "no_necesaria"
    return None


def _db_final(value):
    value = _txt(value).lower()
    if value in {"reunion valida", "reunión válida"}:
        return "valida"
    if value in {"reunion no valida", "reunión no válida"}:
        return "no_valida"
    if value in {"reunion cancelada", "reunión cancelada"}:
        return "cancelacion"
    if value in {"reagendar reunion", "reagendar reunión"}:
        return "reagendar"
    return None


def _bant_str(value):
    if not isinstance(value, dict):
        return None
    mapping = {"Budget": "B", "Authority": "A", "Need": "N", "Timeline": "T"}
    return ",".join(code for label, code in mapping.items() if value.get(label)) or None


def _bool_icp(value):
    value = _txt(value).lower()
    if value == "cumple":
        return True
    if value == "no cumple":
        return False
    return None


def _date_db(value):
    try:
        day, month, year = str(value).split("/")
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    except Exception:
        return None


def _time_db(value):
    raw = _txt(value).upper().replace(".", "")
    if not raw:
        return None
    try:
        hm, suffix = raw.split()
        hour, minute = [int(x) for x in hm.split(":")[:2]]
        if suffix == "PM" and hour != 12:
            hour += 12
        if suffix == "AM" and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute:02d}:00"
    except Exception:
        return raw[:8]


def _flag_meta_countable(final_value):
    final_db = _db_final(final_value)
    if final_db == "valida":
        return True
    if final_db in {"no_valida", "cancelacion", "reagendar"}:
        return False
    return None


def _post_tracking(payload):
    body = dict(payload)
    response = None
    for _ in range(5):
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/seguimiento_reuniones",
            params={"on_conflict": "reunion_id"},
            headers={**SUPABASE_WRITE_HEADERS, "Prefer": "resolution=merge-duplicates,return=representation"},
            json=body,
            timeout=15,
        )
        if response.ok:
            return response
        missing = re.search(r"Could not find the '([^']+)' column", response.text or "")
        if not missing or missing.group(1) not in body:
            return response
        body.pop(missing.group(1), None)
    return response


def _patch_meeting(reunion_id, payload):
    if not payload:
        return None
    response = requests.patch(
        f"{SUPABASE_URL}/rest/v1/reuniones",
        params={"id": f"eq.{int(reunion_id)}"},
        headers={**SUPABASE_WRITE_HEADERS, "Prefer": "return=minimal"},
        json=payload,
        timeout=15,
    )
    return response


def _insert_history(reunion_id, section, text):
    requests.post(
        f"{SUPABASE_URL}/rest/v1/meeting_status_history",
        headers={**SUPABASE_WRITE_HEADERS, "Prefer": "return=minimal"},
        json={
            "meeting_id": int(reunion_id),
            "field_changed": section,
            "old_value": None,
            "new_value": text,
            "changed_by": "Francisca / Yanina",
            "changed_by_role": "panel_interno",
            "source_dashboard": "Seguimiento_Reuniones",
        },
        timeout=10,
    )


def _exclude_dashboard_meeting(payload):
    meeting = payload.get("meeting") or {}
    reunion_id = meeting.get("id")
    if not reunion_id:
        return {"ok": False, "error": "falta_reunion"}
    response = requests.patch(
        f"{SUPABASE_URL}/rest/v1/reuniones",
        params={"id": f"eq.{int(reunion_id)}"},
        headers={**SUPABASE_WRITE_HEADERS, "Prefer": "return=minimal"},
        json={"excluida": True},
        timeout=15,
    )
    if response.ok:
        _insert_history(
            reunion_id,
            "Reunión eliminada",
            "Reunión marcada como excluida (eliminada) desde panel interno",
        )
        return {"ok": True}
    return {"ok": False, "status": response.status_code, "error": response.text[:200]}


def _create_dashboard_meeting(payload):
    meeting = payload.get("meeting") or {}
    cliente_slug = _txt(meeting.get("clientSlug")).lower()
    date_iso = _txt(meeting.get("dateISO"))
    if not cliente_slug or not date_iso:
        return {"ok": False, "error": "faltan_cliente_o_fecha"}
    try:
        y, mo, d = [int(x) for x in date_iso.split("-")]
        hh, mm = 0, 0
        time_txt = _txt(meeting.get("time"))
        if time_txt:
            parts = time_txt.split(":")
            hh = int(parts[0])
            mm = int(parts[1]) if len(parts) > 1 else 0
        tz = _CHILE_TZ or datetime.timezone(datetime.timedelta(hours=-4))
        appointment_at = datetime.datetime(y, mo, d, hh, mm, tzinfo=tz).isoformat()
    except Exception:
        return {"ok": False, "error": "fecha_u_hora_invalida"}
    try:
        last = requests.get(
            f"{SUPABASE_URL}/rest/v1/reuniones?select=id&order=id.desc&limit=1",
            headers=SUPABASE_HEADERS,
            timeout=15,
        )
        rows = last.json() if last.ok else []
        max_id = int(rows[0]["id"]) if rows else 0
    except Exception:
        max_id = 0
    # reuniones.id no es autogenerado; usamos un rango alto para no chocar
    # con los ids que la sincronización de GHL toma de la secuencia.
    new_id = max(max_id, 900000000) + 1
    body = {
        "id": new_id,
        "cliente_slug": cliente_slug,
        "empresa": _txt(meeting.get("company")) or None,
        "contacto": _txt(meeting.get("contact")) or None,
        "email": _txt(meeting.get("email")) or None,
        "appointment_at": appointment_at,
        "estado_reunion": _txt(meeting.get("status")) or "Reunión futura",
        "origen_reunion": "manual",
        "excluida": False,
    }
    body = {key: value for key, value in body.items() if value is not None}
    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/reuniones",
        headers={**SUPABASE_WRITE_HEADERS, "Prefer": "return=minimal"},
        json=body,
        timeout=15,
    )
    if response.ok:
        _insert_history(new_id, "Reunión creada", "Reunión creada manualmente desde panel interno")
        return {"ok": True, "id": new_id}
    return {"ok": False, "status": response.status_code, "error": response.text[:300]}


def _save_dashboard_payload(payload):
    meeting = payload.get("meeting") or {}
    section = _txt(payload.get("section"), "Actualizacion")
    reunion_id = meeting.get("id")
    cliente_slug = _txt(meeting.get("clientSlug")).lower()
    if not reunion_id or not cliente_slug:
        return {"ok": False, "error": "faltan_reunion_o_cliente"}

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    final_db = _db_final(meeting.get("final"))
    status_label = _txt(meeting.get("status"))
    cp_db = _db_cp(meeting.get("cp"))
    client_db = _db_cliente(meeting.get("clientVal"))
    if status_label == "Reunión cancelada":
        cp_db = "no_necesaria"
        client_db = "no_necesaria"
        final_db = final_db or "cancelacion"
    tracking_payload = {
        "reunion_id": int(reunion_id),
        "cliente_slug": cliente_slug,
        "status_reunion": status_label or None,
        "val_estado_cp": cp_db,
        "bant_cp": _bant_str(meeting.get("bant")),
        "icp_cumple": _bool_icp(meeting.get("icp")),
        "comentario_cp": _txt(meeting.get("just")) or None,
        "notas_internas": _txt(meeting.get("notes")) or None,
        "informacion_reunion_manual": _txt(meeting.get("info")) or None,
        "sdr_override": _txt(meeting.get("sdr")) or None,
        "val_estado_cli": client_db,
        "comentario_cli": _txt(meeting.get("clientComment")) or None,
        "motivo_no_validez": _txt(meeting.get("clientReason")) or None,
        "validated_by_cli": _txt(meeting.get("clientActor")) or "Conprospección - override interno",
        "validated_cli_at": now if _db_cliente(meeting.get("clientVal")) else None,
        "proximo_paso": _txt(meeting.get("next")) or None,
        "comentario_final": _txt(meeting.get("finalReason")) or None,
        "val_estado_final": final_db,
        "final_override": bool(final_db),
        "validated_final_by": "Conprospección" if final_db else None,
        "validated_final_at": now if final_db else None,
        "flag_meta_countable": _flag_meta_countable(meeting.get("final")),
        "estado_caso": _txt(meeting.get("caseStatus")) or None,
        "evidencia_visibilidad": _evidence_visibility_payload(meeting.get("evidence")),
        "evidencia_manual": _manual_evidence_payload(meeting.get("evidence")),
        "historial_visibilidad": _json_obj(meeting.get("historyVisibility"), {}),
        "historial_manual": _manual_history_payload(meeting.get("history")),
        "etapa_agenda_metadata": _agenda_metadata_payload(meeting),
        "comentario_final_cliente": _txt(meeting.get("finalClientText")) or None,
        "respuesta_cp_cliente": _txt(meeting.get("cpResponse")) or None,
        "evidencia_cliente": _txt(meeting.get("clientEvidence")) or None,
        "updated_at": now,
    }
    base_payload = {
        "empresa": _txt(meeting.get("company")) or None,
        "contacto": _txt(meeting.get("contact")) or None,
        "cargo": _txt(meeting.get("role")) or None,
        "email": _txt(meeting.get("email")) or None,
        "telefono": _txt(meeting.get("phone")) or None,
        "pais": _txt(meeting.get("country")) or None,
        "industria": _txt(meeting.get("industry")) or None,
        "fecha_reunion": _date_db(meeting.get("date")),
        "hora_reunion": _time_db(meeting.get("time")),
        "informacion_reunion": _txt(meeting.get("info")) or None,
        "estado_reunion": _txt(meeting.get("status")) or None,
        "observacion": _txt(meeting.get("operationalNotes")) or None,
        "direccion_reunion": _txt(meeting.get("meet")) or None,
        "recording_url": _txt(meeting.get("recordingUrl")) or None,
        "transcript_url": _txt(meeting.get("transcriptUrl")) or None,
    }
    if final_db:
        base_payload["estado_validacion"] = final_db
        base_payload["es_valida"] = final_db == "valida"
    if status_label:
        base_payload["cancelada"] = status_label == "Reunión cancelada"
    base_payload = {key: value for key, value in base_payload.items() if value is not None}

    track_response = _post_tracking(tracking_payload)
    base_response = _patch_meeting(reunion_id, base_payload)
    if track_response.ok and (base_response is None or base_response.ok):
        manual = payload.get("manualHistory") or {}
        if manual:
            _insert_history(
                reunion_id,
                _txt(manual.get("field"), section),
                _txt(manual.get("description")) or f"{section} guardado desde panel interno",
            )
        else:
            _insert_history(reunion_id, section, f"{section} guardado desde panel interno")
        st.cache_data.clear()
        return {"ok": True}
    return {
        "ok": False,
        "tracking_status": track_response.status_code,
        "tracking_error": track_response.text[:300],
        "meeting_status": getattr(base_response, "status_code", None),
        "meeting_error": getattr(base_response, "text", "")[:300],
    }


if not require_master_auth():
    st.stop()
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



CP_MARK_DATA_URI = _asset_data_uri("assets/cp_mark_dark.png")

from seguimiento_poc_template import POC_HTML

POC_HTML = POC_HTML.replace("__CP_MARK__", CP_MARK_DATA_URI)
real_meetings = cargar_reuniones_reales_poc()
real_meetings_json = json.dumps(real_meetings, ensure_ascii=True).replace("</", "<\\/")
POC_HTML = re.sub(
    r"let meetings=\[[\s\S]*?\];\nconst storageKey=",
    lambda _match: "let meetings=" + real_meetings_json + ";\nconst storageKey=",
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
    "const goal=clientGoals[code]||0;",
    "const goal=clientGoals[code]||((rows.find(m=>m.client===code)||meetings.find(m=>m.client===code)||{}).goal||0);",
)

COMPONENT_DIR = Path(tempfile.gettempdir()) / "cp_seguimiento_reuniones_component"
COMPONENT_DIR.mkdir(parents=True, exist_ok=True)
(COMPONENT_DIR / "index.html").write_text(POC_HTML, encoding="utf-8")

_reload_token = st.session_state.get("_seguimiento_reload", 0)
component_payload = render_meeting_component(COMPONENT_DIR, key=f"seguimiento_reuniones_operativo_{_reload_token}")
if isinstance(component_payload, dict):
    nonce = _txt(component_payload.get("nonce")) or json.dumps(component_payload, sort_keys=True, ensure_ascii=True)
    if st.session_state.get("_seguimiento_last_save_nonce") != nonce:
        st.session_state["_seguimiento_last_save_nonce"] = nonce
        if _txt(component_payload.get("action")) == "create":
            create_result = _create_dashboard_meeting(component_payload)
            if create_result.get("ok"):
                st.session_state["_seguimiento_reload"] = st.session_state.get("_seguimiento_reload", 0) + 1
                st.cache_data.clear()
                st.toast("Reunión creada.")
                st.rerun()
            st.error(
                "No fue posible crear la reunión. "
                f"{create_result.get('status', '')} {create_result.get('error', '')}"
            )
        elif _txt(component_payload.get("action")) == "exclude":
            exclude_result = _exclude_dashboard_meeting(component_payload)
            if exclude_result.get("ok"):
                st.cache_data.clear()
                st.toast("Reunión eliminada del panel.")
                st.rerun()
            st.error(
                "No fue posible eliminar la reunión. "
                f"{exclude_result.get('status', '')} {exclude_result.get('error', '')}"
            )
        else:
            save_result = _save_dashboard_payload(component_payload)
            if save_result.get("ok"):
                st.cache_data.clear()
                st.toast("Cambio guardado en Supabase.")
                st.rerun()
            st.error(
                "No fue posible guardar el cambio. "
                f"Seguimiento: {save_result.get('tracking_status')} {save_result.get('tracking_error', save_result.get('error', ''))} "
                f"Reunion: {save_result.get('meeting_status')} {save_result.get('meeting_error', '')}"
            )
