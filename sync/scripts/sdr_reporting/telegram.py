from __future__ import annotations

from typing import Any

import httpx


EXPECTED_USERNAME = "equipo_alicia_bot"


class EquipoAliciaTelegram:
    """Cliente de salida limitado al bot y chat operativos autorizados."""

    def __init__(
        self,
        token: str,
        chat_id: str,
        *,
        transport: Any | None = None,
    ) -> None:
        if not token:
            raise RuntimeError("Falta TELEGRAM_SDR_TOKEN")
        if not chat_id:
            raise RuntimeError("Falta TELEGRAM_SDR_CHAT_ID")
        self.token = token
        self.chat_id = str(chat_id)
        self.transport = transport or httpx.Client(timeout=30)
        self.base_url = f"https://api.telegram.org/bot{token}"
        self._verified = False

    def verify_identity(self) -> dict[str, Any]:
        response = self.transport.get(f"{self.base_url}/getMe")
        response.raise_for_status()
        result = response.json().get("result") or {}
        if result.get("username") != EXPECTED_USERNAME or result.get("is_bot") is not True:
            raise RuntimeError(
                f"El token no corresponde a @{EXPECTED_USERNAME}; envío cancelado"
            )
        self._verified = True
        return result

    def send_message(self, text: str) -> dict[str, Any]:
        if not self._verified:
            self.verify_identity()
        response = self.transport.post(
            f"{self.base_url}/sendMessage",
            json={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )
        response.raise_for_status()
        return response.json().get("result") or {}

