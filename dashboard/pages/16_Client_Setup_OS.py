"""Client Setup OS - internal operations module.

Phase 1:
- GBS Logistics pilot.
- Reads proposed normalized tables if they exist.
- Falls back to existing GBS artifacts in CLIENTES/GBS_LOGISTICS.
- Does not call external APIs.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime
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
from portal_auth import img_b64
from shared.config import supabase_key, supabase_url

st.set_page_config(page_title="Client Setup OS - ConprospeccionOS", layout="wide", page_icon="")
if not require_master_auth():
    st.stop()

SB_URL = supabase_url()
SB_KEY = supabase_key()
SB_H = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"}
SB_HW = {**SB_H, "Content-Type": "application/json", "Prefer": "return=representation"}

CLIENT_SLUG = "gbs_logistics"
LEGACY_SLUGS = ["gbs", "GBS_LOGISTICS", "gbs_logistics", "GBS Logistics", "GBS_LOGISTICS"]
GBS_DIR = ROOT / "CLIENTES" / "GBS_LOGISTICS"
MIGRATION_PATH = ROOT / "supabase" / "migrations" / "006_client_setup_os_proposed.sql"

P = {
    "dark": "#111827",
    "panel": "#ffffff",
    "muted": "#64748b",
    "border": "#e2e8f0",
    "purple": "#6d28d9",
    "purple2": "#7c3aed",
    "pink": "#db2777",
    "blue": "#2563eb",
    "green": "#16a34a",
    "amber": "#d97706",
    "red": "#dc2626",
    "slate": "#334155",
}


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def _read_text(path: Path, default: str = "") -> str:
    try:
        if path.exists():
            return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return default
    return default


def _split_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    text = str(value or "")
    parts = re.split(r"[\n,;|]+", text)
    return [p.strip(" -\t") for p in parts if p.strip(" -\t")]


def _norm(text: str) -> str:
    text = str(text or "").lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def _sb_get(table: str, query: str = "select=*") -> list[dict[str, Any]]:
    if not SB_KEY:
        return []
    try:
        r = requests.get(f"{SB_URL}/rest/v1/{table}?{query}", headers=SB_H, timeout=12)
        if r.ok:
            return r.json()
    except Exception:
        return []
    return []


@st.cache_data(ttl=45, show_spinner=False)
def load_sources() -> dict[str, Any]:
    estado = _read_json(GBS_DIR / "estado_cliente.json", {})
    comercial = _read_json(GBS_DIR / "07_BASE_DATOS" / "comercial.json", {})
    ghl_config = _read_json(GBS_DIR / "07_BASE_DATOS" / "ghl_config.json", {})
    manifest = _read_json(
        GBS_DIR
        / "08_BASES_Y_CALIFICACION"
        / "03_finales_campanas"
        / "paquetes_campanas"
        / "GBS_manifest_campanas_listas_20260602.json",
        [],
    )
    plan_snov = _read_text(
        GBS_DIR
        / "08_BASES_Y_CALIFICACION"
        / "03_finales_campanas"
        / "paquetes_campanas"
        / "GBS_plan_campanas_snov_20260602.md"
    )
    onboarding = {}
    rows = _sb_get("gbs_onboarding", "select=*&cliente=eq.gbs&limit=1")
    if rows:
        onboarding = rows[0]

    setup_rows = _sb_get("client_setup", "select=*&canonical_slug=eq.gbs_logistics&limit=1")
    setup = setup_rows[0] if setup_rows else {}
    setup_id = setup.get("id")

    normalized = {
        "steps": [],
        "profiles": [],
        "segments": [],
        "domains": [],
        "mailboxes": [],
        "signatures": [],
        "warmup": [],
        "databases": [],
        "campaigns": [],
        "sdr_assignments": [],
        "history": [],
    }
    if setup_id:
        q = f"select=*&client_setup_id=eq.{setup_id}"
        for key, table in [
            ("steps", "client_setup_steps"),
            ("profiles", "client_icp_profiles"),
            ("segments", "client_icp_segments"),
            ("domains", "client_domains"),
            ("mailboxes", "client_mailboxes"),
            ("signatures", "client_email_signatures"),
            ("warmup", "client_warmup"),
            ("databases", "client_databases"),
            ("campaigns", "client_campaigns"),
            ("sdr_assignments", "client_sdr_assignments"),
        ]:
            normalized[key] = _sb_get(table, q)
        normalized["history"] = _sb_get(
            "client_setup_history",
            f"select=*&client_setup_id=eq.{setup_id}&order=action_at.desc&limit=100",
        )

    return {
        "estado": estado,
        "comercial": comercial,
        "ghl_config": ghl_config,
        "manifest": manifest if isinstance(manifest, list) else [],
        "plan_snov": plan_snov,
        "onboarding": onboarding,
        "setup": setup,
        "normalized": normalized,
    }


def file_inventory() -> dict[str, Any]:
    files = []
    if GBS_DIR.exists():
        for p in GBS_DIR.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                files.append(p)

    by_name = Counter(_norm(p.stem) for p in files)
    duplicate_names = [p for p in files if by_name[_norm(p.stem)] > 1]
    db_files = [
        p for p in files
        if p.suffix.lower() in (".csv", ".xlsx", ".xls", ".json", ".jsonl")
        and any(x in str(p).lower() for x in ["base", "apollo", "snov", "campana", "campaign"])
    ]
    signature_files = [p for p in files if "firma" in p.name.lower()]

    root_data = list((ROOT / "data" / "outputs" / "GBS").glob("*")) if (ROOT / "data" / "outputs" / "GBS").exists() else []
    apollo = list((ROOT / "BASES_APOLLO" / "GBS Logistics").glob("*")) if (ROOT / "BASES_APOLLO" / "GBS Logistics").exists() else []
    snov = list((ROOT / "BASES_SNOV" / "GBS Logistics").glob("*")) if (ROOT / "BASES_SNOV" / "GBS Logistics").exists() else []

    return {
        "files": files,
        "db_files": db_files,
        "duplicate_names": duplicate_names,
        "signature_files": signature_files,
        "root_data": root_data,
        "apollo": apollo,
        "snov": snov,
    }


@st.cache_data(ttl=45, show_spinner=False)
def load_all() -> tuple[dict[str, Any], dict[str, Any]]:
    return load_sources(), file_inventory()


def css() -> None:
    st.markdown(
        f"""
