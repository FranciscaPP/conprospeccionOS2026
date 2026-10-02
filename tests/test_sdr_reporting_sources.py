import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from sdr_reporting.sources import (
    summarize_conversation_work,
    summarize_email_messages,
    summarize_whatsapp_messages,
)

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


def test_whatsapp_separates_manual_templates_automatic_and_replies():
    messages = [
        {**msg(9, "outbound", "workflow", "auto"), "message_type": "TYPE_WHATSAPP"},
        {**msg(10, "outbound", "app", "new"), "message_type": "TYPE_WHATSAPP"},
        {**msg(11, "inbound", conversation="answered"), "message_type": "TYPE_WHATSAPP"},
        {**msg(12, "outbound", "bulk_actions", "answered"), "message_type": "TYPE_WHATSAPP"},
        {**msg(13, "inbound", conversation="pending"), "message_type": "TYPE_WHATSAPP"},
    ]
    assert summarize_whatsapp_messages(messages) == {
        "manual_sent": 2,
        "automatic_sent": 1,
        "received": 2,
        "responded": 1,
        "pending": 1,
        "new_manual": 1,
        "work_seconds": 360,
    }


def test_two_day_email_universe_tracks_previous_today_and_current_open_state():
    messages = [
        {**msg(18, "inbound", conversation="prior-open"), "occurred_at": datetime(2026, 9, 23, 18, tzinfo=CHILE)},
        {**msg(18, "inbound", conversation="prior-closed"), "occurred_at": datetime(2026, 9, 23, 18, tzinfo=CHILE)},
        {**msg(19, "outbound", "app", "prior-closed"), "occurred_at": datetime(2026, 9, 23, 19, tzinfo=CHILE)},
        msg(10, "inbound", conversation="today-answered"),
        msg(11, "outbound", "app", "today-answered"),
        msg(12, "inbound", conversation="today-open"),
        msg(13, "outbound", "workflow", "today-open"),
    ]

    result = summarize_conversation_work(messages, date(2026, 9, 24), "TYPE_EMAIL")

    assert result == {
        "pending_previous": 1,
        "today": 2,
        "total": 3,
        "responded": 1,
        "unanswered": 2,
    }


def test_prior_open_conversation_with_new_inbound_today_is_counted_once():
    messages = [
        {**msg(18, "inbound", conversation="same"), "occurred_at": datetime(2026, 9, 23, 18, tzinfo=CHILE)},
        msg(10, "inbound", conversation="same"),
        msg(11, "outbound", "bulk_actions", "same"),
    ]

    result = summarize_conversation_work(messages, date(2026, 9, 24), "TYPE_EMAIL")

    assert result["pending_previous"] == 1
    assert result["today"] == 0
    assert result["total"] == 1
    assert result["responded"] == 1
    assert result["unanswered"] == 0

