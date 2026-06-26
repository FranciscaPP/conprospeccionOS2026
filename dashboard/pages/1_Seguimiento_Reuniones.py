import sys
import html
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
from shared.meeting_scope import ACTIVE_MEETING_CLIENT_NAMES, ACTIVE_MEETING_CLIENT_SLUGS
from shared.metas import meta_de, NOMBRE_A_SLUG
from shared.validacion import (
    ESTATUS_VALIDACION,
    ESTADOS_FLUJO,
    ETAPAS_AGENDA,
    LABEL_ESTATUS_VALIDACION,
    LABEL_ESTADO_FLUJO,
    LABEL_ETAPA_AGENDA,
    STATUS_REUNION,
    VAL_ESTADOS,
    bant_desde_fuentes,
    construir_justificacion,
    derivar_estatus_validacion,
    derivar_estado_flujo,
    derivar_etapa_agenda,
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
    LABEL_VALIDEZ, LABEL_FINAL, LABEL_STATUS, LABEL_ESTADO_COMERCIAL, chip_status,
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

ACTIVE_MEETING_CLIENT_SET = set(ACTIVE_MEETING_CLIENT_SLUGS)
ACTIVE_MEETING_CLIENT_LABELS = list(ACTIVE_MEETING_CLIENT_NAMES.values())

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
def _dk_val(v):
    """Limpia un valor de celda tratando NaN/None/NaT como vacío.

    Ojo: `pd.NaN or ""` devuelve NaN (NaN es truthy en Python), así que el
    patrón `str(x or "")` colapsaba todas las filas con opportunity_id nulo en
    una sola clave ("opp","nan") — esto borraba clientes sin pipeline (p. ej.
    GBS, cuyas reuniones vienen de calendario sin opportunity_id)."""
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s.lower() in ("nan", "none", "nat", "<na>") else s


def _dedup_key(row):
    cid = _dk_val(row.get("ghl_contact_id"))
    if cid:
        return ("contact", cid)
    opp = _dk_val(row.get("opportunity_id"))
    if opp:
        return ("opp", opp)
    email = _dk_val(row.get("email")).lower()
    if email:
        return ("email", email)
    contacto = _dk_val(row.get("contacto")).lower()
    empresa = _dk_val(row.get("empresa")).lower()
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
    if "cliente_slug" in df.columns:
        df = df[df["cliente_slug"].astype(str).str.lower().isin(ACTIVE_MEETING_CLIENT_SET)].copy()
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
            for column in (
                "id", "raw_data", "informacion_reunion", "bant_sdr",
                "recording_url", "transcript_url", "ai_summary", "ai_evidence",
            )
            if column in extras.columns
        ]
        df = df.merge(extras[extra_columns], on="id", how="left", suffixes=("", "_extra"))
        for column in (
            "raw_data", "informacion_reunion", "bant_sdr",
            "recording_url", "transcript_url", "ai_summary", "ai_evidence",
        ):
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
        "?select=id,raw_data,informacion_reunion,bant_sdr,"
        "recording_url,transcript_url,ai_summary,ai_evidence",
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


@st.cache_data(ttl=30)
def cargar_historial(reunion_id: int) -> list[dict]:
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/meeting_status_history"
        f"?select=*&meeting_id=eq.{reunion_id}&order=changed_at.asc",
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
        timeout=15)
    return r.json() if r.ok else []


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
        "solicita_cotizacion": "cotizacion",
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
        source_status = _normalizar_status_interno(row.get("estado_reunion"))
        status = (
            "cotizacion"
            if source_status == "cotizacion"
            else texto_real(seg.get("status_reunion")) or source_status
        )
        _ev = str(row.get("estado_validacion") or "").lower()
        _er = str(row.get("estado_reunion") or "").lower()
        cp = texto_real(seg.get("val_estado_cp")) or (
            "valida" if _ev in {"valida", "reunion_valida"}
            else "no_valida" if _ev in {"no_valida", "reunion_no_valida"}
            else "cancelacion" if ("cancel" in _er or _ev in {"cancelacion", "cancelada"})
            else "espera"
        )
        client = texto_real(seg.get("val_estado_cli")) or "espera"
        if status == "cotizacion":
            cp = "valida"
            final = "valida"
        elif seg.get("val_estado_final") == "valida" and seg.get("flag_meta_countable") is True:
            final = "valida"
        else:
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
        row["_cp"] = cp
        row["_client"] = client
        row["_final"] = final
        row["_agenda_stage"] = derivar_etapa_agenda(
            row.get("fecha_d") or row.get("fecha"),
            status,
        )
        row["_validation_status"] = derivar_estatus_validacion(
            row["_agenda_stage"],
            cp,
            client,
            final,
            flag_disputa=bool(seg.get("flag_disputa")),
        )
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
    slugs = ",".join(ACTIVE_MEETING_CLIENT_SLUGS)
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/clientes?select=nombre,slug&slug=in.({slugs})&order=nombre.asc",
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
        timeout=15,
    )
    if not resp.ok:
        return ACTIVE_MEETING_CLIENT_LABELS
    by_slug = {str(r.get("slug") or ""): r.get("nombre") for r in resp.json()}
    return [by_slug.get(slug) or ACTIVE_MEETING_CLIENT_NAMES[slug] for slug in ACTIVE_MEETING_CLIENT_SLUGS]


@st.cache_data(ttl=30)
def cargar_seg_slug(slug: str) -> dict:
    """Carga seguimiento_reuniones para un slug (cacheado 30 s)."""
    return _cargar_seg(slug)


