import datetime
import base64
import json
import re
import tempfile
from pathlib import Path

import requests
import streamlit as st
import streamlit.components.v1 as components

from shared.config import supabase_key, supabase_url
from shared.meeting_scope import ACTIVE_MEETING_CLIENT_SLUGS
from shared.metas import meta_de
from meeting_component import render_meeting_component
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


def _status_label(row, seg):
    raw = f"{_txt(seg.get('status_reunion'))} {_txt(row.get('estado_reunion'))}".lower()
    if "reagend" in raw:
        return "Reagendar reunión"
    if "cancel" in raw or "no_asist" in raw:
        return "Reunión cancelada"
    # Regla de negocio: toda reunión cuya fecha/hora aún no ocurre es
    # "Reunión futura", por encima de cualquier estado "realizada/válida"
    # heredado del sync. Solo cancelada/reagendar (arriba) la sobreescriben.
    try:
        d = datetime.date.fromisoformat(str(row.get("fecha") or "")[:10])
    except Exception:
        return "Reunión futura"
    today = datetime.date.today()
    if d > today:
        return "Reunión futura"
    if d == today:
        raw_time = _txt(row.get("hora"))
        if not raw_time:
            return "Reunión futura"
        try:
            parts = raw_time.split(":")
            meeting_time = datetime.time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
            if meeting_time > datetime.datetime.now().time():
                return "Reunión futura"
        except Exception:
            return "Reunión futura"
    # La reunión ya ocurrió por fecha/hora.
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
    return value if isinstance(value, type(default)) else default


def _apply_evidence_visibility(evidence, saved_visibility, history):
    visibility = _json_obj(saved_visibility, {}).copy()
    for event in reversed(history or []):
        if _txt(event.get("field")) != "Visibilidad evidencia":
            continue
        text = _txt(event.get("to")) or _txt(event.get("description"))
        if ":" not in text:
            continue
        evidence_type, state = [part.strip() for part in text.split(":", 1)]
        visibility[evidence_type] = "visible" in state.lower() and "solo" not in state.lower()
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
    return None


def _db_cliente(value):
    value = _txt(value).lower()
    if value in {"confirmar", "confirmada", "valida", "válida"}:
        return "valida"
    if value in {"no valida", "no válida"}:
        return "no_valida"
    if value in {"solicitar revision", "solicita revision", "solicita revisión"}:
        return "requiere_revision"
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
    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/seguimiento_reuniones",
        params={"on_conflict": "reunion_id"},
        headers={**SUPABASE_WRITE_HEADERS, "Prefer": "resolution=merge-duplicates,return=representation"},
        json=payload,
        timeout=15,
    )
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


def _save_dashboard_payload(payload):
    meeting = payload.get("meeting") or {}
    section = _txt(payload.get("section"), "Actualizacion")
    reunion_id = meeting.get("id")
    cliente_slug = _txt(meeting.get("clientSlug")).lower()
    if not reunion_id or not cliente_slug:
        return {"ok": False, "error": "faltan_reunion_o_cliente"}

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    final_db = _db_final(meeting.get("final"))
    tracking_payload = {
        "reunion_id": int(reunion_id),
        "cliente_slug": cliente_slug,
        "status_reunion": _txt(meeting.get("status")) or None,
        "val_estado_cp": _db_cp(meeting.get("cp")),
        "bant_cp": _bant_str(meeting.get("bant")),
        "icp_cumple": _bool_icp(meeting.get("icp")),
        "comentario_cp": _txt(meeting.get("just")) or None,
        "notas_internas": _txt(meeting.get("notes")) or None,
        "informacion_reunion_manual": _txt(meeting.get("info")) or None,
        "sdr_override": _txt(meeting.get("sdr")) or None,
        "val_estado_cli": _db_cliente(meeting.get("clientVal")),
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
    }
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
    base_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/reuniones"
        "?select=id,ghl_contact_id,fecha_agendada,recording_url,transcript_url,ai_summary,ai_evidence,sdr_slug",
        headers=SUPABASE_HEADERS,
        timeout=15,
    )
    contacts_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/contactos?select=ghl_contact_id,sdr_slug,raw_data,custom_fields&cliente_slug=in.({slugs})",
        headers=SUPABASE_HEADERS,
        timeout=15,
    )
    sdr_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/sdrs?select=slug,nombre",
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
    base_meetings = {}
    if base_response.ok:
        base_meetings = {int(x["id"]): x for x in base_response.json() if x.get("id")}
    contact_sdr = {}
    contact_extra = {}
    if contacts_response.ok:
        contact_sdr = {
            x["ghl_contact_id"]: x.get("sdr_slug")
            for x in contacts_response.json()
            if x.get("ghl_contact_id") and x.get("sdr_slug")
        }
        contact_extra = {
            x["ghl_contact_id"]: _contact_enrichment(x)
            for x in contacts_response.json()
            if x.get("ghl_contact_id")
        }
    sdr_names = {}
    if sdr_response.ok:
        sdr_names = {x.get("slug"): x.get("nombre") for x in sdr_response.json() if x.get("slug") and x.get("nombre")}
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
                    "user": _txt(event.get("changed_by"), "Conprospección"),
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
        base_row = base_meetings.get(int(rid), {})
        extra = contact_extra.get(row.get("ghl_contact_id"), {})
        slug = _txt(row.get("cliente_slug")).lower()
        status = _status_label(row, seg)
        cp = _cp_label(row, seg)
        client_val = _client_val_label(seg)
        row_history = histories.get(int(rid), [])
        manual_evidence = _json_obj(seg.get("evidencia_manual"), [])
        evidence = _evidence({**row, **base_row}, seg) + manual_evidence
        evidence = _apply_evidence_visibility(evidence, seg.get("evidencia_visibilidad"), row_history)
        agenda_meta = _json_obj(seg.get("etapa_agenda_metadata"), {})
        if status == "Reunión cancelada":
            if cp == "Pendiente":
                cp = ""
            if client_val == "Pendiente":
                client_val = ""
        final = _final_label(seg)
        assigned_sdr = (
            _txt(seg.get("sdr_override"))
            or _sdr_display(contact_sdr.get(row.get("ghl_contact_id")), sdr_names)
            or _sdr_display(base_row.get("sdr_slug"), sdr_names)
            or _txt(row.get("sdr"), "Sin asignar")
        )
        meta = meta_de(slug)
        rows.append(
            {
                "id": int(rid),
                "clientSlug": slug,
                "date": _date_es(row.get("fecha")),
                "time": _time_12(row.get("hora")),
                "scheduledDate": _date_es(base_row.get("fecha_agendada")),
                "client": _client_label(slug, row.get("cliente")),
                "company": _txt(row.get("empresa"), "-").title(),
                "contact": _txt(row.get("contacto"), "-").title(),
                "role": _txt(row.get("cargo"), "-").title(),
                "sdr": assigned_sdr,
                "status": status,
                "cp": cp,
                "clientVal": client_val,
                "final": final,
                "caseStatus": _txt(seg.get("estado_caso")) or _case_status(cp, client_val, final),
                "email": _txt(row.get("email")),
                "phone": _txt(row.get("telefono")),
                "country": _country_label(row.get("pais")),
                "industry": _txt(row.get("industria")),
                "website": extra.get("website", ""),
                "linkedin": extra.get("linkedin", ""),
                "linkedinCompany": extra.get("linkedinCompany", ""),
                "companySize": extra.get("companySize", ""),
                "sourceChannel": extra.get("sourceChannel", ""),
                "companyInfo": extra.get("companyInfo", ""),
                "contactInfo": extra.get("contactInfo", ""),
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
                "finalClientText": _txt(seg.get("comentario_final_cliente")),
                "finalInternalNote": _txt(seg.get("notas_internas")),
                "evidence": evidence,
                "clientReason": _txt(seg.get("motivo_no_validez")),
                "clientComment": _txt(seg.get("comentario_cli")),
                "clientDate": _txt(seg.get("validated_cli_at"))[:16].replace("T", " "),
                "clientActor": _txt(seg.get("validated_by_cli"), _txt(row.get("contacto"), "Cliente")),
                "clientEvidence": _txt(seg.get("evidencia_cliente")),
                "cpResponse": _txt(seg.get("respuesta_cp_cliente")),
                "cancelWho": _txt(agenda_meta.get("cancelWho")),
                "cancelReason": _txt(agenda_meta.get("cancelReason")),
                "cancelComment": _txt(agenda_meta.get("cancelComment")),
                "rescheduleWho": _txt(agenda_meta.get("rescheduleWho")),
                "rescheduleReason": _txt(agenda_meta.get("rescheduleReason")),
                "rescheduleOld": _txt(agenda_meta.get("rescheduleOld")),
                "rescheduleNew": _txt(agenda_meta.get("rescheduleNew")),
                "rescheduleComment": _txt(agenda_meta.get("rescheduleComment")),
                "history": row_history,
                "goal": int(meta["validas"]) if meta else 0,
            }
        )
    rows = _dedupe_clickie_latest(rows)
    rows.sort(key=_dt_sort_key, reverse=True)
    return rows


CP_MARK_DATA_URI = _asset_data_uri("assets/cp_mark_dark.png")

