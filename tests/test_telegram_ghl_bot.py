"""Tests de sync/scripts/telegram_ghl_bot.py (logica pura, sin red)."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from telegram_ghl_bot import (
    CLIENT_CALENDAR_CONFIG,
    PENDING_AGENDAR_SLOTS,
    PENDING_AGENDAR_TITLE,
    PENDING_EMAIL_REPLY,
    PENDING_MANUAL_TASK,
    handle_agendar_callback,
    handle_agendar_slot_callback,
    handle_email_callback,
    handle_message,
    handle_tarea_callback,
    parse_fecha_hora,
)


def _clear_all_pending():
    PENDING_AGENDAR_SLOTS.clear()
    PENDING_AGENDAR_TITLE.clear()
    PENDING_EMAIL_REPLY.clear()
    PENDING_MANUAL_TASK.clear()


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
    _clear_all_pending()
    PENDING_AGENDAR_SLOTS[("bambutech", 111)] = {"0": "2026-09-28T10:00:00-06:00"}
    ghl = MagicMock()
    telegram = MagicMock()

    handle_agendar_slot_callback("contact-1", "0", 111, "bambutech", ghl, telegram)

    ghl.create_appointment.assert_not_called()
    telegram.send_message.assert_called_once_with(111, "¿Qué título le ponemos a la reunión?")
    assert ("bambutech", 111) not in PENDING_AGENDAR_SLOTS
    assert PENDING_AGENDAR_TITLE[("bambutech", 111)] == {
        "contact_id": "contact-1", "slot_iso": "2026-09-28T10:00:00-06:00", "stage": "title",
    }


def test_handle_agendar_slot_callback_slot_vencido_no_deja_pendiente():
    _clear_all_pending()
    ghl = MagicMock()
    telegram = MagicMock()

    handle_agendar_slot_callback("contact-1", "0", 111, "bambutech", ghl, telegram)

    ghl.create_appointment.assert_not_called()
    assert ("bambutech", 111) not in PENDING_AGENDAR_TITLE
    telegram.send_message.assert_called_once_with(
        111, "⚠️ Ese horario ya no está disponible, pedí la lista de nuevo.",
    )


def _mock_ghl_con_contacto():
    ghl = MagicMock()
    ghl.get_contact.return_value = {
        "contact": {"locationId": "loc1", "firstName": "Caterina", "lastName": "Cronoro"},
    }
    return ghl


def test_handle_message_con_titulo_pendiente_pide_confirmacion_sin_agendar():
    # Primer paso: llega el texto con el titulo -> todavia NO se crea la
    # cita, se pide confirmacion explicita primero (capa de seguridad).
    _clear_all_pending()
    PENDING_AGENDAR_TITLE[("bambutech", 111)] = {
        "contact_id": "contact-1", "slot_iso": "2026-09-28T10:00:00-06:00", "stage": "title",
    }
    ghl = _mock_ghl_con_contacto()
    telegram = MagicMock()
    supabase = MagicMock()
    message = {"chat": {"id": 111}, "text": "Demo de producto"}

    handle_message(message, "bambutech", telegram, ghl, supabase, "loc1")

    ghl.create_appointment.assert_not_called()
    pending = PENDING_AGENDAR_TITLE[("bambutech", 111)]
    assert pending["stage"] == "confirm"
    assert pending["titulo"] == "Demo de producto"
    prompt = telegram.send_message.call_args[0][1]
    assert "Demo de producto" in prompt
    assert "Caterina Cronoro" in prompt
    assert "confirm" in prompt.lower() or "'si'" in prompt.lower()


def test_handle_message_falla_get_contact_al_confirmar_no_deja_armado_para_si_suelto():
    # Hallazgo del revisor: si _build_agendar_confirmation_text explota (ej.
    # GHL 5xx/timeout en get_contact) DESPUES de que el titulo llega, el SDR
    # nunca ve el prompt de confirmacion. Si el codigo igual dejara
    # stage="confirm" armado, un "si" suelto y sin relacion mandado despues
    # agendaria una cita real sin confirmacion genuina. Verificamos que el
    # pending no quede armado en "confirm" y que ese "si" posterior no
    # agende nada.
    _clear_all_pending()
    PENDING_AGENDAR_TITLE[("bambutech", 111)] = {
        "contact_id": "contact-1", "slot_iso": "2026-09-28T10:00:00-06:00", "stage": "title",
    }
    ghl = MagicMock()
    ghl.get_contact.side_effect = RuntimeError("GHL 503")
    telegram = MagicMock()
    supabase = MagicMock()
    message = {"chat": {"id": 111}, "text": "Demo de producto"}

    handle_message(message, "bambutech", telegram, ghl, supabase, "loc1")

    ghl.create_appointment.assert_not_called()
    pending = PENDING_AGENDAR_TITLE.get(("bambutech", 111))
    assert pending is None or pending.get("stage") != "confirm"
    # Se aviso el fallo por Telegram en vez de quedar en silencio.
    aviso = telegram.send_message.call_args[0][1]
    assert "no pude" in aviso.lower() or "⚠️" in aviso

    # Un "si" suelto y sin relacion, mandado despues del fallo, NO debe
    # agendar de verdad -- es exactamente el escenario que el revisor
    # reprodujo.
    telegram.reset_mock()
    ghl.create_appointment.reset_mock()
    message_si = {"chat": {"id": 111}, "text": "si"}
    handle_message(message_si, "bambutech", telegram, ghl, supabase, "loc1")

    ghl.create_appointment.assert_not_called()


def test_handle_message_confirmacion_afirmativa_agenda_de_verdad():
    # Segundo paso: con el titulo ya guardado y stage "confirm", una
    # respuesta afirmativa ("si") es lo unico que dispara create_appointment.
    _clear_all_pending()
    PENDING_AGENDAR_TITLE[("bambutech", 111)] = {
        "contact_id": "contact-1", "slot_iso": "2026-09-28T10:00:00-06:00",
        "stage": "confirm", "titulo": "Demo de producto",
    }
    ghl = _mock_ghl_con_contacto()
    telegram = MagicMock()
    supabase = MagicMock()
    message = {"chat": {"id": 111}, "text": "Sí"}

    handle_message(message, "bambutech", telegram, ghl, supabase, "loc1")

    ghl.create_appointment.assert_called_once_with(
        CLIENT_CALENDAR_CONFIG["bambutech"]["calendar_id"], "loc1", "contact-1", "2026-09-28T10:00:00-06:00", "Demo de producto",
    )
    assert ("bambutech", 111) not in PENDING_AGENDAR_TITLE
    confirmation = telegram.send_message.call_args[0][1]
    assert "Demo de producto" in confirmation
    assert "Caterina Cronoro" in confirmation


def test_handle_message_confirmacion_negativa_no_agenda_y_limpia_pendiente():
    # Cualquier respuesta que no sea un "si"/"yes"/"confirmar" claro cancela
    # el flujo en vez de agendar o quedar colgado esperando para siempre.
    _clear_all_pending()
    PENDING_AGENDAR_TITLE[("bambutech", 111)] = {
        "contact_id": "contact-1", "slot_iso": "2026-09-28T10:00:00-06:00",
        "stage": "confirm", "titulo": "Demo de producto",
    }
    ghl = _mock_ghl_con_contacto()
    telegram = MagicMock()
    supabase = MagicMock()
    message = {"chat": {"id": 111}, "text": "mejor no"}

    handle_message(message, "bambutech", telegram, ghl, supabase, "loc1")

    ghl.create_appointment.assert_not_called()
    assert ("bambutech", 111) not in PENDING_AGENDAR_TITLE
    telegram.send_message.assert_called_once_with(111, "❌ No se agendó nada. Si querés, elegí el horario de nuevo.")


def test_handle_agendar_slot_callback_cancela_tarea_manual_pendiente():
    # Falla #2 del bug original: la SDR arranca una tarea manual y, antes de
    # terminarla, elige un horario para agendar -- eso debe cancelar la
    # tarea a medias, no dejarla viva para que su proxima respuesta (pensada
    # para la tarea) se cuele como titulo de la reunion.
    _clear_all_pending()
    PENDING_MANUAL_TASK[("bambutech", 111)] = {"contact_id": "contact-1", "step": "descripcion", "titulo": "Llamar de nuevo"}
    PENDING_AGENDAR_SLOTS[("bambutech", 111)] = {"0": "2026-09-28T10:00:00-06:00"}
    ghl = MagicMock()
    telegram = MagicMock()

    handle_agendar_slot_callback("contact-1", "0", 111, "bambutech", ghl, telegram)

    assert ("bambutech", 111) not in PENDING_MANUAL_TASK
    assert PENDING_AGENDAR_TITLE[("bambutech", 111)]["stage"] == "title"


def test_handle_agendar_slot_callback_cancela_email_pendiente():
    _clear_all_pending()
    PENDING_EMAIL_REPLY[("bambutech", 111)] = {
        "contact_id": "contact-1", "account_email": "a@b.com", "to": "c@d.com",
        "subject": "asunto", "references": "",
    }
    PENDING_AGENDAR_SLOTS[("bambutech", 111)] = {"0": "2026-09-28T10:00:00-06:00"}
    ghl = MagicMock()
    telegram = MagicMock()

    handle_agendar_slot_callback("contact-1", "0", 111, "bambutech", ghl, telegram)

    assert ("bambutech", 111) not in PENDING_EMAIL_REPLY
    assert ("bambutech", 111) in PENDING_AGENDAR_TITLE


def test_handle_tarea_callback_cancela_agendar_pendiente():
    # Falla #1 del bug original: la SDR elige un horario para agendar y,
    # antes de contestar el titulo, arranca (o el equipo dispara) una tarea
    # manual -- eso debe cancelar el agendar a medias en vez de dejar un
    # texto libre cualquiera colarse como titulo de una cita real.
    _clear_all_pending()
    PENDING_AGENDAR_TITLE[("bambutech", 111)] = {
        "contact_id": "contact-1", "slot_iso": "2026-09-28T10:00:00-06:00", "stage": "title",
    }
    telegram = MagicMock()

    handle_tarea_callback(["tarea", "contact-1", "manual"], 111, "bambutech", telegram)

    assert ("bambutech", 111) not in PENDING_AGENDAR_TITLE
    assert PENDING_MANUAL_TASK[("bambutech", 111)] == {"contact_id": "contact-1", "step": "titulo"}


def test_handle_email_callback_cancela_agendar_pendiente(monkeypatch):
    _clear_all_pending()
    PENDING_AGENDAR_TITLE[("bambutech", 111)] = {
        "contact_id": "contact-1", "slot_iso": "2026-09-28T10:00:00-06:00", "stage": "title",
    }
    ghl = MagicMock()
    ghl.get_contact.return_value = {"contact": {"email": "prospecto@ejemplo.com"}}
    telegram = MagicMock()

    fake_module = MagicMock()
    fake_module.find_reply_thread.return_value = {
        "account_email": "bambutech@buzon.com", "subject": "Consulta",
        "references": "", "body": "hola",
    }
    monkeypatch.setitem(sys.modules, "client_mailboxes", fake_module)

    handle_email_callback("contact-1", 111, "bambutech", ghl, telegram)

    assert ("bambutech", 111) not in PENDING_AGENDAR_TITLE
    assert ("bambutech", 111) in PENDING_EMAIL_REPLY


def test_handle_message_texto_suelto_con_agendar_pendiente_no_consume_tarea_vieja():
    # Reproduce el modo de falla #1 completo end-to-end: se elige un slot
    # (arranca PENDING_AGENDAR_TITLE) y, gracias a _clear_pending, una tarea
    # manual vieja para el mismo chat ya no puede seguir viva ni consumir
    # el texto del titulo.
    _clear_all_pending()
    PENDING_MANUAL_TASK[("bambutech", 111)] = {"contact_id": "contact-1", "step": "titulo"}
    PENDING_AGENDAR_SLOTS[("bambutech", 111)] = {"0": "2026-09-28T10:00:00-06:00"}
    ghl = _mock_ghl_con_contacto()
    telegram = MagicMock()

    handle_agendar_slot_callback("contact-1", "0", 111, "bambutech", ghl, telegram)
    assert ("bambutech", 111) not in PENDING_MANUAL_TASK

    telegram.reset_mock()
    supabase = MagicMock()
    message = {"chat": {"id": 111}, "text": "cualquier texto sin relacion"}
    handle_message(message, "bambutech", telegram, ghl, supabase, "loc1")

    # El texto se consumio como titulo de la reunion (unico flujo activo),
    # no como tarea, y todavia no se agendo nada de verdad.
    ghl.create_appointment.assert_not_called()
    ghl.create_task.assert_not_called()
    assert PENDING_AGENDAR_TITLE[("bambutech", 111)]["stage"] == "confirm"


def test_client_calendar_config_tiene_bambutech_gbs_y_balia():
    # bambutech, gbs y balia (calendario "BALIA B") tienen calendario cableado.
    assert "bambutech" in CLIENT_CALENDAR_CONFIG
    assert "gbs" in CLIENT_CALENDAR_CONFIG
    assert CLIENT_CALENDAR_CONFIG["balia"]["calendar_id"] == "2chaXy63L9xltYeM71xP"


def test_handle_agendar_callback_gbs_ahora_funciona():
    # Antes del cambio, gbs caia en el gate de "no configurado" igual que
    # balia -- ahora debe consultar el calendario de GBS como bambutech.
    _clear_all_pending()
    ghl = MagicMock()
    ghl.free_slots.return_value = {"2026-09-28": {"slots": ["2026-09-28T10:00:00-03:00"]}}
    telegram = MagicMock()

    handle_agendar_callback("contact-1", 111, "gbs", ghl, telegram)

    ghl.free_slots.assert_called_once()
    called_calendar_id = ghl.free_slots.call_args[0][0]
    called_timezone = ghl.free_slots.call_args[0][3]
    assert called_calendar_id == CLIENT_CALENDAR_CONFIG["gbs"]["calendar_id"]
    assert called_timezone == "America/Santiago"
    telegram.send_message.assert_called_once()
    assert "no está configurado" not in telegram.send_message.call_args[0][1]


def test_handle_agendar_callback_cliente_sin_calendario_no_configurado():
    _clear_all_pending()
    ghl = MagicMock()
    telegram = MagicMock()

    handle_agendar_callback("contact-1", 111, "cliente_sin_calendario", ghl, telegram)

    ghl.free_slots.assert_not_called()
    telegram.send_message.assert_called_once_with(111, "⚠️ Todavía no está configurado el calendario de este cliente")


def test_handle_email_callback_busca_en_casillas_del_cliente(monkeypatch):
    # find_reply_thread ahora recibe el slug -- el mock debe verificar que se
    # le pasa "gbs" y no queda hardcodeado a bambutech.
    _clear_all_pending()
    ghl = MagicMock()
    ghl.get_contact.return_value = {"contact": {"email": "prospecto@ejemplo.com"}}
    telegram = MagicMock()

    fake_module = MagicMock()
    fake_module.find_reply_thread.return_value = {
        "account_email": "sammiller@gbs-logistics.cl", "subject": "Consulta",
        "references": "", "body": "hola",
    }
    monkeypatch.setitem(sys.modules, "client_mailboxes", fake_module)

    handle_email_callback("contact-1", 111, "gbs", ghl, telegram)

    fake_module.find_reply_thread.assert_called_once_with("gbs", "prospecto@ejemplo.com")
    assert ("gbs", 111) in PENDING_EMAIL_REPLY