@st.cache_data(ttl=30)
def cargar_flags_validacion() -> dict:
    """Cuenta flags globales de validación final."""
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/seguimiento_reuniones"
        f"?select=flag_meta_countable,flag_disputa,flag_cliente_pendiente"
        f"&cliente_slug=in.({','.join(ACTIVE_MEETING_CLIENT_SLUGS)})",
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


# SDR asignable a mano desde el panel interno. El SDR "real" viene del contacto
# (vista), pero el equipo puede reasignarlo; el override se guarda en
# seguimiento_reuniones.sdr_override (sync-safe) y NO toca reuniones.sdr_slug.
SDR_EDITABLES = [
    ("yanina_olivo", "Yanina Olivo"),
    ("sebastian_gutierrez", "Sebastián Gutiérrez"),
    ("constanza_catalan", "Constanza Catalán"),
    ("mariela_tello", "Mariela Tello"),
    ("luciana_acuna", "Luciana Acuña"),
    ("francisca_polanco", "Francisca Polanco"),
]
SDR_SLUG_A_NOMBRE = {slug: nombre for slug, nombre in SDR_EDITABLES}
SDR_NOMBRE_A_SLUG = {nombre: slug for slug, nombre in SDR_EDITABLES}

_OVERRIDE_OPTS = ["(automática)", "valida", "no_valida", "en_disputa", "excluida", "cancelacion"]


# ─────────────────────────────────────────────────────────────────────────────
# CAPA VISUAL — panel maestro operativo (referencia: mockups + portal GBS pág.12)
# Todo el HTML va por st.markdown(..., unsafe_allow_html=True) y SIN sangría en
# las líneas de contenido, para que Streamlit no lo interprete como bloque de
# código y lo imprima literal.
# ─────────────────────────────────────────────────────────────────────────────

MASTER_UI_CSS = """
<style>
.block-container { padding-top:2.4rem !important; padding-bottom:1rem !important; max-width:1500px; min-width:1120px; }
section.main > div { overflow-x:auto; }
div[data-testid="stVerticalBlock"] { gap:0.55rem; }
div[data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; }
div[data-testid="stHorizontalBlock"] > div { min-width:0 !important; }
.cp-master-top { display:flex; justify-content:space-between; align-items:flex-end; margin:0 0 12px; }
.cp-master-title { font-size:22px; font-weight:800; color:#0f172a; line-height:1.1; }
.cp-master-sub { font-size:12px; color:#64748b; margin-top:2px; }
.cp-master-tag { font-size:12px; font-weight:800; color:#7c3aed; }
.cp-kpi-row { display:flex; flex-wrap:nowrap; gap:10px; margin:6px 0 14px; overflow-x:auto; padding-bottom:4px; }
.cp-kpi-card { background:#fff; border:1px solid #e9eef5; border-left:4px solid var(--accent);
  border-radius:12px; padding:11px 13px; box-shadow:0 1px 2px rgba(15,23,42,.04); flex:1 0 152px; min-width:152px; }
.cp-kpi-label { font-size:12px; color:#64748b; font-weight:600; line-height:1.2; }
.cp-kpi-number { font-size:24px; font-weight:800; color:#0f172a; line-height:1.1; margin-top:3px; }
.cp-kpi-foot { font-size:10px; color:#94a3b8; margin-top:2px; }
.cp-avance-head { display:flex; justify-content:space-between; align-items:center; margin:4px 0 9px; }
.cp-avance-title { font-size:15px; font-weight:800; color:#0f172a; }
.cp-avance-hint { font-size:12px; color:#94a3b8; }
.cp-avance-grid { display:flex; flex-wrap:nowrap; gap:12px; margin-bottom:14px; overflow-x:auto; padding-bottom:4px; }
.cp-avance-card { background:#fff; border:1px solid #e9eef5; border-radius:12px;
  padding:13px 15px; box-shadow:0 1px 2px rgba(15,23,42,.04); flex:1 0 280px; min-width:280px; }
.cp-avance-top { display:flex; align-items:center; gap:11px; }
.cp-avance-logo { width:40px; height:40px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  background:var(--soft); color:var(--accent); font-weight:800; font-size:14px; flex:0 0 auto; }
.cp-avance-name { font-size:15px; font-weight:800; color:#0f172a; }
.cp-avance-num { font-size:12px; color:#64748b; }
.cp-avance-track { height:8px; background:#eef2f7; border-radius:6px; overflow:hidden; margin:9px 0 4px; }
.cp-avance-fill { display:block; height:8px; background:#16a34a; border-radius:6px; }
.cp-avance-pctrow { display:flex; justify-content:flex-end; }
.cp-avance-pct { font-size:12px; font-weight:800; color:#16a34a; }
.cp-status-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin:8px 0 6px; }
.cp-status-cell { background:#f8fafc; border:1px solid #eef2f7; border-radius:10px; padding:8px 10px; }
.cp-status-k { font-size:10px; font-weight:800; letter-spacing:.4px; text-transform:uppercase; color:#94a3b8; }
.cp-status-v { font-size:13px; font-weight:700; color:#0f172a; margin-top:2px; }
.cp-info-grid { display:grid; grid-template-columns:1fr 1fr; gap:6px 16px; margin:4px 0 6px; }
.cp-info-k { font-size:11px; color:#64748b; }
.cp-info-v { font-size:13px; font-weight:600; color:#0f172a; }
div[data-testid="stDialog"] { justify-content:flex-end !important; align-items:stretch !important; padding:0 !important; }
div[data-testid="stDialog"] div[role="dialog"] {
  position:fixed !important; top:0 !important; right:0 !important; left:auto !important; transform:none !important;
  width:min(580px,100vw) !important; max-width:min(580px,100vw) !important; height:100vh !important;
  max-height:100vh !important; margin:0 !important; border-radius:16px 0 0 16px !important; overflow-y:auto !important; }
</style>
"""


