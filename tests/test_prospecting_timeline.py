import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dashboard"))

from client_meeting_portal import _build_html
from shared.prospecting_timeline import (
    business_days,
    calendar_days,
    proportional_valid_range,
    prospecting_timeline_for_client,
)


def test_bambutech_timeline_days_and_summary():
    timeline = prospecting_timeline_for_client("bambutech")

    assert [segment["calendarDays"] for segment in timeline["segments"]] == [29, 21, 17]
    assert [segment["businessDays"] for segment in timeline["segments"]] == [21, 15, 13]
    assert timeline["summary"]["activeCalendarDays"] == 46
    assert timeline["summary"]["pauseCalendarDays"] == 21
    assert timeline["summary"]["meetings"] == 10
    assert timeline["summary"]["validMeetings"] == 6


def test_calendar_and_business_days_are_inclusive():
    assert calendar_days("2026-07-07", "2026-07-23") == 17
    assert business_days("2026-07-07", "2026-07-23") == 13


def test_proportional_reference_range():
    assert proportional_valid_range(
        active_days=17,
        standard_period_days=30,
        monthly_min=10,
        monthly_max=12,
    ) == {"min": 6, "max": 7}


def test_portal_injects_timeline_only_for_bambutech():
    bambu_html = _build_html(
        client_slug="bambutech",
        meetings=[],
        title="Validacion de reuniones",
        brand="BambuTech Services",
        user_label="Usuario BambuTech",
        user_subtitle="Validacion contractual",
    )
    gbs_html = _build_html(
        client_slug="gbs",
        meetings=[],
        title="Validacion de reuniones",
        brand="GBS",
        user_label="Usuario GBS",
        user_subtitle="Validacion contractual",
    )

    assert "OPERATIONAL_TIMELINE = {" in bambu_html
    assert "Contexto operativo de la prospecci\\u00f3n" in bambu_html
    assert "OPERATIONAL_TIMELINE = null" in gbs_html
