"""Portal cliente Tiresias — Validación de Reuniones."""
import sys, calendar, requests, pandas as pd, streamlit as st
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from shared.config import supabase_url, supabase_key, ghl_tokens
from portal_auth import require_auth_tiresias, render_client_nav, img_b64

st.set_page_config(page_title="Tiresias — Validación Reuniones", layout="wide", page_icon="")

SUPABASE_URL = supabase_url()
SUPABASE_KEY = supabase_key()
GHL_TOKEN = ghl_tokens().get("tiresias", "")

MESES_ES = ["enero","febrero","marzo","abril","mayo","junio",
            "julio","agosto","septiembre","octubre","noviembre","diciembre"]
DIAS_ES = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]

# Opciones cliente: sin "pendiente" visible
OPCIONES_VAL = {
    "— Seleccionar estado —": "pendiente_validacion",
    "Reunión válida": "valida",
    "Reunión no válida": "no_valida",
    "Reagendar": "reagendar",
}
_VAL_LABEL = {v: k for k, v in OPCIONES_VAL.items()}
_VAL_LABEL.update({
    "reunion_valida": "Reunión válida",
    "reunion_no_valida": "Reunión no válida",
    "reagendada": "Reagendar",
})

ETAPAS = {
    "— Sin etapa —": None,
    "Envió propuesta": "envio_propuesta",
    "Seguimiento propuesta": "seguimiento_propuesta",
    "Sin respuesta post propuesta": "sin_respuesta_post",
    "Avanzando post propuesta": "avanzando_post",
}
_ETAPA_LABEL = {v: k for k, v in ETAPAS.items() if v}

ETAPA_A_CAT = {
    "envio_propuesta": "cotizacion",
    "seguimiento_propuesta": "seguimiento",
    "sin_respuesta_post": "no_contesta",
    "avanzando_post": "responde",
}
VAL_A_CAT = {
    "valida": "reunion_valida",
    "no_valida": "reunion_no_valida",
    "reagendar": "reagendar",
}
ESTADO_STYLE = {
    "valida": ("#dcfce7","#166534","Válida"),
    "reunion_valida": ("#dcfce7","#166534","Válida"),
    "no_valida": ("#fee2e2","#991b1b","No válida"),
    "reunion_no_valida": ("#fee2e2","#991b1b","No válida"),
    "reagendar": ("#ffedd5","#9a3412","Reagendar"),
    "reagendada": ("#ffedd5","#9a3412","Reagendar"),
}

_H = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
_HW = {**_H, "Content-Type": "application/json", "Prefer": "return=minimal"}


def _safe(v, d="—"):
    if v is None or (isinstance(v, float) and pd.isna(v)): return d
    s = str(v).strip(); return s or d

def fmt_fecha(d):
    if d is None or (isinstance(d, float) and pd.isna(d)): return "—"
    dt = pd.to_datetime(str(d))
    return f"{DIAS_ES[dt.weekday()]} {dt.day} de {MESES_ES[dt.month-1]} {dt.year}"

def mes_rango(anio, mes):
    _, ult = calendar.monthrange(anio, mes)
    return f"{anio}-{mes:02d}-01", f"{anio}-{mes:02d}-{ult:02d}"

def badge(txt, bg, color, sz="11px"):
    return (f'<span style="background:{bg};color:{color};padding:2px 10px;'
            f'border-radius:10px;font-size:{sz};font-weight:600;display:inline-block">{txt}</span>')

@st.cache_data(ttl=60)
def cargar_reuniones(fi, ff):
    url = (f"{SUPABASE_URL}/rest/v1/vw_reuniones_semana"
           f"?select=*&cliente_slug=eq.tiresias&fecha=gte.{fi}&fecha=lte.{ff}&order=fecha.asc,hora.asc")
    r = requests.get(url, headers=_H, timeout=15)
    df = pd.DataFrame(r.json() if r.ok and r.json() else [])
    if not df.empty:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.date
        if "nombre" in df.columns and "contacto" not in df.columns:
            df["contacto"] = df["nombre"]
    return df

@st.cache_data(ttl=300)
def cargar_stages():
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/ghl_pipeline_stages"
        f"?select=pipeline_id,pipeline_name,stage_id,stage_category&cliente_slug=eq.tiresias",
        headers=_H, timeout=15)
    if not r.ok: return {}
    rows = r.json()
    src = [x for x in rows if "clickie" in x.get("pipeline_name","").lower()] or rows
    out = {}
    for x in src:
        cat = x.get("stage_category")
        if cat and cat not in out:
            out[cat] = (x["pipeline_id"], x["stage_id"])
    return out

