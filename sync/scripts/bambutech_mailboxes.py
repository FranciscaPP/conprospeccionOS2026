from __future__ import annotations

import email
import imaplib
import logging
import smtplib
from email.header import decode_header
from email.mime.text import MIMEText
from email.utils import make_msgid
from typing import Any

from config import get_optional_env

logger = logging.getLogger(__name__)

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


def _find_all_mail_folder(conn: imaplib.IMAP4_SSL) -> str | None:
    """Busca en el LIST de carpetas IMAP la que tiene el atributo especial
    \\All (la carpeta "Todos" / "All Mail" de Gmail, que incluye mensajes de
    cualquier label/carpeta, p.ej. el label "snovio"). El nombre exacto varia
    segun el idioma de la cuenta ("[Gmail]/All Mail", "[Gmail]/Todos", etc.),
    por eso no se hardcodea sino que se descubre via LIST."""
    status, folders = conn.list()
    if status != "OK" or not folders:
        return None
    for raw_line in folders:
        if raw_line is None:
            continue
        line = raw_line.decode("utf-8", errors="replace") if isinstance(raw_line, bytes) else raw_line
        if "\\All" not in line:
            continue
        # Formato tipico: b'(\\HasNoChildren \\All) "/" "[Gmail]/All Mail"'
        # El nombre de la carpeta es el ultimo token entre comillas.
        parts = line.split('"')
        if len(parts) >= 2:
            return parts[-2]
    return None


def _quote_mailbox(name: str) -> str:
    if name.startswith('"') and name.endswith('"'):
        return name
    return f'"{name}"'


def _search_mailbox(account_email: str, password: str, prospect_email: str) -> dict[str, Any] | None:
    conn = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    try:
        conn.login(account_email, password)

        all_mail_folder = _find_all_mail_folder(conn)
        selected = False
        if all_mail_folder:
            status, _ = conn.select(_quote_mailbox(all_mail_folder), readonly=True)
            selected = status == "OK"
            if not selected:
                logger.warning(
                    "No se pudo seleccionar la carpeta All Mail (%s) en %s, se usara solo INBOX",
                    all_mail_folder,
                    account_email,
                )
        else:
            logger.warning(
                "No se encontro carpeta All Mail (atributo \\All) en %s, se usara solo INBOX",
                account_email,
            )

        if not selected:
            status, _ = conn.select("INBOX", readonly=True)
            if status != "OK":
                return None

        status, data = conn.search(None, f'(FROM "{prospect_email}")')
        if status != "OK" or not data or not data[0]:
            return None
        message_ids = data[0].split()
        latest_id = message_ids[-1]
        # BODY.PEEK[] es el equivalente de solo-lectura de RFC822: trae el
        # mensaje completo (headers + cuerpo) sin marcar \Seen, a diferencia
        # de RFC822/BODY[] que en modo lectura-escritura si lo marca.
        status, msg_data = conn.fetch(latest_id, "(BODY.PEEK[])")
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


def send_reply(account_email: str, to_email: str, subject: str, body: str, references: str | None) -> None:
    account_key = next(
        (key for key in BAMBUTECH_ACCOUNTS if (get_optional_env(f"SMTP_{key}_EMAIL") or "").lower() == account_email.lower()),
        None,
    )
    if not account_key:
        raise RuntimeError(f"No hay credenciales SMTP guardadas para {account_email}")
    creds = _account_credentials(account_key)
    if creds is None:
        raise RuntimeError(f"Falta la contrasena SMTP para {account_email}")
    _, password = creds

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
    msg["From"] = account_email
    msg["To"] = to_email
    msg["Message-ID"] = make_msgid()
    if references:
        msg["In-Reply-To"] = references
        msg["References"] = references

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(account_email, password)
        server.send_message(msg)
