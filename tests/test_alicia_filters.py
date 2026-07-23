"""Tests del filtrado determinístico de correos (sin IA)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alicia.reply_filters import (
    Classification,
    classify,
    normalize_headers,
    sender_email,
)


def h(**kwargs):
    """Construye lista de cabeceras estilo Gmail a partir de kwargs."""
    return [{"name": k.replace("_", "-"), "value": v} for k, v in kwargs.items()]


def test_genuine_reply_passes():
    headers = h(From="Juan Perez <juan@empresa.com>", Subject="Re: Propuesta comercial")
    classification, _ = classify(headers, ["INBOX", "UNREAD"])
    assert classification is Classification.GENUINE


def test_spam_label_detected():
    headers = h(From="x@y.com", Subject="hola")
    classification, reason = classify(headers, ["SPAM"])
    assert classification is Classification.SPAM
    assert "spam" in reason.lower()


def test_mailer_daemon_bounce():
    headers = h(From="Mail Delivery Subsystem <MAILER-DAEMON@google.com>", Subject="Undelivered Mail Returned to Sender")
    classification, _ = classify(headers, ["INBOX"])
    assert classification is Classification.BOUNCE


def test_dsn_content_type_bounce():
    headers = h(
        From="postmaster@empresa.com",
        Subject="Delivery Status Notification (Failure)",
        Content_Type="multipart/report; report-type=delivery-status; boundary=abc",
    )
    classification, _ = classify(headers, ["INBOX"])
    assert classification is Classification.BOUNCE


def test_empty_return_path_bounce():
    headers = h(From="algo@empresa.com", Subject="aviso", Return_Path="<>")
    classification, _ = classify(headers, ["INBOX"])
    assert classification is Classification.BOUNCE


def test_out_of_office_subject():
    headers = h(From="ceo@empresa.com", Subject="Automatic reply: Out of office")
    classification, _ = classify(headers, ["INBOX"])
    assert classification is Classification.OUT_OF_OFFICE


def test_out_of_office_spanish():
    headers = h(From="ceo@empresa.com", Subject="Respuesta automática - Fuera de la oficina")
    classification, _ = classify(headers, ["INBOX"])
    assert classification is Classification.OUT_OF_OFFICE


def test_auto_submitted_header():
    headers = h(From="ceo@empresa.com", Subject="Gracias", Auto_Submitted="auto-replied")
    classification, _ = classify(headers, ["INBOX"])
    assert classification is Classification.AUTO_REPLY


def test_precedence_bulk_auto():
    headers = h(From="news@empresa.com", Subject="Newsletter", Precedence="bulk")
    classification, _ = classify(headers, ["INBOX"])
    assert classification is Classification.AUTO_REPLY


def test_x_autoreply_header():
    headers = h(From="ceo@empresa.com", Subject="ok", X_Autoreply="yes")
    classification, _ = classify(headers, ["INBOX"])
    assert classification is Classification.AUTO_REPLY


def test_sender_email_extraction():
    assert sender_email({"from": "Juan Perez <juan.perez@empresa.com>"}) == "juan.perez@empresa.com"
    assert sender_email({"from": "solo@dominio.cl"}) == "solo@dominio.cl"
    assert sender_email({"from": "sin correo"}) == ""


def test_normalize_headers_dedup_and_lowercase():
    normalized = normalize_headers(h(From="a@b.com", Subject="X"))
    assert normalized["from"] == "a@b.com"
    assert normalized["subject"] == "X"


def test_bounce_takes_priority_over_genuine():
    headers = h(From="MAILER-DAEMON@x.com", Subject="Re: propuesta")
    classification, _ = classify(headers, ["INBOX", "UNREAD"])
    assert classification is Classification.BOUNCE
