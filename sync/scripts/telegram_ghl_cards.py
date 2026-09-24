from __future__ import annotations

import unicodedata
from typing import Any

STATUS_PROSPECTO_ORDER = [
    "No Contesta",
    "Informacion Adicional",
    "Coordinando Reunion",
    "Reunion Agendada",
    "Reagendar Reunion",
    "No Interesado",
    "No Califica",
    "Deriva Refiere Directo",
    "Deriva Refiere Seguimiento",
    "Telefono / Whatsapp no existen",
]

CLIENT_ACCENTS = {"bambutech": "🟢", "gbs": "🔵", "balia": "🟠"}


def _strip_accents(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()


def order_status_options(real_options: list[str]) -> list[str]:
    """Ordena las opciones reales de GHL segun STATUS_PROSPECTO_ORDER.
    Cualquier opcion que no matchee ninguna palabra clave queda al final,
    en el orden en que vino de GHL."""

    def sort_key(option: str) -> tuple[int, int]:
        normalized = _strip_accents(option)
        for index, wanted in enumerate(STATUS_PROSPECTO_ORDER):
            if _strip_accents(wanted) == normalized:
                return (index, 0)
        return (len(STATUS_PROSPECTO_ORDER), real_options.index(option))

    return sorted(real_options, key=sort_key)


def build_status_keyboard(ordered_options: list[str], contact_id: str) -> dict[str, Any]:
    rows = [ordered_options[i:i + 2] for i in range(0, len(ordered_options), 2)]
    inline_keyboard: list[list[dict[str, str]]] = []
    idx = 0
    for row in rows:
        keyboard_row = []
        for label in row:
            keyboard_row.append({"text": label, "callback_data": f"status:{contact_id}:{idx}"})
            idx += 1
        inline_keyboard.append(keyboard_row)
    return {"inline_keyboard": inline_keyboard}


def build_new_contact_card(
    cliente_slug: str, cliente_nombre: str, campaign_name: str,
    enrichment: dict[str, Any], email: str,
) -> str:
    accent = CLIENT_ACCENTS.get(cliente_slug, "🆕")
    nombre = enrichment.get("name") or "(sin nombre)"
    lines = [
        f"{accent} *Nuevo contacto creado en GHL*",
        "",
        f"*Cliente:* {cliente_nombre}",
        f"*Campaña:* {campaign_name}",
        "",
        f"*Prospecto:* {nombre}",
    ]
    if enrichment.get("cargo"):
        lines.append(f"*Cargo:* {enrichment['cargo']}")
    if enrichment.get("company_name"):
        lines.append(f"*Empresa:* {enrichment['company_name']}")
    if enrichment.get("tamano_empresa"):
        lines.append(f"*Tamaño empresa:* {enrichment['tamano_empresa']}")
    if enrichment.get("website"):
        lines.append(f"*Web:* {enrichment['website']}")
    if enrichment.get("country"):
        lines.append(f"*País:* {enrichment['country']}")
    lines.append(f"*Correo:* {email}")
    if enrichment.get("linkedin_personal"):
        lines.append(f"*LinkedIn:* {enrichment['linkedin_personal']}")
    lines += [
        "",
        "_Respondió la campaña — no existía en GHL, se creó con estos datos._",
        "",
        "Respondé este mensaje para mover el estatus o crear una tarea.",
    ]
    return "\n".join(lines)


def build_updated_contact_card(cliente_slug: str, cliente_nombre: str, nombre: str, email: str) -> str:
    accent = CLIENT_ACCENTS.get(cliente_slug, "🔄")
    return (
        f"{accent} *Contacto actualizado en GHL*\n\n"
        f"*Cliente:* {cliente_nombre}\n"
        f"*Prospecto:* {nombre} ({email})\n\n"
        "_Respondió de nuevo la campaña — se completaron datos que faltaban._\n\n"
        "Respondé este mensaje para mover el estatus o crear una tarea."
    )


def build_mismatch_alert(cliente_nombre: str, email: str, ghl_name: str, snov_name: str) -> str:
    return (
        f"⚠️ *Revisar a mano* — {cliente_nombre}\n\n"
        f"El correo `{email}` ya existe en GHL a nombre de *{ghl_name}*, "
        f"pero en Snov respondió *{snov_name}*.\n\n"
        "No se modificó el contacto ni el estatus — puede ser una casilla "
        "compartida o datos cruzados."
    )


def build_already_status_text(nombre: str, status: str) -> str:
    return f"ℹ️ *{nombre}* ya está en *{status}* en GHL — no hay cambios."


def build_status_changed_text(nombre: str, status: str) -> str:
    return f"✅ *{nombre}* ahora está en *{status}* en GHL."


def parse_task_command(text: str) -> str | None:
    """Devuelve el texto de la tarea si el mensaje empieza con 'tarea' (con
    o sin ':'), sino None."""
    stripped = text.strip()
    lowered = stripped.lower()
    if lowered.startswith("tarea:"):
        rest = stripped[len("tarea:"):].strip()
    elif lowered.startswith("tarea "):
        rest = stripped[len("tarea "):].strip()
    else:
        return None
    return rest or None
