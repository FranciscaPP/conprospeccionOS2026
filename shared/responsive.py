"""CSS responsivo global para Conprospeccion OS (uso en teléfono y tablet).

Fuente única del comportamiento responsivo del dashboard. Se inyecta desde los
puntos de entrada de autenticación (`master_auth.require_master_auth` y
`portal_auth.require_auth_client`), que TODAS las páginas y portales llaman al
inicio. Así el panel interno y todos los dashboards de cliente quedan usables en
pantallas chicas sin tener que editar página por página.

Estrategia (solo CSS, sin tocar la lógica de cada página):
- En móvil las columnas de Streamlit (`st.columns`) se apilan en vertical en
  lugar de quedar apretadas lado a lado.
- Se reduce el padding lateral del contenedor para aprovechar el ancho.
- Titulares, métricas y tarjetas se reescalan a un tamaño legible en teléfono.
- Tablas / dataframes y bloques anchos hacen scroll horizontal propio en vez de
  romper el ancho de la página.
- Botones e inputs quedan con un área táctil cómoda (>= 44px).
"""
from __future__ import annotations

import streamlit as st

# Breakpoints:
#   <= 640px  -> teléfono (apila columnas, compacta todo)
#   <= 992px  -> tablet   (reduce padding, mantiene 2 columnas donde caben)
_RESPONSIVE_CSS = """
<style id="cp-responsive">
/* Nunca permitir scroll horizontal de la página completa en móvil. */
html, body, [data-testid="stAppViewContainer"] { overflow-x: hidden; }

/* Bloques anchos (tablas, dataframes, HTML custom) hacen su propio scroll. */
[data-testid="stDataFrame"],
[data-testid="stTable"],
[data-testid="stDataEditor"] {
  overflow-x: auto !important;
  max-width: 100% !important;
}
[data-testid="stDataFrame"] img,
.element-container img { max-width: 100%; height: auto; }

/* ── Tablet ───────────────────────────────────────────────────────────── */
@media (max-width: 992px) {
  .block-container {
    padding-left: 1.4rem !important;
    padding-right: 1.4rem !important;
  }
}

/* ── Teléfono ─────────────────────────────────────────────────────────── */
@media (max-width: 640px) {
  /* Contenedor principal: aprovechar todo el ancho disponible. */
  .block-container {
    padding-left: 0.8rem !important;
    padding-right: 0.8rem !important;
    padding-top: 3.2rem !important;
    max-width: 100% !important;
  }

  /* Columnas: apilar en vertical. Cada columna ocupa el 100% del ancho. */
  [data-testid="stHorizontalBlock"] {
    flex-wrap: wrap !important;
    gap: 0.6rem !important;
  }
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
  [data-testid="stHorizontalBlock"] > [data-testid="column"] {
    flex: 1 1 100% !important;
    width: 100% !important;
    min-width: 100% !important;
  }

  /* Titulares y texto: escala legible en teléfono. */
  h1, [data-testid="stHeading"] h1 { font-size: 1.5rem !important; line-height: 1.25 !important; }
  h2 { font-size: 1.25rem !important; line-height: 1.3 !important; }
  h3 { font-size: 1.08rem !important; line-height: 1.3 !important; }

  /* Métricas más compactas. */
  [data-testid="stMetricValue"] { font-size: 1.4rem !important; }
  [data-testid="stMetricLabel"] { font-size: 0.72rem !important; }

  /* Botones e inputs: área táctil cómoda y ancho completo. */
  .stButton > button,
  .stDownloadButton > button,
  [data-testid="stFormSubmitButton"] > button {
    width: 100% !important;
    min-height: 44px !important;
  }
  [data-testid="stTextInput"] input,
  [data-testid="stNumberInput"] input,
  [data-testid="stDateInput"] input,
  [data-baseweb="select"] > div { min-height: 42px !important; }

  /* Tabs y radios: permitir que envuelvan en vez de desbordar. */
  [data-baseweb="tab-list"] { flex-wrap: wrap !important; }

  /* Tarjetas / cabeceras HTML custom con padding grande: compactar y no
     desbordar. Cubre las de app.py, portales y los headers de cada módulo. */
  .module-card { padding: 16px 18px !important; }
  .block-container div[style*="padding:40px"],
  .block-container div[style*="padding: 40px"] { padding: 22px 20px !important; }

  /* Evitar que cualquier bloque hijo del contenedor empuje el ancho. */
  .block-container [data-testid="stVerticalBlock"] { min-width: 0 !important; }

  /* Grids HTML escritos a mano (KPIs, tarjetas de los dashboards de
     Intelligence Insight, Client Setup, etc.) que usan un número fijo de
     columnas inline: apilarlos a una sola columna en teléfono para que no
     desborden el ancho. Sólo alcanza HTML propio dentro del contenedor;
     no afecta el layout interno de Streamlit (que no usa grid inline). */
  .block-container [style*="grid-template-columns"] {
    grid-template-columns: 1fr !important;
  }

  /* Tablas HTML propias (no dataframes): que hagan scroll en vez de romper. */
  .block-container [data-testid="stMarkdownContainer"] table {
    display: block;
    overflow-x: auto;
    max-width: 100%;
    white-space: nowrap;
  }
}
</style>
"""


