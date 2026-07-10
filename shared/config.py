"""
Configuración centralizada de ConprospecciónOS.
Todos los módulos (dashboard, alicia, mvp_setup, sync) deben importar desde aquí.
El .env vive en la RAÍZ del proyecto (conprospeccion-os/.env).
En Streamlit Cloud, las variables se leen desde st.secrets.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent  # conprospeccion-os/
_loaded = False


def _load() -> None:
    global _loaded
    if _loaded:
        return
    for candidate in [_ROOT / ".env.local", _ROOT / ".env", _ROOT / ".env.txt"]:
        if candidate.exists():
            load_dotenv(candidate, override=True)
            break
    _loaded = True


def _get(key: str, default: str = "") -> str:
    """Lee una variable: primero st.secrets (Streamlit Cloud), luego os.environ (.env local)."""
    _load()
    try:
        import streamlit as st
        val = st.secrets.get(key)
        if val:
            return str(val)
    except Exception:
        pass
    return os.getenv(key, default)


def supabase_url() -> str:
    return _get("SUPABASE_URL", "https://gdlncvbvhbfjonbnmxfl.supabase.co")


def supabase_key() -> str:
    return _get("SUPABASE_KEY") or _get("SUPABASE_SECRET_KEY")


def ghl_tokens() -> dict[str, str]:
    """Devuelve {cliente_slug: token_GHL}."""
    return {
        "gbs":           _get("GHL_TOKEN_GBS_LOGISTICS"),
        "just4u":        _get("GHL_TOKEN_JUST4U"),
        "clickie":       _get("GHL_TOKEN_CLICKIE"),
        "tiresias":      _get("GHL_TOKEN_TIRESIAS"),
        "ecosmart":      _get("GHL_TOKEN_ECOSMART"),
        "bambutech":     _get("GHL_TOKEN_BAMBUTECH"),
    }


def ghl_location_ids() -> dict[str, str]:
    """Devuelve {cliente_slug: location_id_GHL} — usado por Alicia."""
    return {
        "ecosmart":  _get("GHL_LOCATION_ECOSMART"),
        "clickie":   _get("GHL_LOCATION_CLICKIE"),
        "just4u":    _get("GHL_LOCATION_JUST4U"),
        "tiresias":  _get("GHL_LOCATION_TIRESIAS"),
        "bambutech": _get("GHL_LOCATION_BAMBUTECH"),
        "gbs":       _get("GHL_LOCATION_GBS"),
    }


def anthropic_key() -> str:
    return _get("ANTHROPIC_API_KEY")


def telegram_token() -> str:
    return _get("TELEGRAM_TOKEN")


def telegram_chat_id() -> str:
    return _get("TELEGRAM_CHAT_ID")


def ghl_agency_token() -> str:
    return _get("GHL_AGENCY_TOKEN")


def portal_passwords() -> dict[str, str]:
    """Devuelve {cliente_slug: password} para el portal de clientes.

    `demo` trae fallback en codigo a proposito: es la credencial que se comparte
    con prospectos por correo, no un secreto. La variable de entorno permite
    rotarla sin tocar el codigo.
    """
    return {
        "tiresias": _get("PORTAL_PASSWORD_TIRESIAS"),
        "clickie":  _get("PORTAL_PASSWORD_CLICKIE"),
        "gbs":      _get("PORTAL_PASSWORD_GBS"),
        "bambutech": _get("PORTAL_PASSWORD_BAMBUTECH"),
        "demo":     _get("PORTAL_PASSWORD_DEMO") or "DEMO2026",
    }


def master_passwords() -> dict[str, str]:
    """Devuelve {username: password} para el login master del dashboard interno."""
    return {
        "francisca": _get("MASTER_PASSWORD_FRANCISCA"),
        "yanina":    _get("MASTER_PASSWORD_YANINA"),
    }
