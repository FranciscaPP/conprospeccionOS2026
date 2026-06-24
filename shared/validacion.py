"""Reglas del nucleo de validacion de reuniones, puras y testeables.

Conprospeccion determina la validez contractual. El cliente solo confirma la
evaluacion o solicita revision; no evalua BANT ni invalida unilateralmente.
"""
import json
import re
from datetime import date

STATUS_REUNION = [
    "agendada",
    "realizada",
    "cotizacion",
    "no_asistio_lead",
    "no_asistio_cliente",
    "cancelada_lead",
    "cancelada_cliente",
    "reagendada",
    "pendiente_reagendar",
    "sin_info",
]
VAL_ESTADOS = ["espera", "valida", "no_valida", "requiere_revision"]
VAL_FINAL = ["pendiente", "valida", "no_valida", "en_disputa", "reagendada", "excluida"]
BANT_OPTS = ["B", "A", "N", "T"]
KPI_GBS = ("total", "validas", "no_validas", "avance_meta")
MOTIVO_NO_VALIDEZ = [
    "no_calza_icp",
    "bant_insuficiente",
    "no_realizada",
    "prospecto_no_asistio",
    "otro_contractual",
]
ESTADO_COMERCIAL = [
    "pendiente_seguimiento",
    "proximo_paso",
    "solicita_propuesta",
    "propuesta_enviada",
    "seguimiento_propuesta",
    "negociacion",
    "no_responde",
    "cliente_ganado",
    "cliente_perdido",
    "no_califica",
]

_NO_REALIZADA = {
    "no_asistio_lead",
    "no_asistio_cliente",
    "cancelada_lead",
    "cancelada_cliente",
}

ESTADOS_FLUJO = [
    "reunion_futura",
    "reunion_cancelada",
    "pendiente_evaluacion_cp",
    "pendiente_evaluacion_cliente",
    "cliente_solicita_revision",
    "evaluacion_cerrada_valida",
    "evaluacion_cerrada_no_valida",
]

ETAPAS_AGENDA = [
    "reunion_futura",
    "reunion_agendada",
    "reunion_realizada",
    "cotizacion",
    "reagendar",
    "reunion_cancelada",
]

LABEL_ETAPA_AGENDA = {
    "reunion_futura": "Reunión futura",
    "reunion_agendada": "Reunión agendada",
    "reunion_realizada": "Reunión realizada",
    "cotizacion": "Cotización",
    "reagendar": "Reagendar",
    "reunion_cancelada": "Reunión cancelada",
}