def render_master_header() -> None:
    st.markdown(MASTER_UI_CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="cp-master-top">'
        '<div><div class="cp-master-title">Seguimiento de Reuniones</div>'
        '<div class="cp-master-sub">Panel maestro operativo · el equipo evalúa, el cliente valida, la validez final sincroniza ambos</div></div>'
        '<div class="cp-master-tag">GBS · Clickie · BambuTech</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _pct_foot(part: int, total: int) -> str:
    return "0% del total" if total <= 0 else f"{round(part / total * 100)}% del total"


def render_kpi_cards(counts: dict) -> None:
    total = counts.get("total", 0)
    data = [
        ("Total reuniones", counts.get("total", 0), "Todas las reuniones", "#2563eb"),
        ("Válidas", counts.get("validas", 0), _pct_foot(counts.get("validas", 0), total), "#16a34a"),
        ("Pendiente CP", counts.get("pend_cp", 0), "Por evaluar", "#f59e0b"),
        ("Pendiente cliente", counts.get("pend_cli", 0), "Por confirmar", "#2563eb"),
        ("En revisión", counts.get("revision", 0), "Solicita ajustes", "#7c3aed"),
        ("Reagenda", counts.get("reagenda", 0), "Reprogramadas", "#0891b2"),
        ("No válidas", counts.get("no_validas", 0), "No cumplen", "#dc2626"),
    ]
    cards = "".join(
        f'<div class="cp-kpi-card" style="--accent:{accent}">'
        f'<div class="cp-kpi-label">{html.escape(label)}</div>'
        f'<div class="cp-kpi-number">{value}</div>'
        f'<div class="cp-kpi-foot">{html.escape(foot)}</div></div>'
        for label, value, foot, accent in data
    )
    st.markdown(f'<div class="cp-kpi-row">{cards}</div>', unsafe_allow_html=True)


def cliente_initials(nombre: str) -> str:
    cleaned = (nombre or "").replace("LOGISTICS", "").strip()
    if not cleaned:
        return "?"
    words = cleaned.split()
    if len(words) == 1:
        return words[0][:2].upper()
    return "".join(w[0] for w in words[:2]).upper()


def render_avance_clientes(df_base: pd.DataFrame, final_map: dict) -> None:
    mes_actual = datetime.date.today().month
    anio_actual = datetime.date.today().year

    def _es_final_valida(rid):
        return str(final_map.get(int(rid), "")).lower() in ("valida", "reunion_valida")

    cards = ""
    nombres = [c for c in COLORES_CLIENTE if c in df_base["cliente"].astype(str).str.upper().unique()]
    for nombre in nombres:
        sub = df_base[df_base["cliente"].astype(str).str.upper() == nombre]
        slug = NOMBRE_A_SLUG.get(nombre, "")
        meta = meta_de(slug)
        if sub.empty or not meta:
            continue
        if meta["tipo"] == "mensual":
            sub_meta = sub[(sub["fecha"].dt.month == mes_actual) & (sub["fecha"].dt.year == anio_actual)]
            validas = int(sub_meta["id"].apply(_es_final_valida).sum()) if not sub_meta.empty else 0
            sufijo = " este mes"
        else:
            validas = int(sub["id"].apply(_es_final_valida).sum())
            sufijo = ""
        meta_n = int(meta["validas"])
        pct = 0 if meta_n <= 0 else min(round(validas / meta_n * 100), 100)
        col = COLORES_CLIENTE[nombre]
        label = html.escape(str(sub["cliente"].iloc[0]))
        cards += (
            '<div class="cp-avance-card">'
            '<div class="cp-avance-top">'
            f'<div class="cp-avance-logo" style="--accent:{col["border"]};--soft:{col["bg"]}">{cliente_initials(nombre)}</div>'
            f'<div><div class="cp-avance-name">{label}</div>'
            f'<div class="cp-avance-num">{validas} / {meta_n}{html.escape(sufijo)}</div></div></div>'
            f'<div class="cp-avance-track"><span class="cp-avance-fill" style="width:{pct}%"></span></div>'
            f'<div class="cp-avance-pctrow"><span class="cp-avance-pct">{pct}%</span></div>'
            '</div>'
        )
    st.markdown(
        '<div class="cp-avance-head"><div class="cp-avance-title">Avance por cliente</div>'
        '<div class="cp-avance-hint">válidas (validación final) / meta</div></div>'
        f'<div class="cp-avance-grid">{cards}</div>',
        unsafe_allow_html=True,
    )


_VALID_SET = {"evaluacion_cerrada_valida", "cotizacion_valida"}


def contar_kpis(dff: pd.DataFrame) -> dict:
    if dff.empty or "_validation_status" not in dff.columns:
        return {k: 0 for k in
                ("total", "validas", "pend_cp", "pend_cli", "revision", "reagenda", "no_validas")}
    vs = dff["_validation_status"]
    return {
        "total": len(dff),
        "validas": int(vs.isin(_VALID_SET).sum()),
        "pend_cp": int((vs == "pendiente_evaluacion_cp").sum()),
        "pend_cli": int((vs == "pendiente_confirmacion_cliente").sum()),
        "revision": int((vs == "cliente_solicita_revision").sum()),
        "reagenda": int((vs == "reagendar").sum()),
        "no_validas": int((vs == "evaluacion_cerrada_no_valida").sum()),
    }


def estado_operativo_parts(row: dict, seg: dict) -> dict:
    seg = seg or {}
    return {
        "estado_reunion": row.get("_status") or "agendada",
        "evaluacion_cp": texto_real(seg.get("val_estado_cp")) or row.get("_cp") or "espera",
        "validacion_cliente": texto_real(seg.get("val_estado_cli")) or row.get("_client") or "espera",
        "validez_final": row.get("_final") or "pendiente",
    }


def label_estado_reunion(value: str) -> str:
    return LABEL_STATUS.get(value, value or "Sin información")


def label_evaluacion_cp(value: str) -> str:
    return LABEL_VALIDEZ.get(value, value or "En espera")


def label_validacion_cliente(value: str) -> str:
    return LABEL_VALIDEZ.get(value, value or "En espera")


def label_validez_final(value: str) -> str:
    return LABEL_FINAL.get(value, value or "Pendiente")


def filtros_operativos(df_base: pd.DataFrame, prefix: str) -> pd.DataFrame:
    c1, c2, c3, c4, c5, c6 = st.columns([2.4, 1.7, 1.5, 1.7, 1.9, 0.9])
    with c1:
        termino = st.text_input(
            "Buscar", placeholder="Empresa, contacto o cargo…", key=f"{prefix}_search")
    fechas_validas = df_base["fecha_d"].dropna()
    min_d = fechas_validas.min() if not fechas_validas.empty else datetime.date.today()
    max_d = fechas_validas.max() if not fechas_validas.empty else datetime.date.today()
    with c2:
        rango = st.date_input(
            "Rango de fechas", value=(min_d, max_d), format="DD/MM/YYYY", key=f"{prefix}_rango")
    with c3:
        clientes = ["Todo"] + cargar_clientes()
        sel_cliente = st.selectbox("Cliente", clientes, key=f"{prefix}_cliente")
    with c4:
        estados = ["Todo", *STATUS_REUNION]
        sel_estado = st.selectbox(
            "Estado de reunión", estados, key=f"{prefix}_estado",
            format_func=lambda x: "Todo" if x == "Todo" else LABEL_STATUS.get(x, x))
    with c5:
        validaciones = ["Todo", *ESTATUS_VALIDACION]
        sel_val = st.selectbox(
            "Estatus de validación", validaciones, key=f"{prefix}_validacion",
            format_func=lambda x: "Todo" if x == "Todo" else LABEL_ESTATUS_VALIDACION.get(x, x))
    with c6:
        st.markdown('<div style="height:1.75rem"></div>', unsafe_allow_html=True)
        if st.button("Limpiar", use_container_width=True, key=f"{prefix}_limpiar"):
            for suf in ("search", "rango", "cliente", "estado", "validacion"):
                st.session_state.pop(f"{prefix}_{suf}", None)
            st.rerun()

    dff = df_base.copy()
    if isinstance(rango, (tuple, list)) and len(rango) == 2:
        ini, fin = rango
        dff = dff[(dff["fecha_d"] >= ini) & (dff["fecha_d"] <= fin)]
    if sel_cliente != "Todo":
        dff = dff[dff["cliente"] == sel_cliente]
    if sel_estado != "Todo" and "_status" in dff.columns:
        dff = dff[dff["_status"] == sel_estado]
    if sel_val != "Todo" and "_validation_status" in dff.columns:
        dff = dff[dff["_validation_status"] == sel_val]
    dff = filtrar_busqueda(dff, termino)
    return dff.sort_values("fecha", ascending=False, na_position="last")


def filtrar_busqueda(dff: pd.DataFrame, termino: str) -> pd.DataFrame:
    """Filtra por coincidencia en empresa, contacto, correo, teléfono o cargo."""
    t = (termino or "").strip().lower()
    if not t or dff.empty:
        return dff
    cols = [c for c in ("empresa", "contacto", "email", "telefono", "cargo") if c in dff.columns]
    mask = pd.Series(False, index=dff.index)
    for c in cols:
        mask = mask | dff[c].astype(str).str.lower().str.contains(t, na=False, regex=False)
    return dff[mask]


def _chip_style(kind: str, value: str) -> tuple[str, str]:
    normalized = str(value or "").lower()
    if kind == "status":
        if normalized in {"realizada", "completed"}:
            return "#dcfce7", "#166534"
        if "agendada" in normalized or "futura" in normalized:
            return "#dbeafe", "#1d4ed8"
        if "cancel" in normalized or "no_asistio" in normalized:
            return "#fee2e2", "#991b1b"
        if "reagend" in normalized:
            return "#ffedd5", "#9a3412"
        if "cotizacion" in normalized:
            return "#ede9fe", "#6d28d9"
    if normalized in {"valida", "reunion_valida"}:
        return "#dcfce7", "#166534"
    if normalized in {"no_valida", "reunion_no_valida", "cancelacion"}:
        return "#fee2e2", "#991b1b"
    if "revision" in normalized or "requiere" in normalized:
        return "#ede9fe", "#6d28d9"
    if "espera" in normalized or "pendiente" in normalized:
        return "#fef3c7", "#b45309"
    return "#f1f5f9", "#475569"


def _chip_html(label: str, bg: str, color: str) -> str:
    return (
        f'<span class="cp-table-chip" style="background:{bg};color:{color}">'
        f'{html.escape(label)}</span>'
    )


def render_tabla(dff: pd.DataFrame, prefix: str):
    """Tabla HTML dinamica basada en el mockup, con link de detalle por reunion."""
    if dff.empty:
        return None
    table_css = """
<style>
.cp-html-table-wrap{border:1px solid #e5e7eb;border-radius:12px;overflow:auto;max-height:620px;background:#fff}
.cp-html-table{width:100%;border-collapse:separate;border-spacing:0;min-width:1120px;font-size:13px;color:#0f172a}
.cp-html-table thead th{position:sticky;top:0;z-index:2;background:#f8fafc;border-bottom:1px solid #e5e7eb;color:#334155;font-size:12px;font-weight:850;text-align:left;padding:11px 12px;white-space:nowrap}
.cp-html-table tbody td{border-bottom:1px solid #f1f5f9;padding:12px;vertical-align:middle;white-space:nowrap;max-width:190px;overflow:hidden;text-overflow:ellipsis}
.cp-html-table tbody tr:hover{background:#fafafa}
.cp-html-date{font-weight:750;color:#0f172a}
.cp-html-time{color:#64748b;font-size:12px;margin-top:2px}
.cp-html-client{font-weight:800;color:#0f172a}
.cp-html-meta{display:inline-block;margin-top:4px;background:#f1f5f9;color:#64748b;border-radius:7px;padding:2px 7px;font-size:11px}
.cp-table-chip{display:inline-flex;align-items:center;justify-content:center;border-radius:8px;padding:5px 10px;font-size:12px;font-weight:850;white-space:nowrap}
.cp-detail-link{display:inline-flex;align-items:center;justify-content:center;border:1px solid #c4b5fd;color:#6d28d9;border-radius:8px;padding:6px 10px;text-decoration:none;font-weight:850;font-size:12px;background:#fff}
.cp-detail-link:hover{background:#f5f3ff}
</style>
"""
    rows = []
    for _, row in dff.iterrows():
        rid = int(row.get("id", 0))
        seg = row.get("_seg") or {}
        parts = estado_operativo_parts(row, seg)
        fecha = pd.to_datetime(row.get("fecha"), errors="coerce")
        fecha_txt = "-" if pd.isna(fecha) else fecha.strftime("%d/%m/%Y")
        hora_txt = str(row.get("hora") or "")[:5]
        cliente = str(row.get("cliente") or "-")
        meta = meta_de(str(row.get("cliente_slug") or ""))
        meta_txt = f"Meta: {meta['validas']}" if meta else ""
        sdr_ovr = texto_real(seg.get("sdr_override"))
        sdr = SDR_SLUG_A_NOMBRE.get(sdr_ovr, str(row.get("sdr") or "Sin asignar"))
        status_label = label_estado_reunion(parts["estado_reunion"])
        cp_label = label_evaluacion_cp(parts["evaluacion_cp"])
        cli_label = label_validacion_cliente(parts["validacion_cliente"])
        status_bg, status_color = _chip_style("status", parts["estado_reunion"])
        cp_bg, cp_color = _chip_style("cp", parts["evaluacion_cp"])
        cli_bg, cli_color = _chip_style("cli", parts["validacion_cliente"])
        rows.append(
            "<tr>"
            f"<td><div class='cp-html-date'>{html.escape(fecha_txt)}</div><div class='cp-html-time'>{html.escape(hora_txt)}</div></td>"
            f"<td><div class='cp-html-client'>{html.escape(cliente)}</div><div class='cp-html-meta'>{html.escape(meta_txt)}</div></td>"
            f"<td>{html.escape(sdr)}</td>"
            f"<td title='{html.escape(str(row.get('empresa') or '-').title())}'>{html.escape(str(row.get('empresa') or '-').title())}</td>"
            f"<td title='{html.escape(str(row.get('contacto') or '-').title())}'>{html.escape(str(row.get('contacto') or '-').title())}</td>"
            f"<td title='{html.escape(str(row.get('cargo') or '-').title())}'>{html.escape(str(row.get('cargo') or '-').title())}</td>"
            f"<td>{_chip_html(status_label, status_bg, status_color)}</td>"
            f"<td>{_chip_html(cp_label, cp_bg, cp_color)}</td>"
            f"<td>{_chip_html(cli_label, cli_bg, cli_color)}</td>"
            f"<td><a class='cp-detail-link' href='?rid={rid}'>Ver detalle</a></td>"
            "</tr>"
        )
    table = (
        table_css
        + "<div class='cp-html-table-wrap'><table class='cp-html-table'>"
        + "<thead><tr>"
        + "<th>Fecha</th><th>Cliente</th><th>SDR</th><th>Empresa</th><th>Contacto</th><th>Cargo</th>"
        + "<th>Estado reunion</th><th>Evaluacion CP</th><th>Validacion cliente</th><th>Ver detalle</th>"
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )
    st.markdown(table, unsafe_allow_html=True)

    selected_raw = st.query_params.get("rid")
    try:
        selected = int(selected_raw) if selected_raw else None
    except (TypeError, ValueError):
        selected = None
    if selected in set(dff["id"].astype(int)):
        return selected
    return None


def render_status_summary(parts: dict) -> None:
    st.markdown(
        '<div class="cp-status-grid">'
        f'<div class="cp-status-cell"><div class="cp-status-k">Estado reunión</div>'
        f'<div class="cp-status-v">{html.escape(label_estado_reunion(parts["estado_reunion"]))}</div></div>'
        f'<div class="cp-status-cell"><div class="cp-status-k">Evaluación CP</div>'
        f'<div class="cp-status-v">{html.escape(label_evaluacion_cp(parts["evaluacion_cp"]))}</div></div>'
        f'<div class="cp-status-cell"><div class="cp-status-k">Validación cliente</div>'
        f'<div class="cp-status-v">{html.escape(label_validacion_cliente(parts["validacion_cliente"]))}</div></div>'
        f'<div class="cp-status-cell"><div class="cp-status-k">Validez final</div>'
        f'<div class="cp-status-v">{html.escape(label_validez_final(parts["validez_final"]))}</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _info_grid(row: dict) -> str:
    pares = [
        ("Empresa", str(row.get("empresa") or "—").title()),
        ("Contacto", str(row.get("contacto") or "—").title()),
        ("Cargo", str(row.get("cargo") or "—").title()),
        ("Email", str(row.get("email") or "—")),
        ("Teléfono", str(row.get("telefono") or "—")),
        ("País", str(row.get("pais") or "—")),
    ]
    celdas = "".join(
        f'<div><div class="cp-info-k">{html.escape(k)}</div>'
        f'<div class="cp-info-v">{html.escape(v)}</div></div>'
        for k, v in pares
    )
    return f'<div class="cp-info-grid">{celdas}</div>'


def render_historial(reunion_id: int) -> None:
    eventos = cargar_historial(reunion_id)
    if not eventos:
        st.caption("Sin historial de cambios registrado.")
        return
    etiquetas = {
        "val_estado_cp": "Evaluación Conprospección",
        "val_estado_cli": "Respuesta del cliente",
        "val_estado_final": "Validez final",
        "bant_cp": "BANT actualizado",
        "status_reunion": "Estado de reunión",
        "informacion_reunion_manual": "Información para reunión",
        "icp_cumple": "Antecedente ICP",
        "sdr_override": "SDR reasignado",
    }
    lineas = []
    for ev in eventos:
        when = pd.to_datetime(ev.get("changed_at"), errors="coerce", utc=True)
        when_txt = "" if pd.isna(when) else when.strftime("%d/%m/%Y %H:%M")
        campo = etiquetas.get(texto_real(ev.get("field_changed")), texto_real(ev.get("field_changed")) or "Actualización")
        nuevo = texto_real(ev.get("new_value"))
        lineas.append(
            f'<div style="display:grid;grid-template-columns:120px 1fr;gap:8px;padding:6px 0;border-top:1px solid #f1f5f9">'
            f'<span style="font-size:11px;color:#94a3b8;font-weight:700">{html.escape(when_txt)}</span>'
            f'<span><b style="font-size:13px;color:#334155">{html.escape(campo)}</b>'
            f'<br><span style="font-size:12px;color:#64748b">{html.escape(nuevo)}</span></span></div>'
        )
    st.markdown("".join(lineas), unsafe_allow_html=True)


def guardar_evaluacion(reunion_id, cliente_slug, seg, status_actual, *,
                       vcp, bcp, sr, vf, sdr_sel, sdr_raw, info_manual, icp_edit,
                       coment_cp, proximo, notas) -> bool:
    old_cp = seg.get("val_estado_cp")
    old_bant = bant_to_list(seg.get("bant_cp"))
    old_info = texto_real(seg.get("informacion_reunion_manual"))
    old_final = seg.get("val_estado_final")
    _gn_cp(reunion_id, cliente_slug, "cp", val_estado=vcp, bant=bcp)
    ahora = datetime.datetime.now(datetime.timezone.utc).isoformat()
    antecedentes = payload_antecedentes_internos(
        informacion=info_manual, bant=bcp, icp_cumple=icp_edit)
    patch = {"status_reunion": sr, "validated_by_cp": "cp",
             "validated_cp_at": ahora, "final_override": False,
             "comentario_cp": coment_cp.strip() or None,
             "informacion_reunion_manual": antecedentes["informacion_reunion_manual"],
             "icp_cumple": antecedentes["icp_cumple"],
             "proximo_paso": proximo.strip() or None,
             "notas_internas": notas.strip() or None}
    if sdr_sel != sdr_raw and sdr_sel in SDR_NOMBRE_A_SLUG:
        patch["sdr_override"] = SDR_NOMBRE_A_SLUG[sdr_sel]
    if vf != "(automática)":
        patch.update({"val_estado_final": vf, "final_override": True,
                      "validated_final_by": "CP", "validated_final_at": ahora})
    resp = requests.patch(
        f"{SUPABASE_URL}/rest/v1/seguimiento_reuniones?reunion_id=eq.{reunion_id}",
        json=patch,
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                 "Content-Type": "application/json", "Prefer": "return=minimal"},
        timeout=10)
    if not resp.ok:
        fallback = {k: v for k, v in patch.items()
                    if k not in {"informacion_reunion_manual", "icp_cumple"}}
        resp = requests.patch(
            f"{SUPABASE_URL}/rest/v1/seguimiento_reuniones?reunion_id=eq.{reunion_id}",
            json=fallback,
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                     "Content-Type": "application/json", "Prefer": "return=minimal"},
            timeout=10)
        if resp.ok and (antecedentes["informacion_reunion_manual"] or antecedentes["icp_cumple"] is not None):
            st.warning("La evaluación se guardó, pero la migración de Información/ICP aún no está aplicada en Supabase.")
    current = {**seg, **patch, "val_estado_cp": vcp, "bant_cp": ",".join(bcp)}
    if vf != "(automática)":
        current["val_estado_final"] = vf
    recalculated = recalcular_final_y_flags(reunion_id, cliente_slug, fila=current)
    registrar_historial(reunion_id, "status_reunion", status_actual, sr, "cp", "cp", "seguimiento")
    registrar_historial(reunion_id, "val_estado_cp", old_cp, vcp, "cp", "cp", "seguimiento")
    registrar_historial(reunion_id, "bant_cp", ",".join(old_bant), ",".join(bcp), "cp", "cp", "seguimiento")
    registrar_historial(reunion_id, "informacion_reunion_manual", old_info, info_manual.strip(), "cp", "cp", "seguimiento")
    registrar_historial(reunion_id, "icp_cumple", seg.get("icp_cumple"), icp_edit, "cp", "cp", "seguimiento")
    registrar_historial(reunion_id, "val_estado_final", old_final, recalculated["final"], "cp", "cp", "seguimiento")
    return bool(resp.ok)


