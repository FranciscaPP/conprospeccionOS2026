import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

import pytest

from report_sdr_bot import BotController, process_queued_query


class FakeStore:
    def __init__(self, row):
        self.row = row
        self.answered = []
        self.failed = []

    def claim_query(self, update_id):
        return self.row

    def mark_query_answered(self, update_id):
        self.answered.append(update_id)

    def mark_query_failed(self, update_id, error):
        self.failed.append((update_id, error))


class FakeSender:
    def __init__(self):
        self.messages = []

    def send_message(self, text, reply_markup=None):
        self.messages.append((text, reply_markup))


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


def test_queued_query_uses_shared_parser_and_marks_answered_once():
    store = FakeStore({"update_id": 12345, "chat_id": 123, "text": "llamadas"})
    sender = FakeSender()
    requests = []

    processed = process_queued_query(
        12345,
        store,
        sender,
        "123",
        query=lambda request: requests.append(request) or ["parte 1", "parte 2"],
    )

    assert processed is True
    assert requests[0].intents == ("call_counts",)
    assert sender.messages[0] == ("parte 1", None)
    assert sender.messages[1][0] == "parte 2"
    assert sender.messages[1][1] is not None
    assert store.answered == [12345]
    assert store.failed == []


def test_answered_or_duplicate_query_is_not_sent_again():
    store = FakeStore(None)
    sender = FakeSender()

    assert process_queued_query(12345, store, sender, "123") is False
    assert sender.messages == []
    assert store.answered == []


def test_queued_query_failure_is_persisted_for_one_retry():
    store = FakeStore({"update_id": 12345, "chat_id": 123, "text": "resumen"})

    with pytest.raises(RuntimeError, match="falló la consulta"):
        process_queued_query(
            12345,
            store,
            FakeSender(),
            "123",
            query=lambda request: (_ for _ in ()).throw(RuntimeError("falló la consulta")),
        )

    assert store.answered == []
    assert store.failed[0][0] == 12345


def test_queued_query_rejects_a_row_for_another_chat():
    store = FakeStore({"update_id": 12345, "chat_id": 999, "text": "resumen"})

    with pytest.raises(RuntimeError, match="chat no autorizado"):
        process_queued_query(12345, store, FakeSender(), "123")

    assert store.failed[0][0] == 12345
