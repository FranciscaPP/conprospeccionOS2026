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
from shared.icp_summary import perfil_icp
from shared.metas import meta_de
from shared.seguimiento import (
    COLUMNAS_CLIENTE,
    bant_to_list,
    payload_respuesta_cliente,
    recalcular_final_y_flags,
    registrar_historial,
)
from shared.validacion import (
    ESTATUS_VALIDACION,
    ESTADOS_FLUJO,
    LABEL_ESTATUS_VALIDACION,
    LABEL_ESTADO_FLUJO,
    LABEL_ETAPA_AGENDA,
    MOTIVO_NO_VALIDEZ,
    acciones_cliente_permitidas,
    bant_desde_fuentes,
    derivar_estatus_validacion,
    derivar_estado_flujo,
    derivar_etapa_agenda,
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
    "pending_client": "Pendiente cliente",
    "review": "En revisión",
    "reschedule": "Reagenda",
}

AGENDA_STYLE = {
    "reunion_futura": ("#e0f2fe", "#075985"),
    "reunion_agendada": ("#eef2ff", "#4338ca"),
    "reunion_realizada": ("#ccfbf1", "#0f766e"),
    "cotizacion": ("#f3e8ff", "#7e22ce"),
    "reagendar": ("#ffedd5", "#9a3412"),
    "reunion_cancelada": ("#f1f5f9", "#475569"),
}

VISIBLE_ETAPAS_AGENDA = [
    "reunion_futura",
    "reunion_realizada",
    "cotizacion",
    "reagendar",
    "reunion_cancelada",
]

VALIDATION_STYLE = {
    "pendiente_evaluacion_cp": ("#fef9c3", "#a16207"),
    "validada_por_cp": ("#dcfce7", "#166534"),
    "rechazada_por_cp": ("#fee2e2", "#991b1b"),
    "pendiente_confirmacion_cliente": ("#ede9fe", "#6d28d9"),
    "cliente_solicita_revision": ("#cffafe", "#0e7490"),
    "cotizacion_valida": ("#f3e8ff", "#7e22ce"),
    "reagendar": ("#ffedd5", "#9a3412"),
    "reunion_cancelada": ("#f1f5f9", "#475569"),
    "evaluacion_cerrada_valida": ("#bbf7d0", "#14532d"),
    "evaluacion_cerrada_no_valida": ("#fecaca", "#7f1d1d"),
}


def _clean(value, default=""):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    return texto_real(value) or default


def _safe_html(value):
    return html.escape(_clean(value))


def etapa_agenda_visible(value):
    """Oculta la etapa tecnica `reunion_agendada` del portal cliente."""
    return "reunion_futura" if value == "reunion_agendada" else value


