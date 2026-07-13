"""Datos ficticios del Intelligence Insight demo.

Sustituye las dos fuentes de la pagina real (pages/20_..._Intelligence_Insight):
  * el snapshot JSON del ciclo (dashboard/data/*_intelligence.json)
  * las llamadas en vivo a Supabase (reuniones_reales / reuniones_detalle)

Devuelve exactamente las mismas estructuras que consume el render, con datos
inventados y coherentes entre si. Un unico "Cliente Demo", contactos y empresas
"Empresa Demo N". Ninguna industria o area identifica a un cliente real: son
categorias genericas de mercado.

AISLAMIENTO: no importa requests, supabase ni shared.config. La pagina demo es
incapaz de leer o escribir en produccion. tests/test_demo_intelligence.py lo
verifica.

Todo es determinista (random sembrado) para que el demo y los tests no cambien
entre corridas.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

_CHILE_TZ = ZoneInfo("America/Santiago")

SLUG = "demo"
META_VALIDAS = 12  # espejo de shared/metas.py -> "demo"

# Categorias genericas de mercado. No identifican a ningun cliente.
INDUSTRIAS = [
    "Manufactura", "Retail y Consumo", "Alimentos y Bebidas", "Construcción",
    "Minería y Metales", "Tecnología", "Salud", "Servicios Financieros",
]
AREAS = [
    "Dirección / Gerencia", "Operaciones", "Comercial / Ventas",
    "Abastecimiento / Compras", "Logística / Supply Chain",
    "Finanzas / Administración", "Tecnología / TI",
]
TEMAS = [
    "Eficiencia operativa y reducción de costos",
    "Visibilidad y trazabilidad de procesos",
    "Automatización y digitalización",
    "Escalar la operación sin perder control",
    "Integración de sistemas y datos",
]
RESULTADOS = [
    "no_contesta", "positiva", "no_califica", "negativa", "deriva", "numero_malo",
]
# Pesos: la mayoria en seguimiento sin respuesta, una minoria positiva.
_PESOS = [0.55, 0.11, 0.10, 0.08, 0.06, 0.10]

_ESTADO_POSITIVA = ["Reunión Agendada", "Coordinando reunión", "Información adicional"]


def hoy_chile() -> date:
    return datetime.now(_CHILE_TZ).date()


def _periodo() -> dict:
    """Mes en curso, para que el ciclo se vea siempre reciente."""
    hoy = hoy_chile()
    inicio = hoy.replace(day=1)
    fin = (inicio + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    return {
        "inicio": inicio.isoformat(),
        "fin": fin.isoformat(),
        "nota": "Prospección Cliente Demo, ciclo del mes en curso (datos ficticios).",
    }


def _registros(rng: random.Random, periodo: dict, n: int = 240) -> list[dict]:
    ini = date.fromisoformat(periodo["inicio"])
    fin = date.fromisoformat(periodo["fin"])
    tramo = max((fin - ini).days, 1)
    filas = []
    for i in range(n):
        industria = rng.choices(INDUSTRIAS, weights=[5, 4, 4, 3, 4, 3, 2, 2])[0]
        area = rng.choices(AREAS, weights=[6, 4, 3, 3, 3, 2, 2])[0]
        resultado = rng.choices(RESULTADOS, weights=_PESOS)[0]
        if resultado == "positiva":
            estado_raw = rng.choice(_ESTADO_POSITIVA)
        elif resultado == "negativa":
            estado_raw = rng.choice(["No es prioridad ahora", "Ya tiene proveedor"])
        else:
            estado_raw = ""
        filas.append({
            "industria": industria,
            "area": area,
            "resultado": resultado,
            "estado_raw": estado_raw,
            "fecha": (ini + timedelta(days=rng.randint(0, tramo))).isoformat(),
            "empresa": f"Empresa Demo {i % 90 + 1}",
            "tema": rng.choice(TEMAS),
        })
    return filas


def _reuniones_por_segmento(registros: list[dict]) -> list[dict]:
    """Los cruces industria+area de las reuniones agendadas (alimenta el heatmap)."""
    agendadas = [r for r in registros if r["estado_raw"] == "Reunión Agendada"]
    return [{"industria": r["industria"], "area": r["area"]} for r in agendadas]


def _positiva_desglose(registros: list[dict]) -> dict:
    pos = [r for r in registros if r["resultado"] == "positiva"]
    return {
        "informacion_adicional": sum(1 for r in pos if r["estado_raw"] == "Información adicional"),
        "coordinando_reunion": sum(1 for r in pos if r["estado_raw"] == "Coordinando reunión"),
        "reunion_agendada": sum(1 for r in pos if r["estado_raw"] == "Reunión Agendada"),
    }


def snapshot() -> dict:
    """Consolidado ficticio del ciclo, con la misma forma que el snapshot real."""
    rng = random.Random(2026)  # sembrado -> estable
    periodo = _periodo()
    registros = _registros(rng, periodo)
    gestionados = len(registros)
    contactados = int(gestionados * 1.03)
    return {
        "periodo": periodo,
        "universo_unico": 720,
        "correo": {
            "enviados": 735, "entregados": 731, "contactados": contactados,
            "rebotes": 4, "respuestas": 0, "aperturas": 0,
            "auto_respuestas": 6, "bajas": 1,
        },
        "canal_actividad": [
            {"canal": "WhatsApp", "gestiones": 291},
            {"canal": "Correo", "gestiones": 731},
            {"canal": "Llamada", "gestiones": 88},
        ],
        "gestion": {"gestionados": gestionados, "conversaciones":
                    sum(1 for r in registros
                        if r["resultado"] not in {"no_contesta", "numero_malo", "no_califica"})},
        "positiva_desglose": _positiva_desglose(registros),
        "registros": registros,
        "reuniones_por_segmento": _reuniones_por_segmento(registros),
        "objetivo": {"total": 92},
    }


# ── Sustitutos de las llamadas a Supabase ────────────────────────────────────
def reuniones_reales() -> dict:
    """Espejo de la funcion homonima de la pagina real, sin red."""
    return {"total": 14, "validas": 3, "reagendar": 1, "no_validas": 1}


_DETALLE = [
    ("Empresa Demo 12", "Reunión", "Válida", ""),
    ("Empresa Demo 27", "Cotización", "Válida", ""),
    ("Empresa Demo 41", "Reunión", "Válida", ""),
    ("Empresa Demo 9", "Reunión", "Pendiente", ""),
    ("Empresa Demo 55", "Reunión", "Pendiente", ""),
    ("Empresa Demo 63", "Reunión", "Reagendar", "El prospecto pidió nueva fecha"),
    ("Empresa Demo 18", "Reunión", "No válida", "ICP incorrecto (fuera de perfil)"),
    ("Empresa Demo 33", "Reunión", "Válida", ""),
    ("Empresa Demo 47", "Cotización", "Válida", ""),
    ("Empresa Demo 71", "Reunión", "Pendiente", ""),
]


def reuniones_detalle() -> pd.DataFrame:
    """Detalle ficticio de reuniones/cotizaciones del ciclo."""
    hoy = hoy_chile()
    filas = []
    for i, (empresa, tipo, estado, motivo) in enumerate(_DETALLE):
        filas.append({
            "Fecha": (hoy - timedelta(days=3 + i * 2)).strftime("%d/%m/%Y"),
            "Empresa": empresa,
            "Tipo": tipo,
            "Estado final": estado,
            "Motivo": motivo,
        })
    return pd.DataFrame(filas)
