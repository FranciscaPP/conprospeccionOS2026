import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

import sdr_reporting.cli as cli


class PhotoOnlySender:
    def __init__(self):
        self.photos = []

    def send_photo(self, path, caption):
        self.photos.append((Path(path), caption))


class FakeCloudState:
    def __init__(self, claim):
        self.claim = claim
        self.parts = []
        self.sent = []
        self.failed = []

    def claim_delivery(self, key):
        return self.claim

    def mark_delivery_part(self, key, part):
        self.parts.append((key, part))

    def mark_delivery_sent(self, key):
        self.sent.append(key)

    def mark_delivery_failed(self, key, error):
        self.failed.append((key, error))


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


def test_cloud_delivery_sends_both_images_and_records_each_part(tmp_path, monkeypatch):
    paths = [tmp_path / "report_1.png", tmp_path / "report_2.png"]
    for path in paths:
        path.write_bytes(b"png")
    monkeypatch.setattr(cli, "render_tabular_report", lambda report, directory: paths)
    state = FakeCloudState({"part1_sent_at": None, "part2_sent_at": None})
    sender = PhotoOnlySender()

    result = cli.deliver_cloud_report({}, sender, tmp_path, state, "hourly:test")

    assert result == paths
    assert [caption for _, caption in sender.photos] == ["Reporte Nora · 1 de 2", "Reporte Nora · 2 de 2"]
    assert state.parts == [("hourly:test", 1), ("hourly:test", 2)]
    assert state.sent == ["hourly:test"]


def test_cloud_delivery_skips_an_already_claimed_or_sent_key(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "render_tabular_report", lambda report, directory: pytest.fail("must not render"))
    state = FakeCloudState(None)

    result = cli.deliver_cloud_report({}, PhotoOnlySender(), tmp_path, state, "hourly:test")

    assert result == []


def test_cloud_retry_sends_only_the_missing_second_image(tmp_path, monkeypatch):
    paths = [tmp_path / "report_1.png", tmp_path / "report_2.png"]
    for path in paths:
        path.write_bytes(b"png")
    monkeypatch.setattr(cli, "render_tabular_report", lambda report, directory: paths)
    state = FakeCloudState({"part1_sent_at": "2026-10-05T13:00:00Z", "part2_sent_at": None})
    sender = PhotoOnlySender()

    cli.deliver_cloud_report({}, sender, tmp_path, state, "hourly:test")

    assert sender.photos == [(paths[1], "Reporte Nora · 2 de 2")]
    assert state.parts == [("hourly:test", 2)]
    assert state.sent == ["hourly:test"]
