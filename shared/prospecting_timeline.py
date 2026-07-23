"""Contexto operativo de prospeccion por cliente."""
from __future__ import annotations

from datetime import date
from math import ceil


def calendar_days(start: str | date, end: str | date) -> int:
    """Dias calendario inclusivos entre dos fechas."""
    start_date = _to_date(start)
    end_date = _to_date(end)
    if end_date < start_date:
        raise ValueError("end must be greater than or equal to start")
    return (end_date - start_date).days + 1


def business_days(start: str | date, end: str | date) -> int:
    """Dias habiles lunes-viernes, inclusivos."""
    start_date = _to_date(start)
    end_date = _to_date(end)
    if end_date < start_date:
        raise ValueError("end must be greater than or equal to start")
    return sum(
        1
        for offset in range((end_date - start_date).days + 1)
        if date.fromordinal(start_date.toordinal() + offset).weekday() < 5
    )


def proportional_valid_range(
    *,
    active_days: int,
    standard_period_days: int,
    monthly_min: int,
    monthly_max: int,
) -> dict[str, int]:
    """Referencia proporcional de reuniones validas al corte."""
    if active_days < 0 or standard_period_days <= 0 or monthly_min < 0 or monthly_max < monthly_min:
        raise ValueError("invalid proportional range inputs")
    return {
        "min": ceil(monthly_min * active_days / standard_period_days),
        "max": ceil(monthly_max * active_days / standard_period_days),
    }


def build_timeline_config(config: dict) -> dict:
    """Agrega calculos derivados a una configuracion de timeline."""
    segments = []
    active_calendar_days = 0
    pause_calendar_days = 0
    for segment in config["segments"]:
        calculated = {
            **segment,
            "calendarDays": calendar_days(segment["start"], segment["end"]),
            "businessDays": business_days(segment["start"], segment["end"]),
        }
        if segment.get("type") == "pause":
            pause_calendar_days += calculated["calendarDays"]
        else:
            active_calendar_days += calculated["calendarDays"]
        segments.append(calculated)

    rhythm = dict(config["rhythm"])
    rhythm["proportionalRange"] = proportional_valid_range(
        active_days=int(rhythm["activeDays"]),
        standard_period_days=int(rhythm["standardPeriodDays"]),
        monthly_min=int(rhythm["monthlyReferenceMin"]),
        monthly_max=int(rhythm["monthlyReferenceMax"]),
    )
    return {
        **config,
        "segments": segments,
        "summary": {
            **config["summary"],
            "activeCalendarDays": active_calendar_days,
            "pauseCalendarDays": pause_calendar_days,
        },
        "rhythm": rhythm,
    }


def prospecting_timeline_for_client(client_slug: str) -> dict | None:
    config = _TIMELINE_CONFIGS.get((client_slug or "").lower())
    if not config:
        return None
    return build_timeline_config(config)


def _to_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


_TIMELINE_CONFIGS = {
    "bambutech": {
        "component": "ProspectingTimeline",
        "title": "Contexto operativo de la prospección",
        "subtitle": "Períodos efectivos de actividad, pausas y resultados acumulados.",
        "badge": "Corte al 23/07/2026",
        "milestones": [
            {
                "date": "18/05/2026",
                "title": "Inicio de prospección",
                "subtitle": "Etapa inicial de estrategia y activación comercial",
            },
            {
                "date": "16/06/2026",
                "title": "Pausa operativa",
                "subtitle": "Pausa por pago pendiente",
            },
            {
                "date": "07/07/2026",
                "title": "Reactivación",
                "subtitle": "Reinicio de campañas y prospección",
            },
            {
                "date": "23/07/2026",
                "title": "Corte actual",
                "subtitle": "Estado considerado para los indicadores",
            },
        ],
        "segments": [
            {
                "type": "active",
                "start": "2026-05-18",
                "end": "2026-06-15",
                "label": "Tramo activo inicial",
                "metrics": ["5 reuniones", "3 válidas", "1 no válida", "1 por reagendar"],
            },
            {
                "type": "pause",
                "start": "2026-06-16",
                "end": "2026-07-06",
                "label": "Pausa operativa",
                "metrics": ["Las campanas no estuvieron activas."],
                "note": (
                    "Durante la pausa se realizó el 21/06 una reunión que había sido "
                    "agendada previamente. La reunión fue validada."
                ),
            },
            {
                "type": "active",
                "start": "2026-07-07",
                "end": "2026-07-23",
                "label": "Reactivacion",
                "metrics": [
                    "4 reuniones agendadas",
                    "2 válidas",
                    "1 en revisión del cliente",
                    "1 futura, programada para el 24/07",
                ],
            },
        ],
        "summary": {
            "meetings": 10,
            "validMeetings": 6,
            "validationRate": "60%",
        },
        "rhythm": {
            "title": "Ritmo proporcional desde la reactivación",
            "monthlyReferenceMin": 10,
            "monthlyReferenceMax": 12,
            "standardPeriodDays": 30,
            "activeDays": 17,
            "confirmedSinceReactivation": 2,
            "openOpportunities": 2,
            "potentialPipeline": 4,
            "tooltip": (
                "El cálculo utiliza 17 días efectivos de actividad sobre un período "
                "estándar de 30 días y una referencia operativa mensual de 10 a 12 "
                "reuniones válidas."
            ),
        },
    }
}