POC_HTML = r"""
<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
@import url('https://fonts.googleapis.com/css2?family=Saira:wght@400;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
:root{
  --gold:#FFD700;--gold-hover:#FFCC00;--carbon:#333333;--ink:#1A1A1A;
  --bg:#FAFAF8;--surface:#FFFFFF;--muted-surface:#F4F4F2;--muted:#6B6B6B;
  --line:#EDECEA;--line-strong:#C9C9C4;--primary:#FFD700;--primary-soft:#FFF7BF;
  --green:#15803D;--green-bg:#EAF6EF;--orange:#A66A00;--orange-bg:#FFF3D8;
  --red:#C92B2B;--red-bg:#FDECEA;--blue:#2563EB;--blue-bg:#EAF1FE;
  --purple:#6D28D9;--purple-bg:#F1EDFF;--gray:#8A8A86;--gray-bg:#F4F4F2;
}
*{box-sizing:border-box}
html{font-size:16px;-webkit-font-smoothing:antialiased}
body{margin:0;background:#ECECEA;color:var(--ink);font-family:"IBM Plex Sans",ui-sans-serif,system-ui,sans-serif;font-size:14px}body.detail-open{overflow:visible}
button,input,select,textarea{font:inherit}
.app{min-width:0;min-height:auto;padding:0 12px 24px;background:#ECECEA}
.top{height:64px;display:flex;align-items:center;justify-content:space-between;border-bottom:0;margin-bottom:14px;background:var(--carbon);color:#FFFFFF;border-radius:0 0 10px 10px;padding:0 18px;box-shadow:0 10px 24px rgba(26,26,26,.14)}
.brand{display:flex;align-items:center;gap:14px}.hamb{font-size:22px;color:#9A9A98}.brand-logo{width:32px;height:32px;object-fit:contain;border-radius:7px;box-shadow:0 0 0 1px #5C5C58}.mark{width:22px;height:22px;border-radius:6px;background:linear-gradient(135deg,var(--carbon) 0 52%,var(--gold) 52% 100%);box-shadow:inset 0 0 0 2px #fff,0 0 0 1px var(--line-strong)}
.title h1{font-family:Saira,"IBM Plex Sans",sans-serif;font-size:18px;line-height:1.2;margin:0;font-weight:700;text-transform:none;color:#FFFFFF}.title p{font-size:12px;margin:2px 0 0;color:#C9C9C6}
.user{display:flex;align-items:center;gap:14px}.bell{position:relative;width:32px;height:32px;border:0;background:transparent;border-radius:8px;display:grid;place-items:center;cursor:pointer}.bell:before{content:"";width:13px;height:15px;border:1.8px solid #FFFFFF;border-radius:8px 8px 4px 4px;display:block}.bell[data-count]:after{content:attr(data-count);position:absolute;top:-4px;right:-2px;min-width:16px;height:16px;padding:0 4px;border-radius:99px;background:#C0392B;color:white;font-size:10px;display:grid;place-items:center;font-weight:700}.usertext{font-size:12px;line-height:1.15;color:#ECECEA}.usertext b{display:block;color:#FFFFFF}
.notif{position:absolute;right:18px;top:62px;width:360px;max-height:420px;overflow:auto;background:var(--surface);border:1px solid var(--line);border-radius:9px;box-shadow:0 12px 32px rgba(26,26,26,.13);z-index:50;padding:10px}.notif[hidden]{display:none}.notif h3{font-family:Saira,"IBM Plex Sans",sans-serif;font-size:13px;margin:2px 4px 8px}.notif-item{border-top:1px solid var(--line);padding:9px 4px;font-size:12px}.notif-item b{display:block}
.layout{display:grid;grid-template-columns:1fr;gap:12px;align-items:start}.layout.open{grid-template-columns:minmax(0,1fr) minmax(430px,34vw)}.layout.open .main{min-width:0;overflow:hidden}
.main{display:flex;flex-direction:column;gap:12px;min-width:0}.card{background:var(--surface);border:1px solid #D8D8D5;border-radius:10px;box-shadow:0 8px 20px rgba(26,26,26,.05)}
.filters{padding:14px;display:grid;grid-template-columns:2fr .9fr .9fr 1.35fr .95fr .7fr;gap:10px;background:#FAFAF8;border-radius:10px}.extra{display:none;grid-template-columns:repeat(6,1fr);gap:10px;padding:0 14px 14px;background:#FAFAF8}.extra.open{display:grid}
.field{height:38px;border:1px solid #D8D8D5;border-radius:9px;background:#FFFFFF;display:flex;align-items:center;gap:8px;padding:0 11px;min-width:0;position:relative}.field label{position:absolute;top:-8px;left:9px;background:#FFFFFF;font-size:10px;color:#6B6B6B;font-weight:700;padding:0 4px;text-transform:uppercase;letter-spacing:.04em}.field input,.field select{border:0;outline:0;background:transparent;width:100%;height:100%;color:var(--ink);font-size:12px}.field button{border:0;background:transparent;width:100%;height:100%;display:flex;align-items:center;justify-content:center;gap:7px;font-weight:700;font-size:12px;color:var(--ink);cursor:pointer}.date-range{display:grid;grid-template-columns:1fr 1fr auto;gap:4px;align-items:center}.date-range input{font-family:"IBM Plex Mono",monospace;font-size:11px}.clear-date{border:0;background:transparent;color:var(--muted);cursor:pointer}
.active-filters{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:0 12px 12px}.filter-chip{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);background:var(--muted-surface);border-radius:999px;padding:5px 8px;font-size:11px}.filter-chip button{border:0;background:transparent;cursor:pointer;color:var(--muted)}.clear-all{border:1px solid var(--line);background:#fff;border-radius:8px;padding:6px 9px;font-size:12px;cursor:pointer;color:var(--primary)}
.kpis{display:grid;grid-template-columns:repeat(8,1fr);overflow:hidden}.kpi{min-height:74px;padding:10px 12px;border-right:1px solid var(--line);display:flex;gap:10px;align-items:center;cursor:pointer}.kpi:last-child{border-right:0}.kpi.active{box-shadow:inset 0 -3px 0 var(--gold);background:#fffdf0}
.ico{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;font-weight:700}.ico.blue{background:var(--blue-bg);color:var(--blue)}.ico.green{background:var(--green-bg);color:var(--green)}.ico.orange{background:var(--orange-bg);color:var(--orange)}.ico.purple{background:var(--purple-bg);color:var(--purple)}.ico.red{background:var(--red-bg);color:var(--red)}
.kpi span{display:block;font-size:11px;font-weight:700}.kpi b{display:block;font-family:"IBM Plex Mono",monospace;font-size:24px;line-height:1.1;margin-top:2px}.kpi small{display:block;font-size:10.5px;color:var(--muted);margin-top:4px}
.progress{padding:16px 18px;background:#FAFAF8}.section-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}.section-head b{font-family:Saira,"IBM Plex Sans",sans-serif;font-size:15px}.section-head small{color:var(--carbon);font-weight:700}.client-row{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.client{padding:14px 14px 10px;border-left:4px solid var(--client-color,#9A9A98);box-shadow:none}.client-top{display:flex;justify-content:space-between;align-items:center;font-weight:700}.client-name{display:flex;align-items:center;gap:10px}.client-badge{width:28px;height:28px;border-radius:8px;display:grid;place-items:center;background:var(--client-color,#9A9A98);color:#111;font-weight:800;font-size:12px}.client-count{font-family:"IBM Plex Mono",monospace;font-size:20px;font-weight:700}.bar{height:6px;background:#ECECEA;border-radius:99px;margin:10px 0 9px;overflow:hidden}.fill{height:100%;background:var(--client-color,#15803D);border-radius:99px}.client-foot{display:flex;align-items:center;justify-content:space-between}.client-ratio{font-family:"IBM Plex Mono",monospace;color:#333;font-size:13px}.goal-pill{border-radius:6px;padding:4px 8px;font-size:11px;font-weight:800;letter-spacing:.04em}.goal-ok{background:#EAF6EF;color:#15803D}.goal-mid{background:#FFF3D8;color:#92610A}.goal-bad{background:#FDECEA;color:#C0392B}
.table-card{overflow:hidden}.table-head{display:flex;justify-content:space-between;align-items:end;padding:11px 14px 7px}.table-head h2{font-family:Saira,"IBM Plex Sans",sans-serif;font-size:14px;margin:0}.table-head p{font-size:11px;color:var(--muted);margin:3px 0 0}
.table-wrap{overflow:visible;border-top:1px solid var(--line)}table{width:100%;border-collapse:separate;border-spacing:0;font-size:12px;table-layout:auto}thead th{position:sticky;top:0;z-index:3;background:var(--muted-surface);border-bottom:1px solid var(--line);text-align:left;color:#9A9A98;font-size:11px;font-weight:700;padding:6px 10px;white-space:nowrap;text-transform:uppercase;letter-spacing:.03em}.sort{border:0;background:transparent;color:inherit;font-weight:700;cursor:pointer;padding:0}.quick{width:100%;height:22px;border:0;border-radius:0;background:transparent;font-size:11px;color:#8A8A86;font-weight:700;text-transform:uppercase;letter-spacing:.03em;outline:0;cursor:pointer;padding:0}.quick.active{color:var(--ink);background:#fff;border:1px solid var(--line);border-radius:6px;padding:0 5px;text-transform:none;letter-spacing:0}
tbody td{border-bottom:1px solid var(--line);padding:6px 10px;vertical-align:middle;white-space:nowrap;height:38px;overflow:hidden;text-overflow:ellipsis}tbody tr{cursor:pointer}tbody tr:hover{background:#FFF9D6}tbody tr.selected{box-shadow:inset 3px 0 0 var(--gold)}.sub{display:block;color:var(--muted);font-size:10.5px;margin-top:2px;line-height:1.2;overflow:hidden;text-overflow:ellipsis}.company{font-weight:600}.avatar-sm{width:22px;height:22px;border-radius:50%;display:inline-grid;place-items:center;margin-right:8px;background:var(--gray-bg);color:var(--gray);font-size:10px;font-weight:700}.avatar-sm.gbs{background:var(--purple-bg);color:var(--purple)}.avatar-sm.clickie{background:#FFF1B8;color:#A66A00}.avatar-sm.bambutech{background:var(--green-bg);color:var(--green)}
.chip,.pill{display:inline-flex;align-items:center;justify-content:center;gap:6px;border-radius:6px;padding:5px 9px;min-width:96px;font-size:.72rem;font-weight:600;border:1px solid transparent}.chip:before{content:"";width:6px;height:6px;border-radius:99px;background:currentColor}.pill{appearance:none;outline:0;cursor:pointer}.green{background:var(--green-bg);color:var(--green)}.orange{background:var(--orange-bg);color:var(--orange)}.red{background:var(--red-bg);color:var(--red)}.purple{background:var(--purple-bg);color:var(--purple)}.blue{background:var(--blue-bg);color:var(--blue)}.gray{background:var(--gray-bg);color:var(--gray)}
.action{border:1px solid var(--line);background:#fff;color:var(--carbon);font-size:12px;font-weight:700;cursor:pointer;border-radius:7px;padding:5px 9px}.action:hover{background:var(--gold);border-color:var(--gold);color:var(--ink)}.drawer{padding:0;position:sticky;top:10px;display:flex;flex-direction:column;overflow:visible}.drawer.hidden{display:none}.drawer-fixed{flex:0 0 auto;padding:10px 14px 0;background:var(--surface);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}.close{position:absolute;right:8px;top:3px;border:0;background:transparent;color:var(--ink);font-size:20px;cursor:pointer;z-index:6}.detail-band{display:flex;flex-wrap:nowrap;gap:12px 18px;align-items:center;border:1px solid #FFE6A3;background:#FFF7D0;border-radius:8px;padding:10px 28px 10px 12px;margin-bottom:12px}.band-main{min-width:190px;flex:1.25 1 190px;border-right:1px solid #F0D28D;padding-right:16px}.band-title{min-width:0}.band-title b{display:block;font-family:Saira,"IBM Plex Sans",sans-serif;font-size:15px;line-height:1.1;color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:190px}.band-title span{display:block;margin-top:3px;color:var(--muted);font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:190px}.band-item{display:grid;grid-template-columns:1fr auto;gap:5px;align-items:center;min-width:118px;flex:1 1 118px}.band-copy small{display:block;color:var(--muted);font-size:10px;line-height:1.05}.band-copy b,.band-copy select{display:block;margin-top:2px;color:var(--ink);font-size:12px;font-weight:700;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.band-copy select{border:0;background:transparent;outline:0;padding:0}.band-caret{color:#B88600;font-weight:800;font-size:12px}.alert-wrap{margin:0 0 6px}
.summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:0 0 18px}.sum{border:1px solid var(--line);border-radius:8px;padding:11px 12px;min-width:0;background:#fff;text-align:left;cursor:pointer;color:var(--ink);font:inherit}.sum:hover{border-color:var(--gold);background:#fffdf0}.sum.final-state{border-color:var(--gold);background:var(--primary-soft)}.sum small{display:block;font-size:10px;color:var(--muted);font-weight:700;text-transform:uppercase;margin-bottom:8px;line-height:1.08}.sum.final-state small{color:#7A6400}.sum .chip{min-width:0;width:100%;padding:7px 9px;font-size:12px;justify-content:flex-start;line-height:1.12}.meta{display:block}.alertline{border:1px solid #E8C164!important;background:#FFF8DC;border-radius:7px;padding:7px 9px!important;margin:0 0 10px}.alertline small{display:block;color:var(--orange);font-size:10px;margin-bottom:1px}.alertline b{display:block;font-size:12px;line-height:1.16}.alertline.final{background:#FFF8DC;border-color:var(--gold)!important}.alertline.final small{color:#7A6400}
.tabs{display:grid;grid-template-columns:repeat(5,1fr);gap:0;background:#F6F6F4;border:1px solid var(--line);border-radius:8px;padding:0;margin:0 0 18px;overflow:hidden}.tabs button{border:0;border-bottom:2px solid transparent;background:transparent;border-radius:0;padding:12px 4px 11px;font-size:12px;font-weight:700;color:var(--muted);cursor:pointer;line-height:1.05}.tabs button.active{color:var(--ink);background:#fff;border-bottom-color:var(--gold);box-shadow:none}.panel{overflow:visible;padding:0 20px 0;flex:0 0 auto}.grid{display:grid;grid-template-columns:1fr 1fr;gap:4px 6px}.field2 label{display:block;font-size:9px;color:var(--muted);font-weight:700;margin-bottom:1px}.field2 input,.field2 select,.field2 textarea{width:100%;border:1px solid var(--line);border-radius:7px;background:var(--surface);min-height:27px;padding:3px 7px;font-size:12px;outline:0}.field2 textarea{min-height:34px;resize:vertical}.field2 input[readonly],.field2 textarea[readonly]{background:#FAFAF8;color:var(--muted)}.wide{grid-column:1/-1}.context{background:var(--orange-bg);border:1px solid #F0D28D;border-radius:9px;padding:6px;margin-bottom:6px}.block-title{display:block;font-family:Saira,"IBM Plex Sans",sans-serif;font-size:12px;font-weight:700;margin-bottom:5px}.co-head{margin-bottom:16px}.co-head b{display:block;font-size:18px}.co-head span{display:block;color:var(--muted);font-size:13px}.co-section{border-top:1px solid var(--gold);padding:16px 0 10px}.co-section:first-of-type{border-top:0}.co-section summary{display:flex;align-items:center;gap:12px;cursor:pointer;list-style:none;margin-bottom:12px}.co-section summary::-webkit-details-marker{display:none}.co-icon{width:36px;height:36px;border-radius:7px;background:var(--primary-soft);display:grid;place-items:center;color:#7A6400;font-weight:800}.co-title b{display:block;font-size:15px}.co-title span{display:block;color:var(--muted);font-size:12px}.co-chevron{margin-left:auto;color:var(--ink);font-weight:800}.section-title{font-family:Saira,"IBM Plex Sans",sans-serif;font-size:12px;font-weight:700;margin:0 0 4px;color:var(--ink)}.btn-row{display:flex;gap:8px;justify-content:flex-end;margin-top:7px}.save-bar{position:static;background:var(--surface);border-top:1px solid var(--line);padding:7px 0 0;margin:7px 0 0;z-index:4}.primary,.ghost{border-radius:9px;padding:7px 10px;font-size:12px;font-weight:700;cursor:pointer}.primary{border:0;background:var(--gold);color:var(--ink)}.primary:hover{background:var(--gold-hover)}.ghost{border:1px dashed var(--line-strong);background:white;color:var(--carbon)}
.evidence{display:grid;grid-template-columns:1fr 1fr;gap:6px}.evi{border:1px solid var(--line);border-radius:8px;padding:7px;background:white;font-size:12px;font-weight:600}.bant-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}.bant-item{display:flex;align-items:center;gap:6px;border:1px solid var(--line);border-radius:7px;background:white;padding:5px 7px;font-size:11.5px;font-weight:700}.bant-item small{margin-left:auto;color:var(--muted);font-weight:600}.evi-top{display:flex;align-items:center;justify-content:space-between;gap:6px}.vis-toggle{border:1px solid var(--line);background:#fff;border-radius:999px;padding:3px 7px;font-size:10.5px;color:var(--muted);cursor:pointer;white-space:nowrap}.vis-toggle.on{border-color:#BFE6CC;background:var(--green-bg);color:var(--green)}.evi small,.evi p{display:block;color:var(--muted);font-weight:500;margin:3px 0 0;font-size:10.5px;line-height:1.32}.evi a{color:var(--carbon);text-decoration:underline;text-decoration-color:var(--gold);text-underline-offset:3px}.read,.visible-client{border:1px solid var(--line);border-radius:9px;padding:7px;background:white}.visible-client{border-color:#BFE6CC;background:#F7FFF9}.visible-client:before{content:"Visible para cliente";display:inline-flex;margin-bottom:5px;border-radius:999px;background:var(--green-bg);color:var(--green);font-size:10px;font-weight:800;padding:2px 6px}.read p{margin:4px 0;font-size:12px}.history,.timeline{border-left:2px solid var(--line);padding-left:10px;margin-left:5px}.hist,.tl{position:relative;margin-bottom:6px}.hist small,.tl small{color:var(--muted);font-size:10.5px}.hist b,.tl b{display:block;font-size:12px;margin:1px 0}.hist:before,.tl:before{content:"";position:absolute;left:-15px;top:3px;width:7px;height:7px;border-radius:99px;background:var(--gold)}.hist-row{display:grid;grid-template-columns:1fr auto;gap:8px;align-items:start}.event-meta{font-size:11px;color:var(--muted);margin-top:2px}.event-badge{display:inline-flex;border-radius:999px;padding:2px 6px;font-size:10.5px;font-weight:700;background:var(--gray-bg);color:var(--gray);margin-left:4px}.event-badge.manual{background:var(--orange-bg);color:var(--orange)}.event-badge.client{background:var(--blue-bg);color:var(--blue)}.visibility-btn{border:1px solid var(--line);border-radius:999px;background:#fff;color:var(--red);font-size:11px;font-weight:800;width:24px;height:24px;cursor:pointer}.visibility-btn.on{border-color:#BFE6CC;background:var(--green-bg);color:var(--green)}.manual-form{border:1px solid var(--line);border-radius:9px;background:#fff;padding:8px;margin-bottom:8px}.manual-actions{display:flex;gap:6px;margin-top:5px}.mini{border:1px solid var(--line);background:#fff;border-radius:6px;padding:4px 7px;font-size:11px;cursor:pointer;color:var(--carbon)}.mini:hover{border-color:var(--gold);background:#fffdf0}.save-note{position:fixed;right:24px;bottom:18px;background:var(--carbon);color:white;border-radius:8px;padding:10px 12px;font-size:12px;font-weight:600;box-shadow:0 8px 24px rgba(26,26,26,.22);z-index:20}
.layout.open .filters{grid-template-columns:1.4fr .7fr .7fr 1fr .7fr .55fr}.layout.open .kpis{grid-template-columns:repeat(4,1fr)}.layout.open .kpi{min-height:66px;padding:8px 10px}.layout.open .kpi b{font-size:21px}.layout.open table{table-layout:fixed;font-size:10.6px}.layout.open thead th,.layout.open tbody td{padding:5px 5px}.layout.open .pill{min-width:0;width:100%;padding:4px 5px;font-size:10.2px}.layout.open .quick{height:20px;font-size:10px}.layout.open .sub{font-size:9.3px;line-height:1.2}.layout.open thead th:nth-child(1),.layout.open tbody td:nth-child(1){width:74px}.layout.open thead th:nth-child(2),.layout.open tbody td:nth-child(2){width:72px}.layout.open thead th:nth-child(3),.layout.open tbody td:nth-child(3){width:118px}.layout.open thead th:nth-child(4),.layout.open tbody td:nth-child(4){width:74px}.layout.open thead th:nth-child(5),.layout.open tbody td:nth-child(5){width:122px}.layout.open thead th:nth-child(6),.layout.open tbody td:nth-child(6){width:103px}.layout.open thead th:nth-child(7),.layout.open tbody td:nth-child(7){width:82px}.layout.open thead th:nth-child(8),.layout.open tbody td:nth-child(8){width:90px}.layout.open thead th:nth-child(9),.layout.open tbody td:nth-child(9){width:100px}.layout.open thead th:nth-child(10),.layout.open tbody td:nth-child(10){width:46px}
@media(max-width:1200px){.layout.open{grid-template-columns:minmax(0,1fr) 420px}.detail-band{grid-template-columns:minmax(150px,1fr) 1fr 1fr;padding-right:24px}.band-main{grid-row:span 2}.summary{grid-template-columns:repeat(4,minmax(0,1fr))}.grid{grid-template-columns:1fr}.tabs button{font-size:10px;padding:4px 2px}}
@media(max-width:760px){.app{min-width:0}.layout.open{grid-template-columns:1fr}.drawer{position:relative;height:auto;max-height:none}.detail-band{grid-template-columns:1fr}.band-main{grid-column:auto}.summary{display:flex;overflow-x:auto}.sum{min-width:160px}.tabs{display:flex;overflow-x:auto}.tabs button{min-width:130px}.panel{max-height:none}}
</style>
</head>
<body>
<div class="app">
  <header class="top">
    <div class="brand"><div class="hamb">&#9776;</div><img class="brand-logo" src="__CP_MARK__" alt="Conprospeccion"><div class="title"><h1>Seguimiento de reuniones</h1><p>Panel operativo</p></div></div>
    <div class="user"><button class="bell" id="bell" onclick="toggleNotifications()" aria-label="Notificaciones"></button><div class="usertext"><b>Francisca / Yanina</b>Panel interno</div></div>
  </header>
  <div class="notif" id="notifications" hidden></div>
  <div class="layout" id="layout">
    <main class="main">
      <section class="card">
        <div class="filters">
          <div class="field"><span>&#8981;</span><input id="q" placeholder="Buscar empresa, contacto, cargo, correo..." oninput="setFilter('q',this.value)"></div>
          <div class="field"><label>Mes</label><select id="fMonth" onchange="setFilter('month',this.value)"></select></div>
          <div class="field"><label>Año</label><select id="fYear" onchange="setFilter('year',this.value)"></select></div>
          <div class="field date-range"><label>Rango de fechas</label><input id="fDateFrom" type="date" onchange="setFilter('dateFrom',this.value)"><input id="fDateTo" type="date" onchange="setFilter('dateTo',this.value)"><button class="clear-date" onclick="resetDateRange()" title="Restablecer rango">x</button></div>
          <div class="field"><label>Cliente</label><select id="fClient" onchange="setFilter('client',this.value)"></select></div>
          <div class="field"><label>SDR</label><select id="fSdr" onchange="setFilter('sdr',this.value)"></select></div>
          <div class="field"><button id="moreBtn" onclick="toggleMore()">Más filtros</button></div>
        </div>
        <div class="extra" id="extraFilters">
          <div class="field"><label>Etapa Agenda</label><select id="fStatus" onchange="setFilter('status',this.value)"></select></div>
          <div class="field"><label>Evaluación CP</label><select id="fCp" onchange="setFilter('cp',this.value)"></select></div>
          <div class="field"><label>Evaluación Cliente</label><select id="fClientVal" onchange="setFilter('clientVal',this.value)"></select></div>
          <div class="field"><label>Estado Final</label><select id="fFinal" onchange="setFilter('final',this.value)"></select></div>
          <div class="field"><label>País</label><select id="fCountry" onchange="setFilter('country',this.value)"></select></div>
          <div class="field"><label>Estado del Caso</label><select id="fCaseStatus" onchange="setFilter('caseStatus',this.value)"></select></div>
        </div>
        <div class="active-filters" id="activeFilters"></div>
      </section>
      <section class="card progress">
        <div class="section-head"><b>Avance por cliente <span class="sub" style="display:inline">reuniones válidas CP / meta contractual</span></b><small onclick="filters.client='Todos';render()" style="cursor:pointer">Ver todos los clientes</small></div>
        <div class="client-row" id="clientProgress"></div>
      </section>
      <section class="card kpis" id="kpis"></section>
      <section class="card table-card">
        <div class="table-head"><div><h2>Tabla principal</h2><p>Filtros, KPIs, avance y tabla usan el mismo estado central.</p></div></div>
        <div class="table-wrap"><table><thead id="thead"></thead><tbody id="rows"></tbody></table></div>
      </section>
    </main>
    <aside class="card drawer hidden" id="drawer">
      <div class="drawer-fixed">
        <button class="close" onclick="closeDetail()" aria-label="Cerrar">&times;</button>
        <div class="detail-band" id="detailBand"></div>
        <div class="summary" id="summary"></div>
        <div class="meta alert-wrap" id="meta"></div>
        <div class="tabs" id="tabs"></div>
      </div>
      <div class="panel" id="panel"></div>
    </aside>
  </div>
</div>
<script>
function streamlitSend(type,data={}){window.parent.postMessage({isStreamlitMessage:true,type,...data},"*")}
function componentReady(){streamlitSend("streamlit:componentReady",{apiVersion:1})}
function setComponentValue(value){streamlitSend("streamlit:setComponentValue",{value,dataType:"json"})}
function setComponentHeight(){streamlitSend("streamlit:setFrameHeight",{height:Math.max(900,document.documentElement.scrollHeight)})}
componentReady();window.addEventListener("load",()=>setTimeout(setComponentHeight,100));window.addEventListener("resize",setComponentHeight);
const statuses=["Reunión futura","Reunión realizada","Reunión cancelada","Reagendar reunión"];
const cps=["","Pendiente","Válida","No válida","No necesaria"];
const clientVals=["","Pendiente","Válida","No válida","Solicita revisión","No necesaria"];
const finalOptions=["Pendiente","Reunión válida","Reunión no válida","Reunión cancelada","Reagendar reunión"];
const caseStatusOptions=["Abierto","En evaluación CP","Esperando cliente","En revisión","Cerrado"];
const cancellationActors=["Cliente","Prospecto","SDR","Conprospección"];
const rescheduleReasons=["Conflicto de agenda","Vacaciones","Enfermedad","Problema técnico","Esperando información","Cambio interno","Otro"];
const clientRevisionReasons=["No corresponde al ICP","Cargo incorrecto","Empresa incorrecta","Competencia","Sin interés comercial","BANT insuficiente","Información incorrecta","Información incompleta","Otro"];
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
meetings=meetings.map(m=>({...m,caseStatus:m.caseStatus||"Abierto",cp:m.status==="Reunión cancelada"?"No necesaria":m.cp,clientVal:m.status==="Reunión cancelada"?"No necesaria":m.clientVal,final:m.status==="Reunión cancelada"?"Reunión cancelada":m.final,clientActor:m.clientActor||m.contact||"",clientTimeline:m.clientTimeline||buildClientTimeline(m),historyVisibility:m.historyVisibility||{}}));
let selected=null, tab="Información", panelOpen=false, more=false, notifOpen=false;
let filters=defaultFilters();
let sortState={key:"dateTime",dir:"desc"};
function defaultRange(){const now=new Date();return rangeForMonth(now.getFullYear(),now.getMonth()+1)}
function defaultFilters(){const r=defaultRange();return {q:"",client:"Todos",sdr:"Todos",status:"Todos",cp:"Todos",clientVal:"Todos",final:"Todos",country:"Todos",caseStatus:"Todos",month:String(new Date().getMonth()+1),year:String(new Date().getFullYear()),...r}}
function rangeForMonth(year,month){const first=new Date(Number(year),Number(month)-1,1);const last=new Date(Number(year),Number(month),0);return {dateFrom:iso(first),dateTo:iso(last)}}
function monthOptions(){return [["1","Enero"],["2","Febrero"],["3","Marzo"],["4","Abril"],["5","Mayo"],["6","Junio"],["7","Julio"],["8","Agosto"],["9","Septiembre"],["10","Octubre"],["11","Noviembre"],["12","Diciembre"]]}
function yearOptions(){const years=[...new Set(meetings.map(m=>(parseDate(m.date)||"").slice(0,4)).filter(Boolean))];const now=String(new Date().getFullYear());if(!years.includes(now))years.push(now);return years.sort()}
function optPairs(values,current){return values.map(v=>`<option value="${esc(v[0])}" ${v[0]===current?"selected":""}>${esc(v[1])}</option>`).join("")}
function iso(d){return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`}
function esc(s){return String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[m]))}
function opt(values,current){return values.map(v=>`<option value="${esc(v)}" ${v===current?"selected":""}>${esc(v)}</option>`).join("")}
function parseDate(s){const [d,m,y]=String(s).split("/");return y&&m&&d?`${y}-${m.padStart(2,"0")}-${d.padStart(2,"0")}`:""}
function dtValue(m){const d=parseDate(m.date);const hour=m.time.includes("PM")&&m.time.slice(0,2)!=="12"?Number(m.time.slice(0,2))+12:Number(m.time.slice(0,2));return `${d} ${String(hour).padStart(2,"0")}${m.time.slice(2,5)}`}
function finalStatus(m){return m.final||"Pendiente"}
function finalDisplay(m){return finalStatus(m)==="Pendiente"?"Pendiente de cierre":finalStatus(m)}
function persist(){localStorage.setItem(storageKey,JSON.stringify(meetings))}
function notify(msg){let n=document.getElementById("saveNote");if(!n){n=document.createElement("div");n.id="saveNote";n.className="save-note";document.body.appendChild(n)}n.textContent=msg;clearTimeout(window.__saveNoteTimer);window.__saveNoteTimer=setTimeout(()=>n.remove(),1800)}
function compactMeeting(m){return {id:m.id,clientSlug:m.clientSlug,client:m.client,date:m.date,time:m.time,scheduledDate:m.scheduledDate,company:m.company,contact:m.contact,role:m.role,email:m.email,phone:m.phone,country:m.country,industry:m.industry,sdr:m.sdr,status:m.status,cp:m.cp,clientVal:m.clientVal,final:m.final,caseStatus:m.caseStatus,info:m.info,icp:m.icp,bant:m.bant,just:m.just,notes:m.notes,next:m.next,clientReason:m.clientReason,clientComment:m.clientComment,clientActor:m.clientActor,clientEvidence:m.clientEvidence,cpResponse:m.cpResponse,finalReason:m.finalReason,finalClientText:m.finalClientText,finalInternalNote:m.finalInternalNote,evidence:m.evidence,historyVisibility:m.historyVisibility,cancelWho:m.cancelWho,cancelReason:m.cancelReason,cancelComment:m.cancelComment,rescheduleWho:m.rescheduleWho,rescheduleReason:m.rescheduleReason,rescheduleOld:m.rescheduleOld,rescheduleNew:m.rescheduleNew,rescheduleComment:m.rescheduleComment}}
async function saveMeeting(m,section,silent=false,extra={}){if(!m||!m.id||!m.clientSlug){if(!silent)notify("No se pudo guardar: falta cliente o reunión");return false}try{if(!silent)notify("Guardando...");setComponentValue({nonce:`${Date.now()}-${Math.random()}`,section,meeting:compactMeeting(m),...extra});if(!silent)notify(`${section} guardado`);return true}catch(err){console.error(err);notify(`Error al guardar: ${err.message||err}`);return false}}
function saveSection(section){const m=current();addHistory(m,`Guardar ${section}`,"Pendiente","Guardado");persist();saveMeeting(m,section);render()}
function saveBar(section,label){return `<div class="btn-row save-bar"><button class="primary" onclick="saveSection('${section}')">${label}</button></div>`}
function buildClientTimeline(m){if(m.status==="Reunión cancelada"||m.clientVal==="No necesaria")return[{when:"No aplica",actor:"Sistema",status:"No necesaria",reason:"Etapa agenda cancelada",comment:"No se requiere acción del cliente en el portal."}];const items=[{when:"Pendiente inicial",actor:"Portal cliente",status:"Pendiente",reason:"",comment:"Esperando acción del cliente"}];if(m.clientVal&&m.clientVal!=="Pendiente"){items.push({when:m.clientDate||"Sin fecha registrada",actor:m.clientActor||m.contact||"Cliente",status:m.clientVal,reason:m.clientReason||"",comment:m.clientComment||""})}if(m.cpResponse){items.push({when:"Respuesta interna",actor:"Conprospección",status:"Respuesta enviada",reason:"",comment:m.cpResponse})}return items}
function finalAlert(m){if(finalStatus(m)==="Pendiente")return"Estado final pendiente de cierre administrativo por Conprospección";return""}
function operationalAlert(m){if(m.clientVal==="Solicita revisión")return"Cliente solicitó revisión: requiere respuesta interna";if(m.status==="Reunión cancelada")return"Registrar motivo de cancelación. CP y cliente quedan como no necesarios.";if(m.status==="Reagendar reunión")return"Registrar nueva fecha y evaluar CP si corresponde";if(m.cp!=="Pendiente"&&m.cp!=="No necesaria"&&finalStatus(m)==="Pendiente")return"Evaluación lista, caso aún sin cierre administrativo";return"Sin alertas operativas"}
function tone(v){if(["Válida","Confirmada","Reunión realizada","Cumple","Reunión válida"].includes(v))return"green";if(["Pendiente","Pendiente de cierre","Reagendar reunión"].includes(v))return"orange";if(["Reunión futura"].includes(v))return"blue";if(["Solicita revisión","En revisión"].includes(v))return"purple";if(["No válida","Reunión cancelada","Reunión no válida"].includes(v))return"red";if(["No necesaria"].includes(v))return"gray";return"gray"}
function current(){return meetings.find(m=>m.id===selected)||meetings[0]}
function addHistory(m,field,from,to){if(JSON.stringify(from)===JSON.stringify(to))return;m.history=m.history||[];m.history.unshift({when:new Date().toLocaleString("es-CL"),user:"Francisca / Yanina",field,from,to})}
function labelField(f){return {status:"Etapa Agenda",cp:"Evaluación CP",clientVal:"Evaluación Cliente",final:"Estado Final",caseStatus:"Estado del Caso",sdr:"SDR asignada",icp:"ICP",info:"Información reunión",just:"Justificación CP",notes:"Notas internas",cpResponse:"Respuesta CP"}[f]||f}
function recordClientEvent(m,field,from,to){if(JSON.stringify(from)===JSON.stringify(to))return;const status=field==="clientVal"?to:m.clientVal;const reason=field==="clientReason"?to:m.clientReason;const comment=field==="clientComment"?to:(field==="cpResponse"?`Respuesta CP: ${to}`:m.clientComment);m.clientTimeline=m.clientTimeline||[];m.clientTimeline.unshift({when:new Date().toLocaleString("es-CL"),actor:field==="cpResponse"?"Conprospección":(m.clientActor||m.contact||"Cliente"),status,reason:reason||"",comment:comment||""})}
function setField(id,field,value){const m=meetings.find(x=>x.id===id);const old=m[field];m[field]=value;if(field==="status"&&value==="Reunión cancelada"){const oldCp=m.cp,oldClient=m.clientVal,oldFinal=m.final;m.cp="No necesaria";m.clientVal="No necesaria";m.final="Reunión cancelada";m.clientTimeline=buildClientTimeline(m);addHistory(m,"Evaluación CP",oldCp,"No necesaria");addHistory(m,"Evaluación Cliente",oldClient,"No necesaria");addHistory(m,"Estado Final",oldFinal,"Reunión cancelada")}if(field==="status"&&old==="Reunión cancelada"&&value!=="Reunión cancelada"){if(m.cp==="No necesaria")m.cp="Pendiente";if(m.clientVal==="No necesaria")m.clientVal="Pendiente";if(m.final==="Reunión cancelada")m.final="Pendiente";m.clientTimeline=buildClientTimeline(m)}addHistory(m,labelField(field),old,value);if(["clientVal","clientReason","clientComment","clientEvidence","cpResponse"].includes(field)){recordClientEvent(m,field,old,value)}selected=id;panelOpen=true;if(field==="cp"&&value&&value!=="Pendiente")tab="Evaluación CP";if(field==="status"&&["Reunión cancelada","Reagendar reunión"].includes(value))tab="Información";if(field==="final")tab="Estado Final";if(field==="clientVal")tab="Evaluación Cliente";persist();saveMeeting(m,labelField(field),true);render()}
function setFilter(k,v){filters[k]=v;if(k==="month"||k==="year"){Object.assign(filters,rangeForMonth(filters.year,filters.month))}syncDependent(k);render()}
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
function renderFilters(rows){const opts=optionSets(applyFilters({ignore:["sdr","country","status","cp","clientVal","final","caseStatus"]}));document.getElementById("q").value=filters.q;document.getElementById("fMonth").innerHTML=optPairs(monthOptions(),filters.month);document.getElementById("fYear").innerHTML=opt(yearOptions(),filters.year);document.getElementById("fClient").innerHTML=opt(["Todos",...optionSets(meetings).client],filters.client);document.getElementById("fDateFrom").value=filters.dateFrom;document.getElementById("fDateTo").value=filters.dateTo;document.getElementById("fSdr").innerHTML=opt(["Todos",...opts.sdr],filters.sdr);document.getElementById("fStatus").innerHTML=opt(["Todos",...opts.status],filters.status);document.getElementById("fCp").innerHTML=opt(["Todos",...opts.cp],filters.cp);document.getElementById("fClientVal").innerHTML=opt(["Todos",...opts.clientVal],filters.clientVal);document.getElementById("fFinal").innerHTML=opt(["Todos",...opts.final],filters.final);document.getElementById("fCountry").innerHTML=opt(["Todos",...opts.country],filters.country);document.getElementById("fCaseStatus").innerHTML=opt(["Todos",...opts.caseStatus],filters.caseStatus);document.getElementById("extraFilters").classList.toggle("open",more);document.getElementById("moreBtn").textContent=`Más filtros${activeFilterCount()?` (${activeFilterCount()})`:""}`;renderActiveFilters()}
function renderActiveFilters(){const d=defaultRange();const labels={q:"Buscar",client:"Cliente",sdr:"SDR",status:"Etapa",cp:"CP",clientVal:"Cliente",final:"Final",country:"País",caseStatus:"Caso"};const chips=[];Object.keys(labels).forEach(k=>{if((k==="q"&&filters.q)||(k!=="q"&&filters[k]&&filters[k]!=="Todos"))chips.push(`<span class="filter-chip">${labels[k]}: ${esc(filters[k])}<button onclick="clearFilter('${k}')">x</button></span>`)});if(filters.dateFrom!==d.dateFrom||filters.dateTo!==d.dateTo)chips.push(`<span class="filter-chip">Fecha: ${filters.dateFrom} / ${filters.dateTo}<button onclick="clearFilter('date')">x</button></span>`);if(chips.length)chips.push(`<button class="clear-all" onclick="clearAll()">Limpiar filtros</button>`);document.getElementById("activeFilters").innerHTML=chips.join("")}
function renderKpis(rows){const total=rows.length||1;const cards=[["Total reuniones",rows.length,"Todas las reuniones","blue","T",()=>{filters.status="Todos";filters.cp="Todos";filters.clientVal="Todos";filters.final="Todos"}],["Pendiente CP",rows.filter(x=>x.cp==="Pendiente").length,pct(rows.filter(x=>x.cp==="Pendiente").length,total),"orange","P",()=>toggleFilter("cp","Pendiente")],["CP válida",rows.filter(x=>x.cp==="Válida").length,pct(rows.filter(x=>x.cp==="Válida").length,total),"green","V",()=>toggleFilter("cp","Válida")],["Solicita revisión",rows.filter(x=>x.clientVal==="Solicita revisión").length,pct(rows.filter(x=>x.clientVal==="Solicita revisión").length,total),"purple","R",()=>toggleFilter("clientVal","Solicita revisión")],["Final válida",rows.filter(x=>finalStatus(x)==="Reunión válida").length,pct(rows.filter(x=>finalStatus(x)==="Reunión válida").length,total),"green","F",()=>toggleFilter("final","Reunión válida")],["Reagendar",rows.filter(x=>x.status==="Reagendar reunión").length,pct(rows.filter(x=>x.status==="Reagendar reunión").length,total),"orange","A",()=>toggleFilter("status","Reagendar reunión")],["Canceladas",rows.filter(x=>x.status==="Reunión cancelada").length,pct(rows.filter(x=>x.status==="Reunión cancelada").length,total),"red","C",()=>toggleFilter("status","Reunión cancelada")],["No válidas final",rows.filter(x=>finalStatus(x)==="Reunión no válida").length,pct(rows.filter(x=>finalStatus(x)==="Reunión no válida").length,total),"red","X",()=>toggleFilter("final","Reunión no válida")]];window.__kpiActions=cards.map(c=>c[5]);document.getElementById("kpis").innerHTML=cards.map((i,idx)=>`<div class="kpi ${kpiActive(i[0])?"active":""}" onclick="__kpiActions[${idx}]();render()"><div class="ico ${i[3]}">${i[4]}</div><div><span>${i[0]}</span><b>${i[1]}</b><small>${i[2]}</small></div></div>`).join("")}
function kpiActive(label){return label==="Pendiente CP"&&filters.cp==="Pendiente"||label==="CP válida"&&filters.cp==="Válida"||label==="Solicita revisión"&&filters.clientVal==="Solicita revisión"||label==="Final válida"&&filters.final==="Reunión válida"||label==="Reagendar"&&filters.status==="Reagendar reunión"||label==="Canceladas"&&filters.status==="Reunión cancelada"||label==="No válidas final"&&filters.final==="Reunión no válida"}
function toggleFilter(k,v){filters[k]=filters[k]===v?"Todos":v}
function pct(n,total){return total?`${((n/total)*100).toFixed(1)}% del total`:"0% del total"}
function clientColor(code){return {Clickie:"#F59E0B",GBS:"#7C3AED",BambuTech:"#15803D"}[code]||"#9A9A98"}
function goalState(p){if(p>=75)return["EN META","goal-ok"];if(p>=20)return["A MEDIAS","goal-mid"];return["ATRASADO","goal-bad"]}
function renderProgress(rows){let codes=[...new Set(rows.map(m=>m.client))];if(filters.client!=="Todos")codes=[filters.client];document.getElementById("clientProgress").innerHTML=codes.map(code=>{const goal=clientGoals[code]||((rows.find(m=>m.client===code)||meetings.find(m=>m.client===code)||{}).goal||0);const valid=rows.filter(m=>m.client===code&&m.cp==="Válida").length;const p=goal?Math.round(valid/goal*100):0;const state=goalState(p);const color=clientColor(code);return `<div class="card client" onclick="filters.client='${esc(code)}';render()" style="cursor:pointer;--client-color:${color}"><div class="client-top"><div class="client-name"><span class="client-badge">${esc(code[0]||"?")}</span><span>${esc(code)}</span></div><span class="client-count">${p}%</span></div><div class="bar"><div class="fill" style="width:${Math.min(p,100)}%"></div></div><div class="client-foot"><span class="client-ratio">${valid} / ${goal}</span><span class="goal-pill ${state[1]}">${state[0]}</span></div></div>`}).join("")||`<div class="sub">Sin reuniones para los filtros aplicados.</div>`}
function renderHead(){const cols=[["dateTime","Fecha y hora"],["client","Cliente"],["company","Empresa"],["sdr","SDR"],["contact","Contacto"],["status","Etapa Agenda"],["cp","Evaluación CP"],["clientVal","Evaluación Cliente"],["final","Estado Final"],["actions","Acciones"]];const filterable=["client","sdr","status","cp","clientVal","final"];const allOpts=optionSets(applyFilters({ignore:filterable}));const header=(k,label)=>{if(k==="actions")return label;if(filterable.includes(k)){const active=filters[k]!=="Todos";const options=[`<option value="Todos">${label}</option>`].concat((allOpts[k]||[]).map(v=>`<option value="${esc(v)}" ${filters[k]===v?"selected":""}>${esc(v)}</option>`)).join("");return `<select class="quick ${active?"active":""}" title="Filtrar ${label}" onchange="setFilter('${k}',this.value)">${options}</select>`}return `<button class="sort" onclick="setSort('${k}')">${label} ${sortState.key===k?(sortState.dir==="asc"?"asc":"desc"):""}</button>`};document.getElementById("thead").innerHTML=`<tr>${cols.map(c=>`<th>${header(c[0],c[1])}</th>`).join("")}</tr>`}
function renderRows(rows){document.getElementById("rows").innerHTML=sortRows(rows).map(m=>`<tr class="${m.id===selected?"selected":""}" onclick="openDetail(${m.id})"><td><b>${m.date}</b><span class="sub">${m.time}</span></td><td><span class="avatar-sm ${m.client.toLowerCase()}">${m.client[0]}</span><span class="company">${m.client}</span></td><td>${esc(m.company)}</td><td>${esc(m.sdr)||"<span class='sub'>Sin asignar</span>"}</td><td>${esc(m.contact)}<span class="sub">${esc(m.role)}</span></td><td onclick="event.stopPropagation()"><select class="pill ${tone(m.status)}" onchange="setField(${m.id},'status',this.value)">${opt(statuses,m.status)}</select></td><td onclick="event.stopPropagation()"><select class="pill ${tone(m.cp)}" onchange="setField(${m.id},'cp',this.value)">${opt(cps,m.cp)}</select></td><td onclick="event.stopPropagation()"><select class="pill ${tone(m.clientVal)}" onchange="setField(${m.id},'clientVal',this.value)">${opt(clientVals,m.clientVal)}</select></td><td onclick="event.stopPropagation()"><select class="pill ${tone(finalStatus(m))}" onchange="setField(${m.id},'final',this.value)">${opt(finalOptions,finalStatus(m))}</select></td><td><button class="action" onclick="event.stopPropagation();openDetail(${m.id})">Ver</button></td></tr>`).join("")}
function openDetail(id){selected=id;tab="Información";panelOpen=true;render()}
function closeDetail(){panelOpen=false;document.body.classList.remove("detail-open");render()}
function field(k,label,type="input"){const m=current();const val=esc(m[k]);return `<div class="field2 ${type==="textarea"?"wide":""}"><label>${label}</label>${type==="textarea"?`<textarea onchange="setField(${m.id},'${k}',this.value)">${val}</textarea>`:`<input value="${val}" onchange="setField(${m.id},'${k}',this.value)">`}</div>`}
function selectField(k,label,values){const m=current();return `<div class="field2"><label>${label}</label><select onchange="setField(${m.id},'${k}',this.value)">${opt(values,m[k])}</select></div>`}
function renderPanel(){if(!panelOpen)return;const m=current();document.getElementById("detailBand").innerHTML=`<div class="band-main"><div class="band-title"><b>${esc(m.company||m.contact||"Detalle de reunión")}</b><span data-role="contact-subtitle">${esc(m.contact||"Sin contacto")} - ${esc(m.client||"Sin cliente")}</span></div></div><div class="band-item"><span class="band-copy"><small>Fecha y hora</small><b>${esc(m.date)} ${esc(m.time)}</b></span></div><div class="band-item"><span class="band-copy"><small>SDR asignada</small><select onchange="setField(${m.id},'sdr',this.value)">${opt([...new Set(meetings.map(x=>x.sdr).filter(Boolean))],m.sdr)}</select></span><span class="band-caret">⌄</span></div>`;const states=[["Etapa Agenda",m.status,"","Información"],["Evaluación CP",m.cp,"","Evaluación CP"],["Evaluación Cliente",m.clientVal,"","Evaluación Cliente"],["Estado Final",finalDisplay(m),"final-state","Estado Final"]];document.getElementById("summary").innerHTML=states.map(i=>`<button class="sum ${i[2]}" onclick="tab='${i[3]}';renderPanel()" title="Ver detalle de ${esc(i[0])}"><small>${i[0]}</small><span class="chip ${tone(i[1])}" title="${esc(i[1])}">${esc(i[1])}</span></button>`).join("");const alert=operationalAlert(m);const fAlert=finalAlert(m);document.getElementById("meta").innerHTML=`${fAlert?`<div class="alertline final"><small>Alerta final</small><b>${esc(fAlert)}</b></div>`:""}${alert&&alert!=="Sin alertas operativas"?`<div class="alertline"><small>Alerta operativa</small><b>${esc(alert)}</b></div>`:""}`;const tabs=["Información","Evaluación CP","Evaluación Cliente","Estado Final","Historial"];document.getElementById("tabs").innerHTML=tabs.map(t=>`<button class="${tab===t?"active":""}" onclick="tab='${t}';renderPanel()">${t}</button>`).join("");let html="";if(tab==="Información")html=infoTab(m);if(tab==="Evaluación CP")html=cpTab(m);if(tab==="Evaluación Cliente")html=clientTab(m);if(tab==="Estado Final")html=finalTab(m);if(tab==="Historial")html=historyTab(m);document.getElementById("panel").innerHTML=html}
function infoSection(title,subtitle,icon,body,open=true){return `<details class="co-section" ${open?"open":""}><summary><span class="co-icon">${icon}</span><span class="co-title"><b>${title}</b><span>${subtitle}</span></span><span class="co-chevron">⌃</span></summary><div class="grid">${body}</div></details>`}
function infoTab(m){let ctx="";if(m.status==="Reunión cancelada")ctx=`<div class="context"><b>Motivo de cancelación</b><div class="grid">${selectField("cancelWho","Quién canceló",cancellationActors)}${field("cancelReason","Motivo")}${field("cancelComment","Detalle / respaldo","textarea")}</div><div class="btn-row"><button class="primary" onclick="saveSection('Cancelación')">Guardar cancelación</button></div></div>`;if(m.status==="Reagendar reunión")ctx=`<div class="context"><b>Motivo de reagendamiento</b><div class="grid">${selectField("rescheduleWho","Quién solicita",cancellationActors)}${selectField("rescheduleReason","Motivo",rescheduleReasons)}${field("rescheduleOld","Fecha anterior")}${field("rescheduleNew","Nueva fecha")}${field("rescheduleComment","Detalle / respaldo","textarea")}</div><div class="btn-row"><button class="primary" onclick="saveSection('Reagendamiento')">Guardar reagendamiento</button></div></div>`;return `<div class="co-head"><b>Información de la reunión</b><span>Completa y actualiza todos los datos.</span></div>`+ctx+infoSection("Empresa","Información de la empresa","▣",`${field("company","Nombre de empresa")}${field("industry","Industria")}${field("country","País")}${field("website","Sitio web")}${field("linkedinCompany","LinkedIn empresa")}${field("companyInfo","Información adicional empresa","textarea")}`)+infoSection("Contacto","Información de la persona","○",`${field("contact","Nombre del contacto")}${field("role","Cargo")}${field("email","Correo electrónico")}${field("phone","Teléfono")}${field("linkedin","LinkedIn")}${field("contactInfo","Información adicional contacto","textarea")}`)+infoSection("Reunión","Información de la reunión","▣",`${field("date","Fecha")}${field("time","Hora")}${field("sdr","SDR asignada")}${field("sourceChannel","Canal de origen")}${field("meet","Enlace reunión")}${field("ghlContact","Ficha contacto")}${field("ghlOpp","Ficha oportunidad")}${field("info","Información de preparación","textarea")}${field("operationalNotes","Observaciones operativas","textarea")}`)+saveBar("Información","Guardar información")}
function evidenceCard(e,idx){const link=e.url?`<small><a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.name||"Abrir")}</a></small>`:`<small>${esc(e.name||"Disponible")}</small>`;const text=e.text?`<p>${esc(e.text).slice(0,420)}</p>`:"";const visible=!!e.clientVisible;return `<div class="evi"><div class="evi-top"><span>${e.valid?"OK ":""}${esc(e.type)}</span><button class="vis-toggle ${visible?"on":""}" onclick="event.stopPropagation();toggleEvidenceVisibility(${idx})">${visible?"Cliente ve":"Solo interno"}</button></div>${link}${text}</div>`}
function toggleEvidenceVisibility(idx){const m=current();const e=(m.evidence||[])[idx];if(!e)return;e.clientVisible=!e.clientVisible;const description=`${e.type}: ${e.clientVisible?"Visible para cliente":"Solo interno"}`;addHistory(m,"Visibilidad evidencia",e.type,e.clientVisible?"Visible para cliente":"Solo interno");persist();saveMeeting(m,"Visibilidad evidencia",false,{manualHistory:{field:"Visibilidad evidencia",description,manual:true,visibility:e.clientVisible?"Visible para el cliente":"Solo uso interno",client:m.client,meetingId:m.id}});renderPanel()}
function cpTab(m){m.evidence=m.evidence||[];return `<div class="grid"><div class="field2"><label>Evaluación CP</label><select onchange="setField(${m.id},'cp',this.value)">${opt(cps,m.cp)}</select></div><div class="field2"><label>ICP</label><select onchange="setField(${m.id},'icp',this.value)">${opt(["No evaluado","Cumple","No cumple"],m.icp)}</select></div><div class="wide"><span class="block-title">BANT</span><div class="bant-grid">${Object.keys(m.bant).map(k=>`<label class="bant-item"><input type="checkbox" ${m.bant[k]?"checked":""} onchange="const m=current();const old={...m.bant};m.bant['${k}']=this.checked;addHistory(m,'BANT',old,{...m.bant});persist();saveMeeting(m,'BANT',true);render()"> ${k}<small>${m.bant[k]?"Sí":"No"}</small></label>`).join("")}</div></div><div class="wide visible-client">${field("just","Justificación CP","textarea")}</div>${field("notes","Nota interna CP","textarea")}</div><span class="block-title" style="margin-top:10px">Evidencias y archivos</span><div class="evidence">${m.evidence.map(evidenceCard).join("")||"<span class='sub'>Sin evidencia sincronizada todavía.</span>"}<button class="ghost" onclick="addEvidence('Archivo')">Subir archivo</button><button class="ghost" onclick="addEvidence('Enlace')">Pegar enlace</button><button class="ghost" onclick="addEvidence('Comentario')">Agregar comentario</button></div>${saveBar("Evaluación CP","Guardar Evaluación CP")}`}
function clientTimeline(m){const items=(m.clientTimeline&&m.clientTimeline.length?m.clientTimeline:buildClientTimeline(m));return `<span class="block-title" style="margin-top:8px">Seguimiento cliente</span><div class="timeline">${items.map(i=>`<div class="tl"><small>${esc(i.when)} - ${esc(i.actor||"Cliente")}</small><b>${esc(i.status||"Pendiente")}</b>${i.reason?`<div class="event-meta">Motivo: ${esc(i.reason)}</div>`:""}${i.comment?`<div class="event-meta">${esc(i.comment)}</div>`:""}</div>`).join("")}</div>`}
function clientTab(m){if(m.status==="Reunión cancelada"||m.clientVal==="No necesaria")return `<div class="read"><p><b>Estado actual:</b> No necesaria</p><p><b>Regla:</b> Una reunión cancelada no requiere validación del cliente.</p><p><b>Decisión final:</b> Conprospección puede evaluar CP y cerrar el Estado Final manualmente.</p></div>${clientTimeline(m)}`;return `<div class="read"><p><b>Estado actual:</b> ${esc(m.clientVal)}</p><p><b>Última acción:</b> ${esc(m.clientDate)||"Sin fecha registrada"}</p><p><b>Contacto cliente:</b> ${esc(m.clientActor||m.contact)||"Sin contacto registrado"}</p><p><b>Motivo:</b> ${esc(m.clientReason)||"Sin motivo registrado"}</p><p><b>Comentario:</b> ${esc(m.clientComment)||"Sin comentario registrado"}</p></div><div class="grid" style="margin-top:8px"><div class="field2"><label>Evaluación Cliente</label><input value="${esc(m.clientVal)}" readonly></div><div class="field2"><label>Contacto cliente</label><input value="${esc(m.clientActor||m.contact||"")}" readonly></div><div class="field2 wide"><label>Comentario ingresado por cliente</label><textarea readonly>${esc(m.clientComment||"Sin comentario registrado")}</textarea></div><div class="field2"><label>Evidencia aportada por cliente</label><input value="${esc(m.clientEvidence||"Sin evidencia registrada")}" readonly></div></div>${clientTimeline(m)}<div class="field2 wide" style="margin-top:8px"><label>Respuesta de Conprospección</label><textarea onchange="setField(${m.id},'cpResponse',this.value)">${esc(m.cpResponse)}</textarea></div>${saveBar("Evaluación Cliente","Guardar respuesta")}`}
function finalTab(m){const alert=operationalAlert(m);const fAlert=finalAlert(m);return `<div class="grid"><div class="field2"><label>Estado Final</label><select onchange="setField(${m.id},'final',this.value)">${opt(finalOptions,finalStatus(m))}</select><span class="sub">Cierre administrativo definido manualmente por Conprospección.</span></div><div class="field2"><label>Estado del Caso</label><select onchange="setField(${m.id},'caseStatus',this.value)">${opt(caseStatusOptions,m.caseStatus)}</select><span class="sub">Seguimiento interno, no visible al cliente.</span></div>${fAlert?`<div class="field2 wide"><label>Alerta final</label><input value="${esc(fAlert)}" readonly></div>`:""}${alert&&alert!=="Sin alertas operativas"?`<div class="field2 wide"><label>Alerta operativa</label><input value="${esc(alert)}" readonly></div>`:""}${field("finalReason","Motivo final interno","textarea")}<div class="wide"><span class="sub">Motivo contractual/administrativo para trazabilidad interna.</span></div><div class="wide visible-client">${field("finalClientText","Mensaje al cliente","textarea")}</div><div class="wide"><span class="sub">Texto publicable para el portal del cliente. No incluye notas internas.</span></div>${field("finalInternalNote","Nota interna","textarea")}</div>${saveBar("Estado Final","Guardar Estado Final")}`}
function historySource(h){if(h.manual)return"Nota manual";if(String(h.user||"").toLowerCase().includes("cliente"))return"Cliente";if(String(h.user||"").toLowerCase().includes("ghl")||String(h.user||"").toLowerCase().includes("sistema"))return"Sistema";return"Conprospección"}
function historyText(h){if(h.description)return esc(h.description);const from=typeof h.from==="undefined"?"":JSON.stringify(h.from);const to=typeof h.to==="undefined"?"":JSON.stringify(h.to);return `${esc(from)} -> ${esc(to)}`}
function latestWhen(m,field){const hit=(m.history||[]).find(h=>h.field===field);return hit?hit.when:""}
function eventVisible(m,key,def=false){m.historyVisibility=m.historyVisibility||{};return key in m.historyVisibility?m.historyVisibility[key]:def}
function visibilityLabel(v){return v?"✓":"×"}
function visibleHistory(m){const items=[];items.push({key:"fecha_agenda",when:m.scheduledDate||m.date||"Sin fecha",user:"Sistema",field:"Fecha Agenda",description:m.scheduledDate||m.date||"Sin fecha registrada",visibility:eventVisible(m,"fecha_agenda",false)});if(m.status==="Reunión realizada")items.push({key:"fecha_realizada",when:latestWhen(m,"Etapa Agenda")||m.date||"Sin fecha",user:"Sistema",field:"Fecha reunión realizada",description:`${m.date||""} ${m.time||""}`.trim(),visibility:eventVisible(m,"fecha_realizada",false)});if(m.cp&&m.cp!=="Pendiente"&&m.cp!=="")items.push({key:"fecha_cp",when:latestWhen(m,"Evaluación CP")||"Sin fecha",user:"Conprospección",field:"Fecha evaluación CP",description:m.cp,visibility:eventVisible(m,"fecha_cp",true)});if(m.clientVal&&m.clientVal!=="Pendiente"&&m.clientVal!=="")items.push({key:"fecha_cliente",when:latestWhen(m,"Evaluación Cliente")||m.clientDate||"Sin fecha",user:m.clientVal==="No necesaria"?"Sistema":"Cliente",field:"Fecha evaluación cliente",description:m.clientVal,visibility:eventVisible(m,"fecha_cliente",m.clientVal!=="No necesaria")});if(finalStatus(m)!=="Pendiente")items.push({key:"fecha_final",when:latestWhen(m,"Estado Final")||"Sin fecha",user:"Conprospección",field:"Fecha Estado Final",description:finalStatus(m),visibility:eventVisible(m,"fecha_final",true)});const manual=(m.history||[]).map((h,idx)=>({...h,_idx:idx,key:`manual_${idx}`,user:String(h.user||"").toUpperCase()==="GHL"?"Sistema":h.user,visibility:h.visibility==="Visible para el cliente"})).filter(h=>h.manual);return items.concat(manual)}
function historyTab(m){const items=visibleHistory(m);const form=`<div class="manual-form"><span class="block-title">Agregar comentario adicional</span><div class="grid"><div class="field2"><label>Tipo de actualización</label><select id="manualType">${opt(["Fecha Agenda","Fecha reunión realizada","Evaluación CP","Evaluación Cliente","Estado Final","Comentario adicional"],"Comentario adicional")}</select></div><div class="field2"><label>Visibilidad</label><select id="manualVisibility">${opt(["Solo uso interno","Visible para el cliente"],"Solo uso interno")}</select></div><div class="field2 wide"><label>Descripción</label><textarea id="manualText" placeholder="Escribe una actualización breve"></textarea></div></div><div class="btn-row"><button class="primary" onclick="addManualHistory()">Agregar comentario</button></div><small class="sub">Esta nota no modifica automáticamente los estados operativos.</small></div>`;return form+`<div class="history">${items.length?items.map((h)=>{const source=historySource(h);const cls=h.manual?"manual":source==="Cliente"?"client":"";const visible=!!h.visibility;return `<div class="hist"><div class="hist-row"><div><small>${esc(h.when)} - ${esc(h.user||"Sistema")} <span class="event-badge ${cls}">${source}</span></small><b>${esc(h.field||"Actualización")}</b><div>${historyText(h)}</div>${h.manual?`<div class="manual-actions"><button class="mini" onclick="editManualHistory(${h._idx})">Editar</button><button class="mini" onclick="deleteManualHistory(${h._idx})">Eliminar</button></div>`:""}</div><button class="visibility-btn ${visible?"on":""}" title="${visible?"Visible para cliente":"Solo uso interno"}" onclick="toggleHistoryVisibility('${h.key}',${h._idx===undefined?"null":h._idx})">${visibilityLabel(visible)}</button></div></div>`}).join(""):"<span class='sub'>Sin cambios relevantes.</span>"}</div>`}
function toggleHistoryVisibility(key,idx){const m=current();m.historyVisibility=m.historyVisibility||{};if(idx!==null&&idx!==undefined){const h=(m.history||[])[idx];if(h){h.visibility=h.visibility==="Visible para el cliente"?"Solo uso interno":"Visible para el cliente";m.historyVisibility[key]=h.visibility==="Visible para el cliente"}}else{m.historyVisibility[key]=!eventVisible(m,key,false)}persist();saveMeeting(m,"Visibilidad historial",true,{manualHistory:{field:"Visibilidad historial",description:`${key}: ${eventVisible(m,key,false)?"Visible para cliente":"Solo uso interno"}`,manual:true,visibility:"Solo uso interno",client:m.client,meetingId:m.id}});renderPanel()}
function addManualHistory(){const m=current();const text=(document.getElementById("manualText").value||"").trim();if(!text)return;const type=document.getElementById("manualType").value;const visibility=document.getElementById("manualVisibility").value;const h={when:new Date().toLocaleString("es-CL"),user:"Francisca / Yanina",field:type,description:text,manual:true,visibility,client:m.client,meetingId:m.id};m.history=m.history||[];m.history.unshift(h);persist();saveMeeting(m,type,false,{manualHistory:h});renderPanel();notify("Actualización agregada al historial")}
function editManualHistory(idx){const m=current();const h=(m.history||[])[idx];if(!h||!h.manual)return;const next=prompt("Corregir actualización manual",h.description||"");if(next===null)return;const old=h.description||"";h.description=next;const audit={when:new Date().toLocaleString("es-CL"),user:"Francisca / Yanina",field:"Auditoría nota manual",description:`Nota manual editada: ${old} -> ${next}`,manual:false,visibility:"Solo uso interno",client:m.client,meetingId:m.id};m.history.unshift(audit);persist();saveMeeting(m,"Auditoría nota manual",true,{manualHistory:audit});renderPanel()}
function deleteManualHistory(idx){const m=current();const h=(m.history||[])[idx];if(!h||!h.manual)return;if(!confirm("Eliminar esta actualización manual?"))return;const old=h.description||"";m.history.splice(idx,1);const audit={when:new Date().toLocaleString("es-CL"),user:"Francisca / Yanina",field:"Auditoría nota manual",description:`Nota manual eliminada: ${old}`,manual:false,visibility:"Solo uso interno",client:m.client,meetingId:m.id};m.history.unshift(audit);persist();saveMeeting(m,"Auditoría nota manual",true,{manualHistory:audit});renderPanel()}
function addEvidence(type="Manual"){const m=current();const name=prompt(type==="Enlace"?"Pega el enlace":"Nombre, archivo o comentario de evidencia");if(!name)return;m.evidence=m.evidence||[];m.evidence.push({type,name,valid:true,source:"manual",clientVisible:false});addHistory(m,`Carga ${type}`,"",name);persist();saveMeeting(m,"Evidencia",false);render()}
function buildNotifications(){return meetings.flatMap(m=>(m.history||[]).slice(0,3).map(h=>({client:m.client,company:m.company,contact:m.contact,type:h.field,when:h.when,state:h.to}))).filter(n=>n.type!=="Guardar Historial").slice(0,9)}
function toggleNotifications(){notifOpen=!notifOpen;renderNotifications()}
function renderNotifications(){const box=document.getElementById("notifications");const events=buildNotifications();document.getElementById("bell").toggleAttribute("data-count",events.length>0);if(events.length>0)document.getElementById("bell").setAttribute("data-count",events.length);box.hidden=!notifOpen;box.innerHTML=`<h3>Notificaciones operativas</h3>${events.length?events.map(e=>`<div class="notif-item"><b>${esc(e.type)}</b><span>${esc(e.client)} - ${esc(e.company)} - ${esc(e.contact)}</span><br><small>${esc(e.when)} - ${esc(e.state)}</small></div>`).join(""):`<div class="notif-item">Sin novedades pendientes.</div>`}`}
function render(){const rows=applyFilters();document.body.classList.toggle("detail-open",panelOpen);document.getElementById("layout").classList.toggle("open",panelOpen);document.getElementById("drawer").classList.toggle("hidden",!panelOpen);renderFilters(rows);renderKpis(rows);renderProgress(rows);renderHead();renderRows(rows);renderNotifications();if(panelOpen)renderPanel()}
render();
</script>
</body>
</html>
"""

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

component_payload = render_meeting_component(COMPONENT_DIR, key="seguimiento_reuniones_operativo")
if isinstance(component_payload, dict):
    nonce = _txt(component_payload.get("nonce")) or json.dumps(component_payload, sort_keys=True, ensure_ascii=True)
    if st.session_state.get("_seguimiento_last_save_nonce") != nonce:
        st.session_state["_seguimiento_last_save_nonce"] = nonce
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

