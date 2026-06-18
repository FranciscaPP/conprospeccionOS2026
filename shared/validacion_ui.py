"""Componentes visuales compartidos para la validación de reuniones (3 capas).

Fuente ÚNICA de labels, colores y HTML para que el bloque de validación se vea
idéntico en el panel interno (Seguimiento) y en el portal del cliente (Validación).
Todo es HTML/CSS puro (Plotly/Altair no funcionan en Streamlit Cloud) y sin emojis.

Reglas de color (alineadas a shared/gbs_brand):
  • Morado = marca (BANT, acentos).
  • Verde / ámbar / rojo / naranja = semántico (válida / pendiente / no válida / disputa).
Color + TEXTO siempre (nunca solo color), por accesibilidad.
"""
from __future__ import annotations
from shared.validacion import DESCRIPCION_ESTADO_FLUJO, LABEL_ESTADO_FLUJO

# ── Labels amigables (sin slugs ni nombres de plataformas) ────────────────────
LABEL_VALIDEZ = {
    "espera": "En espera",
    "valida": "Válida",
    "no_valida": "No válida",
    "requiere_revision": "Requiere revisión",
}
LABEL_FINAL = {
    "pendiente": "Pendiente",
    "valida": "Válida",
    "no_valida": "No válida",
    "en_disputa": "En revisión",
    "reagendada": "Reagendada",
    "excluida": "Excluida",
}
LABEL_STATUS = {
    "agendada": "Agendada",
    "realizada": "Realizada",
    "no_asistio_lead": "No asistió el prospecto",
    "no_asistio_cliente": "No asistió el cliente",
    "cancelada_lead": "Cancelada por el prospecto",
    "cancelada_cliente": "Cancelada por el cliente",
    "reagendada": "Reagendada",
    "pendiente_reagendar": "Pendiente de reagendar",
    "sin_info": "Sin información",
}
BANT_LABEL = {"B": "Budget", "A": "Authority", "N": "Need", "T": "Time"}

LABEL_ESTADO_COMERCIAL = {
    "pendiente_seguimiento": "Pendiente de seguimiento",
    "proximo_paso": "Próximo paso definido",
    "solicita_propuesta": "Solicita propuesta",
    "propuesta_enviada": "Propuesta enviada",
    "seguimiento_propuesta": "Seguimiento de propuesta",
    "negociacion": "En negociación",
    "no_responde": "No responde",
    "cliente_ganado": "Cliente ganado",
    "cliente_perdido": "Cliente perdido",
    "no_califica": "No califica",
}
LABEL_MOTIVO = {
    "no_calza_icp": "No cumple ICP definido",
    "bant_insuficiente": "No cumple mínimo 2 variables BANT",
    "no_realizada": "Reunión no realizada",
    "prospecto_no_asistio": "Prospecto no asistió",
    "contacto_incorrecto": "Contacto incorrecto sin derivación válida",
    "evidencia_insuficiente": "Evidencia insuficiente",
    "empresa_duplicada_excluida": "Empresa duplicada o excluida",
    "otro_contractual": "Otro motivo contractual",
}

# ── Pares de color accesibles (bg claro + texto oscuro, contraste ≥ 4.5:1) ────
_COL_VALIDEZ = {
    "valida":            ("#dcfce7", "#166534"),
    "no_valida":         ("#fee2e2", "#991b1b"),
    "espera":            ("#fef9c3", "#854d0e"),
    "requiere_revision": ("#e0e7ff", "#3730a3"),
}
_COL_FINAL = {
    "valida":     ("#dcfce7", "#166534"),
    "no_valida":  ("#fee2e2", "#991b1b"),
    "pendiente":  ("#fef9c3", "#854d0e"),
    "en_disputa": ("#ffedd5", "#9a3412"),
    "reagendada": ("#e0f2fe", "#075985"),
    "excluida":   ("#f1f5f9", "#475569"),
}
_COL_STATUS = {
    "realizada":           ("#dcfce7", "#166534"),
    "agendada":            ("#e0f2fe", "#075985"),
    "reagendada":          ("#fef9c3", "#854d0e"),
    "pendiente_reagendar": ("#fef9c3", "#854d0e"),
    "no_asistio_lead":     ("#fee2e2", "#991b1b"),
    "no_asistio_cliente":  ("#fee2e2", "#991b1b"),
    "cancelada_lead":      ("#fee2e2", "#991b1b"),
    "cancelada_cliente":   ("#fee2e2", "#991b1b"),
    "sin_info":            ("#f1f5f9", "#475569"),
}
_PURPLE_BG, _PURPLE_TX = "#ede9fe", "#5b21b6"

