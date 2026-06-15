"""Tests de los helpers puros de shared/seguimiento.py (run: python tests/test_seguimiento_helpers.py)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.seguimiento import (
    TIPO_RESPUESTA_OPTS, bant_to_list, bant_to_str, tipo_valido, payload_nivel,
)


def test_bant_roundtrip():
    assert bant_to_list("B,A,N") == ["B", "A", "N"]
    assert bant_to_list(["b", "x", "T"]) == ["B", "T"]
    assert bant_to_str(["B", "A", "Z"]) == "B,A"


def test_tipo_valido():
    assert tipo_valido("Solicita reunión")
    assert tipo_valido("No es la persona")
    assert not tipo_valido("cualquier cosa")
    assert not tipo_valido(None)


def test_opts_tienen_8():
    assert len(TIPO_RESPUESTA_OPTS) == 8
    assert "Solicita más información" in TIPO_RESPUESTA_OPTS
    assert "Sin respuesta" in TIPO_RESPUESTA_OPTS


def test_payload_nivel_cli():
    p = payload_nivel(
        reunion_id=7, cliente_slug="gbs", nivel="cli",
        val_estado="valida", etapa="envio_propuesta",
        bant=["B", "A"], tipo_respuesta="Solicita reunión", status="ok")
    assert p["reunion_id"] == 7
    assert p["cliente_slug"] == "gbs"
    assert p["val_estado_cli"] == "valida"
    assert p["etapa_cli"] == "envio_propuesta"
    assert p["bant_cli"] == "B,A"
    assert p["tipo_respuesta_cli"] == "Solicita reunión"
    assert p["status_cli"] == "ok"
    assert "updated_at" in p and "updated_by_cli" in p


if __name__ == "__main__":
    test_bant_roundtrip(); test_tipo_valido(); test_opts_tienen_8(); test_payload_nivel_cli()
    print("OK seguimiento helpers")
