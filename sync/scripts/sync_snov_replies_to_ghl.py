from __future__ import annotations

import argparse
import logging
from typing import Any

import httpx

from config import get_optional_env, get_settings
from ghl_client import DuplicateContactError, GHLClient
from snov_client import SnovClient
from snov_ghl_matching import (
    GhlAction,
    build_ghl_contact_payload,
    build_update_payload,
    decide_action,
    extract_snov_enrichment,
)
from supabase_rest import SupabaseRestClient
from telegram_client import TelegramClient
from telegram_ghl_cards import (
    build_agendar_keyboard,
    build_agendar_prompt,
    build_mismatch_alert,
    build_new_contact_card,
    build_reply_email_keyboard,
    build_status_keyboard,
    build_status_prompt,
    build_tarea_keyboard,
    build_tarea_prompt,
    build_updated_contact_card,
    order_status_options,
)


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)


def token_for_client(slug: str) -> str:
    env_key = {"gbs": "GHL_TOKEN_GBS_LOGISTICS"}.get(slug, f"GHL_TOKEN_{slug.upper()}")
    token = get_optional_env(env_key)
    if not token:
        raise RuntimeError(f"Falta {env_key} en .env/.env.txt")
    return token


def telegram_for_client(slug: str) -> tuple[TelegramClient, list[str]] | None:
    token = get_optional_env(f"TELEGRAM_BOT_{slug.upper()}_TOKEN")
    chat_ids_raw = get_optional_env(f"TELEGRAM_BOT_{slug.upper()}_CHAT_IDS")
    if not token or not chat_ids_raw:
        return None
    chat_ids = [c.strip() for c in chat_ids_raw.split(",") if c.strip()]
    return (TelegramClient(token), chat_ids) if chat_ids else None


def active_clients(supabase: SupabaseRestClient) -> list[dict[str, Any]]:
    rows = supabase.select("clientes", "nombre,slug,ghl_location_id", order="nombre.asc")
    return [row for row in rows if row.get("ghl_location_id")]


def campaigns_by_client(supabase: SupabaseRestClient) -> dict[str, list[str]]:
    rows = supabase.select_all("snov_campaign_map", "snov_campaign_id,cliente_slug")
    result: dict[str, list[str]] = {}
    for row in rows:
        if row.get("cliente_slug") and row.get("snov_campaign_id"):
            result.setdefault(row["cliente_slug"], []).append(row["snov_campaign_id"])
    return result


def _send_status_options(
    client_bot: TelegramClient, chat_id: str, ghl: GHLClient, location_id: str, contact_id: str, nombre: str,
) -> None:
    """Replica send_status_options() de telegram_ghl_bot.py — se duplica en
    vez de importarse porque telegram_ghl_bot.py no expone esta funcion como
    utilidad de bajo nivel reusable sin arrastrar el resto del modulo del bot."""
    custom_field_ids = ghl.custom_field_id_map(location_id)
    field_id = custom_field_ids.get("status_prospecto")
    if not field_id:
        client_bot.send_message(chat_id, "⚠️ No encontré el campo STATUS PROSPECTO en esta location.")
        return
    ordered = order_status_options(ghl.custom_field_options(location_id, field_id))
    keyboard = build_status_keyboard(ordered, contact_id)
    client_bot.send_message(chat_id, build_status_prompt(nombre, contact_id), reply_markup=keyboard)


def send_followup_buttons(
    client_bot: TelegramClient, chat_id: str, ghl: GHLClient, location_id: str, contact_id: str, nombre: str,
) -> None:
    """Manda los 3 bloques de botones (status/agendar/tarea) que antes solo
    se mandaban cuando la SDR respondia a la tarjeta (telegram_ghl_bot.py,
    handle_message) — ahora se mandan de una junto con la tarjeta, para que
    le lleguen todos los botones juntos sin que tenga que responder primero.
    El camino de responder a la tarjeta sigue funcionando igual (no se
    toca), por si necesita re-disparar los botones despues."""
    for step in (
        lambda: _send_status_options(client_bot, chat_id, ghl, location_id, contact_id, nombre),
        lambda: client_bot.send_message(
            chat_id, build_agendar_prompt(nombre, contact_id), reply_markup=build_agendar_keyboard(contact_id),
        ),
        lambda: client_bot.send_message(
            chat_id, build_tarea_prompt(nombre, contact_id), reply_markup=build_tarea_keyboard(contact_id),
        ),
    ):
        try:
            step()
        except Exception:
            # Un bloque que falla (ej. GHL momentaneamente caido) no debe
            # tirar abajo el resto del sync run para los demas prospectos.
            logging.exception("Error mandando un bloque de botones para %s", contact_id)


