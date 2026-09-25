from __future__ import annotations

from typing import Any

import httpx


class TelegramClient:
    def __init__(self, token: str):
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.client = httpx.Client(timeout=30)

    def send_message(self, chat_id: int | str, text: str, reply_markup: dict[str, Any] | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        if reply_markup:
            body["reply_markup"] = reply_markup
        response = self.client.post(f"{self.base_url}/sendMessage", json=body)
        if response.status_code == 400 and "can't parse" in response.text.lower():
            # Telegram rechazo el Markdown por caracteres especiales sin escapar
            # (nombre de prospecto/empresa, etc.). Reintentar una vez como texto
            # plano para no perder la notificacion.
            body.pop("parse_mode", None)
            response = self.client.post(f"{self.base_url}/sendMessage", json=body)
        response.raise_for_status()
        return response.json()["result"]

    def answer_callback_query(self, callback_query_id: str, text: str = "") -> None:
        response = self.client.post(
            f"{self.base_url}/answerCallbackQuery",
            json={"callback_query_id": callback_query_id, "text": text},
        )
        response.raise_for_status()

    def get_updates(self, offset: int | None = None, timeout: int = 30) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        response = self.client.get(f"{self.base_url}/getUpdates", params=params, timeout=timeout + 10)
        response.raise_for_status()
        return response.json().get("result", [])
