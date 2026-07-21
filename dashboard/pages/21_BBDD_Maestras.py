"""BBDD Maestras — pool único de prospectos (Apollo/Snov/GHL) reutilizable por ICP.

Layout tipo MVP Setup: a la izquierda "Bases de datos" con los clientes en
prospección; al hacer clic se abre a la derecha el panel del cliente para revisar
el pool según su ICP y preparar el envío a Snov (correo verificado) / GHL (teléfono).

Fase 1 (esta entrega): consolidación + dedup que alerta (no borra) + limpieza
(industria/país) + ICP editable + candidatos por ICP con ruta + export + guardar
asignaciones. El envío real a Snov/GHL (Fase 2) queda gated hasta activación.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

from master_auth import get_current_user, render_master_user_sidebar, require_master_auth
from shared.bbdd_maestra import (
    ICP,
    candidatos,
    consolidar,
    normalizar_industria,
    normalizar_pais,
    resumen_pool,
)
from shared.config import supabase_key, supabase_url

st.set_page_config(page_title="BBDD Maestras - ConprospeccionOS", layout="wide", page_icon="🗂️")
if not require_master_auth():
    st.stop()
render_master_user_sidebar()

SB_URL = supabase_url()
SB_KEY = supabase_key()
SB_H = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"}
SB_HW = {**SB_H, "Content-Type": "application/json", "Prefer": "return=representation"}

# Clientes en prospección (los que reutilizan el pool). Editable a medida que sumen.
PROSPECCION = [
    {"slug": "gbs", "nombre": "GBS Logistics"},
    {"slug": "bambutech", "nombre": "BambuTech"},
]

P = {
    "purple": "#6d28d9", "purple2": "#7c3aed", "blue": "#2563eb", "green": "#16a34a",
    "amber": "#d97706", "red": "#dc2626", "muted": "#64748b", "border": "#e2e8f0",
}


# ── Data access ───────────────────────────────────────────────────────────────
def _sb_get(table: str, query: str = "select=*") -> list[dict[str, Any]]:
    if not SB_KEY:
        return []
    try:
        r = requests.get(f"{SB_URL}/rest/v1/{table}?{query}", headers=SB_H, timeout=20)
        if r.ok:
            return r.json()
    except Exception:
        return []
    return []


@st.cache_data(ttl=600, show_spinner="Cargando pool maestro…")
def load_pool() -> list[dict[str, Any]]:
    """Trae todas las filas de la vista unificada, paginando de a 1000."""
    cols = "fuente,ref_id,email_norm,email,nombre,empresa,cargo,industria,pais,localidad,telefono,email_status,linkedin_url,cliente_slug_origen"
    filas: list[dict[str, Any]] = []
    offset = 0
    while True:
        chunk = _sb_get("vw_prospectos_maestros", f"select={cols}&limit=1000&offset={offset}")
        if not chunk:
            break
        filas.extend(chunk)
        if len(chunk) < 1000:
            break
        offset += 1000
    return consolidar(filas)


@st.cache_data(ttl=60, show_spinner=False)
def load_icp(slug: str) -> dict[str, Any]:
    rows = _sb_get("icp_clientes", f"select=*&cliente_slug=eq.{slug}&limit=1")
    if rows:
        return rows[0]
    # Fallback GBS: derivar ICP desde gbs_onboarding.
    if slug == "gbs":
        ob = _sb_get("gbs_onboarding", "select=*&cliente=eq.gbs&limit=1")
        if ob:
            o = ob[0]
            return {
                "cliente_slug": "gbs",
                "paises": o.get("icp_pais"),
                "industrias": o.get("icp_industrias"),
                "cargos": o.get("icp_cargos"),
                "tamanos": o.get("icp_tamano"),
                "keywords": o.get("keywords_prospecto"),
                "exclusiones": o.get("icp_descarte"),
                "umbral_score": 2,
            }
    return {"cliente_slug": slug, "umbral_score": 2}


def save_icp(icp: ICP, user: str) -> bool:
    payload = {
        "cliente_slug": icp.cliente_slug,
        "paises": icp.paises, "industrias": icp.industrias, "cargos": icp.cargos,
        "tamanos": icp.tamanos, "keywords": icp.keywords, "exclusiones": icp.exclusiones,
        "umbral_score": icp.umbral_score, "updated_by": user, "updated_at": "now()",
    }
    try:
        r = requests.post(
            f"{SB_URL}/rest/v1/icp_clientes",
            headers={**SB_HW, "Prefer": "resolution=merge-duplicates,return=representation"},
            json=payload, timeout=15,
        )
        return r.ok
    except Exception:
        return False


@st.cache_data(ttl=30, show_spinner=False)
def load_asignaciones(slug: str) -> list[dict[str, Any]]:
    return _sb_get("bbdd_maestra_asignaciones", f"select=*&cliente_slug=eq.{slug}")


def guardar_asignaciones(rows: list[dict[str, Any]], slug: str, user: str) -> int:
    payload = [
        {
            "email_norm": r["email_norm"], "cliente_slug": slug, "estado": "asignado",
            "score_icp": r.get("score_icp"),
            "motivo": ", ".join(k for k, v in (r.get("match") or {}).items() if v),
            "origen": {"fuentes": r.get("fuentes"), "rutas": r.get("rutas")},
            "created_by": user,
        }
        for r in rows
    ]
    if not payload:
        return 0
    try:
        r = requests.post(
            f"{SB_URL}/rest/v1/bbdd_maestra_asignaciones",
            headers={**SB_HW, "Prefer": "resolution=merge-duplicates,return=representation"},
            json=payload, timeout=30,
        )
        return len(r.json()) if r.ok else 0
    except Exception:
        return 0


# ── UI helpers ────────────────────────────────────────────────────────────────
def metric_row(items: list[tuple[str, Any, str]]) -> None:
    cols = st.columns(len(items))
    for col, (label, value, color) in zip(cols, items):
        col.markdown(
            f"""<div style="border:1px solid {P['border']};border-left:4px solid {color};
            border-radius:10px;padding:12px 16px;background:#fff">
            <div style="font-size:11px;color:{P['muted']};text-transform:uppercase;letter-spacing:.5px;font-weight:700">{label}</div>
            <div style="font-size:24px;font-weight:800;color:#111827;margin-top:2px">{value}</div></div>""",
            unsafe_allow_html=True,
        )


def _fmt(n: int) -> str:
    return f"{n:,}".replace(",", ".")


# CSS del sidebar tipo MVP Setup (oscuro + botón activo).
st.markdown(
    """<style>
