import sys
import datetime
import requests
import pandas as pd
import streamlit as st
from pathlib import Path

DASHBOARD_DIR = Path(__file__).resolve().parent.parent
ROOT = DASHBOARD_DIR.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))
from shared.config import supabase_url, supabase_key, ghl_tokens
from shared.metas import meta_de, NOMBRE_A_SLUG
from shared.validacion import (
    ESTADOS_FLUJO,
    LABEL_ESTADO_FLUJO,
    STATUS_REUNION,
    VAL_ESTADOS,
    bant_desde_fuentes,
    derivar_estado_flujo,
    derivar_final,
    icp_gbs,
    informacion_reunion,
    texto_real,
)
from shared.seguimiento import (
    cargar as _cargar_seg, guardar_nivel as _gn_cp,
    payload_antecedentes_internos, recalcular_final_y_flags, registrar_historial, bant_to_list,
)
from shared.validacion import ESTADO_COMERCIAL
from shared.validacion_ui import (
    LABEL_VALIDEZ, LABEL_STATUS, LABEL_ESTADO_COMERCIAL, chip_status,
    banner_final, fila_resumen, bloque_resumen, encabezado_seccion,
    mini_label, CAP_CP, CAP_CLI, chip_estado_flujo, tarjeta_estado_flujo,
)
from master_auth import require_master_auth, render_master_user_sidebar

st.set_page_config(page_title="Seguimiento Reuniones", layout="wide")
if not require_master_auth():
    st.stop()

SUPABASE_URL = supabase_url()
SUPABASE_KEY = supabase_key()
GHL_TOKENS = ghl_tokens()

COLORES_CLIENTE = {
    "GBS LOGISTICS": {"bg": "#ede9fe", "color": "#5b21b6", "border": "#7c3aed"},
    "TIRESIAS": {"bg": "#1e3a5f", "color": "#ffffff", "border": "#3b82f6"},
    "CLICKIE": {"bg": "#fef08a", "color": "#78350f", "border": "#f59e0b"},
    "BAMBUTECH": {"bg": "#dcfce7", "color": "#166534", "border": "#22c55e"},
    "JUST4U": {"bg": "#ffedd5", "color": "#9a3412", "border": "#f97316"},
    "ECOSMART": {"bg": "#e0f7fa", "color": "#0e7490", "border": "#06b6d4"},
}

MESES_ES = ["enero","febrero","marzo","abril","mayo","junio",
            "julio","agosto","septiembre","octubre","noviembre","diciembre"]
DIAS_ES = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]

PALETA_SDRS = [
    {"bg": "#fce7f3", "color": "#9d174d"},
    {"bg": "#dbeafe", "color": "#1e40af"},
    {"bg": "#fef9c3", "color": "#854d0e"},
    {"bg": "#d1fae5", "color": "#065f46"},
    {"bg": "#ede9fe", "color": "#5b21b6"},
    {"bg": "#ffedd5", "color": "#9a3412"},
    {"bg": "#e0f2fe", "color": "#075985"},
    {"bg": "#fce7f3", "color": "#831843"},
]
_sdr_color_cache: dict[str, dict] = {}


def color_sdr(nombre: str) -> dict:
    if nombre not in _sdr_color_cache:
        _sdr_color_cache[nombre] = PALETA_SDRS[len(_sdr_color_cache) % len(PALETA_SDRS)]
    return _sdr_color_cache[nombre]


ESTADOS_OPCIONES = {
    "Espera de validación": "pendiente_validacion",
    "Reunión válida": "valida",
    "Reunión no válida": "no_valida",
    "Reunión cancelada por cliente": "cancelada_cliente",
    "Reunión cancelada por CP": "cancelada_cp",
    "Reagendar reunión": "reagendar",
    "Reagendar - prospecto no asistió": "reagendar_no_asistio",
    "Reagendar - prospecto sugiere otro horario": "reagendar_otro_horario",
}
ESTADOS_LABEL = {v: k for k, v in ESTADOS_OPCIONES.items()}

ESTADO_A_STAGE_CATEGORY = {
    "valida": "reunion_valida",
    "no_valida": "reunion_no_valida",
    "cancelada_cliente": "reunion_no_valida",
    "cancelada_cp": "reunion_no_valida",
    "reagendar": "reagendada",
    "reagendar_no_asistio": "reagendada",
    "reagendar_otro_horario": "reagendada",
}

