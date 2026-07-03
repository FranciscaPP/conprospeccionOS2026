from pathlib import Path
import shutil
import sys
import os

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    EXTENSIONES_DOCUMENTOS,
    EXTENSIONES_IMAGENES,
    EXTENSIONES_BASES,
    EXTENSIONES_HTML,
    EXTENSIONES_LOGOS,
)

PALABRAS_LOGO = {"logo", "brand", "marca", "logotipo", "isotipo", "isologo"}


def clasificar_archivo(filename: str) -> tuple[str, str]:
    """Returns (subcarpeta_destino, categoria)"""
    name = filename.lower()
    ext = Path(filename).suffix.lower()

    es_posible_logo = any(palabra in name for palabra in PALABRAS_LOGO)

    if ext in EXTENSIONES_LOGOS and es_posible_logo:
        return "00_INPUT_CLIENTE/logos", "logo"
    elif ext in EXTENSIONES_DOCUMENTOS:
        if "minuta" in name or "reunion" in name or "meeting" in name:
            return "00_INPUT_CLIENTE/minutas", "minuta"
        return "00_INPUT_CLIENTE/documentos", "documento"
    elif ext in EXTENSIONES_IMAGENES:
        return "00_INPUT_CLIENTE/imagenes", "imagen"
    elif ext in EXTENSIONES_BASES:
        return "00_INPUT_CLIENTE/bases", "base"
    elif ext in EXTENSIONES_HTML:
        return "00_INPUT_CLIENTE/documentos", "html"
    else:
        return "00_INPUT_CLIENTE/otros", "otro"


def guardar_archivo(cliente_dir: Path, filename: str, contenido: bytes) -> dict:
    subcarpeta, categoria = clasificar_archivo(filename)
    destino_dir = cliente_dir / subcarpeta
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino_path = destino_dir / filename

    # No sobrescribir, agregar sufijo si existe
    if destino_path.exists():
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        i = 1
        while destino_path.exists():
            destino_path = destino_dir / f"{stem}_{i}{suffix}"
            i += 1

    destino_path.write_bytes(contenido)

    # Si es imagen/logo, copiar también a logos_cliente
    if categoria in ("logo", "imagen") and Path(filename).suffix.lower() in EXTENSIONES_LOGOS:
        logos_dir = cliente_dir / "02_BRANDING_Y_ACTIVOS/logos_cliente"
        logos_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(destino_path, logos_dir / destino_path.name)

    return {
        "archivo": filename,
        "destino": str(destino_path.relative_to(cliente_dir)),
        "categoria": categoria,
        "subcarpeta": subcarpeta,
        "guardado_en": str(destino_path),
    }


def listar_logos(cliente_dir: Path) -> list:
    logos = []
    for carpeta in ["00_INPUT_CLIENTE/logos", "02_BRANDING_Y_ACTIVOS/logos_cliente"]:
        path = cliente_dir / carpeta
        if path.exists():
            for f in path.iterdir():
                if f.suffix.lower() in EXTENSIONES_LOGOS and f.is_file():
                    if str(f) not in [l["path"] for l in logos]:
                        logos.append({"nombre": f.name, "path": str(f), "carpeta": carpeta})
    return logos


def listar_archivos_por_carpeta(cliente_dir: Path) -> dict:
    resultado = {}
    if not cliente_dir.exists():
        return resultado
    for item in sorted(cliente_dir.rglob("*")):
        if item.is_file():
            carpeta_rel = str(item.parent.relative_to(cliente_dir))
            if carpeta_rel not in resultado:
                resultado[carpeta_rel] = []
            resultado[carpeta_rel].append({
                "nombre": item.name,
                "path": str(item),
                "tamaño": item.stat().st_size,
                "extension": item.suffix.lower(),
            })
    return resultado
