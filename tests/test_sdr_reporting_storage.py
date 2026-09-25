import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from sdr_reporting.storage import SnapshotStore


class FakeSupabase:
    def __init__(self):
        self.calls = []

    def upsert(self, table, rows, conflict):
        self.calls.append((table, rows, conflict))
        return rows

    def select(self, table, columns, **params):
        return []


def test_snapshot_uses_idempotent_day_cut_scope_key():
    fake = FakeSupabase()
    store = SnapshotStore(fake)
    store.save_report({
        "day": date(2026, 9, 24),
        "cut": datetime(2026, 9, 24, 15, 8, tzinfo=ZoneInfo("America/Santiago")),
        "clients": {},
    })
    table, rows, conflict = fake.calls[0]
    assert table == "sdr_hourly_snapshots"
    assert conflict == "snapshot_date,cut_at,scope"
    assert rows[0]["cut_at"] == "15:00:00"

