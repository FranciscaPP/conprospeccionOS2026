"""Tests del motor de reglas de validación (run: python tests/test_validacion.py).

Regla de negocio: **el cliente manda**. Si el cliente marca válida, la final es
válida y cuenta para meta sin importar el estado operativo interno.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.validacion import (
    derivar_final, flag_disputa, flag_meta_countable, gate_valida_permitida, bant_list,
)


def test_cliente_valida_manda_siempre():
    # El cliente manda: válida → válida aunque la reunión figure agendada o sin tocar por CP.
    assert derivar_final("agendada", "espera", "valida", "") == "valida"
    assert derivar_final("realizada", "no_valida", "valida", "") == "valida"
    assert derivar_final("realizada", "valida", "valida", "B,A") == "valida"
    # No exige BANT: válida sin ningún BANT también cuenta.
    assert derivar_final("agendada", "espera", "valida", "") == "valida"


def test_sin_cliente_y_no_realizada_no_cuenta():
    # Si el cliente no validó y la reunión no se realizó, la final es no válida.
    assert derivar_final("no_asistio_lead", "valida", "espera", "B,A,N,T") == "no_valida"
    assert derivar_final("cancelada_cliente", "valida", "espera", "B,A") == "no_valida"


def test_sin_cliente_pendiente():
    # Cliente aún no validó y la reunión no está en estado "no realizada" → pendiente.
    assert derivar_final("reagendada", "espera", "espera", "") == "pendiente"
    assert derivar_final("agendada", "espera", "espera", "") == "pendiente"
    assert derivar_final("realizada", "valida", "espera", "B,A") == "pendiente"


def test_disputa_engano():
    # Cliente la rechaza pero CP la calificaba con ≥2 BANT → en_disputa (revisión de Francisca).
    assert derivar_final("realizada", "valida", "no_valida", "B,A,N") == "en_disputa"
    assert flag_disputa("valida", "no_valida", "B,A,N") is True
    # Sin ≥2 BANT del equipo, no hay disputa: el cliente manda → no válida.
    assert derivar_final("realizada", "valida", "no_valida", "B") == "no_valida"


def test_ambos_no_valida():
    assert derivar_final("realizada", "no_valida", "no_valida", "") == "no_valida"


def test_override_manda():
    assert derivar_final("no_asistio_lead", "no_valida", "no_valida", "", override="valida") == "valida"
    assert derivar_final("agendada", "espera", "valida", "", override="excluida") == "excluida"


def test_meta_countable():
    assert flag_meta_countable("valida") is True
    assert flag_meta_countable("en_disputa") is False
    assert flag_meta_countable("pendiente") is False
    assert flag_meta_countable("no_valida") is False


def test_gate_informativo():
    # gate_valida_permitida sigue disponible como señal informativa para el equipo.
    assert gate_valida_permitida("realizada") is True
    assert gate_valida_permitida("agendada") is False


def test_bant_list():
    assert bant_list("B,A,x,T") == ["B", "A", "T"]
    assert bant_list("") == []
    assert bant_list(["b", "a"]) == ["B", "A"]


if __name__ == "__main__":
    for fn in [test_cliente_valida_manda_siempre, test_sin_cliente_y_no_realizada_no_cuenta,
               test_sin_cliente_pendiente, test_disputa_engano, test_ambos_no_valida,
               test_override_manda, test_meta_countable, test_gate_informativo, test_bant_list]:
        fn()
    print("OK validacion")