@st.dialog("Detalle de reunión")
def abrir_detalle(row: dict):
    reunion_id = int(row.get("id", 0))
    cliente_slug = str(row.get("cliente_slug") or "")
    cliente_val = str(row.get("cliente") or "")
    seg = row.get("_seg") or {}
    parts = estado_operativo_parts(row, seg)
    status_actual = parts["estado_reunion"]
    is_quote = cliente_slug == "gbs" and row.get("_agenda_stage") == "cotizacion"
    sdr_raw = str(row.get("sdr") or "Sin asignar")
    sdr_ovr = texto_real(seg.get("sdr_override"))
    if sdr_ovr:
        sdr_raw = SDR_SLUG_A_NOMBRE.get(sdr_ovr, sdr_raw)

    st.markdown(MASTER_UI_CSS, unsafe_allow_html=True)
    render_status_summary(parts)
    st.caption(f"{cliente_val} · {formato_dia(row.get('fecha'))} · {str(row.get('hora') or '—')[:5]}")

    tab_info, tab_eval, tab_evid, tab_just, tab_hist = st.tabs(
        ["Información", "Evaluación CP", "Evidencia", "Justificación", "Historial"])

    bant_actual = bant_desde_fuentes(row, seg)
    info_actual = informacion_reunion(row, seg)
    if is_quote and not info_actual:
        info_actual = texto_real(row.get("observacion"))
    icp_actual = icp_gbs(status_actual, seg.get("icp_cumple")) if cliente_slug == "gbs" else seg.get("icp_cumple")

    with tab_info:
        st.markdown("**Contacto y empresa**")
        st.markdown(_info_grid(row), unsafe_allow_html=True)
        st.markdown(mini_label("Información para reunión (visible al cliente)"), unsafe_allow_html=True)
        st.text_area(
            "Información para reunión", value=info_actual, height=120,
            label_visibility="collapsed", key=f"d_info_{reunion_id}",
            placeholder="Si la plataforma no la trajo desde el origen, complétala aquí.")

    with tab_eval:
        st.markdown(banner_final(parts["validez_final"]), unsafe_allow_html=True)
        e1, e2 = st.columns(2)
        with e1:
            st.markdown(mini_label("Validez del equipo"), unsafe_allow_html=True)
            vcp_actual = "valida" if is_quote else parts["evaluacion_cp"]
            st.selectbox(
                "Validez del equipo", VAL_ESTADOS,
                index=VAL_ESTADOS.index(vcp_actual) if vcp_actual in VAL_ESTADOS else 0,
                format_func=lambda x: LABEL_VALIDEZ.get(x, x), disabled=is_quote,
                key=f"d_vcp_{reunion_id}", label_visibility="collapsed")
        with e2:
            st.markdown(mini_label("Criterios BANT"), unsafe_allow_html=True)
            st.multiselect(
                "BANT", ["B", "A", "N", "T"], default=bant_actual,
                placeholder="Completar/forzar", key=f"d_bcp_{reunion_id}",
                label_visibility="collapsed")
        e3, e4 = st.columns(2)
        with e3:
            st.markdown(mini_label("SDR asignado"), unsafe_allow_html=True)
            nombres = [n for _, n in SDR_EDITABLES]
            opts = nombres if sdr_raw in nombres else [sdr_raw, *nombres]
            st.selectbox(
                "SDR asignado", opts, index=opts.index(sdr_raw),
                key=f"d_sdr_{reunion_id}", label_visibility="collapsed",
                help="Viene del contacto; cámbialo si corresponde otro SDR.")
        with e4:
            st.markdown(mini_label("Cumple ICP"), unsafe_allow_html=True)
            if cliente_slug == "gbs":
                st.checkbox("Cumple ICP", value=bool(icp_actual), key=f"d_icp_{reunion_id}")
            else:
                st.caption("Cumple" if icp_actual else "No definido")
        with st.expander("Ajustes avanzados (estado de agenda · forzar validez final)"):
            a1, a2 = st.columns(2)
            with a1:
                st.markdown(mini_label("Etapa de agenda"), unsafe_allow_html=True)
                st.selectbox(
                    "Etapa de agenda", STATUS_REUNION,
                    index=STATUS_REUNION.index(status_actual) if status_actual in STATUS_REUNION else 0,
                    format_func=lambda x: LABEL_STATUS.get(x, x), disabled=is_quote,
                    key=f"d_sr_{reunion_id}", label_visibility="collapsed")
            with a2:
                st.markdown(mini_label("Forzar validez final"), unsafe_allow_html=True)
                st.selectbox(
                    "Forzar validez final", _OVERRIDE_OPTS, index=0,
                    format_func=lambda x: LABEL_FINAL.get(x, x),
                    help="Dejar en automática salvo que quieras fijarla a mano.",
                    key=f"d_vf_{reunion_id}", label_visibility="collapsed")

    with tab_evid:
        recording = texto_real(row.get("recording_url")) or texto_real(seg.get("recording_url"))
        transcript = texto_real(row.get("transcript_url")) or texto_real(seg.get("transcript_url"))
        confirmation = (texto_real(row.get("ai_summary")) or texto_real(seg.get("ai_summary"))
                        or texto_real(row.get("ai_evidence")) or texto_real(seg.get("ai_evidence")))
        if is_quote:
            st.info("Cotización válida automáticamente por interés inmediato y traspaso al equipo comercial del cliente.")
        elif any((recording, transcript, confirmation)):
            cev = st.columns(2)
            with cev[0]:
                if recording:
                    st.link_button("Abrir grabación", recording, use_container_width=True)
                else:
                    st.button("Grabación no disponible", disabled=True, use_container_width=True, key=f"d_norec_{reunion_id}")
            with cev[1]:
                if transcript:
                    st.link_button("Abrir transcripción", transcript, use_container_width=True)
                else:
                    st.button("Transcripción no disponible", disabled=True, use_container_width=True, key=f"d_notr_{reunion_id}")
            if confirmation:
                st.markdown(mini_label("Resumen de la reunión (automático, solo lectura)"), unsafe_allow_html=True)
                st.write(confirmation)
        else:
            st.caption("Sin evidencia enlazada.")

    with tab_just:
        justificacion = construir_justificacion(
            st.session_state.get(f"d_vcp_{reunion_id}", parts["evaluacion_cp"]),
            icp=icp_actual,
            bant=st.session_state.get(f"d_bcp_{reunion_id}", bant_actual),
            evidencia=any(seg.get(f) for f in ("recording_url", "transcript_url", "ai_summary", "ai_evidence")),
            tiene_informacion=bool((info_actual or "").strip()),
        )
        st.markdown(mini_label("Justificación sugerida (referencia)"), unsafe_allow_html=True)
        st.caption(justificacion or "Completa los antecedentes para generar una sugerencia.")
        st.markdown(mini_label("Justificación (visible al cliente)"), unsafe_allow_html=True)
        st.text_area(
            "Justificación", value=seg.get("comentario_cp") or "", height=90,
            label_visibility="collapsed", key=f"d_ccp_{reunion_id}",
            placeholder="Ej.: el cliente cambió la reunión sin aviso y no fue posible seguimiento.")
        j1, j2 = st.columns(2)
        with j1:
            st.markdown(mini_label("Próximo paso (interno)"), unsafe_allow_html=True)
            st.text_input("Próximo paso", value=seg.get("proximo_paso") or "",
                          label_visibility="collapsed", key=f"d_pp_{reunion_id}")
        with j2:
            st.markdown(mini_label("Notas internas (privadas)"), unsafe_allow_html=True)
            st.text_input("Notas internas", value=seg.get("notas_internas") or "",
                          label_visibility="collapsed", key=f"d_ni_{reunion_id}")
        _ec = seg.get("estado_comercial")
        st.caption(
            "Estado comercial (cliente): "
            + (LABEL_ESTADO_COMERCIAL.get(_ec, "Sin definir") if _ec else "Sin definir"))

    with tab_hist:
        render_historial(reunion_id)

    st.divider()
    cbtn1, cbtn2 = st.columns([1, 1])
    with cbtn1:
        if st.button("Cancelar", use_container_width=True, key=f"d_cancel_{reunion_id}"):
            st.session_state.pop("cp_handled_rid", None)
            st.query_params.clear()
            st.rerun()
    with cbtn2:
        guardar = st.button("Guardar cambios", type="primary", use_container_width=True,
                            key=f"d_save_{reunion_id}")
    if guardar:
        ok = guardar_evaluacion(
            reunion_id, cliente_slug, seg, status_actual,
            vcp=st.session_state.get(f"d_vcp_{reunion_id}", parts["evaluacion_cp"]),
            bcp=st.session_state.get(f"d_bcp_{reunion_id}", bant_actual),
            sr=st.session_state.get(f"d_sr_{reunion_id}", status_actual),
            vf=st.session_state.get(f"d_vf_{reunion_id}", "(automática)"),
            sdr_sel=st.session_state.get(f"d_sdr_{reunion_id}", sdr_raw), sdr_raw=sdr_raw,
            info_manual=st.session_state.get(f"d_info_{reunion_id}", info_actual or ""),
            icp_edit=st.session_state.get(f"d_icp_{reunion_id}", icp_actual) if cliente_slug == "gbs" else icp_actual,
            coment_cp=st.session_state.get(f"d_ccp_{reunion_id}", ""),
            proximo=st.session_state.get(f"d_pp_{reunion_id}", ""),
            notas=st.session_state.get(f"d_ni_{reunion_id}", ""),
        )
        if ok:
            st.success("Cambios guardados.")
            st.session_state.pop("cp_handled_rid", None)
            st.query_params.clear()
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("No fue posible guardar los cambios.")


