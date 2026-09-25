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

PROSPECT_BADGE_PALETTE = ["🟥", "🟧", "🟨", "🟩", "🟦", "🟪", "🟫"]


def prospect_badge(contact_id: str) -> str:
    """Emoji de color fijo por contact_id (mismo id -> siempre el mismo
    color). Con paleta de 7, se puede repetir si hay muchos prospectos
    activos en simultaneo en el mismo chat — es una ayuda visual, no un
    identificador unico."""
    index = sum(ord(char) for char in contact_id) % len(PROSPECT_BADGE_PALETTE)
    return PROSPECT_BADGE_PALETTE[index]


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


def _enrichment_detail_lines(enrichment: dict[str, Any], email: str, reply_snippet: str | None) -> list[str]:
    """Lineas de detalle compartidas entre las tarjetas de contacto nuevo y
    actualizado: cargo/empresa/tamaño/web/pais/correo/telefono/linkedin y,
    si vino, el extracto de la respuesta. Se usa `.get()` en todos los
    campos para que un `enrichment` vacio no rompa nada (simplemente no
    agrega esas lineas)."""
    lines: list[str] = []
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
    if enrichment.get("phone"):
        lines.append(f"*Teléfono:* {enrichment['phone']}")
    if enrichment.get("linkedin_personal"):
        lines.append(f"*LinkedIn:* {enrichment['linkedin_personal']}")
    if reply_snippet:
        preview = reply_snippet.strip().replace("\r\n", " ").replace("\n", " ")
        if len(preview) > 300:
            preview = preview[:300].rstrip() + "…"
        lines += ["", f"*Respondió:* _{preview}_"]
    return lines


def build_new_contact_card(
    cliente_slug: str, cliente_nombre: str, campaign_name: str,
    enrichment: dict[str, Any], email: str, contact_id: str, reply_snippet: str | None = None,
) -> str:
    accent = CLIENT_ACCENTS.get(cliente_slug, "🆕")
    badge = prospect_badge(contact_id)
    nombre = enrichment.get("name") or "(sin nombre)"
    lines = [
        f"{accent} *Nuevo contacto en el CRM*",
        "",
        f"*Cliente:* {cliente_nombre}",
        f"*Campaña:* {campaign_name}",
        "",
        f"*Prospecto:* {badge} {nombre}",
    ]
    lines += _enrichment_detail_lines(enrichment, email, reply_snippet)
    lines += ["", "Esta tarjeta se creó porque respondió la campaña y no existía en el CRM."]
    return "\n".join(lines)


def build_updated_contact_card(
    cliente_slug: str, cliente_nombre: str, nombre: str,
    enrichment: dict[str, Any], email: str, contact_id: str, reply_snippet: str | None = None,
) -> str:
    accent = CLIENT_ACCENTS.get(cliente_slug, "🔄")
    badge = prospect_badge(contact_id)
    lines = [
        f"{accent} *Contacto actualizado en el CRM*",
        "",
        f"*Cliente:* {cliente_nombre}",
        "",
        f"*Prospecto:* {badge} {nombre}",
    ]
    lines += _enrichment_detail_lines(enrichment, email, reply_snippet)
    lines += ["", "Respondió de nuevo la campaña — se completaron datos que faltaban."]
    return "\n".join(lines)


def build_mismatch_alert(cliente_nombre: str, email: str, ghl_name: str, snov_name: str) -> str:
    return (
        f"⚠️ *Revisar a mano* — {cliente_nombre}\n\n"
        f"El correo `{email}` ya existe en el CRM a nombre de *{ghl_name}*, "
        f"pero en Snov respondió *{snov_name}*.\n\n"
        "No se modificó el contacto ni el estatus — puede ser una casilla "
        "compartida o datos cruzados."
    )


def build_already_status_text(nombre: str, status: str, contact_id: str) -> str:
    badge = prospect_badge(contact_id)
    return f"ℹ️ *{badge} {nombre}* ya está en *{status}* en el CRM — no hay cambios."


def build_status_changed_text(nombre: str, status: str, contact_id: str) -> str:
    badge = prospect_badge(contact_id)
    return f"✅ *{badge} {nombre}* ahora está en *{status}* en el CRM."


def build_status_prompt(nombre: str, contact_id: str) -> str:
    badge = prospect_badge(contact_id)
    return f"🔵 *¿A qué estatus movemos a {badge} {nombre}?*"


def build_agendar_prompt(nombre: str, contact_id: str) -> str:
    badge = prospect_badge(contact_id)
    return f"🟢 *Agendar con {badge} {nombre}*"


def build_tarea_prompt(nombre: str, contact_id: str) -> str:
    badge = prospect_badge(contact_id)
    return f"⚪ *Generar tarea para {badge} {nombre}*"


def build_agendar_keyboard(contact_id: str) -> dict[str, Any]:
    return {"inline_keyboard": [[{"text": "📅 Ver horarios disponibles", "callback_data": f"agendar:{contact_id}:0"}]]}


def build_tarea_keyboard(contact_id: str) -> dict[str, Any]:
    return {"inline_keyboard": [[
        {"text": "✍️ Generar manual", "callback_data": f"tarea:{contact_id}:manual"},
        {"text": "⚙️ Generar automática", "callback_data": f"tarea:{contact_id}:auto"},
    ]]}


def build_reply_email_keyboard(contact_id: str) -> dict[str, Any]:
    return {"inline_keyboard": [[{"text": "✉️ Responder correo", "callback_data": f"email:{contact_id}"}]]}
