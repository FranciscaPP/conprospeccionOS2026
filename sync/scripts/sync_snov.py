from __future__ import annotations

import argparse
import hashlib
import logging
from datetime import date, datetime, timezone
from typing import Any

import httpx

from config import get_optional_env, get_settings
from snov_client import SnovClient
from supabase_rest import SupabaseRestClient


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_unix(value: Any) -> str | None:
    if value in (None, "", 0):
        return None
    try:
        return datetime.fromtimestamp(int(value), timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def parse_snov_dt(value: Any) -> str | None:
    if not value:
        return None
    if isinstance(value, dict):
        value = value.get("date")
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).isoformat()
    except ValueError:
        try:
            return datetime.strptime(str(value).split(".")[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            return None


def parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def to_int(value: Any) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def to_num(value: Any) -> float:
    if isinstance(value, str):
        value = value.strip().replace("%", "")
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def campaign_maps(supabase: SupabaseRestClient) -> dict[str, dict[str, Any]]:
    rows = supabase.select_all("snov_campaign_map", "snov_campaign_id,cliente_slug,sdr_slug")
    return {str(row["snov_campaign_id"]): row for row in rows if row.get("snov_campaign_id")}


def campaign_rows(campaigns: list[dict[str, Any]], maps: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for campaign in campaigns:
        campaign_id = str(campaign.get("id"))
        mapping = maps.get(campaign_id, {})
        rows.append(
            {
                "snov_campaign_id": campaign_id,
                "cliente_slug": mapping.get("cliente_slug"),
                "sdr_slug": mapping.get("sdr_slug"),
                "nombre": campaign.get("campaign"),
                "list_id": str(campaign.get("list_id")) if campaign.get("list_id") is not None else None,
                "status": campaign.get("status"),
                "hash": campaign.get("hash"),
                "created_at_snov": parse_unix(campaign.get("created_at")),
                "updated_at_snov": parse_unix(campaign.get("updated_at")),
                "started_at_snov": parse_unix(campaign.get("started_at")),
                "raw_data": campaign,
                "synced_at": iso_now(),
            }
        )
    return rows


def analytics_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "campaigns", "items", "result"):
            if isinstance(payload.get(key), list):
                return payload[key]
        return [payload]
    return []


def metric_rows(
    analytics_by_campaign: dict[str, Any],
    progress_by_campaign: dict[str, dict[str, Any]],
    campaigns_by_id: dict[str, dict[str, Any]],
    maps: dict[str, dict[str, Any]],
    date_from: date | None,
    date_to: date | None,
) -> list[dict[str, Any]]:
    rows = []
    for campaign_id, analytics in analytics_by_campaign.items():
        items = analytics_items(analytics)
        if not items:
            continue
        item = items[0]
        mapping = maps.get(campaign_id, {})
        campaign = campaigns_by_id.get(campaign_id, {})
        progress = progress_by_campaign.get(campaign_id, {})
        rows.append(
            {
                "snov_campaign_id": campaign_id,
                "cliente_slug": mapping.get("cliente_slug") or campaign.get("cliente_slug"),
                "sdr_slug": mapping.get("sdr_slug") or campaign.get("sdr_slug"),
                "periodo_desde": date_from.isoformat() if date_from else None,
                "periodo_hasta": date_to.isoformat() if date_to else None,
                "recipients_contacted": to_int(item.get("recipients_contacted") or item.get("total_contacted") or item.get("contacted")),
                "emails_sent": to_int(item.get("emails_sent") or item.get("sent")),
                "email_opens": to_int(item.get("email_opens") or item.get("opens")),
                "link_clicks": to_int(item.get("link_clicks") or item.get("clicks")),
                "email_replies": to_int(item.get("email_replies") or item.get("replies")),
                "unsubscribed": to_int(item.get("unsubscribed")),
                "auto_replied": to_int(item.get("auto_replied")),
                "bounced": to_int(item.get("bounced") or item.get("bounces")),
                "email_opens_rate": to_num(item.get("email_opens_rate") or item.get("opens_rate")),
                "link_clicks_rate": to_num(item.get("link_clicks_rate") or item.get("clicks_rate")),
                "email_replies_rate": to_num(item.get("email_replies_rate") or item.get("replies_rate")),
                "unsubscribed_rate": to_num(item.get("unsubscribed_rate")),
                "progress": str(progress.get("progress")) if progress.get("progress") is not None else None,
                "progress_status": progress.get("status"),
                "unfinished": to_int(progress.get("unfinished")),
                "raw_analytics": item,
                "raw_progress": progress,
                "synced_at": iso_now(),
            }
        )
    return rows


def event_id(event_type: str, campaign_id: str, item: dict[str, Any]) -> str:
    base = "|".join(
        [
            event_type,
            campaign_id,
            str(item.get("id") or ""),
            str(item.get("hash") or ""),
            str(item.get("prospectId") or ""),
            str(item.get("prospectEmail") or item.get("userEmail") or ""),
            str(item.get("sentDate") or item.get("openedAt") or item.get("visitedAt") or item.get("replyAt") or ""),
        ]
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def normalize_event(event_type: str, campaign_id: str, item: dict[str, Any], maps: dict[str, dict[str, Any]]) -> dict[str, Any]:
    mapping = maps.get(campaign_id, {})
    occurred = (
        item.get("sentDate")
        or item.get("openedAt")
        or item.get("visitedAt")
        or item.get("replyAt")
        or item.get("date")
        or item.get("finishedAt")
    )
    return {
        "snov_event_id": event_id(event_type, campaign_id, item),
        "snov_campaign_id": campaign_id,
        "cliente_slug": mapping.get("cliente_slug"),
        "sdr_slug": mapping.get("sdr_slug"),
        "event_type": event_type,
        "prospect_id": item.get("prospectId"),
        "prospect_name": item.get("prospectName") or item.get("userName"),
        "prospect_email": item.get("prospectEmail") or item.get("userEmail"),
        "company": item.get("companyName") or item.get("company"),
        "cargo": item.get("position"),
        "industria": item.get("industry"),
        "pais": item.get("country"),
        "subject": item.get("emailSubject"),
        "occurred_at": parse_snov_dt(occurred),
        "raw_data": item,
        "synced_at": iso_now(),
    }


def paged_events(fetcher, campaign_id: str, max_offsets: int | None = None) -> list[dict[str, Any]]:
    rows = []
    offset = 0
    page = 0
    while True:
        page += 1
        if max_offsets and page > max_offsets:
            break
        batch = fetcher(campaign_id, offset=offset)
        rows.extend(batch)
        if len(batch) < 10000:
            break
        offset += 10000
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Sincroniza campanas y metricas de Snov.io.")
    parser.add_argument("--date-from")
    parser.add_argument("--date-to")
    parser.add_argument("--campaign-id", action="append")
    parser.add_argument("--include-events", action="store_true")
    parser.add_argument("--max-event-offsets", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    setup_logging()

    client_id = get_optional_env("SNOV_CLIENT_ID")
    client_secret = get_optional_env("SNOV_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Faltan SNOV_CLIENT_ID y/o SNOV_CLIENT_SECRET en .env/.env.txt")

    settings = get_settings()
    supabase = SupabaseRestClient(settings.supabase_url, settings.supabase_secret_key)
    snov = SnovClient(client_id, client_secret)
    maps = campaign_maps(supabase)

    campaigns = snov.campaigns()
    if args.campaign_id:
        campaign_ids = set(args.campaign_id)
        campaigns = [campaign for campaign in campaigns if str(campaign.get("id")) in campaign_ids]
    campaigns_payload = campaign_rows(campaigns, maps)
    campaigns_by_id = {row["snov_campaign_id"]: row for row in campaigns_payload}
    logging.info("Campanas detectadas: %s", len(campaigns_payload))
    if campaigns_payload and not args.dry_run:
        supabase.upsert("snov_campaigns", campaigns_payload, "snov_campaign_id")

    ids = [row["snov_campaign_id"] for row in campaigns_payload]
    date_from = parse_date(args.date_from)
    date_to = parse_date(args.date_to)
    analytics_by_campaign = {}
    progress_by_campaign = {}
    for campaign_id in ids:
        try:
            analytics_by_campaign[campaign_id] = snov.campaign_analytics([campaign_id], date_from, date_to)
        except httpx.HTTPStatusError as exc:
            logging.warning("No se pudo obtener analytics de campana %s: %s", campaign_id, exc.response.text[:200])
        try:
            progress_by_campaign[campaign_id] = snov.campaign_progress(campaign_id)
        except httpx.HTTPStatusError as exc:
            logging.warning("No se pudo obtener progress de campana %s: %s", campaign_id, exc.response.text[:200])
    metrics = metric_rows(analytics_by_campaign, progress_by_campaign, campaigns_by_id, maps, date_from, date_to)
    logging.info("Metricas detectadas: %s", len(metrics))
    if metrics and not args.dry_run:
        supabase.upsert("snov_campaign_metrics", metrics, "snov_campaign_id,periodo_desde,periodo_hasta")

    event_stats: dict[str, int] = {}
    if args.include_events:
        fetchers = {
            "sent": snov.sent,
            "open": snov.opens,
            "click": snov.clicks,
            "reply": snov.replies,
            "finished": snov.finished,
        }
        for event_type, fetcher in fetchers.items():
            rows = []
            for campaign_id in ids:
                for item in paged_events(fetcher, campaign_id, args.max_event_offsets):
                    rows.append(normalize_event(event_type, campaign_id, item, maps))
            event_stats[event_type] = len(rows)
            logging.info("Eventos %s detectados: %s", event_type, len(rows))
            if rows and not args.dry_run:
                for index in range(0, len(rows), 500):
                    supabase.upsert("snov_email_events", rows[index : index + 500], "snov_event_id")

    if not args.dry_run:
        supabase.insert(
            "sync_runs",
            {
                "source": "snov",
                "entity": "campaigns",
                "status": "success",
                "stats": {
                    "campaigns": len(campaigns_payload),
                    "metrics": len(metrics),
                    "events": event_stats,
                    "dry_run": args.dry_run,
                },
                "errors": [],
            },
        )


if __name__ == "__main__":
    main()
