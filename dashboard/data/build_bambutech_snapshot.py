"""
Consolida la prospeccion real de BambuTech en un snapshot (sin PII) que lee
la pagina Intelligence Insight. Cruza: llamadas/WhatsApp + correo + empresas
objetivo.

Fuente de RESULTADOS (llamadas/WhatsApp): Supabase `contactos` (cliente_slug=
bambutech), alimentado desde GoHighLevel por el sync nocturno. Ya no depende de
un export manual GHL.csv.

Fuente de CORREO (agregados): Supabase `snov_campaign_metrics`. Si esa tabla no
tiene metricas frescas de bambutech (p. ej. la cuenta Snov choca con rate limit),
se usa CORREO_FALLBACK y se avisa por consola para que se actualice a mano con las
cifras del panel.

Universo de correo + empresas objetivo: listas exportadas (xlsx/csv) en la
carpeta origen (por defecto ~/Downloads); los conteos son sobre SETS de emails/
empresas, asi que archivos repetidos son idempotentes.

Uso:
    python dashboard/data/build_bambutech_snapshot.py [carpeta_origen]

Salida: dashboard/data/bambutech_intelligence.json  (solo dimensiones/agregados)
NUNCA escribe nombres/emails/telefonos de contactos en la salida.
"""
import sys, re, json, glob, unicodedata
from datetime import date
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "sync" / "scripts"))
from config import get_settings  # noqa: E402
from supabase_rest import SupabaseRestClient  # noqa: E402

SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Downloads"
OUT = Path(__file__).resolve().parent / "bambutech_intelligence.json"

# --- IDs de custom field de la location BambuTech (FJ1YCwi4UVvwcBb8qlOb) ---
CF_STATUS = "m3cYnSBB5t6WPArnU67e"   # STATUS PROSPECTO
CF_CANAL = "pxaRGkfmT0ATBc2TvxCt"    # CANAL DE CONTACTO
CF_MACRO_IND = "xoBxn9yxTX7irSmlG7an"  # MACRO INDUSTRIA
CF_CARGO_MACRO = "mWjVPW2PODOJWzAF3DBb"  # CARGO MACRO

# Periodo del reporte. Inicio = arranque real de prospeccion; fin = hoy.
PERIODO_INICIO = "2026-05-18"
PERIODO_FIN = date.today().isoformat()

# Agregados de correo del panel (Snov). Se usan solo si Supabase no trae metricas
# frescas de bambutech. ACTUALIZAR A MANO con las cifras del panel cuando cambien.
# Cifras dadas por la clienta (jul->hoy): 811 contactos en julio + 157 a la fecha
# = 968 contactos por correo; 7 respuestas, todas negativas. Rebotes/bajas sin dato -> 0.
CORREO_FALLBACK = {"enviados": 968, "contactados": 968, "entregados": 968,
                   "rebotes": 0, "respuestas": 7, "respuestas_negativas": 7,
                   "auto_respuestas": 0, "bajas": 0}


