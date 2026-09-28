import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from sdr_reporting.intents import parse_query


NOW = datetime(2026, 9, 28, 15, 0, tzinfo=ZoneInfo("America/Santiago"))


@pytest.mark.parametrize("text,intents", [
    ("¿Cuántos minutos no ha trabajado hasta ahora?", ("time_usage",)),
    ("¿Cuántos correos llegaron, respondió y cuáles faltan?", ("email_summary", "email_pending")),
    ("Llamadas y minutos por cliente de 11 a 12", ("call_counts", "call_minutes")),
    ("¿Cuántas tareas de hoy y atrasadas hay?", ("tasks",)),
    ("Dame el funnel de GBS hoy", ("funnel",)),
    ("Mándame el gráfico", ("chart",)),
])
def test_parse_queries(text, intents):
    assert parse_query(text, now=NOW).intents == intents


def test_interval_and_client_are_extracted():
    request = parse_query("GBS de 12 a 13", now=NOW)
    assert request.client == "gbs"
    assert request.start.hour == 12 and request.end.hour == 13

