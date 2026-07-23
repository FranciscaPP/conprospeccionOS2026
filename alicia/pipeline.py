"""Orquestación del poller determinístico. SIN IA.

Una corrida:
  para cada cuenta habilitada → listar correos nuevos (Gmail) → clasificar por
  código → correlacionar con Snov → deduplicar → armar UNA notificación agrupada
  para Telegram. Nada de esto llama a un modelo de IA.

Todo se inyecta (Gmail, estado, Snov, Telegram) para poder probar con fakes sin
red. `dry_run` evita mutar Gmail (no marca leído); la idempotencia real vive en
la tabla `alicia_processed_messages`.
"""
from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from alicia import accounts as accounts_mod
from alicia.notifications import ReplyRecord, build_notification
from alicia.reply_filters import Classification, classify, sender_email
from alicia.snov_match import SnovLookup

logger = logging.getLogger("alicia.pipeline")


@dataclass
class PipelineDeps:
    accounts: list[accounts_mod.Account]
    gmail_factory: Callable[[accounts_mod.Account], Any]
    state: Any                 # AliciaState o fake
    snov: SnovLookup
    telegram: Any | None       # TelegramClient o None (no enviar)
    lookback_hours: int = 14
    dry_run: bool = True


@dataclass
class RunResult:
    accounts_checked: int = 0
    messages_scanned: int = 0
    replies_detected: int = 0
    filtered_out: Counter = field(default_factory=Counter)
    replies: list[ReplyRecord] = field(default_factory=list)
    notification: list[str] = field(default_factory=list)


def _headers_of(meta: dict[str, Any]) -> list[dict[str, str]]:
    payload = meta.get("payload") or {}
    return payload.get("headers") or []


def _header_value(headers: list[dict[str, str]], name: str) -> str:
    low = name.lower()
    for item in headers:
        if str(item.get("name", "")).lower() == low:
            return str(item.get("value", "")).strip()
    return ""


def _process_account(account: accounts_mod.Account, deps: PipelineDeps, result: RunResult) -> None:
    gmail = deps.gmail_factory(account)
    message_ids = gmail.list_new_message_ids(deps.lookback_hours)
    for message_id in message_ids:
        result.messages_scanned += 1
        if deps.state.already_processed(message_id):
            continue

        meta = gmail.get_metadata(message_id)
        headers = _headers_of(meta)
        thread_id = str(meta.get("threadId") or message_id)
        label_ids = meta.get("labelIds") or []

        classification, reason = classify(headers, label_ids)

        if classification in {
            Classification.BOUNCE,
            Classification.AUTO_REPLY,
            Classification.OUT_OF_OFFICE,
            Classification.SPAM,
        }:
            result.filtered_out[classification.value] += 1
            deps.state.mark_processed(message_id, thread_id, account.account_id, classification.value)
            continue

        # Respuesta genuina por cabeceras → confirmar contra Snov.
        from_email = sender_email({"from": _header_value(headers, "From")})
        match = deps.snov.by_email(from_email)
        if not match.matched:
            result.filtered_out[Classification.UNRELATED.value] += 1
            deps.state.mark_processed(
                message_id, thread_id, account.account_id, Classification.UNRELATED.value
            )
            continue

        subject = _header_value(headers, "Subject")
        snippet = str(meta.get("snippet") or "")
        internal_ref = accounts_mod.internal_ref(thread_id)

        deps.state.upsert_thread(
            {
                "thread_id": thread_id,
                "internal_ref": internal_ref,
                "account_id": account.account_id,
                "account_email": account.email,
                "prospect_email": from_email,
                "prospect_name": match.prospect_name,
                "empresa": match.empresa,
                "snov_campaign_id": match.snov_campaign_id,
                "cliente_slug": match.cliente_slug or account.cliente_slug,
                "subject": subject,
                "last_message_snippet": snippet,
                "last_gmail_message_id": message_id,
                "classification": Classification.GENUINE.value,
                "estado": "alertada",
                "dry_run": deps.dry_run,
                "last_seen_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        deps.state.mark_processed(
            message_id, thread_id, account.account_id, Classification.GENUINE.value
        )

        result.replies_detected += 1
        result.replies.append(
            ReplyRecord(
                internal_ref=internal_ref,
                cliente=match.cliente_slug or account.cliente_slug,
                campaign=match.campaign_name or match.snov_campaign_id,
                account_email=account.email,
                prospect=match.prospect_name or from_email,
                empresa=match.empresa,
                subject=subject,
                last_message=snippet,
            )
        )

        # En dry-run no mutamos Gmail (no marcamos leído); la idempotencia ya
        # quedó garantizada por alicia_processed_messages.
        if not deps.dry_run:
            try:
                gmail.mark_read(message_id)
            except Exception as exc:  # marcar leído nunca debe tumbar la corrida
                logger.warning("No se pudo marcar leído %s: %s", message_id, exc)


def run(deps: PipelineDeps) -> RunResult:
    result = RunResult()
    for account in deps.accounts:
        result.accounts_checked += 1
        try:
            _process_account(account, deps, result)
        except Exception as exc:
            logger.exception("Fallo procesando cuenta %s: %s", account.account_id, exc)

    result.notification = build_notification(result.replies)

    if deps.telegram is not None and result.replies:
        try:
            deps.telegram.send_all(result.notification)
        except Exception as exc:
            logger.exception("No se pudo enviar la notificación a Telegram: %s", exc)

    logger.info(
        "Alicia run · cuentas=%s escaneados=%s respuestas=%s filtrados=%s dry_run=%s",
        result.accounts_checked,
        result.messages_scanned,
        result.replies_detected,
        dict(result.filtered_out),
        deps.dry_run,
    )
    return result
