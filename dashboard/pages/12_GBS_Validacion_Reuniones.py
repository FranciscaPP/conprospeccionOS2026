"""Portal cliente GBS Logistics - validacion contractual de reuniones."""

import calendar
import html
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from portal_auth import img_b64, render_client_nav, require_auth_client
from shared.config import supabase_key, supabase_url
from shared.gbs_brand import GBS_BORDER_2, GBS_DARK, GBS_PURPLE, GBS_PURPLE_BG
from shared.metas import meta_de
from shared.seguimiento import (
    COLUMNAS_CLIENTE,
    bant_to_list,
    payload_respuesta_cliente,
    recalcular_final_y_flags,
    registrar_historial,
)
from shared.validacion import (
    ESTADOS_FLUJO,
    LABEL_ESTADO_FLUJO,
    MOTIVO_NO_VALIDEZ,
    acciones_cliente_permitidas,
    bant_desde_fuentes,
    construir_justificacion,
    derivar_estado_flujo,
    derivar_final,
    icp_gbs,
    informacion_reunion,
    texto_real,
    valor_custom_field,
)
from shared.validacion_ui import (
    BANT_LABEL,
    LABEL_FINAL,
    LABEL_MOTIVO,
    LABEL_STATUS,
    LABEL_VALIDEZ,
    banner_final,
    bant_chips,
    barra_avance,
    chip_status,
    chip_estado_flujo,
    chip_validez,
    tarjeta_estado_flujo,
)

st.set_page_config(
    page_title="GBS Logistics - Validacion Reuniones",
    layout="wide",
    page_icon="",
)

SUPABASE_URL = supabase_url()
SUPABASE_KEY = supabase_key()
_H = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
_HW = {**_H, "Content-Type": "application/json"}

MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
DIAS_ES = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]

FILTROS_KPI = {
    "all": "Total reuniones",
    "valid": "Válidas",
    "not_valid": "No válidas",
    "progress": "Avance meta",
}


def _clean(value, default=""):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    return texto_real(value) or default


def _safe_html(value):
    return html.escape(_clean(value))


def mes_rango(anio, mes):
    _, ultimo = calendar.monthrange(anio, mes)
    return f"{anio}-{mes:02d}-01", f"{anio}-{mes:02d}-{ultimo:02d}"


def fmt_fecha(value):
    if not value:
        return ""
    dt = pd.to_datetime(str(value), errors="coerce")
    if pd.isna(dt):
        return ""
    return f"{DIAS_ES[dt.weekday()]} {dt.day} de {MESES_ES[dt.month - 1]} {dt.year}"


def normalizar_status(value):
    status = _clean(value).lower()
    return {
        "completed": "realizada",
        "confirmed": "agendada",
        "scheduled": "agendada",
        "cancelled": "cancelada_cliente",
        "canceled": "cancelada_cliente",
        "no_show": "no_asistio_lead",
        "rescheduled": "reagendada",
        "solicita_cotizacion": "agendada",
    }.get(status, status if status in LABEL_STATUS else "sin_info")


def normalizar_cp(row, seg):
    cp = _clean(seg.get("val_estado_cp"))
    if cp:
        return cp
    estado = _clean(row.get("estado_validacion")).lower()
    if estado in {"valida", "reunion_valida"} or row.get("es_valida") is True:
        return "valida"
    if estado in {"no_valida", "reunion_no_valida"}:
        return "no_valida"
    return "espera"


def bant_cp(row, seg):
    return bant_desde_fuentes(row, seg)


def evidencia_disponible(row, seg):
    return any(
        _clean(value)
        for value in (
            seg.get("recording_url"),
            seg.get("transcript_url"),
            seg.get("ai_summary"),
            seg.get("ai_evidence"),
            row.get("recording_url"),
            row.get("transcript_url"),
            row.get("ai_summary"),
            row.get("ai_evidence"),
        )
    )


def valor_evidencia(row, seg, field):
    return _clean(seg.get(field)) or _clean(row.get(field))