ESTATUS_VALIDACION = [
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

LABEL_ESTATUS_VALIDACION = {
    "pendiente_evaluacion_cp": "Pendiente evaluación Conprospección",
    "validada_por_cp": "Validada por Conprospección",
    "rechazada_por_cp": "Rechazada por Conprospección",
    "pendiente_confirmacion_cliente": "Pendiente confirmación cliente",
    "cliente_solicita_revision": "Cliente solicita revisión",
    "cotizacion_valida": "Cotización · Válida",
    "reagendar": "Reagendar",
    "reunion_cancelada": "Reunión cancelada",
    "evaluacion_cerrada_valida": "Evaluación cerrada · Válida",
    "evaluacion_cerrada_no_valida": "Evaluación cerrada · No válida",
}

LABEL_ESTADO_FLUJO = {
    "reunion_futura": "Reunión futura",
    "reunion_cancelada": "Reunión cancelada",
    "pendiente_evaluacion_cp": "Pendiente de evaluación Conprospección",
    "pendiente_evaluacion_cliente": "Pendiente confirmación cliente",
    "cliente_solicita_revision": "Cliente solicita revisión",
    "evaluacion_cerrada_valida": "Evaluación cerrada · Válida",
    "evaluacion_cerrada_no_valida": "Evaluación cerrada · No válida",
}

DESCRIPCION_ESTADO_FLUJO = {
    "reunion_futura": "Esta reunión aún no ocurre. No admite confirmación ni solicitud de revisión.",
    "reunion_cancelada": "Reunión cancelada y resuelta operativamente.",
    "pendiente_evaluacion_cp": "Conprospección aún debe revisar la reunión.",
    "pendiente_evaluacion_cliente": "Conprospección evaluó la reunión y espera la confirmación del cliente.",
    "cliente_solicita_revision": "El cliente pidió revisión. Conprospección debe resolver.",
    "evaluacion_cerrada_valida": "Reunión cerrada como válida.",
    "evaluacion_cerrada_no_valida": "Reunión cerrada como no válida por Conprospección.",
}

_VACIOS = {"", "none", "null", "nan", "n/a", "na", "sin dato", "sin datos", "no disponible", "—", "-"}


def texto_real(value) -> str:
    """Normaliza texto de UI; devuelve vacío para placeholders y valores nulos."""
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in _VACIOS else text


def _normalizar_clave(value) -> str:
    text = texto_real(value).lower()
    return re.sub(r"[^a-z0-9áéíóúüñ]", "", text)


def valor_custom_field(source, aliases):
    """Busca un custom field por key/nombre dentro de estructuras GHL conocidas."""
    if not source:
        return ""
    if isinstance(source, str):
        try:
            source = json.loads(source)
        except (TypeError, ValueError):
            return ""
    targets = {_normalizar_clave(alias) for alias in aliases}
    candidates = []
    if isinstance(source, list):
        candidates.extend(source)
    elif isinstance(source, dict):
        for key in ("customFields", "custom_fields", "contact_custom_fields"):
            value = source.get(key)
            if isinstance(value, list):
                candidates.extend(value)
        for key in ("contact", "raw_data", "appointment"):
            nested = source.get(key)
            if isinstance(nested, (dict, list)):
                nested_value = valor_custom_field(nested, aliases)
                if nested_value:
                    return nested_value
        for alias in aliases:
            direct = source.get(alias)
            if texto_real(direct):
                return texto_real(direct)
    for field in candidates:
        if not isinstance(field, dict):
            continue
        keys = {
            _normalizar_clave(field.get(key))
            for key in ("id", "name", "fieldName", "fieldKey", "key")
        }
        if keys & targets:
            value = field.get("value")
            return value if isinstance(value, (list, tuple, dict)) else texto_real(value)
    return ""


INFO_REUNION_ALIASES = (
    "mwCPOKdikR3VfS7Xf9bm",
    "informacin_de_preparacin_para_la_reunin",
    "informacion_de_preparacion_para_la_reunion",
    "información de preparación para la reunión",
    "preparacion_para_la_reunion",
    "informacion para reunion",
    "meetingInfo",
)

BANT_SDR_ALIASES = (
    "sPpRmRxaHRehCVr0UX29",
    "validacin_sdr_bant",
    "validacion_sdr_bant",
    "validación_sdr_bant",
    "validacion sdr bant",
)


def informacion_reunion(row=None, seguimiento=None) -> str:
    row = {} if row is None else row
    seguimiento = {} if seguimiento is None else seguimiento
    for value in (
        seguimiento.get("informacion_reunion_manual"),
        row.get("informacion_reunion"),
        valor_custom_field(row.get("raw_data"), INFO_REUNION_ALIASES),
    ):
        if texto_real(value):
            return texto_real(value)
    return ""


def bant_desde_fuentes(row=None, seguimiento=None) -> list:
    row = {} if row is None else row
    seguimiento = {} if seguimiento is None else seguimiento
    values = (
        seguimiento.get("bant_cp"),
        row.get("bant_sdr"),
        valor_custom_field(row.get("raw_data"), BANT_SDR_ALIASES),
        row.get("ai_bant_detected"),
    )
    for value in values:
        parsed = bant_list(value)
        if parsed:
            return parsed
    return []


def icp_gbs(status_reunion, valor_guardado=None):
    """GBS cumple ICP salvo cancelación; un valor interno explícito tiene prioridad."""
    if valor_guardado is not None:
        return bool(valor_guardado)
    return status_reunion not in {"cancelada_lead", "cancelada_cliente"}


def construir_justificacion(
    val_cp,
    *,
    icp=None,
    bant=None,
    evidencia=False,
    tiene_informacion=False,
    comentario="",
) -> str:
    partes = []
    comentario = texto_real(comentario)
    if comentario:
        partes.append(comentario)
    if val_cp == "valida":
        partes.append("Evaluación de Conprospección: válida.")
    elif val_cp == "no_valida":
        partes.append("Evaluación de Conprospección: no válida.")
    if icp is True:
        partes.append("ICP: cumple.")
    elif icp is False:
        partes.append("ICP: no cumple.")
    bant_items = bant_list(bant)
    if bant_items:
        partes.append(f"BANT informado: {', '.join(bant_items)}.")
    if evidencia:
        partes.append("Existe evidencia disponible para la evaluación.")
    if tiene_informacion:
        partes.append("Existe información de preparación aportada por la SDR.")
    return " ".join(partes)


def derivar_estado_flujo(
    fecha_reunion,
    status_reunion,
    val_cp,
    val_cli,
    val_final,
    *,
    hoy=None,
):
    """Estado único de UX para portal cliente y seguimiento interno."""
    hoy = hoy or date.today()
    fecha_texto = str(fecha_reunion).strip()
    if fecha_reunion is None or fecha_texto.lower() in {"", "nat", "nan", "none"}:
        fecha = None
    else:
        try:
            fecha = (
                fecha_reunion
                if isinstance(fecha_reunion, date)
                else date.fromisoformat(fecha_texto[:10])
            )
        except (TypeError, ValueError):
            fecha = None

    if fecha and fecha > hoy and status_reunion not in _NO_REALIZADA:
        return "reunion_futura"
    if status_reunion in {"cancelada_lead", "cancelada_cliente"}:
        return "reunion_cancelada"
    if val_final == "valida":
        return "evaluacion_cerrada_valida"
    if val_final in {"no_valida", "excluida"}:
        return "evaluacion_cerrada_no_valida"
    # El cliente puede responder antes que CP. Esa respuesta queda registrada
    # como antecedente, pero el flujo sigue pendiente de la autoridad final.
    if val_cp not in {"valida", "no_valida"}:
        return "pendiente_evaluacion_cp"
    if val_cli in {"requiere_revision", "no_valida", "reagendada"} or val_final == "en_disputa":
        return "cliente_solicita_revision"
    if val_cp == "valida":
        return "pendiente_evaluacion_cliente"
    return "pendiente_evaluacion_cp"


def derivar_etapa_agenda(fecha_reunion, status_reunion, *, hoy=None):
    """Proyecta exclusivamente la etapa operativa de agenda."""
    hoy = hoy or date.today()
    fecha = None
    fecha_texto = str(fecha_reunion).strip()
    if fecha_reunion is not None and fecha_texto.lower() not in {"", "nat", "nan", "none"}:
        try:
            fecha = (
                fecha_reunion
                if isinstance(fecha_reunion, date)
                else date.fromisoformat(fecha_texto[:10])
            )
        except (TypeError, ValueError):
            fecha = None
    if status_reunion in {"cotizacion", "solicita_cotizacion"}:
        return "cotizacion"
    if status_reunion in {"cancelada_lead", "cancelada_cliente"}:
        return "reunion_cancelada"
    if status_reunion in {
        "no_asistio_lead",
        "no_asistio_cliente",
        "reagendada",
        "pendiente_reagendar",
    }:
        return "reagendar"
    if fecha and fecha > hoy:
        return "reunion_futura"
    if status_reunion == "realizada" or (fecha and fecha < hoy):
        return "reunion_realizada"
    return "reunion_agendada"


def derivar_estatus_validacion(
    etapa_agenda,
    val_cp,
    val_cli,
    val_final,
    *,
    flag_disputa=False,
):
    """Proyecta exclusivamente el avance contractual de validación."""
    if etapa_agenda == "cotizacion":
        return "cotizacion_valida"
    if flag_disputa or val_cli in {"requiere_revision", "no_valida", "reagendada"}:
        return "cliente_solicita_revision"
    if etapa_agenda == "reagendar":
        return "reagendar"
    if etapa_agenda == "reunion_cancelada":
        return "reunion_cancelada"
    if etapa_agenda == "reunion_futura":
        if val_cp == "valida":
            return "validada_por_cp"
        if val_cp == "no_valida":
            return "rechazada_por_cp"
        return "pendiente_evaluacion_cp"
    if val_final == "valida":
        return "evaluacion_cerrada_valida"
    if val_final == "no_valida" and val_cp == "no_valida":
        return "evaluacion_cerrada_no_valida"
    if val_cp == "no_valida":
        return "rechazada_por_cp"
    if val_cp == "valida":
        return "pendiente_confirmacion_cliente"
    return "pendiente_evaluacion_cp"


def bant_list(v) -> list:
    if not v:
        return []
    if isinstance(v, str):
        try:
            parsed = json.loads(v)
            items = parsed if isinstance(parsed, list) else re.split(r"[,;|/]+", v)
        except (TypeError, ValueError):
            items = re.split(r"[,;|/]+", v)
    else:
        items = v if isinstance(v, list) else [v]
    aliases = {
        "b": "B", "budget": "B", "presupuesto": "B",
        "a": "A", "authority": "A", "autoridad": "A",
        "n": "N", "need": "N", "necesidad": "N",
        "t": "T", "time": "T", "timing": "T", "tiempo": "T",
    }
    result = []
    for item in items:
        key = texto_real(item).lower()
        value = aliases.get(key)
        if value and value not in result:
            result.append(value)
    return result


def gate_valida_permitida(status_reunion) -> bool:
    """Solo una reunion realizada puede ser valida."""
    return status_reunion == "realizada"


def acciones_cliente_permitidas(estado_flujo, val_cp, val_cli) -> tuple[str, ...]:
    if estado_flujo not in {
        "pendiente_evaluacion_cp",
        "pendiente_evaluacion_cliente",
    }:
        return ()
    if val_cp == "no_valida" or val_cli not in (None, "", "espera"):
        return ()
    return ("confirmar", "solicitar_revision")


def derivar_final(
    status_reunion,
    val_cp,
    val_cli,
    bant_cp,
    override=None,
    evidencia_suficiente=None,
    resultado_actual=None,
):
    """Deriva el resultado final sin permitir cierres negativos del cliente.

    BANT, evidencia y estados operativos son informativos. Una solicitud de
    revision mantiene pendiente la resolucion de Conprospeccion y conserva una
    validez ya contabilizada hasta que exista resolucion interna.
    """
    if override:
        return override
    if status_reunion in {"cotizacion", "solicita_cotizacion"}:
        return "valida"
    if val_cp == "no_valida":
        return "no_valida"
    if val_cp != "valida":
        return "pendiente"
    if val_cli == "valida":
        return "valida"
    if val_cli in ("requiere_revision", "no_valida", "reagendada"):
        return "valida" if resultado_actual == "valida" else "pendiente"
    return "pendiente"


def flag_disputa(val_cp, val_cli, bant_cp) -> bool:
    return val_cp == "valida" and val_cli in ("requiere_revision", "no_valida", "reagendada")


def flag_meta_countable(val_final) -> bool:
    return val_final == "valida"
