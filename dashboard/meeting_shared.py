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
from shared.validacion import bant_desde_fuentes, informacion_reunion, texto_real, valor_custom_field

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
    if value in {"no_necesaria", "no necesaria", "cancelacion"}:
        return "No necesaria"
    if value in {"valida", "reunion_valida"}:
        return "Válida"
    if value in {"no_valida", "reunion_no_valida"}:
        return "No válida"
    return "Pendiente"


def _client_val_label(seg):
    value = _txt(seg.get("val_estado_cli")).lower()
    if value in {"no_necesaria", "no necesaria", "cancelacion"}:
        return "No necesaria"
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


def _normalize_cancelled_meeting(status: str, cp: str, client_val: str, final: str) -> tuple[str, str, str]:
    """Cancelada = cancelada. CP y cliente quedan como no necesarios."""
    if status != "Reunión cancelada":
        return cp, client_val, final
    return "No necesaria", "No necesaria", "Reunión cancelada"


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


def _norm_type_key(value) -> str:
    import unicodedata

    text = unicodedata.normalize("NFD", _txt(value))
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn").lower()


def _visibility_lookup(visibility: dict, evidence_type: str, default: bool = False) -> bool:
    if not visibility:
        return default
    if evidence_type in visibility:
        return bool(visibility[evidence_type])
    target = _norm_type_key(evidence_type)
    for key, val in visibility.items():
        if _norm_type_key(key) == target:
            return bool(val)
    return default


def _type_visible(visible_types: set[str], *candidates: str) -> bool:
    normalized = {_norm_type_key(t) for t in visible_types}
    return any(_norm_type_key(candidate) in normalized for candidate in candidates)


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
        item["clientVisible"] = _visibility_lookup(visibility, item.get("type"))
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


def _manual_history_payload(history):
    manual = []
    for item in history or []:
        if item.get("manual"):
            manual.append(item)
    return manual


