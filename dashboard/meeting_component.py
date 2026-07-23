from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components


def render_meeting_component(
    component_dir: Path,
    key: str,
    name: str = "seguimiento_reuniones_operativo",
):
    """Monta el panel operativo desde `component_dir`.

    `name` DEBE ser distinto por cada directorio. El registro de componentes de
    Streamlit es global a la aplicacion, no por sesion: registrar dos veces el
    mismo nombre con rutas distintas sobrescribe la primera ("overriding
    previously-registered"). Si el panel interno y el portal demo compartieran
    nombre, la ultima pagina visitada se quedaria con el componente y la otra
    serviria el HTML equivocado.
    """
    try:
        component = components.declare_component(name, path=str(component_dir))
        return component(default=None, key=key)
    except RuntimeError as exc:
        if "module is None" not in str(exc):
            raise
        index_path = component_dir / "index.html"
        if index_path.exists():
            components.html(index_path.read_text(encoding="utf-8"), height=920, scrolling=True)
        return None
