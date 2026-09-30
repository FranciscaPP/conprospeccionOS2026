"""Preparación de borradores de respuesta.

Dos vías, y la barata es la predeterminada:

- `literal_reply()`: el usuario DICTA el texto → se usa tal cual, SIN IA.
- `ai_reply()`: el usuario pide redactar → delega en alicia.ai (bajo petición y
  con la IA habilitada). Si la IA está apagada, informa cómo activarla.

El parser de instrucciones (`interpret_instruction`) es determinístico: reconoce
"no responder" y "envía exactamente: ..." sin llamar a ningún modelo.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from alicia import ai


class Intent(str, Enum):
    DO_NOT_REPLY = "do_not_reply"
    LITERAL = "literal"        # el usuario dictó el texto exacto → sin IA
    AI_DRAFT = "ai_draft"      # el usuario pide redactar → IA bajo petición


@dataclass(frozen=True)
class Instruction:
    intent: Intent
    text: str = ""  # texto literal (LITERAL) o instrucción natural (AI_DRAFT)


_DO_NOT_REPLY = (
    "no responder",
    "no contestar",
    "no responderle",
    "ignorar",
    "descartar",
)

# Prefijos que indican dictado literal (sin IA).
_LITERAL_PREFIXES = (
    "envia exactamente:",
    "envía exactamente:",
    "responde exactamente:",
    "texto literal:",
    "literal:",
)


def interpret_instruction(raw: str) -> Instruction:
    """Determinístico. No llama a IA. Decide la intención de la instrucción."""
    text = (raw or "").strip()
    low = text.lower()
    if any(low == phrase or low.startswith(phrase) for phrase in _DO_NOT_REPLY):
        return Instruction(intent=Intent.DO_NOT_REPLY)
    for prefix in _LITERAL_PREFIXES:
        if low.startswith(prefix):
            literal = text[len(prefix):].strip()
            return Instruction(intent=Intent.LITERAL, text=literal)
    # Entre comillas dobles → también se toma como literal.
    quoted = re.match(r'^"(.+)"$', text, re.DOTALL)
    if quoted:
        return Instruction(intent=Intent.LITERAL, text=quoted.group(1).strip())
    return Instruction(intent=Intent.AI_DRAFT, text=text)


def literal_reply(text: str) -> str:
    """El texto dictado por el usuario, sin tocar la IA."""
    return (text or "").strip()


def ai_reply(instruction: str, subject: str, last_message: str, cliente: str = "") -> str:
    """Borrador con IA. Solo si el usuario lo pidió y la IA está habilitada."""
    return ai.draft_reply(instruction, subject, last_message, cliente)


def build_draft(raw_instruction: str, subject: str, last_message: str, cliente: str = "") -> tuple[Intent, str]:
    """Resuelve la instrucción a (intención, cuerpo del borrador).

    Lanza alicia.ai.AIDisabledError solo en la rama AI_DRAFT con IA apagada, para
    que el manejador de Telegram informe cómo activarla o pida dictar el texto.
    """
    instruction = interpret_instruction(raw_instruction)
    if instruction.intent is Intent.DO_NOT_REPLY:
        return Intent.DO_NOT_REPLY, ""
    if instruction.intent is Intent.LITERAL:
        return Intent.LITERAL, literal_reply(instruction.text)
    return Intent.AI_DRAFT, ai_reply(instruction.text, subject, last_message, cliente)
