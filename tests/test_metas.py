"""Tests de la regla de meta acumulada (fuente unica en shared/metas.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.metas import avance_meta, avance_acumulado_por_mes, meta_de


def test_contrato_acumula_todos_los_meses():
    # GBS meta 45 (contrato): las validas de junio siguen contando en julio.
    validas = {"2026-06": 9, "2026-07": 3}
    r = avance_meta("gbs", validas, mes_actual="2026-07")
    assert r["avance"] == 12  # 9 + 3
    assert r["meta"] == 45
    assert r["tipo"] == "contrato"
    assert r["cumplida"] is False


def test_contrato_serie_acumulada_por_mes():
    validas = {"2026-06": 9, "2026-07": 3}
    assert avance_acumulado_por_mes("gbs", validas) == {"2026-06": 9, "2026-07": 12}


def test_mensual_reinicia_cada_mes():
    # Clickie meta 6 (mensual): solo cuenta el mes en curso.
    validas = {"2026-05": 5, "2026-06": 9, "2026-07": 0}
    assert avance_meta("clickie", validas, mes_actual="2026-07")["avance"] == 0
    r_jun = avance_meta("clickie", validas, mes_actual="2026-06")
    assert r_jun["avance"] == 9 and r_jun["cumplida"] is True
    # No acumula entre meses.
    assert avance_acumulado_por_mes("clickie", validas) == validas


def test_bambutech_contrato_cien():
    assert meta_de("bambutech") == {"validas": 100, "tipo": "contrato"}
    r = avance_meta("bambutech", {"2026-05": 1, "2026-06": 3, "2026-07": 2})
    assert r["avance"] == 6 and r["meta"] == 100


def test_cliente_sin_meta_devuelve_none():
    assert avance_meta("desconocido", {"2026-07": 5}) is None
