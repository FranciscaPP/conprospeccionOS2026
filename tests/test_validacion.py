"""Tests del motor contractual de validacion de reuniones."""

import sys
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.validacion import (
    ESTATUS_VALIDACION,
    ESTADOS_FLUJO,
    ETAPAS_AGENDA,
    LABEL_ESTATUS_VALIDACION,
    LABEL_ESTADO_FLUJO,
    KPI_GBS,
    MOTIVO_NO_VALIDEZ,
    acciones_cliente_permitidas,
    bant_list,
    bant_desde_fuentes,
    derivar_estatus_validacion,
    derivar_estado_flujo,
    derivar_etapa_agenda,
    derivar_final,
    flag_disputa,
    flag_meta_countable,
    gate_valida_permitida,
    icp_gbs,
    informacion_reunion,
    texto_real,
)
from shared.icp_summary import lista_onboarding, perfil_icp, resumir_tamano
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


def test_fecha_vacia_no_rompe_proyeccion_del_flujo():
    import pandas as pd

    assert (
        derivar_estado_flujo(
            pd.NaT,
            None,
            None,
            None,
            None,
            hoy=date(2026, 1, 11),
        )
        == "pendiente_evaluacion_cp"
    )


def test_helpers_aceptan_fila_pandas_del_portal():
    import pandas as pd

    row = pd.Series(
        {
            "informacion_reunion": "Preparar tarifas de importación.",
            "bant_sdr": "B,N",
            "raw_data": {},
        }
    )
    assert informacion_reunion(row, {}) == "Preparar tarifas de importación."
    assert bant_desde_fuentes(row, {}) == ["B", "N"]


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


def test_agenda_y_validacion_son_dimensiones_independientes():
    etapa = derivar_etapa_agenda(
        "2026-06-26",
        "agendada",
        hoy=date(2026, 6, 18),
    )
    assert etapa == "reunion_futura"
    assert (
        derivar_estatus_validacion(
            etapa,
            "valida",
            "espera",
            "pendiente",
        )
        == "validada_por_cp"
    )


def test_futura_validada_cp_no_espera_confirmacion_cliente():
    assert (
        derivar_estatus_validacion(
            "reunion_futura",
            "valida",
            "espera",
            "pendiente",
        )
        != "pendiente_confirmacion_cliente"
    )


def test_cancelacion_o_exclusion_no_cierran_validacion_negativa():
    assert (
        derivar_estatus_validacion(
            "reunion_cancelada",
            "espera",
            "espera",
            "excluida",
        )
        == "reunion_cancelada"
    )
    assert (
        derivar_estatus_validacion(
            "reunion_cancelada",
            "no_valida",
            "espera",
            "no_valida",
        )
        == "reunion_cancelada"
    )


def test_estatus_validacion_oficiales_del_portal():
    assert ETAPAS_AGENDA == [
        "reunion_futura",
        "reunion_agendada",
        "reunion_realizada",
        "cotizacion",
        "reagendar",
        "reunion_cancelada",
    ]
    assert ESTATUS_VALIDACION == [
        "pendiente_evaluacion_cp",
        "validada_por_cp",
        "rechazada_por_cp",
        "pendiente_confirmacion_cliente",
        "cliente_solicita_revision",
        "cotizacion_valida",
        "reagendar",
        "reunion_cancelada",
        "evaluacion_cerrada_valida",
        "evaluacion_cerrada_no_valida",
    ]


def test_cotizacion_es_etapa_valida_automatica():
    etapa = derivar_etapa_agenda(
        "2026-06-16",
        "cotizacion",
        hoy=date(2026, 6, 18),
    )
    assert etapa == "cotizacion"
    assert (
        derivar_estatus_validacion(
            etapa,
            "espera",
            "espera",
            "pendiente",
        )
        == "cotizacion_valida"
    )
    assert derivar_final("cotizacion", "espera", "espera", "") == "valida"


def test_interfaz_no_abrevia_conprospeccion_como_cp():
    assert (
        LABEL_ESTATUS_VALIDACION["pendiente_evaluacion_cp"]
        == "Pendiente evaluación Conprospección"
    )
    assert (
        LABEL_ESTADO_FLUJO["pendiente_evaluacion_cp"]
        == "Pendiente de evaluación Conprospección"
    )
    assert all(
        " CP" not in label and not label.endswith("CP")
        for label in (
            *LABEL_ESTATUS_VALIDACION.values(),
            *LABEL_ESTADO_FLUJO.values(),
        )
    )


