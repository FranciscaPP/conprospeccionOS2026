"""Catálogo único de KPIs del cliente (Reporte Mensual + Intelligence Insight).

15 KPIs en 3 grupos. El cliente elige hasta 5 para su PDF mensual.
`compute_kpis(df, slug, validas_final)` devuelve {id: (valor_str, sub_str)}.
"""
from shared.metas import meta_de

KPI_CATALOGO = [
    {"id": "contactos",      "label": "Contactos trabajados", "grupo": "Volumen"},
    {"id": "empresas",       "label": "Empresas impactadas",  "grupo": "Volumen"},
    {"id": "respuestas",     "label": "Respuestas",           "grupo": "Volumen"},
    {"id": "tasa_respuesta", "label": "Tasa de respuesta",    "grupo": "Volumen"},
    {"id": "cobertura_pais", "label": "Cobertura por país",   "grupo": "Volumen"},
    {"id": "positivas",      "label": "Respuestas positivas", "grupo": "Resultados"},
    {"id": "agendadas",      "label": "Reuniones agendadas",  "grupo": "Resultados"},
    {"id": "validas",        "label": "Reuniones válidas",    "grupo": "Resultados"},
    {"id": "avance_meta",    "label": "% avance de meta",     "grupo": "Resultados"},
    {"id": "conversion",     "label": "Conversión",           "grupo": "Resultados"},
    {"id": "top_industria",  "label": "Top industria",        "grupo": "Estratégico"},
    {"id": "top_cargo",      "label": "Top cargo",            "grupo": "Estratégico"},
    {"id": "top_canal",      "label": "Top canal",            "grupo": "Estratégico"},
    {"id": "motivos",        "label": "Motivos de rechazo",   "grupo": "Estratégico"},
    {"id": "proximos_pasos", "label": "Próximos pasos",       "grupo": "Estratégico"},
]
KPI_LABEL = {k["id"]: k["label"] for k in KPI_CATALOGO}
KPI_IDS   = [k["id"] for k in KPI_CATALOGO]
KPI_GRUPO = {k["id"]: k["grupo"] for k in KPI_CATALOGO}


def _fmt(n):
    return f"{int(n):,}".replace(",", ".")


def _pct(x, dec=1):
    return f"{x:.{dec}f}".replace(".", ",") + "%"


def _top(df, dim):
    pos = df[df.positiva].groupby(dim).size()
    if pos.sum() == 0:
        pos = df.groupby(dim).size()
    return str(pos.idxmax()) if len(pos) else "—"


def compute_kpis(df, cliente_slug, validas_final=0):
    cont = len(df)
    resp = int(df.respondio.sum())
    pos  = int(df.positiva.sum())
    agen = int((df.subestado == "agendada").sum())
    emp  = int(df.empresa_id.nunique())
    meta = (meta_de(cliente_slug) or {}).get("validas", 0)

    out = {}
    out["contactos"]      = (_fmt(cont), "Base activa")
    out["empresas"]       = (_fmt(emp), "Cuentas únicas")
    out["respuestas"]     = (_fmt(resp), (_pct(resp / cont * 100, 1) + " de la base") if cont else "—")
    out["tasa_respuesta"] = (_pct(resp / cont * 100, 1) if cont else "—", "Respuestas / contactos")
    out["cobertura_pais"] = (_fmt(df.pais.nunique()), "Países trabajados")
    out["positivas"]      = (_fmt(pos), "Interés confirmado")
    out["agendadas"]      = (_fmt(agen), "Pendientes de validación")
    out["validas"]        = (_fmt(validas_final), "Validación final")
    out["avance_meta"]    = (_pct(validas_final / meta * 100, 0) if meta else "—", f"Meta {meta} válidas")
    out["conversion"]     = (_pct(agen / cont * 100, 1) if cont else "—", "Reuniones / contactos")
    out["top_industria"]  = (_top(df, "industria"), "Donde traccciona la demanda")
    out["top_cargo"]      = (_top(df, "cargo"), "Mayor enganche")
    out["top_canal"]      = (_top(df, "canal"), "Canal más efectivo")

    mot = df[df.motivo_rechazo.notna()].groupby("motivo_rechazo").size().sort_values(ascending=False)
    out["motivos"]        = ((str(mot.index[0]) if len(mot) else "—"),
                             (f"{int(mot.iloc[0])} casos" if len(mot) else "Sin rechazos"))
    out["proximos_pasos"] = (f"Concentrar en {_top(df, 'cargo')}",
                             f"y en {_top(df, 'industria')}")
    return out