def inject_responsive_css() -> None:
    """Inyecta el CSS responsivo global.

    Idempotente en la práctica: se llama una vez por página (desde el auth), y
    aunque se llamara varias veces, sólo agrega `<style>` invisibles sin efecto
    acumulativo. Seguro de invocar antes de cualquier `return` de autenticación.
    """
    st.markdown(_RESPONSIVE_CSS, unsafe_allow_html=True)


# ── Panel de reuniones (componente HTML en iframe) ────────────────────────────
# El panel operativo de reuniones (panel interno y portal cliente) se renderiza
# como un componente HTML dentro de un iframe. El CSS del dashboard NO llega al
# interior del iframe, así que su comportamiento móvil se define aquí y se
# inyecta en el HTML antes de <head>. Es la única fuente del móvil del panel:
# la usan tanto `pages/1_Seguimiento_Reuniones.py` como `client_meeting_portal.py`.
#
# Se usa !important porque el template ya trae reglas de escritorio (y algún
# breakpoint de tablet) con mayor especificidad (p. ej. `.layout.open .kpis`);
# en teléfono estos overrides deben ganar siempre.
_PANEL_MOBILE_CSS = """
<style id="cp-panel-mobile">
@media (max-width:640px){
  .app{padding:0 8px 22px !important}

  /* Cabecera del panel: apilar marca / meta / usuario en vertical. */
  .top{display:flex !important;flex-direction:column !important;align-items:stretch !important;
       height:auto !important;gap:8px !important;padding:10px 12px !important}
  .top-meta{max-width:100% !important;width:100% !important;padding:0 !important}
  .brand-logo{max-width:120px !important;height:26px !important}
  .title h1{font-size:15px !important}

  /* Filtros y KPIs: apilar para que sean usables con el pulgar. */
  .filters{grid-template-columns:1fr !important;padding:12px !important}
  .extra,.extra.open{grid-template-columns:1fr 1fr !important}
  .kpis,.layout .kpis,.layout.open .kpis{grid-template-columns:repeat(2,1fr) !important}
  .kpi,.layout.open .kpi{min-height:60px !important;padding:9px 11px !important}
  .kpi b,.layout.open .kpi b{font-size:20px !important}

  /* Detalle: ocupa el ancho completo debajo de la tabla (no columna lateral). */
  .layout,.layout.open{grid-template-columns:1fr !important}
  .drawer{position:relative !important;top:0 !important;max-height:none !important}
  .drawer-fixed{position:relative !important}
  .grid{grid-template-columns:1fr !important}
  .summary{display:grid !important;grid-template-columns:1fr 1fr !important;overflow:visible !important}
  .sum{min-width:0 !important}
  .tabs{display:flex !important;overflow-x:auto !important;-webkit-overflow-scrolling:touch}
  .tabs button{min-width:120px !important;flex:0 0 auto !important}
  .panel{padding:0 12px 16px !important}
  .actions-row{grid-template-columns:1fr !important}
  .evidence{grid-template-columns:1fr !important}
  .bant-grid{grid-template-columns:repeat(2,1fr) !important}
  .detail-band{grid-template-columns:1fr !important;padding:10px 12px !important}
  .band-main{grid-column:auto !important}

  /* Tabla: scroll horizontal propio, sin comprimir las columnas a ancho fijo. */
  .table-wrap{overflow-x:auto !important;max-height:none !important;-webkit-overflow-scrolling:touch}
  .layout.open table{table-layout:auto !important;font-size:12px !important}
  .layout.open thead th,.layout.open tbody td{padding:6px 8px !important;width:auto !important}
  .layout.open .pill{min-width:96px !important;width:auto !important;font-size:.72rem !important}

  .save-note{right:12px !important;left:12px !important;bottom:12px !important;text-align:center}
}
</style>
"""


def inject_panel_mobile_css(html: str) -> str:
    """Inserta el CSS móvil del panel de reuniones en un documento HTML completo.

    Lo agrega justo antes de `</head>` (o al inicio si no hay `<head>`), de modo
    que sus reglas queden después del `<style>` base del template y ganen por
    orden de origen además del `!important`. Idempotente: no duplica si ya está.
    """
    if "cp-panel-mobile" in html:
        return html
    marker = "</head>"
    if marker in html:
        return html.replace(marker, _PANEL_MOBILE_CSS + marker, 1)
    return _PANEL_MOBILE_CSS + html
