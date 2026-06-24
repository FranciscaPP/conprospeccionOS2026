"""
Consolida la prospección real de BambuTech en un snapshot (sin PII) que lee
la página Intelligence Insight. Cruza: llamadas/WhatsApp + correo + empresas
objetivo. Se corre 1×/mes con los exports nuevos.

Uso:
    python dashboard/data/build_bambutech_snapshot.py [carpeta_origen]

Salida: dashboard/data/bambutech_intelligence.json  (solo dimensiones/agregados)
NUNCA escribe nombres/emails/teléfonos de contactos en la salida.
"""
import sys, re, json, glob, unicodedata
from pathlib import Path
import pandas as pd

SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Downloads"
OUT = Path(__file__).resolve().parent / "bambutech_intelligence.json"


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


def main():
    # ===== 1) GHL: llamadas + WhatsApp (resultados reales) =====
    g = pd.read_csv(SRC / "GHL.csv", dtype=str, encoding="utf-8", on_bad_lines="skip")
    c_status = find(g, "STATUS", "PROSP")
    c_canal = find(g, "CANAL")
    c_ind = find(g, "MACRO", "INDUS")
    c_ind_raw = next((c for c in g.columns if str(c).strip().lower() == "industria"), None)
    c_cargo_m = find(g, "CARGO", "MACRO")
    c_cargo = find(g, "CARGO") if find(g, "CARGO") != c_cargo_m else None
    c_email = find(g, "EMAIL")
    c_emp = find(g, "BUSINESS")
    c_created = find(g, "CREATED")
    c_activity = find(g, "LAST", "ACTIVITY")
    c_meeting_info = find(g, "INFORMACI", "REUNI")

    # ===== campaña por membresía en listas de correo (Snov) =====
    camp_por_email = {}
    snov_emails = set()
    snov_files = sorted(glob.glob(str(SRC / "bambutech*.xlsx")))
    CAMP_NICE = {
        "logistica": "Logística", "retail": "Retail",
        "op-critica": "Op. Crítica y Continuidad", "tecnologia": "Tecnología",
        "servicios": "Servicios", "final-15-junio": "Campaña 15 Junio",
        "campana_mx_final": "Campaña MX",
    }
    for f in snov_files:
        d = pd.read_excel(f, dtype=str)
        ce = find(d, "EMAIL") or find(d, "CORREO")
        if not ce:
            continue
        name = Path(f).stem.lower()
        camp = next((v for k, v in CAMP_NICE.items() if k in name), "Correo")
        for e in d[ce].dropna().map(lambda x: str(x).lower().strip()):
            if e:
                snov_emails.add(e)
                camp_por_email.setdefault(e, camp)

    records = []  # solo dimensiones (sin PII)
    empresas_pos = []
    for _, r in g.iterrows():
        status_raw = str(r.get(c_status) or "").strip()
        b = bucket(status_raw)
        if not b:
            continue  # solo contactos gestionados con resultado
        email = str(r.get(c_email) or "").lower().strip()
        canal_raw = str(r.get(c_canal) or "").strip().upper()
        canal = {"WHATSAPP": "WhatsApp", "LLAMADA": "Llamadas", "CORREO": "Correo"}.get(
            canal_raw, "Llamadas")
        industria = clean_ind(r.get(c_ind), r.get(c_ind_raw) if c_ind_raw else None)
        area = area_de(r.get(c_cargo_m), r.get(c_cargo))
        campaign = camp_por_email.get(email, "Seguimiento multicanal")
        empresa = company_display(r.get(c_emp))
        fecha = activity_date(r.get(c_activity), r.get(c_created))
        tema = message_theme(campaign, r.get(c_meeting_info))
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
    ghl_emails = set(g[c_email].dropna().map(lambda x: str(x).lower().strip())) - {""}
    universo = ghl_emails | snov_emails

    # ===== 3) Empresas objetivo (One Off) y cruce =====
    one_off = list(SRC.glob("One Off*Pre Sales*.xlsx"))
    targets, prospec = set(), set(g[c_emp].dropna().map(norm)) - {""}
    for f in snov_files:
        d = pd.read_excel(f, dtype=str)
        cc = find(d, "Company name") or find(d, "NOMBRE", "EMPRESA")
        if cc:
            prospec |= set(d[cc].dropna().map(norm)) - {""}
    if one_off:
        xl = pd.ExcelFile(one_off[0])
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

    # ===== 4) Agregados de correo (panel mensual; aperturas desactivadas) =====
    correo = {"enviados": 3374, "contactados": 1940, "entregados": 3289,
              "rebotes": 85, "respuestas": 7, "auto_respuestas": 16, "bajas": 3}

    snap = {
        "periodo": {"inicio": "2026-05-18", "fin": "2026-06-18",
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
    print("universo único:", snap["universo_unico"])
    print("gestionados (llam/wpp):", snap["gestion"]["gestionados"],
          "| conversaciones:", snap["gestion"]["conversaciones"])
    print("resultados:", snap["resultados_totales"])
    print("áreas:", {k: sum(v.values()) for k, v in snap["por_area"].items()})
    print("objetivo:", snap["objetivo"])


if __name__ == "__main__":
    main()
