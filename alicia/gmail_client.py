"""Cliente Gmail sobre REST (httpx). Auth por refresh token OAuth por cuenta.

Solo lo necesario para el flujo determinístico:
  - listar mensajes nuevos (query acotada: no leídos + ventana temporal),
  - leer metadatos (cabeceras) y snippet,
  - responder DENTRO del mismo hilo (mismo threadId, In-Reply-To/References),
  - marcar como leído.

No añade dependencias nuevas: usa httpx (ya en sync/requirements) y stdlib.
La auth por refresh token funciona con cualquier Gmail. Para Google Workspace se
puede sustituir el `AccessTokenProvider` por uno de service account con
delegación domain-wide sin tocar el resto del cliente (punto de extensión).
"""
from __future__ import annotations

import base64
from email.message import EmailMessage
from email.utils import formataddr
from typing import Any

import httpx

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_API = "https://gmail.googleapis.com/gmail/v1"


class GmailAuthError(RuntimeError):
    pass


class AccessTokenProvider:
    """Cambia refresh_token → access_token y lo cachea hasta poco antes de expirar."""

    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._token: str | None = None

    def token(self, http: httpx.Client) -> str:
        if self._token:
            return self._token
        if not (self._client_id and self._client_secret and self._refresh_token):
            raise GmailAuthError("Faltan credenciales OAuth de Gmail para esta cuenta.")
        resp = http.post(
            _TOKEN_URL,
            data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()
        token = resp.json().get("access_token")
        if not token:
            raise GmailAuthError("Google no devolvió access_token.")
        self._token = token
        return token


class GmailClient:
    def __init__(self, email: str, auth: AccessTokenProvider, http: httpx.Client | None = None):
        self.email = email
        self._auth = auth
        self._http = http or httpx.Client(timeout=60)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._auth.token(self._http)}"}

    def list_new_message_ids(self, lookback_hours: int, extra_query: str = "") -> list[str]:
        """IDs de mensajes recibidos, no leídos, en la ventana temporal indicada."""
        query = f"in:inbox is:unread newer_than:{max(1, lookback_hours)}h"
        if extra_query:
            query = f"{query} {extra_query}"
        ids: list[str] = []
        page_token: str | None = None
        while True:
            params: dict[str, Any] = {"q": query, "maxResults": 100}
            if page_token:
                params["pageToken"] = page_token
            resp = self._http.get(
                f"{_API}/users/me/messages", headers=self._headers(), params=params
            )
            resp.raise_for_status()
            data = resp.json()
            ids.extend(m["id"] for m in data.get("messages", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return ids

    def get_metadata(self, message_id: str) -> dict[str, Any]:
        """Cabeceras + snippet + labels, sin descargar el cuerpo completo."""
        resp = self._http.get(
            f"{_API}/users/me/messages/{message_id}",
            headers=self._headers(),
            params={
                "format": "metadata",
                "metadataHeaders": [
                    "From", "To", "Subject", "Date", "Message-ID",
                    "In-Reply-To", "References", "Return-Path",
                    "Auto-Submitted", "Precedence", "Content-Type",
                    "X-Autoreply", "X-Autorespond", "X-Auto-Response-Suppress",
                ],
            },
        )
        resp.raise_for_status()
        return resp.json()

    def mark_read(self, message_id: str) -> None:
        resp = self._http.post(
            f"{_API}/users/me/messages/{message_id}/modify",
            headers={**self._headers(), "Content-Type": "application/json"},
            json={"removeLabelIds": ["UNREAD"]},
        )
        resp.raise_for_status()

    def send_reply(
        self,
        thread_id: str,
        to_addr: str,
        subject: str,
        body: str,
        in_reply_to: str = "",
        references: str = "",
        from_name: str = "",
    ) -> dict[str, Any]:
        """Envía una respuesta DENTRO del hilo original desde esta cuenta."""
        raw = build_reply_mime(
            from_addr=self.email,
            to_addr=to_addr,
            subject=subject,
            body=body,
            in_reply_to=in_reply_to,
            references=references,
            from_name=from_name,
        )
        resp = self._http.post(
            f"{_API}/users/me/messages/send",
            headers={**self._headers(), "Content-Type": "application/json"},
            json={"raw": raw, "threadId": thread_id},
        )
        resp.raise_for_status()
        return resp.json()


def reply_subject(original: str) -> str:
    subject = (original or "").strip()
    if subject.lower().startswith("re:"):
        return subject
    return f"Re: {subject}" if subject else "Re:"


def build_reply_mime(
    from_addr: str,
    to_addr: str,
    subject: str,
    body: str,
    in_reply_to: str = "",
    references: str = "",
    from_name: str = "",
) -> str:
    """Construye el MIME (base64url) de una respuesta encadenada al hilo.

    Determinístico y testeable sin red: conserva In-Reply-To/References para que
    el correo caiga en el mismo hilo y respeta el asunto (Re:).
    """
    msg = EmailMessage()
    msg["From"] = formataddr((from_name, from_addr)) if from_name else from_addr
    msg["To"] = to_addr
    msg["Subject"] = reply_subject(subject)
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = (f"{references} {in_reply_to}".strip()) if references else in_reply_to
    msg.set_content(body)
    return base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