@st.cache_data(ttl=60)
def cargar_reuniones(fecha_inicio, fecha_fin):
    base_fields = (
        "id,fecha_reunion,hora_reunion,empresa,contacto,cargo,email,telefono,"
        "industria,pais,estado_reunion,estado_validacion,es_valida,observacion,raw_data,"
        "motivo_no_valida,direccion_reunion,recording_url,transcript_url,"
        "ai_summary,ai_evidence,ai_bant_detected,ai_recommendation,ai_confidence"
    )
    fields = f"{base_fields},informacion_reunion,bant_sdr"
    url = (
        f"{SUPABASE_URL}/rest/v1/reuniones?select={fields}"
        f"&cliente_slug=eq.gbs"
        f"&fecha_reunion=gte.{fecha_inicio}&fecha_reunion=lte.{fecha_fin}"
        f"&order=fecha_reunion.desc,hora_reunion.desc"
    )
    response = requests.get(url, headers=_H, timeout=15)
    if not response.ok:
        fallback_url = url.replace(fields, base_fields)
        response = requests.get(fallback_url, headers=_H, timeout=15)
    rows = response.json() if response.ok else []
    df = pd.DataFrame(rows)
    if not df.empty:
        df["fecha"] = pd.to_datetime(df["fecha_reunion"], errors="coerce").dt.date
        df["hora"] = df["hora_reunion"].fillna("").astype(str).str[:5]
    return df


@st.cache_data(ttl=30)
def cargar_seguimiento():
    base_url = (
        f"{SUPABASE_URL}/rest/v1/seguimiento_reuniones"
        f"?select={COLUMNAS_CLIENTE}&cliente_slug=eq.gbs"
    )
    response = requests.get(
        base_url,
        headers=_H,
        timeout=15,
    )
    if not response.ok:
        legacy_columns = COLUMNAS_CLIENTE.replace(
            ",informacion_reunion_manual,icp_cumple",
            "",
        )
        response = requests.get(
            base_url.replace(COLUMNAS_CLIENTE, legacy_columns),
            headers=_H,
            timeout=15,
        )
    if not response.ok:
        return {}
    return {
        int(row["reunion_id"]): row
        for row in response.json()
        if row.get("reunion_id")
    }


@st.cache_data(ttl=30)
def cargar_historial(reunion_id):
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/meeting_status_history"
        f"?select=*&meeting_id=eq.{reunion_id}&order=changed_at.asc",
        headers=_H,
        timeout=15,
    )
    return response.json() if response.ok else []


@st.cache_data(ttl=300)
def buscar_contacto(term):
    clean_term = term.strip().replace("*", "")
    if not clean_term:
        return pd.DataFrame()
    fields = "contacto,empresa,email,telefono,cargo,industria,fecha_reunion,hora_reunion"
    url = (
        f"{SUPABASE_URL}/rest/v1/reuniones?select={fields}&cliente_slug=eq.gbs"
        f"&or=(email.ilike.*{clean_term}*,empresa.ilike.*{clean_term}*,"
        f"telefono.ilike.*{clean_term}*,contacto.ilike.*{clean_term}*)"
        f"&order=fecha_reunion.desc"
    )
    response = requests.get(url, headers=_H, timeout=15)
    return pd.DataFrame(response.json() if response.ok else [])


def enriquecer(df, seguimiento):
    rows = []
    for _, source in df.iterrows():
        row = source.to_dict()
        reunion_id = int(row.get("id") or 0)
        seg = seguimiento.get(reunion_id, {})
        status = _clean(seg.get("status_reunion")) or normalizar_status(row.get("estado_reunion"))
        cp = normalizar_cp(row, seg)
        bant = bant_cp(row, seg)
        client = _clean(seg.get("val_estado_cli")) or "espera"
        evidence = evidencia_disponible(row, seg)
        override = seg.get("val_estado_final") if seg.get("final_override") else None
        final = derivar_final(
            status,
            cp,
            client,
            bant,
            override=override,
            evidencia_suficiente=evidence,
            resultado_actual=seg.get("val_estado_final"),
        )
        row.update({
            "_seg": seg,
            "_status": status,
            "_cp": cp,
            "_bant": bant,
            "_client": client,
            "_evidence": evidence,
            "_final": final,
            "_flow": derivar_estado_flujo(
                row.get("fecha"),
                status,
                cp,
                client,
                final,
            ),
        })
        rows.append(row)
    return pd.DataFrame(rows)


