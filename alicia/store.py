"""Acceso a Supabase (REST) y helpers de idempotencia/estado para Alicia.

`SupabaseStore` es un cliente REST mínimo (httpx) con la misma semántica que el
usado por el sync. `AliciaState` encapsula las operaciones idempotentes: saber si
un mensaje ya se procesó, registrar hilos y dejar auditoría.

Todo el estado se puede inyectar como fake en los tests (interfaz .select/.upsert/
.insert), de modo que la lógica se prueba sin red.
"""
from __future__ import annotations

from typing import Any

import httpx


class SupabaseStore:
    def __init__(self, url: str, key: str):
        base = url.rstrip("/").removesuffix("/rest/v1")
        self.client = httpx.Client(
            base_url=f"{base}/rest/v1",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            timeout=60,
        )

    def select(self, table: str, columns: str, **params: str) -> list[dict[str, Any]]:
        query = {"select": columns, **params}
        resp = self.client.get(f"/{table}", params=query)
        resp.raise_for_status()
        return resp.json()

    def upsert(self, table: str, rows: list[dict[str, Any]], conflict: str) -> list[dict[str, Any]]:
        resp = self.client.post(
            f"/{table}",
            params={"on_conflict": conflict},
            headers={"Prefer": "resolution=merge-duplicates,return=representation"},
            json=rows,
        )
        resp.raise_for_status()
        return resp.json()

    def insert(self, table: str, row: dict[str, Any]) -> None:
        resp = self.client.post(f"/{table}", headers={"Prefer": "return=minimal"}, json=row)
        resp.raise_for_status()


class AliciaState:
    """Operaciones de estado. `store` puede ser SupabaseStore o un fake en tests."""

    def __init__(self, store: Any):
        self.store = store

    def already_processed(self, gmail_message_id: str) -> bool:
        try:
            rows = self.store.select(
                "alicia_processed_messages",
                "gmail_message_id",
                gmail_message_id=f"eq.{gmail_message_id}",
                limit="1",
            )
        except Exception:
            return False
        return bool(rows)

    def mark_processed(
        self, gmail_message_id: str, thread_id: str, account_id: str, classification: str
    ) -> None:
        self.store.upsert(
            "alicia_processed_messages",
            [
                {
                    "gmail_message_id": gmail_message_id,
                    "thread_id": thread_id,
                    "account_id": account_id,
                    "classification": classification,
                }
            ],
            "gmail_message_id",
        )

    def upsert_thread(self, row: dict[str, Any]) -> None:
        self.store.upsert("alicia_email_threads", [row], "thread_id")

    def log_action(
        self, thread_id: str, action: str, status: str, detail: dict[str, Any], dry_run: bool
    ) -> None:
        self.store.insert(
            "alicia_actions_log",
            {
                "thread_id": thread_id,
                "action": action,
                "status": status,
                "detail": detail,
                "dry_run": dry_run,
            },
        )

    def record_run(self, row: dict[str, Any]) -> None:
        self.store.insert("alicia_runs", row)

    def link_telegram(self, row: dict[str, Any]) -> None:
        self.store.insert("alicia_telegram_links", row)