_COL_ESTADO_FLUJO = {
    "reunion_futura": ("#e0f2fe", "#075985"),
    "reunion_cancelada": ("#fee2e2", "#991b1b"),
    "pendiente_evaluacion_cp": ("#fef9c3", "#854d0e"),
    "pendiente_evaluacion_cliente": ("#fef9c3", "#854d0e"),
    "cliente_solicita_revision": ("#ffedd5", "#9a3412"),
    "evaluacion_cerrada_valida": ("#dcfce7", "#166534"),
    "evaluacion_cerrada_no_valida": ("#fee2e2", "#991b1b"),
}

# Tokens de capa (títulos consistentes en AMBOS dashboards)
CAP_CP    = ("Evaluación Conprospección", "#7c3aed")   # morado de marca — quién: la agencia
CAP_CLI   = ("Respuesta del cliente", "#0e7490")       # cian — quién: el cliente
CAP_FINAL = ("Validez final", "#0f172a")               # neutro fuerte


def _chip(texto: str, bg: str, color: str, *, size: str = "12px", strong: bool = True) -> str:
    fw = "700" if strong else "600"
    return (f'<span style="background:{bg};color:{color};padding:3px 11px;border-radius:9px;'
            f'font-size:{size};font-weight:{fw};display:inline-block;white-space:nowrap">{texto}</span>')


def chip_validez(estado) -> str:
    e = (estado or "espera")
    bg, tx = _COL_VALIDEZ.get(e, ("#f1f5f9", "#475569"))
    return _chip(LABEL_VALIDEZ.get(e, "En espera"), bg, tx)


def chip_final(estado) -> str:
    e = (estado or "pendiente")
    bg, tx = _COL_FINAL.get(e, ("#f1f5f9", "#475569"))
    return _chip(LABEL_FINAL.get(e, "Pendiente"), bg, tx)


def chip_status(status) -> str:
    e = (status or "agendada")
    bg, tx = _COL_STATUS.get(e, ("#f1f5f9", "#475569"))
    return _chip(LABEL_STATUS.get(e, "Agendada"), bg, tx, size="11px")


def chip_estado_flujo(estado) -> str:
    e = estado or "pendiente_evaluacion_cp"
    bg, tx = _COL_ESTADO_FLUJO.get(e, ("#f1f5f9", "#475569"))
    return _chip(LABEL_ESTADO_FLUJO.get(e, e), bg, tx, size="11px")


def tarjeta_estado_flujo(estado) -> str:
    e = estado or "pendiente_evaluacion_cp"
    bg, tx = _COL_ESTADO_FLUJO.get(e, ("#f1f5f9", "#475569"))
    return (
        f'<div style="background:{bg};border:1px solid {tx}33;border-left:5px solid {tx};'
        f'border-radius:10px;padding:12px 16px;margin:10px 0 14px">'
        f'<div style="font-size:14px;font-weight:800;color:{tx}">'
        f'{LABEL_ESTADO_FLUJO.get(e, e)}</div>'
        f'<div style="font-size:12px;color:{tx};opacity:.85;margin-top:3px">'
        f'{DESCRIPCION_ESTADO_FLUJO.get(e, "")}</div></div>'
    )


def bant_chips(lista) -> str:
    """Chips BANT (B·A·N·T) en morado de marca. '—' si no hay ninguno."""
    items = [x for x in (lista or []) if x in BANT_LABEL]
    if not items:
        return ""
    return " ".join(
        f'<span style="background:{_PURPLE_BG};color:{_PURPLE_TX};padding:2px 9px;'
        f'border-radius:7px;font-size:12px;font-weight:700;display:inline-block" '
        f'title="{BANT_LABEL[x]}">{x}</span>'
        for x in items)


