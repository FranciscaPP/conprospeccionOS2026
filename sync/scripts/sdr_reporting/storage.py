from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any


def _jsonable(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(item) for item in value]
    return value


class SnapshotStore:
    def __init__(self, supabase) -> None:
        self.supabase = supabase

    def save_report(self, report: dict) -> None:
        cut = report["cut"].replace(minute=0, second=0, microsecond=0)
        rows = []
        for scope, payload in [("total", report), *report.get("clients", {}).items()]:
            rows.append({
                "snapshot_date": report["day"].isoformat(),
                "cut_at": cut.strftime("%H:%M:%S"),
                "scope": scope,
                "schema_version": 1,
                "payload": _jsonable(payload),
            })
        self.supabase.upsert(
            "sdr_hourly_snapshots", rows, conflict="snapshot_date,cut_at,scope"
        )

    def load_yesterday_same_hour(self, day: date, cut: datetime) -> dict | None:
        rows = self.supabase.select(
            "sdr_hourly_snapshots",
            "payload",
            snapshot_date=f"eq.{(day - timedelta(days=1)).isoformat()}",
            cut_at=f"eq.{cut.replace(minute=0, second=0, microsecond=0).strftime('%H:%M:%S')}",
            scope="eq.total",
            limit="1",
        )
        return rows[0]["payload"] if rows else None

