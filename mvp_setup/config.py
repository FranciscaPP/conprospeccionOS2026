from pathlib import Path

APP_DIR = Path(__file__).parent
BASE_DIR = APP_DIR.parent

CLIENTES_DIR = BASE_DIR / "CLIENTES"

CLIENTES_DIR.mkdir(parents=True, exist_ok=True)

APP_NAME = "Conprospección OS"
APP_VERSION = "1.0.0 MVP"

EXTENSIONES_DOCUMENTOS = {".pdf", ".docx", ".txt", ".md", ".doc"}
EXTENSIONES_IMAGENES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
EXTENSIONES_BASES = {".csv", ".xlsx", ".xls"}
EXTENSIONES_HTML = {".html", ".htm"}
EXTENSIONES_LOGOS = {".png", ".jpg", ".jpeg", ".svg", ".webp"}

ESTADOS_VALIDOS = [
    "creado",
    "archivos_subidos",
    "estructura_creada",
    "firma_generada",
    "analisis_pendiente",
    "analisis_listo",
    "icp_generado",
    "icp_pendiente_revision",
    "icp_aprobado",
    "mensajeria_generada",
    "brief_codex_generado",
    "listo_para_playbook",
    "listo_para_apollo",
    "listo_para_operacion",
]

ETAPAS = [
    {"id": 1, "nombre": "Crear Cliente", "icono": "👤"},
    {"id": 2, "nombre": "Archivos e Input", "icono": "📎"},
    {"id": 3, "nombre": "Branding y Firma", "icono": "✍️"},
    {"id": 4, "nombre": "Análisis Inicial", "icono": "🔍"},
    {"id": 5, "nombre": "ICP y Apollo", "icono": "🎯"},
    {"id": 6, "nombre": "Chat Contextual", "icono": "💬"},
    {"id": 7, "nombre": "Aprobación ICP", "icono": "✅"},
    {"id": 8, "nombre": "Mensajería Comercial", "icono": "📨"},
    {"id": 9, "nombre": "Brief para Codex", "icono": "📋"},
    {"id": 10, "nombre": "Futuras APIs", "icono": "🔌"},
]
