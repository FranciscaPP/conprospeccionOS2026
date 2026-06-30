"""Carga y normalización de reuniones para panel interno y portales cliente."""
from __future__ import annotations

import base64
import datetime
import json
from pathlib import Path

import streamlit as st

try:
    from zoneinfo import ZoneInfo
    _CHILE_TZ = ZoneInfo("America/Santiago")
except Exception:
    _CHILE_TZ = None

import requests

from shared.config import supabase_key, supabase_url
from shared.meeting_scope import ACTIVE_MEETING_CLIENT_SLUGS
from shared.metas import meta_de

SUPABASE_URL = supabase_url()
SUPABASE_KEY = supabase_key()
SUPABASE_HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}

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
    now_local = _now_chile()
    today = now_local.date()
    if d > today:
        return "Reunión futura"
    if d == today:
        raw_time = _txt(row.get("hora"))
        if not raw_time:
            return "Reunión futura"
        try:
            parts = raw_time.split(":")
            meeting_time = datetime.time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
            if meeting_time > now_local.time():
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
        "?select=id,ghl_contact_id,fecha_agendada,direccion_reunion,recording_url,transcript_url,ai_summary,ai_evidence,sdr_slug",
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
                "meet": _txt(base_row.get("direccion_reunion")),
                "recordingUrl": _txt(base_row.get("recording_url")),
                "transcriptUrl": _txt(base_row.get("transcript_url")),
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


def load_meetings(client_slugs: list[str] | None = None):
    slugs = client_slugs or list(ACTIVE_MEETING_CLIENT_SLUGS)
    all_rows = cargar_reuniones_reales_poc()
    allowed = {s.lower() for s in slugs}
    return [row for row in all_rows if _txt(row.get("clientSlug")).lower() in allowed]


def project_meeting_for_client(meeting: dict) -> dict:
    """Proyección cliente: oculta campos internos y evidencia no visible."""
    out = dict(meeting)
    visible_types = {
        str(e.get("type"))
        for e in (meeting.get("evidence") or [])
        if e.get("clientVisible") and e.get("type")
    }
    out["evidence"] = [
        e for e in (meeting.get("evidence") or [])
        if e.get("clientVisible") and (e.get("url") or e.get("text") or e.get("name"))
    ]
    if "Grabación" not in visible_types:
        out.pop("recordingUrl", None)
    if "Transcripción" not in visible_types:
        out.pop("transcriptUrl", None)
    out.pop("sdr", None)
    out.pop("notes", None)
    out.pop("finalReason", None)
    out.pop("finalInternalNote", None)
    out.pop("next", None)
    out.pop("caseStatus", None)
    return out
