"""Portal cliente GBS Logistics — Validación de Reuniones (3 capas, idéntico a Seguimiento)."""
import sys, calendar, requests, pandas as pd, streamlit as st
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from shared.config import supabase_url, supabase_key, ghl_tokens
from shared.gbs_brand import GBS_PURPLE, GBS_DARK, GBS_PURPLE_BG, GBS_BORDER_2
from shared.metas import meta_de
from shared.seguimiento import (
    cargar as cargar_seg_unif, guardar_nivel, bant_to_list,
    recalcular_final_y_flags, registrar_historial, COLUMNAS_CLIENTE,
)
from shared.validacion import VAL_ESTADOS, MOTIVO_NO_VALIDEZ, ESTADO_COMERCIAL
from shared.validacion_ui import (
    LABEL_VALIDEZ, LABEL_ESTADO_COMERCIAL, LABEL_MOTIVO, BANT_LABEL,
    chip_status, banner_final, fila_resumen, bloque_resumen, encabezado_seccion,
    barra_avance, mini_label, CAP_CP, CAP_CLI,
)
from portal_auth import require_auth_client, render_client_nav, img_b64

st.set_page_config(page_title="GBS Logistics — Validación Reuniones", layout="wide", page_icon="")

SUPABASE_URL = supabase_url()
SUPABASE_KEY = supabase_key()
GHL_TOKEN = ghl_tokens().get("gbs", "")

MESES_ES = ["enero","febrero","marzo","abril","mayo","junio",
            "julio","agosto","septiembre","octubre","noviembre","diciembre"]
DIAS_ES = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]

_CLI_VAL_TO_CAT = {"valida": "reunion_valida", "no_valida": "reunion_no_valida"}
_FILTRO_ESTADO_OPTS = ["Todos", "Válidas", "No válidas", "Pendientes"]

_H  = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
_HW = {**_H, "Content-Type": "application/json", "Prefer": "return=minimal"}

GBS_BG     = GBS_PURPLE_BG
GBS_BORDER = GBS_BORDER_2
GBS_BLUE   = GBS_PURPLE


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


@st.cache_data(ttl=60)
def cargar_reuniones(fi, ff):
    url = (f"{SUPABASE_URL}/rest/v1/vw_reuniones_semana"
           f"?select=*&cliente_slug=eq.gbs&fecha=gte.{fi}&fecha=lte.{ff}&order=fecha.asc,hora.asc")
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
        f"?select=pipeline_id,pipeline_name,stage_id,stage_category&cliente_slug=eq.gbs",
        headers=_H, timeout=15)
    if not r.ok: return {}
    rows = r.json()
    src = ([x for x in rows if "gbs" in x.get("pipeline_name","").lower() or
            "sales" in x.get("pipeline_name","").lower()] or rows)
    out = {}
    for x in src:
        cat = x.get("stage_category")
        if cat and cat not in out:
            out[cat] = (x["pipeline_id"], x["stage_id"])
    return out

@st.cache_data(ttl=30)
def cargar_seguimiento():
    # Solo columnas visibles al cliente: nunca trae notas internas ni datos operativos.
    return cargar_seg_unif("gbs", select=COLUMNAS_CLIENTE)

@st.cache_data(ttl=30)
def contar_validas_finales():
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/seguimiento_reuniones"
        f"?cliente_slug=eq.gbs&flag_meta_countable=eq.true&select=reunion_id",
        headers=_H, timeout=15)
    return len(r.json()) if r.ok else 0


def upd_validacion(rid, estado):
    return requests.patch(f"{SUPABASE_URL}/rest/v1/reuniones?id=eq.{rid}",
                          json={"estado_validacion": estado}, headers=_HW, timeout=10).ok

def mover_ghl(opp_id, pid, sid):
    if not all([opp_id, pid, sid, GHL_TOKEN]): return None
    return requests.put(
        f"https://services.leadconnectorhq.com/opportunities/{opp_id}",
        json={"pipelineId": pid, "pipelineStageId": sid},
        headers={"Authorization": f"Bearer {GHL_TOKEN}",
                 "Content-Type": "application/json", "Version": "2021-07-28"}, timeout=15).ok

