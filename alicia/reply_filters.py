"""Clasificación determinística de mensajes de correo. SIN IA.

A partir de las cabeceras y etiquetas que entrega Gmail API, decide si un mensaje
es una respuesta genuina de un prospecto o si debe excluirse (rebote, respuesta
automática, fuera de oficina, spam). Todo con reglas de código; ningún modelo.

La decisión de "no relacionado con Snov" NO se toma aquí: depende de la
correlación con datos de Snov (ver alicia/snov_match.py). Aquí solo se detecta lo
que se puede saber por cabeceras.
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Iterable


class Classification(str, Enum):
    GENUINE = "genuine"
    BOUNCE = "bounce"
    AUTO_REPLY = "auto_reply"
    OUT_OF_OFFICE = "out_of_office"
    SPAM = "spam"
    UNRELATED = "unrelated"  # asignada por el pipeline cuando no hay match Snov


EXCLUDED = frozenset(
    {
        Classification.BOUNCE,
        Classification.AUTO_REPLY,
        Classification.OUT_OF_OFFICE,
        Classification.SPAM,
        Classification.UNRELATED,
    }
)

_BOUNCE_SENDERS = (
    "mailer-daemon",
    "postmaster",
    "mail delivery subsystem",
    "maildelivery",
    "no-reply-delivery",
)

_BOUNCE_SUBJECTS = (
    "undelivered mail",
    "undeliverable",
    "delivery status notification",
    "delivery has failed",
    "returned mail",
    "mail delivery failed",
    "failure notice",
    "correo no entregado",
    "no se pudo entregar",
    "devuelto al remitente",
)

_OOO_SUBJECTS = (
    "out of office",
    "out-of-office",
    "automatic reply",
    "auto-reply",
    "autoreply",
    "respuesta automática",
    "respuesta automatica",
    "fuera de la oficina",
    "fuera de oficina",
    "ausencia",
    "de vacaciones",
    "on vacation",
    "away from",
    "je suis absent",
)

# Cabeceras que marcan correo automatizado según RFC 3834 y usos de facto.
_AUTO_HEADER_TOKENS = {
    "auto-submitted": ("auto-replied", "auto-generated", "auto_replied", "auto_generated"),
    "precedence": ("auto_reply", "bulk", "junk", "list"),
}


def normalize_headers(headers: Iterable[dict[str, str]] | dict[str, str]) -> dict[str, str]:
    """Aplana las cabeceras de Gmail (lista de {name,value}) a un dict en minúsculas.

    Si una cabecera se repite, se conserva la concatenación para no perder señales.
    """
    out: dict[str, str] = {}
    if isinstance(headers, dict):
        for key, value in headers.items():
            out[str(key).strip().lower()] = str(value or "").strip()
        return out
    for item in headers or []:
        name = str(item.get("name", "")).strip().lower()
        value = str(item.get("value", "")).strip()
        if not name:
            continue
        out[name] = f"{out[name]} | {value}" if name in out else value
    return out


def _contains(haystack: str, needles: Iterable[str]) -> bool:
    low = haystack.lower()
    return any(needle in low for needle in needles)


def is_bounce(headers: dict[str, str]) -> bool:
    from_field = headers.get("from", "")
    subject = headers.get("subject", "")
    content_type = headers.get("content-type", "").lower()
    return_path = headers.get("return-path", "").strip()
    if _contains(from_field, _BOUNCE_SENDERS):
        return True
    if _contains(subject, _BOUNCE_SUBJECTS):
        return True
    # Reportes de estado de entrega (DSN).
    if "multipart/report" in content_type and "delivery-status" in content_type:
        return True
    # Return-Path vacío "<>" es típico de notificaciones de rebote.
    if return_path in {"<>", "<>"}:
        return True
    return False


def is_out_of_office(headers: dict[str, str]) -> bool:
    if _contains(headers.get("subject", ""), _OOO_SUBJECTS):
        return True
    # Microsoft/Exchange marca OOO con este valor específico.
    if headers.get("x-auto-response-suppress"):
        return True
    return False


def is_auto_reply(headers: dict[str, str]) -> bool:
    for header, tokens in _AUTO_HEADER_TOKENS.items():
        value = headers.get(header, "").lower()
        if value and any(token in value for token in tokens):
            return True
    if headers.get("x-autoreply") or headers.get("x-autorespond") or headers.get("x-autoresponder"):
        return True
    return False


def is_spam(label_ids: Iterable[str] | None) -> bool:
    labels = {str(x).upper() for x in (label_ids or [])}
    return "SPAM" in labels


def sender_email(headers: dict[str, str]) -> str:
    raw = headers.get("from", "")
    match = re.search(r"[\w.\-+']+@[\w.\-]+\.\w+", raw)
    return match.group(0).lower() if match else ""


def classify(
    headers: Iterable[dict[str, str]] | dict[str, str],
    label_ids: Iterable[str] | None = None,
) -> tuple[Classification, str]:
    """Devuelve (clasificación, razón). Orden: spam → rebote → OOO → auto → genuina."""
    hdr = normalize_headers(headers)
    if is_spam(label_ids):
        return Classification.SPAM, "gmail label SPAM"
    if is_bounce(hdr):
        return Classification.BOUNCE, "cabeceras/asunto de rebote (DSN/MAILER-DAEMON)"
    if is_out_of_office(hdr):
        return Classification.OUT_OF_OFFICE, "asunto/cabecera de fuera de oficina"
    if is_auto_reply(hdr):
        return Classification.AUTO_REPLY, "cabecera Auto-Submitted/Precedence/X-Autoreply"
    return Classification.GENUINE, "sin señales de automatización"
