from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


SCRIPTS_DIR = Path(__file__).resolve().parent
SYNC_DIR    = SCRIPTS_DIR.parent       # sync/
ROOT        = SYNC_DIR.parent          # conprospeccionOS2026/ (raiz del proyecto oficial)


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_secret_key: str
    ghl_agency_token: str


def load_project_env() -> None:
    # Next/Vercel usa .env.local en desarrollo; los scripts heredados aceptan
    # tambien .env/.env.txt para compatibilidad con la etapa Streamlit.
    for candidate in [
        ROOT / ".env.local",
        ROOT / ".env",
        SYNC_DIR / ".env",
        ROOT / ".env.txt",
        SYNC_DIR / ".env.txt",
    ]:
        if candidate.exists():
            load_dotenv(candidate)
            return


def get_settings() -> Settings:
    load_project_env()
    required = {
        "SUPABASE_URL": os.getenv("SUPABASE_URL"),
        "SUPABASE_SECRET_KEY": os.getenv("SUPABASE_SECRET_KEY"),
        "GHL_AGENCY_TOKEN": os.getenv("GHL_AGENCY_TOKEN"),
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"Faltan variables en .env/.env.txt: {', '.join(missing)}")

    return Settings(
        supabase_url=required["SUPABASE_URL"],
        supabase_secret_key=required["SUPABASE_SECRET_KEY"],
        ghl_agency_token=required["GHL_AGENCY_TOKEN"],
    )


def get_optional_env(name: str) -> str | None:
    load_project_env()
    value = os.getenv(name)
    return value.strip() if value and value.strip() else None
