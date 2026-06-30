"""Acceso unificado a la tabla `seguimiento_reuniones` (3 niveles: cp / cli / final).

Una sola fila por reunión. El cliente escribe el nivel `cli`, Conprospección el `cp`
y el `final` (la validación final la define CP). Los 3 dashboards leen/escriben aquí.
"""
from __future__ import annotations
import sys
from pathlib import Path

# Garantiza que el paquete shared sea importable desde cualquier contexto
# (Streamlit Cloud, scripts directos, tests). Idempotente si ya está en el path.
_PKG_ROOT = str(Path(__file__).resolve().parent.parent)
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from datetime import datetime, timezone

import requests

from shared.config import supabase_url, supabase_key

_URL = supabase_url()
_KEY = supabase_key()
_H   = {"apikey": _KEY, "Authorization": f"Bearer {_KEY}"}
_HW  = {**_H, "Content-Type": "application/json"}

# ── Taxonomía única de tipo de respuesta (formato "Solicita..." en positivas) ──
TIPO_RESPUESTA_POS = [
    "Solicita reunión", "Solicita cotización",
    "Solicita reunión + cotización", "Solicita más información",
]
TIPO_RESPUESTA_NEG = [
    "No interesado", "Ya tiene proveedor", "No es la persona", "Sin respuesta",
]
TIPO_RESPUESTA_OPTS = TIPO_RESPUESTA_POS + TIPO_RESPUESTA_NEG

BANT_OPTS = ["B", "A", "N", "T"]
NIVELES   = ("cp", "cli", "final")
RESPUESTAS_CLIENTE_PERMITIDAS = ("valida", "requiere_revision")


def bant_to_list(v) -> list[str]:
    if not v:
        return []
    items = v if isinstance(v, list) else str(v).split(",")
    return [x.strip().upper() for x in items if x and x.strip().upper() in BANT_OPTS]


def bant_to_str(lst) -> str:
    return ",".join(x for x in (lst or []) if x in BANT_OPTS)


def tipo_valido(t) -> bool:
    return t in TIPO_RESPUESTA_OPTS


def payload_nivel(reunion_id: int, cliente_slug: str, nivel: str, *,
                  val_estado=None, etapa=None, bant=None,
                  tipo_respuesta=None, status=None) -> dict:
    """Arma el payload para upsert de un nivel (cp/cli/final). Solo toca columnas del nivel."""
    assert nivel in NIVELES, f"nivel inválido: {nivel}"
    p = {
        "reunion_id": reunion_id, "cliente_slug": cliente_slug,
        f"val_estado_{nivel}": val_estado,
        f"etapa_{nivel}": etapa,
        f"bant_{nivel}": bant_to_str(bant),
        f"tipo_respuesta_{nivel}": tipo_respuesta if tipo_valido(tipo_respuesta) else None,
        f"status_{nivel}": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        f"updated_by_{nivel}": datetime.now(timezone.utc).isoformat() if nivel in ("cp", "cli") else None,
    }
    return {k: v for k, v in p.items() if v is not None}


def payload_respuesta_cliente(
    reunion_id: int,
    cliente_slug: str,
    estado: str,
    *,
    comentario: str = "",
    motivo: str | None = None,
) -> dict:
    """Payload estricto del portal cliente; no admite campos CP u operativos."""
    if estado not in RESPUESTAS_CLIENTE_PERMITIDAS:
        raise ValueError(f"respuesta cliente no permitida: {estado}")
    if estado == "requiere_revision" and not comentario.strip():
        raise ValueError("solicitar revision exige comentario")
    now = datetime.now(timezone.utc).isoformat()
    return {
        "reunion_id": int(reunion_id),
        "cliente_slug": cliente_slug,
        "val_estado_cli": estado,
        "comentario_cli": comentario.strip() or None,
        "motivo_no_validez": motivo if estado == "requiere_revision" else None,
        "validated_by_cli": "cliente",
        "validated_cli_at": now,
        "updated_by_cli": now,
        "updated_at": now,
    }


def payload_antecedentes_internos(
    *,
    informacion: str = "",
    bant=None,
    icp_cumple: bool | None = None,
) -> dict:
    """Campos manuales internos que luego consume el portal cliente."""
    return {
        "informacion_reunion_manual": informacion.strip() or None,
        "bant_cp": bant_to_str(bant),
        "icp_cumple": icp_cumple,
    }


