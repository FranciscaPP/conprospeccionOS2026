"""Tests de notify()/send_followup_buttons en sync_snov_replies_to_ghl.py —
verifican el gating de "mandar los 4 bloques de botones juntos al crear el
contacto" sin tocar Telegram/GHL reales (todo mockeado)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from sync_snov_replies_to_ghl import notify


def _make_telegram():
    client_bot = MagicMock()
    client_bot.send_message.return_value = {"message_id": 123}
    return client_bot, ["111"]


def _make_ghl():
    ghl = MagicMock()
    ghl.custom_field_id_map.return_value = {"status_prospecto": "field-1"}
    ghl.custom_field_options.return_value = ["No Contesta", "No Interesado"]
    return ghl


def test_notify_bambutech_con_contact_id_manda_los_4_bloques():
    # Tarjeta + status + agendar + tarea = 4 mensajes en total.
    client_bot, chat_ids = _make_telegram()
    ghl = _make_ghl()
    supabase = MagicMock()

    notify(
        (client_bot, chat_ids), supabase, "🟢 *Nuevo contacto en el CRM*",
        cliente_slug="bambutech", ghl_contact_id="contact-1", ghl_location_id="loc1",
        prospect_name="Caterina", prospect_email="cate@transapp.cl", dry_run=False, ghl=ghl,
    )

    assert client_bot.send_message.call_count == 4
    texts = [call.args[1] for call in client_bot.send_message.call_args_list]
    assert texts[0] == "🟢 *Nuevo contacto en el CRM*"
    assert "¿A qué estatus" in texts[1]
    assert "Agendar con" in texts[2]
    assert "Generar tarea" in texts[3]


def test_notify_gbs_con_contact_id_manda_los_4_bloques():
    # gbs ahora tiene las mismas casillas/bot interactivo que bambutech --
    # debe mandar tarjeta + status + agendar + tarea igual que bambutech.
    client_bot, chat_ids = _make_telegram()
    ghl = _make_ghl()
    supabase = MagicMock()

    notify(
        (client_bot, chat_ids), supabase, "🔵 *Nuevo contacto en el CRM*",
        cliente_slug="gbs", ghl_contact_id="contact-2", ghl_location_id="loc2",
        prospect_name="Juan", prospect_email="juan@gbs.cl", dry_run=False, ghl=ghl,
    )

    assert client_bot.send_message.call_count == 4
    ghl.custom_field_id_map.assert_called_once()


def test_notify_balia_con_contact_id_no_manda_botones_extra_ni_rompe():
    # balia no tiene casillas de correo ni calendario configurados todavia --
    # no debe crashear ni mandar los 3 bloques extra (siguen siendo solo
    # para bambutech/gbs).
    client_bot, chat_ids = _make_telegram()
    ghl = _make_ghl()
    supabase = MagicMock()

    notify(
        (client_bot, chat_ids), supabase, "🟣 *Nuevo contacto en el CRM*",
        cliente_slug="balia", ghl_contact_id="contact-3", ghl_location_id="loc3",
        prospect_name="Ana", prospect_email="ana@balia.cl", dry_run=False, ghl=ghl,
    )

    assert client_bot.send_message.call_count == 1
    ghl.custom_field_id_map.assert_not_called()


def test_notify_mismatch_sin_contact_id_no_manda_botones_extra_ni_rompe():
    # Tarjeta de mismatch (ghl_contact_id=None): no hay a quien mandarle
    # status/agendar/tarea, y no debe romper aunque sea bambutech.
    client_bot, chat_ids = _make_telegram()
    ghl = _make_ghl()
    supabase = MagicMock()

    notify(
        (client_bot, chat_ids), supabase, "⚠️ *Revisar a mano*",
        cliente_slug="bambutech", ghl_contact_id=None, ghl_location_id="loc1",
        prospect_name="Caterina", prospect_email="cate@transapp.cl", dry_run=False, ghl=ghl,
    )

    assert client_bot.send_message.call_count == 1
    ghl.custom_field_id_map.assert_not_called()
    supabase.insert.assert_not_called()


def test_notify_dry_run_no_manda_nada():
    client_bot, chat_ids = _make_telegram()
    ghl = _make_ghl()
    supabase = MagicMock()

    notify(
        (client_bot, chat_ids), supabase, "🟢 *Nuevo contacto en el CRM*",
        cliente_slug="bambutech", ghl_contact_id="contact-1", ghl_location_id="loc1",
        prospect_name="Caterina", prospect_email="cate@transapp.cl", dry_run=True, ghl=ghl,
    )

    client_bot.send_message.assert_not_called()


def test_notify_un_bloque_que_falla_no_frena_a_los_demas():
    # Si custom_field_options tira una excepcion (ej. GHL caido), el bloque
    # de status se pierde pero agendar/tarea igual deben mandarse.
    client_bot, chat_ids = _make_telegram()
    ghl = _make_ghl()
    ghl.custom_field_options.side_effect = RuntimeError("GHL caido")
    supabase = MagicMock()

    notify(
        (client_bot, chat_ids), supabase, "🟢 *Nuevo contacto en el CRM*",
        cliente_slug="bambutech", ghl_contact_id="contact-1", ghl_location_id="loc1",
        prospect_name="Caterina", prospect_email="cate@transapp.cl", dry_run=False, ghl=ghl,
    )

    # Tarjeta + agendar + tarea = 3 (status se perdio por la excepcion).
    assert client_bot.send_message.call_count == 3
