"""Tests de la lógica del pool maestro (shared/bbdd_maestra.py)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.bbdd_maestra import (
    ICP,
    candidatos,
    consolidar,
    normalizar_industria,
    normalizar_pais,
    resumen_pool,
    ruta_destino,
    score_icp,
)


def test_normaliza_industria_typos():
    # "mini" y variantes de escritura caen en Minería (limpieza uniforme).
    assert normalizar_industria("mini") == "Minería"
    assert normalizar_industria("MINERIA") == "Minería"
    assert normalizar_industria("Mining company") == "Minería"
    assert normalizar_industria("logistica y transporte") == "Logística y transporte"
    # Desconocida: se conserva capitalizada, no se pierde.
    assert normalizar_industria("turismo receptivo") == "Turismo receptivo"


def test_normaliza_pais():
    assert normalizar_pais("cl") == "Chile"
    assert normalizar_pais("PERU") == "Perú"
    assert normalizar_pais("United States") == "Estados Unidos"


def test_dedup_alerta_no_borra():
    rows = [
        {"fuente": "snov", "email": "a@x.com", "nombre": "Ana", "empresa": "X", "email_status": "current"},
        {"fuente": "ghl", "email": "A@X.com", "nombre": "Ana P", "empresa": "X SpA", "cargo": "CEO", "telefono": "+569"},
        {"fuente": "snov", "email": "b@y.com", "nombre": "Beto", "empresa": "Y"},
    ]
    filas = consolidar(rows)
    # No se borra ninguna fila.
    assert len(filas) == 3
    # a@x.com está duplicado y marcado como tal en ambas filas.
    dup = [f for f in filas if f["email_norm"] == "a@x.com"]
    assert len(dup) == 2
    assert all(f["es_duplicado"] and f["veces"] == 2 for f in dup)
    assert set(dup[0]["fuentes"]) == {"snov", "ghl"}
    # El canónico es el registro más completo (el de GHL con cargo+teléfono).
    canonico = next(f for f in dup if f["es_canonico"])
    assert canonico["fuente"] == "ghl"
    # b@y.com no es duplicado.
    assert next(f for f in filas if f["email_norm"] == "b@y.com")["es_duplicado"] is False


def test_ruta_destino():
    assert ruta_destino({"correo_verificado": True, "tiene_telefono": False}) == ["snov"]
    assert ruta_destino({"correo_verificado": False, "tiene_telefono": True}) == ["ghl"]
    assert ruta_destino({"correo_verificado": True, "tiene_telefono": True}) == ["snov", "ghl"]
    assert ruta_destino({}) == []


def test_score_icp_y_exclusiones():
    icp = ICP(paises=["Chile"], industrias=["Minería"], cargos=["gerente"], keywords=["cobre"], exclusiones=["consultora"])
    p_fit = {"pais_norm": "Chile", "industria_norm": "Minería", "cargo": "Gerente de operaciones", "empresa": "Cobre SA"}
    score, detalle = score_icp(p_fit, icp)
    assert score == 4 and all(detalle.values())
    # Exclusión descalifica aunque calce el resto.
    p_excl = {"pais_norm": "Chile", "industria_norm": "Minería", "empresa": "Consultora ABC"}
    score_e, det_e = score_icp(p_excl, icp)
    assert score_e == -1 and det_e.get("excluido")


def test_candidatos_filtra_por_umbral_y_asignados():
    filas = consolidar([
        {"fuente": "snov", "email": "fit@mina.cl", "empresa": "Mina", "cargo": "Gerente",
         "industria": "mineria", "pais": "chile", "email_status": "current"},
        {"fuente": "snov", "email": "nofit@banco.cl", "empresa": "Banco", "cargo": "Cajero",
         "industria": "banca", "pais": "chile", "email_status": "current"},
    ])
    icp = ICP(paises=["Chile"], industrias=["Minería"], cargos=["gerente"], umbral_score=2)
    cands = candidatos(filas, icp)
    emails = [c["email_norm"] for c in cands]
    assert "fit@mina.cl" in emails
    assert "nofit@banco.cl" not in emails
    # Si ya está asignado a ese cliente, se excluye.
    cands2 = candidatos(filas, icp, ya_asignados={"fit@mina.cl"})
    assert "fit@mina.cl" not in [c["email_norm"] for c in cands2]


def test_resumen_pool():
    filas = consolidar([
        {"fuente": "snov", "email": "a@x.com", "industria": "mineria", "pais": "chile", "email_status": "current"},
        {"fuente": "ghl", "email": "a@x.com", "industria": "mineria", "pais": "chile", "telefono": "+569"},
        {"fuente": "snov", "email": "b@y.com", "industria": "banca", "pais": "peru"},
    ])
    r = resumen_pool(filas)
    assert r["prospectos_unicos"] == 2
    assert r["duplicados"] == 1
    assert r["correos_verificados"] == 1
    assert r["con_telefono"] == 1
