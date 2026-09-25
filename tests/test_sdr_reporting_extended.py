import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from sdr_reporting.extended import aggregate_week, new_meeting_alert, render_daily_close

CHILE = ZoneInfo("America/Santiago")


def _report(day=date(2026, 9, 24), calls=10, tasks=4):
    clients = {}
    for slug in ("bambutech", "gbs", "balia"):
        clients[slug] = {
            "tasks_done": tasks, "tasks_total": 10, "overdue_pending": 2,
            "calls": calls, "contacts": calls - 1, "answered": 3,
            "unanswered": calls - 3, "conversation_seconds": 120,
            "phone_seconds": 300, "meetings": 1,
            "email": {"received": 2, "responded": 1, "pending": 1, "new_manual": 3},
        }
    return {"day": day, "cut": datetime(2026, 9, 24, 20, tzinfo=CHILE), "clients": clients}


def test_daily_close_exposes_real_gap_without_inventing_target():
    text = render_daily_close(_report())
    assert "BRECHA DEL DÍA" in text
    assert "Pendientes de la meta GHL: 18" in text
    assert "BAMBU TECH" in text and "GBS" in text and "BALIA" in text


def test_week_aggregation_sums_snapshots_by_client():
    result = aggregate_week([_report(), _report(date(2026, 9, 25), calls=20, tasks=5)])
    assert result["days"] == 2
    assert result["clients"]["gbs"]["calls"] == 30
    assert result["clients"]["gbs"]["tasks_done"] == 9


def test_meeting_alert_omits_missing_fields_and_names_nora():
    text = new_meeting_alert("gbs", {
        "id": "a1", "title": "Reunión Ana", "startTime": "2026-09-25T15:00:00-03:00",
        "contactName": "Ana Pérez", "email": "ana@example.com",
    })
    assert "NUEVA REUNIÓN" in text
    assert "Ana Pérez" in text and "Nora" in text
    assert "Teléfono" not in text

