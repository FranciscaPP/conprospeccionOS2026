"""Correlación determinística remitente ↔ campaña Snov. SIN IA.

Confirma que el correo entrante proviene de un prospecto real de una campaña de
Snov.io y aporta los metadatos (cliente, campaña, empresa). Se apoya en los datos
que el sync ya deja en Supabase (`snov_email_events`, `snov_campaigns`,
`snov_campaign_map`); no llama a ninguna API en el camino caliente.

Si no hay coincidencia, el mensaje se marca como `unrelated` y no genera alerta:
así la IA jamás ve bandejas completas ni correos ajenos a Snov.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SnovMatch:
    matched: bool
    snov_campaign_id: str | None = None
    cliente_slug: str | None = None
    campaign_name: str | None = None
    prospect_name: str | None = None
    empresa: str | None = None


class SnovLookup:
    """Consulta idempotente de eventos Snov por email de prospecto.

    `store` debe exponer .select(table, columns, **eq_filters) -> list[dict]
    con la semántica de PostgREST (p.ej. prospect_email="eq.foo@bar.com").
    """

    def __init__(self, store: Any):
        self.store = store

    def by_email(self, email: str) -> SnovMatch:
        email = (email or "").strip().lower()
        if not email:
            return SnovMatch(matched=False)
        try:
            events = self.store.select(
                "snov_email_events",
                "snov_campaign_id,cliente_slug,prospect_name,company",
                prospect_email=f"eq.{email}",
                order="occurred_at.desc",
                limit="1",
            )
        except Exception:
            events = []
        if not events:
            return SnovMatch(matched=False)
        event = events[0]
        campaign_id = str(event.get("snov_campaign_id") or "") or None
        cliente_slug = event.get("cliente_slug")
        campaign_name = None
        if campaign_id:
            campaign_name, mapped_cliente = self._campaign_meta(campaign_id)
            cliente_slug = cliente_slug or mapped_cliente
        return SnovMatch(
            matched=True,
            snov_campaign_id=campaign_id,
            cliente_slug=cliente_slug,
            campaign_name=campaign_name,
            prospect_name=event.get("prospect_name"),
            empresa=event.get("company"),
        )

    def _campaign_meta(self, campaign_id: str) -> tuple[str | None, str | None]:
        try:
            rows = self.store.select(
                "snov_campaigns",
                "nombre,cliente_slug",
                snov_campaign_id=f"eq.{campaign_id}",
                limit="1",
            )
        except Exception:
            rows = []
        if not rows:
            return None, None
        row = rows[0]
        return (row.get("nombre") or None), (row.get("cliente_slug") or None)