def motivo_reagenda(status):
    return {
        "no_asistio_lead": "El prospecto no asistió",
        "no_asistio_cliente": "El cliente no asistió",
        "reagendada": "El prospecto solicitó reagendar",
        "pendiente_reagendar": "Pendiente de coordinar nueva fecha",
    }.get(_clean(status), "Requiere coordinación de una nueva fecha")


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
        "solicita_cotizacion": "cotizacion",
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
        source_status = normalizar_status(row.get("estado_reunion"))
        status = (
            "cotizacion"
            if source_status == "cotizacion"
            else _clean(seg.get("status_reunion")) or source_status
        )
        cp = normalizar_cp(row, seg)
        bant = bant_cp(row, seg)
        client = _clean(seg.get("val_estado_cli")) or "espera"
        evidence = evidencia_disponible(row, seg)
        override = seg.get("val_estado_final") if seg.get("final_override") else None
        if status == "cotizacion":
            final = "valida"
            cp = "valida"
        elif seg.get("val_estado_final") == "valida" and seg.get("flag_meta_countable") is True:
            final = "valida"
        else:
            final = derivar_final(
                status,
                cp,
                client,
                bant,
                override=override,
                evidencia_suficiente=evidence,
                resultado_actual=seg.get("val_estado_final"),
            )
        etapa_agenda = derivar_etapa_agenda(row.get("fecha"), status)
        cp_visual = cp
        if (
            cp_visual not in {"valida", "no_valida"}
            and icp_gbs(status, seg.get("icp_cumple")) is True
            and len(bant) >= 2
        ):
            cp_visual = "valida"
        estatus_validacion = derivar_estatus_validacion(
            etapa_agenda,
            cp_visual,
            client,
            final,
            flag_disputa=bool(seg.get("flag_disputa")),
        )
        row.update({
            "_seg": seg,
            "_status": status,
            "_cp": cp,
            "_bant": bant,
            "_client": client,
            "_evidence": evidence,
            "_final": final,
            "_agenda_stage": etapa_agenda,
            "_validation_status": estatus_validacion,
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
    term = st.text_input(
        "Buscar contacto",
        placeholder="Buscar contacto por correo, empresa, teléfono o nombre",
        key="gbs_busqueda_historica",
    )
    if term and len(term.strip()) >= 3:
        results = buscar_contacto(term)
        if results.empty:
            st.info("No encontramos reuniones asociadas a ese contacto.")
        else:
            view = results.rename(columns={
                "fecha_reunion": "Fecha",
                "hora_reunion": "Hora",
                "empresa": "Empresa",
                "contacto": "Contacto",
                "cargo": "Cargo",
                "email": "Email",
                "telefono": "Teléfono",
            })
            columns = [
                c for c in
                ["Fecha", "Hora", "Empresa", "Contacto", "Cargo", "Email", "Teléfono"]
                if c in view
            ]
            st.dataframe(view[columns], use_container_width=True, hide_index=True)


def sincronizar_busqueda_principal():
    """Al borrar la búsqueda, restablece inmediatamente el listado visible."""
    if not _clean(st.session_state.get("gbs_search")):
        st.session_state["gbs_kpi_filter"] = None


@st.cache_data(ttl=300)
def cargar_icp_resumen():
    fields = (
        "icp_pais,icp_industrias,icp_tamano,icp_cargos,icp_adicional,"
        "icp_descarte,propuesta_valor,dolores_clientes,gatillos_compra,"
        "keywords_prospecto,updated_at"
    )
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/gbs_onboarding"
            f"?select={fields}&cliente=eq.gbs&limit=1",
            headers=_H,
            timeout=10,
        )
        if response.ok and response.json():
            return response.json()[0]
    except requests.RequestException:
        pass
    return {
        "icp_pais": "Chile, Colombia, Perú",
        "icp_industrias": (
            "Minería y Metales, Retail, Automotriz, Alimentos y Bebidas, "
            "Dispositivos Médicos, Electrónica, Maquinaria Industrial, Vinos y Licores"
        ),
        "icp_tamano": "1-10, 11-20, 21-50, 51-100, 101-200 empleados",
        "icp_cargos": (
            "Gerente de Abastecimiento, Supply Chain Manager, Gerente de Logística, "
            "Encargado de Importaciones, Gerente General / Dueño"
        ),
    }


def _resumen_icp_html():
    profile = perfil_icp(cargar_icp_resumen())
    return (
        '<div style="font-size:11px;color:#475569;line-height:1.45;margin-top:3px">'
        f'<div>{_safe_html(profile["resumen"])}</div></div>'
    )


def set_kpi_filter(value):
    st.session_state["gbs_kpi_filter"] = value


def render_kpis(base_df):
    goal = meta_de("gbs") or {"validas": 0}
    target = int(goal.get("validas") or 0)
    validas = int(
        base_df["_validation_status"].isin(
            {"evaluacion_cerrada_valida", "cotizacion_valida"}
        ).sum()
    )
    counts = {
        "all": len(base_df),
        "valid": validas,
        "not_valid": int(
            (
                base_df["_validation_status"]
                == "evaluacion_cerrada_no_valida"
            ).sum()
        ),
        "pending_client": int(
            (
                base_df["_validation_status"]
                == "pendiente_confirmacion_cliente"
            ).sum()
        ),
        "review": int(
            (
                base_df["_validation_status"]
                == "cliente_solicita_revision"
            ).sum()
        ),
        "reschedule": int(
            (base_df["_validation_status"] == "reagendar").sum()
        ),
    }
    active = st.session_state.get("gbs_kpi_filter")
    palette = {
        "all": ("#eff6ff", "#bfdbfe", "#1d4ed8"),
        "valid": ("#f0fdf4", "#86efac", "#166534"),
        "not_valid": ("#fef2f2", "#fecaca", "#991b1b"),
        "pending_client": ("#ede9fe", "#c4b5fd", "#6d28d9"),
        "review": ("#ecfeff", "#a5f3fc", "#0e7490"),
        "reschedule": ("#fff7ed", "#fdba74", "#9a3412"),
    }
    styles = []
    for key, (background, border, color) in palette.items():
        active_style = f"box-shadow:0 0 0 2px {color}55!important;" if active == key else ""
        styles.append(
            f'div[class*="st-key-gbs_kpi_{key}"] button{{'
            f'background:{background}!important;border:1px solid {border}!important;'
            f'color:{color}!important;min-height:62px!important;text-align:left!important;'
            f'font-weight:800!important;white-space:pre-line!important;{active_style}}}'
            f'div[class*="st-key-gbs_kpi_{key}"] button p{{'
            f'color:{color}!important;font-size:14px!important;line-height:1.45!important}}'
        )
    st.markdown(f"<style>{''.join(styles)}</style>", unsafe_allow_html=True)

    kpi_grid = st.columns([0.18, 1, 1, 1, 1, 1, 1, 0.18], gap="small")
    columns = kpi_grid[1:-1]
    for column, (key, label) in zip(columns, FILTROS_KPI.items()):
        with column:
            st.button(
                f"{label}\n{counts[key]}",
                key=f"gbs_kpi_{key}",
                use_container_width=True,
                type="primary" if active == key else "secondary",
                on_click=set_kpi_filter,
                args=(None if active == key else key,),
            )
    pct = round(validas / target * 100) if target else 0
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;margin:7px 2px 12px">'
        f'<span style="font-size:13px;font-weight:800;color:#6d28d9;white-space:nowrap">'
        f'Avance de meta · {validas}/{target} ({pct}%)</span>'
        f'<div style="height:6px;flex:1;background:#ede9fe;border-radius:6px;overflow:hidden">'
        f'<div style="height:6px;width:{min(pct, 100)}%;background:{GBS_PURPLE};'
        f'border-radius:6px"></div></div></div>',
        unsafe_allow_html=True,
    )
    return counts


