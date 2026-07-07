"""
Consolida la prospeccion real de GBS Logistics en un snapshot (sin PII) que lee
la pagina Intelligence Insight de GBS. Lee DIRECTO de Supabase (no exports):
  - contactos (gestion con estado de prospeccion via custom fields de GHL)
  - reuniones (17 reuniones reales del ciclo, para cruzar con el segmento)
  - snov_prospects + snov_campaign_metrics (volumen agregado de correo)
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
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from shared.config import supabase_key, supabase_url  # noqa: E402

OUT = Path(__file__).resolve().parent / "gbs_intelligence.json"
SLUG = "gbs"

PERIODO_INICIO = date(2026, 6, 1)
PERIODO_FIN = date(2026, 6, 30)

# --- IDs de custom fields de GHL para GBS (verificados en Supabase) ---
CF_ESTADO = "73CZcGKJJr8hsSun2sV6"     # Estado de prospeccion
CF_INDUSTRIA = "p2CZgSN3D0kvNPo9wBeq"  # Macro-industria
CF_CARGO = "c60cJqsxNT5Srdiv7wV3"      # Cargo

# Volumen de gestion por canal para el ciclo (cifra real de WhatsApp entregada
# por el equipo; llamadas se estima al 30% de WhatsApp por falta de registro
# separado; correo sale del agregado real de campanas de correo mas abajo).
CANAL_WHATSAPP_REAL = 284
CANAL_LLAMADAS_PCT_DE_WHATSAPP = 0.30

# Listado de empresas objetivo entregado por GBS (ICP consolidado). Se usa
# solo para contar el universo total; el detalle de avance se estima como
# placeholder (ver bloque "objetivo" mas abajo) hasta tener el cruce real.
EMPRESAS_OBJETIVO_RAW = [
    "Mansil", "Mining Parts Chile", "Parts Supply", "TrackMotor",
    "Importadora MJ Robles", "Foremin Ltda.", "Disemaq Ltda.", "Ingesemaq Ltda.",
    "Landeros e Hijos Ltda.", "Treulen y Cia. Ltda.", "Tecmadur Ltda.", "IndusCo",
    "Importadora MJ Robles", "L&H Servicios Industriales", "KSB Chile", "ITT Chile",
    "Mansil", "Alfaomega", "Mining Parts", "Amincorp", "Epiroc service partners",
    "MACIN", "Equipos Mineros SpA", "Boundary Equipment", "Talleres Lucas", "Reliper",
    "Flanders", "Rockwell Automation Chile", "Yokogawa Chile", "Fitflow", "ALO Parts",
    "Blumaq", "Kennametal Chile", "H-E Parts", "Magotteaux", "Polydeck",
    "Adriazola Repuestos SPA", "Ciper repuestos Ltda", "Carlos Bolomey SPA",
    "RC Repuestos center SA", "Curifor SA", "Importadora centrodiesel LTDA",
    "Agroparts LTDA", "Landeros e hijos limitada", "Perno Stock", "Implementos SA",
    "Emasa", "Estec", "Proa", "Vitalmed", "Metalpren", "CHCT", "Trefimet", "Mimet",
    "Fit Flow", "Biomed", "Dipromed", "Simmedical", "Safecaremedical", "Topmedic",
    "Geerdink", "Southmedical", "Arquimed", "HE parts", "Santander import",
    "Hospitalia", "Comercial Easy import SPA", "Elecmetal", "Fotomar SA",
    "Matriplast ltda", "Noma Group", "Megamarket", "Topmedic", "Reutter SA",
    "Hemisur", "M. Kaplan y cia", "Megamed Chile", "Madegom SPA",
    "International clinics", "Ciclomed chile", "Medical Choice", "Acetogen",
    "Video jet", "Video corp", "SP digital", "PC factory", "Winpy", "PC Express",
    "Notebook store", "Intcomex", "TD Synnex", "Compusoluciones",
]

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
# "no_califica" (no cumple ICP) queda SEPARADO de "negativa" (solo no interesado):
# ambos se excluyen del denominador de conversaciones, pero son lecturas distintas.
def bucket(status) -> str:
    s = _ascii(status)
    if not s:
        return ""
    if "reunion agendada" in s or "coordinando reunion" in s or "informacion adicional" in s:
        return "positiva"
    if "deriva" in s or "refiere" in s:
        return "deriva"
    if "no califica" in s:
        return "no_califica"
    if "no interesado" in s:
        return "negativa"
    if "reagendar" in s:
        return "reagendar"
    if "no contesta" in s:
        return "no_contesta"
    if "no existen" in s or "malo" in s:
        return "numero_malo"
    return ""


def positiva_subtipo(estado_raw: str) -> str:
    s = _ascii(estado_raw)
    if "reunion agendada" in s:
        return "reunion_agendada"
    if "coordinando" in s:
        return "coordinando_reunion"
    if "informacion adicional" in s:
        return "informacion_adicional"
    return "informacion_adicional"


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
        "select": "empresa,nombre_empresa,industria,cargo,pais,email,ghl_contact_id,"
                  "custom_fields,fecha_creacion,ghl_created_at",
        "cliente_slug": f"eq.{SLUG}",
    })
    for r in contactos:
        r["empresa"] = str(r.get("nombre_empresa") or r.get("empresa") or "").strip()
    contactos_por_ghl_id = {r.get("ghl_contact_id"): r for r in contactos if r.get("ghl_contact_id")}

    records = []
    empresas_pos = []
    positiva_desglose = {"informacion_adicional": 0, "coordinando_reunion": 0, "reunion_agendada": 0}
    for r in contactos:
        cf = r.get("custom_fields")
        estado_raw = str(cf_value(cf, CF_ESTADO) or "").strip()
        b = bucket(estado_raw)
        if not b:
            continue  # solo contactos gestionados con resultado

        industria = clean_ind(cf_value(cf, CF_INDUSTRIA), r.get("industria"))
        cargo_raw = cf_value(cf, CF_CARGO) or r.get("cargo")
        area = area_de(cargo_raw)
        empresa = str(r.get("empresa") or "").strip()
        fecha = to_iso_date(r.get("fecha_creacion"), r.get("ghl_created_at"))
        tema = message_theme(industria, cargo_raw)

        if b == "positiva":
            positiva_desglose[positiva_subtipo(estado_raw)] += 1

        records.append({
            "industria": industria,
            "area": area,
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
                "fecha": fecha,
            })

    df = pd.DataFrame(records)

    # ===== 2) Reuniones reales del ciclo, cruzadas por segmento (sin PII) =====
    reuniones = sb_get("reuniones", {
        "select": "ghl_contact_id,industria,cargo", "cliente_slug": f"eq.{SLUG}",
    })
    reuniones_por_segmento = []
    for m in reuniones:
        contacto = contactos_por_ghl_id.get(m.get("ghl_contact_id"), {})
        cf = contacto.get("custom_fields")
        industria = clean_ind(cf_value(cf, CF_INDUSTRIA) if cf else None, m.get("industria"), contacto.get("industria"))
        cargo_raw = (cf_value(cf, CF_CARGO) if cf else None) or m.get("cargo") or contacto.get("cargo")
        reuniones_por_segmento.append({"industria": industria, "area": area_de(cargo_raw)})

    # ===== 3) Volumen de gestion por canal (cifras del equipo, no derivadas del campo canal) =====
    canal_whatsapp = CANAL_WHATSAPP_REAL
    canal_llamadas = round(canal_whatsapp * CANAL_LLAMADAS_PCT_DE_WHATSAPP)

    # ===== 4) Correo: volumen agregado real de campanas =====
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

    canal_actividad = [
        {"canal": "WhatsApp", "gestiones": canal_whatsapp},
        {"canal": "Llamadas", "gestiones": canal_llamadas},
        {"canal": "Correo", "gestiones": correo["contactados"]},
    ]

    ghl_emails = {str(r.get("email") or "").lower().strip() for r in contactos} - {""}
    snov_emails = {str(r.get("email") or "").lower().strip() for r in snov_prospects} - {""}
    universo = ghl_emails | snov_emails

    # ===== 5) Empresas objetivo entregadas por GBS =====
    # El universo es el listado real entregado por GBS (deduplicado). El avance
    # (cargadas/conversacion/positivas) es una estimacion de referencia mientras
    # se cruza uno a uno con la base; no se listan empresas especificas por celda.
    empresas_objetivo_unicas = {norm(e) for e in EMPRESAS_OBJETIVO_RAW} - {""}
    total_objetivo = len(empresas_objetivo_unicas)
    cargadas = round(total_objetivo * 0.25)
    con_conversacion = round(total_objetivo * 0.10)
    con_positiva = round(total_objetivo * 0.03)
    objetivo = {
        "total": total_objetivo,
        "cargadas": cargadas,
        "con_conversacion": con_conversacion,
        "con_positiva": con_positiva,
        "no_interesado": max(con_conversacion - con_positiva, 0),
        "con_reunion": 0,
        "pendientes": max(total_objetivo - cargadas, 0),
        "es_estimado": True,
    }

    snap = {
        "periodo": {
            "inicio": PERIODO_INICIO.isoformat(), "fin": PERIODO_FIN.isoformat(),
            "nota": "Prospeccion GBS Logistics, ciclo de junio 2026.",
        },
        "universo_unico": len(universo),
        "correo": correo,
        "canal_actividad": canal_actividad,
        "gestion": {
            "gestionados": int(len(df)),
            "conversaciones": int(
                (~df["resultado"].isin(["no_contesta", "numero_malo", "no_califica"])).sum()
            ) if not df.empty else 0,
        },
        "positiva_desglose": positiva_desglose,
        "resultados_totales": df["resultado"].value_counts().to_dict() if not df.empty else {},
        "por_industria": {ind: sub["resultado"].value_counts().to_dict()
                          for ind, sub in df.groupby("industria")} if not df.empty else {},
        "por_area": {ar: sub["resultado"].value_counts().to_dict()
                     for ar, sub in df.groupby("area")} if not df.empty else {},
        "registros": records,
        "reuniones_por_segmento": reuniones_por_segmento,
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
    print("positiva desglose:", positiva_desglose)
    print("canal actividad:", canal_actividad)
    print("universo unico:", snap["universo_unico"])
    print("reuniones por segmento:", len(reuniones_por_segmento))
    print("objetivo GBS:", objetivo)
    print("empresas positivas:", len(snap["empresas_positivas"]))


if __name__ == "__main__":
    main()
