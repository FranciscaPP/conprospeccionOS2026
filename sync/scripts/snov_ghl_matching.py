from __future__ import annotations

import unicodedata
from typing import Any


def normalize_name(name: str | None) -> str:
    if not name:
        return ""
    stripped = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return " ".join(stripped.lower().split())


def names_match(snov_name: str | None, ghl_first_name: str | None, ghl_last_name: str | None) -> bool:
    """True si no hay choque de identidad: no hay suficiente informacion para
    comparar, o los nombres comparten al menos un token (nombre o apellido)."""
    ghl_name = " ".join(part for part in [ghl_first_name, ghl_last_name] if part)
    ghl_norm = normalize_name(ghl_name)
    snov_norm = normalize_name(snov_name)
    if not ghl_norm or not snov_norm:
        return True
    return bool(set(snov_norm.split()) & set(ghl_norm.split()))