ESTADO_STYLE = {
    "pendiente_validacion": ("Espera", "#fef9c3", "#854d0e"),
    "pendiente": ("Espera", "#fef9c3", "#854d0e"),
    "reunion_agendada": ("Agendada", "#e0f2fe", "#075985"),
    "valida": ("Válida", "#dcfce7", "#166534"),
    "reunion_valida": ("Válida", "#dcfce7", "#166534"),
    "no_valida": ("No válida", "#fee2e2", "#991b1b"),
    "reunion_no_valida": ("No válida", "#fee2e2", "#991b1b"),
    "cancelada_cliente": ("Cancelada cliente", "#fee2e2", "#991b1b"),
    "cancelada_cp": ("Cancelada CP", "#fee2e2", "#991b1b"),
    "reagendar": ("Reagendar", "#ffedd5", "#9a3412"),
    "reagendar_no_asistio": ("No asistió", "#ffedd5", "#9a3412"),
    "reagendar_otro_horario": ("Otro horario", "#ffedd5", "#9a3412"),
}

_NO_VALIDA = ("no_valida", "reunion_no_valida", "cancelada_cliente", "cancelada_cp")
_REAGENDAR = ("reagendar", "reagendada", "reagendar_no_asistio", "reagendar_otro_horario")


def es_valida(v): return str(v).lower() in ("valida", "reunion_valida")
def es_no_valida(v): return str(v).lower() in _NO_VALIDA
def es_reagendar(v): return str(v).lower() in _REAGENDAR
def es_pendiente(v): return str(v).lower() not in (
    "valida", "reunion_valida", *_NO_VALIDA, *_REAGENDAR
)


def _count(dff: pd.DataFrame, fn) -> int:
    if "estado_validacion" not in dff.columns or dff.empty:
        return 0
    return int(dff["estado_validacion"].apply(fn).sum())


def formato_dia(d) -> str:
    if d is None or (isinstance(d, float) and pd.isna(d)):
        return ""
    d = pd.to_datetime(str(d))
    return f"{DIAS_ES[d.weekday()]} {d.day} de {MESES_ES[d.month-1]} {d.year}"


# <<DEDUP-PURO>>
def _dedup_key(row):
    opp = str(row.get("opportunity_id") or "").strip()
    if opp:
        return ("opp", opp)
    email = str(row.get("email") or "").strip().lower()
    if email:
        return ("email", email)
    contacto = str(row.get("contacto") or "").strip().lower()
    empresa = str(row.get("empresa") or "").strip().lower()
    return ("cont", contacto, empresa)


def deduplicar_reuniones(df):
    """Una reunión por prospecto y cliente: conserva la de fecha más reciente.
    Clave: opportunity_id -> email -> contacto+empresa, dentro de cada cliente_slug."""
    if df is None or df.empty:
        return df
    d = df.copy()
    d["_dk"] = d.apply(_dedup_key, axis=1)
    d = d.sort_values("fecha", na_position="first") # asc: la última fecha queda al final
    d = d.groupby(["cliente_slug", "_dk"], as_index=False, sort=False).tail(1)
    return d.drop(columns=["_dk"])
# <<DEDUP-PURO-FIN>>


_EMPTY_COLS = [
    "id", "opportunity_id", "ghl_contact_id", "cliente_slug", "location_id",
    "cliente", "fecha", "fecha_d", "mes", "hora", "sdr", "contacto", "cargo",
    "empresa", "industria", "pais", "email", "telefono", "estado_reunion",
    "estado_validacion", "es_valida",
    "raw_data", "informacion_reunion", "bant_sdr",
]


@st.cache_data(ttl=30)
def cargar_reuniones() -> pd.DataFrame:
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/vw_reuniones_semana?select=*",
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
        timeout=15,
    )
    if not resp.ok:
        st.error(f"Error cargando datos: {resp.text}")
        return pd.DataFrame(columns=_EMPTY_COLS)
    df = pd.DataFrame(resp.json())
    if df.empty:
        return pd.DataFrame(columns=_EMPTY_COLS)
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["fecha_d"] = df["fecha"].dt.date
    df["mes"] = df["fecha"].dt.to_period("M")
    df["sdr"] = df["sdr"].fillna("Sin asignar")
    df["cliente"] = df["cliente"].fillna("—")
    if "estado_validacion" not in df.columns:
        df["estado_validacion"] = None
    df = deduplicar_reuniones(df)
    extras = cargar_reuniones_extra()
    if not extras.empty and "id" in extras.columns:
        extra_columns = [
            column
            for column in ("id", "raw_data", "informacion_reunion", "bant_sdr")
            if column in extras.columns
        ]
        df = df.merge(extras[extra_columns], on="id", how="left", suffixes=("", "_extra"))
        for column in ("raw_data", "informacion_reunion", "bant_sdr"):
            extra = f"{column}_extra"
            if extra in df.columns:
                if column not in df.columns:
                    df[column] = df[extra]
                else:
                    df[column] = df[column].where(df[column].notna(), df[extra])
                df = df.drop(columns=[extra])
    df = df.sort_values("fecha", ascending=False, na_position="last").reset_index(drop=True)
    return df