@st.cache_data(ttl=60)
def cargar_seguimiento():
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/tiresias_seguimiento?select=reunion_id,status_comercial,etapa_comercial",
        headers=_H, timeout=15)
    if not r.ok: return {}
    return {int(x["reunion_id"]): x for x in r.json() if x.get("reunion_id")}

def upd_validacion(rid, estado):
    return requests.patch(f"{SUPABASE_URL}/rest/v1/reuniones?id=eq.{rid}",
                          json={"estado_validacion": estado}, headers=_HW, timeout=10).ok

def upd_seguimiento(rid, status, etapa):
    return requests.post(
        f"{SUPABASE_URL}/rest/v1/tiresias_seguimiento",
        json={"reunion_id": rid, "status_comercial": status, "etapa_comercial": etapa,
              "updated_at": datetime.now(timezone.utc).isoformat()},
        headers={**_HW, "Prefer": "resolution=merge-duplicates,return=minimal"}, timeout=10).ok

def mover_ghl(opp_id, pid, sid):
    if not all([opp_id, pid, sid, GHL_TOKEN]): return None
    r = requests.put(f"https://services.leadconnectorhq.com/opportunities/{opp_id}",
                     json={"pipelineId": pid, "pipelineStageId": sid},
                     headers={"Authorization": f"Bearer {GHL_TOKEN}",
                              "Content-Type": "application/json", "Version": "2021-07-28"}, timeout=15)
    return r.ok

def guardar_reunion(rid, opp_id, nuevo_estado, estado_ant, nueva_etapa, etapa_ant,
                    nuevo_status, status_ant, stages):
    ok_total = True
    if nuevo_estado != estado_ant and nuevo_estado != "pendiente_validacion":
        ok = upd_validacion(rid, nuevo_estado)
        ok_total = ok_total and ok
        cat = VAL_A_CAT.get(nuevo_estado)
        if cat and cat in stages:
            mover_ghl(opp_id, *stages[cat])

    seg_cambio = nueva_etapa != etapa_ant or nuevo_status.strip() != status_ant.strip()
    if seg_cambio:
        ok = upd_seguimiento(rid, nuevo_status, nueva_etapa)
        ok_total = ok_total and ok
        if nueva_etapa and nueva_etapa != etapa_ant:
            cat = ETAPA_A_CAT.get(nueva_etapa)
            if cat and cat in stages:
                mover_ghl(opp_id, *stages[cat])
    return ok_total


def buscar_contacto(term: str) -> pd.DataFrame:
    """Busca en TODA la historia de reuniones de Tiresias por email, empresa, teléfono o nombre."""
    t = term.strip().replace("*", "")
    if not t:
        return pd.DataFrame()
    url = (
        f"{SUPABASE_URL}/rest/v1/reuniones"
        f"?select=contacto,empresa,email,telefono,cargo,industria,fecha_reunion,hora_reunion,estado_validacion"
        f"&cliente_slug=eq.tiresias"
        f"&or=(email.ilike.*{t}*,empresa.ilike.*{t}*,telefono.ilike.*{t}*,contacto.ilike.*{t}*)"
        f"&order=fecha_reunion.desc"
    )
    r = requests.get(url, headers=_H, timeout=15)
    return pd.DataFrame(r.json() if r.ok else [])