def guardar_respuesta_cliente(reunion_id, estado, comentario="", motivo=None):
    previous = cargar_seguimiento().get(int(reunion_id), {})
    try:
        payload = payload_respuesta_cliente(
            int(reunion_id),
            "gbs",
            estado,
            comentario=comentario,
            motivo=motivo,
        )
    except ValueError:
        return False
    try:
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/seguimiento_reuniones",
            json=payload,
            headers={**_HW, "Prefer": "resolution=merge-duplicates,return=minimal"},
            timeout=15,
        )
    except requests.RequestException:
        return False
    if not response.ok:
        return False
    current = {**previous, **payload}
    recalculated = recalcular_final_y_flags(
        int(reunion_id),
        "gbs",
        fila=current,
    )
    client_history_ok = registrar_historial(
        int(reunion_id),
        "val_estado_cli",
        previous.get("val_estado_cli"),
        estado,
        "cliente",
        "cliente",
        "validacion_gbs",
    )
    final_history_ok = registrar_historial(
        int(reunion_id),
        "val_estado_final",
        previous.get("val_estado_final"),
        recalculated["final"],
        "sistema",
        "sistema",
        "validacion_gbs",
    )
    cargar_seguimiento.clear()
    cargar_historial.clear()
    return bool(recalculated["persisted"] and client_history_ok and final_history_ok)


def render_header():
    goal = meta_de("gbs") or {"validas": 0}
    target = int(goal.get("validas") or 0)
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:center;gap:20px;'
        f'background:linear-gradient(135deg,#faf5ff,#ede9fe);border:1px solid {GBS_BORDER_2};'
        f'border-radius:12px;padding:13px 22px;margin-bottom:14px">'
        f'<div><div style="font-size:20px;font-weight:800;color:{GBS_DARK};line-height:1.1">'
        f'Validación de reuniones</div>'
        f'<div style="font-size:12px;color:#64748b;margin-top:3px">'
        f'Revisa las reuniones generadas por Conprospección y confirma o solicita revisión '
        f'de su evaluación.</div></div>'
        f'<div style="display:flex;align-items:center;gap:14px">'
        f'<span style="font-size:12px;font-weight:800;color:{GBS_PURPLE}">'
        f'Meta · {target} reuniones válidas</span>'
        f'{img_b64("gbs_logo.png", 42)}{img_b64("conprospeccion_logo.png", 36)}</div></div>',
        unsafe_allow_html=True,
    )


def render_buscador():
    with st.expander("Verificar reuniones anteriores de un contacto", expanded=False):
        term = st.text_input(
            "Buscar contacto",
            placeholder="Correo, empresa, telefono o nombre del contacto",
            key="gbs_busqueda_historica",
        )
        if term and len(term.strip()) >= 3:
            results = buscar_contacto(term)
            if results.empty:
                st.info("No encontramos reuniones anteriores con ese contacto.")
            else:
                view = results.rename(columns={
                    "fecha_reunion": "Fecha",
                    "hora_reunion": "Hora",
                    "empresa": "Empresa",
                    "contacto": "Contacto",
                    "cargo": "Cargo",
                    "email": "Email",
                    "telefono": "Telefono",
                })
                columns = [c for c in ["Fecha", "Hora", "Empresa", "Contacto", "Cargo", "Email", "Telefono"] if c in view]
                st.dataframe(view[columns], use_container_width=True, hide_index=True)


