"""Configuración de Alicia. Lee de entorno / .env; nunca hardcodea secretos.

Reutiliza los getters compartidos (`shared.config`) para los secretos que ya
existen en el proyecto (Telegram, Anthropic) y define aquí solo lo específico
de Alicia. Pensado para correr headless (GitHub Actions), sin depender de
Streamlit.
"""
from __future__ import annotations

import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent  # raíz del repo
_loaded = False


def _load() -> None:
    global _loaded
    if _loaded:
        return
    for candidate in [_ROOT / ".env.local", _ROOT / ".env", _ROOT / ".env.txt"]:
        if candidate.exists():
            load_dotenv(candidate, override=False)
            break
    _loaded = True


def _get(key: str, default: str = "") -> str:
    _load()
    return os.getenv(key, default)


def _flag(key: str, default: bool) -> bool:
    raw = _get(key, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "y", "on", "si", "sí"}


# --- Interruptores de seguridad -------------------------------------------------

def dry_run() -> bool:
    """Si True (por defecto) no se envían correos ni se escribe en GHL de verdad."""
    return _flag("ALICIA_DRY_RUN", default=True)


def ai_enabled() -> bool:
    """Interruptor maestro de IA. False por defecto: apaga TODA llamada a modelos.

    Aunque esté en True, la IA sigue sin ejecutarse automáticamente: solo se
    invoca bajo petición explícita del usuario desde Telegram (ver alicia/ai.py).
    """
    return _flag("ALICIA_AI_ENABLED", default=False)


def enabled() -> bool:
    """Interruptor de habilitación del servicio completo (para el workflow)."""
    return _flag("ALICIA_ENABLED", default=False)


# --- Ventana y horario de ejecución --------------------------------------------

def lookback_hours() -> int:
    """Cuántas horas hacia atrás mira Gmail en cada corrida (evita perder correos
    entre ejecuciones espaciadas). Por defecto 14h para cubrir dos corridas/día."""
    try:
        return int(_get("ALICIA_LOOKBACK_HOURS", "14"))
    except ValueError:
        return 14


def timezone() -> ZoneInfo:
    return ZoneInfo(_get("ALICIA_TIMEZONE", "America/Santiago"))


def run_hours() -> list[int]:
    """Horas locales en las que se permite correr. Configurable.

    Por defecto dos veces al día: 08:00 y 20:00. El script se auto-limita a estas
    horas, de modo que el cron del workflow puede dispararse cada hora sin costo.
    """
    raw = _get("ALICIA_RUN_HOURS", "8,20")
    hours: list[int] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if chunk.isdigit():
            hours.append(int(chunk) % 24)
    return hours or [8, 20]


# --- Gmail ----------------------------------------------------------------------

def gmail_oauth_client_id() -> str:
    return _get("GMAIL_OAUTH_CLIENT_ID")


def gmail_oauth_client_secret() -> str:
    return _get("GMAIL_OAUTH_CLIENT_SECRET")


def accounts_json() -> str:
    """Fallback de registro de cuentas cuando no se usa la tabla Supabase.

    JSON: [{"account_id":"cuenta01","email":"...","enabled":true,
            "token_env":"GMAIL_REFRESH_TOKEN_CUENTA01","cliente_slug":"gbs"}]
    """
    return _get("ALICIA_ACCOUNTS_JSON", "")


def refresh_token_for(token_env: str) -> str:
    """Resuelve el refresh token de una cuenta a partir del NOMBRE de su env var."""
    return _get(token_env) if token_env else ""


# --- Telegram / Supabase (reutiliza secretos existentes) ------------------------

def telegram_token() -> str:
    try:
        from shared.config import telegram_token as _t
        val = _t()
        if val:
            return val
    except Exception:
        pass
    return _get("TELEGRAM_TOKEN")


def telegram_chat_id() -> str:
    try:
        from shared.config import telegram_chat_id as _c
        val = _c()
        if val:
            return val
    except Exception:
        pass
    return _get("TELEGRAM_CHAT_ID")


def telegram_webhook_secret() -> str:
    """Token secreto que Telegram envía en la cabecera para validar el webhook."""
    return _get("TELEGRAM_WEBHOOK_SECRET")


def anthropic_key() -> str:
    try:
        from shared.config import anthropic_key as _a
        val = _a()
        if val:
            return val
    except Exception:
        pass
    return _get("ANTHROPIC_API_KEY")


def anthropic_model() -> str:
    return _get("ALICIA_AI_MODEL", "claude-haiku-4-5-20251001")


def supabase_url() -> str:
    return _get("SUPABASE_URL")


def supabase_key() -> str:
    return _get("SUPABASE_SECRET_KEY") or _get("SUPABASE_SERVICE_ROLE_KEY") or _get("SUPABASE_KEY")
