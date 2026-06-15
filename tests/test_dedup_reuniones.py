"""Test de la función pura de dedup (se corre con `python tests/test_dedup_reuniones.py`)."""
import sys
from pathlib import Path
import pandas as pd

_PAGE = Path(__file__).resolve().parent.parent / "dashboard" / "pages" / "1_Seguimiento_Reuniones.py"


def _load():
    """Carga solo el bloque de funciones puras (sin ejecutar la app Streamlit)."""
    src = _PAGE.read_text(encoding="utf-8")
    ini = src.index("# <<DEDUP-PURO>>")
    fin = src.index("# <<DEDUP-PURO-FIN>>")
    ns = {"pd": pd}
    exec(src[ini:fin], ns)
    return ns


def test_dedup_mantiene_ultima_fecha():
    ns = _load()
    df = pd.DataFrame([
        {"id": 1, "cliente_slug": "gbs", "opportunity_id": "A", "email": "x@e.cl", "contacto": "Ana", "empresa": "E", "fecha": pd.Timestamp("2026-05-01")},
        {"id": 2, "cliente_slug": "gbs", "opportunity_id": "A", "email": "x@e.cl", "contacto": "Ana", "empresa": "E", "fecha": pd.Timestamp("2026-06-10")},
        {"id": 3, "cliente_slug": "gbs", "opportunity_id": "",  "email": "y@e.cl", "contacto": "Bob", "empresa": "E", "fecha": pd.Timestamp("2026-05-20")},
    ])
    out = ns["deduplicar_reuniones"](df)
    ids = set(out["id"])
    assert ids == {2, 3}, f"esperaba quedarme con 2 y 3, obtuve {ids}"


def test_dedup_separa_por_cliente():
    ns = _load()
    df = pd.DataFrame([
        {"id": 1, "cliente_slug": "gbs",     "opportunity_id": "", "email": "z@e.cl", "contacto": "C", "empresa": "E", "fecha": pd.Timestamp("2026-05-01")},
        {"id": 2, "cliente_slug": "clickie", "opportunity_id": "", "email": "z@e.cl", "contacto": "C", "empresa": "E", "fecha": pd.Timestamp("2026-05-01")},
    ])
    out = ns["deduplicar_reuniones"](df)
    assert set(out["id"]) == {1, 2}, "no debe deduplicar entre clientes distintos"


if __name__ == "__main__":
    test_dedup_mantiene_ultima_fecha()
    test_dedup_separa_por_cliente()
    print("OK dedup")
