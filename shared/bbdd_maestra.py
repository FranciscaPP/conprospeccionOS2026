"""BBDD Maestra — lógica pura del pool único de prospectos.

Fuente única de la lógica de:
- normalización/limpieza (industria, país, texto) para que todo quede uniforme;
- deduplicación por correo que **alerta, no borra** (marca duplicados, conserva filas);
- ICP por cliente y scoring de fit;
- selección de candidatos reutilizables con routing Snov (correo verificado) /
  GHL (con teléfono).

No depende de Streamlit ni de la red: recibe listas de dicts (filas de
`vw_prospectos_maestros`) y devuelve estructuras Python. Así es testeable con pytest.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Iterable

# Estados de correo que Snov considera entregable/verificado.
VERIFIED_EMAIL_STATUSES = {"current", "valid", "verified", "ok", "deliverable"}


# ── Normalización de texto ────────────────────────────────────────────────────
def strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )


def norm_key(value: Any) -> str:
    """Clave canónica para comparar: minúsculas, sin acentos, sin puntuación."""
    text = strip_accents(str(value or "")).lower().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def email_norm(value: Any) -> str:
    return str(value or "").strip().lower()


# ── Diccionarios canónicos (limpieza uniforme) ────────────────────────────────
# Cada entrada: etiqueta canónica -> lista de fragmentos (norm_key) que la delatan.
# El match es por "contiene", así "mineria del cobre", "mineria", "mining" caen en
# Minería. Editable a mano a medida que aparezcan variantes nuevas.
INDUSTRIA_SINONIMOS: dict[str, list[str]] = {
    "Minería": ["mineria", "minera", "mining", "mineral", "mini "],
    "Logística y transporte": ["logistica", "transporte", "freight", "shipping", "carga", "naviera", "aduana"],
    "Tecnología / Software": ["tecnologia", "software", "saas", "it ", "informatica", "technology", "tech"],
    "Construcción": ["construccion", "constructora", "obras", "building", "inmobiliaria"],
    "Agricultura / Agroindustria": ["agricola", "agro", "agroindustria", "farming", "agricultura"],
    "Manufactura / Industrial": ["manufactura", "industrial", "fabrica", "manufacturing", "planta"],
    "Retail / Comercio": ["retail", "comercio", "tienda", "ecommerce", "e commerce", "consumo"],
    "Salud": ["salud", "clinica", "hospital", "health", "medic", "farmac"],
    "Energía": ["energia", "energy", "electrica", "solar", "renovable", "utilities"],
    "Educación": ["educacion", "education", "universidad", "colegio", "school"],
    "Servicios financieros": ["banca", "banco", "financ", "fintech", "seguros", "insurance"],
    "Alimentos y bebidas": ["alimentos", "bebidas", "food", "beverage", "pesca", "acuicultura", "salmon"],
}

PAIS_SINONIMOS: dict[str, list[str]] = {
    "Chile": ["chile", "cl", "chilena", "santiago"],
    "Perú": ["peru", "pe", "peruana", "lima"],
    "Colombia": ["colombia", "co", "bogota"],
    "México": ["mexico", "mx", "cdmx"],
    "Argentina": ["argentina", "ar", "buenos aires"],
    "Brasil": ["brasil", "brazil", "br", "sao paulo"],
    "Estados Unidos": ["estados unidos", "usa", "us", "united states", "eeuu"],
    "España": ["espana", "spain", "es", "madrid"],
    "Ecuador": ["ecuador", "ec", "quito"],
}


def _match_sinonimo(raw: Any, tabla: dict[str, list[str]]) -> str | None:
    key = norm_key(raw)
    if not key:
        return None
    for canonico, fragmentos in tabla.items():
        for frag in fragmentos:
            if frag.strip() in key:
                return canonico
    return None


def normalizar_industria(raw: Any) -> str:
    """Devuelve la industria canónica; si no reconoce, devuelve el texto original limpio."""
    canonico = _match_sinonimo(raw, INDUSTRIA_SINONIMOS)
    if canonico:
        return canonico
    text = str(raw or "").strip()
    return text[:1].upper() + text[1:] if text else ""


def normalizar_pais(raw: Any) -> str:
    canonico = _match_sinonimo(raw, PAIS_SINONIMOS)
    if canonico:
        return canonico
    text = str(raw or "").strip()
    return text[:1].upper() + text[1:] if text else ""


# ── Consolidación del pool (dedup = alerta, no borra) ─────────────────────────
def _completitud(row: dict[str, Any]) -> int:
    """Cuenta campos útiles presentes — para elegir el registro 'canónico' del grupo."""
    campos = ("nombre", "empresa", "cargo", "industria", "pais", "telefono", "linkedin_url")
    return sum(1 for c in campos if str(row.get(c) or "").strip())


def consolidar(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Enriquyece cada fila SIN borrar ninguna.

    Agrega por fila: email_norm, industria_norm, pais_norm, correo_verificado,
    tiene_telefono, y datos del grupo del mismo correo: veces, es_duplicado,
    fuentes, clientes_origen, es_canonico (el registro más completo del grupo).
    """
    filas = [dict(r) for r in rows]
    grupos: dict[str, list[dict[str, Any]]] = {}
    for r in filas:
        r["email_norm"] = email_norm(r.get("email_norm") or r.get("email"))
        r["industria_norm"] = normalizar_industria(r.get("industria"))
        r["pais_norm"] = normalizar_pais(r.get("pais"))
        r["correo_verificado"] = str(r.get("email_status") or "").strip().lower() in VERIFIED_EMAIL_STATUSES
        r["tiene_telefono"] = bool(str(r.get("telefono") or "").strip())
        grupos.setdefault(r["email_norm"], []).append(r)

    for email, grupo in grupos.items():
        veces = len(grupo)
        fuentes = sorted({str(g.get("fuente") or "") for g in grupo if g.get("fuente")})
        clientes = sorted({str(g.get("cliente_slug_origen") or "") for g in grupo if g.get("cliente_slug_origen")})
        canonico = max(grupo, key=_completitud)
        for g in grupo:
            g["veces"] = veces
            g["es_duplicado"] = veces > 1
            g["fuentes"] = fuentes
            g["clientes_origen"] = clientes
            g["es_canonico"] = g is canonico
    return filas