def aplicar_kpi(df):
    active = st.session_state.get("gbs_kpi_filter", "all")
    if active == "valid":
        return df[
            df["_validation_status"].isin(
                {"evaluacion_cerrada_valida", "cotizacion_valida"}
            )
        ].copy()
    if active == "not_valid":
        return df[
            df["_validation_status"] == "evaluacion_cerrada_no_valida"
        ].copy()
    if active == "pending_client":
        return df[
            df["_validation_status"] == "pendiente_confirmacion_cliente"
        ].copy()
    if active == "review":
        return df[
            df["_validation_status"] == "cliente_solicita_revision"
        ].copy()
    if active == "reschedule":
        return df[df["_validation_status"] == "reagendar"].copy()
    return df.copy()


def tabla_reuniones(df):
    """Tabla ejecutiva original: filas limpias y detalle mediante botón."""
    descending = st.session_state.get("gbs_fecha_desc", True)
    ordered = df.copy()
    ordered["_fecha_orden"] = pd.to_datetime(ordered["fecha"], errors="coerce")
    ordered = ordered.sort_values(
        "_fecha_orden",
        ascending=not descending,
        na_position="last",
    )

    widths = [0.85, 1.55, 1.5, 1.3, 1.35, 1.85, 1]
    # El encabezado queda fuera del área con scroll para permanecer fijo de
    # forma fiable, sin depender de selectores internos de Streamlit.
    with st.container(key="gbs_meeting_table_header"):
        header = st.columns(widths, vertical_alignment="center")
        for column, label in zip(
            header,
            [
                "Fecha",
                "Empresa",
                "Contacto",
                "Cargo",
                "Etapa de agenda",
                "Estatus de validación",
                "",
            ],
        ):
            column.markdown(
                f'<div style="font-size:12px;font-weight:800;text-transform:uppercase;'
                f'letter-spacing:.4px;color:#fff">{label}</div>',
                unsafe_allow_html=True,
            )
        if header[0].button(
            "↓" if descending else "↑",
            key="gbs_sort_fecha",
            help="Ordenar por fecha",
        ):
            st.session_state["gbs_fecha_desc"] = not descending
            st.rerun()

    if True:
        for _, row in ordered.iterrows():
            parsed_date = pd.to_datetime(row.get("fecha"), errors="coerce")
            short_date = "—"
            if row.get("_agenda_stage") == "cotizacion":
                short_date = "Cotización"
            elif not pd.isna(parsed_date):
                short_date = f"{parsed_date.day:02d} {MESES_ES[parsed_date.month - 1][:3]}"
            hour = "" if row.get("_agenda_stage") == "cotizacion" else _clean(row.get("hora"))[:5]
            agenda_stage = etapa_agenda_visible(row.get("_agenda_stage"))
            validation_status = row.get("_validation_status")

            columns = st.columns(widths, vertical_alignment="center")
            columns[0].markdown(
                f'<div style="font-size:14px;font-weight:750;color:#0f172a">{short_date}</div>'
                f'<div style="font-size:13px;color:#64748b">{_safe_html(hour)}</div>',
                unsafe_allow_html=True,
            )
            columns[1].markdown(
                f'<div style="font-size:14px;font-weight:750;color:#0f172a">'
                f'{_safe_html(row.get("empresa"))}</div>',
                unsafe_allow_html=True,
            )
            columns[2].markdown(
                f'<div style="font-size:14px;color:#334155">'
                f'{_safe_html(_clean(row.get("contacto")).title())}</div>',
                unsafe_allow_html=True,
            )
            columns[3].markdown(
                f'<div style="font-size:14px;color:#334155">'
                f'{_safe_html(row.get("cargo"))}</div>',
                unsafe_allow_html=True,
            )
            agenda_bg, agenda_color = AGENDA_STYLE.get(
                agenda_stage,
                ("#f1f5f9", "#475569"),
            )
            agenda_html = (
                f'<span style="background:{agenda_bg};color:{agenda_color};'
                f'padding:6px 11px;border-radius:9px;font-size:13px;font-weight:800;'
                f'display:inline-block;line-height:1.2">'
                f'{LABEL_ETAPA_AGENDA.get(agenda_stage, "Pendiente")}</span>'
            )
            columns[4].markdown(agenda_html, unsafe_allow_html=True)
            validation_bg, validation_color = VALIDATION_STYLE.get(
                validation_status,
                ("#fef9c3", "#a16207"),
            )
            validation_html = (
                f'<span style="background:{validation_bg};color:{validation_color};'
                f'padding:6px 11px;border-radius:9px;font-size:13px;font-weight:800;'
                f'display:inline-block;line-height:1.2">'
                f'{LABEL_ESTATUS_VALIDACION.get(validation_status, "Pendiente")}</span>'
            )
            columns[5].markdown(validation_html, unsafe_allow_html=True)
            if columns[6].button(
                "Ver detalle",
                key=f"gbs_detalle_{int(row['id'])}",
                use_container_width=True,
            ):
                abrir_detalle(row)
            st.markdown(
                '<div style="border-bottom:1px solid #f1f5f9"></div>',
                unsafe_allow_html=True,
            )
    return None


