"""Autenticación y navegación compartida para portales de clientes."""
from __future__ import annotations
import sys, base64, hashlib, time
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = Path(__file__).resolve().parent / "assets"

sys.path.insert(0, str(ROOT))
from shared.config import portal_passwords
from shared.planes import plan_de


def img_b64(fname: str, h: int = 56) -> str:
    p = ASSETS_DIR / fname
    if not p.exists():
        return ""
    ext = p.suffix.lstrip(".")
    d = base64.b64encode(p.read_bytes()).decode()
    return f'<img src="data:image/{ext};base64,{d}" height="{h}" style="object-fit:contain;vertical-align:middle">'


def render_bambutech_page_header(title: str, subtitle: str, meta_html: str = "") -> None:
    """Encabezado único para todos los módulos del portal BambuTech."""
    logo = img_b64("bambutech_logo.png", 48)
    st.markdown(
        f'<div style="display:flex;align-items:center;justify-content:space-between;gap:24px;'
        f'background:linear-gradient(135deg,#171a18,#2b302c);padding:18px 24px;'
        f'border-radius:14px;margin-bottom:16px;color:#fff">'
        f'<div><div style="font-size:22px;font-weight:850;line-height:1.15">{title}</div>'
        f'<div style="font-size:11px;color:#d2d8d3;margin-top:7px">{subtitle}</div></div>'
        f'<div style="display:flex;align-items:center;justify-content:flex-end;gap:18px;flex-shrink:0">'
        f'{meta_html}<div style="display:inline-flex;align-items:center;background:#07110c;'
        f'padding:8px 13px;border-radius:9px">{logo}</div></div></div>',
        unsafe_allow_html=True,
    )


def _check_login(slug: str, user: str, pwd: str) -> bool:
    expected = portal_passwords().get(slug, "")
    expected_user = {"bambutech": "Bambutech", "demo": "DEMO"}.get(slug)
    user_ok = True if expected_user is None else user.strip() == expected_user
    return bool(expected) and user_ok and pwd == expected


# ── Persistencia de sesión vía token efímero en query params ──────────────
# Streamlit Cloud pierde st.session_state cuando reconecta el WebSocket (al
# navegar/retroceder o tras inactividad). Para que la sesión se mantenga abierta
# guardamos un token derivado (hash) de la contraseña + ventana de tiempo. Nunca
# se expone la contraseña; el token caduca solo y permite reentrar sin re-login.
_TOKEN_WINDOW = 1800 # 30 min por "bucket"; se aceptan el actual y el anterior


def _token(slug: str, bucket: int) -> str:
    secret = portal_passwords().get(slug, "")
    return hashlib.sha256(f"{slug}:{secret}:{bucket}".encode()).hexdigest()[:32]


