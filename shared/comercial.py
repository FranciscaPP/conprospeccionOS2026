"""Logica compartida para el modulo Comercial interno.

Fase 1 usa datos demo y calculos locales. La persistencia Supabase queda para
la Fase 2, manteniendo esta capa como frontera para no acoplar la UI a tablas.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


COMMERCIAL_STATES = [
    "Reunion agendada",
    "Preparacion pendiente",
    "Preparacion lista",
    "Reunion realizada",
    "Diagnostico procesado",
    "Investigacion de mercado",
    "Propuesta en preparacion",
    "Propuesta enviada",
    "En seguimiento",
    "Aceptada",
    "Perdida",
    "Pausada",
]

PROPOSAL_STATES = [
    "Borrador",
    "Version 1",
    "Version 2",
    "Enviada",
    "Reemplazada",
    "Aceptada",
    "Rechazada",
]

FOLLOWUP_STATES = [
    "Pendiente",
    "Borrador listo",
    "Aprobado",
    "Enviado",
    "Respondido",
    "Pausado",
    "Cancelado",
    "Vencido",
]

AI_GENERATION_STATES = [
    "Sin generar",
    "Generado",
    "Editado",
    "Aprobado para presentar",
    "Desactualizado",
]


def money(value: float | int | None, currency: str = "CLP") -> str:
    """Formato monetario compacto para UI."""
    if value is None:
        return "Pendiente"
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "Pendiente"
    symbol = "$" if currency == "CLP" else f"{currency} "
    return f"{symbol}{amount:,.0f}".replace(",", ".")


def pct(value: float | int | None) -> str:
    if value is None:
        return "0%"
    return f"{float(value):.0f}%"


def parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except ValueError:
        return None


def active_proposal(opportunity: dict[str, Any]) -> dict[str, Any] | None:
    proposals = opportunity.get("proposals") or []
    active = [p for p in proposals if p.get("is_current")]
    if active:
        return active[0]
    sent = [p for p in proposals if p.get("status") in {"Enviada", "Aceptada"}]
    return sent[-1] if sent else (proposals[-1] if proposals else None)


def opportunity_amount_label(opportunity: dict[str, Any]) -> str:
    proposal = active_proposal(opportunity)
    if not proposal:
        return "Pendiente"
    monthly = proposal.get("monthly_amount")
    total = proposal.get("total_amount")
    if monthly and total:
        return f"{money(monthly)} / mes · {money(total)} total"
    if monthly:
        return f"{money(monthly)} / mes"
    return "Pendiente"


def calculate_price(
    monthly_fixed_costs: float,
    monthly_variable_costs: float,
    implementation_costs: float,
    expected_margin_pct: float,
    minimum_margin_pct: float,
    contract_months: int,
    setup_amount: float,
    contingency: float,
    discount_pct: float,
    expected_meetings: int,
) -> dict[str, float]:
    """Calcula precio sugerido usando margen bruto real.

    Precio sugerido = costo mensual / (1 - margen esperado)
    """
    monthly_cost = max(0.0, monthly_fixed_costs) + max(0.0, monthly_variable_costs)
    expected_margin = max(0.0, min(float(expected_margin_pct) / 100, 0.95))
    minimum_margin = max(0.0, min(float(minimum_margin_pct) / 100, 0.95))
    months = max(1, int(contract_months or 1))
    discount = max(0.0, min(float(discount_pct) / 100, 0.95))

    suggested_monthly = monthly_cost / (1 - expected_margin) if expected_margin < 1 else 0
    suggested_monthly += max(0.0, contingency)
    final_monthly = suggested_monthly * (1 - discount)
    minimum_monthly = monthly_cost / (1 - minimum_margin) if minimum_margin < 1 else 0
    gross_profit_monthly = final_monthly - monthly_cost
    real_margin = (gross_profit_monthly / final_monthly * 100) if final_monthly else 0
    total_cost_period = monthly_cost * months
    total_project_cost = total_cost_period + max(0.0, implementation_costs)
    total_revenue = final_monthly * months + max(0.0, setup_amount)
    total_profit = total_revenue - total_project_cost
    meetings = max(1, int(expected_meetings or 1))

    return {
        "monthly_fixed_costs": monthly_fixed_costs,
        "monthly_variable_costs": monthly_variable_costs,
        "monthly_cost": monthly_cost,
        "period_cost": total_cost_period,
        "implementation_costs": implementation_costs,
        "total_project_cost": total_project_cost,
        "suggested_monthly": suggested_monthly,
        "final_monthly": final_monthly,
        "minimum_monthly": minimum_monthly,
        "gross_profit_monthly": gross_profit_monthly,
        "real_margin": real_margin,
        "total_profit": total_profit,
        "break_even": monthly_cost,
        "cost_per_meeting": monthly_cost / meetings,
        "revenue_per_meeting": final_monthly / meetings,
        "total_revenue": total_revenue,
    }


def scenario_prices(monthly_cost: float) -> list[dict[str, float | str]]:
    scenarios = [("Conservador", 30), ("Recomendado", 40), ("Premium", 50)]
    rows = []
    for name, margin in scenarios:
        price = monthly_cost / (1 - margin / 100) if margin < 100 else 0
        rows.append(
            {
                "Escenario": name,
                "Margen": f"{margin}%",
                "Precio sugerido mensual": price,
                "Utilidad bruta mensual": price - monthly_cost,
            }
        )
    return rows


@dataclass(frozen=True)
class CommercialSettings:
    currency: str = "CLP"
    default_margin_pct: int = 40
    minimum_margin_pct: int = 30
    default_contract_months: int = 5
    institutional_pdf_url: str = "https://conprospeccion.com"
    onboarding_url: str = "https://conprospeccion.com"
    playbook_url: str = "https://conprospeccion.com"
    intelligence_url: str = "https://conprospeccion.com"
    sample_database_url: str = "https://conprospeccion.com"
    briefing_url: str = "https://conprospeccion.com"