@st.cache_data(ttl=30)
def cargar_reuniones_extra() -> pd.DataFrame:
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/reuniones"
        "?select=id,raw_data,informacion_reunion,bant_sdr",
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
        timeout=15,
    )
    if not response.ok:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/reuniones?select=id,raw_data",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            timeout=15,
        )
    return pd.DataFrame(response.json() if response.ok else [])


@st.cache_data(ttl=300)
def cargar_stages() -> pd.DataFrame:
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/ghl_pipeline_stages?select=cliente_slug,pipeline_id,stage_id,stage_category",
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
        timeout=15,
    )
    if not resp.ok:
        return pd.DataFrame()
    return pd.DataFrame(resp.json())


@st.cache_data(ttl=30)
def cargar_validacion_final() -> dict:
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/seguimiento_reuniones?select=reunion_id,val_estado_final",
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
        timeout=15)
    if not r.ok:
        return {}
    return {int(x["reunion_id"]): (x.get("val_estado_final") or "")
            for x in r.json() if x.get("reunion_id")}


def _normalizar_status_interno(value) -> str:
    status = texto_real(value).lower()
    return {
        "completed": "realizada",
        "confirmed": "agendada",
        "scheduled": "agendada",
        "reunion_agendada": "agendada",
        "cancelled": "cancelada_cliente",
        "canceled": "cancelada_cliente",
        "no_show": "no_asistio_lead",
        "rescheduled": "reagendada",
    }.get(status, status if status in STATUS_REUNION else "sin_info")


def enriquecer_estado_funcional(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    seg_por_slug: dict[str, dict] = {}
    rows = []
    for _, source in df.iterrows():
        row = source.to_dict()
        slug = str(row.get("cliente_slug") or "")
        if slug not in seg_por_slug:
            seg_por_slug[slug] = cargar_seg_slug(slug)
        seg = seg_por_slug[slug].get(int(row.get("id") or 0), {})
        status = texto_real(seg.get("status_reunion")) or _normalizar_status_interno(row.get("estado_reunion"))
        cp = texto_real(seg.get("val_estado_cp")) or (
            "valida" if str(row.get("estado_validacion") or "").lower() in {"valida", "reunion_valida"} else "espera"
        )
        client = texto_real(seg.get("val_estado_cli")) or "espera"
        final = derivar_final(
            status,
            cp,
            client,
            bant_desde_fuentes(row, seg),
            override=seg.get("val_estado_final") if seg.get("final_override") else None,
            resultado_actual=seg.get("val_estado_final"),
        )
        row["_seg"] = seg
        row["_status"] = status
        row["_final"] = final
        row["_flow"] = derivar_estado_flujo(
            row.get("fecha_d") or row.get("fecha"),
            status,
            cp,
            client,
            final,
        )
        rows.append(row)
    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def cargar_clientes() -> list[str]:
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/clientes?select=nombre&ghl_location_id=not.is.null&order=nombre.asc",
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
        timeout=15,
    )
    if not resp.ok:
        return []
    return [r["nombre"] for r in resp.json() if r.get("nombre")]


@st.cache_data(ttl=30)
def cargar_seg_slug(slug: str) -> dict:
    """Carga seguimiento_reuniones para un slug (cacheado 30 s)."""
    return _cargar_seg(slug)


@st.cache_data(ttl=30)
def cargar_flags_validacion() -> dict:
    """Cuenta flags globales de validación final."""
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/seguimiento_reuniones"
        f"?select=flag_meta_countable,flag_disputa,flag_cliente_pendiente",
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
        timeout=15)
    if not r.ok:
        return {"countable": 0, "disputa": 0, "pendiente_cli": 0}
    rows = r.json()
    return {
        "countable":    sum(1 for x in rows if x.get("flag_meta_countable")),
        "disputa":      sum(1 for x in rows if x.get("flag_disputa")),
        "pendiente_cli": sum(1 for x in rows if x.get("flag_cliente_pendiente")),
    }


def actualizar_supabase(reunion_id: int, estado: str) -> bool:
    r = requests.patch(
        f"{SUPABASE_URL}/rest/v1/reuniones?id=eq.{reunion_id}",
        json={"estado_validacion": estado},
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                 "Content-Type": "application/json", "Prefer": "return=minimal"},
        timeout=10,
    )
    return r.ok


def actualizar_ghl(opportunity_id: str, cliente_slug: str, estado: str, stages_df: pd.DataFrame) -> None:
    if not opportunity_id or opportunity_id.startswith("opportunity:"):
        opportunity_id = opportunity_id.replace("opportunity:", "") if opportunity_id else ""
    if not opportunity_id:
        return
    category = ESTADO_A_STAGE_CATEGORY.get(estado)
    if not category:
        return
    stage_row = stages_df[
        (stages_df["cliente_slug"] == cliente_slug) &
        (stages_df["stage_category"] == category)
    ]
    if stage_row.empty:
        return
    pipeline_id = stage_row.iloc[0]["pipeline_id"]
    stage_id = stage_row.iloc[0]["stage_id"]
    token = GHL_TOKENS.get(cliente_slug, "")
    if not token:
        return
    requests.put(
        f"https://services.leadconnectorhq.com/opportunities/{opportunity_id}",
        json={"pipelineId": pipeline_id, "pipelineStageId": stage_id},
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json", "Version": "2021-07-28"},
        timeout=10,
    )


