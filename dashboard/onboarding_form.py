"""Formulario reutilizable de onboarding comercial para portales cliente."""
from __future__ import annotations

import html
from datetime import date
from pathlib import Path
from typing import Any

import requests
import streamlit as st
from supabase import create_client

from portal_auth import img_b64
from shared.config import supabase_key, supabase_url, telegram_chat_id, telegram_token
from shared.cp_design import CP_GOLD, CP_GOLD_SOFT, CP_INK, CP_LINE, CP_MUTED, CP_MUTED_SURFACE, CP_ORANGE


ROOT = Path(__file__).resolve().parent.parent

PAISES_LATAM_ES = [
    "Argentina", "Bolivia", "Brasil", "Chile", "Colombia", "Costa Rica", "Cuba",
    "Ecuador", "El Salvador", "España", "Guatemala", "Honduras", "México",
    "Nicaragua", "Panamá", "Paraguay", "Perú", "Puerto Rico",
    "República Dominicana", "Uruguay", "Venezuela", "Estados Unidos",
]

TAMANO_OPTS = [
    "1-10 empleados", "11-20 empleados", "21-50 empleados", "35-99 empleados",
    "51-100 empleados", "101-200 empleados", "100-999 empleados", "201-500 empleados",
    "501-1000 empleados", "1000+ empleados", "1001-2000 empleados",
    "2001-5000 empleados", "5001-10000 empleados", "10001+ empleados",
]


def _notify_telegram(client_name: str, nombre_ej: str, email_ej: str) -> None:
    token = telegram_token()
    chat_id = telegram_chat_id()
    if not token or not chat_id:
        return
    msg = (
        f"*Onboarding {client_name} recibido*\n\n"
        f"Ejecutivo: {nombre_ej or '(sin nombre)'}\n"
        f"Email: {email_ej or '(sin email)'}\n\n"
        "El formulario quedó guardado en Supabase tabla `gbs\\_onboarding`."
    )
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
            timeout=8,
        )
    except Exception:
        pass


def _escape(value: Any) -> str:
    return html.escape(str(value or ""))


def _list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()]
    return [x.strip() for x in str(value).replace("\n", ",").split(",") if x.strip()]


def _summary(data: dict[str, Any]) -> dict[str, Any]:
    paises = _list(data.get("icp_pais"))
    cargos = _list(data.get("icp_cargos"))
    industrias = _list(data.get("icp_industrias"))
    tamano = _list(data.get("icp_tamano"))
    resumen = (
        f"Prospectar empresas en {', '.join(paises) or 'mercados por confirmar'}, "
        f"principalmente {', '.join(industrias[:4]) or 'industrias por confirmar'}, "
        f"con decisores {', '.join(cargos[:4]) or 'por confirmar'}."
    )
    return {
        "resumen": resumen,
        "paises": paises,
        "cargos": cargos,
        "industrias": industrias,
        "tamano_resumido": ", ".join(tamano) or "Por confirmar",
        "exclusiones": _list(data.get("icp_descarte")),
        "complementos": {
            "Criterio adicional": data.get("icp_adicional", ""),
            "Propuesta de valor": data.get("propuesta_valor", ""),
            "Dolores prioritarios": data.get("dolores_clientes", ""),
            "Gatillos de compra": data.get("gatillos_compra", ""),
        },
    }


