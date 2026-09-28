import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from sdr_reporting.render import render_hourly


def sample_report():
    base = {
        "tasks_done": 2, "tasks_total": 4, "pending_today": 2,
        "overdue_pending": 1, "tasks_done_last_hour": 1,
        "calls": 38, "contacts": 34, "answered": 25, "unanswered": 13,
        "repeated_contacts": 4,
        "answered_seconds": 420, "unanswered_phone_seconds": 240,
        "phone_seconds": 660, "meetings": [],
        "email": {"received": 2, "responded": 0, "pending": 2},
        "work_time": {"worked_seconds": 660, "unregistered_seconds": 2940},
    }
    balia = dict(base)
    balia["email"] = None
    return {
        "day": date(2026, 9, 24),
        "cut": datetime(2026, 9, 24, 15, 0, tzinfo=ZoneInfo("America/Santiago")),
        "sdr": "Nora",
        "clients": {"bambutech": dict(base), "gbs": dict(base), "balia": balia},
        "work_time": {"elapsed_seconds": 10800, "worked_seconds": 1320,
                      "unregistered_seconds": 9480, "email_seconds": 0},
        "alerts": [],
        "block_adherence": [],
    }


def test_hourly_report_is_vertical_stable_and_has_all_clients():
    messages = render_hourly(sample_report())
    assert len(messages) == 3
    assert all(len(message) <= 4096 for message in messages)
    joined = "\n".join(messages)
    assert "REPORTE OPERATIVO · 15:00" in joined
    assert "BAMBU TECH" in joined and "GBS" in joined and "BALIA" in joined
    assert "Nora" in joined and "Norma" not in joined
    assert "<pre>" not in joined
    assert "ARRASTRE VENCIDO" not in joined
    assert "VS AYER" not in joined


def test_calls_emails_and_work_time_use_explicit_labels():
    joined = "\n".join(render_hourly(sample_report()))
    assert "Llamadas: 38" in joined
    assert "Remarcaciones: 4" in joined
    assert "Contestadas (&gt;20 s): 25" in joined
    assert "Sin contestar (≤20 s): 13" in joined
    assert "Total teléfono: 11 min" in joined
    assert "Correos: 2 recibidos · 0 respondidos · 2 pendientes" in joined
    assert "Correo: N/D" in joined
    assert "TOTAL TRABAJADO" in joined
    assert "SIN TRABAJAR" in joined


def test_task_card_separates_today_from_previous_day():
    joined = "\n".join(render_hourly(sample_report()))
    assert "Hoy: 2/4 · 50%" in joined
    assert "Pendientes de hoy: 2" in joined
    assert "Atrasadas de ayer: 1" in joined
    assert "+1 última hora" in joined

