"""Alicia · gestión de respuestas de campañas Snov.io desde Telegram.

Diseño (prioridad: mínimo consumo de créditos de IA):

- La DETECCIÓN, lectura de metadatos, filtrado de mensajes nuevos, identificación
  de respuestas / rebotes / fuera de oficina / duplicados es 100% determinística
  (código + Gmail API). Nunca llama a un modelo de IA.
- La IA (Anthropic) se usa SOLO bajo petición explícita desde Telegram
  (resumen, clasificar respuesta ambigua, redactar borrador) o cuando se autoriza
  una automatización específica. Ver `alicia/ai.py` y `alicia/README.md`.
- Si el usuario dicta el texto de respuesta, se envía sin llamar a ningún modelo.

Modo de prueba: `ALICIA_DRY_RUN=true` (por defecto) evita envíos de correo reales
y acciones GHL reales; el pipeline igual detecta, correlaciona y arma la alerta.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