def render_buscador():
    st.markdown(
        '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;'
        'padding:16px 20px;margin-bottom:20px">'
        '<div style="font-size:15px;font-weight:700;color:#14532d;margin-bottom:8px">'
        'Verificar si un contacto ya tuvo reuniones con Tiresias</div>'
        '<div style="font-size:12px;color:#166534;margin-bottom:10px">'
        'Ingresar correo, nombre de empresa, teléfono o nombre del contacto</div>'
        '</div>',
        unsafe_allow_html=True)

    col_inp, col_btn = st.columns([5, 1])
    with col_inp:
        term = st.text_input(
            "Buscar contacto",
            placeholder="ej: rodrigo@empresa.cl / Sitrans / +56912345678",
            label_visibility="collapsed",
            key="buscador_term",
        )
    with col_btn:
        buscar = st.button("Buscar", key="buscador_btn", use_container_width=True)

    if not (term and len(term.strip()) >= 3):
        return

    if buscar or term:
        df_res = buscar_contacto(term)
        if df_res.empty:
            st.markdown(
                '<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:10px;'
                'padding:14px 18px;color:#991b1b;font-weight:600">'
                'Este contacto no ha tenido reuniones previas con Tiresias.</div>',
                unsafe_allow_html=True)
        else:
            n = len(df_res)
            st.markdown(
                f'<div style="background:#dcfce7;border:1px solid #86efac;border-radius:10px;'
                f'padding:14px 18px;color:#14532d;font-weight:700;margin-bottom:10px">'
                f'Encontramos <b>{n}</b> reunión{"es" if n > 1 else ""} previas con Tiresias</div>',
                unsafe_allow_html=True)

            ESTADO_COLOR = {
                "valida": ("#dcfce7","#166534","Válida"),
                "reunion_valida": ("#dcfce7","#166534","Válida"),
                "no_valida": ("#fee2e2","#991b1b","No válida"),
                "reunion_no_valida": ("#fee2e2","#991b1b","No válida"),
                "reagendar": ("#ffedd5","#9a3412","Reagendar"),
                "pendiente_validacion": ("#fef9c3","#854d0e","Pendiente"),
            }
            for _, r in df_res.iterrows():
                fecha_raw = r.get("fecha_reunion") or ""
                try:
                    dt = pd.to_datetime(str(fecha_raw))
                    fecha_str = f"{DIAS_ES[dt.weekday()]} {dt.day} de {MESES_ES[dt.month-1]} {dt.year}"
                except Exception:
                    fecha_str = str(fecha_raw)[:10]
                hora_str = str(r.get("hora_reunion") or "")[:5] or "—"
                contacto = _safe(r.get("contacto"), "—").title()
                empresa = _safe(r.get("empresa"), "—").title()
                cargo = _safe(r.get("cargo"), "")
                email = _safe(r.get("email"), "—")
                tel = _safe(r.get("telefono"), "—")
                estado = _safe(r.get("estado_validacion"), "pendiente_validacion")
                s_bg, s_color, s_lbl = ESTADO_COLOR.get(estado, ("#f3f4f6","#374151","—"))
                cargo_html = (f'<div style="font-size:12px;color:#64748b">{cargo}</div>'
                              if cargo else "")

                st.markdown(
                    f'<div style="border:1px solid #e2e8f0;border-radius:10px;'
                    f'padding:12px 16px;margin-bottom:8px;background:#fff;'
                    f'display:flex;flex-wrap:wrap;gap:12px;align-items:flex-start">'
                    f'<div style="min-width:160px">'
                    f'<div style="font-size:12px;font-weight:700;color:#334155">{fecha_str} · {hora_str}</div>'
                    f'<span style="background:{s_bg};color:{s_color};padding:1px 8px;'
                    f'border-radius:8px;font-size:11px;font-weight:600">{s_lbl}</span></div>'
                    f'<div style="flex:1;min-width:180px">'
                    f'<div style="font-weight:700;color:#0f172a">{contacto}</div>'
                    f'{cargo_html}'
                    f'<div style="font-size:12px;color:#475569">{email}</div>'
                    f'<div style="font-size:12px;color:#475569">{tel}</div></div>'
                    f'<div style="min-width:150px">'
                    f'<div style="font-weight:600;color:#1e293b">{empresa}</div></div>'
                    f'</div>',
                    unsafe_allow_html=True)
        st.markdown("---")


def render_header():
    t = img_b64("tiresias_logo.png", 56) or (
        '<div style="background:#1e3a5f;color:#fff;padding:10px 22px;border-radius:8px;'
        'font-size:19px;font-weight:700;letter-spacing:1.5px">tiresias</div>')
    c = img_b64("conprospeccion_logo.png", 44) or (
        '<div style="background:#111827;padding:8px 18px;border-radius:8px;'
        'font-size:13px;font-weight:700;color:#fbbf24">Conprospección</div>')
    st.markdown(
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'background:linear-gradient(135deg,#f8fafc,#eef2ff);padding:18px 28px;'
        f'border-radius:14px;border:1px solid #c7d2fe;margin-bottom:20px;'
        f'box-shadow:0 2px 8px rgba(0,0,0,.06)">'
        f'<div style="display:flex;align-items:center;gap:18px">{t}'
        f'<div><div style="font-size:22px;font-weight:800;color:#1e293b">Portal de Reuniones</div>'
        f'<div style="font-size:13px;color:#64748b;margin-top:3px">'
        f'Evaluar cada reunión y registrar el estado comercial</div></div></div>{c}</div>',
        unsafe_allow_html=True)


_FILTRO_ESTADO_OPTS = ["Todos", "Válidas", "No válidas", "Reagendar", "Pendientes"]

