"""Visita la demo con un navegador real para que Streamlit Cloud no la duerma.

Un GET simple no cuenta como actividad: hay que abrir la pagina y mantener el
websocket. Si la app ya esta dormida, pulsa el boton de despertar.
"""
from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

URL = "https://conprospeccionos2026-demo.streamlit.app/demo"
WAKE_BUTTON = "Yes, get this app back up!"


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(8_000)

        boton = page.get_by_text(WAKE_BUTTON)
        if boton.count():
            print("App dormida: pulsando el boton de despertar")
            boton.first.click()
            page.wait_for_timeout(60_000)

        # La app corre dentro de un iframe en streamlit.app; basta con que
        # el login ("DEMO") o el recorrido se hayan dibujado.
        page.wait_for_timeout(20_000)
        texto = ""
        for frame in page.frames:
            try:
                texto += frame.inner_text("body", timeout=5_000)
            except Exception:
                pass
        browser.close()

    if WAKE_BUTTON in texto or not texto.strip():
        print("La app no cargo")
        return 1
    print("App activa")
    return 0


if __name__ == "__main__":
    sys.exit(main())
