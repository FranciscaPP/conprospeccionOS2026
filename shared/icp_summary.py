"""Construcción reusable del resumen ICP a partir del onboarding de un cliente."""

from __future__ import annotations

import re
from typing import Any


def lista_onboarding(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        raw = [str(item) for item in value]
    else:
        raw = re.split(r"[\n,;|]+", str(value))
    items = []
    for item in raw:
        clean = re.sub(r"\s+", " ", item).strip(" ·-")
        if clean and clean.lower() not in {"n/a", "sin dato", "no informado", "null"}:
            items.append(clean)
    return list(dict.fromkeys(items))


def resumir_tamano(value: Any) -> str:
    items = lista_onboarding(value)
    numbers = []
    has_open_end = False
    for item in items:
        numbers.extend(int(number) for number in re.findall(r"\d+", item))
        has_open_end = has_open_end or "+" in item
    if not numbers:
        return "Tamaño por confirmar"
    minimum = min(numbers)
    maximum = max(numbers)
    if has_open_end:
        return f"{minimum:,} o más empleados".replace(",", ".")
    return f"{minimum:,} a {maximum:,} empleados".replace(",", ".")


def perfil_icp(onboarding: dict[str, Any] | None) -> dict[str, Any]:
    data = onboarding or {}
    paises = lista_onboarding(data.get("icp_pais"))
    industrias = lista_onboarding(data.get("icp_industrias"))
    cargos = lista_onboarding(data.get("icp_cargos"))
    tamanos = lista_onboarding(data.get("icp_tamano"))
    exclusiones = lista_onboarding(data.get("icp_descarte"))
    keywords = lista_onboarding(data.get("keywords_prospecto"))
    complementos = {
        "Criterio adicional": str(data.get("icp_adicional") or "").strip(),
        "Propuesta de valor": str(data.get("propuesta_valor") or "").strip(),
        "Dolores observados": str(data.get("dolores_clientes") or "").strip(),
        "Gatillos de compra": str(data.get("gatillos_compra") or "").strip(),
        "Palabras clave": ", ".join(keywords),
    }
    complementos = {key: value for key, value in complementos.items() if value}
    resumen = " · ".join(
        part
        for part in (
            ", ".join(paises) if paises else "Países por confirmar",
            f"{len(industrias)} industrias" if industrias else "Industrias por confirmar",
            resumir_tamano(tamanos),
            f"{len(cargos)} cargos objetivo" if cargos else "Cargos por confirmar",
        )
        if part
    )
    return {
        "paises": paises,
        "industrias": industrias,
        "cargos": cargos,
        "tamanos": tamanos,
        "tamano_resumido": resumir_tamano(tamanos),
        "exclusiones": exclusiones,
        "complementos": complementos,
        "resumen": resumen,
    }
