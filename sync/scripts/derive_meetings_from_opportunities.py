from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from typing import Any

from config import get_settings
from supabase_rest import SupabaseRestClient


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Deriva reuniones desde oportunidades en stages de reunion.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    setup_logging()
    settings = get_settings()
    supabase = SupabaseRestClient(settings.supabase_url, settings.supabase_secret_key)

    stages = supabase.select_all("ghl_pipeline_stages", "cliente_slug,pipeline_id,stage_id,pipeline_name,stage_name,stage_category,is_meeting_stage,is_valid_meeting")
    stage_by_key = {(s["cliente_slug"], s["pipeline_id"], s["stage_id"]): s for s in stages}

    opportunities = supabase.select_all(
        "oportunidades",
        "ghl_opportunity_id,ghl_contact_id,cliente_slug,location_id,sdr_slug,ghl_owner_user_id,nombre,pipeline_id,pipeline_stage_id,estado,contacto_nombre,contacto_empresa,contacto_email,contacto_telefono,ghl_created_at,last_stage_change_at,raw_data",
    )

    opp_updates = []
    meeting_rows = []
    for opp in opportunities:
        stage = stage_by_key.get((opp.get("cliente_slug"), opp.get("pipeline_id"), opp.get("pipeline_stage_id")))
        if not stage:
            continue

        opp_updates.append(
            {
                "ghl_opportunity_id": opp["ghl_opportunity_id"],
                "pipeline_name": stage.get("pipeline_name"),
                "pipeline_stage_name": stage.get("stage_name"),
                "stage_category": stage.get("stage_category"),
                "is_meeting_stage": stage.get("is_meeting_stage") or False,
                "is_valid_meeting": stage.get("is_valid_meeting"),
            }
        )

        if not stage.get("is_meeting_stage"):
            continue

        stage_dt = parse_dt(opp.get("last_stage_change_at")) or parse_dt(opp.get("ghl_created_at"))
        created_dt = parse_dt(opp.get("ghl_created_at"))
        meeting_rows.append(
            {
                "ghl_appointment_id": f"opportunity:{opp['ghl_opportunity_id']}",
                "opportunity_id": opp["ghl_opportunity_id"],
                "origen_reunion": "oportunidad_pipeline",
                "fecha_reunion_estimada": True,
                "cliente_slug": opp.get("cliente_slug"),
                "sdr_slug": opp.get("sdr_slug"),
                "ghl_contact_id": opp.get("ghl_contact_id"),
                "ghl_owner_user_id": opp.get("ghl_owner_user_id"),
                "location_id": opp.get("location_id"),
                "titulo": opp.get("nombre"),
                "empresa": opp.get("contacto_empresa"),
                "contacto": opp.get("contacto_nombre"),
                "telefono": opp.get("contacto_telefono"),
                "email": opp.get("contacto_email"),
                "fecha_agendada": created_dt.date().isoformat() if created_dt else None,
                "fecha_reunion": stage_dt.date().isoformat() if stage_dt else None,
                "hora_reunion": stage_dt.time().replace(tzinfo=None).isoformat() if stage_dt else None,
                "starts_at": opp.get("last_stage_change_at") or opp.get("ghl_created_at"),
                "estado_reunion": stage.get("stage_name"),
                "es_valida": stage.get("is_valid_meeting"),
                "observacion": "Reunion inferida desde etapa de oportunidad GHL.",
                "raw_data": opp.get("raw_data") or {},
                "synced_at": iso_now(),
            }
        )

    logging.info("Oportunidades enriquecidas: %s", len(opp_updates))
    logging.info("Reuniones derivadas: %s", len(meeting_rows))

    if not args.dry_run:
        for index in range(0, len(opp_updates), 100):
            supabase.upsert("oportunidades", opp_updates[index : index + 100], "ghl_opportunity_id")
        for index in range(0, len(meeting_rows), 100):
            supabase.upsert("reuniones", meeting_rows[index : index + 100], "ghl_appointment_id")
        supabase.insert(
            "sync_runs",
            {
                "source": "supabase",
                "entity": "derived_meetings",
                "status": "success",
                "stats": {"opportunities_updated": len(opp_updates), "meetings_derived": len(meeting_rows)},
                "errors": [],
            },
        )


if __name__ == "__main__":
    main()
