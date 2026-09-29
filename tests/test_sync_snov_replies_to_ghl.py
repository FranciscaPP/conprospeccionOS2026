"""Tests de sync/scripts/sync_snov_replies_to_ghl.py: limpieza de HTML del
snippet de respuesta (_strip_html) y la logica que decide de donde sale el
snippet y la casilla real donde se respondio (_reply_snippet_and_source),
todo mockeado -- sin IMAP/Telegram/GHL reales."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from sync_snov_replies_to_ghl import _reply_snippet_and_source, _strip_html

REAL_SNOV_HTML = (
    '<div dir="auto"><div>Hola Michelle.</div><div dir="auto"><br></div>'
    '<div dir="auto">Gracias no estamos interesados en este momento.</div>'
    '<div dir="auto"><br></div><div dir="auto">Saludos.</div></div>'
)


def test_strip_html_deja_texto_legible_sin_tags():
    result = _strip_html(REAL_SNOV_HTML)
    assert "<div" not in result
    assert "<br" not in result
    assert "Hola Michelle." in result
    assert "Gracias no estamos interesados en este momento." in result
    assert "Saludos." in result


def test_strip_html_decodifica_entidades():
    result = _strip_html("<div>Ol&aacute; &amp; gracias &lt;3</div>")
    assert "Olá & gracias <3" in result


def test_strip_html_colapsa_espacios_de_mas():
    result = _strip_html("<p>Hola    mundo</p>\n\n<p>otra linea</p>")
    assert "  " not in result


def test_strip_html_vacio_no_rompe():
    assert _strip_html("") == ""
    assert _strip_html(None) is None


def test_reply_snippet_bambutech_usa_body_de_imap_cuando_se_encuentra():
    with patch("sync_snov_replies_to_ghl.client_mailboxes.find_reply_thread") as mock_find:
        mock_find.return_value = {
            "body": "Hola, texto plano real de IMAP.",
            "account_email": "michelle@bambutech.com",
        }
        snippet, desde = _reply_snippet_and_source("bambutech", "prospecto@x.cl", "<div>html de snov</div>")
    mock_find.assert_called_once_with("bambutech", "prospecto@x.cl")
    assert snippet == "Hola, texto plano real de IMAP."
    assert desde == "michelle@bambutech.com"


def test_reply_snippet_gbs_cae_a_snov_cuando_imap_no_encuentra_nada():
    with patch("sync_snov_replies_to_ghl.client_mailboxes.find_reply_thread") as mock_find:
        mock_find.return_value = None
        snippet, desde = _reply_snippet_and_source("gbs", "prospecto@x.cl", "<div>Hola</div><div>mundo</div>")
    mock_find.assert_called_once_with("gbs", "prospecto@x.cl")
    assert snippet == "Hola mundo"
    assert desde is None


def test_reply_snippet_cliente_sin_casillas_no_llama_a_imap():
    with patch("sync_snov_replies_to_ghl.client_mailboxes.find_reply_thread") as mock_find:
        snippet, desde = _reply_snippet_and_source("otro_cliente", "prospecto@x.cl", "<div>Hola</div>")
    mock_find.assert_not_called()
    assert snippet == "Hola"
    assert desde is None


def test_reply_snippet_excepcion_de_imap_no_propaga_y_cae_a_snov():
    with patch("sync_snov_replies_to_ghl.client_mailboxes.find_reply_thread") as mock_find:
        mock_find.side_effect = RuntimeError("IMAP caido")
        snippet, desde = _reply_snippet_and_source("bambutech", "prospecto@x.cl", "<div>Hola</div>")
    assert snippet == "Hola"
    assert desde is None
