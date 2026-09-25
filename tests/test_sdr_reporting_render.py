import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from sdr_reporting.render import render_hourly


def sample_report():
    base = {"tasks_done": 2, "tasks_total": 4, "overdue_pending": 1,
            "calls": 3, "contacts": 2, "answered": 1, "unanswered": 2,
            "conversation_seconds": 65, "phone_seconds": 100,
            "meetings": 0, "task_types": {"Nuevos": (1, 2)}, "gaps": []}
    return {
        "day": date(2026, 9, 24),
        "cut": datetime(2026, 9, 24, 15, 0, tzinfo=ZoneInfo("America/Santiago")),
        "sdr": "Nora",
        "clients": {"bambutech": dict(base), "gbs": dict(base), "balia": dict(base)},
        "comparison": None,
        "email_available": False,
        "baseline_available": True,
        "alerts": ["GBS · Coordinando reunión va atrasado."],
    }


def test_hourly_report_has_three_html_messages_and_all_clients():
    messages = render_hourly(sample_report())
    assert len(messages) == 3
    assert all(len(message) <= 4096 for message in messages)
    joined = "\n".join(messages)
    assert "REPORTE OPERATIVO · 15:00" in joined
    assert "BAMBU TECH" in joined and "GBS" in joined and "BALIA" in joined
    assert "Nora" in joined and "Norma" not in joined
    assert all(f"{number:02d} ·" in joined for number in range(1, 11))


def test_report_does_not_invent_email_or_comparison():
    joined = "\n".join(render_hourly(sample_report()))
    assert "Sin fuente manual confiable" in joined
    assert "Sin snapshot comparable" in joined