# Columnas que el portal del cliente puede ver (vista ejecutiva/contractual).
# Excluye datos operativos internos: notas_internas, proximo_paso, validated_by_*, etc.
COLUMNAS_CLIENTE = (
    "reunion_id,cliente_slug,status_reunion,"
    "val_estado_cp,bant_cp,comentario_cp,informacion_reunion_manual,icp_cumple,"
    "val_estado_cli,comentario_cli,motivo_no_validez,validated_cli_at,"
    "val_estado_final,final_override,flag_meta_countable,flag_disputa,flag_cliente_pendiente,"
    "recording_url,transcript_url,ai_summary,ai_bant_detected,"
    "ai_confidence,ai_evidence"
)


def cargar(cliente_slug: str, select: str = "*") -> dict:
    """Devuelve {reunion_id: fila} de seguimiento_reuniones para un cliente.

    `select` limita las columnas traídas. El portal del cliente debe pasar
    `COLUMNAS_CLIENTE` para no exponer datos operativos internos al navegador.
    """
    r = requests.get(
        f"{_URL}/rest/v1/seguimiento_reuniones?select={select}&cliente_slug=eq.{cliente_slug}",
        headers=_H, timeout=15)
    if not r.ok:
        return {}
    return {int(x["reunion_id"]): x for x in r.json() if x.get("reunion_id")}


def guardar_nivel(reunion_id: int, cliente_slug: str, nivel: str, **campos) -> bool:
    """Upsert (merge) del nivel indicado en seguimiento_reuniones."""
    p = payload_nivel(reunion_id, cliente_slug, nivel, **campos)
    r = requests.post(
        f"{_URL}/rest/v1/seguimiento_reuniones",
        json=p,
        headers={**_HW, "Prefer": "resolution=merge-duplicates,return=minimal"},
        timeout=10)
    return r.ok


# ── Validación 3 capas: historial + recálculo de validez final / flags ──────
# Import lazy para evitar fallos de path en Streamlit Cloud durante module load.
def _val():
    from shared.validacion import derivar_final, flag_disputa, flag_meta_countable  # noqa: PLC0415
    return derivar_final, flag_disputa, flag_meta_countable


def registrar_historial(meeting_id, field, old, new, by, role, dashboard):
    """Registra un cambio de campo en meeting_status_history (si realmente cambió)."""
    if str(old) == str(new):
        return True
    try:
        response = requests.post(
            f"{_URL}/rest/v1/meeting_status_history",
            json={"meeting_id": meeting_id, "field_changed": field,
                  "old_value": str(old) if old is not None else None,
                  "new_value": str(new) if new is not None else None,
                  "changed_by": by, "changed_by_role": role, "source_dashboard": dashboard},
            headers={**_HW, "Prefer": "return=minimal"}, timeout=10)
    except Exception:
        return False
    return response.ok


def recalcular_final_y_flags(
    reunion_id: int,
    cliente_slug: str,
    fila: dict | None = None,
    evidencia_suficiente: bool | None = None,
) -> dict:
    """Deriva la validez final automática y los flags desde la fila actual y los persiste.
    Respeta el override manual (final_override=true).

    ``fila`` permite recalcular con los valores recién guardados, evitando una
    segunda lectura que pueda devolver datos anteriores durante el mismo rerun.
    """
    derivar_final, flag_disputa, flag_meta_countable = _val()
    r = fila if fila is not None else cargar(cliente_slug).get(int(reunion_id), {})
    override = r.get("val_estado_final") if r.get("final_override") else None
    evidencia = evidencia_suficiente
    if evidencia is None:
        evidencia = any(
            r.get(field)
            for field in (
                "recording_url",
                "transcript_url",
                "ai_summary",
                "ai_evidence",
                "comentario_cp",
            )
        )
    final = derivar_final(
        r.get("status_reunion"),
        r.get("val_estado_cp"),
        r.get("val_estado_cli"),
        r.get("bant_cp"),
        override=override,
        evidencia_suficiente=evidencia,
        resultado_actual=r.get("val_estado_final"),
    )
    disp = flag_disputa(r.get("val_estado_cp"), r.get("val_estado_cli"), r.get("bant_cp"))
    countable = flag_meta_countable(final)
    pend_cli = (
        r.get("val_estado_cp") == "valida"
        and r.get("val_estado_cli") in (None, "", "espera")
    )
    try:
        response = requests.post(
            f"{_URL}/rest/v1/seguimiento_reuniones",
            json={"reunion_id": reunion_id, "cliente_slug": cliente_slug,
                  "val_estado_final": final, "flag_disputa": disp,
                  "flag_meta_countable": countable, "flag_cliente_pendiente": pend_cli,
                  "updated_at": datetime.now(timezone.utc).isoformat()},
            headers={**_HW, "Prefer": "resolution=merge-duplicates,return=minimal"}, timeout=10)
        persisted = response.ok
    except Exception:
        persisted = False
    return {
        "final": final,
        "disputa": disp,
        "countable": countable,
        "pendiente_cli": pend_cli,
        "persisted": persisted,
    }