def set_kpi_filter(value):
    st.session_state["gbs_kpi_filter"] = value


def render_kpis(base_df):
    goal = meta_de("gbs") or {"validas": 0}
    target = int(goal.get("validas") or 0)
    validas = int((base_df["_final"] == "valida").sum())
    counts = {
        "all": len(base_df),
        "valid": validas,
        "not_valid": int((base_df["_final"] == "no_valida").sum()),
        "progress": round(validas / target * 100) if target else 0,
    }
    active = st.session_state.get("gbs_kpi_filter")
    palette = {
        "all": ("#eff6ff", "#bfdbfe", "#1d4ed8"),
        "valid": ("#f0fdf4", "#86efac", "#166534"),
        "not_valid": ("#fef2f2", "#fecaca", "#991b1b"),
        "progress": ("#fffbeb", "#fde68a", "#92400e"),
    }
    styles = []
    for key, (background, border, color) in palette.items():
        active_style = f"box-shadow:0 0 0 2px {color}55!important;" if active == key else ""
        styles.append(
            f'div[class*="st-key-gbs_kpi_{key}"] button{{'
            f'background:{background}!important;border:1px solid {border}!important;'
            f'color:{color}!important;min-height:82px!important;text-align:left!important;'
            f'font-weight:800!important;white-space:pre-line!important;{active_style}}}'
            f'div[class*="st-key-gbs_kpi_{key}"] button p{{'
            f'color:{color}!important;font-size:14px!important;line-height:1.45!important}}'
        )
    st.markdown(f"<style>{''.join(styles)}</style>", unsafe_allow_html=True)

    columns = st.columns(4, gap="small")
    for column, (key, label) in zip(columns, FILTROS_KPI.items()):
        with column:
            value = f"{counts[key]}%"
            if key == "progress":
                value += f"\n{validas}/{target}"
                st.button(
                    f"{label}\n{value}",
                    key=f"gbs_kpi_{key}",
                    use_container_width=True,
                    disabled=True,
                )
            else:
                st.button(
                    f"{label}\n{counts[key]}",
                    key=f"gbs_kpi_{key}",
                    use_container_width=True,
                    type="primary" if active == key else "secondary",
                    on_click=set_kpi_filter,
                    args=(None if active == key else key,),
                )
    return counts


def aplicar_kpi(df):
    active = st.session_state.get("gbs_kpi_filter", "all")
    if active == "valid":
        return df[df["_final"] == "valida"].copy()
    if active == "not_valid":
        return df[df["_final"] == "no_valida"].copy()
    return df.copy()


def tabla_reuniones(df):
    table = pd.DataFrame({
        "ID": df["id"].astype(int),
        "Fecha": pd.to_datetime(df["fecha"], errors="coerce"),
        "Hora": df["hora"],
        "Empresa": df["empresa"].fillna(""),
        "Contacto": df["contacto"].fillna(""),
        "Cargo": df["cargo"].fillna(""),
        "Estado": df["_flow"].map(lambda value: LABEL_ESTADO_FLUJO.get(value, value)),
    })
    st.caption(
        "Selecciona una fila para ver el detalle. Haz clic en Fecha para ordenar "
        "ascendente o descendente."
    )
    event = st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        height=min(560, 74 + max(len(table), 1) * 35),
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "ID": None,
            "Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
        },
    )
    selected_rows = event.selection.rows if event and event.selection else []
    if not selected_rows:
        return None
    selected_index = selected_rows[0]
    if selected_index < 0 or selected_index >= len(df):
        return None
    return df.iloc[selected_index]


