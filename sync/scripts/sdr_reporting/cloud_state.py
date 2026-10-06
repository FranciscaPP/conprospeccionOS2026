from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol


class CloudStateClient(Protocol):
    def rpc(self, function: str, payload: dict[str, Any]) -> list[dict[str, Any]]: ...

    def update(self, table: str, values: dict[str, Any], **params: str) -> list[dict[str, Any]]: ...


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _error_summary(error: BaseException | str) -> str:
    if isinstance(error, BaseException):
        summary = f"{type(error).__name__}: {error}"
    else:
        summary = str(error)
    return " ".join(summary.split())[:500]


class CloudStateStore:
    """Atomic delivery/query state backed by service-role-only Supabase RPCs."""

    def __init__(self, client: CloudStateClient):
        self.client = client

    def claim_delivery(self, delivery_key: str) -> dict[str, Any] | None:
        rows = self.client.rpc("claim_sdr_report_delivery", {"p_delivery_key": delivery_key})
        return rows[0] if rows else None

    def mark_delivery_part(self, delivery_key: str, part: int) -> None:
        if part not in (1, 2):
            raise ValueError("part must be 1 or 2")
        self.client.update(
            "sdr_report_deliveries",
            {f"part{part}_sent_at": _utc_now(), "updated_at": _utc_now()},
            delivery_key=f"eq.{delivery_key}",
        )

    def mark_delivery_sent(self, delivery_key: str) -> None:
        now = _utc_now()
        self.client.update(
            "sdr_report_deliveries",
            {"status": "sent", "sent_at": now, "updated_at": now, "error_summary": None},
            delivery_key=f"eq.{delivery_key}",
        )

    def mark_delivery_failed(self, delivery_key: str, error: BaseException | str) -> None:
        self.client.update(
            "sdr_report_deliveries",
            {"status": "failed", "updated_at": _utc_now(), "error_summary": _error_summary(error)},
            delivery_key=f"eq.{delivery_key}",
        )

    def claim_query(self, update_id: int) -> dict[str, Any] | None:
        rows = self.client.rpc("claim_sdr_bot_query", {"p_update_id": int(update_id)})
        return rows[0] if rows else None

    def mark_query_answered(self, update_id: int) -> None:
        now = _utc_now()
        self.client.update(
            "sdr_bot_queries",
            {"status": "answered", "answered_at": now, "updated_at": now, "error_summary": None},
            update_id=f"eq.{int(update_id)}",
        )

    def mark_query_failed(self, update_id: int, error: BaseException | str) -> None:
        self.client.update(
            "sdr_bot_queries",
            {"status": "failed", "updated_at": _utc_now(), "error_summary": _error_summary(error)},
            update_id=f"eq.{int(update_id)}",
        )
