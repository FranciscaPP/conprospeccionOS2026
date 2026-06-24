"""Identidad visual y perfil comercial base de Clickie."""

CLICKIE_PURPLE = "#6d28d9"
CLICKIE_PURPLE_LIGHT = "#7c3aed"
CLICKIE_DARK = "#1e293b"
CLICKIE_BG = "#faf5ff"
CLICKIE_BORDER = "#ddd6fe"
CLICKIE_PURPLE_BG = "#f5f3ff"

# Alias temporales para reutilizar el renderer validado de GBS/BambuTech.
GBS_PURPLE = CLICKIE_PURPLE
GBS_PURPLE_BG = CLICKIE_PURPLE_BG
GBS_BORDER_2 = CLICKIE_BORDER
GBS_DARK = CLICKIE_DARK

# Perfil ICP de Clickie. Aún sin onboarding cargado: se deja vacío para que el
# portal muestre "por confirmar" en lugar de datos inventados. Cuando exista la
# fila en gbs_onboarding (cliente='clickie') o se complete aquí, el panel se llena.
ICP_DEFAULT = {}
