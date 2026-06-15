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


# Columnas que el portal del cliente puede ver (vista ejecutiva/contractual).
# Excluye datos operativos internos: notas_internas, proximo_paso, validated_by_*, etc.
COLUMNAS_CLIENTE = (
    "reunion_id,cliente_slug,status_reunion,"
    "val_estado_cp,bant_cp,comentario_cp,"
    "val_estado_cli,bant_cli,comentario_cli,motivo_no_validez,"
    "val_estado_final,final_override,estado_comercial"
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
        return
    try:
        requests.post(
            f"{_URL}/rest/v1/meeting_status_history",
            json={"meeting_id": meeting_id, "field_changed": field,
                  "old_value": str(old) if old is not None else None,
                  "new_value": str(new) if new is not None else None,
                  "changed_by": by, "changed_by_role": role, "source_dashboard": dashboard},
            headers={**_HW, "Prefer": "return=minimal"}, timeout=10)
    except Exception:
        pass


def recalcular_final_y_flags(reunion_id: int, cliente_slug: str) -> dict:
    """Deriva la validez final automática y los flags desde la fila actual y los persiste.
    Respeta el override manual (final_override=true)."""
    derivar_final, flag_disputa, flag_meta_countable = _val()
    r = cargar(cliente_slug).get(int(reunion_id), {})
    override = r.get("val_estado_final") if r.get("final_override") else None
    final = derivar_final(r.get("status_reunion"), r.get("val_estado_cp"),
                          r.get("val_estado_cli"), r.get("bant_cp"), override=override)
    disp = flag_disputa(r.get("val_estado_cp"), r.get("val_estado_cli"), r.get("bant_cp"))
    countable = flag_meta_countable(final)
    pend_cli = (r.get("val_estado_cli") in (None, "", "espera"))
    requests.post(
        f"{_URL}/rest/v1/seguimiento_reuniones",
        json={"reunion_id": reunion_id, "cliente_slug": cliente_slug,
              "val_estado_final": final, "flag_disputa": disp,
              "flag_meta_countable": countable, "flag_cliente_pendiente": pend_cli,
              "updated_at": datetime.now(timezone.utc).isoformat()},
        headers={**_HW, "Prefer": "resolution=merge-duplicates,return=minimal"}, timeout=10)
    return {"final": final, "disputa": disp, "countable": countable, "pendiente_cli": pend_cli}
