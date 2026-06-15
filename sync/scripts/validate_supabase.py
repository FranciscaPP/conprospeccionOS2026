from __future__ import annotations

import logging
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
TABLES = [
    "sdrs",
    "clientes",
    "sdr_cliente",
    "cliente_metas",
    "cliente_contratos",
    "cliente_costos",
    "costos_fijos",
    "sdr_pago_reglas",
]


def load_env() -> None:
    env_path = ROOT / ".env"
    env_txt_path = ROOT / ".env.txt"
    if env_path.exists():
        load_dotenv(env_path)
    elif env_txt_path.exists():
        load_dotenv(env_txt_path)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    load_env()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SECRET_KEY")
    if not url or not key:
        raise RuntimeError("Faltan SUPABASE_URL o SUPABASE_SECRET_KEY en .env/.env.txt")

    base_url = url.rstrip("/").removesuffix("/rest/v1")
    client = httpx.Client(
        base_url=f"{base_url}/rest/v1",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        timeout=60,
    )
    missing_tables = []
    for table in TABLES:
        response = client.get(f"/{table}", params={"select": "*", "limit": "1"}, headers={"Prefer": "count=exact"})
        if response.status_code == 404:
            logging.warning("%s: no existe o no esta expuesta en PostgREST", table)
            missing_tables.append(table)
            continue
        response.raise_for_status()
        content_range = response.headers.get("content-range", "*/0")
        count = content_range.rsplit("/", 1)[-1]
        logging.info("%s: %s registros", table, count)

    if missing_tables:
        logging.warning("Ejecuta supabase/migrations/001_config_schema.sql antes de importar.")
        return

    response = client.get(
        "/clientes",
        params={"select": "nombre,ghl_location_id,estado_contrato", "order": "nombre.asc"},
    )
    response.raise_for_status()
    clients = response.json()
    logging.info("Clientes:")
    for row in clients:
        logging.info("  - %s | %s | %s", row["nombre"], row["ghl_location_id"], row["estado_contrato"])


if __name__ == "__main__":
    main()