def mini_label(txt: str) -> str:
    return (f'<div style="font-size:10px;font-weight:700;letter-spacing:.4px;'
            f'text-transform:uppercase;color:#94a3b8;margin:0 0 4px">{txt}</div>')


# ── Layout A: banner de validez final + resumen comparativo (todo HTML, sin widgets) ──

def banner_final(
    estado,
    subtitulo: str = "Definida por la evaluación Conprospección y la respuesta del cliente",
) -> str:
    """Banner grande de validez final: lo primero y más importante de la tarjeta."""
    e = estado or "pendiente"
    bg, tx = _COL_FINAL.get(e, ("#f1f5f9", "#475569"))
    return (
        f'<div style="background:{bg};border-left:5px solid {tx};border-radius:10px;'
        f'padding:12px 18px;margin:0 0 12px">'
        f'<div style="font-size:10px;font-weight:800;letter-spacing:.6px;'
        f'text-transform:uppercase;color:{tx};opacity:.7">Validez final</div>'
        f'<div style="font-size:22px;font-weight:800;color:{tx};line-height:1.15">'
        f'{LABEL_FINAL.get(e, "Pendiente")}</div>'
        f'<div style="font-size:11px;color:{tx};opacity:.7;margin-top:1px">{subtitulo}</div>'
        f'</div>')


def _comentario_inline(comentario) -> str:
    if not (comentario and str(comentario).strip()):
        return ""
    safe = str(comentario).strip().replace("<", "&lt;").replace(">", "&gt;")
    return (f'<span style="font-size:12px;color:#94a3b8;font-style:italic;'
            f'flex:1;min-width:160px">— {safe}</span>')


def fila_resumen(titulo: str, color: str, validez, bant, comentario=None,
                 *, primera: bool = False) -> str:
    """Una fila del resumen comparativo (read-only): quién · validez · BANT · comentario."""
    borde = "" if primera else "border-top:1px solid #eef2f7;"
    return (
        f'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;'
        f'padding:10px 14px;{borde}">'
        f'<span style="width:170px;min-width:170px;font-size:11px;font-weight:800;'
        f'letter-spacing:.3px;text-transform:uppercase;color:{color}">{titulo}</span>'
        f'{chip_validez(validez)}'
        f'<span style="font-size:10px;color:#cbd5e1;font-weight:700">BANT</span>'
        f'{bant_chips(bant)}'
        f'{_comentario_inline(comentario)}'
        f'</div>')


def bloque_resumen(*filas: str) -> str:
    """Contenedor del resumen comparativo de capas."""
    return (f'<div style="border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;'
            f'background:#fff;margin-bottom:14px">{"".join(f for f in filas if f)}</div>')


def encabezado_seccion(titulo: str, color: str = "#0e7490") -> str:
    """Encabezado de la zona de edición (p. ej. 'Tu validación')."""
    return (f'<div style="font-size:11px;font-weight:800;letter-spacing:.4px;'
            f'text-transform:uppercase;color:{color};margin:2px 0 8px;'
            f'padding-bottom:5px;border-bottom:2px solid {color}22">{titulo}</div>')


def barra_avance(validas: int, meta: int, *, sufijo: str = "", color: str = "#7c3aed") -> str:
    """Barra de avance de meta en HTML/CSS puro. Números tabulares para estabilidad."""
    pct = round(validas / meta * 100) if meta else 0
    pct_barra = min(pct, 100)
    meta_txt = f"{validas}/{meta}{sufijo}" if meta else "—"
    return (
        f'<div style="background:#fff;border:1px solid #e9d5ff;border-radius:12px;'
        f'padding:14px 18px;margin:6px 0 14px">'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px">'
        f'<span style="font-size:13px;font-weight:700;color:#1e293b">Avance de meta</span>'
        f'<span style="font-size:13px;font-weight:800;color:{color};'
        f'font-variant-numeric:tabular-nums">{meta_txt} · {pct}%</span></div>'
        f'<div style="background:#f1f5f9;border-radius:6px;height:10px;overflow:hidden">'
        f'<div style="width:{pct_barra}%;background:{color};height:10px;border-radius:6px"></div></div>'
        f'<div style="font-size:11px;color:#64748b;margin-top:6px">'
        f'Reuniones válidas (validación final) sobre la meta del contrato.</div>'
        f'</div>')
