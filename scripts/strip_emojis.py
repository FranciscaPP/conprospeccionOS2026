"""Elimina emojis/iconos pictográficos de los archivos de dashboard (look profesional).

Seguro: borra el emoji (+ selector de variación/ZWJ) y como mucho UN espacio/tab
adyacente. Nunca toca saltos de línea ni la indentación. Conserva tipografía
profesional (· — • → no se tocan salvo flechas decorativas listadas abajo).
"""
import re
import sys
from pathlib import Path

# Rangos pictográficos (emojis). NO incluye · (00B7), — (2014), • (2022).
EMOJI = re.compile(
    "(?:"
    "[\U0001F000-\U0001FAFF]"   # emoticons, símbolos, transporte, suplementarios
    "|[\U00002300-\U000023FF]"  # ⏳ ⌛ ⏰ ⌚ técnicos
    "|[\U00002600-\U000027BF]"  # misc symbols + dingbats (✅ ❌ ✉ ✕ ✨ …)
    "|[\U00002B00-\U00002BFF]"  # ⭐ flechas decorativas, estrellas
    "|[\U0001F1E6-\U0001F1FF]"  # banderas
    "|[\U000021A9-\U000021BB]"  # ↺ ↩ ↪ (reset/retorno decorativos)
    "|→"                    # → flecha
    "|⬇|⬆"            # ⬇ ⬆
    ")[️‍]*[ \t]?"
)


def limpiar(texto: str) -> str:
    nuevo = EMOJI.sub("", texto)
    # Espacios dobles que pudieran quedar dentro de una línea (no toca indentación: usa look)
    nuevo = re.sub(r"(?<=\S)  +(?=\S)", " ", nuevo)
    return nuevo


def main(paths):
    cambiados = 0
    for p in paths:
        f = Path(p)
        if not f.exists():
            continue
        orig = f.read_text(encoding="utf-8")
        new = limpiar(orig)
        if new != orig:
            f.write_text(new, encoding="utf-8")
            cambiados += 1
            print("limpiado:", p)
    print(f"--- {cambiados} archivos modificados ---")


if __name__ == "__main__":
    main(sys.argv[1:])
