"""Construcción de la notificación agrupada de Telegram. SIN IA.

Una sola notificación por ejecución del poller, con el total de respuestas y, por
cada una: cliente, campaña, cuenta receptora, prospecto, empresa, asunto, último
mensaje e identificador interno. El texto se arma con reglas; ningún modelo.
"""
from __future__ import annotations

from dataclasses import dataclass

# Límite de Telegram por mensaje. Dejamos margen para el troceo.
TELEGRAM_LIMIT = 3800


@dataclass(frozen=True)
class ReplyRecord:
    internal_ref: str
    cliente: str | None
    campaign: str | None
    account_email: str | None
    prospect: str | None
    empresa: str | None
    subject: str | None
    last_message: str | None


def _clean(value: str | None, fallback: str = "—") -> str:
    text = (value or "").strip()
    return text if text else fallback


def _truncate(value: str | None, limit: int = 320) -> str:
    text = (value or "").strip().replace("\r", " ").replace("\n", " ")
    if len(text) <= limit:
        return text or "—"
    return text[: limit - 1].rstrip() + "…"


def format_reply(index: int, reply: ReplyRecord) -> str:
    return (
        f"{index}. [{reply.internal_ref}] "
        f"{_clean(reply.prospect)} · {_clean(reply.empresa)}\n"
        f"   Cliente: {_clean(reply.cliente)} · Campaña: {_clean(reply.campaign)}\n"
        f"   Cuenta: {_clean(reply.account_email)}\n"
        f"   Asunto: {_clean(reply.subject)}\n"
        f"   Último mensaje: {_truncate(reply.last_message)}"
    )


def build_notification(replies: list[ReplyRecord]) -> list[str]:
    """Devuelve una lista de mensajes (troceados si exceden el límite de Telegram).

    Si no hay respuestas nuevas, devuelve una sola línea informativa.
    """
    total = len(replies)
    if total == 0:
        return ["Alicia · sin respuestas nuevas de campañas Snov en esta ejecución."]

    header = f"Alicia · {total} respuesta(s) de campañas Snov detectada(s):"
    blocks = [format_reply(i + 1, reply) for i, reply in enumerate(replies)]

    messages: list[str] = []
    current = header
    for block in blocks:
        candidate = f"{current}\n\n{block}"
        if len(candidate) > TELEGRAM_LIMIT:
            messages.append(current)
            current = block
        else:
            current = candidate
    messages.append(current)

    if len(messages) > 1:
        messages = [f"({i + 1}/{len(messages)}) {m}" for i, m in enumerate(messages)]
    return messages
