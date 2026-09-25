"""Tests de sync/scripts/telegram_ghl_bot.py (logica pura, sin red)."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from telegram_ghl_bot import (
    BAMBUTECH_CALENDAR_ID,
    PENDING_AGENDAR_SLOTS,
    PENDING_AGENDAR_TITLE,
    handle_agendar_slot_callback,
    handle_message,
    parse_fecha_hora,
)


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


def test_handle_agendar_slot_callback_pide_titulo_en_vez_de_agendar_directo():
    # Cambio de flujo: elegir un horario ya no crea la cita de una — ahora
    # pregunta el titulo primero y guarda el slot elegido pendiente.
    PENDING_AGENDAR_SLOTS.clear()
    PENDING_AGENDAR_TITLE.clear()
    PENDING_AGENDAR_SLOTS[("bambutech", 111)] = {"0": "2026-09-28T10:00:00-06:00"}
    ghl = MagicMock()
    telegram = MagicMock()

    handle_agendar_slot_callback("contact-1", "0", 111, "bambutech", ghl, telegram)

    ghl.create_appointment.assert_not_called()
    telegram.send_message.assert_called_once_with(111, "¿Qué título le ponemos a la reunión?")
    assert ("bambutech", 111) not in PENDING_AGENDAR_SLOTS
    assert PENDING_AGENDAR_TITLE[("bambutech", 111)] == {
        "contact_id": "contact-1", "slot_iso": "2026-09-28T10:00:00-06:00",
    }


def test_handle_agendar_slot_callback_slot_vencido_no_deja_pendiente():
    PENDING_AGENDAR_SLOTS.clear()
    PENDING_AGENDAR_TITLE.clear()
    ghl = MagicMock()
    telegram = MagicMock()

    handle_agendar_slot_callback("contact-1", "0", 111, "bambutech", ghl, telegram)

    ghl.create_appointment.assert_not_called()
    assert ("bambutech", 111) not in PENDING_AGENDAR_TITLE
    telegram.send_message.assert_called_once_with(
        111, "⚠️ Ese horario ya no está disponible, pedí la lista de nuevo.",
    )


def test_handle_message_con_titulo_pendiente_agenda_con_el_titulo(monkeypatch):
    # Segundo paso del flujo: llega el texto con el titulo -> ahi si se crea
    # la cita, con el titulo incluido en la confirmacion.
    PENDING_AGENDAR_SLOTS.clear()
    PENDING_AGENDAR_TITLE.clear()
    PENDING_AGENDAR_TITLE[("bambutech", 111)] = {
        "contact_id": "contact-1", "slot_iso": "2026-09-28T10:00:00-06:00",
    }
    ghl = MagicMock()
    ghl.get_contact.return_value = {
        "contact": {"locationId": "loc1", "firstName": "Caterina", "lastName": "Cronoro"},
    }
    telegram = MagicMock()
    supabase = MagicMock()
    message = {"chat": {"id": 111}, "text": "Demo de producto"}

    handle_message(message, "bambutech", telegram, ghl, supabase, "loc1")

    ghl.create_appointment.assert_called_once_with(
        BAMBUTECH_CALENDAR_ID, "loc1", "contact-1", "2026-09-28T10:00:00-06:00", "Demo de producto",
    )
    assert ("bambutech", 111) not in PENDING_AGENDAR_TITLE
    confirmation = telegram.send_message.call_args[0][1]
    assert "Demo de producto" in confirmation
    assert "Caterina Cronoro" in confirmation
