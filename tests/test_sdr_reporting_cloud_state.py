import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sync" / "scripts"))

from sdr_reporting.cloud_state import CloudStateStore


class FakeSupabase:
    def __init__(self):
        self.rpc_results = {}
        self.rpc_calls = []
        self.update_calls = []

    def rpc(self, function, payload):
        self.rpc_calls.append((function, payload))
        result = self.rpc_results.get((function, tuple(sorted(payload.items()))), [])
        return [dict(row) for row in result]

    def update(self, table, values, **params):
        self.update_calls.append((table, values, params))
        return [{**values}]


def _program(fake, function, payload, rows):
    fake.rpc_results[(function, tuple(sorted(payload.items())))] = rows


def test_claim_delivery_returns_persisted_parts_and_duplicate_returns_none():
    fake = FakeSupabase()
    store = CloudStateStore(fake)
    key = "hourly:2026-10-05:10:America/Santiago"
    claimed = {
        "delivery_key": key,
        "status": "processing",
        "attempt_count": 1,
        "part1_sent_at": None,
        "part2_sent_at": None,
    }
    _program(fake, "claim_sdr_report_delivery", {"p_delivery_key": key}, [claimed])

    assert store.claim_delivery(key) == claimed

    _program(fake, "claim_sdr_report_delivery", {"p_delivery_key": key}, [])
    assert store.claim_delivery(key) is None


def test_delivery_part_sent_and_failure_updates_are_scoped_to_key():
    fake = FakeSupabase()
    store = CloudStateStore(fake)
    key = "hourly:2026-10-05:10:America/Santiago"

    store.mark_delivery_part(key, 1)
    store.mark_delivery_part(key, 2)
    store.mark_delivery_sent(key)
    store.mark_delivery_failed(key, RuntimeError("token abcdef was rejected"))

    assert fake.update_calls[0][0] == "sdr_report_deliveries"
    assert fake.update_calls[0][2] == {"delivery_key": f"eq.{key}"}
    assert "part1_sent_at" in fake.update_calls[0][1]
    assert "part2_sent_at" in fake.update_calls[1][1]
    assert fake.update_calls[2][1]["status"] == "sent"
    assert fake.update_calls[3][1]["status"] == "failed"
    assert fake.update_calls[3][1]["error_summary"] == "RuntimeError: token abcdef was rejected"


def test_claim_query_returns_text_and_answer_is_idempotently_scoped():
    fake = FakeSupabase()
    store = CloudStateStore(fake)
    row = {
        "update_id": 12345,
        "chat_id": 777,
        "text": "tareas de Balia",
        "status": "processing",
        "attempt_count": 1,
    }
    _program(fake, "claim_sdr_bot_query", {"p_update_id": 12345}, [row])

    assert store.claim_query(12345)["text"] == "tareas de Balia"
    store.mark_query_answered(12345)

    assert fake.update_calls[-1][0] == "sdr_bot_queries"
    assert fake.update_calls[-1][1]["status"] == "answered"
    assert fake.update_calls[-1][2] == {"update_id": "eq.12345"}


def test_sent_delivery_and_answered_query_cannot_be_reclaimed():
    fake = FakeSupabase()
    store = CloudStateStore(fake)
    key = "hourly:2026-10-05:10:America/Santiago"
    _program(fake, "claim_sdr_report_delivery", {"p_delivery_key": key}, [])
    _program(fake, "claim_sdr_bot_query", {"p_update_id": 12345}, [])

    assert store.claim_delivery(key) is None
    assert store.claim_query(12345) is None


def test_migration_enforces_service_role_only_and_atomic_claims():
    sql = (ROOT / "sync" / "supabase" / "migrations" / "029_equipo_alicia_cloud.sql").read_text(
        encoding="utf-8"
    ).lower()

    assert "create table if not exists public.sdr_report_deliveries" in sql
    assert "create table if not exists public.sdr_bot_queries" in sql
    assert "enable row level security" in sql
    assert "revoke all" in sql
    assert "from anon" in sql
    assert "from authenticated" in sql
    assert "grant" in sql and "to service_role" in sql
    assert "claim_sdr_report_delivery" in sql
    assert "claim_sdr_bot_query" in sql
    assert "interval '30 minutes'" in sql
    assert "attempt_count < 2" in sql