def notify(
    telegram: tuple[TelegramClient, list[str]] | None,
    supabase: SupabaseRestClient,
    text: str,
    *,
    cliente_slug: str,
    ghl_contact_id: str | None,
    ghl_location_id: str,
    prospect_name: str | None,
    prospect_email: str | None,
    dry_run: bool,
    ghl: GHLClient,
) -> None:
    if not telegram or dry_run:
        return
    client_bot, chat_ids = telegram
    # El botón "Responder correo" solo existe para BambuTech (únicas
    # casillas IMAP/SMTP configuradas hoy) y solo cuando la tarjeta tiene un
    # contacto real asociado — la tarjeta de mismatch (ghl_contact_id=None)
    # no lleva botón porque no hay a quién contestarle.
    reply_markup = build_reply_email_keyboard(ghl_contact_id) if cliente_slug == "bambutech" and ghl_contact_id else None
    for chat_id in chat_ids:
        sent = client_bot.send_message(chat_id, text, reply_markup=reply_markup)
        if ghl_contact_id:
            supabase.insert("telegram_ghl_cards", {
                "cliente_slug": cliente_slug,
                "chat_id": int(chat_id),
                "telegram_message_id": sent["message_id"],
                "ghl_contact_id": ghl_contact_id,
                "ghl_location_id": ghl_location_id,
                "prospect_name": prospect_name,
                "prospect_email": prospect_email,
            })
        # Solo BambuTech tiene bot de Telegram interactivo configurado hoy
        # (mismo gate que el boton de email arriba) y solo cuando hay un
        # contacto real de GHL asociado — sin eso no hay a quien mandarle
        # status/agendar/tarea.
        if cliente_slug == "bambutech" and ghl_contact_id:
            send_followup_buttons(
                client_bot, chat_id, ghl, ghl_location_id, ghl_contact_id, prospect_name or prospect_email or "(sin nombre)",
            )


REPLIES_PAGE_SIZE = 10000


def all_replies(snov: SnovClient, campaign_id: str) -> list[dict[str, Any]]:
    replies: list[dict[str, Any]] = []
    offset = 0
    while True:
        batch = snov.replies(campaign_id, offset=offset)
        replies.extend(batch)
        if len(batch) < REPLIES_PAGE_SIZE:
            break
        offset += REPLIES_PAGE_SIZE
    return replies


def _recover_from_duplicate_create(
    ghl: GHLClient,
    exc: DuplicateContactError,
    enrichment: dict[str, Any],
    custom_field_ids: dict[str, str],
) -> dict[str, Any]:
    """El POST /contacts/ fallo con 400 "duplicated contacts" porque GHL
    considera que el contacto ya existe (por email, additionalEmail,
    telefono u otro criterio interno que no controlamos). En vez de intentar
    adivinar de antemano todos esos criterios, GHL ya nos dio el contactId
    real en el error (exc.contact_id) — lo recuperamos trayendo ese contacto
    y tratandolo exactamente como el camino de UPDATE."""
    existing = ghl.get_contact(exc.contact_id)["contact"]
    payload = build_update_payload(existing, enrichment, custom_field_ids)
    if payload:
        ghl.update_contact(existing["id"], payload)
    return existing


