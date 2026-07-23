"""Entrypoint del poller de Alicia.

Se auto-limita a las horas configuradas (ALICIA_RUN_HOURS, por defecto 8 y 20),
de modo que el cron del workflow puede dispararse cada hora sin costo: solo corre
de verdad dos veces al día. `--force` ignora la ventana horaria (para pruebas).

Nada aquí llama a IA. Con ALICIA_DRY_RUN=true (por defecto) no marca correos como
leídos ni realiza acciones GHL reales.
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone

import httpx

from alicia import accounts as accounts_mod
from alicia import pipeline as pipeline_mod
from alicia import settings
from alicia.gmail_client import AccessTokenProvider, GmailClient
from alicia.snov_match import SnovLookup
from alicia.store import AliciaState, SupabaseStore
from alicia.telegram_io import TelegramClient


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)


def within_schedule() -> bool:
    now_local = datetime.now(settings.timezone())
    return now_local.hour in set(settings.run_hours())


def build_deps() -> pipeline_mod.PipelineDeps:
    store = SupabaseStore(settings.supabase_url(), settings.supabase_key())
    state = AliciaState(store)
    snov = SnovLookup(store)
    accounts = accounts_mod.load_accounts(store, only_enabled=True)

    shared_http = httpx.Client(timeout=60)
    client_id = settings.gmail_oauth_client_id()
    client_secret = settings.gmail_oauth_client_secret()

    def gmail_factory(account: accounts_mod.Account) -> GmailClient:
        auth = AccessTokenProvider(client_id, client_secret, account.refresh_token())
        return GmailClient(account.email, auth, http=shared_http)

    telegram = None
    if settings.telegram_token() and settings.telegram_chat_id():
        telegram = TelegramClient(settings.telegram_token(), settings.telegram_chat_id())

    return pipeline_mod.PipelineDeps(
        accounts=accounts,
        gmail_factory=gmail_factory,
        state=state,
        snov=snov,
        telegram=telegram,
        lookback_hours=settings.lookback_hours(),
        dry_run=settings.dry_run(),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Poller de respuestas Snov → Telegram (Alicia).")
    parser.add_argument("--force", action="store_true", help="Ignora la ventana horaria.")
    args = parser.parse_args()
    setup_logging()

    if not settings.enabled():
        logging.info("ALICIA_ENABLED=false — servicio deshabilitado, no se ejecuta.")
        return 0
    if not args.force and not within_schedule():
        logging.info(
            "Fuera de la ventana horaria (%s). Usa --force para forzar.", settings.run_hours()
        )
        return 0

    deps = build_deps()
    if not deps.accounts:
        logging.warning("No hay cuentas habilitadas (alicia_accounts / ALICIA_ACCOUNTS_JSON).")

    started = datetime.now(timezone.utc)
    result = pipeline_mod.run(deps)
    finished = datetime.now(timezone.utc)

    try:
        deps.state.record_run(
            {
                "started_at": started.isoformat(),
                "finished_at": finished.isoformat(),
                "accounts_checked": result.accounts_checked,
                "messages_scanned": result.messages_scanned,
                "replies_detected": result.replies_detected,
                "filtered_out": dict(result.filtered_out),
                "status": "success",
                "dry_run": deps.dry_run,
            }
        )
    except Exception as exc:
        logging.warning("No se pudo registrar la corrida: %s", exc)

    return 0


if __name__ == "__main__":
    sys.exit(main())
