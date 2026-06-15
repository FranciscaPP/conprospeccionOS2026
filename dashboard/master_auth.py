"""Login master para el dashboard interno — Francisca y Yanina."""
from __future__ import annotations
import sys, base64
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = Path(__file__).resolve().parent / "assets"

sys.path.insert(0, str(ROOT))
from shared.config import master_passwords

SESSION_KEY = "master_logged_in"
USER_KEY = "master_user"

_DISPLAY_NAMES = {
    "francisca": "Francisca Polanco",
    "yanina": "Yanina",
}


def _img_b64(fname: str, h: int = 56) -> str:
    p = ASSETS_DIR / fname
    if not p.exists():
        return ""
    ext = p.suffix.lstrip(".")
    d = base64.b64encode(p.read_bytes()).decode()
    return f'<img src="data:image/{ext};base64,{d}" height="{h}" style="object-fit:contain;vertical-align:middle">'


def _check(user: str, pwd: str) -> bool:
    passwords = master_passwords()
    expected = passwords.get(user.lower().strip(), "")
    return bool(expected) and pwd == expected


def get_current_user() -> str:
    """Devuelve el nombre visible del usuario logueado, o cadena vacía."""
    return _DISPLAY_NAMES.get(st.session_state.get(USER_KEY, ""), "")


def logout() -> None:
    st.session_state[SESSION_KEY] = False
    st.session_state[USER_KEY] = ""
    st.session_state["admin_mode"] = False
    st.rerun()


def _show_login_page() -> None:
    """Muestra la pantalla de login master a pantalla completa."""
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] > .main {
        background: linear-gradient(135deg,#0f172a 0%,#1e1e2e 50%,#2d1f5e 100%) !important;
        min-height: 100vh;
    }
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    footer { display: none !important; }
    #MainMenu{ display: none !important; }
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        logo = _img_b64("conprospeccion_logo.png", 60)
        logo_div = '<div style="margin-bottom:12px">' + logo + '</div>' if logo else ""
        st.markdown(
            f'<div style="text-align:center;padding:56px 0 32px">'
            f'{logo_div}'
            f'<div style="color:#fff;font-size:32px;font-weight:900;letter-spacing:-0.5px;margin-bottom:6px">'
            f'ConprospecciónOS</div>'
            f'<div style="color:#a78bfa;font-size:14px;font-weight:500">'
            f'Plataforma operativa interna</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        with st.form("master_login_form", clear_on_submit=False):
            st.markdown(
                '<div style="background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);'
                'border-radius:18px;padding:32px 32px 24px">',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div style="color:#e2e8f0;font-size:13px;font-weight:600;margin-bottom:6px">Usuario</div>',
                unsafe_allow_html=True,
            )
            user = st.text_input(
                "Usuario", placeholder="francisca · yanina",
                label_visibility="collapsed", key="ml_user",
            )
            st.markdown(
                '<div style="color:#e2e8f0;font-size:13px;font-weight:600;margin:12px 0 6px">Contraseña</div>',
                unsafe_allow_html=True,
            )
            pwd = st.text_input(
                "Contraseña", type="password", placeholder="••••••••",
                label_visibility="collapsed", key="ml_pwd",
            )
            st.markdown('<div style="margin-top:8px"></div>', unsafe_allow_html=True)
            submitted = st.form_submit_button("Ingresar ", use_container_width=True, type="primary")
            st.markdown("</div>", unsafe_allow_html=True)

            if submitted:
                if _check(user, pwd):
                    st.session_state[SESSION_KEY] = True
                    st.session_state[USER_KEY] = user.lower().strip()
                    st.session_state["admin_mode"] = True
                    st.rerun()
                else:
                    st.markdown(
                        '<div style="background:#fef2f2;border:1px solid #fca5a5;border-radius:8px;'
                        'padding:10px 14px;color:#991b1b;font-weight:600;margin-top:10px;text-align:center">'
                        'Usuario o contraseña incorrectos</div>',
                        unsafe_allow_html=True,
                    )

        st.markdown(
            '<div style="text-align:center;color:#475569;font-size:12px;margin-top:20px">'
            'Solo para uso interno del equipo Conprospección</div>',
            unsafe_allow_html=True,
        )


def require_master_auth() -> bool:
    """
    Llama esto al inicio de cada página interna.
    - Si ya está logueado: retorna True y setea admin_mode.
    - Si no: muestra el login y retorna False (la página debe hacer st.stop() después).
    """
    if st.session_state.get(SESSION_KEY):
        st.session_state["admin_mode"] = True
        return True
    _show_login_page()
    return False


def render_master_user_sidebar() -> None:
    """Muestra el usuario logueado y botón de logout en el sidebar."""
    nombre = get_current_user()
    if not nombre:
        return
    with st.sidebar:
        st.markdown("---")
        st.markdown(
            f'<div style="padding:8px 0;font-size:12px;color:#94a3b8">'
            f'<b style="color:#e2e8f0">{nombre}</b></div>',
            unsafe_allow_html=True,
        )
        if st.button("Cerrar sesión", use_container_width=True, key="master_logout"):
            logout()
