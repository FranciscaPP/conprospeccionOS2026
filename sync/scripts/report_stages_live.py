from __future__ import annotations

"""Reporte EN VIVO de oportunidades en etapas de trabajo activo (GHL).

Cuenta contactos/oportunidades ABIERTAS en:
  - INFORMACION ADICIONAL
  - COORDINANDO REUNION
y hace cuanto tiempo llevan ahi (lastStageChangeAt -> hoy).

Uso: python report_stages_live.py [--clients bambutech,gbs]
"""

import argparse
import sys
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from config import get_optional_env
from ghl_client import GHLClient

CHILE = ZoneInfo("America/Santiago")
UTC = ZoneInfo("UTC")

TOKEN_ENV = {"gbs": "GHL_TOKEN_GBS_LOGISTICS", "bambutech": "GHL_TOKEN_BAMBUTECH"}
LOCATION = {"bambutech": "FJ1YCwi4UVvwcBb8qlOb", "gbs": "u9b8KkJXhM8lqJfzxa7G"}
NOMBRE = {"bambutech": "BAMBUTECH", "gbs": "GBS LOGISTICS"}

# Etapas objetivo (por nombre, normalizado sin tildes/mayus)
TARGET = {"informacion adicional", "coordinando reunion"}


def norm(s: str) -> str:
    return (s or "").lower().translate(str.maketrans("áéíóúñ", "aeioun")).strip()


def parse_dt(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


def stage_names(ghl: GHLClient, location_id: str) -> dict[str, str]:
    out: dict[str, str] = {}
    data = ghl.list_pipelines(location_id)
    for p in data.get("pipelines", []):
        for s in p.get("stages", []):
            out[s.get("id")] = s.get("name")
    return out


def all_open_opps(ghl: GHLClient, location_id: str) -> list[dict]:
    opps: list[dict] = []
    start_after = None
    start_after_id = None
    for _ in range(200):
        payload = ghl.list_opportunities_page(
            location_id, limit=100, start_after=start_after, start_after_id=start_after_id
        )
        page = payload.get("opportunities") or []
        opps.extend(page)
        meta = payload.get("meta") or {}
        start_after = meta.get("startAfter")
        start_after_id = meta.get("startAfterId")
        if len(page) < 100 or not start_after_id:
            break
    return opps


def report_client(slug: str) -> dict:
    ghl = GHLClient(get_optional_env(TOKEN_ENV[slug]))
    names = stage_names(ghl, LOCATION[slug])
    opps = all_open_opps(ghl, LOCATION[slug])
    now = datetime.now(UTC)

    # etapa_norm -> lista de (nombre_contacto, dias_en_etapa)
    by_stage: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for o in opps:
        if o.get("status") != "open":
            continue
        stage_name = names.get(o.get("pipelineStageId"), "")
        n = norm(stage_name)
        if n not in TARGET:
            continue
        changed = parse_dt(o.get("lastStageChangeAt")) or parse_dt(o.get("updatedAt"))
        dias = (now - changed).days if changed else -1
        cname = o.get("name") or (o.get("contact") or {}).get("name") or "(sin nombre)"
        by_stage[n].append((cname, dias))
    return {"slug": slug, "nombre": NOMBRE[slug], "by_stage": by_stage}


def bucket(dias_list: list[int]) -> dict[str, int]:
    b = {"hoy (0d)": 0, "1-3d": 0, "4-7d": 0, "8-14d": 0, "15-30d": 0, "+30d": 0}
    for d in dias_list:
        if d <= 0: b["hoy (0d)"] += 1
        elif d <= 3: b["1-3d"] += 1
        elif d <= 7: b["4-7d"] += 1
        elif d <= 14: b["8-14d"] += 1
        elif d <= 30: b["15-30d"] += 1
        else: b["+30d"] += 1
    return b


def build(rows: list[dict]) -> str:
    L: list[str] = []
    L.append("=" * 64)
    L.append(f" ETAPAS DE TRABAJO ACTIVO - {datetime.now(CHILE).strftime('%Y-%m-%d %H:%M')} (Chile)")
    L.append(" EN VIVO desde GHL - oportunidades ABIERTAS")
    L.append("=" * 64)
    labels = {"informacion adicional": "INFORMACION ADICIONAL", "coordinando reunion": "COORDINANDO REUNION"}
    for r in rows:
        L.append(f"\n# {r['nombre']}")
        for key, title in labels.items():
            items = sorted(r["by_stage"].get(key, []), key=lambda t: -t[1])
            L.append(f"\n  {title}: {len(items)} contactos")
            if not items:
                continue
            b = bucket([d for _, d in items])
            L.append("   Antiguedad en etapa: " + " | ".join(f"{k}:{v}" for k, v in b.items() if v))
            for cname, dias in items:
                d_txt = f"{dias}d" if dias >= 0 else "s/f"
                L.append(f"     - {cname[:42]:<42} {d_txt:>5} en etapa")
    L.append("\nNota: antiguedad = dias desde el ultimo cambio de etapa (lastStageChangeAt).")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clients", default="bambutech,gbs")
    args = ap.parse_args()
    slugs = [s.strip() for s in args.clients.split(",") if s.strip()]
    rows = [report_client(s) for s in slugs]
    text = build(rows)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(text)
    out = f"reporte_etapas_{datetime.now(CHILE).date().isoformat()}.txt"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(f"\n[archivo guardado: {out}]")


if __name__ == "__main__":
    main()