def render_evidencia(row, seg, *, cotizacion=False):
    if cotizacion:
        st.markdown(
            '<div style="background:#faf5ff;border:1px solid #d8b4fe;'
            'border-left:5px solid #9333ea;border-radius:10px;padding:13px 15px;'
            'font-size:12px;color:#6b21a8;line-height:1.5">'
            '<b>Confirmación Conprospección:</b> al solicitar una cotización, el prospecto '
            'demuestra interés inmediato por el servicio de GBS Logistics y se realiza '
            'el traspaso directo al equipo comercial del cliente. La cotización se '
            'considera válida automáticamente.</div>',
            unsafe_allow_html=True,
        )
        return
    recording = valor_evidencia(row, seg, "recording_url")
    transcript = valor_evidencia(row, seg, "transcript_url")
    ai_summary = valor_evidencia(row, seg, "ai_summary")
    ai_evidence = valor_evidencia(row, seg, "ai_evidence")
    confirmation = ai_summary or ai_evidence
    cols = st.columns(2)
    with cols[0]:
        if recording:
            st.link_button("Abrir grabación", recording, use_container_width=True)
        else:
            st.button("Grabación no disponible", disabled=True, use_container_width=True)
    with cols[1]:
        if transcript:
            st.link_button("Abrir transcripción", transcript, use_container_width=True)
        else:
            st.button("Transcripción no disponible", disabled=True, use_container_width=True)
    if confirmation:
        st.markdown(
            '<div style="display:grid;grid-template-columns:150px minmax(0,1fr);gap:13px;'
            'align-items:start;background:#faf5ff;border:1px solid #d8b4fe;'
            'border-left:5px solid #7c3aed;border-radius:10px;padding:12px 14px;'
            'margin-top:8px">'
            f'<div style="font-size:12px;font-weight:850;color:{GBS_PURPLE};'
            'line-height:1.35">Confirmación<br>Conprospección</div>'
            f'<div style="font-size:12px;color:#475569;line-height:1.5">'
            f'{_safe_html(confirmation)}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="display:grid;grid-template-columns:150px minmax(0,1fr);gap:13px;'
            'background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;'
            'padding:11px 14px;margin-top:8px">'
            f'<div style="font-size:12px;font-weight:850;color:{GBS_PURPLE}">'
            'Confirmación Conprospección</div>'
            '<div style="font-size:12px;color:#94a3b8">Aún no disponible.</div></div>',
            unsafe_allow_html=True,
        )


