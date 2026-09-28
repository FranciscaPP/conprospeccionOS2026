import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from report_sdr_bot import BotController


def test_bot_ignores_unauthorized_chat():
    calls = []
    controller = BotController(allowed_chat_id="123", query=lambda request: calls.append(request) or ["ok"])
    assert controller.handle({"chat": {"id": 999}, "text": "resumen"}) is None
    assert calls == []


def test_bot_answers_authorized_chat_with_shared_query():
    calls = []
    controller = BotController(allowed_chat_id="123", query=lambda request: calls.append(request) or ["respuesta"])
    assert controller.handle({"chat": {"id": 123}, "text": "llamadas"}) == ["respuesta"]
    assert calls[0].intents == ("call_counts",)
