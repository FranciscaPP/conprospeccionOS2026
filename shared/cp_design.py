"""Tokens del design system interno de Conprospeccion.

Fuente de verdad: panel interno de Seguimiento de Reuniones
(dashboard/pages/1_Seguimiento_Reuniones.py). Acento primario = dorado,
texto carbon/tinta, verde solo como semantica de "positivo".
Usado por la pagina Intelligence Insight de GBS para NO reutilizar el
verde de BambuTech.
"""

# --- Marca ---
CP_GOLD = "#FFD700"
CP_GOLD_HOVER = "#FFCC00"
CP_GOLD_SOFT = "#FFF7BF"
CP_CARBON = "#333333"
CP_INK = "#1A1A1A"

# --- Superficies ---
CP_BG = "#FAFAF8"
CP_SURFACE = "#FFFFFF"
CP_MUTED_SURFACE = "#F4F4F2"
CP_MUTED = "#6B6B6B"
CP_LINE = "#EDECEA"
CP_LINE_STRONG = "#C9C9C4"

# --- Semantica ---
CP_GREEN = "#15803D"
CP_GREEN_BG = "#EAF6EF"
CP_ORANGE = "#A66A00"
CP_ORANGE_BG = "#FFF3D8"
CP_RED = "#C92B2B"
CP_RED_BG = "#FDECEA"
CP_BLUE = "#2563EB"
CP_BLUE_BG = "#EAF1FE"
CP_PURPLE = "#6D28D9"
CP_PURPLE_BG = "#F1EDFF"
CP_GRAY = "#8A8A86"
CP_GRAY_BG = "#F4F4F2"

# Escala de calor para el heatmap (off-white -> dorado -> ambar oscuro)
CP_HEAT = ["#F4F4F2", "#FFF3D8", "#FFE08A", "#E6A700"]

FONT_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?"
    "family=Saira:wght@400;600;700;800&"
    "family=IBM+Plex+Sans:wght@400;500;600;700&"
    "family=IBM+Plex+Mono:wght@400;500;600&display=swap');"
)
FONT_HEAD = 'Saira,"IBM Plex Sans",sans-serif'
FONT_BODY = '"IBM Plex Sans",ui-sans-serif,system-ui,sans-serif'
FONT_MONO = '"IBM Plex Mono",monospace'
