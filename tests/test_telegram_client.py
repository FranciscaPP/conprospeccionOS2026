"""Tests de sync/scripts/telegram_client.py con httpx mockeado (sin red real)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from telegram_client import TelegramClient


def _mock_response(json_data):
    response = MagicMock()
    response.json.return_value = json_data
    response.raise_for_status.return_value = None
    return response


def test_send_message_llama_al_endpoint_correcto():
    client = TelegramClient("FAKE_TOKEN")
    client.client.post = MagicMock(return_value=_mock_response({"ok": True, "result": {"message_id": 42}}))

    result = client.send_message("123", "hola")

    client.client.post.assert_called_once()
    args, kwargs = client.client.post.call_args
    assert args[0] == "https://api.telegram.org/botFAKE_TOKEN/sendMessage"
    assert kwargs["json"]["chat_id"] == "123"
    assert kwargs["json"]["text"] == "hola"
    assert result["message_id"] == 42


def test_send_message_incluye_reply_markup_si_se_pasa():
    client = TelegramClient("FAKE_TOKEN")
    client.client.post = MagicMock(return_value=_mock_response({"ok": True, "result": {"message_id": 1}}))

    keyboard = {"inline_keyboard": [[{"text": "A", "callback_data": "a"}]]}
    client.send_message("123", "hola", reply_markup=keyboard)

    _, kwargs = client.client.post.call_args
    assert kwargs["json"]["reply_markup"] == keyboard


def test_get_updates_pasa_el_offset():
    client = TelegramClient("FAKE_TOKEN")
    client.client.get = MagicMock(return_value=_mock_response({"ok": True, "result": [{"update_id": 5}]}))

    result = client.get_updates(offset=5, timeout=1)

    args, kwargs = client.client.get.call_args
    assert kwargs["params"]["offset"] == 5
    assert result == [{"update_id": 5}]