def buscar_contacto(term: str) -> pd.DataFrame:
    t = term.strip().replace("*", "")
    if not t: return pd.DataFrame()
    url = (
        f"{SUPABASE_URL}/rest/v1/reuniones"
        f"?select=contacto,empresa,email,telefono,cargo,industria,fecha_reunion,hora_reunion"
        f"&cliente_slug=eq.gbs"
        f"&or=(email.ilike.*{t}*,empresa.ilike.*{t}*,telefono.ilike.*{t}*,contacto.ilike.*{t}*)"
        f"&order=fecha_reunion.desc")
    r = requests.get(url, headers=_H, timeout=15)
    return pd.DataFrame(r.json() if r.ok else [])


def _vf_de(seg, rid):
    return seg.get(int(rid) if rid else 0, {}).get("val_estado_final") or "pendiente"

def _aplicar_filtro_estado(df, seg, sel):
    if sel == "Todos":
        return df
    if sel == "Válidas":
        return df[df["id"].apply(lambda r: _vf_de(seg, r) == "valida")]
    if sel == "No válidas":
        return df[df["id"].apply(lambda r: _vf_de(seg, r) in ("no_valida", "en_disputa"))]
    if sel == "Pendientes":
        return df[df["id"].apply(lambda r: _vf_de(seg, r) in ("pendiente", "reagendada", "excluida", None, ""))]
    return df


def render_buscador():
    st.markdown(
        f'<div style="background:{GBS_BG};border:1px solid {GBS_BORDER};border-radius:12px;'
        f'padding:16px 20px;margin-bottom:18px">'
        f'<div style="font-size:15px;font-weight:700;color:#4c1d95;margin-bottom:8px">'
        f'Verificar si un contacto ya tuvo reuniones con GBS Logistics</div>'
        f'<div style="font-size:12px;color:#6d28d9;margin-bottom:10px">'
        f'Ingresar correo, nombre de empresa, teléfono o nombre del contacto</div></div>',
        unsafe_allow_html=True)
    col_inp, col_btn = st.columns([5, 1])
    with col_inp:
        term = st.text_input("Buscar contacto",
            placeholder="ej: gerente@empresa.cl / Kaufmann / +56912345678",
            label_visibility="collapsed", key="buscador_term")
    with col_btn:
        st.button("Buscar", key="buscador_btn", use_container_width=True)
    if not (term and len(term.strip()) >= 3):
        return
    df_res = buscar_contacto(term)
    if df_res.empty:
        st.markdown(
            '<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:10px;'
            'padding:14px 18px;color:#991b1b;font-weight:600">'
            'Este contacto no ha tenido reuniones previas con GBS Logistics.</div>',
            unsafe_allow_html=True)
    else:
        n = len(df_res)
        st.markdown(
            f'<div style="background:#ede9fe;border:1px solid #c4b5fd;border-radius:10px;'
            f'padding:14px 18px;color:#4c1d95;font-weight:700;margin-bottom:10px">'
            f'Encontramos <b>{n}</b> reunión{"es" if n > 1 else ""} previa{"s" if n > 1 else ""} con GBS</div>',
            unsafe_allow_html=True)
    st.markdown("---")


def render_header():
    g = img_b64("gbs_logo.png", 56) or (
        f'<div style="background:{GBS_BLUE};color:#fff;padding:10px 22px;border-radius:8px;'
        f'font-size:18px;font-weight:800;letter-spacing:2px">GBS</div>')
    c = img_b64("conprospeccion_logo.png", 44) or (
        '<div style="background:#111827;padding:8px 18px;border-radius:8px;'
        'font-size:13px;font-weight:700;color:#fbbf24">Conprospección</div>')
    st.markdown(
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'background:linear-gradient(135deg,#faf5ff,#ede9fe);padding:18px 28px;'
        f'border-radius:14px;border:1px solid {GBS_BORDER};margin-bottom:18px;'
        f'box-shadow:0 2px 8px rgba(0,0,0,.06)">'
        f'<div style="display:flex;align-items:center;gap:18px">{g}'
        f'<div><div style="font-size:22px;font-weight:800;color:#1e293b">Portal de Reuniones</div>'
        f'<div style="font-size:13px;color:#64748b;margin-top:3px">'
        f'Evaluar cada reunión y registrar el estado comercial</div></div></div>{c}</div>',
        unsafe_allow_html=True)


