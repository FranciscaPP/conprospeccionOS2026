"""Tests del Intelligence Insight demo (datos ficticios).

Lo critico que se protege aqui:
  1. Ni el modulo de datos ni la pagina pueden tocar Supabase.
  2. La pagina no menciona a ningun cliente real ni al equipo interno.
  3. El snapshot ficticio tiene la forma exacta que consume el render.
  4. Los datos son deterministas (no cambian entre corridas).
"""

import ast
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shared import demo_intelligence as di

PAGINA = ROOT / "demo" / "pages" / "demo_intelligence.py"

MODULOS_PROHIBIDOS = {"requests", "supabase", "shared.config", "master_auth", "meeting_shared"}
NOMBRES_PROHIBIDOS = {"supabase_url", "supabase_key", "require_master_auth"}


def _imports_de(path: Path) -> set[str]:
    arbol = ast.parse(path.read_text(encoding="utf-8"))
    encontrados = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            encontrados.update(a.name for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.module:
                encontrados.add(nodo.module)
            encontrados.update(a.name for a in nodo.names)
    return encontrados


# ── Aislamiento ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "archivo", [ROOT / "shared" / "demo_intelligence.py", PAGINA],
    ids=["demo_intelligence", "pagina"],
)
def test_no_puede_tocar_supabase(archivo):
    importados = _imports_de(archivo)
    assert not (importados & MODULOS_PROHIBIDOS)
    assert not (importados & NOMBRES_PROHIBIDOS)


# ── Anonimato ────────────────────────────────────────────────────────────────
def test_la_pagina_no_menciona_clientes_reales_ni_al_equipo():
    """El original estaba lleno de GBS, logistica y nombres de empresas reales."""
    texto = PAGINA.read_text(encoding="utf-8").lower()
    prohibidos = ("gbs", "bambutech", "clickie", "tiresias", "francisca", "yanina",
                  "carga temperada", "thermoliner", "rubi group", "comex", "aduan")
    for termino in prohibidos:
        assert termino not in texto, termino


def test_los_datos_no_traen_empresas_reales():
    empresas = {r["empresa"] for r in di.snapshot()["registros"]}
    assert all(e.startswith("Empresa Demo ") for e in empresas)
    detalle = di.reuniones_detalle()
    assert detalle["Empresa"].str.startswith("Empresa Demo ").all()


# ── Forma del snapshot ───────────────────────────────────────────────────────
def test_el_snapshot_tiene_las_claves_que_el_render_consume():
    s = di.snapshot()
    requeridas = {"periodo", "universo_unico", "correo", "canal_actividad",
                  "positiva_desglose", "registros", "reuniones_por_segmento", "objetivo"}
    assert requeridas <= set(s)
    assert {"inicio", "fin"} <= set(s["periodo"])


def test_cada_registro_trae_las_columnas_del_render():
    reg = pd.DataFrame(di.snapshot()["registros"])
    assert {"industria", "area", "resultado", "estado_raw", "fecha", "empresa", "tema"} <= set(reg.columns)


def test_los_resultados_usan_el_vocabulario_esperado():
    reg = pd.DataFrame(di.snapshot()["registros"])
    validos = {"no_contesta", "positiva", "no_califica", "negativa", "deriva", "numero_malo"}
    assert set(reg["resultado"]) <= validos


def test_hay_respuestas_positivas_para_que_los_kpis_no_salgan_en_cero():
    reg = pd.DataFrame(di.snapshot()["registros"])
    positivas = reg["resultado"].isin(["positiva", "deriva"]).sum()
    assert positivas >= 10


def test_las_reuniones_por_segmento_calzan_con_las_agendadas():
    s = di.snapshot()
    agendadas = sum(1 for r in s["registros"] if r["estado_raw"] == "Reunión Agendada")
    assert len(s["reuniones_por_segmento"]) == agendadas
    assert agendadas >= 1  # el heatmap necesita al menos un cruce


def test_el_periodo_cae_en_el_mes_en_curso():
    s = di.snapshot()
    hoy = di.hoy_chile()
    from datetime import date
    assert date.fromisoformat(s["periodo"]["inicio"]) == hoy.replace(day=1)


# ── Sustitutos de Supabase ───────────────────────────────────────────────────
def test_reuniones_reales_tiene_la_forma_del_original():
    r = di.reuniones_reales()
    assert set(r) == {"total", "validas", "reagendar", "no_validas"}
    assert r["validas"] <= r["total"]


def test_reuniones_detalle_trae_las_columnas_de_la_tabla():
    d = di.reuniones_detalle()
    assert {"Fecha", "Empresa", "Tipo", "Estado final", "Motivo"} <= set(d.columns)
    assert not d.empty


# ── Determinismo ─────────────────────────────────────────────────────────────
def test_el_snapshot_es_estable_entre_corridas():
    assert di.snapshot()["registros"] == di.snapshot()["registros"]


# ── Ubicacion ────────────────────────────────────────────────────────────────
def test_la_pagina_vive_en_la_app_demo():
    assert PAGINA.exists()
    interno = ROOT / "dashboard" / "pages" / "demo_intelligence.py"
    assert not interno.exists()
