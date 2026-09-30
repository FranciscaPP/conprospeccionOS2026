"""Registro de cuentas de correo monitoreadas.

Escala a 25+ cuentas sin lógica duplicada: el pipeline itera uniformemente sobre
las cuentas habilitadas. Habilitar una cuenta nueva es SOLO configuración
(una fila en la tabla `alicia_accounts` o una entrada en ALICIA_ACCOUNTS_JSON),
más su refresh token en Secrets bajo el nombre indicado por `token_env`.

Ningún secreto vive aquí: `token_env` es el NOMBRE de la variable de entorno.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from alicia import settings


@dataclass(frozen=True)
class Account:
    account_id: str
    email: str
    enabled: bool
    token_env: str
    cliente_slug: str | None = None
    notas: str | None = None

    def refresh_token(self) -> str:
        return settings.refresh_token_for(self.token_env)


def _coerce(row: dict[str, Any]) -> Account | None:
    account_id = str(row.get("account_id") or "").strip()
    email = str(row.get("email") or "").strip()
    token_env = str(row.get("token_env") or "").strip()
    if not account_id or not email:
        return None
    return Account(
        account_id=account_id,
        email=email,
        enabled=bool(row.get("enabled", False)),
        token_env=token_env or f"GMAIL_REFRESH_TOKEN_{account_id.upper()}",
        cliente_slug=(str(row["cliente_slug"]).strip() or None) if row.get("cliente_slug") else None,
        notas=(str(row["notas"]).strip() or None) if row.get("notas") else None,
    )


def from_json(raw: str) -> list[Account]:
    if not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    accounts = [_coerce(row) for row in data if isinstance(row, dict)]
    return [a for a in accounts if a is not None]


def from_supabase(store: Any) -> list[Account]:
    """`store` debe exponer .select(table, columns, **filters) -> list[dict]."""
    try:
        rows = store.select(
            "alicia_accounts",
            "account_id,email,enabled,token_env,cliente_slug,notas",
        )
    except Exception:
        return []
    accounts = [_coerce(row) for row in rows if isinstance(row, dict)]
    return [a for a in accounts if a is not None]


def load_accounts(store: Any | None = None, *, only_enabled: bool = True) -> list[Account]:
    """Carga cuentas: primero la tabla Supabase (si hay store), luego el JSON.

    El JSON de entorno complementa/rellena cuando la tabla no está disponible
    (útil para el piloto de una sola cuenta antes de poblar la tabla).
    """
    accounts: dict[str, Account] = {}
    if store is not None:
        for account in from_supabase(store):
            accounts[account.account_id] = account
    if not accounts:
        for account in from_json(settings.accounts_json()):
            accounts.setdefault(account.account_id, account)
    result = list(accounts.values())
    if only_enabled:
        result = [a for a in result if a.enabled]
    result.sort(key=lambda a: a.account_id)
    return result


def internal_ref(thread_id: str) -> str:
    """Identificador interno estable y determinístico a partir del threadId."""
    digest = hashlib.sha256(thread_id.encode("utf-8")).hexdigest()
    return "AL-" + digest[:8].upper()