def resumen_clientes_html(dff: pd.DataFrame, final_map: dict) -> str:
    import datetime as _dt
    mes_actual = _dt.date.today().month
    anio_actual = _dt.date.today().year
    cards = ""
    for nombre in [c for c in COLORES_CLIENTE if c in dff["cliente"].str.upper().unique()]:
        sub = dff[dff["cliente"].str.upper() == nombre]
        if sub.empty:
            continue
        c = COLORES_CLIENTE[nombre]
        slug = NOMBRE_A_SLUG.get(nombre, "")
        meta = meta_de(slug)

        def _es_final_valida(rid):
            return str(final_map.get(int(rid), "")).lower() in ("valida", "reunion_valida")

        if meta and meta["tipo"] == "mensual":
            sub_meta = sub[(sub["fecha"].dt.month == mes_actual) & (sub["fecha"].dt.year == anio_actual)]
            validas_final = int(sub_meta["id"].apply(_es_final_valida).sum()) if not sub_meta.empty else 0
            meta_n, sufijo = meta["validas"], "/mes"
        elif meta:
            validas_final = int(sub["id"].apply(_es_final_valida).sum())
            meta_n, sufijo = meta["validas"], ""
        else:
            validas_final, meta_n, sufijo = 0, 0, ""

        pct = round(validas_final / meta_n * 100) if meta_n else 0
        pct_barra = min(pct, 100)
        meta_txt = f"{validas_final}/{meta_n}{sufijo}" if meta_n else "—"
        cards += f"""
        <div style="background:{c['bg']};color:{c['color']};border:2px solid {c['border']};
                    border-radius:12px;padding:14px 18px;min-width:175px;flex:1">
          <div style="display:flex;justify-content:space-between;margin-bottom:6px">
            <span style="font-size:11px;font-weight:800;letter-spacing:.5px;text-transform:uppercase;opacity:.8">{sub['cliente'].iloc[0]}</span>
            <span style="font-size:13px;font-weight:700;opacity:.75">{pct}%</span>
          </div>
          <div style="font-size:22px;font-weight:700;margin-bottom:2px">{meta_txt}</div>
          <div style="font-size:10px;opacity:.7;margin-bottom:6px">reuniones válidas (validación final)</div>
          <div style="background:rgba(0,0,0,0.08);border-radius:4px;height:5px;margin-bottom:9px">
            <div style="background:{c['border']};width:{pct_barra}%;height:100%;border-radius:4px"></div>
          </div>
          <div style="font-size:11px;display:flex;flex-direction:column;gap:3px">
            <div style="display:flex;justify-content:space-between"><span>Válidas</span><b>{int((sub.get('_final', pd.Series(dtype=str)) == 'valida').sum())}</b></div>
            <div style="display:flex;justify-content:space-between"><span>No válidas</span><b>{int((sub.get('_final', pd.Series(dtype=str)) == 'no_valida').sum())}</b></div>
            <div style="display:flex;justify-content:space-between"><span>Solicita revisión</span><b>{int((sub.get('_flow', pd.Series(dtype=str)) == 'cliente_solicita_revision').sum())}</b></div>
            <div style="display:flex;justify-content:space-between"><span>Pendientes CP</span><b>{int((sub.get('_flow', pd.Series(dtype=str)) == 'pendiente_evaluacion_cp').sum())}</b></div>
          </div>
        </div>"""
    return f'<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:22px">{cards}</div>'


_OVERRIDE_OPTS = ["(automática)", "valida", "no_valida", "en_disputa", "excluida"]