def _contact_enrichment(contact):
    raw = contact.get("raw_data") or {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            raw = {}
    fields = contact.get("custom_fields") or raw.get("customFields") or []
    source = {"customFields": fields, **raw, "raw_data": raw}
    website = _txt(raw.get("website")) or texto_real(
        valor_custom_field(source, ("website", "sitio web", "sitio_web"))
    )
    linkedin = _custom_field(fields, "iimkT4RjJWRONU2HcwbN") or texto_real(
        valor_custom_field(source, ("linkedin_personal", "linkedin personal", "linkedin"))
    )
    linkedin_company = _custom_field(fields, "SnRP2tiJlYfQOHBM3adE") or texto_real(
        valor_custom_field(source, ("linkedin_empresa", "linkedin empresa", "linkedin company"))
    )
    return {
        "website": website,
        "linkedin": linkedin,
        "linkedinCompany": linkedin_company,
        "companySize": _custom_field(fields, "3uQfRamZN2ruaNg367XL", "SZKSPwPVwnjbHZpCzdg8"),
        "sourceChannel": _custom_field(fields, "mipcTmLgax5URM1q3Mut") or _txt(contact.get("fuente")) or _txt(raw.get("source")),
        "companyInfo": _custom_field(fields, "x8bV5PXJ0MgJcmdMk9Bd", "uWCMW4RCrWDGlu02nMkp", "QfY4XP9fPVWKAidootqt"),
        "contactInfo": _custom_field(fields, "iZwhsMPoJZ5IgdcA3kYk", "Q6PFJIn4ETLXlgsKRwvx"),
        "contactInfoMeeting": _txt(contact.get("informacion_reunion")) or texto_real(
            valor_custom_field(source, ("informacion para reunion", "preparacion_para_la_reunion"))
        ),
        "bantSdr": contact.get("bant_sdr"),
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



@st.cache_data(ttl=0)
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
        "?select=id,ghl_contact_id,fecha_agendada,direccion_reunion,recording_url,transcript_url,"
        "ai_summary,ai_evidence,ai_bant_detected,sdr_slug,informacion_reunion,bant_sdr,"
        "observacion,notas,raw_data,pais,industria,cargo,email,telefono,empresa,contacto",
        headers=SUPABASE_HEADERS,
        timeout=15,
    )
    contacts_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/contactos?select=ghl_contact_id,sdr_slug,fuente,raw_data,custom_fields,"
        "informacion_reunion,bant_sdr,pais,industria,cargo,email,telefono,nombre_contacto,nombre_empresa"
        f"&cliente_slug=in.({slugs})",
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
        if row.get("excluida") is True:
            continue
        rid = row.get("id")
        if not rid:
            continue
        seg = tracking.get(int(rid), {})
        base_row = base_meetings.get(int(rid), {})
        base_raw = _json_obj(base_row.get("raw_data"), {})
        base_contact = _json_obj(base_raw.get("contact"), {}) if isinstance(base_raw, dict) else {}
        base_contact_fields = base_raw.get("contact_custom_fields", []) if isinstance(base_raw, dict) else []
        extra = contact_extra.get(row.get("ghl_contact_id")) or _contact_enrichment(
            {
                "raw_data": base_contact,
                "custom_fields": base_contact_fields or base_contact.get("customFields") or [],
                "informacion_reunion": base_row.get("informacion_reunion"),
                "bant_sdr": base_row.get("bant_sdr"),
                "fuente": base_contact.get("source"),
            }
        )
        merged_raw = {
            "raw_data": base_raw or row.get("raw_data") or {},
            "contact_custom_fields": base_raw.get("contact_custom_fields", []),
        }
        merged_row = {**base_row, **row, **merged_raw}
        slug = _txt(row.get("cliente_slug")).lower()
        status = _status_label(row, seg)
        cp = _cp_label(row, seg)
        client_val = _client_val_label(seg)
        manual_history = _json_obj(seg.get("historial_manual"), [])
        audit_history = histories.get(int(rid), [])
        row_history = manual_history + audit_history
        manual_evidence = _json_obj(seg.get("evidencia_manual"), [])
        evidence = _evidence({**row, **base_row}, seg) + manual_evidence
        evidence = _apply_evidence_visibility(evidence, seg.get("evidencia_visibilidad"), row_history)
        agenda_meta = _json_obj(seg.get("etapa_agenda_metadata"), {})
        final = _final_label(seg)
        cp, client_val, final = _normalize_cancelled_meeting(status, cp, client_val, final)
        assigned_sdr = (
            _txt(seg.get("sdr_override"))
            or _sdr_display(contact_sdr.get(row.get("ghl_contact_id")), sdr_names)
            or _sdr_display(base_row.get("sdr_slug"), sdr_names)
            or _txt(row.get("sdr"), "Sin asignar")
        )
        meta = meta_de(slug)
        recording_url = _txt(base_row.get("recording_url")) or _txt(seg.get("recording_url"))
        transcript_url = _txt(base_row.get("transcript_url")) or _txt(seg.get("transcript_url"))
        date_label = _date_es(row.get("fecha"))
        time_label = _time_12(row.get("hora"))
        rows.append(
            {
                "id": int(rid),
                "clientSlug": slug,
                "date": date_label,
                "time": time_label,
                "sortKey": _dt_sort_key({"date": date_label, "time": time_label}),
                "scheduledDate": _date_es(base_row.get("fecha_agendada")),
                "client": _client_label(slug, row.get("cliente")),
                "company": _txt(row.get("empresa") or base_row.get("empresa"), "-").title(),
                "contact": _txt(row.get("contacto") or base_row.get("contacto"), "-").title(),
                "role": _txt(row.get("cargo") or base_row.get("cargo"), "-").title(),
                "sdr": assigned_sdr,
                "status": status,
                "cp": cp,
                "clientVal": client_val,
                "final": final,
                "caseStatus": _txt(seg.get("estado_caso")) or _case_status(cp, client_val, final),
                "email": _txt(row.get("email") or base_row.get("email")),
                "phone": _txt(row.get("telefono") or base_row.get("telefono")),
                "country": _country_label(row.get("pais") or base_row.get("pais")),
                "industry": _txt(row.get("industria") or base_row.get("industria")),
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
                "recordingUrl": recording_url,
                "transcriptUrl": transcript_url,
                "info": informacion_reunion(merged_row, seg) or extra.get("contactInfoMeeting", ""),
                "operationalNotes": _txt(base_row.get("observacion")) or _txt(base_row.get("notas")),
                "icp": "Cumple" if seg.get("icp_cumple") is True else "No cumple" if seg.get("icp_cumple") is False else "No evaluado",
                "bant": _bant(",".join(bant_desde_fuentes({**merged_row, "bant_sdr": base_row.get("bant_sdr") or row.get("bant_sdr") or extra.get("bantSdr")}, seg))),
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
                "historyVisibility": _json_obj(seg.get("historial_visibilidad"), {}),
                "historialManual": manual_history,
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


def _resolve_history_visibility(meeting: dict) -> dict:
    """Combina historial_visibilidad persistido con toggles guardados en auditoría."""
    visibility = _json_obj(meeting.get("historyVisibility"), {}).copy()
    for event in reversed(meeting.get("history") or []):
        if _txt(event.get("field")) != "Visibilidad historial":
            continue
        text = _txt(event.get("to")) or _txt(event.get("description")) or ""
        if ":" not in text:
            continue
        key, state = [part.strip() for part in text.split(":", 1)]
        if key:
            visibility[key] = _visibility_from_state(state)
    return visibility


def _history_visible(meeting: dict, key: str, default: bool = False) -> bool:
    visibility = _resolve_history_visibility(meeting)
    if key in visibility:
        return bool(visibility[key])
    return default


def _latest_history_when(history: list[dict], field: str) -> str:
    for event in history or []:
        if _txt(event.get("field")) == field:
            return _txt(event.get("when"))
    return ""


def _friendly_history_actor(user: str) -> str:
    raw = _txt(user).lower()
    if "cliente" in raw:
        return "Cliente"
    if "ghl" in raw or "sistema" in raw:
        return "Sistema"
    return "Conprospección"


def _build_client_history(meeting: dict) -> list[dict]:
    """Historial visible para el cliente; no expone auditoría interna."""
    items: list[dict] = []
    history = meeting.get("history") or []
    meeting_for_visibility = {**meeting, "historyVisibility": _resolve_history_visibility(meeting)}

    def add(when: str, user: str, field: str, text: str) -> None:
        clean = _txt(text)
        if not clean:
            return
        items.append(
            {
                "when": when or "Sin fecha",
                "user": user,
                "field": field,
                "text": clean,
            }
        )

    if _history_visible(meeting_for_visibility, "fecha_agenda", False):
        when = _txt(meeting.get("scheduledDate")) or _txt(meeting.get("date")) or "Sin fecha"
        add(when, "Sistema", "Fecha de agenda", when)

    if meeting.get("status") == "Reunión realizada" and _history_visible(meeting_for_visibility, "fecha_realizada", False):
        when = _latest_history_when(history, "Etapa Agenda") or f"{_txt(meeting.get('date'))} {_txt(meeting.get('time'))}".strip()
        add(when, "Sistema", "Reunión realizada", when)

    cp = _txt(meeting.get("cp"))
    if (
        cp
        and cp not in {"Pendiente", "", "No necesaria"}
        and meeting.get("status") != "Reunión cancelada"
        and _history_visible(meeting_for_visibility, "fecha_cp", True)
    ):
        when = _latest_history_when(history, "Evaluación CP") or "Sin fecha"
        add(when, "Conprospección", "Evaluación Conprospección", cp)

    client_val = _txt(meeting.get("clientVal"))
    if client_val and client_val not in {"Pendiente", ""} and _history_visible(
        meeting_for_visibility,
        "fecha_cliente",
        client_val != "No necesaria",
    ):
        actor = "Sistema" if client_val == "No necesaria" else "Cliente"
        when = _latest_history_when(history, "Evaluación Cliente") or _txt(meeting.get("clientDate")) or "Sin fecha"
        add(when, actor, "Evaluación del cliente", client_val)

    final = _txt(meeting.get("final"))
    if final and final not in {"Pendiente", ""} and _history_visible(meeting_for_visibility, "fecha_final", True):
        when = _latest_history_when(history, "Estado Final") or "Sin fecha"
        label = "Pendiente de cierre" if final == "Pendiente" else final
        add(when, "Conprospección", "Estado final", label)

    for note in _json_obj(meeting.get("historialManual"), []):
        if note.get("visibility") != "Visible para el cliente":
            continue
        add(
            _txt(note.get("when")),
            _friendly_history_actor(note.get("user")),
            _txt(note.get("field")) or "Actualización",
            _txt(note.get("description")) or _txt(note.get("text")),
        )

    return items


def project_meeting_for_client(meeting: dict) -> dict:
    """Proyección cliente: oculta campos internos y evidencia no visible."""
    out = dict(meeting)
    status = _txt(out.get("status"))
    cp, client_val, final = _normalize_cancelled_meeting(
        status,
        _txt(out.get("cp")),
        _txt(out.get("clientVal")),
        _txt(out.get("final")),
    )
    out["cp"] = cp
    out["clientVal"] = client_val
    out["final"] = final
    visible_types = {
        str(e.get("type"))
        for e in (meeting.get("evidence") or [])
        if e.get("clientVisible") and e.get("type")
    }
    out["evidence"] = [
        e for e in (meeting.get("evidence") or [])
        if e.get("clientVisible") and (e.get("url") or e.get("text") or e.get("name"))
    ]
    if not _type_visible(visible_types, "Grabación"):
        out.pop("recordingUrl", None)
    if not _type_visible(visible_types, "Transcripción"):
        out.pop("transcriptUrl", None)
    out["history"] = _build_client_history(meeting)
    for key in (
        "sdr",
        "notes",
        "finalReason",
        "finalInternalNote",
        "next",
        "caseStatus",
        "historyVisibility",
        "historialManual",
        "ghlContact",
        "ghlOpp",
    ):
        out.pop(key, None)
    return out
