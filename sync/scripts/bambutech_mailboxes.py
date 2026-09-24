from __future__ import annotations

import email
import imaplib
from email.header import decode_header
from typing import Any

from config import get_optional_env

BAMBUTECH_ACCOUNTS = ["BAMBUTECH01", "BAMBUTECH02"]  # michelle@ y michelle.hernandez@


def _decode(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    return "".join(
        part.decode(enc or "utf-8", errors="replace") if isinstance(part, bytes) else part
        for part, enc in parts
    )


def _account_credentials(account_key: str) -> tuple[str, str] | None:
    email_addr = get_optional_env(f"SMTP_{account_key}_EMAIL")
    password = get_optional_env(f"SMTP_{account_key}_PASSWORD")
    if not email_addr or not password:
        return None
    return email_addr, password


def find_reply_thread(prospect_email: str) -> dict[str, Any] | None:
    """Busca en las casillas de BambuTech el ultimo correo REAL recibido de
    prospect_email. Devuelve {account_email, message_id, subject, body,
    references} o None si no se encuentra en ninguna."""
    for account_key in BAMBUTECH_ACCOUNTS:
        creds = _account_credentials(account_key)
        if not creds:
            continue
        account_email, password = creds
        result = _search_mailbox(account_email, password, prospect_email)
        if result:
            return {**result, "account_email": account_email}
    return None


def _search_mailbox(account_email: str, password: str, prospect_email: str) -> dict[str, Any] | None:
    conn = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    try:
        conn.login(account_email, password)
        conn.select("INBOX")
        status, data = conn.search(None, f'(FROM "{prospect_email}")')
        if status != "OK" or not data or not data[0]:
            return None
        message_ids = data[0].split()
        latest_id = message_ids[-1]
        status, msg_data = conn.fetch(latest_id, "(RFC822)")
        if status != "OK" or not msg_data or not msg_data[0]:
            return None
        raw = msg_data[0][1]
        message = email.message_from_bytes(raw)
        body = _extract_plain_text(message)
        return {
            "message_id": message.get("Message-ID"),
            "references": message.get("References") or message.get("Message-ID"),
            "subject": _decode(message.get("Subject")),
            "body": body,
        }
    finally:
        conn.logout()


def _extract_plain_text(message: email.message.Message) -> str:
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                charset = part.get_content_charset() or "utf-8"
                return part.get_payload(decode=True).decode(charset, errors="replace")
        return ""
    charset = message.get_content_charset() or "utf-8"
    payload = message.get_payload(decode=True)
    return payload.decode(charset, errors="replace") if payload else ""
