"""Tests de sync/scripts/client_mailboxes.py (logica pura, sin red real)."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

import client_mailboxes
from client_mailboxes import CLIENT_ACCOUNTS, find_reply_thread, send_reply


def _set_creds(monkeypatch, account_key: str, email: str, password: str = "pw") -> None:
    monkeypatch.setenv(f"SMTP_{account_key}_EMAIL", email)
    monkeypatch.setenv(f"SMTP_{account_key}_PASSWORD", password)


def test_client_accounts_tiene_bambutech_y_gbs():
    assert CLIENT_ACCOUNTS["bambutech"] == ["BAMBUTECH01", "BAMBUTECH02"]
    assert CLIENT_ACCOUNTS["gbs"] == ["GBS01", "GBS02", "GBS03"]


def test_find_reply_thread_gbs_busca_solo_casillas_de_gbs(monkeypatch):
    # No debe tocar las casillas de bambutech -- solo las 3 de gbs.
    _set_creds(monkeypatch, "BAMBUTECH01", "michelle@bambutech.test")
    _set_creds(monkeypatch, "GBS01", "sam@gbs-logistics.cl")
    _set_creds(monkeypatch, "GBS02", "sammiller@gbs-logistics.cl")
    _set_creds(monkeypatch, "GBS03", "sam.miller@gbs-logistics.cl")

    searched_accounts = []

    def fake_search(account_email, password, prospect_email):
        searched_accounts.append(account_email)
        if account_email == "sammiller@gbs-logistics.cl":
            return {"message_id": "<m1>", "references": "<m1>", "subject": "Hola", "body": "cuerpo"}
        return None

    with patch.object(client_mailboxes, "_search_mailbox", side_effect=fake_search):
        result = find_reply_thread("gbs", "prospecto@ejemplo.com")

    assert result is not None
    assert result["account_email"] == "sammiller@gbs-logistics.cl"
    assert "michelle@bambutech.test" not in searched_accounts
    assert searched_accounts == ["sam@gbs-logistics.cl", "sammiller@gbs-logistics.cl"]


def test_find_reply_thread_slug_desconocido_devuelve_none(monkeypatch):
    assert find_reply_thread("balia", "prospecto@ejemplo.com") is None


def test_find_reply_thread_una_casilla_rota_no_aborta_la_busqueda(monkeypatch):
    # SMTP_GBS01 simula credenciales invalidas (login IMAP falla) -- las
    # otras 2 casillas de gbs deben seguir intentandose igual.
    _set_creds(monkeypatch, "GBS01", "sam@gbs-logistics.cl")
    _set_creds(monkeypatch, "GBS02", "sammiller@gbs-logistics.cl")
    _set_creds(monkeypatch, "GBS03", "sam.miller@gbs-logistics.cl")

    attempted = []

    def fake_search(account_email, password, prospect_email):
        attempted.append(account_email)
        if account_email == "sam@gbs-logistics.cl":
            raise Exception("IMAP login failed: bad credentials")
        return None

    with patch.object(client_mailboxes, "_search_mailbox", side_effect=fake_search):
        result = find_reply_thread("gbs", "prospecto@ejemplo.com")

    assert result is None
    # Las 3 casillas fueron intentadas -- la rota no corto la busqueda.
    assert attempted == ["sam@gbs-logistics.cl", "sammiller@gbs-logistics.cl", "sam.miller@gbs-logistics.cl"]


def test_send_reply_encuentra_cuenta_de_cualquier_cliente(monkeypatch):
    # send_reply no recibe cliente_slug -- debe encontrar la cuenta por
    # email entre TODOS los clientes, no solo bambutech.
    _set_creds(monkeypatch, "BAMBUTECH01", "michelle@bambutech.test")
    _set_creds(monkeypatch, "GBS02", "sammiller@gbs-logistics.cl", "gbspw")

    sent = {}

    class FakeSMTP:
        def __init__(self, *a, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def login(self, user, password):
            sent["user"] = user
            sent["password"] = password

        def send_message(self, msg):
            sent["msg"] = msg

    with patch("client_mailboxes.smtplib.SMTP_SSL", FakeSMTP):
        send_reply("sammiller@gbs-logistics.cl", "prospecto@ejemplo.com", "Asunto", "cuerpo", None)

    assert sent["user"] == "sammiller@gbs-logistics.cl"
    assert sent["password"] == "gbspw"


def test_send_reply_cuenta_no_configurada_lanza_error(monkeypatch):
    monkeypatch.delenv("SMTP_GBS01_EMAIL", raising=False)
    monkeypatch.delenv("SMTP_GBS02_EMAIL", raising=False)
    monkeypatch.delenv("SMTP_GBS03_EMAIL", raising=False)
    monkeypatch.delenv("SMTP_BAMBUTECH01_EMAIL", raising=False)
    monkeypatch.delenv("SMTP_BAMBUTECH02_EMAIL", raising=False)

    try:
        send_reply("nadie@ejemplo.com", "prospecto@ejemplo.com", "Asunto", "cuerpo", None)
        assert False, "deberia haber lanzado RuntimeError"
    except RuntimeError as exc:
        assert "nadie@ejemplo.com" in str(exc)