def render_tabla(dff: pd.DataFrame, stages_df: pd.DataFrame, prefix: str) -> list[dict]:
    """Tarjeta por reunión con el MISMO bloque de 3 capas que el portal del cliente.
    Aquí el equipo (CP) edita su validez; la del cliente es solo-lectura; la final es
    automática con opción de override (Francisca)."""
    seg_por_slug: dict[str, dict] = {}
    for i, (_, row) in enumerate(dff.iterrows()):
        reunion_id = int(row.get("id", 0))
        opp_id = str(row.get("opportunity_id") or "")
        cliente_slug = str(row.get("cliente_slug") or "")
        cliente_val = str(row.get("cliente") or "")
        sdr_raw = str(row.get("sdr") or "Sin asignar")
        contacto = str(row.get("contacto") or "—").title()
        cargo = str(row.get("cargo") or "").title()
        empresa = str(row.get("empresa") or "—").title()
        email = str(row.get("email") or "")
        telefono = str(row.get("telefono") or "")
        industria = str(row.get("industria") or "")
        pais = str(row.get("pais") or "")
        hora = str(row.get("hora") or "—")[:5]
        dia = formato_dia(row.get("fecha"))

        if cliente_slug not in seg_por_slug:
            seg_por_slug[cliente_slug] = cargar_seg_slug(cliente_slug)
        seg = row.get("_seg") or seg_por_slug[cliente_slug].get(reunion_id, {})

        sc = color_sdr(sdr_raw)
        cl = COLORES_CLIENTE.get(cliente_val.upper(), {"bg": "#e5e7eb", "color": "#374151"})
        final = row.get("_final") or seg.get("val_estado_final") or "pendiente"
        flow = row.get("_flow") or "pendiente_evaluacion_cp"
        status_actual = row.get("_status") or _normalizar_status_interno(row.get("estado_reunion"))
        bant_actual = bant_desde_fuentes(row, seg)
        info_actual = informacion_reunion(row, seg)
        icp_actual = icp_gbs(status_actual, seg.get("icp_cumple")) if cliente_slug == "gbs" else seg.get("icp_cumple")
        override = bool(seg.get("final_override"))
        sdr_bg = sc["bg"] if sdr_raw != "Sin asignar" else "#fee2e2"
        sdr_color = sc["color"] if sdr_raw != "Sin asignar" else "#991b1b"

        datos = " · ".join(x for x in [cargo, email, telefono, industria, pais] if x and x != "—")
        with st.container(border=True):
            # Cabecera: cliente · SDR (interno) · empresa · contacto + fecha/hora/estado reunión
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px">'
                f'<span style="background:{cl["bg"]};color:{cl["color"]};padding:2px 9px;'
                f'border-radius:8px;font-size:11px;font-weight:700">{cliente_val}</span>'
                f'<span style="background:{sdr_bg};color:{sdr_color};padding:2px 9px;'
                f'border-radius:8px;font-size:11px;font-weight:600">{sdr_raw.title()}</span></div>'
                f'<div style="font-size:16px;font-weight:800;color:#0f172a">{empresa}'
                f'<span style="color:#cbd5e1;margin:0 6px">·</span>{contacto}</div>'
                f'<div style="font-size:12px;color:#64748b;margin-top:2px">{datos}</div>'
                f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:7px">'
                f'<span style="font-size:13px;font-weight:700;color:#334155">{dia}</span>'
                f'<span style="color:#94a3b8">·</span>'
                f'<span style="font-size:14px;font-weight:800;color:#4f46e5">{hora}</span>'
                f'{chip_estado_flujo(flow)}</div>',
                unsafe_allow_html=True)
            st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
            st.markdown(tarjeta_estado_flujo(flow), unsafe_allow_html=True)

            # 1) Validez final (banner)
            st.markdown(banner_final(final), unsafe_allow_html=True)

            # 2) Resumen comparativo (read-only): Conprospección + Cliente
            st.markdown(bloque_resumen(
                fila_resumen("Evaluación Conprospección", CAP_CP[1],
                             seg.get("val_estado_cp") or "espera", bant_actual,
                             seg.get("comentario_cp"), primera=True),
                fila_resumen("Validación del cliente", CAP_CLI[1],
                             seg.get("val_estado_cli") or "espera", bant_to_list(seg.get("bant_cli")),
                             seg.get("comentario_cli")),
            ), unsafe_allow_html=True)

            # 3) Zona de edición — Conprospección (lo que edita el equipo)
            st.markdown(encabezado_seccion("Tu evaluación (Conprospección)", CAP_CP[1]),
                        unsafe_allow_html=True)
            e1, e2 = st.columns(2)
            with e1:
                st.markdown(mini_label("Validez del equipo"), unsafe_allow_html=True)
                vcp = st.selectbox("Validez del equipo", VAL_ESTADOS,
                    index=VAL_ESTADOS.index(seg.get("val_estado_cp"))
                          if seg.get("val_estado_cp") in VAL_ESTADOS else 0,
                    format_func=lambda x: LABEL_VALIDEZ.get(x, x),
                    key=f"{prefix}_vcp_{reunion_id}_{i}", label_visibility="collapsed")
            with e2:
                st.markdown(mini_label("Criterios BANT"), unsafe_allow_html=True)
                bcp = st.multiselect("BANT equipo", ["B", "A", "N", "T"],
                    default=bant_actual,
                    placeholder="Opcional", key=f"{prefix}_bcp_{reunion_id}_{i}",
                    label_visibility="collapsed")
            e3, e4 = st.columns(2)
            with e3:
                st.markdown(mini_label("Estado de la reunión"), unsafe_allow_html=True)
                sr = st.selectbox("Estado de la reunión", STATUS_REUNION,
                    index=STATUS_REUNION.index(status_actual)
                          if status_actual in STATUS_REUNION else 0,
                    format_func=lambda x: LABEL_STATUS.get(x, x),
                    key=f"{prefix}_sr_{reunion_id}_{i}", label_visibility="collapsed")
            with e4:
                st.markdown(mini_label("Forzar validez final"), unsafe_allow_html=True)
                vf = st.selectbox("Forzar validez final", _OVERRIDE_OPTS, index=0,
                    key=f"{prefix}_vf_{reunion_id}_{i}",
                    help="Dejar en automática salvo que quieras fijarla a mano.",
                    label_visibility="collapsed")
            st.markdown(mini_label("Comentario de respaldo (lo ve el cliente)"), unsafe_allow_html=True)
            coment_cp = st.text_input("Comentario de respaldo", value=seg.get("comentario_cp") or "",
                key=f"{prefix}_ccp_{reunion_id}_{i}", label_visibility="collapsed",
                placeholder="Justifica la evaluación; aparece en el portal del cliente")
            st.markdown(mini_label("Información para reunión (visible al cliente)"), unsafe_allow_html=True)
            info_manual = st.text_area(
                "Información para reunión",
                value=info_actual,
                key=f"{prefix}_info_{reunion_id}_{i}",
                label_visibility="collapsed",
                placeholder="Completar preparación, contexto y antecedentes útiles para la reunión.",
            )
            if cliente_slug == "gbs":
                icp_edit = st.checkbox(
                    "Cumple ICP",
                    value=bool(icp_actual),
                    key=f"{prefix}_icp_{reunion_id}_{i}",
                    help="Antecedente de evaluación; no decide automáticamente la validez.",
                )
            else:
                icp_edit = icp_actual
            e5, e6 = st.columns(2)
            with e5:
                st.markdown(mini_label("Próximo paso (interno)"), unsafe_allow_html=True)
                proximo = st.text_input("Próximo paso", value=seg.get("proximo_paso") or "",
                    key=f"{prefix}_pp_{reunion_id}_{i}", label_visibility="collapsed")
            with e6:
                st.markdown(mini_label("Notas internas (no las ve el cliente)"), unsafe_allow_html=True)
                notas = st.text_input("Notas internas", value=seg.get("notas_internas") or "",
                    key=f"{prefix}_ni_{reunion_id}_{i}", label_visibility="collapsed")

            # Estado comercial (lo define el cliente — solo lectura para el equipo) + Guardar
            _ec = seg.get("estado_comercial")
            col_ec, col_save = st.columns([3, 1])
            with col_ec:
                st.markdown(
                    f'<div style="font-size:12px;color:#64748b;margin-top:14px">'
                    f'Estado comercial (cliente): <b style="color:#334155">'
                    f'{LABEL_ESTADO_COMERCIAL.get(_ec, "Sin definir") if _ec else "Sin definir"}</b></div>',
                    unsafe_allow_html=True)
            with col_save:
                st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
                guardar = st.button("Guardar", key=f"{prefix}_save_{reunion_id}_{i}",
                                    type="primary", use_container_width=True)

            if guardar:
                old_cp = seg.get("val_estado_cp")
                old_bant = bant_to_list(seg.get("bant_cp"))
                old_info = texto_real(seg.get("informacion_reunion_manual"))
                old_final = seg.get("val_estado_final")
                _gn_cp(reunion_id, cliente_slug, "cp", val_estado=vcp, bant=bcp)
                _ahora = datetime.datetime.now(datetime.timezone.utc).isoformat()
                antecedentes = payload_antecedentes_internos(
                    informacion=info_manual,
                    bant=bcp,
                    icp_cumple=icp_edit,
                )
                _patch = {"status_reunion": sr, "validated_by_cp": "cp",
                          "validated_cp_at": _ahora, "final_override": False,
                          "comentario_cp": coment_cp.strip() or None,
                          "informacion_reunion_manual": antecedentes["informacion_reunion_manual"],
                          "icp_cumple": antecedentes["icp_cumple"],
                          "proximo_paso": proximo.strip() or None,
                          "notas_internas": notas.strip() or None}
                if vf != "(automática)":
                    _patch.update({"val_estado_final": vf, "final_override": True,
                                   "validated_final_by": "CP", "validated_final_at": _ahora})
                save_response = requests.patch(
                    f"{SUPABASE_URL}/rest/v1/seguimiento_reuniones?reunion_id=eq.{reunion_id}",
                    json=_patch,
                    headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                             "Content-Type": "application/json", "Prefer": "return=minimal"},
                    timeout=10)
                if not save_response.ok:
                    fallback_patch = {
                        key: value
                        for key, value in _patch.items()
                        if key not in {"informacion_reunion_manual", "icp_cumple"}
                    }
                    save_response = requests.patch(
                        f"{SUPABASE_URL}/rest/v1/seguimiento_reuniones?reunion_id=eq.{reunion_id}",
                        json=fallback_patch,
                        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                                 "Content-Type": "application/json", "Prefer": "return=minimal"},
                        timeout=10)
                    if save_response.ok and (
                        antecedentes["informacion_reunion_manual"] or antecedentes["icp_cumple"] is not None
                    ):
                        st.warning(
                            "La evaluación se guardó, pero la migración de Información para reunión/ICP "
                            "aún no está aplicada en Supabase."
                        )
                current = {
                    **seg,
                    **_patch,
                    "val_estado_cp": vcp,
                    "bant_cp": ",".join(bcp),
                }
                if vf != "(automática)":
                    current["val_estado_final"] = vf
                recalculated = recalcular_final_y_flags(reunion_id, cliente_slug, fila=current)
                registrar_historial(reunion_id, "status_reunion",
                                    status_actual, sr, "cp", "cp", "seguimiento")
                registrar_historial(reunion_id, "val_estado_cp",
                                    old_cp, vcp, "cp", "cp", "seguimiento")
                registrar_historial(reunion_id, "bant_cp",
                                    ",".join(old_bant), ",".join(bcp), "cp", "cp", "seguimiento")
                registrar_historial(reunion_id, "informacion_reunion_manual",
                                    old_info, info_manual.strip(), "cp", "cp", "seguimiento")
                registrar_historial(reunion_id, "icp_cumple",
                                    seg.get("icp_cumple"), icp_edit, "cp", "cp", "seguimiento")
                registrar_historial(reunion_id, "val_estado_final",
                                    old_final, recalculated["final"], "cp", "cp", "seguimiento")
                st.cache_data.clear()
                st.rerun()

        st.markdown('<div style="margin-bottom:18px"></div>', unsafe_allow_html=True)
    return []  # guardado por fila; cambios masivos descontinuados