def render_onboarding_form(cfg: dict[str, Any]) -> None:
    """Renderiza el onboarding editable estilo GBS antiguo."""
    slug = cfg["slug"]
    client_name = cfg["client_name"]
    prefix = f"{slug}_onb_"
    accent = cfg.get("accent", CP_GOLD)
    accent_2 = cfg.get("accent_2", CP_ORANGE)
    soft = cfg.get("soft", CP_GOLD_SOFT)
    border = cfg.get("border", "#F0D28D")
    ink = cfg.get("ink", CP_INK)
    defaults = cfg.get("defaults", {})

    def key(name: str) -> str:
        return prefix + name

    def val(name: str, fallback: Any = "") -> Any:
        return defaults.get(name, fallback)

    def current(name: str, fallback: Any = "") -> Any:
        return st.session_state.get(key(name), val(name, fallback))

    def build_payload() -> dict[str, Any]:
        return {
            "cliente": slug,
            "updated_at": "now()",
            "icp_pais": ", ".join(current("icp_pais", []) or []),
            "icp_cargos": "\n".join(current("icp_cargos", []) or []),
            "icp_industrias": "\n".join(current("icp_industrias", []) or []),
            "icp_tamano": ", ".join(current("icp_tamano", []) or []),
            "icp_adicional": current("icp_adicional", ""),
            "icp_descarte": "\n".join(current("icp_descarte", []) or []),
            "web": current("web", ""),
            "linkedin_empresa": current("linkedin_empresa", ""),
            "propuesta_valor": current("propuesta_valor", ""),
            "diferenciadores": current("diferenciadores", ""),
            "presentacion_servicio": current("presentacion_servicio", ""),
            "casos_exito": current("casos_exito", ""),
            "tono_lenguaje": current("tono_lenguaje", ""),
            "mensajes_funcionan": current("mensajes_funcionan", ""),
            "mensajes_no_decir": current("mensajes_no_decir", ""),
            "objeciones": current("objeciones", ""),
            "nombre_ejecutivo": current("nombre_ejecutivo", ""),
            "cargo_ejecutivo": current("cargo_ejecutivo", ""),
            "email_ejecutivo": current("email_ejecutivo", ""),
            "proceso_comercial": current("proceso_comercial", ""),
            "duracion_reunion": current("duracion_reunion", ""),
            "intervalo_reunion": current("intervalo_reunion", ""),
            "anticipacion_agenda": current("anticipacion_agenda", ""),
            "notificaciones": current("notificaciones", ""),
            "tiempo_cierre": int(current("tiempo_cierre", 45)),
            "ticket_promedio": current("ticket_promedio", ""),
            "plan_contratado": current("plan_contratado", ""),
            "preguntas_discovery": current("preguntas_discovery", ""),
            "dolores_clientes": current("dolores_clientes", ""),
            "gatillos_compra": current("gatillos_compra", ""),
            "keywords_prospecto": current("keywords_prospecto", ""),
            "notas_adicionales": current("notas_adicionales", ""),
        }

    def save_payload(success_text: str) -> dict[str, Any] | None:
        payload = build_payload()
        try:
            create_client(supabase_url(), supabase_key()).table("gbs_onboarding").upsert(
                payload, on_conflict="cliente"
            ).execute()
            st.toast(success_text)
            st.success(success_text)
            return payload
        except Exception as exc:
            st.error(f"Error al guardar el formulario: {exc}")
            return None

    st.markdown(
        f"""
<style>
.block-container{{max-width:1180px;padding-top:1rem!important}}
div[class*="st-key-{prefix}submit"] button,
div[class*="st-key-{prefix}save"] button{{
  background:{accent}!important;border:none!important;color:{ink}!important;font-weight:800!important
}}
span[data-baseweb="tag"]{{background:{soft}!important;color:{ink}!important}}
span[data-baseweb="tag"] span{{color:{ink}!important}}
.onb-source{{background:#fff;border:1px solid {CP_LINE};border-radius:8px;padding:13px 15px}}
.onb-source b{{color:{ink};font-size:13px}}.onb-source p{{color:{CP_MUTED};font-size:12px;line-height:1.45;margin:6px 0 0}}
</style>
        """,
        unsafe_allow_html=True,
    )

    logo = img_b64(cfg.get("logo_file", ""), 56) or (
        f'<div style="background:{accent};color:{ink};padding:10px 22px;border-radius:8px;'
        f'font-size:18px;font-weight:850">{client_name}</div>'
    )
    cp_logo = img_b64("conprospeccion_logo.png", 44) or ""
    st.markdown(
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'background:linear-gradient(135deg,{soft},#fff);padding:18px 28px;'
        f'border-radius:14px;border:1px solid {border};margin-bottom:8px;'
        f'box-shadow:0 2px 8px rgba(0,0,0,.06)">'
        f'<div style="display:flex;align-items:center;gap:18px">{logo}'
        f'<div><div style="font-size:22px;font-weight:850;color:{ink}">Formulario de Onboarding</div>'
        f'<div style="font-size:13px;color:{CP_MUTED};margin-top:3px">'
        f'Completar antes del inicio del proyecto. Esta información define ICP, mensajes y agenda.</div>'
        f'</div></div>{cp_logo}</div>',
        unsafe_allow_html=True,
    )

    def section(title: str, section_id: str) -> None:
        st.markdown(
            f'<div style="background:linear-gradient(135deg,{accent_2},{accent});color:{ink};'
            f'border-radius:10px;padding:12px 20px;margin:24px 0 8px;font-size:15px;font-weight:850">'
            f'{title}</div>',
            unsafe_allow_html=True,
        )
        save_col, _ = st.columns([1, 5])
        with save_col:
            if st.button("Guardar", use_container_width=True, key=f"{prefix}save_{section_id}"):
                save_payload(f"{title} guardado.")

    section("Definición del ICP (Perfil de Cliente Ideal)", "icp")
    st.markdown(
        f'<div style="background:{soft};border:1px solid {border};border-left:4px solid {accent};'
        f'border-radius:10px;padding:12px 16px;margin-bottom:16px;font-size:13px;color:{ink}">'
        f'<b>Primer paso, y el más importante.</b> Ajusta países, cargos, industrias, tamaño, '
        f'exclusiones y criterio adicional antes de avanzar.</div>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.multiselect("País(es) objetivo", PAISES_LATAM_ES, default=val("icp_pais", []), key=key("icp_pais"))
        st.multiselect("Cargos objetivo", cfg["cargo_opts"], default=val("icp_cargos", []), key=key("icp_cargos"))
        st.multiselect("Tamaño de empresa (n.º de empleados)", TAMANO_OPTS, default=val("icp_tamano", []), key=key("icp_tamano"))
    with c2:
        st.multiselect("Industrias objetivo", cfg["industria_opts"], default=val("icp_industrias", []), key=key("icp_industrias"))
        st.text_area("Criterio adicional ICP (diferenciador de calidad)", value=val("icp_adicional", ""), height=100, key=key("icp_adicional"))

    c3, c4 = st.columns(2)
    with c3:
        st.multiselect("Industrias o segmentos a excluir de la prospección", cfg["descarte_opts"], default=val("icp_descarte", []), key=key("icp_descarte"))
    with c4:
        st.file_uploader("Clientes actuales (CSV o XLSX)", type=["csv", "xlsx"], key=key("clientes_actuales"))

    section("Empresa y Marca", "empresa")
    c5, c6 = st.columns(2)
    with c5:
        st.text_input("Página web", value=val("web", ""), key=key("web"))
        st.text_input("LinkedIn empresa", value=val("linkedin_empresa", ""), key=key("linkedin_empresa"))
        st.text_area("Propuesta de valor", value=val("propuesta_valor", ""), height=120, key=key("propuesta_valor"))
    with c6:
        st.text_area("Diferenciadores vs. la competencia", value=val("diferenciadores", ""), height=100, key=key("diferenciadores"))
        st.text_area("Presentación del servicio", value=val("presentacion_servicio", ""), height=100, key=key("presentacion_servicio"))

    c7, c8 = st.columns(2)
    with c7:
        st.file_uploader("Archivos de marca (logos, brochure, imagen corporativa)", type=["png", "jpg", "jpeg", "pdf", "zip"], accept_multiple_files=True, key=key("archivos_marca"))
    with c8:
        st.text_area("Casos de éxito", value=val("casos_exito", ""), height=100, key=key("casos_exito"))

    section("Mensajería y Tono de Comunicación", "mensajeria")
    c9, c10 = st.columns(2)
    with c9:
        st.selectbox("Tipo de lenguaje a usar", cfg["tono_opts"], index=cfg.get("tono_index", 0), key=key("tono_lenguaje"))
        st.text_area("Ejemplos de mensajes que han funcionado", value=val("mensajes_funcionan", ""), height=120, key=key("mensajes_funcionan"))
    with c10:
        st.text_area("Frases o mensajes a evitar", value=val("mensajes_no_decir", ""), height=100, key=key("mensajes_no_decir"))
        st.text_area("Principales objeciones recibidas", value=val("objeciones", ""), height=100, key=key("objeciones"))

    section("Proceso Comercial y Configuración de Agenda", "proceso")
    c11, c12 = st.columns(2)
    with c11:
        st.text_input("Nombre del ejecutivo que toma las reuniones", value=val("nombre_ejecutivo", ""), key=key("nombre_ejecutivo"))
        st.text_input("Cargo del ejecutivo", value=val("cargo_ejecutivo", ""), key=key("cargo_ejecutivo"))
        st.text_input("Email del ejecutivo", value=val("email_ejecutivo", ""), key=key("email_ejecutivo"))
        st.text_area("Proceso comercial paso a paso", value=val("proceso_comercial", ""), height=100, key=key("proceso_comercial"))
    with c12:
        st.selectbox("Duración de las reuniones", ["30 minutos", "45 minutos", "60 minutos"], index=cfg.get("duracion_index", 0), key=key("duracion_reunion"))
        st.selectbox("Tiempo de preparación entre reuniones", ["15 minutos", "30 minutos", "45 minutos", "60 minutos", "90 minutos"], index=1, key=key("intervalo_reunion"))
        st.selectbox("Tiempo máximo de anticipación para agendar", ["24 horas", "48 horas", "1 semana", "2 semanas"], index=1, key=key("anticipacion_agenda"))
        st.text_area("Quiénes reciben la info del lead agendado", value=val("notificaciones", ""), height=80, key=key("notificaciones"))

    c13, c14 = st.columns(2)
    with c13:
        st.number_input("Tiempo promedio de cierre (días)", min_value=7, max_value=365, value=int(val("tiempo_cierre", 45)), key=key("tiempo_cierre"))
    with c14:
        st.text_input("Costo promedio del servicio (ticket promedio)", value=val("ticket_promedio", ""), key=key("ticket_promedio"))
    st.radio("Plan contratado con Conprospección", ["Starter", "Growth"], horizontal=True, key=key("plan_contratado"), index=1 if val("plan_contratado", "Growth") == "Growth" else 0)

    section("Inteligencia Comercial Adicional (Recomendado)", "inteligencia")
    c15, c16 = st.columns(2)
    with c15:
        st.text_area("¿Qué preguntas de discovery funcionan mejor en las reuniones?", value=val("preguntas_discovery", ""), height=100, key=key("preguntas_discovery"))
        st.text_area("¿Cuáles son los dolores más frecuentes que reportan los clientes actuales?", value=val("dolores_clientes", ""), height=100, key=key("dolores_clientes"))
    with c16:
        st.text_area("¿Qué gatillos de compra activan la decisión?", value=val("gatillos_compra", ""), height=100, key=key("gatillos_compra"))
        st.text_area("¿Qué palabras clave usan los prospectos en LinkedIn / emails?", value=val("keywords_prospecto", ""), height=100, key=key("keywords_prospecto"))

    st.text_area("Notas adicionales para el equipo de Conprospección", value=val("notas_adicionales", ""), height=100, key=key("notas_adicionales"))

    data = {
        "icp_pais": st.session_state.get(key("icp_pais"), []),
        "icp_cargos": st.session_state.get(key("icp_cargos"), []),
        "icp_industrias": st.session_state.get(key("icp_industrias"), []),
        "icp_tamano": st.session_state.get(key("icp_tamano"), []),
        "icp_adicional": st.session_state.get(key("icp_adicional"), ""),
        "icp_descarte": st.session_state.get(key("icp_descarte"), []),
        "propuesta_valor": st.session_state.get(key("propuesta_valor"), ""),
        "dolores_clientes": st.session_state.get(key("dolores_clientes"), ""),
        "gatillos_compra": st.session_state.get(key("gatillos_compra"), ""),
        "keywords_prospecto": st.session_state.get(key("keywords_prospecto"), ""),
    }
    profile = _summary(data)
    st.markdown(
        f'<div id="{slug}-resumen-icp" style="scroll-margin-top:72px;background:#fff;'
        f'border:1px solid {border};border-left:6px solid {accent};border-radius:12px;'
        f'padding:18px 20px;margin:24px 0 18px">'
        f'<div style="font-size:16px;font-weight:850;color:{ink}">Resumen ICP acordado</div>'
        f'<div style="font-size:12px;color:{CP_MUTED};margin:4px 0 14px">'
        f'Este perfil se construye con la definición ICP y las señales comerciales del onboarding.</div>'
        f'<div style="background:{soft};border:1px solid {border};border-radius:9px;'
        f'padding:10px 13px;margin-bottom:12px;font-size:13px;font-weight:800;color:{ink}">'
        f'{_escape(profile["resumen"])}</div>'
        f'<div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px">'
        f'<div><b style="color:{ink}">Países</b><br><span style="font-size:12px;color:#475569">{_escape(", ".join(profile["paises"]) or "Por confirmar")}</span></div>'
        f'<div><b style="color:{ink}">Tamaño</b><br><span style="font-size:12px;color:#475569">{_escape(profile["tamano_resumido"])}</span></div>'
        f'<div><b style="color:{ink}">Industrias</b><br><span style="font-size:12px;color:#475569">{_escape(", ".join(profile["industrias"]) or "Por confirmar")}</span></div>'
        f'<div><b style="color:{ink}">Cargos</b><br><span style="font-size:12px;color:#475569">{_escape(", ".join(profile["cargos"]) or "Por confirmar")}</span></div>'
        f'</div>'
        f'<div style="margin-top:13px"><b style="font-size:12px;color:{ink}">Exclusiones</b>'
        f'<div style="font-size:12px;color:#475569;line-height:1.5">{_escape(", ".join(profile["exclusiones"]) or "Por confirmar")}</div></div>'
        + "".join(
            f'<div style="margin-top:10px"><b style="font-size:12px;color:{ink}">{_escape(label)}</b>'
            f'<div style="font-size:12px;color:#475569;line-height:1.5">{_escape(value)}</div></div>'
            for label, value in profile["complementos"].items() if value
        )
        + '</div>',
        unsafe_allow_html=True,
    )
    summary_col, _ = st.columns([1, 5])
    with summary_col:
        if st.button("Guardar", use_container_width=True, key=f"{prefix}save_resumen"):
            save_payload("Resumen ICP guardado.")

    if cfg.get("sources"):
        section("Comprobantes y fuentes del ICP", "fuentes")
        cols = st.columns(min(4, len(cfg["sources"])))
        for idx, source in enumerate(cfg["sources"]):
            with cols[idx % len(cols)]:
                st.markdown(
                    f'<div class="onb-source"><b>{_escape(source["title"])}</b>'
                    f'<p>{_escape(source["detail"])}</p></div>',
                    unsafe_allow_html=True,
                )

    st.markdown("<br>", unsafe_allow_html=True)
    send_col, _ = st.columns([1, 3])
    with send_col:
        if st.button("Enviar formulario a Conprospección", type="primary", use_container_width=True, key=key("submit")):
            payload = save_payload("Formulario enviado y guardado correctamente.")
            if payload:
                _notify_telegram(client_name, payload["nombre_ejecutivo"], payload["email_ejecutivo"])

    cp = img_b64("conprospeccion_logo.png", 18) or ""
    st.markdown(
        f'<div style="text-align:center;color:#94a3b8;font-size:11px;margin-top:40px;padding:16px">'
        f'{cp}&nbsp;Formulario de Onboarding - <b style="color:{ink}">Conprospección</b> · '
        f'Confidencial · {date.today().strftime("%B %Y").capitalize()}</div>',
        unsafe_allow_html=True,
    )