def render_evidencia(row, seg):
    recording = valor_evidencia(row, seg, "recording_url")
    transcript = valor_evidencia(row, seg, "transcript_url")
    ai_summary = valor_evidencia(row, seg, "ai_summary")
    ai_evidence = valor_evidencia(row, seg, "ai_evidence")
    available = [bool(recording), bool(transcript), bool(ai_summary)]
    cols = st.columns(sum(available)) if any(available) else []
    index = 0
    if recording:
        with cols[index]:
            st.link_button("Ver grabacion", recording, use_container_width=True)
        index += 1
    if transcript:
        with cols[index]:
            st.link_button("Ver transcripcion", transcript, use_container_width=True)
        index += 1
    if ai_summary:
        with st.expander("Resumen IA"):
            st.write(ai_summary)
    if ai_evidence:
        with st.expander("Evidencia IA"):
            st.write(ai_evidence)


def render_historial(reunion_id, row):
    history = cargar_historial(int(reunion_id))
    items = [(
        f"{_clean(row.get('fecha_reunion'))} {_clean(row.get('hora_reunion'))}".strip(),
        "Reunión agendada",
        "",
    )]
    event_labels = {
        "status_reunion": "Estado de la reunión",
        "val_estado_cp": "Evaluación Conprospección",
        "val_estado_cli": "Respuesta del cliente",
        "val_estado_final": "Resolución Conprospección",
        "bant_cp": "BANT actualizado por Conprospección",
        "informacion_reunion_manual": "Información para reunión actualizada",
        "icp_cumple": "Antecedente ICP actualizado",
    }
    for event in history:
        field = _clean(event.get("field_changed"), "Actualización")
        new_value = _clean(event.get("new_value"))
        if field == "val_estado_cli":
            detail = {
                "valida": "Cliente confirmó la reunión",
                "requiere_revision": "Cliente solicitó revisión",
                "no_valida": "Cliente solicitó revisión",
            }.get(new_value, new_value)
        elif field == "val_estado_cp":
            detail = LABEL_VALIDEZ.get(new_value, new_value)
        elif field == "val_estado_final":
            detail = LABEL_FINAL.get(new_value, new_value)
        elif field == "status_reunion":
            detail = LABEL_STATUS.get(new_value, new_value)
            if new_value == "realizada":
                detail = "Reunión realizada"
        else:
            detail = new_value
        items.append((
            _clean(event.get("changed_at")),
            event_labels.get(field, field),
            detail,
        ))
    items.append(("", "Estado actual", LABEL_ESTADO_FLUJO.get(row.get("_flow"), row.get("_flow"))))

    timeline = []
    for when, event, detail in items:
        timeline.append(
            f'<div style="display:grid;grid-template-columns:12px 145px 1fr;gap:10px;'
            f'padding:7px 0;align-items:start">'
            f'<span style="width:9px;height:9px;border-radius:50%;background:{GBS_PURPLE};'
            f'margin-top:5px"></span>'
            f'<span style="font-size:11px;color:#94a3b8;font-weight:700">{_safe_html(when)}</span>'
            f'<span><b style="font-size:13px;color:#334155">{_safe_html(event)}</b>'
            f'<br><span style="font-size:12px;color:#64748b">{_safe_html(detail)}</span></span>'
            f'</div>'
        )
    st.markdown("".join(timeline), unsafe_allow_html=True)


def _section_header(number, title):
    return (
        f'<div style="font-size:12px;font-weight:800;color:{GBS_PURPLE};'
        f'margin:17px 0 8px;padding-bottom:6px;border-bottom:1px solid #e9d5ff">'
        f'{number}. {title}</div>'
    )


def _detail_line(label, value, link=False):
    clean = _clean(value)
    if not clean:
        return ""
    rendered = (
        f'<a href="{html.escape(clean)}" target="_blank" '
        f'style="color:{GBS_PURPLE};font-weight:600;text-decoration:none">{html.escape(clean)}</a>'
        if link else f'<span style="font-weight:600;color:#0f172a">{html.escape(clean)}</span>'
    )
    return (
        f'<div style="display:grid;grid-template-columns:125px 1fr;gap:8px;'
        f'padding:3px 0;font-size:12px">'
        f'<span style="color:#64748b">{label}</span>{rendered}</div>'
    )


