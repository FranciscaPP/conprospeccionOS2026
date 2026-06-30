"""Contratos del portal cliente de validación de reuniones."""
from pathlib import Path

from dashboard.meeting_shared import project_meeting_for_client


def test_project_meeting_for_client_solo_evidencia_visible():
    meeting = {
        "id": 1,
        "company": "Medizintechnik",
        "evidence": [
            {"type": "Grabación", "name": "Abrir grabación", "url": "https://example.com/rec", "clientVisible": True},
            {"type": "Transcripción", "name": "Abrir transcripción", "url": "https://example.com/tr", "clientVisible": False},
            {"type": "Resumen IA", "name": "Resumen", "text": "Resumen visible", "clientVisible": True},
        ],
        "sdr": "Mariana",
        "notes": "interno",
    }
    out = project_meeting_for_client(meeting)
    types = [e["type"] for e in out["evidence"]]
    assert types == ["Grabación", "Resumen IA"]
    assert "sdr" not in out
    assert "notes" not in out


def test_portal_gbs_muestra_evidencias_en_evaluacion_cp():
    html = Path("dashboard/client_meeting_portal/index.html").read_text(encoding="utf-8")
    assert "Evidencias y archivos" in html
    assert "evidenceTab(m)" in html
    assert "evidenceBlock" in html