def norm(x):
    if x is None or isinstance(x, float):
        return ""
    s = unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    for w in ("grupo", "sa de cv", "s a de c v", "sa", "cv", "de cv", "mexico",
              "the", "inc", "corp", "compania", "company", "sab", "s a b"):
        s = re.sub(rf"\b{w}\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def company_display(x):
    value = str(x or "").strip()
    aliases = {
        "grupo maxima": "EMWA",
    }
    return aliases.get(norm(value), value)


def activity_date(last_activity, created):
    for raw in (last_activity, created):
        if not str(raw or "").strip():
            continue
        parsed = pd.to_datetime(raw, errors="coerce", utc=True)
        if not pd.isna(parsed):
            return parsed.date().isoformat()
    return None


def message_theme(campaign, meeting_info):
    text = _ascii(f"{campaign} {meeting_info}")
    rules = [
        ("Ciberseguridad", ("ciber", "seguridad")),
        ("IA aplicada", (" inteligencia artificial", " ia ", "machine learning")),
        ("Cloud / escalabilidad", ("cloud", "nube", "escalab")),
        ("Integración de sistemas", ("integracion", "sistemas", "tecnologia")),
        ("Automatización de procesos", ("automatiz", "op critica", "procesos")),
        ("Productividad operativa", ("logistica", "productividad", "tiempo", "operacion")),
        ("Plataformas web / apps", ("retail", "plataforma", "app", "web")),
        ("Software a medida", ("servicios", "software", "desarrollo")),
    ]
    return next((label for label, keys in rules if any(k in f" {text} " for k in keys)),
                "Transformación digital")


def find(df, *subs):
    for c in df.columns:
        cu = str(c).upper()
        if all(s.upper() in cu for s in subs):
            return c
    return None


# ---- Limpieza de macro-industria (la columna origen trae cargos y vacíos) ----
def _ascii(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    return unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode().lower().strip()


def clean_ind(*vals):
    for x in vals:
        t = _ascii(x)
        if not t:
            continue
        if any(k in t for k in ("manufactura", "mineria", "minera", "industrial", "energia",
                                "acero", "metal", "quimic", "cemento", "automotriz", "autopart")):
            return "Industrial / Manufactura / Minería / Energía"
        if any(k in t for k in ("logistica", "transporte", "supply", "carga", "almacen", "freight")):
            return "Logística / Transporte / Supply Chain"
        if any(k in t for k in ("salud", "farma", "hospital", "medic", "clinic", "pharma")):
            return "Salud / Farma / Hospitales"
        if any(k in t for k in ("retail", "consumo", "multisucursal", "alimentos", "bebidas",
                                "comercio", "moda", "abarrotes")):
            return "Retail / Consumo / Multisucursal"
        if any(k in t for k in ("financ", "banca", "banco", "fintech", "seguro", "credito")):
            return "Banca / Servicios Financieros"
        if any(k in t for k in ("tecnolog", "software", "telecom", "ti ", "saas")):
            return "Tecnología / Telecom"
        if any(k in t for k in ("construc", "inmobil", "real estate")):
            return "Construcción / Inmobiliario"
    return "Sin clasificar"  # descarta basura tipo CEO/COO/Revisar


# ---- Clasificación macro-cargo = ÁREA funcional (no seniority) ----


def area_de(cargo_macro, cargo_raw):
    # 1) Usar el macro-cargo ya curado en origen (más confiable)
    cm = _ascii(cargo_macro)
    if cm and cm != "revisar":
        if "tecnolog" in cm or "transformacion" in cm or "seguridad informatica" in cm:
            return "Tecnología / Transformación"
        if "operaci" in cm or "proceso" in cm:
            return "Operaciones / Procesos"
        if "riesgo" in cm:
            return "Riesgo / Seguridad"
        if "mercado" in cm or "cx" in cm or "rentabilidad" in cm or "comercial" in cm:
            return "Comercial / Marketing"
        if "finanz" in cm:
            return "Finanzas"
        if "humano" in cm or "rrhh" in cm:
            return "Recursos Humanos"
        if "negocio" in cm or "direccion" in cm:
            return "Dirección / Negocio"
    # 2) Fallback: clasificar por el cargo crudo
    t = _ascii(cargo_raw)
    def has(*kw): return any(k in t for k in kw)
    if has("ceo", "founder", "fundador", "dueno", "owner", "presidente",
           "director general", "gerente general", "propietario", "general manager"):
        return "Dirección / Negocio"
    if has("cfo", "finanz", "finance", "contab", "tesorer", "controller", "fiscal"):
        return "Finanzas"
    if has("rrhh", "recursos humanos", "human resource", " hr", "talent", "talento",
           "recruit", "reclut", "beneficios", "nomina", "capacitacion"):
        return "Recursos Humanos"
    if has("cto", "cio", "ciso", "tecnolog", "software", "sistemas", "data",
           "analytics", "desarroll", "ingenier", "digital", "transformacion",
           "cyber", "informatica"):
        return "Tecnología / Transformación"
    if has("coo", "operaci", "operations", "supply", "logist", "almacen", "abastec",
           "planta", "manufactura", "produccion", "calidad", "compras", "procurement"):
        return "Operaciones / Procesos"
    if has("venta", "sales", "comercial", "business development", "revenue",
           "growth", "marketing", "cmo", "marca", "brand", "mercado"):
        return "Comercial / Marketing"
    if has("riesgo", "risk", "compliance", "cumplimiento", "auditor", "legal", "juridico"):
        return "Riesgo / Seguridad"
    return "Otros"


# ---- Resultado / bucket de la conversación ----
POS = {"informacion adicional", "coordinando reunion", "reunion agendada"}
NEG = {"no interesado", "no califica"}
def bucket(status):
    s = unicodedata.normalize("NFKD", str(status or "")).encode("ascii", "ignore").decode().lower().strip()
    if s in POS: return "positiva"
    if "deriva" in s or "refiere" in s: return "deriva"
    if s in NEG: return "negativa"
    if "reagendar" in s: return "reagendar"
    if "no contesta" in s: return "no_contesta"
    if "no existen" in s or "malo" in s: return "numero_malo"
    return ""


def cf_value(custom_fields, field_id):
    """Valor de un custom field de GHL por id, desde el array crudo de Supabase."""
    for cf in custom_fields or []:
        if isinstance(cf, dict) and cf.get("id") == field_id:
            return cf.get("value")
    return None


def correo_desde_supabase(supabase):
    """Agregados de correo desde snov_campaign_metrics (suma de campañas bambutech)."""
    rows = supabase.select(
        "snov_campaign_metrics",
        "recipients_contacted,emails_sent,email_replies,auto_replied,bounced,unsubscribed",
        cliente_slug="eq.bambutech",
    )
    if not rows:
        return None
    def s(k):
        return int(sum((r.get(k) or 0) for r in rows))
    enviados = s("emails_sent")
    rebotes = s("bounced")
    return {
        "enviados": enviados,
        "contactados": s("recipients_contacted"),
        "entregados": max(enviados - rebotes, 0),
        "rebotes": rebotes,
        "respuestas": s("email_replies"),
        "auto_respuestas": s("auto_replied"),
        "bajas": s("unsubscribed"),
    }


def leer_listas_correo(src):
    """Universo de correo (emails) + campaña por email + set de empresas prospectadas,
    desde listas Snov exportadas (xlsx o csv). Idempotente ante archivos repetidos."""
    CAMP_NICE = {
        "logistica": "Logística", "retail": "Retail",
        "op-critica": "Op. Crítica y Continuidad", "tecnologia": "Tecnología",
        "servicios": "Servicios", "final-15-junio": "Campaña 15 Junio",
        "campana_mx_final": "Campaña MX", "mineria-ti": "Minería / TI",
        "21-de-julio": "Campaña 21 Julio", "rrhh": "RRHH",
    }
    # Exports de campaña Snov: convención con guion (bambutech-<segmento>) en xlsx/csv,
    # más la lista RRHH. Excluye adrede staging de import, FAQ y señales sueltas.
    patrones = ["bambutech*.xlsx", "bambutech-*.csv", "rrhh-bambutech*.csv"]
    archivos = sorted({f for p in patrones for f in glob.glob(str(src / p))})
    camp_por_email, snov_emails, prospec = {}, set(), set()
    for f in archivos:
        try:
            if f.lower().endswith(("xlsx", "xls")):
                d = pd.read_excel(f, dtype=str)
            else:
                try:
                    d = pd.read_csv(f, dtype=str, on_bad_lines="skip")
                except UnicodeDecodeError:
                    d = pd.read_csv(f, dtype=str, on_bad_lines="skip", encoding="latin-1")
        except Exception as exc:  # noqa: BLE001
            print("  (aviso) no se pudo leer", Path(f).name, "->", exc)
            continue
        name = Path(f).stem.lower()
        camp = next((v for k, v in CAMP_NICE.items() if k in name), "Correo")
        ce = find(d, "EMAIL") or find(d, "CORREO")
        if ce:
            for e in d[ce].dropna().map(lambda x: str(x).lower().strip()):
                if e:
                    snov_emails.add(e)
                    camp_por_email.setdefault(e, camp)
        cc = find(d, "Company name") or find(d, "NOMBRE", "EMPRESA") or find(d, "EMPRESA")
        if cc:
            prospec |= set(d[cc].dropna().map(norm)) - {""}
    return camp_por_email, snov_emails, prospec, archivos


def main():
    settings = get_settings()
    supabase = SupabaseRestClient(settings.supabase_url, settings.supabase_secret_key)

    # ===== 1) Resultados reales (llamadas/WhatsApp) desde Supabase =====
    contactos = supabase.select_all(
        "contactos",
        "nombre_empresa,email,industria,cargo,informacion_reunion,"
        "ghl_updated_at,ghl_created_at,custom_fields",
        cliente_slug="eq.bambutech",
    )
    print("contactos bambutech en Supabase:", len(contactos))

    camp_por_email, snov_emails, prospec_listas, archivos = leer_listas_correo(SRC)

    records = []  # solo dimensiones (sin PII)
    empresas_pos = []
    ghl_emails = set()
    for c in contactos:
        email = str(c.get("email") or "").lower().strip()
        if email:
            ghl_emails.add(email)
        cfs = c.get("custom_fields") or []
        status_raw = str(cf_value(cfs, CF_STATUS) or "").strip()
        b = bucket(status_raw)
        if not b:
            continue  # solo contactos gestionados con resultado
        canal_raw = str(cf_value(cfs, CF_CANAL) or "").strip().upper()
        canal = {"WHATSAPP": "WhatsApp", "LLAMADA": "Llamadas", "CORREO": "Correo"}.get(
            canal_raw, "Llamadas")
        industria = clean_ind(cf_value(cfs, CF_MACRO_IND), c.get("industria"))
        area = area_de(cf_value(cfs, CF_CARGO_MACRO), c.get("cargo"))
        campaign = camp_por_email.get(email, "Seguimiento multicanal")
        empresa = company_display(c.get("nombre_empresa"))
        fecha = activity_date(c.get("ghl_updated_at"), c.get("ghl_created_at"))
        tema = message_theme(campaign, c.get("informacion_reunion"))
        records.append({
            "industria": industria,
            "area": area,
            "canal": canal,
            "campana": campaign,
            "resultado": b,
            "estado_raw": status_raw,
            "fecha": fecha,
            "empresa": empresa,
            "tema": tema,
        })
        if b == "positiva" and empresa:
            estado_ascii = _ascii(status_raw)
            if "reunion agendada" in estado_ascii:
                estado = "Reunión agendada"
            elif "coordinando" in estado_ascii:
                estado = "Coordinando reunión"
            else:
                estado = "Información adicional"
            empresas_pos.append({
                "empresa": empresa,
                "estado": estado,
                "industria": industria,
                "area": area,
                "canal": canal,
                "fecha": fecha,
            })

    df = pd.DataFrame(records)

    # ===== 2) Universo deduplicado (correo + llamadas/WhatsApp) =====
    universo = ghl_emails | snov_emails

    # ===== 3) Empresas objetivo (One Off) y cruce =====
    one_off = list(SRC.glob("One Off*Pre Sales*.xlsx"))
    targets = set()
    prospec = set(str(c.get("nombre_empresa") or "") for c in contactos)
    prospec = {norm(x) for x in prospec} - {""}
    prospec |= prospec_listas
    if one_off:
        xl = pd.ExcelFile(sorted(one_off)[-1])
        for s in xl.sheet_names:
            raw = xl.parse(s, header=None)
            cols = raw.shape[1]
            it = ([raw[0]] if cols <= 5 else [raw.iloc[1:, c] for c in range(cols)])
            for col in it:
                for v in col.dropna():
                    if "\n" not in str(v) and 0 < len(str(v).split()) <= 5:
                        k = norm(v)
                        if len(k) >= 4:
                            targets.add(k)

    def matched(k):
        if k in prospec:
            return True
        if len(k) >= 5:
            return any(len(p) >= 5 and (k in p or p in k) for p in prospec)
        return False
    t_pros = sum(1 for k in targets if matched(k))

    # ===== 4) Agregados de correo (Supabase; fallback al panel manual) =====
    correo = correo_desde_supabase(supabase)
    if not correo or not correo.get("enviados"):
        correo = dict(CORREO_FALLBACK)
        print("  (aviso) sin metricas Snov frescas en Supabase -> usando CORREO_FALLBACK; "
              "actualizar a mano con el panel si cambio.")

    snap = {
        "periodo": {"inicio": PERIODO_INICIO, "fin": PERIODO_FIN,
                    "nota": "Prospección activa desde el 18 de mayo. El mes previo fue configuración."},
        "universo_unico": len(universo),
        "correo": correo,
        "gestion": {  # llamadas/WhatsApp
            "gestionados": int(len(df)),
            "conversaciones": int((df["resultado"] != "no_contesta").sum() - (df["resultado"] == "numero_malo").sum()),
        },
        "resultados_totales": df["resultado"].value_counts().to_dict(),
        "por_industria": {ind: sub["resultado"].value_counts().to_dict()
                          for ind, sub in df.groupby("industria")},
        "por_area": {ar: sub["resultado"].value_counts().to_dict()
                     for ar, sub in df.groupby("area")},
        "registros": records,  # para filtros cruzados en la página
        "objetivo": {"total": len(targets), "prospectadas": t_pros,
                     "pct": round(t_pros / len(targets) * 100) if targets else 0,
                     "pendientes": len(targets) - t_pros},
        "empresas_positivas": list({
            norm(e["empresa"]): e for e in empresas_pos if norm(e["empresa"])
        }.values())[:30],
    }
    OUT.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
    print("OK ->", OUT)
    print("periodo:", snap["periodo"]["inicio"], "->", snap["periodo"]["fin"])
    print("listas correo leidas:", [Path(a).name for a in archivos])
    print("universo único:", snap["universo_unico"])
    print("gestionados (llam/wpp):", snap["gestion"]["gestionados"],
          "| conversaciones:", snap["gestion"]["conversaciones"])
    print("resultados:", snap["resultados_totales"])
    print("correo:", snap["correo"])
    print("áreas:", {k: sum(v.values()) for k, v in snap["por_area"].items()})
    print("objetivo:", snap["objetivo"])


if __name__ == "__main__":
    main()
