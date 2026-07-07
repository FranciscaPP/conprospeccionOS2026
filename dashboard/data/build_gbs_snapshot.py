"""
Consolida la prospeccion real de GBS Logistics en un snapshot (sin PII) que lee
la pagina Intelligence Insight de GBS. Lee DIRECTO de Supabase (no exports):
  - contactos (gestion WhatsApp/llamada/correo con estado de prospeccion)
  - snov_prospects + snov_campaign_metrics (universo y volumen de correo)
Se corre 1x/mes.

Uso:
    python dashboard/data/build_gbs_snapshot.py

Salida: dashboard/data/gbs_intelligence.json  (solo dimensiones/agregados)
NUNCA escribe nombres/emails/telefonos de contactos en la salida.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from shared.config import supabase_key, supabase_url  # noqa: E402

OUT = Path(__file__).resolve().parent / "gbs_intelligence.json"
SLUG = "gbs"

# --- IDs de custom fields de GHL para GBS (verificados en Supabase) ---
CF_ESTADO = "73CZcGKJJr8hsSun2sV6"     # Estado de prospeccion
CF_CANAL = "mipcTmLgax5URM1q3Mut"      # Canal: WHATSAPP / LLAMADA / CORREO
CF_INDUSTRIA = "p2CZgSN3D0kvNPo9wBeq"  # Macro-industria
CF_CARGO = "c60cJqsxNT5Srdiv7wV3"      # Cargo

SB_URL = supabase_url().rstrip("/")
SB_KEY = supabase_key()
HEADERS = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"}


def _ascii(x) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    return unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode().lower().strip()


def norm(x) -> str:
    s = _ascii(x)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    for w in ("spa", "s a", "ltda", "limitada", "sa", "chile", "peru", "colombia",
              "grupo", "inc", "corp", "company", "comercial", "importadora", "the"):
        s = re.sub(rf"\b{w}\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def sb_get(table: str, params: dict) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        q = dict(params)
        q["limit"] = 1000
        q["offset"] = offset
        resp = requests.get(f"{SB_URL}/rest/v1/{table}", headers=HEADERS, params=q, timeout=30)
        resp.raise_for_status()
        batch = resp.json()
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return rows


def cf_value(custom_fields, field_id: str):
    if not isinstance(custom_fields, list):
        return None
    for field in custom_fields:
        if isinstance(field, dict) and field.get("id") == field_id:
            return field.get("value")
    return None


# ---- Macro-industria para el ICP de GBS (importadores/exportadores) ----
def clean_ind(*vals) -> str:
    for x in vals:
        t = _ascii(x)
        if not t:
            continue
        if any(k in t for k in ("mineria", "minera", "mining", "metal", "acero", "steel")):
            return "Mineria y Metales"
        if any(k in t for k in ("food", "beverage", "aliment", "bebida", "wine", "vino",
                                "farming", "agro", "produccion de aliment")):
            return "Alimentos, Bebidas y Agro"
        if any(k in t for k in ("machinery", "maquinaria", "industrial engineering",
                                "mechanical", "electr", "manufactur", "equipos")):
            return "Maquinaria e Industria"
        if any(k in t for k in ("automot", "vehicul", "autopart")):
            return "Automotriz"
        if any(k in t for k in ("retail", "consumo", "wholesale", "mayor", "apparel",
                                "fashion", "moda", "comercio")):
            return "Retail y Consumo"
        if any(k in t for k in ("construc", "building material", "materiales", "civil eng",
                                "inmobil")):
            return "Construccion y Materiales"
        if any(k in t for k in ("health", "hospital", "medic", "pharma", "farma", "clinic",
                                "device")):
            return "Salud y Farma"
        if any(k in t for k in ("import", "export", "comex", "comercio exterior", "trading")):
            return "Importacion / Exportacion"
    return "Sin clasificar"


# ---- Macro-cargo = AREA funcional para el ICP de GBS (COMEX / abastecimiento) ----
def area_de(cargo_raw) -> str:
    t = _ascii(cargo_raw)
    if not t:
        return "Sin clasificar"

    def has(*kw):
        return any(k in t for k in kw)

    if has("comex", "comercio exterior", "importacion", "importaciones", "foreign trade",
           "export manager", "import", "aduana", "customs"):
        return "Comercio Exterior / COMEX"
    if has("abastecim", "compras", "procurement", "purchasing", "adquisicion", "buyer"):
        return "Abastecimiento / Compras"
    if has("logist", "supply chain", "distribu", "bodega", "warehouse", "transporte",
           "despacho", "planificacion y control"):
        return "Logistica / Supply Chain"
    if has("ceo", "founder", "fundador", "dueno", "owner", "presidente", "director general",
           "gerente general", "propietario", "general manager", "socio"):
        return "Direccion / Gerencia"
    if has("operaci", "operations", "planta", "produccion", "manufactura", "calidad"):
        return "Operaciones"
    if has("finanz", "finance", "cfo", "contab", "controller", "tesorer", "administ"):
        return "Finanzas / Administracion"
    if has("venta", "sales", "comercial", "marketing", "business development", "cuenta"):
        return "Comercial / Ventas"
    return "Otros"


# ---- Resultado / bucket de la conversacion (estado GHL de GBS) ----
def bucket(status) -> str:
    s = _ascii(status)
    if not s:
        return ""
    if "reunion agendada" in s or "coordinando reunion" in s or "informacion adicional" in s:
        return "positiva"
    if "deriva" in s or "refiere" in s:
        return "deriva"
    if "no califica" in s or "no interesado" in s:
        return "negativa"
    if "reagendar" in s:
        return "reagendar"
    if "no contesta" in s:
        return "no_contesta"
    if "no existen" in s or "malo" in s:
        return "numero_malo"
    return ""


# ---- Tema/mensaje inferido para el ICP de GBS ----
def message_theme(industria: str, cargo_raw: str) -> str:
    t = _ascii(f"{industria} {cargo_raw}")
    rules = [
        ("Carga temperada (vino y alimentos)", ("aliment", "bebida", "wine", "vino", "food")),
        ("Importacion de maquinaria y repuestos", ("machinery", "maquinaria", "industria", "equipos", "mineria", "metal")),
        ("Servicio integral puerta a puerta", ("comex", "importacion", "abastecim", "compras", "logist")),
        ("Reduccion de costos y visibilidad de carga", ("retail", "consumo", "automot", "construc")),
    ]
    for label, keys in rules:
        if any(k in t for k in keys):
            return label
    return "Un solo interlocutor logistico"


def estado_display(estado_raw: str) -> str:
    s = _ascii(estado_raw)
    if "reunion agendada" in s:
        return "Reunion agendada"
    if "coordinando" in s:
        return "Coordinando reunion"
    if "informacion adicional" in s:
        return "Informacion adicional"
    return estado_raw or "Interes"


def to_iso_date(*vals):
    for raw in vals:
        if not str(raw or "").strip():
            continue
        parsed = pd.to_datetime(raw, errors="coerce", utc=True)
        if not pd.isna(parsed):
            return parsed.date().isoformat()
    return None


def main() -> None:
    # ===== 1) Contactos GBS (gestion real con estado de prospeccion) =====
    contactos = sb_get("contactos", {
        "select": "empresa,nombre_empresa,industria,cargo,pais,email,custom_fields,fecha_creacion,ghl_created_at",
        "cliente_slug": f"eq.{SLUG}",
    })
    for r in contactos:
        r["empresa"] = str(r.get("nombre_empresa") or r.get("empresa") or "").strip()

    records = []
    empresas_pos = []
    for r in contactos:
        cf = r.get("custom_fields")
        estado_raw = str(cf_value(cf, CF_ESTADO) or "").strip()
        b = bucket(estado_raw)
        if not b:
            continue  # solo contactos gestionados con resultado

        canal_raw = str(cf_value(cf, CF_CANAL) or "").strip().upper()
        canal = {"WHATSAPP": "WhatsApp", "LLAMADA": "Llamadas", "CORREO": "Correo"}.get(
            canal_raw, "WhatsApp")
        industria = clean_ind(cf_value(cf, CF_INDUSTRIA), r.get("industria"))
        cargo_raw = cf_value(cf, CF_CARGO) or r.get("cargo")
        area = area_de(cargo_raw)
        empresa = str(r.get("empresa") or "").strip()
        fecha = to_iso_date(r.get("fecha_creacion"), r.get("ghl_created_at"))
        tema = message_theme(industria, cargo_raw)

        records.append({
            "industria": industria,
            "area": area,
            "canal": canal,
            "campana": "Prospeccion GBS",
            "resultado": b,
            "estado_raw": estado_raw,
            "fecha": fecha,
            "empresa": empresa,
            "tema": tema,
        })
        if b in ("positiva", "deriva") and empresa:
            empresas_pos.append({
                "empresa": empresa,
                "estado": estado_display(estado_raw) if b == "positiva" else "Deriva / refiere a decisor",
                "industria": industria,
                "area": area,
                "canal": canal,
                "fecha": fecha,
            })

    df = pd.DataFrame(records)

    # ===== 2) Snov: universo de correo + volumen agregado =====
    snov_prospects = sb_get("snov_prospects", {
        "select": "email,empresa", "cliente_slug": f"eq.{SLUG}",
    })
    metrics = sb_get("snov_campaign_metrics", {
        "select": "emails_sent,recipients_contacted,email_opens,email_replies,bounced,unsubscribed,auto_replied",
        "cliente_slug": f"eq.{SLUG}",
    })

    def msum(key):
        return int(sum(int(m.get(key) or 0) for m in metrics))

    enviados = msum("emails_sent")
    rebotes = msum("bounced")
    correo = {
        "enviados": enviados,
        "entregados": max(enviados - rebotes, 0),
        "contactados": msum("recipients_contacted"),
        "rebotes": rebotes,
        "respuestas": msum("email_replies"),
        "aperturas": msum("email_opens"),
        "auto_respuestas": msum("auto_replied"),
        "bajas": msum("unsubscribed"),
    }

    ghl_emails = {str(r.get("email") or "").lower().strip() for r in contactos} - {""}
    snov_emails = {str(r.get("email") or "").lower().strip() for r in snov_prospects} - {""}
    universo = ghl_emails | snov_emails

    # ===== 3) Cobertura de cuentas (empresas alcanzadas vs gestionadas) =====
    empresas_universo = (
        {norm(r.get("empresa")) for r in contactos}
        | {norm(r.get("empresa")) for r in snov_prospects}
    ) - {""}
    empresas_gestionadas = {norm(e) for e in df["empresa"]} - {""} if not df.empty else set()
    total_cuentas = len(empresas_universo)
    prospectadas = len(empresas_gestionadas & empresas_universo)
    objetivo = {
        "total": total_cuentas,
        "prospectadas": prospectadas,
        "pct": round(prospectadas / total_cuentas * 100) if total_cuentas else 0,
        "pendientes": max(total_cuentas - prospectadas, 0),
    }

    # ===== 4) Periodo =====
    fechas = pd.to_datetime(df["fecha"], errors="coerce").dropna() if not df.empty else pd.Series([], dtype="datetime64[ns]")
    inicio = fechas.min().date().isoformat() if not fechas.empty else "2026-06-01"
    fin = datetime.now(timezone.utc).date().isoformat()

    snap = {
        "periodo": {
            "inicio": inicio, "fin": fin,
            "nota": "Prospeccion GBS Logistics; canal principal WhatsApp, correo via Snov.",
        },
        "universo_unico": len(universo),
        "correo": correo,
        "gestion": {
            "gestionados": int(len(df)),
            "conversaciones": int(
                (~df["resultado"].isin(["no_contesta", "numero_malo"])).sum()
            ) if not df.empty else 0,
        },
        "resultados_totales": df["resultado"].value_counts().to_dict() if not df.empty else {},
        "por_industria": {ind: sub["resultado"].value_counts().to_dict()
                          for ind, sub in df.groupby("industria")} if not df.empty else {},
        "por_area": {ar: sub["resultado"].value_counts().to_dict()
                     for ar, sub in df.groupby("area")} if not df.empty else {},
        "registros": records,
        "objetivo": objetivo,
        "empresas_positivas": list({
            norm(e["empresa"]): e for e in empresas_pos if norm(e["empresa"])
        }.values())[:30],
    }
    OUT.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
    print("OK ->", OUT)
    print("gestionados:", snap["gestion"]["gestionados"],
          "| conversaciones:", snap["gestion"]["conversaciones"])
    print("resultados:", snap["resultados_totales"])
    print("universo unico:", snap["universo_unico"])
    print("correo:", correo)
    print("cobertura cuentas:", objetivo)
    print("empresas positivas:", len(snap["empresas_positivas"]))


if __name__ == "__main__":
    main()
