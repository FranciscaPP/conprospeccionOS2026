from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from .config import CHILE


@dataclass(frozen=True)
class QueryRequest:
    intents: tuple[str, ...]
    day: date
    start: datetime | None
    end: datetime | None
    client: str | None
    live: bool


def _normal(text: str) -> str:
    return unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()


def parse_query(text: str, now: datetime | None = None) -> QueryRequest:
    now = (now or datetime.now(CHILE)).astimezone(CHILE)
    value = _normal(text)
    intents: list[str] = []

    def add(intent: str) -> None:
        if intent not in intents:
            intents.append(intent)

    if any(word in value for word in ("no ha trabajado", "sin trabajar", "tiempo trabajado", "uso del tiempo")):
        add("time_usage")
    if any(word in value for word in ("correo", "email")):
        add("email_summary")
        if any(word in value for word in ("falta", "pendiente", "cuales")):
            add("email_pending")
    if "llamada" in value:
        add("call_counts")
    if any(word in value for word in ("minuto", "tiempo al telefono", "hablando")) and "no ha trabajado" not in value:
        add("call_minutes")
    if "tarea" in value:
        add("tasks")
    if any(word in value for word in ("funnel", "embudo", "movimiento")):
        add("funnel")
    if "grafico" in value:
        add("chart")
    if any(word in value for word in ("reunion", "reuniones", "agenda")):
        add("meetings")
    if any(word in value for word in ("bloque", "adherencia", "horario")):
        add("adherence")
    if any(word in value for word in ("resumen", "como va", "reporte", "cierre")):
        add("summary")
    if not intents:
        add("menu")

    client = None
    if "bambu" in value:
        client = "bambutech"
    elif "gbs" in value:
        client = "gbs"
    elif "balia" in value or "valia" in value:
        client = "balia"

    day = now.date() - timedelta(days=1) if "ayer" in value else now.date()
    start = end = None
    match = re.search(r"(?:de\s+)?(\d{1,2})(?::(\d{2}))?\s*(?:a|hasta|-)\s*(\d{1,2})(?::(\d{2}))?", value)
    if match:
        sh, sm, eh, em = (int(part or 0) for part in match.groups())
        if 0 <= sh <= 23 and 0 <= eh <= 23 and sm <= 59 and em <= 59:
            start = datetime.combine(day, time(sh, sm), tzinfo=CHILE)
            end = datetime.combine(day, time(eh, em), tzinfo=CHILE)
    return QueryRequest(tuple(intents), day, start, end, client, any(word in value for word in ("ahora", "en vivo")))