def seccion_header(titulo: str, color_a: str, color_b: str) -> None:
    st.markdown(
        f'<div style="background:linear-gradient(135deg,{color_a},{color_b});padding:14px 20px;'
        f'border-radius:10px;margin:20px 0 14px">'
        f'<div style="color:white;font-size:18px;font-weight:700">{titulo}</div></div>',
        unsafe_allow_html=True,
    )


def filtros_seccion(df_base: pd.DataFrame, prefix: str, idx_dia_default: int = 0,
                    banner_bg: str = "#eff6ff", banner_border: str = "#3b82f6",
                    banner_color: str = "#1e40af", banner_label: str = "FILTROS"):
    st.markdown(
        f'<div style="background:{banner_bg};border-left:4px solid {banner_border};'
        f'border-radius:0 8px 8px 0;padding:6px 14px;font-size:11px;font-weight:700;'
        f'color:{banner_color};margin-bottom:10px">{banner_label}</div>',
        unsafe_allow_html=True,
    )

    meses_disp = sorted(df_base["mes"].dropna().unique())
    meses_labels = ["Todos"] + [f"{MESES_ES[p.month-1].capitalize()} {p.year}" for p in meses_disp]

    c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
    with c1:
        mes_label = st.selectbox("Mes", meses_labels, index=0, key=f"{prefix}_mes")

    if mes_label == "Todos":
        df_mes = df_base.copy()
    else:
        mes_period = meses_disp[meses_labels.index(mes_label) - 1]
        df_mes = df_base[df_base["mes"] == mes_period].copy()
    fechas = sorted(df_mes["fecha_d"].dropna().unique())
    dias_opts = ["Todos"] + [formato_dia(d) for d in fechas]

    hoy_local = datetime.date.today()
    if idx_dia_default > 0 and hoy_local in fechas:
        idx_dia_safe = fechas.index(hoy_local) + 1
    else:
        idx_dia_safe = min(idx_dia_default, len(dias_opts) - 1)

    with c2:
        sel_dia = st.selectbox("Día", dias_opts, index=idx_dia_safe, key=f"{prefix}_dia")
    with c3:
        clientes = ["Todos"] + cargar_clientes()
        sel_cliente = st.selectbox("Cliente", clientes, key=f"{prefix}_cliente")
    with c4:
        estados_filter = ["Todos", *ESTADOS_FLUJO]
        sel_estado = st.selectbox(
            "Estado",
            estados_filter,
            format_func=lambda value: "Todos los estados" if value == "Todos" else LABEL_ESTADO_FLUJO[value],
            key=f"{prefix}_estado_f",
        )

    return df_mes, fechas, dias_opts, sel_dia, sel_cliente, sel_estado