def test_estados_no_realizados_se_agrupan_como_reagendar():
    for status in (
        "no_asistio_lead",
        "no_asistio_cliente",
        "reagendada",
        "pendiente_reagendar",
    ):
        etapa = derivar_etapa_agenda(
            "2026-06-01",
            status,
            hoy=date(2026, 6, 18),
        )
        assert etapa == "reagendar"
        assert (
            derivar_estatus_validacion(
                etapa,
                "valida",
                "espera",
                "pendiente",
            )
            == "reagendar"
        )


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
        "pendiente_evaluacion_cp",
        "espera",
        "espera",
    ) == ("confirmar", "solicitar_revision")
    assert acciones_cliente_permitidas(
        "pendiente_evaluacion_cliente",
        "valida",
        "espera",
    ) == ("confirmar", "solicitar_revision")


def test_respuesta_cliente_anticipada_sigue_pendiente_cp():
    assert (
        derivar_estado_flujo(
            "2026-01-01",
            "realizada",
            "espera",
            "valida",
            "pendiente",
            hoy=date(2026, 1, 2),
        )
        == "pendiente_evaluacion_cp"
    )
    assert (
        derivar_estado_flujo(
            "2026-01-01",
            "realizada",
            "espera",
            "requiere_revision",
            "pendiente",
            hoy=date(2026, 1, 2),
        )
        == "pendiente_evaluacion_cp"
    )


def test_kpi_gbs_definitivos():
    assert KPI_GBS == (
        "total",
        "validas",
        "no_validas",
        "pendiente_cliente",
        "en_revision",
    )
    portal = Path("dashboard/pages/12_GBS_Validacion_Reuniones.py").read_text(encoding="utf-8")
    for label in (
        "Total reuniones",
        "Válidas",
        "No válidas",
        "Pendiente cliente",
        "En revisión",
    ):
        assert label in portal
    assert '"progress": "Avance meta"' not in portal
    assert '"evaluacion_cerrada_valida", "cotizacion_valida"' in portal
    assert '"_validation_status"] == "evaluacion_cerrada_no_valida"' in portal
    assert 'df["_final"] == "valida"' not in portal
    assert 'df["_final"] == "no_valida"' not in portal


def test_campos_vacios_no_producen_texto_visible():
    for value in (None, "", "N/A", "Sin dato", "No disponible", "null", "—"):
        assert texto_real(value) == ""
    portal = Path("dashboard/pages/12_GBS_Validacion_Reuniones.py").read_text(encoding="utf-8")
    assert 'if not clean:\n        return ""' in portal


def test_evidencia_muestra_botones_y_confirmacion_sin_bloque_ia_duplicado():
    portal = Path("dashboard/pages/12_GBS_Validacion_Reuniones.py").read_text(encoding="utf-8")
    assert 'st.link_button("Abrir grabación"' in portal
    assert 'st.link_button("Abrir transcripción"' in portal
    assert 'with st.popover("Confirmación Conprospección"' not in portal
    assert "grid-template-columns:150px minmax(0,1fr)" in portal
    assert 'with st.expander("Evidencia IA")' not in portal


def test_evaluacion_cp_muestra_icp_y_bant_horizontales():
    portal = Path("dashboard/pages/12_GBS_Validacion_Reuniones.py").read_text(encoding="utf-8")
    assert "def _icp_evaluation" in portal
    assert "def _bant_evaluation" in portal
    assert "grid-template-columns:repeat(4,minmax(0,1fr))" in portal
    assert "No informada" in portal
    assert "st.markdown(_bant_evaluation(bant)" in portal


def test_historial_no_duplica_titulos_genericos():
    portal = Path("dashboard/pages/12_GBS_Validacion_Reuniones.py").read_text(encoding="utf-8")
    assert 'if is_quote and new_value == "realizada":' in portal
    assert 'current_validation_event = "Evaluación cerrada · Válida"' in portal
    assert '"Etapa de agenda actual"' not in portal
    assert '"Estatus de validación actual"' not in portal


