"""Constantes de marca y dominio de GBS Logistics — fuente única de verdad.

Centraliza la paleta, los tokens semánticos de datos y los top-5 cargos/industrias
para que los reportes «Indicadores» (11_GBS) y «Validación de Reuniones» (12_GBS),
más el «Playbook SDR», nunca se desincronicen.

Regla de color (UI/UX):
  • Morado/rosa/amarillo = colores de MARCA (volumen, neutro, acento).
  • Verde/ámbar/rojo      = colores SEMÁNTICOS (positivo / riesgo / negativo).
"""

# ── Paleta oficial GBS (extraída del logo) ────────────────────────────
GBS_PURPLE = "#7c3aed"
GBS_PINK   = "#db2777"
GBS_YELLOW = "#f59e0b"
GBS_DARK   = "#1e293b"
GBS_BG     = "#faf5ff"
GBS_BORDER = "#e9d5ff"

# Variantes claras (fondos suaves) y oscuras (texto sobre fondo claro)
GBS_PURPLE_DK = "#5b21b6"   # texto morado accesible sobre fondos claros
GBS_PURPLE_BG = "#f5f3ff"
GBS_BORDER_2  = "#ddd6fe"

# ── Tokens semánticos de datos (NO son de marca) ──────────────────────
C_GREEN = "#16a34a"   # positivo / válida
C_RED   = "#dc2626"   # negativo / rechazo
C_AMBER = "#d97706"   # riesgo / atención
C_SLATE = "#64748b"   # neutro / secundario

# ── Top-5 cargos e industrias (idénticos en filtros, ICP y campañas) ──
TOP_CARGOS = ["Encargado de Importaciones", "Jefe COMEX", "Gerente de Operaciones",
              "Supply Chain Manager", "Gerente de Abastecimiento"]
TOP_INDUSTRIAS = ["Minería y Metales", "Retail", "Automotriz",
                  "Alimentos y Bebidas", "Dispositivos Médicos"]

# Pesos para el dataset demo (deben sumar ~1.0 y respetar el orden de los top-5)
W_CARGO = [("Encargado de Importaciones", .30), ("Jefe COMEX", .23),
           ("Gerente de Operaciones", .18), ("Supply Chain Manager", .16),
           ("Gerente de Abastecimiento", .13)]
W_IND   = [("Minería y Metales", .26), ("Retail", .24), ("Automotriz", .20),
           ("Alimentos y Bebidas", .18), ("Dispositivos Médicos", .12)]
