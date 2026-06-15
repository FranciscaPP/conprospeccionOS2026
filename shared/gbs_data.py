"""Dataset demo compartido de la campaña GBS (Intelligence Insight + Reporte PDF).

Mismo escenario fijo (seed 42) que el dashboard: 784 contactos · 148 empresas ·
21 respuestas · 8 positivas (6 info + 2 agendadas). Fuente única para que el
reporte y el dashboard muestren exactamente los mismos números.
"""
import random
import pandas as pd

from shared.gbs_brand import W_CARGO as BRAND_W_CARGO, W_IND as BRAND_W_IND

MOTIVO_OPTS = ["Ya tienen proveedor", "Sin respuesta", "No interesado"]


def _pick(rng, weighted):
    r = rng.random()
    acc = 0.0
    for val, w in weighted:
        acc += w
        if r <= acc:
            return val
    return weighted[-1][0]


def cargar_dataset(base_n=776):
    rng = random.Random(42)
    W_PAIS  = [("Chile", .68), ("Perú", .20), ("Colombia", .12)]
    W_IND   = BRAND_W_IND
    W_CARGO = BRAND_W_CARGO
    W_CANAL = [("Llamadas", .45), ("Correo electrónico", .30), ("WhatsApp", .25)]
    W_TAM   = [("10–50 empleados", .45), ("50–200 empleados", .40), ("200+ empleados", .15)]
    W_PER   = [("Mayo 2026", .58), ("Junio 2026", .42)]

    filas = []
    n_resp_neg = 13
    for i in range(base_n):
        respondio = i < n_resp_neg
        motivo = MOTIVO_OPTS[i % len(MOTIVO_OPTS)] if respondio else None
        filas.append({
            "periodo": _pick(rng, W_PER), "canal": _pick(rng, W_CANAL),
            "pais": _pick(rng, W_PAIS), "industria": _pick(rng, W_IND),
            "cargo": _pick(rng, W_CARGO), "tamano": _pick(rng, W_TAM),
            "empresa_id": (i % 148) + 1,
            "respondio": respondio, "positiva": False, "reunion": False,
            "subestado": None,
            "tipo_respuesta": ("Reunión no válida" if respondio and i % 4 == 0 else None),
            "etapa": None, "bant": [],
            "interes_lead": None, "motivo_rechazo": motivo,
        })
    rng.shuffle(filas)

    POS = [
        ("Chile",    "Minería y Metales",   "Encargado de Importaciones", "Llamadas",           "50–200 empleados", "Junio 2026", "info_adicional", ["B", "N"],           "Cotización"),
        ("Chile",    "Minería y Metales",   "Encargado de Importaciones", "Llamadas",           "200+ empleados",   "Junio 2026", "info_adicional", ["B", "A", "N", "T"], "Reunión + Cotización"),
        ("Perú",     "Minería y Metales",   "Gerente de Operaciones",     "Llamadas",           "50–200 empleados", "Junio 2026", "info_adicional", ["B", "A", "N"],      "Cotización"),
        ("Chile",    "Retail",              "Jefe COMEX",                 "Correo electrónico", "200+ empleados",   "Mayo 2026",  "info_adicional", ["A", "N"],           "Reunión"),
        ("Chile",    "Automotriz",          "Encargado de Importaciones", "WhatsApp",           "10–50 empleados",  "Mayo 2026",  "info_adicional", ["N", "T"],           "Cotización"),
        ("Colombia", "Alimentos y Bebidas", "Supply Chain Manager",       "Correo electrónico", "50–200 empleados", "Junio 2026", "info_adicional", ["B", "N"],           "Reunión"),
        ("Chile",    "Minería y Metales",   "Encargado de Importaciones", "Llamadas",           "50–200 empleados", "Junio 2026", "agendada",       ["B", "N", "T"],      "Reunión + Cotización"),
        ("Chile",    "Retail",              "Gerente de Operaciones",     "Llamadas",           "50–200 empleados", "Mayo 2026",  "agendada",       ["B", "A", "N", "T"], "Reunión"),
    ]
    for j, (pais, ind, cargo, canal, tam, per, sub, bant, interes) in enumerate(POS):
        filas.append({
            "periodo": per, "canal": canal, "pais": pais, "industria": ind,
            "cargo": cargo, "tamano": tam, "empresa_id": j + 1,
            "respondio": True, "positiva": True, "reunion": False,
            "subestado": sub, "tipo_respuesta": "Espera validación",
            "etapa": None, "bant": bant,
            "interes_lead": interes, "motivo_rechazo": None,
        })
    return pd.DataFrame(filas)
