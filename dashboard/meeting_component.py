from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components


def render_meeting_component(component_dir: Path, key: str):
    component = components.declare_component(
        "seguimiento_reuniones_operativo",
        path=str(component_dir),
    )
    return component(default=None, key=key)
