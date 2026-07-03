import json
from pathlib import Path
from datetime import datetime


def _hoy() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def cargar_estado(cliente_dir: Path) -> dict:
    ruta = cliente_dir / "estado_cliente.json"
    if ruta.exists():
        try:
            return json.loads(ruta.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def guardar_estado(cliente_dir: Path, estado: dict) -> None:
    estado["fecha_actualizacion"] = _hoy()
    ruta = cliente_dir / "estado_cliente.json"
    ruta.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")


def actualizar_campo(cliente_dir: Path, campo: str, valor) -> dict:
    estado = cargar_estado(cliente_dir)
    estado[campo] = valor
    guardar_estado(cliente_dir, estado)
    return estado


def calcular_progreso(estado: dict) -> dict:
    campos_estado = [
        "estado_estructura",
        "estado_archivos",
        "estado_branding",
        "estado_firma",
        "estado_analisis",
        "estado_icp",
        "estado_playbook",
        "estado_apollo",
        "estado_mensajeria",
    ]
    completados = sum(
        1 for c in campos_estado
        if estado.get(c) not in ("pendiente", "", None)
    )
    total = len(campos_estado)
    return {
        "completados": completados,
        "total": total,
        "porcentaje": int((completados / total) * 100) if total > 0 else 0,
    }


COLORES_ESTADO = {
    "pendiente": "#f59e0b",
    "en_proceso": "#3b82f6",
    "generado": "#8b5cf6",
    "lista": "#10b981",
    "aprobado": "#10b981",
    "listo": "#10b981",
    "creado": "#6b7280",
}


def color_estado(valor: str) -> str:
    if not valor:
        return COLORES_ESTADO["pendiente"]
    for key, color in COLORES_ESTADO.items():
        if key in valor.lower():
            return color
    return "#6b7280"


def emoji_estado(valor: str) -> str:
    if not valor or valor == "pendiente":
        return "⏳"
    if valor in ("lista", "aprobado", "listo", "generado"):
        return "✅"
    if valor == "en_proceso":
        return "🔄"
    if valor == "creado":
        return "🆕"
    return "📌"