def run():
    if not require_auth_client("gbs"):
        return
    render_client_nav("12_GBS_Validacion", "gbs")

    st.markdown(
        f'<style>'
        f'button[kind="primary"]{{background:{GBS_PURPLE}!important;border:none!important;'
        f'color:#fff!important;font-weight:700!important}}'
        f'button[kind="primary"]:hover{{filter:brightness(1.08)}}'
        f'span[data-baseweb="tag"]{{background:#ede9fe!important;color:#5b21b6!important}}'
        f'span[data-baseweb="tag"] span{{color:#5b21b6!important}}'
        f'span[data-baseweb="tag"] svg{{fill:#5b21b6!important}}'
        f'</style>', unsafe_allow_html=True)

    render_header()
    render_buscador()
    hoy = date.today()

    # ── Filtros año / mes / día + Actualizar ──────────────────────────────────
    c_anio, c_mes, c_dia_ph, c_ref = st.columns([1.2, 1.6, 2.4, 1])
    with c_anio:
        anio = int(st.number_input("Año", 2024, 2030, hoy.year, key="tc_anio"))
    with c_mes:
        mes = st.selectbox("Mes", range(1, 13),
            format_func=lambda m: MESES_ES[m-1].capitalize(),
            index=hoy.month - 1, key="tc_mes")
    with c_ref:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Actualizar", key="tc_ref", use_container_width=True):
            st.cache_data.clear(); st.rerun()

    fi, ff = mes_rango(anio, int(mes))
    df = cargar_reuniones(fi, ff)
    stages = cargar_stages()
    seguimiento = cargar_seguimiento()

    estado_f = "Todos"
    if not df.empty:
        fechas = sorted(df["fecha"].dropna().unique())
        opts_dia = ["Todos los días"] + [
            f"{DIAS_ES[pd.Timestamp(str(f)).weekday()]} {pd.Timestamp(str(f)).day} "
            f"de {MESES_ES[pd.Timestamp(str(f)).month-1]}" for f in fechas]
        with c_dia_ph:
            dia_sel = st.selectbox("Día", opts_dia, key="tc_dia")
        c_ef, _ = st.columns([2, 4])
        with c_ef:
            estado_f = st.selectbox("Estado de validación", _FILTRO_ESTADO_OPTS, key="tc_estado_f")
        if dia_sel != "Todos los días":
            df = df[df["fecha"] == fechas[opts_dia.index(dia_sel) - 1]].copy()
        df = _aplicar_filtro_estado(df, seguimiento, estado_f)

    # ── KPIs principales (validez final, consistente con la meta) ─────────────
    if not df.empty:
        rids = [int(r) for r in df["id"].dropna()]
    else:
        rids = []
    n_val  = sum(1 for rid in rids if seguimiento.get(rid, {}).get("val_estado_final") == "valida")
    n_nv   = sum(1 for rid in rids if seguimiento.get(rid, {}).get("val_estado_final") == "no_valida")
    n_disp = sum(1 for rid in rids if seguimiento.get(rid, {}).get("val_estado_final") == "en_disputa")
    n_pend = len(rids) - n_val - n_nv - n_disp

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Reuniones", len(rids))
    m2.metric("Válidas", n_val)
    m3.metric("No válidas", n_nv)
    m4.metric("En revisión", n_disp)
    m5.metric("Pendientes", n_pend)

    meta = meta_de("gbs") or {"validas": 0}
    st.markdown(barra_avance(contar_validas_finales(), meta["validas"], color=GBS_PURPLE),
                unsafe_allow_html=True)

    if df.empty:
        st.markdown(
            f'<div style="text-align:center;padding:48px 20px">'
            f'<div style="font-size:18px;font-weight:800;color:#1e293b;margin-bottom:6px">'
            f'Sin reuniones para el período</div>'
            f'<div style="font-size:14px;color:#64748b">Probá con otro mes o quitá el filtro de estado.</div></div>',
            unsafe_allow_html=True)
        return

    st.markdown(
        f'<div style="background:linear-gradient(135deg,#4c1d95,#7c3aed);color:white;'
        f'padding:11px 20px;border-radius:10px;margin:10px 0 6px;font-weight:700;font-size:15px">'
        f'{MESES_ES[int(mes)-1].capitalize()} {anio} — de más antigua a más reciente</div>',
        unsafe_allow_html=True)
    st.markdown("")

    for i, (_, row) in enumerate(df.iterrows()):
        rid     = int(row.get("id") or 0)
        opp_id  = _safe(row.get("opportunity_id"), "")
        contacto = _safe(row.get("contacto") or row.get("nombre"), "Sin nombre").title()
        cargo   = _safe(row.get("cargo"), "Cargo no registrado").title()
        empresa = _safe(row.get("empresa"), "Empresa no registrada").title()
        email   = _safe(row.get("email"), "Email no registrado")
        tel     = _safe(row.get("telefono"), "Teléfono no registrado")
        ind     = _safe(row.get("industria"), "Industria no registrada").title()
        pais    = _safe(row.get("pais"), "")
        hora    = str(row.get("hora") or "")[:5] or "—"
        fecha_txt = fmt_fecha(row.get("fecha"))
        seg = seguimiento.get(rid, {})

        cp_val   = seg.get("val_estado_cp") or "espera"
        cp_bant  = bant_to_list(seg.get("bant_cp"))
        cli_val  = seg.get("val_estado_cli") or "espera"
        cli_bant = bant_to_list(seg.get("bant_cli"))
        final    = seg.get("val_estado_final") or "pendiente"
        datos    = " · ".join(x for x in [cargo, email, tel, ind, pais]
                              if x and x not in ("—", "Cargo no registrado",
                                                 "Email no registrado", "Teléfono no registrado",
                                                 "Industria no registrada"))

        with st.container(border=True):
            # Cabecera: empresa · contacto + datos + fecha/hora/estado reunión
            st.markdown(
                f'<div style="font-size:16px;font-weight:800;color:#0f172a">{empresa}'
                f'<span style="color:#cbd5e1;margin:0 6px">·</span>{contacto}</div>'
                f'<div style="font-size:12px;color:#64748b;margin-top:2px">{datos}</div>'
                f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:7px">'
                f'<span style="font-size:13px;font-weight:700;color:#334155">{fecha_txt}</span>'
                f'<span style="color:#94a3b8">·</span>'
                f'<span style="font-size:14px;font-weight:800;color:{GBS_BLUE}">{hora}</span>'
                f'<span style="font-size:11px;color:#64748b;margin-left:6px">Reunión:</span>'
                f'{chip_status(seg.get("status_reunion"))}</div>',
                unsafe_allow_html=True)
            st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

            # 1) Validez final (banner) — lo que manda
            st.markdown(banner_final(final), unsafe_allow_html=True)

            # 2) Resumen comparativo (read-only): Conprospección + Cliente
            st.markdown(bloque_resumen(
                fila_resumen("Evaluación Conprospección", CAP_CP[1], cp_val, cp_bant,
                             seg.get("comentario_cp"), primera=True),
                fila_resumen("Validación del cliente", CAP_CLI[1], cli_val, cli_bant,
                             seg.get("comentario_cli")),
            ), unsafe_allow_html=True)

            # 3) Zona de edición — solo lo que el cliente controla
            st.markdown(encabezado_seccion("Tu validación", CAP_CLI[1]), unsafe_allow_html=True)
            e1, e2 = st.columns(2)
            with e1:
                st.markdown(mini_label("Validez"), unsafe_allow_html=True)
                v_cli = st.selectbox("Tu validación", VAL_ESTADOS,
                    index=VAL_ESTADOS.index(cli_val) if cli_val in VAL_ESTADOS else 0,
                    format_func=lambda x: LABEL_VALIDEZ.get(x, x),
                    key=f"vcli_{rid}_{i}", label_visibility="collapsed")
            with e2:
                st.markdown(mini_label("Criterios BANT (opcional)"), unsafe_allow_html=True)
                b_cli = st.multiselect("BANT", ["B", "A", "N", "T"], default=cli_bant,
                    format_func=lambda x: f"{x} · {BANT_LABEL[x]}",
                    placeholder="Opcional", key=f"bcli_{rid}_{i}", label_visibility="collapsed")
            e3, e4 = st.columns(2)
            with e3:
                st.markdown(mini_label("Estado comercial"), unsafe_allow_html=True)
                ec_prev = seg.get("estado_comercial") or ""
                ec_idx = (ESTADO_COMERCIAL.index(ec_prev) + 1) if ec_prev in ESTADO_COMERCIAL else 0
                ec = st.selectbox("Estado comercial", ["—"] + ESTADO_COMERCIAL, index=ec_idx,
                    format_func=lambda x: LABEL_ESTADO_COMERCIAL.get(x, x),
                    key=f"ec_{rid}_{i}", label_visibility="collapsed")
            with e4:
                motivo = None
                if v_cli == "no_valida":
                    st.markdown(mini_label("Motivo (opcional)"), unsafe_allow_html=True)
                    mot_prev = seg.get("motivo_no_validez") or MOTIVO_NO_VALIDEZ[0]
                    mot_idx = MOTIVO_NO_VALIDEZ.index(mot_prev) if mot_prev in MOTIVO_NO_VALIDEZ else 0
                    motivo = st.selectbox("Motivo (opcional)", MOTIVO_NO_VALIDEZ, index=mot_idx,
                        format_func=lambda x: LABEL_MOTIVO.get(x, x),
                        key=f"mot_{rid}_{i}", label_visibility="collapsed")
            st.markdown(mini_label("Comentario (opcional)"), unsafe_allow_html=True)
            coment = st.text_input("Comentario (opcional)", value=seg.get("comentario_cli") or "",
                key=f"ccli_{rid}_{i}", label_visibility="collapsed")

            _, col_btn = st.columns([5, 1])
            with col_btn:
                if st.button("Guardar", key=f"csave_{rid}_{i}", type="primary",
                             use_container_width=True):
                    _leg = {"valida": "valida", "no_valida": "no_valida"}.get(v_cli, "pendiente_validacion")
                    upd_validacion(rid, _leg)
                    _cat = _CLI_VAL_TO_CAT.get(v_cli)
                    if _cat and _cat in stages:
                        mover_ghl(opp_id, *stages[_cat])
                    guardar_nivel(rid, "gbs", "cli", val_estado=v_cli, bant=b_cli,
                        etapa=(ec if ec != "—" else None), status=coment)
                    _patch = {
                        "estado_comercial": (ec if ec != "—" else None),
                        "comentario_cli": coment.strip() or None,
                        "motivo_no_validez": motivo,
                        "validated_by_cli": "cliente",
                        "validated_cli_at": datetime.now(timezone.utc).isoformat(),
                    }
                    requests.patch(
                        f"{SUPABASE_URL}/rest/v1/seguimiento_reuniones?reunion_id=eq.{rid}",
                        json={k: v for k, v in _patch.items() if v is not None},
                        headers=_HW, timeout=10)
                    recalcular_final_y_flags(rid, "gbs")
                    registrar_historial(rid, "val_estado_cli", seg.get("val_estado_cli"), v_cli,
                                        "cliente", "cliente", "validacion")
                    st.toast("Guardado")
                    st.cache_data.clear(); st.rerun()

        st.markdown('<div style="margin-bottom:20px"></div>', unsafe_allow_html=True)


run()