def _aplicar_filtro_estado(df: pd.DataFrame, sel: str) -> pd.DataFrame:
    if sel == "Válidas":
        return df[df["estado_validacion"].apply(lambda v: str(v).lower() in ("valida","reunion_valida"))]
    if sel == "No válidas":
        return df[df["estado_validacion"].apply(lambda v: str(v).lower() in ("no_valida","reunion_no_valida"))]
    if sel == "Reagendar":
        return df[df["estado_validacion"].apply(lambda v: str(v).lower() in ("reagendar","reagendada"))]
    if sel == "Pendientes":
        return df[df["estado_validacion"].apply(
            lambda v: str(v).lower() not in ("valida","reunion_valida","no_valida","reunion_no_valida","reagendar","reagendada"))]
    return df


def run():
    if not require_auth_tiresias():
        return

    render_client_nav("4_Tiresias_Validacion", "tiresias")
    render_header()
    render_buscador()
    hoy = date.today()

    c_mes, c_anio, c_ref = st.columns([2, 1, 1])
    with c_mes:
        mes = st.selectbox("Mes", range(1,13),
                           format_func=lambda m: MESES_ES[m-1].capitalize(),
                           index=hoy.month-1, key="tc_mes")
    with c_anio:
        anio = int(st.number_input("Año", 2024, 2030, hoy.year, key="tc_anio"))
    with c_ref:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Actualizar", key="tc_ref"):
            st.cache_data.clear(); st.rerun()

    fi, ff = mes_rango(anio, int(mes))
    df = cargar_reuniones(fi, ff)
    stages = cargar_stages()
    seguimiento = cargar_seguimiento()

    # ── Filtros: día y estado de validación ───────────────────────────────────
    if not df.empty:
        fechas = sorted(df["fecha"].dropna().unique())
        opts_dia = ["Todos los días"] + [
            f"{DIAS_ES[pd.Timestamp(str(f)).weekday()]} {pd.Timestamp(str(f)).day} "
            f"de {MESES_ES[pd.Timestamp(str(f)).month-1]}"
            for f in fechas]
        c_dia, c_estado_f = st.columns([3, 2])
        with c_dia:
            dia_sel = st.selectbox("Día", opts_dia, key="tc_dia")
        with c_estado_f:
            estado_f = st.selectbox("Estado de validación", _FILTRO_ESTADO_OPTS, key="tc_estado_f")
        if dia_sel != "Todos los días":
            idx = opts_dia.index(dia_sel) - 1
            df = df[df["fecha"] == fechas[idx]].copy()
        df = _aplicar_filtro_estado(df, estado_f)

    if df.empty:
        st.info("No hay reuniones para el período y filtros seleccionados.")
        return

    total = len(df)
    n_val = int(df["estado_validacion"].apply(lambda v: str(v).lower() in ("valida","reunion_valida")).sum())
    n_nv = int(df["estado_validacion"].apply(lambda v: str(v).lower() in ("no_valida","reunion_no_valida")).sum())
    n_reag = int(df["estado_validacion"].apply(lambda v: str(v).lower() in ("reagendar","reagendada")).sum())
    n_pend = int(df["estado_validacion"].apply(
        lambda v: str(v).lower() not in ("valida","reunion_valida","no_valida","reunion_no_valida","reagendar","reagendada")).sum())

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total", total)
    m2.metric("Válidas", n_val)
    m3.metric("No válidas", n_nv)
    m4.metric("Reagendar", n_reag)
    m5.metric("Pendientes", n_pend)

    st.markdown(
        f'<div style="background:linear-gradient(135deg,#1e3a5f,#2563eb);color:white;'
        f'padding:11px 20px;border-radius:10px;margin:14px 0 6px;font-weight:700;font-size:15px">'
        f'{MESES_ES[int(mes)-1].capitalize()} {anio} — de más antigua a más reciente</div>',
        unsafe_allow_html=True)
    st.markdown("---")

    for i, (_, row) in enumerate(df.iterrows()):
        rid = int(row.get("id") or 0)
        opp_id = _safe(row.get("opportunity_id"), "")
        contacto = _safe(row.get("contacto") or row.get("nombre"), "Sin nombre").title()
        cargo = _safe(row.get("cargo"), "Cargo no registrado").title()
        empresa = _safe(row.get("empresa"), "Empresa no registrada").title()
        email = _safe(row.get("email"), "Email no registrado")
        tel = _safe(row.get("telefono"), "Teléfono no registrado")
        ind = _safe(row.get("industria"), "Industria no registrada").title()
        pais = _safe(row.get("pais"), "")
        hora = str(row.get("hora") or "")[:5] or "—"
        fecha_txt = fmt_fecha(row.get("fecha"))
        estado_db = _safe(row.get("estado_validacion"), "pendiente_validacion")

        seg = seguimiento.get(rid, {})
        status_prev = seg.get("status_comercial") or ""
        etapa_prev = seg.get("etapa_comercial")

        # Mostrar badge solo si está validado (no "pendiente")
        estado_badge = ESTADO_STYLE.get(estado_db)
        badge_html = ""
        if estado_badge:
            s_bg, s_color, s_lbl = estado_badge
            badge_html = badge(s_lbl, s_bg, s_color)

        lbl_val = _VAL_LABEL.get(estado_db, "— Seleccionar estado —")
        if lbl_val not in OPCIONES_VAL:
            lbl_val = "— Seleccionar estado —"

        with st.container():
            st.markdown(
                f'<div style="background:#f1f5f9;padding:10px 16px;border-radius:10px 10px 0 0;'
                f'border:1px solid #cbd5e1;display:flex;align-items:center;gap:10px;flex-wrap:wrap">'
                f'<span style="font-size:13px;font-weight:700;color:#334155">{fecha_txt}</span>'
                f'<span style="color:#94a3b8">·</span>'
                f'<span style="font-size:15px;font-weight:800;color:#1e40af">{hora}</span>'
                + badge_html + '</div>',
                unsafe_allow_html=True)

            col_e, col_c = st.columns(2)
            with col_e:
                pais_html = f'<div style="font-size:12px;color:#64748b;margin-top:2px">{pais}</div>' if pais else ""
                st.markdown(
                    f'<div style="padding:12px 16px;border:1px solid #e2e8f0;border-top:none;background:#fff">'
                    f'<div style="font-size:15px;font-weight:700;color:#0f172a">{empresa}</div>'
                    f'<div style="font-size:12px;color:#64748b;margin-top:3px">{ind}</div>'
                    + pais_html + '</div>',
                    unsafe_allow_html=True)
            with col_c:
                st.markdown(
                    f'<div style="padding:12px 16px;border:1px solid #e2e8f0;border-top:none;'
                    f'border-left:none;background:#fff">'
                    f'<div style="font-size:15px;font-weight:700;color:#0f172a">{contacto}</div>'
                    f'<div style="font-size:12px;color:#64748b;margin-top:3px">{cargo}</div>'
                    f'<div style="font-size:12px;color:#475569;margin-top:6px"><span style="font-family:monospace">{email}</span></div>'
                    f'<div style="font-size:12px;color:#475569">{tel}</div></div>',
                    unsafe_allow_html=True)

            c1, c2, c3 = st.columns([1, 1, 2])
            with c1:
                nuevo_estado_lbl = st.selectbox("Validación",
                    list(OPCIONES_VAL.keys()),
                    index=list(OPCIONES_VAL.keys()).index(lbl_val),
                    key=f"cval_{rid}_{i}")
                nuevo_estado = OPCIONES_VAL[nuevo_estado_lbl]
            with c2:
                etapa_keys = list(ETAPAS.keys())
                etapa_default = _ETAPA_LABEL.get(etapa_prev, "— Sin etapa —") if etapa_prev else "— Sin etapa —"
                nueva_etapa_lbl = st.selectbox("Etapa comercial", etapa_keys,
                    index=etapa_keys.index(etapa_default) if etapa_default in etapa_keys else 0,
                    key=f"cetapa_{rid}_{i}")
                nueva_etapa = ETAPAS[nueva_etapa_lbl]
            with c3:
                nuevo_status = st.text_area("Status comercial",
                    value=status_prev, height=88,
                    placeholder="Ej: Enviamos propuesta el 26/05, esperamos respuesta...",
                    key=f"cstatus_{rid}_{i}")

            _, col_btn = st.columns([5, 1])
            with col_btn:
                if st.button("Guardar", key=f"csave_{rid}_{i}", type="primary"):
                    ok = guardar_reunion(rid, opp_id, nuevo_estado, estado_db,
                                        nueva_etapa, etapa_prev,
                                        nuevo_status, status_prev, stages)
                    st.toast("Guardado correctamente" if ok else "Hubo un problema al guardar")
                    st.cache_data.clear()
                    st.rerun()

        st.markdown('<div style="margin-bottom:18px"></div>', unsafe_allow_html=True)


run()
