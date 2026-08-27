"""Salida a Telegram (envío de mensajes). El webhook entrante NO llama a IA.

Enviar un mensaje a Telegram no consume créditos de IA. Este módulo solo publica
alertas/confirmaciones. El manejo de instrucciones entrantes (webhook) se decide
por código; solo delega en `alicia.ai` cuando el usuario lo pide explícitamente.
"""
from __future__ import annotations

import httpx

_API = "https://api.telegram.org"


class TelegramClient:
    def __init__(self, token: str, chat_id: str, http: httpx.Client | None = None):
        self.token = token
        self.chat_id = chat_id
        self._http = http or httpx.Client(timeout=15)

    def send_message(self, text: str) -> dict:
        if not self.token or not self.chat_id:
            return {"ok": False, "skipped": "missing token/chat_id"}
        resp = self._http.post(
            f"{_API}/bot{self.token}/sendMessage",
            json={"chat_id": self.chat_id, "text": text, "disable_web_page_preview": True},
        )
        resp.raise_for_status()
        return resp.json()

    def send_all(self, messages: list[str]) -> list[dict]:
        return [self.send_message(m) for m in messages]