def _bant_evaluation(bant):
    if not bant:
        return ""
    labels = [("N", "Need"), ("A", "Authority"), ("B", "Budget"), ("T", "Timing")]
    rows = []
    for code, label in labels:
        detected = code in bant
        if detected:
            rows.append(
            f'<div style="display:flex;justify-content:space-between;padding:3px 0;'
            f'font-size:12px;color:#334155"><span>{label}</span>'
            f'<b style="color:#16a34a">Detectada</b></div>'
        )
    return (
        f'<div style="border:1px solid #e2e8f0;border-radius:8px;padding:11px 13px">'
        f'<div style="font-size:11px;font-weight:800;color:{GBS_PURPLE};margin-bottom:4px">'
        f'BANT · {len(bant)} de 4 variables</div>{"".join(rows)}</div>'
    )


def render_detalle(row):
    seg = row["_seg"]
    reunion_id = int(row["id"])
    cp = row["_cp"]
    bant = row["_bant"]
    client = row["_client"]
    final = row["_final"]
    status = row["_status"]
    flow = row["_flow"]
    future = flow == "reunion_futura"
    evidence = bool(row["_evidence"])
    info_reunion = informacion_reunion(row, seg)
    icp = icp_gbs(status, seg.get("icp_cumple"))
    locked = client in {"valida", "requiere_revision", "no_valida", "reagendada"}
    client_actions = acciones_cliente_permitidas(flow, cp, client)
    contractually_valid = "confirmar" in client_actions

    meeting_link = _clean(row.get("direccion_reunion"))
    justification = construir_justificacion(
        cp,
        icp=icp,
        bant=bant,
        evidencia=evidence,
        tiene_informacion=bool(info_reunion),
        comentario=_clean(seg.get("comentario_cp"))
        or _clean(row.get("motivo_no_valida")),
    )
    website = valor_custom_field(row.get("raw_data"), ("website", "sitio web"))
    company_linkedin = valor_custom_field(row.get("raw_data"), ("linkedin_empresa", "linkedin empresa"))
    contact_linkedin = valor_custom_field(row.get("raw_data"), ("linkedin_personal", "linkedin personal"))

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;font-size:12px;'
        f'font-weight:700;color:#334155"><span style="width:9px;height:9px;'
        f'border-radius:50%;background:#16a34a"></span>'
        f'{chip_estado_flujo(flow)} · '
        f'{_safe_html(fmt_fecha(row.get("fecha")))} · {_safe_html(row.get("hora"))}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(tarjeta_estado_flujo(flow), unsafe_allow_html=True)

    st.markdown(_section_header(1, "Contacto y empresa"), unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        st.markdown(
            _detail_line("Empresa", row.get("empresa"))
            + _detail_line("Contacto", row.get("contacto"))
            + _detail_line("Cargo", row.get("cargo"))
            + _detail_line("Email", row.get("email"))
            + _detail_line("Teléfono", row.get("telefono")),
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            _detail_line("País", row.get("pais"))
            + _detail_line("Website", website, link=True)
            + _detail_line("LinkedIn empresa", company_linkedin, link=True)
            + _detail_line("LinkedIn contacto", contact_linkedin, link=True)
            + _detail_line("Fecha reunión", fmt_fecha(row.get("fecha")))
            + _detail_line("Hora reunión", row.get("hora"))
            + _detail_line("Link reunión", meeting_link, link=True),
            unsafe_allow_html=True,
        )

    if info_reunion:
        st.markdown(_section_header(2, "Información para reunión"), unsafe_allow_html=True)
        st.markdown(
            f'<div style="font-size:13px;color:#334155;line-height:1.5">'
            f'{_safe_html(info_reunion)}</div>',
            unsafe_allow_html=True,
        )

    st.markdown(_section_header(3, "Evaluación Conprospección"), unsafe_allow_html=True)
    eval_left, eval_right = st.columns([1, 1.35])
    with eval_left:
        icp_label = (
            ("Cumple", "#166534", "#f0fdf4", "#86efac")
            if icp
            else ("No cumple", "#991b1b", "#fef2f2", "#fecaca")
        )
        st.markdown(
            f'<div style="border:1px solid {icp_label[3]};background:{icp_label[2]};'
            f'border-radius:8px;padding:11px 13px">'
            f'<div style="font-size:11px;font-weight:800;color:{GBS_PURPLE};margin-bottom:6px">ICP</div>'
            f'<div style="font-size:14px;font-weight:800;color:{icp_label[1]}">{icp_label[0]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with eval_right:
        if bant:
            st.markdown(_bant_evaluation(bant), unsafe_allow_html=True)

    if justification and not future:
        st.markdown(_section_header(4, "Justificación Conprospección"), unsafe_allow_html=True)
        st.markdown(
            f'<div style="font-size:13px;color:#334155;line-height:1.55">'
            f'{_safe_html(justification)}</div>',
            unsafe_allow_html=True,
        )

    if evidence:
        st.markdown(_section_header(5, "Evidencia"), unsafe_allow_html=True)
        render_evidencia(row, seg)

    if not future:
        st.markdown(_section_header(6, "Acción cliente"), unsafe_allow_html=True)
    if future:
        st.info("Reunión futura. Aún no admite confirmación ni solicitud de revisión.")
    elif locked:
        st.info("La respuesta del cliente ya fue registrada. La reunión queda bloqueada.")
    elif cp == "espera":
        st.info("Conprospección aún no emite su evaluación. No hay acciones disponibles.")
    elif cp == "no_valida":
        st.info("Conprospección marcó la reunión como no válida. No requiere confirmación.")
    elif not client_actions:
        st.info("Esta reunión no tiene acciones disponibles para el cliente.")
    else:
        confirm_col, review_col = st.columns(2)
        with confirm_col:
            if st.button(
                "Confirmar reunión",
                key=f"confirm_{reunion_id}",
                type="primary",
                use_container_width=True,
                disabled=not contractually_valid,
            ):
                if guardar_respuesta_cliente(
                    reunion_id,
                    "valida",
                ):
                    st.success("Reunión confirmada.")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("No fue posible completar el guardado de la confirmación.")
        with review_col:
            st.caption("Solicita revisión para que Conprospección vuelva a evaluar.")

        if not contractually_valid:
            st.warning("Solo se puede confirmar una evaluación positiva previa de Conprospección.")

        with st.form(f"review_form_{reunion_id}"):
            reason = st.selectbox(
                "Motivo de revisión",
                MOTIVO_NO_VALIDEZ,
                format_func=lambda value: LABEL_MOTIVO.get(value, value),
                index=None,
                placeholder="Selecciona un motivo",
            )
            comment = st.text_area(
                "Comentario obligatorio",
                placeholder="Explica el motivo contractual de la solicitud.",
            )
            request_review = st.form_submit_button(
                "Solicitar revisión",
                use_container_width=True,
            )
            if request_review:
                if not reason:
                    st.error("El motivo es obligatorio.")
                elif not comment.strip():
                    st.error("El comentario es obligatorio.")
                elif guardar_respuesta_cliente(
                    reunion_id,
                    "requiere_revision",
                    comentario=comment,
                    motivo=reason,
                ):
                    st.success("Solicitud de revisión registrada y pendiente de resolución.")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("No fue posible guardar la solicitud.")

    st.markdown(_section_header(7, "Historial"), unsafe_allow_html=True)
    render_historial(reunion_id, row)


@st.dialog("Detalle de reunión", width="large")
def abrir_detalle(row):
    render_detalle(row)


def run():
    if not require_auth_client("gbs"):
        return

    render_client_nav("12_GBS_Validacion", "gbs")
    st.markdown(
        f"""
        <style>
        button[kind="primary"] {{
            background:{GBS_PURPLE}!important;
            border-color:{GBS_PURPLE}!important;
            color:#fff!important;
            font-weight:700!important;
        }}
        div[data-testid="stButton"] button {{
            white-space:pre-line;
            font-weight:700;
        }}
        div[data-testid="stDataFrame"] {{
            border:1px solid #e2e8f0;
            border-radius:10px;
            overflow:hidden;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    render_header()

    today = date.today()
    month_start = date(today.year, today.month, 1)
    month_end = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    selected_range = st.session_state.get("gbs_date_range", (month_start, month_end))
    if isinstance(selected_range, (tuple, list)) and len(selected_range) == 2:
        fecha_inicio, fecha_fin = str(selected_range[0]), str(selected_range[1])
    elif isinstance(selected_range, (tuple, list)) and len(selected_range) == 1:
        fecha_inicio = fecha_fin = str(selected_range[0])
    else:
        fecha_inicio, fecha_fin = str(month_start), str(month_end)
    query = st.session_state.get("gbs_search", "")
    selected_status = st.session_state.get("gbs_flow_status", "all")
    if selected_status not in {"all", *ESTADOS_FLUJO}:
        selected_status = "all"
        st.session_state["gbs_flow_status"] = "all"

    meetings = cargar_reuniones(fecha_inicio, fecha_fin)
    tracking = cargar_seguimiento()
    enriched = enriquecer(meetings, tracking) if not meetings.empty else meetings
    if not enriched.empty and query.strip():
        needle = query.strip().lower()
        enriched = enriched[
            enriched.apply(
                lambda row: needle in " ".join(
                    _clean(row.get(field)).lower()
                    for field in ("empresa", "contacto", "cargo", "email", "telefono", "pais")
                ),
                axis=1,
            )
        ].copy()
    if not enriched.empty and selected_status != "all":
        enriched = enriched[enriched["_flow"] == selected_status].copy()

    counts = render_kpis(enriched) if "_final" in enriched.columns else {
        "all": 0,
        "valid": 0,
        "not_valid": 0,
        "progress": 0,
    }
    goal = meta_de("gbs") or {"validas": 0}
    st.markdown(
        barra_avance(counts["valid"], goal["validas"], color=GBS_PURPLE),
        unsafe_allow_html=True,
    )

    filter_cols = st.columns([4, 3, 3, 1.2])
    with filter_cols[0]:
        st.text_input(
            "Buscar",
            placeholder="Buscar empresa, contacto o cargo",
            label_visibility="collapsed",
            key="gbs_search",
        )
    with filter_cols[1]:
        st.date_input(
            "Fecha",
            value=(month_start, month_end),
            format="DD/MM/YYYY",
            label_visibility="collapsed",
            key="gbs_date_range",
        )
    with filter_cols[2]:
        st.selectbox(
            "Estado",
            ["all", *ESTADOS_FLUJO],
            format_func=lambda value: "Todos los estados" if value == "all" else LABEL_ESTADO_FLUJO[value],
            label_visibility="collapsed",
            key="gbs_flow_status",
        )
    with filter_cols[3]:
        if st.button("Actualizar", use_container_width=True, key="gbs_refresh"):
            st.cache_data.clear()
            st.session_state["gbs_kpi_filter"] = None
            st.rerun()

    render_buscador()

    filtered = aplicar_kpi(enriched) if not enriched.empty else enriched
    if filtered.empty:
        st.info("No hay reuniones para el periodo y filtros seleccionados.")
        return

    st.markdown(
        f'<div style="background:linear-gradient(135deg,#4c1d95,#7c3aed);color:white;'
        f'padding:11px 20px;border-radius:10px;margin:10px 0 8px;font-weight:700;'
        f'font-size:15px">{_safe_html(fecha_inicio)} a {_safe_html(fecha_fin)} · '
        f'{len(filtered)} reuniones</div>',
        unsafe_allow_html=True,
    )
    selected = tabla_reuniones(filtered)
    if selected is not None:
        abrir_detalle(selected)


run()