def aplicar_filtros(df_mes, fechas, dias_opts, sel_dia, sel_cliente,
                     sel_estado="Todos", final_map=None):
    final_map = final_map or {}
    dff = df_mes.copy()
    if sel_dia != "Todos":
        fecha_sel = fechas[dias_opts.index(sel_dia) - 1]
        dff = dff[dff["fecha_d"] == fecha_sel]
    if sel_cliente != "Todos":
        dff = dff[dff["cliente"] == sel_cliente]
    if sel_estado != "Todos" and not dff.empty:
        dff = dff[dff["_flow"] == sel_estado]
    dff = dff.sort_values("fecha", ascending=False, na_position="last")
    return dff


def filtrar_busqueda(dff: pd.DataFrame, termino: str) -> pd.DataFrame:
    """Filtra por coincidencia en empresa, contacto (nombre/apellido), correo o teléfono."""
    t = (termino or "").strip().lower()
    if not t or dff.empty:
        return dff
    cols = [c for c in ("empresa", "contacto", "email", "telefono", "cargo") if c in dff.columns]
    mask = pd.Series(False, index=dff.index)
    for c in cols:
        mask = mask | dff[c].astype(str).str.lower().str.contains(t, na=False, regex=False)
    return dff[mask]


def _final_de(final_map, rid):
    return str(final_map.get(int(rid), "") or "pendiente")


