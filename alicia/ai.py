"""Gateway ÚNICO de IA de Alicia. Apagado por defecto.

CONTROL DE COSTOS (obligatorio leer antes de habilitar):

Toda llamada a un modelo pasa por aquí. El pipeline de detección NO importa ni
usa este módulo: la detección es 100% determinística. La IA solo se invoca desde
el manejador de Telegram cuando el usuario lo pide explícitamente.

  1. ¿CUÁNDO se ejecuta exactamente?
     - `summarize()`      → solo si el usuario escribe "resumen" / "resúmeme ..."
     - `classify()`       → solo si el usuario pide "clasifica esta respuesta"
     - `draft_reply()`    → solo si el usuario pide "redáctale ..." / "responde ..."
     Si el usuario DICTA el texto ("envía exactamente: ..."), NO se llama a la IA:
     el texto va directo al envío (ver alicia/drafting.py::literal_reply).
     Nunca se llama una vez por correo detectado ni en bucle.

  2. ¿QUÉ información se envía al modelo?
     - Para resumen/clasificación: asunto + último mensaje del prospecto (texto),
       cliente y campaña. Nada de bandejas completas ni historiales masivos.
     - Para borrador: además, la instrucción en lenguaje natural del usuario.
     - Nunca se envían secretos, tokens ni PII más allá del cuerpo del correo.

  3. ¿QUÉ modelo se usa?
     - `ALICIA_AI_MODEL` (por defecto claude-haiku-4-5-20251001, el más barato).
     - `max_tokens` acotado por función para limitar el costo por llamada.

  4. ¿CÓMO se desactiva por completo?
     - `ALICIA_AI_ENABLED=false` (valor por defecto) apaga TODA llamada: cada
       función lanza `AIDisabledError` sin tocar la red.
     - Sin `ANTHROPIC_API_KEY` tampoco se ejecuta.
"""
from __future__ import annotations

from alicia import settings

# Presupuesto de tokens por tipo de tarea (tope de costo por llamada).
_MAX_TOKENS = {"summary": 220, "classify": 60, "draft": 500}


class AIDisabledError(RuntimeError):
    """Se lanza cuando se intenta usar IA con el interruptor apagado."""


def _guard() -> None:
    if not settings.ai_enabled():
        raise AIDisabledError(
            "IA desactivada (ALICIA_AI_ENABLED=false). Actívala solo si quieres "
            "permitir resúmenes/clasificación/borradores bajo petición."
        )
    if not settings.anthropic_key():
        raise AIDisabledError("Falta ANTHROPIC_API_KEY; no se puede llamar a la IA.")


def _call(prompt: str, task: str, system: str) -> str:
    _guard()
    import anthropic  # import perezoso: no se carga si la IA está apagada

    client = anthropic.Anthropic(api_key=settings.anthropic_key())
    response = client.messages.create(
        model=settings.anthropic_model(),
        max_tokens=_MAX_TOKENS.get(task, 200),
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    parts = [block.text for block in response.content if getattr(block, "type", "") == "text"]
    return "".join(parts).strip()


def summarize(subject: str, last_message: str, cliente: str = "", campaign: str = "") -> str:
    """Resumen breve de UNA respuesta. Solo bajo petición explícita del usuario."""
    prompt = (
        f"Cliente: {cliente or '—'} · Campaña: {campaign or '—'}\n"
        f"Asunto: {subject or '—'}\n"
        f"Mensaje del prospecto:\n{last_message or '—'}\n\n"
        "Resume en 1-2 frases qué pide o responde el prospecto."
    )
    return _call(prompt, "summary", "Eres un asistente comercial conciso en español.")


def classify(subject: str, last_message: str) -> str:
    """Clasifica una respuesta ambigua. Solo bajo petición explícita del usuario."""
    prompt = (
        f"Asunto: {subject or '—'}\nMensaje:\n{last_message or '—'}\n\n"
        "Clasifica la intención en una palabra: interesado, no_interesado, "
        "pide_info, reagendar, derivar, u otro."
    )
    return _call(prompt, "classify", "Clasificas intención de respuestas comerciales.")


def draft_reply(instruction: str, subject: str, last_message: str, cliente: str = "") -> str:
    """Redacta un borrador a partir de la instrucción del usuario. Bajo petición."""
    prompt = (
        f"Cliente: {cliente or '—'}\nAsunto original: {subject or '—'}\n"
        f"Mensaje del prospecto:\n{last_message or '—'}\n\n"
        f"Instrucción del usuario: {instruction}\n\n"
        "Redacta la respuesta al prospecto en español, cordial y profesional. "
        "Devuelve solo el cuerpo del correo, sin asunto ni firma."
    )
    return _call(prompt, "draft", "Redactas correos comerciales en nombre de un SDR.")