def _persist_token(slug: str) -> None:
    try:
        st.query_params["cp_s"] = slug
        st.query_params["cp_k"] = _token(slug, int(time.time() // _TOKEN_WINDOW))
    except Exception:
        pass


def _restore_from_token(slug: str, session_key: str) -> bool:
    try:
        if st.query_params.get("cp_s") != slug:
            return False
        k = st.query_params.get("cp_k", "")
        b = int(time.time() // _TOKEN_WINDOW)
        if k and k in (_token(slug, b), _token(slug, b - 1)):
            st.session_state[session_key] = True
            return True
    except Exception:
        return False
    return False


def _clear_token() -> None:
    try:
        for q in ("cp_s", "cp_k"):
            if q in st.query_params:
                del st.query_params[q]
    except Exception:
        pass


_CLIENTS: dict[str, dict] = {
    "bambutech": {
        "session_key": "portal_auth_bambutech",
        "logo_file": "bambutech_logo.png",
        "nav": [
            ("Inicio portal", "pages/15_BambooTech.py", "base"),
            ("Onboarding", "pages/17_BambuTech_Onboarding.py", "base"),
            ("Validación de reuniones", "pages/18_BambuTech_Validacion_Reuniones.py", "base"),
            ("Intelligence Insight", "pages/19_BambuTech_Intelligence_Insight.py", "premium"),
            ("Playbook SDR", "pages/20_BambuTech_Playbook_SDR.py", "base"),
        ],
    },
    "gbs": {
        "session_key": "portal_auth_gbs",
        "logo_file": "gbs_logo.png",
        "nav": [
            ("Validación de reuniones", "pages/12_GBS.py", "premium"),
        ],
    },
    # Portal demo para prospectos. Vive en la app aparte `demo/app.py`, no en
    # el panel interno: sus rutas son relativas a demo/, no a dashboard/.
    "demo": {
        "session_key": "portal_auth_demo",
        "logo_file": "conprospeccion_logo.png",
        "nav": [
            ("Onboarding", "pages/demo.py", "demo"),
            ("Seguimiento de Reuniones", "pages/demo_reuniones.py", "demo"),
            ("Intelligence Insight", "pages/demo_intelligence.py", "demo"),
        ],
    },
}


def render_client_nav(current: str, cliente: str) -> None:
    """Sidebar personalizado para el portal cliente. Oculta la navegación interna."""
    cfg = _CLIENTS[cliente]
    st.markdown(
        '<style>[data-testid="stSidebarNav"]{display:none!important}</style>',
        unsafe_allow_html=True,
    )

    # Botón "Atrás" al hub interno — SOLO para el equipo de Conprospección (admin),
    # no para el cliente (esa ruta pide login de admin y no le corresponde).
    if st.session_state.get("admin_mode"):
        col_back, _ = st.columns([1, 7])
        with col_back:
            if st.button("← Atrás", key=f"back_btn_{current}", use_container_width=True):
                st.switch_page("pages/2_Clientes.py")

    with st.sidebar:
        # Admin: botón volver al menú principal en lugar del logout
        if st.session_state.get("admin_mode"):
            if st.button("← Volver al menú", use_container_width=True, key="back_to_clientes"):
                st.switch_page("pages/2_Clientes.py")
            st.markdown("---")

        # Color de acento por cliente (GBS = morado de marca).
        if cliente == "bambutech":
            nav_accent, nav_accent2 = "#38d430", "#208d25"
        elif cliente == "demo":
            # Dorado oscuro de Conprospeccion: legible como fondo con texto blanco.
            nav_accent, nav_accent2 = "#A66A00", "#7A4F00"
        else:
            nav_accent = "#7c3aed" if cliente == "gbs" else "#1e40af"
            nav_accent2 = "#5b21b6" if cliente == "gbs" else "#1e3a8a"

        logo = img_b64(cfg["logo_file"], 44)
        if cliente != "bambutech":
            st.markdown(
                f'<div style="text-align:center;padding:18px 0 10px">{logo}</div>'
                if logo else
                f'<div style="text-align:center;padding:18px 0 10px;font-weight:800;'
                f'font-size:18px;color:{nav_accent}">{cliente.upper()}</div>',
                unsafe_allow_html=True,
            )
        st.markdown("---")

        # Todos los items son el MISMO botón (misma alineación siempre). Al activo solo
        # se le cambia el color con CSS, para que nada se "desordene" según la página.
        # Los módulos contratables permanecen visibles. La página de destino explica
        # cuando un plan todavía no habilita su contenido.
        def _nav_key(path: str) -> str:
            return "nav_" + path.replace("/", "_").replace(".", "_").replace(" ", "_")

        items = cfg["nav"]

        active_key = next((_nav_key(it[1]) for it in items if current in it[1]), None)
        if active_key:
            st.markdown(
                f'<style>'
                f'[class*="st-key-{active_key}"] button{{'
                f'background:linear-gradient(135deg,{nav_accent},{nav_accent2})!important;'
                f'color:#fff!important;border:none!important;font-weight:800!important;'
                f'box-shadow:0 3px 10px {nav_accent}55!important}}'
                f'[class*="st-key-{active_key}"] button p{{color:#fff!important;font-weight:800!important}}'
                f'</style>',
                unsafe_allow_html=True,
            )

        for it in items:
            label, path = it[0], it[1]
            if cfg.get("solo_modulo"):
                continue
            es_activa = current in path
            if st.button(label, use_container_width=True, key=_nav_key(path)) and not es_activa:
                st.switch_page(path)
        st.markdown("---")
        if not st.session_state.get("admin_mode"):
            if st.button("Cerrar sesión", use_container_width=True):
                st.session_state[cfg["session_key"]] = False
                _clear_token()
                st.rerun()


def require_auth_client(cliente: str) -> bool:
    """Muestra login si no autenticado (retorna False). Si autenticado retorna True."""
    cfg = _CLIENTS[cliente]
    if st.session_state.get(cfg["session_key"]):
        return True
    # Admin interno: si navegó desde el dashboard principal, no pide login
    if st.session_state.get("admin_mode"):
        return True
    # Sesión persistente: restaurar desde token efímero (sobrevive reconexiones)
    if _restore_from_token(cliente, cfg["session_key"]):
        return True

    if cliente == "bambutech":
        accent, accent2 = "#38d430", "#208d25"
        login_bg = "linear-gradient(135deg,#f4f6f4 0%,#e8eee9 55%,#f8faf8 100%)"
    elif cliente == "demo":
        accent, accent2 = "#A66A00", "#7A4F00"
        login_bg = "linear-gradient(135deg,#FAFAF8 0%,#FFF7BF 55%,#FAFAF8 100%)"
    else:
        accent = "#7c3aed" if cliente == "gbs" else "#1e40af"
        accent2 = "#db2777" if cliente == "gbs" else "#2563eb"
        login_bg = "linear-gradient(135deg,#faf5ff 0%,#ede9fe 55%,#f5f3ff 100%)"
    st.markdown(f"""
    <style>
    .stApp {{
        background: {login_bg} !important;
    }}
    [data-testid="stSidebar"] {{ display:none !important; }}
    [data-testid="collapsedControl"] {{ display:none !important; }}
    header[data-testid="stHeader"] {{ display:none !important; }}
    [data-testid="stToolbar"] {{ display:none !important; }}
    [data-testid="stDecoration"] {{ display:none !important; }}
    footer {{ display:none !important; }}
    #MainMenu{{ display:none !important; }}
    .block-container {{ padding-top:1.6rem !important; padding-bottom:1rem !important; max-width:560px; }}
    /* Campos legibles: fondo blanco, texto oscuro, foco en color del cliente */
    [data-testid="stTextInput"] input {{
        background:#ffffff !important; color:#1e293b !important;
        border:1px solid #e2e8f0 !important; border-radius:10px !important;
        padding:10px 14px !important;
    }}
    [data-testid="stTextInput"] input::placeholder {{ color:#94a3b8 !important; }}
    [data-testid="stTextInput"] input:focus {{
        border-color:{accent} !important; box-shadow:0 0 0 2px {accent}33 !important;
    }}
    button[kind="primaryFormSubmit"] {{
        background:linear-gradient(135deg,{accent},{accent2}) !important;
        border:none !important; color:#fff !important; font-weight:700 !important;
        border-radius:10px !important; padding:10px 0 !important;
    }}
    button[kind="primaryFormSubmit"]:hover {{ filter:brightness(1.06); }}
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 5, 1])
    with col:
        logo_html = img_b64(cfg["logo_file"], 64) or (
            f'<div style="background:{accent};color:#fff;padding:14px 30px;'
            f'border-radius:12px;font-size:24px;font-weight:900;letter-spacing:3px">'
            f'{cliente.upper()}</div>'
        )
        if cliente == "bambutech" and img_b64(cfg["logo_file"], 64):
            logo_html = (
                '<div style="display:inline-flex;align-items:center;'
                'background:linear-gradient(135deg,#07110c,#0e1b15);'
                'padding:16px 30px;border-radius:16px">' + logo_html + '</div>'
            )
        st.markdown(
            f'<div style="text-align:center;padding:6px 0 14px">'
            f'{logo_html}'
            f'<div style="color:#1e293b;font-size:21px;font-weight:800;margin-top:10px">'
            f'Portal Cliente</div>'
            f'<div style="color:{accent};font-size:13px;font-weight:600;margin-top:3px">'
            f'Ingresa tus credenciales para continuar</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        with st.form(f"login_form_{cliente}", clear_on_submit=False):
            st.markdown(
                '<div style="background:#ffffff;border:1px solid #e9d5ff;'
                'border-radius:16px;padding:6px 4px;box-shadow:0 4px 16px rgba(124,58,237,.08)"></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div style="color:#334155;font-size:13px;font-weight:600;margin-bottom:6px">'
                'Usuario</div>', unsafe_allow_html=True)
            user = st.text_input("Usuario", placeholder="Nombre de usuario",
                                 label_visibility="collapsed", key=f"lu_{cliente}")
            st.markdown(
                '<div style="color:#334155;font-size:13px;font-weight:600;margin:10px 0 6px">'
                'Contraseña</div>', unsafe_allow_html=True)
            pwd = st.text_input("Contraseña", type="password", placeholder="••••••••",
                                label_visibility="collapsed", key=f"lp_{cliente}")
            st.markdown('<div style="margin-top:6px"></div>', unsafe_allow_html=True)
            submitted = st.form_submit_button("Ingresar ", use_container_width=True, type="primary")
            st.markdown('</div>', unsafe_allow_html=True)

            if submitted:
                if _check_login(cliente, user, pwd):
                    st.session_state[cfg["session_key"]] = True
                    _persist_token(cliente)
                    st.rerun()
                else:
                    st.markdown(
                        '<div style="background:#fef2f2;border:1px solid #fca5a5;border-radius:8px;'
                        'padding:10px 14px;color:#991b1b;font-weight:600;margin-top:8px;text-align:center">'
                        'Usuario o contraseña incorrectos</div>',
                        unsafe_allow_html=True,
                    )

        cp = img_b64("conprospeccion_logo.png", 22) or ""
        st.markdown(
            f'<div style="text-align:center;color:#64748b;font-size:12px;margin-top:14px">'
            f'{cp}&nbsp;Powered by <a href="https://conprospeccion.com" target="_blank" '
            f'rel="noopener" style="color:#111827;font-weight:700;text-decoration:none">'
            f'Conprospección</a></div>',
            unsafe_allow_html=True,
        )
    return False


# Alias retrocompatible para las páginas de Tiresias existentes
def logout_client(cliente: str) -> None:
    """Cierra sesión del portal cliente y limpia token persistente."""
    cfg = _CLIENTS[cliente]
    st.session_state[cfg["session_key"]] = False
    _clear_token()


def require_auth_bambutech() -> bool:
    return require_auth_client("bambutech")