def resumen_pool(filas: list[dict[str, Any]]) -> dict[str, Any]:
    """Métricas del pool ya consolidado."""
    unicos = {f["email_norm"] for f in filas if f.get("email_norm")}
    duplicados = {f["email_norm"] for f in filas if f.get("es_duplicado")}
    verificados = {f["email_norm"] for f in filas if f.get("correo_verificado")}
    con_tel = {f["email_norm"] for f in filas if f.get("tiene_telefono")}
    por_industria: dict[str, int] = {}
    por_pais: dict[str, int] = {}
    for email in unicos:
        fila = next(f for f in filas if f["email_norm"] == email and f.get("es_canonico"))
        por_industria[fila.get("industria_norm") or "(sin dato)"] = por_industria.get(fila.get("industria_norm") or "(sin dato)", 0) + 1
        por_pais[fila.get("pais_norm") or "(sin dato)"] = por_pais.get(fila.get("pais_norm") or "(sin dato)", 0) + 1
    return {
        "total_filas": len(filas),
        "prospectos_unicos": len(unicos),
        "duplicados": len(duplicados),
        "correos_verificados": len(verificados),
        "con_telefono": len(con_tel),
        "por_industria": dict(sorted(por_industria.items(), key=lambda x: -x[1])),
        "por_pais": dict(sorted(por_pais.items(), key=lambda x: -x[1])),
    }