def process_client(
    client: dict[str, Any],
    campaign_ids: list[str],
    snov: SnovClient,
    supabase: SupabaseRestClient,
    stats: dict[str, int],
    dry_run: bool,
) -> None:
    slug = client["slug"]
    location_id = client["ghl_location_id"]
    ghl = GHLClient(token_for_client(slug))
    custom_field_ids = ghl.custom_field_id_map(location_id)
    telegram = telegram_for_client(slug)

    for campaign_id in campaign_ids:
        for reply in all_replies(snov, campaign_id):
            email = reply.get("prospectEmail")
            prospect_id = reply.get("prospectId")
            if not email or not prospect_id:
                continue

            detail = snov.prospect_by_id(prospect_id)
            enrichment = extract_snov_enrichment(detail.get("data") or {})
            if not enrichment.get("name"):
                enrichment["name"] = reply.get("prospectName")

            existing = ghl.find_contact_by_email(location_id, email)
            action = decide_action(existing, enrichment, custom_field_ids)
            nombre = enrichment.get("name") or email
            campaign_name = reply.get("campaign") or campaign_id
            reply_snippet = (reply.get("emails") or [{}])[0].get("emailBody")

            if action == GhlAction.CREATE:
                payload = build_ghl_contact_payload(enrichment, email, slug, custom_field_ids)
                contact_id = None
                recovered_existing = None
                if not dry_run:
                    try:
                        created = ghl.create_contact(location_id, payload)
                        contact_id = created["contact"]["id"]
                    except DuplicateContactError as exc:
                        # GHL considera el contacto duplicado (por email,
                        # additionalEmail u otro criterio propio) y ya nos dio
                        # el contactId real — nos recuperamos como si hubiera
                        # sido un UPDATE en vez de perder este prospecto.
                        recovered_existing = _recover_from_duplicate_create(
                            ghl, exc, enrichment, custom_field_ids,
                        )

                if recovered_existing is not None:
                    stats["updated"] += 1
                    notify(
                        telegram, supabase,
                        build_updated_contact_card(
                            slug, client["nombre"], nombre, enrichment, email, recovered_existing["id"],
                            reply_snippet=reply_snippet,
                        ),
                        cliente_slug=slug, ghl_contact_id=recovered_existing["id"], ghl_location_id=location_id,
                        prospect_name=nombre, prospect_email=email, dry_run=dry_run, ghl=ghl,
                    )
                else:
                    stats["created"] += 1
                    # En dry-run no hay contact_id real todavia (no se crea el
                    # contacto) — se usa el email como identificador estable para
                    # la insignia, es solo una ayuda visual, no un id real.
                    notify(
                        telegram, supabase, build_new_contact_card(
                            slug, client["nombre"], campaign_name, enrichment, email, contact_id or email,
                            reply_snippet=reply_snippet,
                        ),
                        cliente_slug=slug, ghl_contact_id=contact_id, ghl_location_id=location_id,
                        prospect_name=nombre, prospect_email=email, dry_run=dry_run, ghl=ghl,
                    )

            elif action == GhlAction.UPDATE:
                payload = build_update_payload(existing, enrichment, custom_field_ids)
                if payload and not dry_run:
                    ghl.update_contact(existing["id"], payload)
                stats["updated"] += 1
                notify(
                    telegram, supabase,
                    build_updated_contact_card(
                        slug, client["nombre"], nombre, enrichment, email, existing["id"],
                        reply_snippet=reply_snippet,
                    ),
                    cliente_slug=slug, ghl_contact_id=existing["id"], ghl_location_id=location_id,
                    prospect_name=nombre, prospect_email=email, dry_run=dry_run, ghl=ghl,
                )

            elif action == GhlAction.SKIP_MISMATCH:
                stats["mismatch"] += 1
                ghl_name = f"{existing.get('firstName') or ''} {existing.get('lastName') or ''}".strip() or "(sin nombre)"
                notify(
                    telegram, supabase, build_mismatch_alert(client["nombre"], email, ghl_name, nombre),
                    cliente_slug=slug, ghl_contact_id=None, ghl_location_id=location_id,
                    prospect_name=nombre, prospect_email=email, dry_run=dry_run, ghl=ghl,
                )
            else:
                stats["skipped"] += 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Detecta respuestas de Snov y crea/actualiza el contacto en GHL.")
    parser.add_argument("--client", action="append", help="Limitar a estos cliente_slug")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    setup_logging()

    snov_client_id = get_optional_env("SNOV_CLIENT_ID")
    snov_client_secret = get_optional_env("SNOV_CLIENT_SECRET")
    if not snov_client_id or not snov_client_secret:
        raise RuntimeError("Faltan SNOV_CLIENT_ID y/o SNOV_CLIENT_SECRET en .env/.env.txt")
    snov = SnovClient(snov_client_id, snov_client_secret)

    settings = get_settings()
    supabase = SupabaseRestClient(settings.supabase_url, settings.supabase_secret_key)

    clients = active_clients(supabase)
    if args.client:
        wanted = set(args.client)
        clients = [c for c in clients if c["slug"] in wanted]
    by_client = campaigns_by_client(supabase)

    stats: dict[str, int] = {"created": 0, "updated": 0, "mismatch": 0, "skipped": 0}
    errors: list[str] = []
    for client in clients:
        campaign_ids = by_client.get(client["slug"], [])
        if not campaign_ids:
            logging.info("%s: sin campanas mapeadas en snov_campaign_map, se omite", client["slug"])
            continue
        try:
            process_client(client, campaign_ids, snov, supabase, stats, args.dry_run)
        except httpx.HTTPStatusError as exc:
            logging.error("%s fallo HTTP %s: %s", client["slug"], exc.response.status_code, exc.response.text[:300])
            errors.append(f"{client['slug']}: HTTP {exc.response.status_code} {exc.response.text[:200]}")
        except Exception as exc:
            logging.error("%s fallo: %s", client["slug"], exc)
            errors.append(f"{client['slug']}: {exc}")

    logging.info("Resumen: %s", stats)
    if not args.dry_run:
        supabase.insert("sync_runs", {"source": "snov_replies_ghl", "entity": "contacts", "status": "success" if not errors else "partial_error", "stats": stats, "errors": errors})


if __name__ == "__main__":
    main()
