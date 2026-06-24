"""Tests del motor contractual de validacion de reuniones."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.validacion import (
    ESTADOS_FLUJO,
    KPI_GBS,
    acciones_cliente_permitidas,
    bant_list,
    bant_desde_fuentes,
    derivar_estado_flujo,
    derivar_final,
    flag_disputa,
    flag_meta_countable,
    gate_valida_permitida,
    icp_gbs,
    informacion_reunion,
    texto_real,
)
from shared.seguimiento import (
    payload_antecedentes_internos,
    payload_respuesta_cliente,
    recalcular_final_y_flags,
    registrar_historial,
)


def test_cp_valida_cliente_pendiente():
    assert derivar_final("realizada", "valida", "espera", "B,A", evidencia_suficiente=True) == "pendiente"


def test_cp_valida_cliente_confirma():
    assert derivar_final("realizada", "valida", "valida", "") == "valida"


def test_cliente_no_puede_saltar_cp():
    assert derivar_final("agendada", "espera", "valida", "") == "pendiente"
    assert derivar_final("realizada", "no_valida", "valida", "B,A") == "no_valida"


def test_estados_operativos_no_cierran_negativo_automaticamente():
    assert derivar_final("no_asistio_lead", "valida", "espera", "B,A") == "pendiente"
    assert derivar_final("cancelada_cliente", "valida", "espera", "B,A") == "pendiente"
    assert derivar_final("reagendada", "valida", "espera", "B,A") == "pendiente"


def test_bant_y_evidencia_no_resuelven_resultado_negativo():
    assert derivar_final("realizada", "valida", "valida", "B", evidencia_suficiente=True) == "valida"
    assert derivar_final("realizada", "valida", "valida", "B,A", evidencia_suficiente=False) == "valida"


def test_icp_faltante_no_invalida_y_gbs_cumple_salvo_cancelada():
    assert derivar_final("realizada", "valida", "espera", "") == "pendiente"
    assert icp_gbs("realizada", None) is True
    assert icp_gbs("cancelada_cliente", None) is False


def test_solicitud_revision_queda_pendiente():
    assert derivar_final("realizada", "valida", "requiere_revision", "B,A") == "pendiente"
    assert flag_disputa("valida", "requiere_revision", "B,A") is True
    assert flag_meta_countable("pendiente") is False


def test_revision_no_descuenta_valida_ya_contabilizada():
    assert (
        derivar_final(
            "realizada",
            "valida",
            "requiere_revision",
            "B,A",
            resultado_actual="valida",
        )
        == "valida"
    )


def test_valores_cliente_legacy_se_proyectan_como_revision_sin_cierre_negativo():
    assert derivar_final("realizada", "valida", "no_valida", "B,A") == "pendiente"
    assert derivar_final("realizada", "valida", "reagendada", "B,A") == "pendiente"
    assert (
        derivar_estado_flujo(
            "2026-01-01",
            "realizada",
            "valida",
            "reagendada",
            "pendiente",
        )
        == "cliente_solicita_revision"
    )


def test_override_manda():
    assert derivar_final("no_asistio_lead", "no_valida", "no_valida", "", override="valida") == "valida"
    assert derivar_final("agendada", "espera", "valida", "", override="excluida") == "excluida"


def test_meta_countable():
    assert flag_meta_countable("valida") is True
    assert flag_meta_countable("en_disputa") is False
    assert flag_meta_countable("pendiente") is False
    assert flag_meta_countable("no_valida") is False


def test_gate_informativo():
    assert gate_valida_permitida("realizada") is True
    assert gate_valida_permitida("agendada") is False


def test_bant_list():
    assert bant_list("B,A,x,T") == ["B", "A", "T"]
    assert bant_list("") == []
    assert bant_list(["b", "a"]) == ["B", "A"]
    assert bant_list("Budget; Authority; Need") == ["B", "A", "N"]


def test_siete_estados_oficiales_sin_reagendamiento_cliente():
    assert ESTADOS_FLUJO == [
        "reunion_futura",
        "reunion_cancelada",
        "pendiente_evaluacion_cp",
        "pendiente_evaluacion_cliente",
        "cliente_solicita_revision",
        "evaluacion_cerrada_valida",
        "evaluacion_cerrada_no_valida",
    ]


def test_payload_cliente_solo_escribe_campos_autorizados():
    payload = payload_respuesta_cliente(123, "gbs", "valida")
    campos_prohibidos = {
        "status_reunion",
        "val_estado_cp",
        "bant_cp",
        "recording_url",
        "transcript_url",
        "ai_summary",
        "ai_evidence",
        "val_estado_final",
        "final_override",
    }
    assert campos_prohibidos.isdisjoint(payload)
    assert payload["val_estado_cli"] == "valida"


def test_futuro_no_tiene_acciones_cliente():
    assert acciones_cliente_permitidas("reunion_futura", "valida", "espera") == ()
    assert acciones_cliente_permitidas(
        "pendiente_evaluacion_cliente",
        "valida",
        "espera",
    ) == ("confirmar", "solicitar_revision")


def test_kpi_gbs_definitivos():
    assert KPI_GBS == ("total", "validas", "no_validas", "avance_meta")
    portal = Path("dashboard/pages/12_GBS_Validacion_Reuniones.py").read_text(encoding="utf-8")
    for label in ("Total reuniones", "Válidas", "No válidas", "Avance meta"):
        assert label in portal
    assert '"pending_client": "Pendiente validación cliente"' not in portal
    assert '"dispute": "En disputa"' not in portal


def test_campos_vacios_no_producen_texto_visible():
    for value in (None, "", "N/A", "Sin dato", "No disponible", "null", "—"):
        assert texto_real(value) == ""
    portal = Path("dashboard/pages/12_GBS_Validacion_Reuniones.py").read_text(encoding="utf-8")
    assert 'if not clean:\n        return ""' in portal


def test_informacion_reunion_prioriza_edicion_manual_y_raw_data():
    row = {
        "informacion_reunion": "Sincronizada",
        "raw_data": {
            "contact": {
                "customFields": [
                    {
                        "key": "informacion_de_preparacion_para_la_reunion",
                        "value": "Desde GHL",
                    }
                ]
            }
        },
    }
    assert informacion_reunion(row, {}) == "Sincronizada"
    assert informacion_reunion(row, {"informacion_reunion_manual": "Manual"}) == "Manual"


def test_bant_puede_venir_de_ghl_o_completarse_internamente():
    row = {"bant_sdr": "Budget, Authority"}
    assert bant_desde_fuentes(row, {}) == ["B", "A"]
    assert bant_desde_fuentes(row, {"bant_cp": "N,T"}) == ["N", "T"]
    payload = payload_antecedentes_internos(
        informacion="Preparación manual",
        bant=["B", "N"],
        icp_cumple=True,
    )
    assert payload == {
        "informacion_reunion_manual": "Preparación manual",
        "bant_cp": "B,N",
        "icp_cumple": True,
    }


def test_portal_y_seguimiento_dependen_de_la_misma_derivacion_de_estado():
    portal = Path("dashboard/pages/12_GBS_Validacion_Reuniones.py").read_text(encoding="utf-8")
    interno = Path("dashboard/pages/1_Seguimiento_Reuniones.py").read_text(encoding="utf-8")
    assert "derivar_estado_flujo(" in portal
    assert "derivar_estado_flujo(" in interno


def test_payload_revision_exige_motivo_y_comentario():
    for motivo, comentario in ((None, "detalle"), ("otro_contractual", "")):
        try:
            payload_respuesta_cliente(
                123,
                "gbs",
                "requiere_revision",
                motivo=motivo,
                comentario=comentario,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("La revisión incompleta debió ser rechazada")


def test_cliente_no_puede_rechazar_guardar_no_valida_ni_reagendada():
    for estado in ("rechazar", "no_valida", "reagendada"):
        try:
            payload_respuesta_cliente(123, "gbs", estado)
        except ValueError:
            pass
        else:
            raise AssertionError(f"El estado cliente {estado} debió ser rechazado")


def test_recalculo_persiste_final_y_kpi_con_fila_recien_guardada():
    row = {
        "status_reunion": "realizada",
        "val_estado_cp": "valida",
        "val_estado_cli": "valida",
        "bant_cp": "B,A",
        "comentario_cp": "Evidencia revisada",
    }
    response = Mock(ok=True)
    with patch("shared.seguimiento.requests.post", return_value=response) as post:
        result = recalcular_final_y_flags(123, "gbs", fila=row)
    payload = post.call_args.kwargs["json"]
    assert result["persisted"] is True
    assert result["final"] == "valida"
    assert payload["val_estado_final"] == "valida"
    assert payload["flag_meta_countable"] is True
    assert payload["flag_cliente_pendiente"] is False


def test_recalculo_acepta_evidencia_de_la_reunion_base():
    row = {
        "status_reunion": "realizada",
        "val_estado_cp": "valida",
        "val_estado_cli": "valida",
        "bant_cp": "B,A",
    }
    with patch("shared.seguimiento.requests.post", return_value=Mock(ok=True)):
        result = recalcular_final_y_flags(
            123,
            "gbs",
            fila=row,
            evidencia_suficiente=True,
        )
    assert result["final"] == "valida"
    assert result["countable"] is True


def test_recalculo_revision_queda_pendiente_sin_cierre_negativo():
    row = {
        "status_reunion": "realizada",
        "val_estado_cp": "valida",
        "val_estado_cli": "requiere_revision",
        "bant_cp": "B,A",
    }
    with patch("shared.seguimiento.requests.post", return_value=Mock(ok=True)):
        result = recalcular_final_y_flags(123, "gbs", fila=row)
    assert result["final"] == "pendiente"
    assert result["disputa"] is True
    assert result["countable"] is False


def test_recalculo_revision_preserva_valida_ya_contabilizada():
    row = {
        "status_reunion": "realizada",
        "val_estado_cp": "valida",
        "val_estado_cli": "requiere_revision",
        "val_estado_final": "valida",
        "bant_cp": "B,A",
    }
    with patch("shared.seguimiento.requests.post", return_value=Mock(ok=True)):
        result = recalcular_final_y_flags(123, "gbs", fila=row)
    assert result["final"] == "valida"
    assert result["disputa"] is True
    assert result["countable"] is True


def test_historial_reporta_si_supabase_rechaza_el_registro():
    with patch("shared.seguimiento.requests.post", return_value=Mock(ok=False)):
        assert registrar_historial(123, "val_estado_cli", "espera", "valida", "cliente", "cliente", "gbs") is False


if __name__ == "__main__":
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("test_") and callable(value)
    ]
    for test in tests:
        test()
    print("OK validacion")