# ── ICP y scoring ─────────────────────────────────────────────────────────────
@dataclass
class ICP:
    cliente_slug: str = ""
    paises: list[str] = field(default_factory=list)
    industrias: list[str] = field(default_factory=list)
    cargos: list[str] = field(default_factory=list)
    tamanos: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    exclusiones: list[str] = field(default_factory=list)
    umbral_score: float = 2

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "ICP":
        def _list(v: Any) -> list[str]:
            if isinstance(v, list):
                return [str(x).strip() for x in v if str(x).strip()]
            return _split_list(v)
        return cls(
            cliente_slug=str(row.get("cliente_slug") or ""),
            paises=_list(row.get("paises")),
            industrias=_list(row.get("industrias")),
            cargos=_list(row.get("cargos")),
            tamanos=_list(row.get("tamanos")),
            keywords=_list(row.get("keywords")),
            exclusiones=_list(row.get("exclusiones")),
            umbral_score=float(row.get("umbral_score") or 2),
        )


def _split_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    text = str(value or "")
    parts = re.split(r"[\n,;|]+", text)
    return [p.strip(" -\t") for p in parts if p.strip(" -\t")]


def _any_match(valor: Any, criterios: list[str]) -> bool:
    """True si el valor contiene (o está contenido en) alguno de los criterios."""
    v = norm_key(valor)
    if not v:
        return False
    for c in criterios:
        ck = norm_key(c)
        if ck and (ck in v or v in ck):
            return True
    return False


def score_icp(prospecto: dict[str, Any], icp: ICP) -> tuple[float, dict[str, bool]]:
    """Puntúa el fit del prospecto contra el ICP.

    Cada dimensión con criterios suma 1 si matchea. Si matchea una exclusión,
    el prospecto se descalifica (score = -1). Devuelve (score, detalle).
    """
    campos_texto = " ".join(
        str(prospecto.get(k) or "") for k in ("empresa", "cargo", "industria", "pais", "nombre")
    )
    if icp.exclusiones and _any_match(campos_texto, icp.exclusiones):
        return -1.0, {"excluido": True}

    detalle = {
        "pais": bool(icp.paises) and _any_match(prospecto.get("pais_norm") or prospecto.get("pais"), icp.paises),
        "industria": bool(icp.industrias) and _any_match(prospecto.get("industria_norm") or prospecto.get("industria"), icp.industrias),
        "cargo": bool(icp.cargos) and _any_match(prospecto.get("cargo"), icp.cargos),
        "keyword": bool(icp.keywords) and _any_match(campos_texto, icp.keywords),
    }
    return float(sum(1 for v in detalle.values() if v)), detalle


def ruta_destino(prospecto: dict[str, Any]) -> list[str]:
    """A qué plataforma puede ir: Snov si correo verificado, GHL si tiene teléfono."""
    rutas = []
    if prospecto.get("correo_verificado"):
        rutas.append("snov")
    if prospecto.get("tiene_telefono"):
        rutas.append("ghl")
    return rutas


def candidatos(
    filas: list[dict[str, Any]],
    icp: ICP,
    ya_asignados: set[str] | None = None,
    incluir_sin_verificar: bool = False,
) -> list[dict[str, Any]]:
    """Candidatos reutilizables para un cliente según su ICP.

    - un registro por prospecto único (el canónico del grupo);
    - excluye los ya asignados a ese cliente (`ya_asignados` = set de email_norm);
    - score >= umbral y no excluido;
    - por defecto exige correo verificado O teléfono (algo accionable);
    - ordenado por score desc.
    """
    ya = ya_asignados or set()
    out = []
    for f in filas:
        if not f.get("es_canonico"):
            continue
        if f["email_norm"] in ya:
            continue
        score, detalle = score_icp(f, icp)
        if score < icp.umbral_score:
            continue
        rutas = ruta_destino(f)
        if not rutas and not incluir_sin_verificar:
            continue
        out.append({**f, "score_icp": score, "match": detalle, "rutas": rutas})
    out.sort(key=lambda x: x["score_icp"], reverse=True)
    return out
