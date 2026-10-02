import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

import sdr_reporting.cli as cli


class PhotoOnlySender:
    def __init__(self):
        self.photos = []

    def send_photo(self, path, caption):
        self.photos.append((Path(path), caption))


def test_hourly_delivery_sends_exactly_two_images_with_short_captions(tmp_path, monkeypatch):
    paths = [tmp_path / "report_1.png", tmp_path / "report_2.png"]
    for path in paths:
        path.write_bytes(b"png")
    monkeypatch.setattr(cli, "render_tabular_report", lambda report, directory: paths)
    sender = PhotoOnlySender()
    report = {
        "day": date(2026, 10, 2),
        "cut": datetime(2026, 10, 2, 15, tzinfo=ZoneInfo("America/Santiago")),
        "sdr": "Nora",
    }

    result = cli.deliver_hourly_report(report, sender, tmp_path, send=True)

    assert result == paths
    assert sender.photos == [
        (paths[0], "Reporte Nora · 1 de 2"),
        (paths[1], "Reporte Nora · 2 de 2"),
    ]


def test_hourly_dry_run_renders_without_sending(tmp_path, monkeypatch):
    paths = [tmp_path / "report_1.png", tmp_path / "report_2.png"]
    monkeypatch.setattr(cli, "render_tabular_report", lambda report, directory: paths)
    sender = PhotoOnlySender()

    result = cli.deliver_hourly_report({}, sender, tmp_path, send=False)

    assert result == paths
    assert sender.photos == []
