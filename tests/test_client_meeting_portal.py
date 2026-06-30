"""Contratos del portal cliente de validación de reuniones."""
from pathlib import Path

from dashboard.meeting_shared import (
    _apply_evidence_visibility,
    _build_client_history,
    _normalize_cancelled_meeting,
    project_meeting_for_client,
)


def test_build_client_history_respeta_visibilidad_desde_auditoria():
    meeting = {
        "cp": "Válida",
        "clientVal": "Pendiente",
        "final": "Reunión válida",
        "status": "Reunión realizada",
        "date": "30/06/2026",
        "time": "11:00 AM",
        "historyVisibility": {},
        "history": [
            {
                "when": "2026-06-30 18:37",
                "user": "Francisca / Yanina",
                "field": "Visibilidad historial",
                "to": "fecha_realizada: Visible para cliente",
            },
            {
                "when": "2026-06-30 20:09",
                "user": "CP",
                "field": "role",
                "to": "role guardado desde panel interno",
            },
        ],
    }
    out = project_meeting_for_client(meeting)
    fields = [item["field"] for item in out["history"]]
    assert "role" not in fields
    assert "Visibilidad historial" not in fields
    assert "guardado desde panel interno" not in " ".join(item["text"] for item in out["history"])
    assert "Reunión realizada" in fields


def test_cancelled_meeting_no_muestra_no_valida_cp():
    cp, client_val, final = _normalize_cancelled_meeting(
        "Reunión cancelada",
        "No válida",
        "Pendiente",
        "Pendiente",
    )
    assert cp == "No necesaria"
    assert client_val == "No necesaria"
    assert final == "Reunión cancelada"

    meeting = {
        "status": "Reunión cancelada",
        "cp": "No válida",
        "clientVal": "Pendiente",
        "final": "Pendiente",
        "historyVisibility": {},
        "history": [],
    }
    out = project_meeting_for_client(meeting)
    assert out["cp"] == "No necesaria"
    assert out["final"] == "Reunión cancelada"
    history_fields = [item["field"] for item in out["history"]]
    assert "No válida" not in history_fields


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
