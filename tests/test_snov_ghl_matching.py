"""Tests de sync/scripts/snov_ghl_matching.py (logica pura, sin red)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from snov_ghl_matching import names_match, normalize_name


def test_normalize_name_quita_acentos_y_mayusculas():
    assert normalize_name("José García") == "jose garcia"


def test_normalize_name_none_da_vacio():
    assert normalize_name(None) == ""


def test_names_match_mismo_nombre():
    assert names_match("José García", "Jose", "Garcia") is True


def test_names_match_nombres_distintos():
    assert names_match("José García", "Juan", "Perez") is False


def test_names_match_ghl_sin_nombre_no_hay_choque():
    assert names_match("José García", None, None) is True


def test_names_match_snov_sin_nombre_no_hay_choque():
    assert names_match(None, "Juan", "Perez") is True
