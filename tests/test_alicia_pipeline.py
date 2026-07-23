"""Tests determinísticos del pipeline, correlación Snov, notificación y borradores.

Todo con fakes en memoria: sin red, sin IA, sin Gmail real.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alicia import accounts as accounts_mod
from alicia.drafting import Intent, build_draft, interpret_instruction
from alicia.gmail_client import build_reply_mime, reply_subject
from alicia.notifications import ReplyRecord, build_notification
from alicia.pipeline import PipelineDeps, run
from alicia.snov_match import SnovLookup


# --- Fakes ----------------------------------------------------------------------

class FakeStore:
    """Emula PostgREST: .select con filtros eq., más upsert/insert en memoria."""

    def __init__(self, snov_events=None, campaigns=None):
        self.snov_events = snov_events or {}   # email -> row
        self.campaigns = campaigns or {}       # campaign_id -> row
        self.processed = set()
        self.threads = {}
        self.actions = []
        self.runs = []
        self.links = []

    def select(self, table, columns, **params):
        if table == "snov_email_events":
            email = params.get("prospect_email", "").removeprefix("eq.")
            row = self.snov_events.get(email)
            return [row] if row else []
        if table == "snov_campaigns":
            cid = params.get("snov_campaign_id", "").removeprefix("eq.")
            row = self.campaigns.get(cid)
            return [row] if row else []
        if table == "alicia_processed_messages":
            mid = params.get("gmail_message_id", "").removeprefix("eq.")
            return [{"gmail_message_id": mid}] if mid in self.processed else []
        if table == "alicia_accounts":
            return []
        return []

    def upsert(self, table, rows, conflict):
        if table == "alicia_processed_messages":
            for r in rows:
                self.processed.add(r["gmail_message_id"])
        elif table == "alicia_email_threads":
            for r in rows:
                self.threads[r["thread_id"]] = r
        return rows

    def insert(self, table, row):
        if table == "alicia_actions_log":
            self.actions.append(row)
        elif table == "alicia_runs":
            self.runs.append(row)
        elif table == "alicia_telegram_links":
            self.links.append(row)


class FakeState:
    def __init__(self, store):
        self.store = store

    def already_processed(self, mid):
        return mid in self.store.processed

    def mark_processed(self, mid, thread_id, account_id, classification):
        self.store.processed.add(mid)

    def upsert_thread(self, row):
        self.store.threads[row["thread_id"]] = row


class FakeGmail:
    def __init__(self, messages):
        self.messages = messages          # id -> meta dict
        self.marked_read = []

    def list_new_message_ids(self, lookback_hours, extra_query=""):
        return list(self.messages.keys())

    def get_metadata(self, message_id):
        return self.messages[message_id]

    def mark_read(self, message_id):
        self.marked_read.append(message_id)


class FakeTelegram:
    def __init__(self):
        self.sent = []

    def send_all(self, messages):
        self.sent.extend(messages)
        return [{"ok": True} for _ in messages]


def meta(thread_id, from_addr, subject, snippet="", labels=None, extra_headers=None):
    headers = [
        {"name": "From", "value": from_addr},
        {"name": "Subject", "value": subject},
    ]
    for k, v in (extra_headers or {}).items():
        headers.append({"name": k, "value": v})
    return {
        "threadId": thread_id,
        "snippet": snippet,
        "labelIds": labels or ["INBOX", "UNREAD"],
        "payload": {"headers": headers},
    }


# --- Correlación Snov -----------------------------------------------------------

def test_snov_match_found():
    store = FakeStore(
        snov_events={"ana@empresa.com": {"snov_campaign_id": "C1", "cliente_slug": "gbs",
                                         "prospect_name": "Ana Díaz", "company": "Empresa SA"}},
        campaigns={"C1": {"nombre": "GBS Q3", "cliente_slug": "gbs"}},
    )
    match = SnovLookup(store).by_email("ana@empresa.com")
    assert match.matched
    assert match.cliente_slug == "gbs"
    assert match.campaign_name == "GBS Q3"
    assert match.empresa == "Empresa SA"


def test_snov_match_not_found():
    match = SnovLookup(FakeStore()).by_email("desconocido@nadie.com")
    assert not match.matched


# --- Pipeline end-to-end (determinístico) --------------------------------------

def _deps(store, gmail, telegram=None, dry_run=True):
    account = accounts_mod.Account(
        account_id="cuenta01", email="ventas@conprospeccion.com",
        enabled=True, token_env="GMAIL_REFRESH_TOKEN_CUENTA01", cliente_slug="gbs",
    )
    return PipelineDeps(
        accounts=[account],
        gmail_factory=lambda _a: gmail,
        state=FakeState(store),
        snov=SnovLookup(store),
        telegram=telegram,
        lookback_hours=14,
        dry_run=dry_run,
    )


def test_pipeline_detects_only_snov_reply():
    store = FakeStore(
        snov_events={"ana@empresa.com": {"snov_campaign_id": "C1", "cliente_slug": "gbs",
                                         "prospect_name": "Ana Díaz", "company": "Empresa SA"}},
        campaigns={"C1": {"nombre": "GBS Q3", "cliente_slug": "gbs"}},
    )
    gmail = FakeGmail({
        "m1": meta("t1", "Ana Díaz <ana@empresa.com>", "Re: Propuesta", "Me interesa, conversemos"),
        "m2": meta("t2", "MAILER-DAEMON@x.com", "Undelivered Mail"),            # rebote
        "m3": meta("t3", "ceo@otra.com", "Automatic reply: out of office"),     # OOO
        "m4": meta("t4", "extrano@ajeno.com", "Re: cualquier cosa"),            # no Snov
    })
    telegram = FakeTelegram()
    result = run(_deps(store, gmail, telegram))

    assert result.replies_detected == 1
    assert result.replies[0].prospect == "Ana Díaz"
    assert result.filtered_out["bounce"] == 1
    assert result.filtered_out["out_of_office"] == 1
    assert result.filtered_out["unrelated"] == 1
    # Una sola notificación agrupada, y se envió.
    assert telegram.sent
    assert "1 respuesta" in telegram.sent[0]


def test_pipeline_dry_run_does_not_mark_read():
    store = FakeStore(
        snov_events={"ana@empresa.com": {"snov_campaign_id": "C1", "cliente_slug": "gbs",
                                         "prospect_name": "Ana", "company": "E"}},
        campaigns={"C1": {"nombre": "GBS", "cliente_slug": "gbs"}},
    )
    gmail = FakeGmail({"m1": meta("t1", "ana@empresa.com", "Re: x", "hola")})
    run(_deps(store, gmail, dry_run=True))
    assert gmail.marked_read == []


def test_pipeline_idempotent_second_run():
    store = FakeStore(
        snov_events={"ana@empresa.com": {"snov_campaign_id": "C1", "cliente_slug": "gbs",
                                         "prospect_name": "Ana", "company": "E"}},
        campaigns={"C1": {"nombre": "GBS", "cliente_slug": "gbs"}},
    )
    gmail = FakeGmail({"m1": meta("t1", "ana@empresa.com", "Re: x", "hola")})
    first = run(_deps(store, gmail))
    second = run(_deps(store, gmail))
    assert first.replies_detected == 1
    assert second.replies_detected == 0  # ya procesado → no re-alerta


def test_pipeline_not_dry_run_marks_read():
    store = FakeStore(
        snov_events={"ana@empresa.com": {"snov_campaign_id": "C1", "cliente_slug": "gbs",
                                         "prospect_name": "Ana", "company": "E"}},
        campaigns={"C1": {"nombre": "GBS", "cliente_slug": "gbs"}},
    )
    gmail = FakeGmail({"m1": meta("t1", "ana@empresa.com", "Re: x", "hola")})
    run(_deps(store, gmail, dry_run=False))
    assert gmail.marked_read == ["m1"]


# --- Notificación agrupada ------------------------------------------------------

def test_notification_empty():
    msgs = build_notification([])
    assert len(msgs) == 1
    assert "sin respuestas" in msgs[0].lower()


def test_notification_fields_present():
    reply = ReplyRecord(
        internal_ref="AL-ABCD1234", cliente="gbs", campaign="GBS Q3",
        account_email="ventas@conprospeccion.com", prospect="Ana Díaz",
        empresa="Empresa SA", subject="Re: Propuesta", last_message="Me interesa",
    )
    msg = build_notification([reply])[0]
    for token in ["AL-ABCD1234", "gbs", "GBS Q3", "ventas@conprospeccion.com",
                  "Ana Díaz", "Empresa SA", "Re: Propuesta", "Me interesa"]:
        assert token in msg


# --- Borradores / instrucciones (sin IA) ---------------------------------------

def test_interpret_do_not_reply():
    assert interpret_instruction("No responder").intent is Intent.DO_NOT_REPLY


def test_interpret_literal_prefix():
    ins = interpret_instruction("Envía exactamente: Gracias, coordinemos el martes")
    assert ins.intent is Intent.LITERAL
    assert ins.text == "Gracias, coordinemos el martes"


def test_interpret_quoted_literal():
    ins = interpret_instruction('"Te enviaremos la información"')
    assert ins.intent is Intent.LITERAL
    assert ins.text == "Te enviaremos la información"


def test_interpret_natural_is_ai():
    ins = interpret_instruction("Respóndele agradeciendo y propón reunión el martes")
    assert ins.intent is Intent.AI_DRAFT


def test_build_draft_literal_no_ai():
    intent, body = build_draft("literal: hola mundo", "Re: x", "mensaje", "gbs")
    assert intent is Intent.LITERAL
    assert body == "hola mundo"


def test_build_draft_ai_disabled_raises():
    # IA apagada por defecto → la rama AI_DRAFT debe fallar de forma controlada.
    from alicia.ai import AIDisabledError
    with pytest.raises(AIDisabledError):
        build_draft("redáctale algo amable", "Re: x", "mensaje", "gbs")


# --- MIME de respuesta en hilo --------------------------------------------------

def test_reply_subject_prefixes_re():
    assert reply_subject("Propuesta") == "Re: Propuesta"
    assert reply_subject("Re: Propuesta") == "Re: Propuesta"
    assert reply_subject("") == "Re:"


def test_build_reply_mime_threads_headers():
    import base64
    raw = build_reply_mime(
        from_addr="ventas@conprospeccion.com", to_addr="ana@empresa.com",
        subject="Propuesta", body="Hola Ana", in_reply_to="<msg-1@empresa.com>",
        references="<msg-0@empresa.com>",
    )
    decoded = base64.urlsafe_b64decode(raw).decode("utf-8")
    assert "In-Reply-To: <msg-1@empresa.com>" in decoded
    assert "<msg-0@empresa.com>" in decoded and "<msg-1@empresa.com>" in decoded
    assert "Subject: Re: Propuesta" in decoded
    assert "Hola Ana" in decoded


# --- Identificador interno ------------------------------------------------------

def test_internal_ref_stable():
    a = accounts_mod.internal_ref("thread-xyz")
    b = accounts_mod.internal_ref("thread-xyz")
    assert a == b and a.startswith("AL-") and len(a) == 11


def test_accounts_from_json_and_enabled_filter():
    raw = (
        '[{"account_id":"c1","email":"a@x.com","enabled":true,"token_env":"T1"},'
        '{"account_id":"c2","email":"b@x.com","enabled":false,"token_env":"T2"}]'
    )
    parsed = accounts_mod.from_json(raw)
    assert len(parsed) == 2
    enabled = [a for a in parsed if a.enabled]
    assert len(enabled) == 1 and enabled[0].account_id == "c1"