def test_portal_gbs_busqueda_legibilidad_icp_y_modulos_visibles():
    portal = Path("dashboard/pages/12_GBS_Validacion_Reuniones.py").read_text(encoding="utf-8")
    nav = Path("dashboard/portal_auth.py").read_text(encoding="utf-8")
    report = Path("dashboard/pages/15_GBS_Reporte_Mensual.py").read_text(encoding="utf-8")
    insight = Path("dashboard/pages/11_GBS.py").read_text(encoding="utf-8")
    standard = Path("docs/PORTAL_CLIENTE_UX_STANDARD.md").read_text(encoding="utf-8")

    assert "def sincronizar_busqueda_principal" in portal
    assert "on_change=sincronizar_busqueda_principal" in portal
    assert "cargar_icp_resumen" in portal
    assert "Ver ICP acordado →" in portal
    assert "font-size:15px;font-weight:850" in portal
    assert "font-size:13px;font-weight:800;color:#6d28d9" in portal
    assert 'items = cfg["nav"]' in nav
    assert "todavía no tiene datos habilitados" in report
    assert "Dashboard disponible para clientes premium" in insight
    assert "Orden: KPIs → filtros → tabla → drawer lateral." in standard


def test_resumen_icp_compacto_se_construye_desde_todo_el_onboarding():
    onboarding = {
        "icp_pais": "Chile, Perú, Colombia",
        "icp_industrias": "Minería\nRetail",
        "icp_tamano": "1-10 empleados, 11-20 empleados, 101-200 empleados",
        "icp_cargos": "Gerente General\nJefe COMEX",
        "icp_descarte": "Freight forwarders\nNavieras",
        "icp_adicional": "Importaciones recurrentes",
        "dolores_clientes": "Falta de visibilidad",
        "gatillos_compra": "Cambio de proveedor",
        "keywords_prospecto": "COMEX, aduana",
    }
    profile = perfil_icp(onboarding)
    assert lista_onboarding(onboarding["icp_pais"]) == ["Chile", "Perú", "Colombia"]
    assert resumir_tamano(onboarding["icp_tamano"]) == "1 a 200 empleados"
    assert profile["resumen"] == (
        "Chile, Perú, Colombia · 2 industrias · 1 a 200 empleados · 2 cargos objetivo"
    )
    assert profile["exclusiones"] == ["Freight forwarders", "Navieras"]
    assert profile["complementos"]["Dolores observados"] == "Falta de visibilidad"

    portal = Path("dashboard/pages/12_GBS_Validacion_Reuniones.py").read_text(encoding="utf-8")
    onboarding_page = Path("dashboard/pages/14_GBS_Onboarding.py").read_text(encoding="utf-8")
    assert "Ver ICP acordado →" in portal
    assert 'st.session_state["gbs_scroll_to_icp"] = True' in portal
    assert 'st.switch_page("pages/14_GBS_Onboarding.py")' in portal
    assert 'id="resumen-icp"' in onboarding_page
    assert "Resumen ICP acordado" in onboarding_page
    assert "scrollIntoView" in onboarding_page


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
    assert informacion_reunion(
        {
            "raw_data": {
                "customFields": [
                    {
                        "id": "mwCPOKdikR3VfS7Xf9bm",
                        "value": "Preparación desde GHL",
                    }
                ]
            }
        },
        {},
    ) == "Preparación desde GHL"


def test_bant_puede_venir_de_ghl_o_completarse_internamente():
    row = {"bant_sdr": "Budget, Authority"}
    assert bant_desde_fuentes(row, {}) == ["B", "A"]
    assert bant_desde_fuentes(row, {"bant_cp": "N,T"}) == ["N", "T"]
    assert bant_desde_fuentes(
        {
            "raw_data": {
                "customFields": [
                    {
                        "id": "sPpRmRxaHRehCVr0UX29",
                        "value": ["Budget", "Need"],
                    }
                ]
            }
        },
        {},
    ) == ["B", "N"]
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


def test_motivos_revision_cliente_sin_opciones_descartadas():
    assert "contacto_incorrecto" not in MOTIVO_NO_VALIDEZ
    assert "evidencia_insuficiente" not in MOTIVO_NO_VALIDEZ
    assert "empresa_duplicada_excluida" not in MOTIVO_NO_VALIDEZ


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
