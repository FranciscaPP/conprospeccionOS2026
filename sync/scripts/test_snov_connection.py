from __future__ import annotations

import argparse
import logging

from config import get_optional_env
from snov_client import SnovClient


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prueba conexion Snov.io.")
    parser.add_argument("--show-campaigns", action="store_true")
    args = parser.parse_args()
    setup_logging()

    client_id = get_optional_env("SNOV_CLIENT_ID")
    client_secret = get_optional_env("SNOV_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Faltan SNOV_CLIENT_ID y/o SNOV_CLIENT_SECRET en .env/.env.txt")

    snov = SnovClient(client_id, client_secret)
    token = snov.access_token()
    logging.info("Conexion Snov OK. Token recibido: %s...", token[:8])

    campaigns = snov.campaigns()
    logging.info("Campanas visibles: %s", len(campaigns))
    if args.show_campaigns:
        for campaign in campaigns:
            logging.info(
                "ID=%s | status=%s | list_id=%s | nombre=%s",
                campaign.get("id"),
                campaign.get("status"),
                campaign.get("list_id"),
                campaign.get("campaign"),
            )


if __name__ == "__main__":
    main()
