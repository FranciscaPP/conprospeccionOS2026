"""Contratos del portal cliente de validación de reuniones."""
from pathlib import Path

from dashboard.meeting_shared import (
    _apply_evidence_visibility,
    _build_client_history,
    project_meeting_for_client,
)


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


def test_project_meeting_for_client_filtra_urls_por_visibilidad():
    meeting = {
        "id": 2,
        "recordingUrl": "https://example.com/rec",
        "transcriptUrl": "https://example.com/tr",
        "evidence": [
            {"type": "Grabación", "url": "https://example.com/rec", "clientVisible": True},
            {"type": "Transcripción", "url": "https://example.com/tr", "clientVisible": False},
        ],
    }
    out = project_meeting_for_client(meeting)
    assert out.get("recordingUrl") == "https://example.com/rec"
    assert "transcriptUrl" not in out


def test_apply_evidence_visibility_acepta_claves_sin_acento():
    evidence = [{"type": "Transcripción", "url": "https://example.com/tr"}]
    visibility = {"Transcripcion": True}
    out = _apply_evidence_visibility(evidence, visibility, [])
    assert out[0]["clientVisible"] is True


def test_apply_evidence_visibility_desde_historial_toggle():
    evidence = [
        {"type": "Grabación", "url": "https://example.com/rec"},
        {"type": "Transcripción", "url": "https://example.com/tr"},
    ]
    history = [
        {
            "field": "Visibilidad evidencia",
            "from": "Grabación",
            "to": "Visible para cliente",
        }
    ]
    out = _apply_evidence_visibility(evidence, {}, history)
    assert out[0]["clientVisible"] is True
    assert out[1]["clientVisible"] is False


def test_build_client_history_oculta_auditoria_interna():
    meeting = {
        "cp": "Válida",
        "clientVal": "Pendiente",
        "final": "Pendiente",
        "status": "Reunión realizada",
        "date": "30/06/2026",
        "time": "11:00 AM",
        "historyVisibility": {},
        "history": [
            {"when": "2026-06-30 20:11", "user": "cliente", "field": "val_estado_cli", "to": "valida"},
            {"when": "2026-06-30 20:09", "user": "CP", "field": "BANT", "to": "B,A"},
        ],
    }
    items = _build_client_history(meeting)
    fields = [item["field"] for item in items]
    assert "val_estado_cli" not in fields
    assert "BANT" not in fields
    assert "Evaluación Conprospección" in fields


def test_project_meeting_for_client_reemplaza_historial():
    meeting = {
        "id": 3,
        "cp": "Válida",
        "clientVal": "Pendiente",
        "final": "Pendiente",
        "status": "Reunión realizada",
        "historyVisibility": {},
        "history": [
            {"when": "2026-06-30 20:09", "user": "CP", "field": "ICP", "to": "Cumple"},
        ],
    }
    out = project_meeting_for_client(meeting)
    assert all(item["field"] != "ICP" for item in out["history"])


def test_portal_gbs_muestra_evidencias_y_evaluacion_cliente():
    html = Path("dashboard/client_meeting_portal/index.html").read_text(encoding="utf-8")
    assert "Evidencias y archivos" in html
    assert "evidenceTab(m)" in html
    assert "Abrir grabación" in html
    assert "LinkedIn empresa" in html
    assert "Solicitar revisión" in html
    assert "Motivo</label>" not in html
