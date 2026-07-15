"""Portal cliente de validación de reuniones (componente HTML + persistencia)."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import requests
import streamlit as st

_DASHBOARD = Path(__file__).resolve().parent
import sys
if str(_DASHBOARD) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD))

from meeting_component import render_meeting_component
from meeting_shared import load_meetings, project_meeting_for_client
from shared.config import supabase_key, supabase_url
from shared.metas import meta_de
from shared.seguimiento import (
    cargar as cargar_seguimiento,
    payload_respuesta_cliente,
    recalcular_final_y_flags,
    registrar_historial,
)

_COMPONENT_DIR = Path(__file__).resolve().parent / "client_meeting_portal"
_TEMPLATE = (_COMPONENT_DIR / "index.html").read_text(encoding="utf-8")
_ASSETS_DIR = Path(__file__).resolve().parent / "assets"


def _asset_data_uri(fname: str, mime: str = "image/png") -> str:
    path = _ASSETS_DIR / fname
    try:
        import base64

        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    except Exception:
        return ""
    return f"data:{mime};base64,{encoded}"

SUPABASE_URL = supabase_url()
SUPABASE_KEY = supabase_key()
_HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
_WRITE_HEADERS = {**_HEADERS, "Content-Type": "application/json"}


def _client_val_to_db(value: str) -> str | None:
    raw = (value or "").strip().lower()
    if raw in {"valida", "válida", "confirmar", "confirmada"}:
        return "valida"
    if raw in {"solicita revisión", "solicitar revisión", "requiere_revision"}:
        return "requiere_revision"
    return None


def _build_html(
    *,
    client_slug: str,
    meetings: list[dict],
    title: str,
    brand: str,
    user_label: str,
    user_subtitle: str,
) -> str:
    goal = int((meta_de(client_slug) or {}).get("validas") or 0)
    projected = [project_meeting_for_client(m) for m in meetings]
    for row in projected:
        row["clientSlug"] = client_slug
    meetings_json = json.dumps(projected, ensure_ascii=True).replace("</", "<\\/")
    html = _TEMPLATE
    html = html.replace("__BRAND_MARK__", _asset_data_uri("cp_mark_dark.png"))
    html = html.replace("__MEETINGS_JSON__", meetings_json)
    html = html.replace("__CLIENT_GOAL__", str(goal))
    html = html.replace("__CLIENT_SLUG__", client_slug)
    html = html.replace("__PORTAL_TITLE__", title)
    html = html.replace("__PORTAL_BRAND__", brand)
    html = html.replace("__PORTAL_USER__", user_label)
    html = html.replace("__PORTAL_SUBTITLE__", user_subtitle)
    return html


def _guardar_respuesta_cliente(
    client_slug: str,
    reunion_id: int,
    estado: str,
    *,
    comentario: str = "",
    motivo: str | None = None,
    evidencia: str | None = None,
) -> bool:
    previous = cargar_seguimiento(client_slug).get(int(reunion_id), {})
    try:
        payload = payload_respuesta_cliente(
            int(reunion_id),
            client_slug,
            estado,
            comentario=comentario,
            motivo=motivo,
        )
    except ValueError:
        return False
    # Evidencia opcional aportada por el cliente al solicitar revisión.
    if evidencia and str(evidencia).strip() and estado == "requiere_revision":
        payload["evidencia_cliente"] = str(evidencia).strip()
    try:
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/seguimiento_reuniones",
            json=payload,
            headers={**_WRITE_HEADERS, "Prefer": "resolution=merge-duplicates,return=minimal"},
            timeout=15,
        )
    except requests.RequestException:
        return False
    if not response.ok:
        return False
    current = {**previous, **payload}
    recalculated = recalcular_final_y_flags(int(reunion_id), client_slug, fila=current)
    client_history_ok = registrar_historial(
        int(reunion_id),
        "val_estado_cli",
        previous.get("val_estado_cli"),
        estado,
        "cliente",
        "cliente",
        f"validacion_{client_slug}",
    )
    final_history_ok = registrar_historial(
        int(reunion_id),
        "val_estado_final",
        previous.get("val_estado_final"),
        recalculated["final"],
        "sistema",
        "sistema",
        f"validacion_{client_slug}",
    )
    return bool(recalculated["persisted"] and client_history_ok and final_history_ok)


def _handle_payload(client_slug: str, payload: dict) -> bool:
    if payload.get("action") != "client_response":
        return False
    meeting = payload.get("meeting") or {}
    reunion_id = meeting.get("id")
    if not reunion_id:
        return False
    estado = _client_val_to_db(payload.get("clientVal"))
    if not estado:
        return False
    return _guardar_respuesta_cliente(
        client_slug,
        int(reunion_id),
        estado,
        comentario=str(payload.get("clientComment") or ""),
        motivo=payload.get("clientReason") or None,
        evidencia=payload.get("clientEvidence") or None,
    )


def _render_portal_frame(
    *,
    client_slug: str,
    page_key: str,
    title: str,
    brand: str,
    user_label: str,
    user_subtitle: str,
) -> None:
    reload_token = st.session_state.get(f"_portal_reload_{client_slug}", 0)
    meetings = load_meetings([client_slug])
    html = _build_html(
        client_slug=client_slug,
        meetings=meetings,
        title=title,
        brand=brand,
        user_label=user_label,
        user_subtitle=user_subtitle,
    )

    component_dir = Path(tempfile.gettempdir()) / f"cp_client_portal_{client_slug}"
    component_dir.mkdir(parents=True, exist_ok=True)
    (component_dir / "index.html").write_text(html, encoding="utf-8")

    component_payload = render_meeting_component(
        component_dir,
        key=f"client_portal_{client_slug}_{reload_token}",
    )
    if isinstance(component_payload, dict) and component_payload.get("action") == "client_response":
        nonce = json.dumps(component_payload, sort_keys=True, ensure_ascii=True)
        if st.session_state.get(f"_portal_last_{client_slug}") != nonce:
            st.session_state[f"_portal_last_{client_slug}"] = nonce
            if _handle_payload(client_slug, component_payload):
                st.cache_data.clear()
                st.session_state[f"_portal_reload_{client_slug}"] = reload_token + 1
                st.toast("Respuesta guardada.")
                st.rerun()
            st.error("No fue posible guardar la respuesta. Revisa el comentario e intenta nuevamente.")


def render_client_meeting_portal(
    *,
    client_slug: str,
    page_key: str,
    title: str = "Validación de reuniones",
    brand: str = "",
    user_label: str = "Portal cliente",
    user_subtitle: str = "Validación contractual",
) -> None:
    st.markdown(
        """
<style>
[data-testid="stSidebar"],[data-testid="collapsedControl"],header[data-testid="stHeader"]{display:none!important}
.block-container{max-width:100%!important;padding:0!important}
iframe{display:block}
</style>
        """,
        unsafe_allow_html=True,
    )

    # Sin auto-refresco: la página no debe recargarse sola porque reinicia el
    # scroll, cierra el panel lateral y borra lo que el cliente está escribiendo
    # en su evaluación. Se renderiza una vez (igual que el panel interno); cada
    # interacción del cliente ya dispara un rerun natural de Streamlit.
    _render_portal_frame(
        client_slug=client_slug,
        page_key=page_key,
        title=title,
        brand=brand,
        user_label=user_label,
        user_subtitle=user_subtitle,
    )
