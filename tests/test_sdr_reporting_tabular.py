import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from sdr_reporting.tabular import _duration, build_table_document, render_tabular_report


CHILE = ZoneInfo("America/Santiago")


def sample_report():
    def client(overdue, today, completed, calls, answered, email, whatsapp=None, outside=None):
        return {
            "tasks_overdue": overdue,
            "tasks_today": today,
            "tasks_completed": completed,
            "tasks_pending": overdue + today - completed,
            "calls": calls,
            "answered": answered,
            "unanswered": calls - answered,
            "answered_seconds": answered * 60,
            "unanswered_phone_seconds": (calls - answered) * 10,
            "phone_seconds": answered * 60 + (calls - answered) * 10,
            "email": email,
            "whatsapp": whatsapp,
            "meetings": [],
            "outside_hours": outside or {
                "before": {"count": 0, "phone_seconds": 0},
                "lunch": {"count": 0, "phone_seconds": 0},
                "after": {"count": 0, "phone_seconds": 0},
                "total": {"count": 0, "phone_seconds": 0},
            },
        }

    communication = {
        "pending_previous": 2,
        "today": 8,
        "total": 10,
        "responded": 6,
        "unanswered": 4,
    }
    bambu_outside = {
        "before": {"count": 1, "phone_seconds": 30},
        "lunch": {"count": 2, "phone_seconds": 50},
        "after": {"count": 1, "phone_seconds": 40},
        "total": {"count": 4, "phone_seconds": 120},
    }
    return {
        "day": date(2026, 10, 2),
        "cut": datetime(2026, 10, 2, 15, 0, tzinfo=CHILE),
        "sdr": "Nora",
        "clients": {
            "bambutech": client(1, 4, 3, 12, 8, dict(communication), dict(communication), bambu_outside),
            "gbs": client(1, 4, 3, 12, 8, dict(communication)),
            "balia": client(1, 4, 3, 12, 8, dict(communication)),
        },
        "conprospeccion": {
            **client(2, 3, 1, 7, 2, dict(communication)),
            "meetings": [],
            "meetings_scheduled": [],
        },
        "work_time": {
            "elapsed_seconds": 4 * 3600,
            "worked_seconds": 2 * 3600,
            "unregistered_seconds": 2 * 3600,
        },
        "block_adherence": [
            {
                "client": "bambutech",
                "start": "13:00",
                "end": "15:00",
                "correct_calls": 8,
                "other_calls": 2,
            }
        ],
    }


def test_table_document_recalculates_totals_and_marks_partial_channels():
    document = build_table_document(sample_report())

    assert document["tasks"]["total"] == {
        "overdue": 5,
        "today": 15,
        "total": 20,
        "completed": 10,
        "pending": 10,
        "percent": 50,
    }
    assert document["calls_count"]["total"]["today"] == 43
    assert document["email"]["total"]["total"] == 40
    assert document["email"]["total"]["partial"] is False
    assert document["whatsapp"]["gbs"] is None
    assert document["whatsapp"]["balia"] is None
    assert document["whatsapp"]["conprospeccion"] is None
    assert document["whatsapp"]["total"]["partial"] is True
    assert document["outside"]["total"]["lunch"]["count"] == 2


def test_prospecting_is_present_in_all_primary_tables_even_when_empty():
    report = sample_report()
    report["conprospeccion"] = {
        "tasks_overdue": 0,
        "tasks_today": 0,
        "tasks_completed": 0,
        "calls": 0,
        "answered": 0,
        "unanswered": 0,
        "phone_seconds": 0,
        "answered_seconds": 0,
        "unanswered_phone_seconds": 0,
        "meetings": [],
        "meetings_scheduled": [],
        "email": None,
        "whatsapp": None,
        "outside_hours": {},
    }

    document = build_table_document(report)

    assert document["tasks"]["conprospeccion"]["total"] == 0
    assert any(row["client"] == "conprospeccion" for row in document["meetings"])
    assert document["scheduled"]["conprospeccion"]["count"] == 0
    assert document["calls_count"]["conprospeccion"]["today"] == 0
    assert "conprospeccion" in document["email"]
    assert "conprospeccion" in document["outside"]


def test_render_tabular_report_creates_two_fixed_width_pngs(tmp_path):
    paths = render_tabular_report(sample_report(), tmp_path)

    assert len(paths) == 2
    assert paths[0].name.endswith("_1.png")
    assert paths[1].name.endswith("_2.png")
    for path in paths:
        assert path.exists() and path.stat().st_size > 0
        with Image.open(path) as image:
            assert image.format == "PNG"
            assert image.width == 1200


def test_duration_keeps_seconds_so_rows_and_totals_can_be_reconciled():
    assert _duration(839) == "13m 59s"
    assert _duration(5664) == "1h 34m 24s"