def render_historial(reunion_id, row):
    history = cargar_historial(int(reunion_id))

    def _fecha_historial(value, hora=""):
        dt = pd.to_datetime(value, errors="coerce", utc=True)
        if pd.isna(dt):
            return ""
        fecha = dt.strftime("%d/%m/%Y")
        hora_txt = _clean(hora)[:5]
        if not hora_txt and (dt.hour or dt.minute):
            hora_txt = dt.strftime("%H:%M")
        return f"{fecha} · {hora_txt}" if hora_txt else fecha

    fecha_reunion = row.get("fecha_reunion") or row.get("fecha")
    hora_reunion = row.get("hora_reunion") or row.get("hora")
    items = []
    seen = set()

    def add_item(when, event, detail=""):
        key = (event, detail)
        if key not in seen:
            seen.add(key)
            items.append((when, event, detail))

    is_quote = row.get("_agenda_stage") == "cotizacion"
    quote_status_recorded = any(
        _clean(event.get("field_changed")) == "status_reunion"
        and _clean(event.get("new_value")) in {"cotizacion", "solicita_cotizacion"}
        for event in history
    )
    if is_quote:
        if not quote_status_recorded:
            add_item(_fecha_historial(fecha_reunion), "Cotización")
    else:
        add_item(
            _fecha_historial(fecha_reunion, hora_reunion),
            "Reunión agendada",
        )
    fecha_dt = pd.to_datetime(fecha_reunion, errors="coerce")
    if not is_quote and (row.get("_status") == "realizada" or (
        not pd.isna(fecha_dt) and fecha_dt.date() <= date.today()
        and row.get("_flow") != "reunion_cancelada"
    )):
        add_item(
            _fecha_historial(fecha_reunion, hora_reunion),
            "Reunión realizada",
        )
    event_labels = {
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
            if is_quote and new_value == "realizada":
                continue
            detail = LABEL_STATUS.get(new_value, new_value)
            if new_value == "realizada":
                detail = "Reunión realizada"
            add_item(
                _fecha_historial(event.get("changed_at")),
                detail,
            )
            continue
        else:
            detail = new_value
        add_item(
            _fecha_historial(event.get("changed_at")),
            event_labels.get(field, field),
            detail,
        )
    current_validation_event = LABEL_ESTATUS_VALIDACION.get(
        row.get("_validation_status"),
        row.get("_validation_status"),
    )
    if row.get("_final") == "valida":
        current_validation_event = "Evaluación cerrada · Válida"
    elif row.get("_final") == "no_valida":
        current_validation_event = "Evaluación cerrada · No válida"
    add_item(
        _fecha_historial(pd.Timestamp.now(tz="UTC")),
        current_validation_event,
    )
    if row.get("_agenda_stage") == "reagendar":
        add_item(
            _fecha_historial(pd.Timestamp.now(tz="UTC")),
            "Motivo de reagenda",
            motivo_reagenda(row.get("_status")),
        )

    timeline = []
    for when, event, detail in items:
        timeline.append(
            f'<div style="display:grid;grid-template-columns:12px 105px 1fr;gap:8px;'
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
        f'<div style="font-size:15px;font-weight:850;color:{GBS_PURPLE};'
        f'margin:17px 0 8px;padding-bottom:6px;border-bottom:1px solid #e9d5ff">'
        f'{number}. {title}</div>'
    )


def _detail_line(label, value, link=False, link_label="Abrir enlace ↗"):
    clean = _clean(value)
    if not clean:
        return ""
    rendered = (
        f'<a href="{html.escape(clean)}" target="_blank" '
        f'style="color:{GBS_PURPLE};font-weight:600;text-decoration:none;'
        f'min-width:0;overflow-wrap:anywhere;word-break:break-word">'
        f'{html.escape(link_label)}</a>'
        if link else f'<span style="font-weight:600;color:#0f172a">{html.escape(clean)}</span>'
    )
    return (
        f'<div style="display:grid;grid-template-columns:96px minmax(0,1fr);gap:8px;'
        f'padding:3px 0;font-size:12px">'
        f'<span style="color:#64748b">{label}</span>{rendered}</div>'
    )


def _bant_evaluation(bant):
    labels = [("N", "Need"), ("A", "Authority"), ("B", "Budget"), ("T", "Timing")]
    variables = []
    for code, label in labels:
        detected = code in bant
        variables.append(
            f'<div style="background:{"#ecfdf5" if detected else "#f8fafc"};'
            f'border:1px solid {"#86efac" if detected else "#e2e8f0"};'
            f'border-radius:8px;padding:7px 8px;text-align:center;min-width:0">'
            f'<div style="font-size:11px;font-weight:850;color:'
            f'{"#166534" if detected else "#64748b"}">{code} · {label}</div>'
            f'<div style="font-size:10px;color:{"#16a34a" if detected else "#94a3b8"};'
            f'margin-top:2px">{"Detectada" if detected else "No informada"}</div></div>'
        )
    return (
        f'<div style="border:1px solid #ddd6fe;background:#fff;border-radius:10px;'
        f'padding:11px 12px;margin-top:9px">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;'
        f'margin-bottom:8px"><div style="font-size:12px;font-weight:850;color:{GBS_PURPLE}">'
        f'Variables BANT</div><div style="font-size:11px;font-weight:750;color:#64748b">'
        f'{len(bant)} de 4 detectadas</div></div>'
        f'<div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));'
        f'gap:6px">{"".join(variables)}</div></div>'
    )


def _icp_evaluation(icp):
    icp_label = (
        ("Cumple", "#166534", "#f0fdf4", "#86efac")
        if icp
        else ("No cumple", "#991b1b", "#fef2f2", "#fecaca")
    )
    return (
        f'<div style="border:1px solid {icp_label[3]};background:{icp_label[2]};'
        f'border-radius:10px;padding:12px 14px">'
        f'<div style="display:grid;grid-template-columns:82px minmax(0,1fr);gap:14px;'
        f'align-items:start">'
        f'<div><div style="font-size:12px;font-weight:850;color:{GBS_PURPLE};'
        f'margin-bottom:5px">ICP</div>'
        f'<div style="font-size:15px;font-weight:850;color:{icp_label[1]}">'
        f'{icp_label[0]}</div></div>'
        f'<div>{_resumen_icp_html()}</div></div></div>'
    )


def render_detalle(row):
    seg = row["_seg"]
    reunion_id = int(row["id"])
    cp = row["_cp"]
    bant = row["_bant"]
    client = row["_client"]
    final = row["_final"]
    status = row["_status"]
    is_quote = row.get("_agenda_stage") == "cotizacion"
    flow = row["_flow"]
    future = flow == "reunion_futura"
    evidence = bool(row["_evidence"])
    info_reunion = informacion_reunion(row, seg)
    if is_quote and not info_reunion:
        info_reunion = _clean(row.get("observacion"))
    icp = icp_gbs(status, seg.get("icp_cumple"))
    locked = client in {"valida", "requiere_revision", "no_valida", "reagendada"}
    client_actions = acciones_cliente_permitidas(flow, cp, client)
    if row.get("_agenda_stage") in {"cotizacion", "reagendar", "reunion_cancelada"}:
        client_actions = ()
    contractually_valid = "confirmar" in client_actions

    meeting_link = _clean(row.get("direccion_reunion"))
    website = valor_custom_field(row.get("raw_data"), ("website", "sitio web"))
    company_linkedin = valor_custom_field(row.get("raw_data"), ("linkedin_empresa", "linkedin empresa"))
    contact_linkedin = valor_custom_field(row.get("raw_data"), ("linkedin_personal", "linkedin personal"))
    visible_agenda_stage = etapa_agenda_visible(row["_agenda_stage"])
    agenda_bg, agenda_color = AGENDA_STYLE.get(
        visible_agenda_stage,
        ("#f1f5f9", "#475569"),
    )
    validation_bg, validation_color = VALIDATION_STYLE.get(
        row["_validation_status"],
        ("#fef9c3", "#a16207"),
    )

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;font-size:13px;'
        f'font-weight:700;color:#334155"><span style="width:9px;height:9px;'
        f'border-radius:50%;background:#16a34a"></span>'
        f'<span style="background:{agenda_bg};color:{agenda_color};padding:4px 9px;'
        f'border-radius:9px">{_safe_html(LABEL_ETAPA_AGENDA[visible_agenda_stage])}</span>'
        f'<span style="background:{validation_bg};color:{validation_color};padding:4px 9px;'
        f'border-radius:9px">{_safe_html(LABEL_ESTATUS_VALIDACION[row["_validation_status"]])}</span> · '
        f'{"Cotización" if is_quote else _safe_html(fmt_fecha(row.get("fecha")))}'
        f'{" · " + _safe_html(row.get("hora")) if not is_quote and _clean(row.get("hora")) else ""}</div>',
        unsafe_allow_html=True,
    )
    if row.get("_agenda_stage") == "reagendar":
        motivo = motivo_reagenda(status)
        comentario = _clean(seg.get("comentario_cp"))
        st.markdown(
            '<div style="background:#fff7ed;border:1px solid #fdba74;'
            'border-left:5px solid #ea580c;border-radius:10px;padding:14px 16px;'
            'margin:10px 0 14px">'
            '<div style="font-size:15px;font-weight:800;color:#9a3412">Reagendar</div>'
            f'<div style="font-size:12px;color:#7c2d12;margin-top:5px">{_safe_html(motivo)}</div>'
            + (
                f'<div style="font-size:11px;color:#9a3412;margin-top:6px">'
                f'{_safe_html(comentario)}</div>'
                if comentario else ""
            )
            + '</div>',
            unsafe_allow_html=True,
        )
    else:
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
            + _detail_line("Website", website, link=True, link_label="Abrir sitio ↗")
            + _detail_line("LinkedIn empresa", company_linkedin, link=True, link_label="Ver perfil ↗")
            + _detail_line("LinkedIn contacto", contact_linkedin, link=True, link_label="Ver perfil ↗")
            + (
                ""
                if is_quote
                else _detail_line("Fecha reunión", fmt_fecha(row.get("fecha")))
                + _detail_line("Hora reunión", row.get("hora"))
                + _detail_line("Link reunión", meeting_link, link=True, link_label="Unirse a reunión ↗")
            ),
            unsafe_allow_html=True,
        )

    st.markdown(
        _section_header(2, "Información" if is_quote else "Información para reunión"),
        unsafe_allow_html=True,
    )
    if info_reunion:
        st.markdown(
            f'<div style="font-size:13px;color:#334155;line-height:1.5">'
            f'{_safe_html(info_reunion)}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption("Sin información registrada." if is_quote else "Sin información de preparación registrada.")

    st.markdown(_section_header(3, "Evaluación Conprospección"), unsafe_allow_html=True)
    st.markdown(_icp_evaluation(icp), unsafe_allow_html=True)
    if st.button(
        "Ver ICP acordado →",
        key=f"gbs_icp_link_{reunion_id}",
        help="Abrir el resumen ICP confirmado en Onboarding",
    ):
        st.session_state["gbs_scroll_to_icp"] = True
        st.switch_page("pages/14_GBS_Onboarding.py")
    if not is_quote:
        st.markdown(_bant_evaluation(bant), unsafe_allow_html=True)
    if not is_quote:
        st.markdown(
            '<div style="background:#faf5ff;border:1px solid #ddd6fe;border-radius:8px;'
            'padding:9px 12px;margin-top:9px;font-size:11px;color:#5b21b6;line-height:1.45">'
            '<b>Criterio de referencia:</b> ICP validado y al menos 2 variables BANT. '
            'Conprospección conserva la resolución final según los antecedentes de cada reunión.'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown(_section_header(4, "Evidencia"), unsafe_allow_html=True)
    render_evidencia(row, seg, cotizacion=is_quote)

    st.markdown(_section_header(5, "Acción cliente"), unsafe_allow_html=True)
    if is_quote:
        st.info(
            "Cotización válida automáticamente por interés inmediato y traspaso al equipo comercial de GBS Logistics."
        )
    elif future:
        st.info("Reunión futura. Aún no admite confirmación ni solicitud de revisión.")
    elif locked:
        st.info("La respuesta del cliente ya fue registrada. La reunión queda bloqueada.")
    elif cp == "no_valida":
        st.info("Conprospección marcó la reunión como no válida. No requiere confirmación.")
    elif not client_actions:
        st.info("Esta reunión no tiene acciones disponibles para el cliente.")
    else:
        if cp == "espera":
            st.info(
                "Puedes dejar tu respuesta ahora. La reunión seguirá pendiente de "
                "evaluación de Conprospección y no afectará la meta hasta su resolución."
            )
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
            show_review = st.button(
                "Solicitar revisión",
                key=f"show_review_{reunion_id}",
                use_container_width=True,
            )

        review_open_key = f"review_open_{reunion_id}"
        if show_review:
            st.session_state[review_open_key] = True

        if st.session_state.get(review_open_key):
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
                    "Enviar solicitud de revisión",
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

    st.markdown(_section_header(6, "Historial"), unsafe_allow_html=True)
    render_historial(reunion_id, row)


@st.dialog("Detalle de reunión", width="small")
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
        div[class*="st-key-gbs_icp_link_"] button {{
            background:transparent!important;
            border:none!important;
            color:{GBS_PURPLE}!important;
            min-height:auto!important;
            padding:3px 0!important;
            box-shadow:none!important;
            font-size:12px!important;
            text-decoration:underline!important;
        }}
        div[class*="st-key-gbs_icp_link_"] button p {{
            color:{GBS_PURPLE}!important;
            font-weight:800!important;
        }}
        div[data-testid="stDataFrame"] {{
            border:1px solid #e2e8f0;
            border-radius:10px;
            overflow:hidden;
        }}
        div[data-testid="stLayoutWrapper"]:has(> .st-key-gbs_meeting_table_header) {{
            position:sticky!important;
            top:2.75rem!important;
            z-index:99999!important;
            background:linear-gradient(90deg,#4c1d95,#7c3aed)!important;
            padding:9px 12px!important;
            border-radius:10px!important;
            box-shadow:0 4px 10px rgba(15,23,42,.10)!important;
            width:100%!important;
        }}
        .st-key-gbs_meeting_table_header {{
            background:transparent!important;
        }}
        .st-key-gbs_meeting_table_header button {{
            background:#fff!important;
            min-height:36px!important;
        }}
        div[data-testid="stVerticalBlock"]:has(.st-key-gbs_meeting_table_header),
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-gbs_meeting_table_header) {{
            overflow:visible!important;
        }}
        div[data-testid="stDialog"] {{
            justify-content:flex-end!important;
            align-items:stretch!important;
            padding:0!important;
        }}
        html:has(div[data-testid="stDialog"]),
        body:has(div[data-testid="stDialog"]),
        div[data-testid="stAppViewContainer"]:has(div[data-testid="stDialog"]),
        section[data-testid="stMain"]:has(div[data-testid="stDialog"]) {{
            overflow:hidden!important;
        }}
        div[data-testid="stDialog"] div[role="dialog"] {{
            position:fixed!important;
            top:0!important;
            right:0!important;
            left:auto!important;
            transform:none!important;
            width:min(560px,100vw)!important;
            max-width:min(560px,100vw)!important;
            height:100vh!important;
            max-height:100vh!important;
            margin:0!important;
            border-radius:16px 0 0 16px!important;
            overflow-y:auto!important;
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
    selected_agenda = st.session_state.get("gbs_agenda_stage", "all")
    if selected_agenda not in {"all", *VISIBLE_ETAPAS_AGENDA}:
        selected_agenda = "all"
        st.session_state["gbs_agenda_stage"] = "all"
    selected_validation = st.session_state.get(
        "gbs_validation_status",
        "all",
    )
    if selected_validation not in {"all", *ESTATUS_VALIDACION}:
        selected_validation = "all"
        st.session_state["gbs_validation_status"] = "all"

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
    if not enriched.empty and selected_agenda != "all":
        enriched = enriched[
            enriched["_agenda_stage"].map(etapa_agenda_visible) == selected_agenda
        ].copy()
    if not enriched.empty and selected_validation != "all":
        enriched = enriched[
            enriched["_validation_status"] == selected_validation
        ].copy()

    counts = render_kpis(enriched) if "_final" in enriched.columns else {
        "all": 0,
        "valid": 0,
        "not_valid": 0,
        "pending_client": 0,
        "review": 0,
        "reschedule": 0,
    }
    filter_cols = st.columns([3.2, 2.2, 2.2, 2.6, 1.1])
    with filter_cols[0]:
        st.text_input(
            "Buscar",
            placeholder="Buscar empresa, contacto o cargo",
            label_visibility="collapsed",
            key="gbs_search",
            on_change=sincronizar_busqueda_principal,
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
            "Etapa de agenda",
            ["all", *VISIBLE_ETAPAS_AGENDA],
            format_func=lambda value: (
                "Todo"
                if value == "all"
                else LABEL_ETAPA_AGENDA[value]
            ),
            label_visibility="visible",
            key="gbs_agenda_stage",
        )
    with filter_cols[3]:
        st.selectbox(
            "Estatus de validación",
            ["all", *ESTATUS_VALIDACION],
            format_func=lambda value: (
                "Todo"
                if value == "all"
                else LABEL_ESTATUS_VALIDACION[value]
            ),
            label_visibility="visible",
            key="gbs_validation_status",
        )
    with filter_cols[4]:
        if st.button("Actualizar", use_container_width=True, key="gbs_refresh"):
            st.cache_data.clear()
            st.session_state["gbs_kpi_filter"] = None
            st.rerun()

    render_buscador()

    filtered = aplicar_kpi(enriched) if not enriched.empty else enriched
    if filtered.empty:
        st.info("No hay reuniones para el periodo y filtros seleccionados.")
        return

    tabla_reuniones(filtered)


run()
