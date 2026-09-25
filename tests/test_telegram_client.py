"""Tests de sync/scripts/telegram_client.py con httpx mockeado (sin red real)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from telegram_client import TelegramClient


def _mock_response(json_data, status_code=200, text=""):
    response = MagicMock()
    response.json.return_value = json_data
    response.status_code = status_code
    response.text = text
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


def test_send_message_reintenta_sin_markdown_si_telegram_rechaza_por_entidades():
    client = TelegramClient("FAKE_TOKEN")
    error_response = _mock_response(
        {
            "ok": False,
            "error_code": 400,
            "description": "Bad Request: can't parse entities: Character '(' is reserved and must be escaped",
        },
        status_code=400,
        text='{"ok":false,"error_code":400,"description":"Bad Request: can\'t parse entities: Character \'(\' is reserved and must be escaped"}',
    )
    success_response = _mock_response({"ok": True, "result": {"message_id": 99}}, status_code=200)
    responses = [error_response, success_response]
    sent_bodies = []

    def _fake_post(url, json):
        sent_bodies.append(dict(json))  # snapshot: `json` es mutado in-place por el reintento
        return responses.pop(0)

    client.client.post = MagicMock(side_effect=_fake_post)

    result = client.send_message("123", "Empresa (Grupo_XYZ)")

    assert client.client.post.call_count == 2
    first_body, second_body = sent_bodies
    assert first_body["parse_mode"] == "Markdown"
    assert "parse_mode" not in second_body
    assert second_body["text"] == "Empresa (Grupo_XYZ)"
    assert result["message_id"] == 99


def test_send_message_no_reintenta_si_el_primer_intento_tiene_exito():
    client = TelegramClient("FAKE_TOKEN")
    client.client.post = MagicMock(return_value=_mock_response({"ok": True, "result": {"message_id": 1}}, status_code=200))

    client.send_message("123", "hola")

    client.client.post.assert_called_once()


def test_send_message_no_reintenta_si_el_400_no_es_por_parseo():
    client = TelegramClient("FAKE_TOKEN")
    error_response = _mock_response(
        {"ok": False, "error_code": 400, "description": "Bad Request: chat not found"},
        status_code=400,
        text='{"ok":false,"error_code":400,"description":"Bad Request: chat not found"}',
    )
    error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "400 Bad Request", request=MagicMock(), response=error_response
    )
    client.client.post = MagicMock(return_value=error_response)

    with pytest.raises(httpx.HTTPStatusError):
        client.send_message("123", "hola")

    client.client.post.assert_called_once()
