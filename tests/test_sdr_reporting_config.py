import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from sdr_reporting.config import CLIENTS, client_at, work_blocks_for


def test_three_clients_and_official_colors():
    assert CLIENTS["bambutech"].color == "#22C55E"
    assert CLIENTS["gbs"].color == "#8B5CF6"
    assert CLIENTS["balia"].color == "#EC4899"
    assert [c.short for c in CLIENTS.values()] == ["BAM", "GBS", "BAL"]


def test_official_chile_schedule_excludes_lunch():
    blocks = work_blocks_for(date(2026, 9, 24))
    assert [(b.start.hour, b.end.hour, b.client) for b in blocks] == [
        (11, 12, "balia"),
        (12, 13, "gbs"),
        (13, 16, "bambutech"),
        (17, 18, "gbs"),
        (18, 20, "bambutech"),
    ]
    lunch = datetime(2026, 9, 24, 16, 30, tzinfo=ZoneInfo("America/Santiago"))
    assert client_at(lunch) is None


def test_weekends_have_no_work_blocks():
    assert work_blocks_for(date(2026, 9, 26)) == []

