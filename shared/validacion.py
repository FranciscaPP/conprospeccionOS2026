"""Reglas del núcleo de validación de reuniones — puro y testeable.

3 capas de validez (cp/cli/final). La final se deriva automáticamente con
`derivar_final`. Regla de negocio (definida por el cliente del producto):
**el cliente manda** — si el cliente marca válida, la validez final es válida
y cuenta para la meta de inmediato, sin depender del estado operativo interno.
CP nunca se pisa (queda como registro del equipo); el override de CP manda sobre todo.
"""

STATUS_REUNION = ["agendada", "realizada", "no_asistio_lead", "no_asistio_cliente",
                  "cancelada_lead", "cancelada_cliente", "reagendada",
                  "pendiente_reagendar", "sin_info"]
VAL_ESTADOS = ["espera", "valida", "no_valida", "requiere_revision"]      # CP y cliente
VAL_FINAL   = ["pendiente", "valida", "no_valida", "en_disputa", "reagendada", "excluida"]
BANT_OPTS   = ["B", "A", "N", "T"]
MOTIVO_NO_VALIDEZ = ["no_calza_icp", "sin_necesidad", "sin_autoridad", "sin_presupuesto",
                     "sin_timing", "no_realizada", "otro"]
ESTADO_COMERCIAL = ["pendiente_seguimiento", "proximo_paso", "solicita_propuesta",
                    "propuesta_enviada", "seguimiento_propuesta", "negociacion",
                    "no_responde", "cliente_ganado", "cliente_perdido", "no_califica"]

_NO_REALIZADA = {"no_asistio_lead", "no_asistio_cliente", "cancelada_lead", "cancelada_cliente"}


def bant_list(v) -> list:
    if not v:
        return []
    items = v if isinstance(v, list) else str(v).split(",")
    return [x.strip().upper() for x in items if x and x.strip().upper() in BANT_OPTS]


def gate_valida_permitida(status_reunion) -> bool:
    """Solo una reunión realizada puede ser válida (candado)."""
    return status_reunion == "realizada"


def derivar_final(status_reunion, val_cp, val_cli, bant_cp, override=None):
    """Validez final automática. **El cliente manda.**

    - `override` (validez fijada a mano por CP/Francisca) manda sobre todo.
    - Si el cliente marca **válida** → final **válida** y cuenta para meta,
      sin importar el estado operativo (la validación del cliente implica que la reunión ocurrió).
    - Si el cliente marca **no válida** → final **no válida**; salvo "engaño"
      (CP la tenía válida con ≥2 BANT) → **en_disputa** para que Francisca lo revise.
    - Si el cliente aún no validó (espera / requiere_revisión): se mira el estado
      operativo — si no se realizó (no_asistió / cancelada) → **no_valida**; resto → **pendiente**.
    """
    if override:
        return override
    # El cliente manda sobre la validez final
    if val_cli == "valida":
        return "valida"
    if val_cli == "no_valida":
        if val_cp == "valida" and len(bant_list(bant_cp)) >= 2:
            return "en_disputa"        # señal de engaño: CP la calificaba, el cliente la rechaza
        return "no_valida"
    # Cliente aún no validó: el estado operativo decide
    if status_reunion in _NO_REALIZADA:
        return "no_valida"
    return "pendiente"


def flag_disputa(val_cp, val_cli, bant_cp) -> bool:
    return val_cp == "valida" and val_cli == "no_valida" and len(bant_list(bant_cp)) >= 2


def flag_meta_countable(val_final) -> bool:
    return val_final == "valida"
