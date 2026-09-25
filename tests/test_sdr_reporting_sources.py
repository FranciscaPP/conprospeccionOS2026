import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from sdr_reporting.sources import summarize_email_messages

CHILE = ZoneInfo("America/Santiago")


def msg(hour, direction, source=None, conversation="c1"):
    return {
        "conversation_id": conversation,
        "message_type": "TYPE_EMAIL",
        "direction": direction,
        "source": source,
        "occurred_at": datetime(2026, 9, 24, hour, 0, tzinfo=CHILE),
    }


def test_email_summary_excludes_automatic_and_tracks_manual_replies():
    messages = [
        msg(9, "outbound", "workflow", "auto"),
        msg(10, "inbound", conversation="answered"),
        msg(11, "outbound", "app", "answered"),
        msg(12, "inbound", conversation="pending"),
        msg(13, "outbound", "bulk_actions", "new"),
    ]
    result = summarize_email_messages(messages)
    assert result == {"received": 2, "responded": 1, "pending": 1, "new_manual": 1, "manual_sent": 2}


def test_outbound_before_inbound_is_not_a_managed_reply():
    result = summarize_email_messages([
        msg(9, "outbound", "app", "same"),
        msg(10, "inbound", conversation="same"),
    ])
    assert result["responded"] == 0
    assert result["pending"] == 1
    assert result["new_manual"] == 1