[data-testid="stSidebar"] { background:#0f172a !important; }
[data-testid="stSidebar"] p,[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,[data-testid="stSidebar"] div { color:#cbd5e1 !important; }
[data-testid="stSidebar"] hr { border-color:#1e293b !important; }
[data-testid="stSidebar"] .stButton > button {
  background:transparent !important; border:none !important; color:#94a3b8 !important;
  text-align:left !important; padding:8px 14px !important; border-radius:8px !important;
  font-size:14px !important; width:100%; transition:all .15s; }
[data-testid="stSidebar"] .stButton > button:hover { background:#1e293b !important; color:#f1f5f9 !important; }
[data-testid="stSidebar"] .btn-activo > button { background:#1e3a5f !important; color:#93c5fd !important; font-weight:600 !important; }
</style>""",
    unsafe_allow_html=True,
)


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    f"""<div style="background:linear-gradient(135deg,#111827 0%,#312e81 100%);
    border-radius:16px;padding:26px 32px;margin-bottom:18px;color:#fff">
    <div style="font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#c4b5fd;font-weight:800">Prospección · Datos</div>
    <div style="font-size:28px;font-weight:900;margin-top:4px">BBDD Maestras</div>
    <div style="color:#cbd5e1;font-size:14px;max-width:720px;margin-top:6px;line-height:1.5">
    Un solo pool de prospectos (Apollo · Snov · GHL) deduplicado por correo. Selecciona una base
    de datos a la izquierda y reutiliza los contactos según el ICP de cada cliente: correo verificado → Snov,
    con teléfono → GHL.</div></div>""",
    unsafe_allow_html=True,
)

user = get_current_user() or "interno"
pool = load_pool()

if not pool:
    st.warning("No se pudo cargar el pool maestro (revisa la conexión a Supabase).")
    st.stop()

# ── Nav "Bases de datos" en el sidebar (estilo MVP Setup) ─────────────────────
if "bbdd_cliente" not in st.session_state:
    st.session_state["bbdd_cliente"] = PROSPECCION[0]["slug"]

with st.sidebar:
    st.markdown('<hr style="border-color:#1e293b;margin:10px 0 6px">', unsafe_allow_html=True)
    st.markdown('<div style="font-size:18px;font-weight:800;color:#f1f5f9;padding:0 8px">🗂️ Bases de datos</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:1.5px;padding:6px 8px 4px">Clientes en prospección</div>', unsafe_allow_html=True)
    for c in PROSPECCION:
        activo = st.session_state["bbdd_cliente"] == c["slug"]
        st.markdown(f'<div class="{"btn-activo" if activo else ""}">', unsafe_allow_html=True)
        if st.button(f"📁  {c['nombre']}", key=f"nav_{c['slug']}", use_container_width=True):
            st.session_state["bbdd_cliente"] = c["slug"]
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    r = resumen_pool(pool)
    st.markdown('<hr style="border-color:#1e293b;margin:10px 0 6px">', unsafe_allow_html=True)
    st.markdown(
        f"""<div style="padding:10px 12px;background:#0f2040;border-radius:8px;margin:4px">
        <div style="font-size:10px;color:#64748b;letter-spacing:1px">POOL GLOBAL</div>
        <div style="font-size:22px;font-weight:800;color:#93c5fd">{_fmt(r['prospectos_unicos'])}</div>
        <div style="font-size:10px;color:#94a3b8">prospectos únicos · ⚠️ {_fmt(r['duplicados'])} duplicados</div>
        <div style="font-size:10px;color:#94a3b8;margin-top:4px">{_fmt(r['correos_verificados'])} verif. (Snov) · {_fmt(r['con_telefono'])} con tel. (GHL)</div>
        </div>""",
        unsafe_allow_html=True,
    )

slug = st.session_state["bbdd_cliente"]
nombre_cliente = next(c["nombre"] for c in PROSPECCION if c["slug"] == slug)

panel = st.container()
with panel:
    st.markdown(f"### {nombre_cliente}")
    tab_pool, tab_icp, tab_cand, tab_dup = st.tabs(
        ["📊 Resumen del pool", "🎯 ICP del cliente", "♻️ Candidatos a reutilizar", "⚠️ Duplicados"]
    )

    # — Resumen del pool —
    with tab_pool:
        rp = resumen_pool(pool)
        metric_row([
            ("Filas totales", _fmt(rp["total_filas"]), P["muted"]),
            ("Prospectos únicos", _fmt(rp["prospectos_unicos"]), P["purple"]),
            ("Duplicados (alerta)", _fmt(rp["duplicados"]), P["amber"]),
            ("Verificados (Snov)", _fmt(rp["correos_verificados"]), P["green"]),
            ("Con teléfono (GHL)", _fmt(rp["con_telefono"]), P["blue"]),
        ])
        st.markdown("")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Cobertura por industria** (normalizada)")
            df_i = pd.DataFrame(list(rp["por_industria"].items()), columns=["Industria", "Prospectos"]).head(15)
            st.dataframe(df_i, use_container_width=True, hide_index=True)
        with c2:
            st.markdown("**Cobertura por país** (normalizado)")
            df_p = pd.DataFrame(list(rp["por_pais"].items()), columns=["País", "Prospectos"]).head(15)
            st.dataframe(df_p, use_container_width=True, hide_index=True)

    # — ICP del cliente —
    with tab_icp:
        icp_row = load_icp(slug)
        icp = ICP.from_row(icp_row)
        st.caption("El ICP define qué prospectos del pool se reutilizan para este cliente. Se guarda en `icp_clientes`.")
        with st.form(f"icp_form_{slug}"):
            col1, col2 = st.columns(2)
            with col1:
                paises = st.text_area("Países", ", ".join(icp.paises), height=70, help="Separa por coma")
                industrias = st.text_area("Industrias", ", ".join(icp.industrias), height=90)
                cargos = st.text_area("Cargos", ", ".join(icp.cargos), height=90)
            with col2:
                tamanos = st.text_area("Tamaño empresa", ", ".join(icp.tamanos), height=70)
                keywords = st.text_area("Keywords", ", ".join(icp.keywords), height=90)
                exclusiones = st.text_area("Exclusiones (descartar)", ", ".join(icp.exclusiones), height=90)
            umbral = st.slider("Umbral de score (mín. dimensiones que deben calzar)", 1, 4, int(icp.umbral_score or 2))
            if st.form_submit_button("💾 Guardar ICP", type="primary"):
                nueva = ICP(
                    cliente_slug=slug,
                    paises=[x.strip() for x in paises.split(",") if x.strip()],
                    industrias=[x.strip() for x in industrias.split(",") if x.strip()],
                    cargos=[x.strip() for x in cargos.split(",") if x.strip()],
                    tamanos=[x.strip() for x in tamanos.split(",") if x.strip()],
                    keywords=[x.strip() for x in keywords.split(",") if x.strip()],
                    exclusiones=[x.strip() for x in exclusiones.split(",") if x.strip()],
                    umbral_score=umbral,
                )
                if save_icp(nueva, user):
                    st.success("ICP guardado.")
                    load_icp.clear()
                else:
                    st.error("No se pudo guardar el ICP.")

    # — Candidatos a reutilizar —
    with tab_cand:
        icp = ICP.from_row(load_icp(slug))
        if not any([icp.paises, icp.industrias, icp.cargos, icp.keywords]):
            st.info("Define primero el ICP en la pestaña anterior para calcular candidatos.")
        else:
            asig = load_asignaciones(slug)
            ya = {a["email_norm"] for a in asig}
            incluir = st.checkbox("Incluir prospectos sin correo verificado ni teléfono", value=False)
            cands = candidatos(pool, icp, ya_asignados=ya, incluir_sin_verificar=incluir)

            snov = [c for c in cands if "snov" in c["rutas"]]
            ghl = [c for c in cands if "ghl" in c["rutas"]]
            metric_row([
                ("Candidatos ICP", _fmt(len(cands)), P["purple"]),
                ("→ Snov (correo verif.)", _fmt(len(snov)), P["green"]),
                ("→ GHL (con teléfono)", _fmt(len(ghl)), P["blue"]),
                ("Ya asignados", _fmt(len(ya)), P["muted"]),
            ])

            if cands:
                df = pd.DataFrame([
                    {
                        "Nombre": c.get("nombre"), "Empresa": c.get("empresa"),
                        "Cargo": c.get("cargo"), "Industria": c.get("industria_norm"),
                        "País": c.get("pais_norm"), "Email": c.get("email"),
                        "Verificado": "✓" if c.get("correo_verificado") else "",
                        "Teléfono": "✓" if c.get("tiene_telefono") else "",
                        "Ruta": " + ".join(c["rutas"]).upper(),
                        "Score": c["score_icp"], "Duplicado": "⚠️" if c.get("es_duplicado") else "",
                        "email_norm": c["email_norm"],
                    }
                    for c in cands
                ])
                st.dataframe(
                    df.drop(columns=["email_norm"]), use_container_width=True, hide_index=True, height=380
                )
                st.download_button(
                    "⬇️ Exportar candidatos (CSV)",
                    df.drop(columns=["email_norm"]).to_csv(index=False).encode("utf-8"),
                    file_name=f"candidatos_{slug}.csv", mime="text/csv",
                )

                cA, cB = st.columns(2)
                with cA:
                    if st.button(f"📌 Guardar {len(cands)} como asignados a {nombre_cliente}", type="primary"):
                        n = guardar_asignaciones(cands, slug, user)
                        st.success(f"{n} prospectos asignados a {nombre_cliente} (ledger).")
                        load_asignaciones.clear()
                with cB:
                    st.button("🚀 Enviar a Snov / GHL", disabled=True,
                              help="Fase 2: el envío real a Snov/GHL se activa tras confirmación. Por ahora se registran las asignaciones.")
                st.caption("El envío directo a Snov (agregar a lista/campaña) y GHL (crear contacto) está preparado pero **desactivado** hasta tu visto bueno (Fase 2).")
            else:
                st.info("No hay candidatos nuevos con este ICP y umbral.")

    # — Duplicados —
    with tab_dup:
        st.caption("Correos que aparecen en más de un registro o fuente. **No se eliminan**: se listan para revisión.")
        dups = [f for f in pool if f.get("es_duplicado") and f.get("es_canonico")]
        st.markdown(f"**{_fmt(len(dups))}** correos duplicados en el pool.")
        if dups:
            df_d = pd.DataFrame([
                {
                    "Email": d.get("email"), "Nombre": d.get("nombre"), "Empresa": d.get("empresa"),
                    "Veces": d.get("veces"), "Fuentes": ", ".join(d.get("fuentes") or []),
                    "Clientes origen": ", ".join(d.get("clientes_origen") or []),
                }
                for d in dups
            ]).sort_values("Veces", ascending=False)
            st.dataframe(df_d, use_container_width=True, hide_index=True, height=420)
            st.download_button(
                "⬇️ Exportar duplicados (CSV)",
                df_d.to_csv(index=False).encode("utf-8"),
                file_name="duplicados_pool.csv", mime="text/csv",
            )