def _final_de(final_map, rid):
    return str(final_map.get(int(rid), "") or "pendiente")


def run():
    render_master_header()

    df = cargar_reuniones()
    final_map = cargar_validacion_final()
    if df.empty:
        st.info("No hay reuniones cargadas.")
        return
    df = enriquecer_estado_funcional(df)

    dff = filtros_operativos(df, prefix="op")

    ref_col, _ = st.columns([1.1, 7])
    with ref_col:
        if st.button("Actualizar", use_container_width=True, key="op_refresh_final"):
            st.cache_data.clear()
            st.rerun()

    render_kpi_cards(contar_kpis(dff))
    render_avance_clientes(dff if not dff.empty else df, final_map)

    if dff.empty:
        st.warning("No hay reuniones con los filtros seleccionados.")
        return

    st.markdown(
        '<div style="font-size:15px;font-weight:850;color:#0f172a;margin:8px 0">Reuniones</div>',
        unsafe_allow_html=True,
    )
    selected = render_tabla(dff, prefix="op")
    # El detalle se abre por deep-link (?rid=). Recordamos el id ya abierto para que
    # cerrar el modal (incluida la X nativa de Streamlit) no lo reabra en el rerun
    # siguiente; al limpiarse el ?rid (Cancelar/Guardar) se resetea y puede reabrirse.
    if selected is None:
        st.session_state.pop("cp_handled_rid", None)
    elif selected != st.session_state.get("cp_handled_rid"):
        st.session_state["cp_handled_rid"] = selected
        match = dff[dff["id"] == selected]
        if not match.empty:
            abrir_detalle(match.iloc[0].to_dict())


run()
render_master_user_sidebar()
