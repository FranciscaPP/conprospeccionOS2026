import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from sdr_reporting.telegram import EquipoAliciaTelegram


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeTransport:
    def __init__(self, username="equipo_alicia_bot"):
        self.username = username
        self.posts = []

    def get(self, url, **kwargs):
        return FakeResponse({"ok": True, "result": {"username": self.username, "is_bot": True}})

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        return FakeResponse({"ok": True, "result": {"message_id": 7}})


def test_sender_rejects_wrong_bot():
    sender = EquipoAliciaTelegram("token", "123", transport=FakeTransport("otro_bot"))
    with pytest.raises(RuntimeError, match="equipo_alicia_bot"):
        sender.verify_identity()


def test_sender_uses_html_and_only_configured_chat():
    transport = FakeTransport()
    sender = EquipoAliciaTelegram("token", "123", transport=transport)
    sender.send_message("<b>hola</b>")

    assert len(transport.posts) == 1
    _, kwargs = transport.posts[0]
    assert kwargs["json"] == {
        "chat_id": "123",
        "text": "<b>hola</b>",
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }


def test_sender_rejects_empty_credentials():
    with pytest.raises(RuntimeError, match="TELEGRAM_SDR_TOKEN"):
        EquipoAliciaTelegram("", "123")
    with pytest.raises(RuntimeError, match="TELEGRAM_SDR_CHAT_ID"):
        EquipoAliciaTelegram("token", "")

