from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components


def render_work_board_component(
    component_dir: Path,
    key: str,
    name: str = "work_project_management_board",
    **kwargs,
):
    """Monta el tablero draggable de Work and Project Management.

    Se declara desde un modulo importado, siguiendo el patron robusto de
    `meeting_component.py`; declararlo directamente en la pagina puede fallar
    en Streamlit Cloud porque el frame caller no siempre tiene modulo asociado.
    """
    component = components.declare_component(name, path=str(component_dir))
    return component(default=None, key=key, **kwargs)
