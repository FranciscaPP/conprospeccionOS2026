import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from sdr_reporting.followups import followup_age_summary


CHILE = ZoneInfo("America/Santiago")


class FakeGHL:
    def list_custom_fields(self, _location_id):
        return {"customFields": [{"id": "status", "name": "STATUS PROSPECTO"}]}

    def search_contacts_page(self, _location_id, search_after=None, page_limit=100):
        assert page_limit == 100
        if search_after:
            return {"contacts": []}
        return {"contacts": [
            {"id": "recent", "assignedTo": "nora", "lastActivity": "2026-11-08T12:00:00Z", "customFields": [{"id": "status", "value": "Información adicional"}], "searchAfter": "1"},
            {"id": "week", "assignedTo": "nora", "lastActivity": "2026-11-02T12:00:00Z", "customFields": [{"id": "status", "value": "Información adicional"}], "searchAfter": "2"},
            {"id": "old", "assignedTo": "nora", "lastActivity": "2026-10-20T12:00:00Z", "customFields": [{"id": "status", "value": "Coordinando reunión"}], "searchAfter": "3"},
            {"id": "other", "assignedTo": "other", "lastActivity": "2026-10-01T12:00:00Z", "customFields": [{"id": "status", "value": "Información adicional"}], "searchAfter": "4"},
        ]}


def test_followup_thresholds_are_cumulative_and_user_scoped():
    result = followup_age_summary(
        FakeGHL(), "loc", datetime(2026, 11, 9, 13, tzinfo=CHILE),
        unit_for_contact=lambda contact: "client" if contact.get("assignedTo") == "nora" else None,
    )

    assert result["client"]["informacion adicional"] == {
        "total": 2, "up_to_3": 1, "over_3": 1, "over_6": 1, "over_14": 0, "no_date": 0,
    }
    assert result["client"]["coordinando reunion"] == {
        "total": 1, "up_to_3": 0, "over_3": 1, "over_6": 1, "over_14": 1, "no_date": 0,
    }
