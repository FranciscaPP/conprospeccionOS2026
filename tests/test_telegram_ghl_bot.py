"""Tests de sync/scripts/telegram_ghl_bot.py (logica pura, sin red)."""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from telegram_ghl_bot import parse_fecha_hora


def test_parse_fecha_hora_manana_11am():
    result = parse_fecha_hora("mañana 11am")
    assert result is not None
    due = datetime.fromisoformat(result)
    now = datetime.now(timezone.utc)
    assert due.hour == 11
    assert due.minute == 0
    # Es un dia despues de hoy (no dos, no el mismo).
    assert (due.date() - now.date()).days == 1


def test_parse_fecha_hora_pasado_manana_10am():
    result = parse_fecha_hora("pasado mañana 10am")
    assert result is not None
    due = datetime.fromisoformat(result)
    now = datetime.now(timezone.utc)
    assert due.hour == 10
    # "pasado mañana" es dos dias despues de hoy, no confundir con "mañana" (un dia).
    assert (due.date() - now.date()).days == 2


def test_parse_fecha_hora_viernes_3pm():
    result = parse_fecha_hora("viernes 3pm")
    assert result is not None
    due = datetime.fromisoformat(result)
    assert due.hour == 15
    assert due.weekday() == 4  # viernes


def test_parse_fecha_hora_dos_dias_de_semana_elige_uno_deterministico():
    # Menciona lunes y viernes — el resultado debe ser consistente con
    # "quedarse con el que aparece mas a la derecha en el texto" (viernes),
    # no con el primero que matchee por orden de iteracion (lunes).
    result = parse_fecha_hora("no puedo el lunes, mejor el viernes 3pm")
    assert result is not None
    due = datetime.fromisoformat(result)
    assert due.weekday() == 4  # viernes, no lunes (weekday 0)
    assert due.hour == 15


def test_parse_fecha_hora_numero_suelto_no_se_confunde_con_hora():
    # "20" (del "20 de noviembre") no debe interpretarse como hora=20 --
    # el numero de hora real es "3pm".
    result = parse_fecha_hora("viernes 20 de noviembre 3pm")
    assert result is not None
    due = datetime.fromisoformat(result)
    assert due.hour == 15
    assert due.hour != 20


def test_parse_fecha_hora_texto_basura_da_none():
    assert parse_fecha_hora("asdf qwerty sin sentido") is None
    assert parse_fecha_hora("") is None