def run():
    st.markdown("""
    <div style="background:#1e1e2e;padding:20px 28px;border-radius:12px;margin-bottom:20px">
      <div style="color:white;font-size:24px;font-weight:700">Seguimiento Reuniones</div>
      <div style="color:#aaa;font-size:13px">Filtrar por mes, día, cliente o estado. El equipo registra su evaluación; el cliente valida en su portal; la validez final sincroniza ambos.</div>
    </div>""", unsafe_allow_html=True)

    _, col_ref = st.columns([8, 2])
    with col_ref:
        if st.button("Actualizar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    df = cargar_reuniones()
    stages_df = cargar_stages()
    final_map = cargar_validacion_final()

    if df.empty:
        st.info("No hay reuniones cargadas.")
        return
    df = enriquecer_estado_funcional(df)

    seccion_header("Reuniones por cliente", "#065f46", "#10b981")

    df_mes_f, fechas_f, dias_opts_f, sel_dia_f, sel_cliente_f, sel_estado_f = filtros_seccion(
        df, prefix="f", idx_dia_default=0,
        banner_bg="#ecfdf5", banner_border="#10b981", banner_color="#065f46",
        banner_label="FILTROS — mes · día · cliente · estado de validación",
    )

    dff = aplicar_filtros(df_mes_f, fechas_f, dias_opts_f, sel_dia_f, sel_cliente_f,
                          sel_estado=sel_estado_f, final_map=final_map)

    # Buscador: empresa · nombre/apellido · correo · teléfono (filtra sobre lo ya filtrado)
    c_busca, _ = st.columns([3, 1])
    with c_busca:
        termino = st.text_input(
            "Buscar reunión",
            placeholder="Buscar por empresa, nombre, apellido, correo o teléfono",
            label_visibility="collapsed", key="f_busca")
    dff = filtrar_busqueda(dff, termino)
    if termino and termino.strip():
        st.caption(f"{len(dff)} resultado(s) para «{termino.strip()}»")

    # Avance de meta por cliente (validación final)
    st.markdown(resumen_clientes_html(dff, final_map), unsafe_allow_html=True)

    # KPIs principales — todos por VALIDEZ FINAL (consistente con el portal del cliente)
    if dff.empty:
        rids = []
    else:
        rids = [int(r) for r in dff["id"].dropna()]
    n_val  = sum(1 for r in rids if _final_de(final_map, r) == "valida")
    n_nv   = sum(1 for r in rids if _final_de(final_map, r) == "no_valida")
    n_revision = int((dff["_flow"] == "cliente_solicita_revision").sum())
    n_pend_cp = int((dff["_flow"] == "pendiente_evaluacion_cp").sum())

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total reuniones", len(rids))
    k2.metric("Válidas", n_val)
    k3.metric("No válidas", n_nv)
    k4.metric("Solicita revisión", n_revision)
    k5.metric("Pendiente evaluación CP", n_pend_cp)
    st.markdown("")

    if dff.empty:
        st.warning("No hay reuniones con los filtros seleccionados.")
    else:
        render_tabla(dff, stages_df, "f")

    with st.expander("¿Cómo funciona la validación en 3 capas?"):
        st.markdown("""
        **Equipo (CP):** el equipo registra su evaluación de cada reunión (validez + BANT). Queda como respaldo.

        **Cliente:** el cliente solo puede confirmar una evaluación positiva previa o solicitar revisión.

        **Validez final:** Conprospección es la autoridad final. BANT, ICP, evidencia e información de preparación aportan contexto, pero no deciden por sí solos.

        Ambos paneles leen y escriben la misma información: lo que cambia en uno se ve en el otro.
        """)


run()
render_master_user_sidebar()