<style>
#MainMenu, footer {{display:none}}
.block-container {{padding-top:1.2rem; max-width:1500px}}
.hero {{
  background:linear-gradient(135deg,#111827 0%,#1e1e2e 48%,#312e81 100%);
  border-radius:16px; padding:28px 34px; margin-bottom:20px; color:white;
  box-shadow:0 12px 32px rgba(15,23,42,.18);
}}
.hero-top {{display:flex;justify-content:space-between;align-items:flex-start;gap:20px}}
.eyebrow {{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#c4b5fd;font-weight:800}}
.hero h1 {{margin:4px 0 6px;font-size:30px;line-height:1.1;color:white;font-weight:900;letter-spacing:0}}
.hero p {{margin:0;color:#cbd5e1;font-size:13px;max-width:850px;line-height:1.55}}
.hero-badges {{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}}
.badge {{
  display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:5px 10px;
  font-size:11px;font-weight:800;border:1px solid #e2e8f0;background:#fff;color:#334155;
}}
.badge.dark {{background:rgba(255,255,255,.08);border-color:rgba(255,255,255,.18);color:#e9d5ff}}
.badge.green {{background:#dcfce7;border-color:#86efac;color:#166534}}
.badge.amber {{background:#fef3c7;border-color:#fcd34d;color:#92400e}}
.badge.red {{background:#fee2e2;border-color:#fca5a5;color:#991b1b}}
.badge.purple {{background:#f5f3ff;border-color:#ddd6fe;color:#5b21b6}}
.kpi-grid {{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px;margin:16px 0 20px}}
.kpi {{
  background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:15px 16px;
  box-shadow:0 1px 6px rgba(15,23,42,.05);min-height:104px;
}}
.kpi small {{display:block;color:#64748b;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.04em}}
.kpi strong {{display:block;color:#0f172a;font-size:28px;line-height:1.1;margin-top:8px}}
.kpi span {{display:block;color:#64748b;font-size:12px;margin-top:5px}}
.section-title {{display:flex;align-items:flex-end;justify-content:space-between;margin:18px 0 10px}}
.section-title h2 {{font-size:18px;margin:0;color:#111827;font-weight:900}}
.section-title p {{font-size:12px;margin:2px 0 0;color:#64748b}}
.panel {{
  background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:18px 20px;
  box-shadow:0 1px 6px rgba(15,23,42,.04); margin-bottom:14px;
}}
.panel h3 {{font-size:15px;margin:0 0 10px;color:#111827;font-weight:900}}
.metric-row {{display:grid;grid-template-columns:1.1fr .9fr;gap:14px}}
.timeline {{display:grid;grid-template-columns:repeat(8,1fr);gap:8px;margin-top:12px}}
.step {{
  border:1px solid #e2e8f0;background:#f8fafc;border-radius:10px;padding:10px;min-height:86px;
}}
.step b {{display:block;font-size:12px;color:#111827;line-height:1.25}}
.step small {{display:block;font-size:11px;color:#64748b;margin-top:6px}}
.step.done {{background:#f0fdf4;border-color:#86efac}}
.step.warn {{background:#fffbeb;border-color:#fcd34d}}
.step.bad {{background:#fef2f2;border-color:#fca5a5}}
.segment-grid {{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}}
.segment-card {{border:1px solid #e2e8f0;border-radius:12px;padding:14px;background:#fff}}
.segment-card h4 {{font-size:14px;margin:0 0 8px;color:#111827}}
.segment-card p {{font-size:12px;color:#64748b;margin:0 0 9px;line-height:1.45}}
.line {{display:flex;justify-content:space-between;gap:12px;border-bottom:1px solid #f1f5f9;padding:8px 0;font-size:13px}}
.line span:first-child {{color:#64748b}}
.line span:last-child {{font-weight:800;color:#111827;text-align:right}}
.warn-box {{border:1px solid #fcd34d;background:#fffbeb;color:#78350f;border-radius:12px;padding:13px 15px;font-size:13px;line-height:1.5}}
.risk-box {{border:1px solid #fecaca;background:#fef2f2;color:#7f1d1d;border-radius:12px;padding:13px 15px;font-size:13px;line-height:1.5}}
.ok-box {{border:1px solid #bbf7d0;background:#f0fdf4;color:#14532d;border-radius:12px;padding:13px 15px;font-size:13px;line-height:1.5}}
.muted {{color:#64748b;font-size:12px;line-height:1.5}}
.dataframe {{font-size:12px}}
@media (max-width: 1100px) {{
  .kpi-grid {{grid-template-columns:repeat(2,minmax(0,1fr))}}
  .timeline {{grid-template-columns:repeat(2,1fr)}}
  .segment-grid {{grid-template-columns:1fr}}
  .metric-row {{grid-template-columns:1fr}}
}}
</style>
""",
        unsafe_allow_html=True,
    )


def badge(text: str, tone: str = "") -> str:
    return f'<span class="badge {tone}">{text}</span>'


def header(sources: dict[str, Any], inventory: dict[str, Any]) -> None:
    setup = sources["setup"]
    estado = sources["estado"]
    onboarding = sources["onboarding"]
    mode = "Normalizado en Supabase" if setup else "Fallback GBS existente"
    received = onboarding.get("updated_at") or onboarding.get("created_at") or "sin intake reciente"
    logo = img_b64("gbs_logo.png", 48)
    logo_html = logo or '<div style="background:#7c3aed;color:white;padding:10px 18px;border-radius:9px;font-weight:900">GBS</div>'
    st.markdown(
        f"""
<div class="hero">
  <div class="hero-top">
    <div style="display:flex;gap:16px;align-items:center">
      {logo_html}
      <div>
        <div class="eyebrow">Modulo interno de operaciones</div>
        <h1>Client Setup OS</h1>
        <p>Centro operativo para intake, ICP, segmentos, dominios, correos, warmup, bases, campanas, GHL, SDR, checklist e historial. GBS Logistics es el piloto; el modelo queda preparado para cualquier cliente futuro.</p>
      </div>
    </div>
    <div class="hero-badges">
      {badge("Cliente: GBS Logistics", "dark")}
      {badge("Slug canonico: gbs_logistics", "dark")}
      {badge(mode, "dark")}
      {badge("Sin APIs externas", "dark")}
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    camp_count = len(sources["manifest"])
    db_count = len(inventory["db_files"]) + len(inventory["root_data"]) + len(inventory["apollo"]) + len(inventory["snov"])
    seg_count = len(build_segments(sources))
    risk_count = len(build_risks(sources, inventory))
    kpis = [
        ("Intake", "1" if onboarding else "0", f"Ultima recepcion: {received}"),
        ("Segmentos", seg_count, "TMP principal + subsegmentos detectados"),
        ("Campanas/BBDD", camp_count + db_count, "Artefactos existentes auditables"),
        ("Infra correo", len(inventory["signature_files"]), "Firmas/activos detectados"),
        ("SDR/GHL", len((sources.get("ghl_config") or {}).get("sdrs") or []), "Usuarios en config local"),
        ("Riesgos", risk_count, "Alertas de normalizacion"),
    ]
    html = '<div class="kpi-grid">' + "".join(
        f'<div class="kpi"><small>{label}</small><strong>{value}</strong><span>{sub}</span></div>'
        for label, value, sub in kpis
    ) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


def section(title: str, sub: str = "") -> None:
    st.markdown(
        f'<div class="section-title"><div><h2>{title}</h2><p>{sub}</p></div></div>',
        unsafe_allow_html=True,
    )


def build_segments(sources: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = sources["normalized"].get("segments") or []
    if normalized:
        return normalized

    estado = sources["estado"]
    onboarding = sources["onboarding"]
    paises = _split_list(onboarding.get("icp_pais") or estado.get("icp_paises_foco") or estado.get("pais_objetivo"))
    industrias = _split_list(onboarding.get("icp_industrias") or estado.get("icp_industrias"))
    cargos = _split_list(onboarding.get("icp_cargos") or estado.get("icp_cargos"))
    if not paises:
        paises = ["Chile", "Peru", "Colombia"]
    if not industrias:
        industrias = ["Mineria y Metales", "Retail", "Equipamiento Medico", "Tecnologia", "Maquinaria Industrial"]
    if not cargos:
        cargos = ["Comercio Exterior", "Supply Chain", "Operaciones", "Compras", "Abastecimiento"]

    presets = [
        ("Chile / Mineria / Comercio Exterior", "Chile", "Mineria y Metales", "Comercio Exterior", "active", "high", "Mayor senal historica en GBS; priorizar cargas criticas y repuestos."),
        ("Chile / Tecnologia / Supply Chain", "Chile", "Tecnologia", "Supply Chain", "active", "medium", "Segmento para validar con empresas importadoras de equipos o electronica."),
        ("Peru / Retail / Operaciones", "Peru", "Retail", "Operaciones", "review", "medium", "Base amplia; requiere control de calidad por pais y cargo."),
        ("Colombia / Equipamiento Medico / Abastecimiento", "Colombia", "Equipamiento Medico", "Abastecimiento", "review", "medium", "Subsegmento con potencial, aun con volumen menor."),
        ("Mexico / Manufactura / Compras", "Mexico", "Manufactura", "Compras", "paused", "low", "Preparado para expansion futura; no activo en piloto."),
        ("Centroamerica / Repuestos / Dueno", "Centroamerica", "Repuestos", "Dueno", "draft", "low", "Hipotesis futura, requiere datos."),
    ]
    return [
        {
            "segment_name": name,
            "country": country,
            "industry": industry,
            "cargo_area": cargo,
            "status": status,
            "priority": priority,
            "learning_notes": notes,
            "database_status": "ready" if country in ("Chile", "Peru", "Colombia") else "pending",
            "campaign_status": "draft" if country in ("Chile", "Peru", "Colombia") else "pending",
        }
        for name, country, industry, cargo, status, priority, notes in presets
    ]


def build_campaign_rows(sources: dict[str, Any], inventory: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for item in sources["manifest"]:
        name = item.get("campaign_name") or item.get("list_name") or Path(str(item.get("file", ""))).stem
        alerts = []
        if not item.get("country"):
            alerts.append("Campana sin pais")
        if not item.get("segment"):
            alerts.append("Campana sin segmento")
        if not item.get("platform"):
            alerts.append("Campana sin plataforma")
        status = "Pendiente cargar Snov" if item.get("platform") == "Snov.io" else "Pendiente cargar GHL"
        if item.get("contacts", 0) and int(item.get("contacts") or 0) < 20:
            alerts.append("BBDD incompleta")
            quality = "Media"
        else:
            quality = "Reutilizable"
        rows.append({
            "Nombre": name,
            "Cliente": "GBS Logistics",
            "Fuente": item.get("source") or "",
            "Pais": item.get("country") or "",
            "Segmento": item.get("segment") or "",
            "Plataforma": item.get("platform") or "",
            "Prospectos": item.get("contacts") or 0,
            "Estado": status,
            "Calidad estimada": quality,
            "Alertas": ", ".join(alerts) if alerts else "Sin alertas criticas",
            "Archivo": item.get("file") or "",
        })

    for p in inventory["root_data"]:
        if p.suffix.lower() not in (".csv", ".xlsx"):
            continue
        alerts = []
        name = p.stem
        if "fit" in name.lower() or "snov" in name.lower():
            quality = "Reutilizable"
        else:
            quality = "Pendiente segmentar"
            alerts.append("Pendiente segmentar")
        rows.append({
            "Nombre": name,
            "Cliente": "GBS Logistics",
            "Fuente": "data/outputs/GBS",
            "Pais": "",
            "Segmento": "",
            "Plataforma": "BBDD",
            "Prospectos": "",
            "Estado": "En revision",
            "Calidad estimada": quality,
            "Alertas": ", ".join(alerts) if alerts else "Mala nomenclatura posible",
            "Archivo": str(p.relative_to(ROOT)),
        })

    seen = Counter(_norm(r["Nombre"]) for r in rows)
    for r in rows:
        if seen[_norm(r["Nombre"])] > 1:
            r["Alertas"] = (r["Alertas"] + ", BBDD duplicada").strip(", ")

    return pd.DataFrame(rows)


def build_risks(sources: dict[str, Any], inventory: dict[str, Any]) -> list[dict[str, str]]:
    risks = []
    setup = sources["setup"]
    ghl = sources["ghl_config"] or {}
    estado = sources["estado"] or {}
    comercial = sources["comercial"] or {}

    if not setup:
        risks.append({
            "Riesgo": "Tablas Client Setup OS no ejecutadas",
            "Impacto": "La pantalla usa fallback local; aun no existe fuente normalizada definitiva.",
            "Accion": "Revisar y ejecutar 006_client_setup_os_proposed.sql en Fase 2."
        })
    if len(set(_norm(x) for x in LEGACY_SLUGS)) > 2:
        risks.append({
            "Riesgo": "Slugs distintos para GBS",
            "Impacto": "gbs, GBS_LOGISTICS, gbs_logistics y GBS Logistics conviven en rutas/tablas.",
            "Accion": "Usar gbs_logistics como canonical_slug y mapear aliases."
        })
    sdrs = ghl.get("sdrs") or []
    mixed = [s for s in sdrs if "bambutech" in str(s.get("email", "")).lower()]
    if mixed:
        risks.append({
            "Riesgo": "Configuracion GHL mezclada",
            "Impacto": "ghl_config.json de GBS contiene emails/datos con dominio Bambutech.",
            "Accion": "Validar location_id, token y usuarios antes de usar en operacion."
        })
    if len(inventory["signature_files"]) > 1:
        risks.append({
            "Riesgo": "Firmas duplicadas",
            "Impacto": "Hay multiples firmas/html/imagenes; riesgo de instalar una version no vigente.",
            "Accion": "Definir firma vigente por casilla y archivar referencias."
        })
    if inventory["duplicate_names"]:
        risks.append({
            "Riesgo": "Archivos duplicados",
            "Impacto": "Existen nombres normalizados repetidos en la carpeta GBS.",
            "Accion": "Clasificar como version vigente, respaldo o descartar."
        })
    if not comercial.get("fecha_inicio_prospeccion"):
        risks.append({
            "Riesgo": "Fecha de prospeccion incompleta",
            "Impacto": "Checklist de lanzamiento no puede calcular readiness temporal.",
            "Accion": "Completar condiciones comerciales canonicas."
        })
    if estado.get("estado_icp") != "icp_aprobado":
        risks.append({
            "Riesgo": "ICP no aprobado formalmente",
            "Impacto": "Hay ICP vigente/operativo, pero estado_cliente marca pendiente de revision.",
            "Accion": "Cerrar aprobacion interna en Client Setup OS."
        })
    return risks


def render_intake(sources: dict[str, Any]) -> None:
    onboarding = sources["onboarding"]
    estado = sources["estado"]
    comercial = sources["comercial"]
    cols = st.columns([1.2, 1])
    with cols[0]:
        st.markdown('<div class="panel"><h3>Intake oficial</h3>', unsafe_allow_html=True)
        lines = [
            ("Fuente", "gbs_onboarding" if onboarding else "estado_cliente.json fallback"),
            ("Estado revision", sources["setup"].get("review_status", "pending_review")),
            ("Fecha recepcion", onboarding.get("updated_at") or onboarding.get("created_at") or "No disponible"),
            ("Responsable", sources["setup"].get("responsable") or get_current_user() or "Operacion"),
            ("Plan", onboarding.get("plan_contratado") or comercial.get("plan_contratado") or "Starter"),
            ("Meta", f"{comercial.get('reuniones_garantizadas', 45)} reuniones garantizadas"),
        ]
        st.markdown("".join(f'<div class="line"><span>{k}</span><span>{v}</span></div>' for k, v in lines), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with cols[1]:
        st.markdown('<div class="panel"><h3>Resumen cliente</h3>', unsafe_allow_html=True)
        summary = estado.get("resumen_servicio") or "GBS Logistics - freight forwarding y logistica internacional."
        st.markdown(f'<p class="muted">{summary[:650]}</p>', unsafe_allow_html=True)
        st.markdown(
            badge("Portal solo intake", "purple")
            + " "
            + badge("Operacion interna aqui", "green")
            + " "
            + badge("APIs externas pausadas", "amber"),
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    section("Campos capturados por onboarding", "Estos datos alimentan el setup, pero operaciones puede editarlos o crear nuevos segmentos.")
    rows = [
        ("Paises", onboarding.get("icp_pais") or estado.get("icp_paises_foco") or estado.get("pais_objetivo")),
        ("Industrias", onboarding.get("icp_industrias") or estado.get("icp_industrias")),
        ("Cargos", onboarding.get("icp_cargos") or estado.get("icp_cargos")),
        ("Tamano empresa", onboarding.get("icp_tamano") or estado.get("icp_tamano_empresa")),
        ("Exclusiones", onboarding.get("icp_descarte") or estado.get("icp_criterios_descarte")),
        ("Keywords", onboarding.get("keywords_prospecto") or estado.get("icp_keywords")),
    ]
    st.dataframe(pd.DataFrame(rows, columns=["Campo", "Valor"]), use_container_width=True, hide_index=True)


def render_icp(sources: dict[str, Any]) -> None:
    estado = sources["estado"]
    onboarding = sources["onboarding"]
    section("Target Market Profile", "ICP principal normalizado desde onboarding + estado GBS existente.")
    c1, c2, c3, c4 = st.columns(4)
    cards = [
        ("Paises", _split_list(onboarding.get("icp_pais") or estado.get("icp_paises_foco") or estado.get("pais_objetivo"))),
        ("Industrias", _split_list(onboarding.get("icp_industrias") or estado.get("icp_industrias"))[:10]),
        ("Cargos", _split_list(onboarding.get("icp_cargos") or estado.get("icp_cargos"))[:10]),
        ("Tamano", _split_list(onboarding.get("icp_tamano") or estado.get("icp_tamano_empresa"))),
    ]
    for col, (title, vals) in zip([c1, c2, c3, c4], cards):
        with col:
            chips = " ".join(badge(v, "purple") for v in vals[:8]) or '<span class="muted">Pendiente</span>'
            st.markdown(f'<div class="panel"><h3>{title}</h3>{chips}</div>', unsafe_allow_html=True)

    section("Subsegmentos operativos", "Cada subsegmento puede tener BBDD, campanas, SDR, resultados y aprendizaje propios.")
    segments = build_segments(sources)
    html = '<div class="segment-grid">'
    for seg in segments:
        status = seg.get("status", "draft")
        tone = "green" if status == "active" else ("amber" if status in ("review", "paused") else "purple")
        html += f"""
<div class="segment-card">
  <div style="display:flex;justify-content:space-between;gap:8px;align-items:flex-start">
    <h4>{seg.get("segment_name")}</h4>{badge(status, tone)}
  </div>
  <p>{seg.get("country") or "-"} / {seg.get("industry") or "-"} / {seg.get("cargo_area") or "-"}</p>
  <div class="line"><span>BBDD</span><span>{seg.get("database_status", "pending")}</span></div>
  <div class="line"><span>Campanas</span><span>{seg.get("campaign_status", "pending")}</span></div>
  <div class="line"><span>Prioridad</span><span>{seg.get("priority", "medium")}</span></div>
  <p style="margin-top:10px">{seg.get("learning_notes") or "Sin aprendizaje aun."}</p>
</div>
"""
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

    with st.expander("Crear o editar segmento - preparado para Fase 2", expanded=False):
        cc = st.columns(4)
        cc[0].text_input("Pais", value="Chile", disabled=True)
        cc[1].text_input("Industria", value="Mineria y Metales", disabled=True)
        cc[2].text_input("Cargo/area", value="Comercio Exterior", disabled=True)
        cc[3].selectbox("Estado", ["active", "review", "paused", "discarded"], disabled=True)
        st.text_area("Aprendizaje / observaciones", value="Persistencia habilitada al ejecutar migraciones normalizadas.", disabled=True)


def render_campaigns_databases(sources: dict[str, Any], inventory: dict[str, Any]) -> None:
    section("Campanas y BBDD existentes", "Auditoria de lo ya construido. No se borra nada; se clasifica para reutilizar, revisar o descartar.")
    df = build_campaign_rows(sources, inventory)
    f1, f2, f3 = st.columns([1, 1, 1])
    status = f1.multiselect("Estado", sorted(df["Estado"].dropna().unique().tolist()), default=[])
    platform = f2.multiselect("Plataforma", sorted(df["Plataforma"].dropna().unique().tolist()), default=[])
    query = f3.text_input("Buscar", placeholder="campana, pais, archivo")
    dff = df.copy()
    if status:
        dff = dff[dff["Estado"].isin(status)]
    if platform:
        dff = dff[dff["Plataforma"].isin(platform)]
    if query:
        q = query.lower()
        dff = dff[dff.apply(lambda r: q in " ".join(str(x).lower() for x in r.values), axis=1)]
    st.dataframe(dff, use_container_width=True, hide_index=True)

    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown('<div class="panel"><h3>Alertas detectadas</h3>', unsafe_allow_html=True)
        alert_counts = Counter()
        for val in df["Alertas"].fillna(""):
            for part in [p.strip() for p in str(val).split(",") if p.strip() and p.strip() != "Sin alertas criticas"]:
                alert_counts[part] += 1
        if alert_counts:
            st.markdown("".join(f'<div class="line"><span>{k}</span><span>{v}</span></div>' for k, v in alert_counts.most_common()), unsafe_allow_html=True)
        else:
            st.markdown('<div class="ok-box">Sin alertas criticas en manifiesto actual.</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="panel"><h3>Inventario de bases</h3>', unsafe_allow_html=True)
        inv_lines = [
            ("CLIENTES/GBS_LOGISTICS", len(inventory["db_files"])),
            ("data/outputs/GBS", len(inventory["root_data"])),
            ("BASES_APOLLO/GBS Logistics", len(inventory["apollo"])),
            ("BASES_SNOV/GBS Logistics", len(inventory["snov"])),
        ]
        st.markdown("".join(f'<div class="line"><span>{k}</span><span>{v}</span></div>' for k, v in inv_lines), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


def render_infra(sources: dict[str, Any], inventory: dict[str, Any]) -> None:
    section("Dominios, correos, firmas y warmup", "Preparado para Hostinger, Zapmail y Snov warmup, sin conectar APIs.")
    c1, c2, c3, c4 = st.columns(4)
    boxes = [
        ("Dominios", "Pendiente", "Proveedor y fecha de creacion aun no normalizados."),
        ("Correos", "Pendiente", "Casillas por dominio listas para modelar."),
        ("Firmas", f"{len(inventory['signature_files'])} detectadas", "Requiere seleccionar version vigente."),
        ("Warmup", "Pendiente", "Snov warmup preparado como entidad."),
    ]
    for col, (title, value, sub) in zip([c1, c2, c3, c4], boxes):
        with col:
            st.markdown(f'<div class="kpi"><small>{title}</small><strong>{value}</strong><span>{sub}</span></div>', unsafe_allow_html=True)

    sig_rows = []
    for p in inventory["signature_files"]:
        sig_rows.append({
            "Archivo": str(p.relative_to(ROOT)),
            "Tipo": p.suffix.lower(),
            "Estado": "Pendiente revisar" if "html" not in p.suffix.lower() else "Reutilizable",
        })
    st.dataframe(pd.DataFrame(sig_rows), use_container_width=True, hide_index=True)


def render_ghl_sdr(sources: dict[str, Any]) -> None:
    section("Usuarios GHL y SDR", "Lectura local actual; validar antes de usar como configuracion canonica.")
    ghl = sources["ghl_config"] or {}
    sdrs = ghl.get("sdrs") or []
    left, right = st.columns([1.2, 1])
    with left:
        rows = []
        for s in sdrs:
            email = s.get("email", "")
            alerts = []
            if "bambutech" in str(email).lower():
                alerts.append("Dominio Bambutech en config GBS")
            rows.append({
                "Usuario": s.get("nombre"),
                "Rol": s.get("rol"),
                "Email": email,
                "GHL user id": s.get("ghl_user_id"),
                "Estado": "En revision" if alerts else "Pendiente confirmar",
                "Alertas": ", ".join(alerts),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    with right:
        st.markdown('<div class="panel"><h3>Configuracion GHL detectada</h3>', unsafe_allow_html=True)
        lines = [
            ("Location ID local", ghl.get("location_id", "No disponible")),
            ("Token local", "Detectado en archivo" if ghl.get("api_key") else "No disponible"),
            ("Usuarios", len(sdrs)),
            ("Estado", "Riesgo alto: validar antes de sync"),
        ]
        st.markdown("".join(f'<div class="line"><span>{k}</span><span>{v}</span></div>' for k, v in lines), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


def render_checklist(sources: dict[str, Any], inventory: dict[str, Any]) -> None:
    section("Checklist de lanzamiento", "Readiness operativo para pasar de setup a prospeccion.")
    estado = sources["estado"]
    manifest = sources["manifest"]
    ghl = sources["ghl_config"] or {}
    checks = [
        ("Intake recibido", bool(sources["onboarding"]), "done" if sources["onboarding"] else "warn"),
        ("ICP definido", bool(estado.get("icp_tipo_cliente") or estado.get("icp_cargos")), "done"),
        ("ICP aprobado", estado.get("estado_icp") == "icp_aprobado", "done" if estado.get("estado_icp") == "icp_aprobado" else "warn"),
        ("Dominios listos", False, "bad"),
        ("Correos listos", False, "bad"),
        ("Firmas listas", len(inventory["signature_files"]) > 0, "warn"),
        ("Warmup listo", False, "bad"),
        ("BBDD lista", len(manifest) > 0 or len(inventory["root_data"]) > 0, "done"),
        ("Campanas listas", len(manifest) > 0, "warn"),
        ("SDR asignado", bool((ghl.get("sdrs") or [])), "warn"),
        ("GHL listo", False, "bad"),
        ("Historial activo", bool(sources["normalized"].get("history")), "warn"),
    ]
    html = '<div class="timeline">'
    for name, ok, tone in checks:
        label = "Listo" if ok and tone == "done" else ("Revisar" if ok or tone == "warn" else "Pendiente")
        html += f'<div class="step {tone}"><b>{name}</b><small>{label}</small></div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_history(sources: dict[str, Any]) -> None:
    section("Historial y aprendizaje operacional", "Registro preparado para iterar segmentos y decisiones.")
    hist = sources["normalized"].get("history") or []
    if hist:
        st.dataframe(pd.DataFrame(hist), use_container_width=True, hide_index=True)
    else:
        rows = [
            {"Fecha": "2026-05-16", "Accion": "Creacion estructura GBS", "Usuario": "Operacion", "Observaciones": "Se crea carpeta CLIENTES/GBS_LOGISTICS."},
            {"Fecha": "2026-05-29", "Accion": "Clasificacion base Snov", "Usuario": "Operacion", "Observaciones": "Se genera scoring ICP y archivos para Snov/GHL."},
            {"Fecha": "2026-06-02", "Accion": "Plan campanas Snov", "Usuario": "Operacion", "Observaciones": "Se documentan campanas Chile, Peru y Colombia."},
            {"Fecha": datetime.now().strftime("%Y-%m-%d"), "Accion": "Fase 1 Client Setup OS", "Usuario": get_current_user() or "Operacion", "Observaciones": "Se centraliza lectura piloto sin APIs externas."},
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.markdown(
        '<div class="panel"><h3>Aprendizajes iniciales GBS</h3>'
        '<div class="line"><span>Segmento con mejor senal</span><span>Chile / Mineria / Comercio Exterior</span></div>'
        '<div class="line"><span>Hipotesis a validar</span><span>Peru Retail y Colombia Equipamiento Medico</span></div>'
        '<div class="line"><span>Riesgo operacional</span><span>Campanas y BBDD requieren normalizacion antes de escalar</span></div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_risks(sources: dict[str, Any], inventory: dict[str, Any]) -> None:
    section("Riesgos detectados", "Normalizacion necesaria antes de convertir GBS en plantilla para otros clientes.")
    risks = build_risks(sources, inventory)
    if risks:
        st.dataframe(pd.DataFrame(risks), use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="ok-box">No hay riesgos criticos detectados en la lectura actual.</div>', unsafe_allow_html=True)

    duplicates = inventory["duplicate_names"][:40]
    if duplicates:
        with st.expander("Archivos duplicados detectados", expanded=False):
            st.dataframe(
                pd.DataFrame({"Archivo": [str(p.relative_to(ROOT)) for p in duplicates]}),
                use_container_width=True,
                hide_index=True,
            )


def render_model() -> None:
    section("Modelo de datos propuesto", "Migracion creada como propuesta; pendiente ejecutar tras aprobacion.")
    tables = [
        ("client_setup", "Cabecera canonica por cliente y estado general de setup."),
        ("client_setup_steps", "Checklist operacional con responsables, estados y fechas."),
        ("client_icp_profiles", "Target Market Profile principal versionable."),
        ("client_icp_segments", "Subsegmentos iterables con BBDD, campanas, SDR y aprendizaje."),
        ("client_target_accounts", "Empresas objetivo."),
        ("client_excluded_accounts", "Clientes actuales, historicos, competidores y exclusiones."),
        ("client_domains", "Dominios y proveedor."),
        ("client_mailboxes", "Casillas por dominio/proveedor."),
        ("client_email_signatures", "Firmas asignadas e implementacion."),
        ("client_warmup", "Warmup por casilla."),
        ("client_databases", "BBDD por fuente, pais, industria, cargo y segmento."),
        ("client_campaigns", "Campanas por plataforma, segmento, estado y calidad."),
        ("client_sdr_assignments", "Asignacion SDR por cliente/segmento."),
        ("client_setup_history", "Historial y auditoria de cambios."),
    ]
    st.dataframe(pd.DataFrame(tables, columns=["Tabla", "Proposito"]), use_container_width=True, hide_index=True)
    st.markdown(
        f'<div class="warn-box">Archivo creado: <b>{MIGRATION_PATH.relative_to(ROOT)}</b>. No fue ejecutado contra Supabase.</div>',
        unsafe_allow_html=True,
    )
    with st.expander("Ver SQL propuesto", expanded=False):
        st.code(_read_text(MIGRATION_PATH), language="sql")


def main() -> None:
    css()
    sources, inventory = load_all()
    header(sources, inventory)

    tabs = st.tabs([
        "Resumen",
        "Intake",
        "ICP y segmentos",
        "Campanas y BBDD",
        "Correo y warmup",
        "GHL / SDR",
        "Checklist",
        "Historial",
        "Riesgos",
        "Modelo datos",
    ])

    with tabs[0]:
        section("Flujo operativo futuro", "Onboarding -> Client Setup OS -> Apollo -> Snov -> GHL -> SDR -> Reuniones -> Validacion -> Revenue Intelligence")
        st.markdown(
            '<div class="panel">'
            '<div class="timeline">'
            '<div class="step done"><b>Onboarding</b><small>Portal cliente captura intake</small></div>'
            '<div class="step warn"><b>Client Setup OS</b><small>Operacion normaliza y decide</small></div>'
            '<div class="step warn"><b>Apollo</b><small>Preparado, sin API</small></div>'
            '<div class="step warn"><b>Snov</b><small>Listas/campanas auditadas</small></div>'
            '<div class="step bad"><b>GHL</b><small>Validar config GBS</small></div>'
            '<div class="step warn"><b>SDR</b><small>Asignacion por segmento</small></div>'
            '<div class="step warn"><b>Validacion</b><small>Ya existe modulo</small></div>'
            '<div class="step warn"><b>Revenue Intelligence</b><small>Ya existe dashboard GBS</small></div>'
            '</div></div>',
            unsafe_allow_html=True,
        )
        render_checklist(sources, inventory)
        render_risks(sources, inventory)

    with tabs[1]:
        render_intake(sources)
    with tabs[2]:
        render_icp(sources)
    with tabs[3]:
        render_campaigns_databases(sources, inventory)
    with tabs[4]:
        render_infra(sources, inventory)
    with tabs[5]:
        render_ghl_sdr(sources)
    with tabs[6]:
        render_checklist(sources, inventory)
    with tabs[7]:
        render_history(sources)
    with tabs[8]:
        render_risks(sources, inventory)
    with tabs[9]:
        render_model()

    render_master_user_sidebar()


main()
