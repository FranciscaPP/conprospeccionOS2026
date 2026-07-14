"""Respaldo de reuniones desde el calendario publico de Google (feed iCal .ics).

Sirve como SEGUNDA FUENTE cuando GoHighLevel (GHL) esta caido o intermitente:
lee el .ics publico de cada cliente y agrega a `reuniones` las citas que aun
no existan en la base.

Clave anti-duplicados: los eventos de Google Calendar creados por GHL llevan en
su DESCRIPTION el `event_id` de GHL, que es EXACTAMENTE el `ghl_appointment_id`
que guarda el sync normal. Por eso se importa con ese mismo id y **se fusiona**
con lo de GHL en vez de duplicar. Ademas solo se INSERTAN las citas que faltan
(no se pisan filas ya sincronizadas por GHL, que son mas ricas).

Un calendario en modo "Solo libre/ocupado" (Busy) no expone detalles ni
event_id: esos eventos se ignoran (no se pueden usar de respaldo).
"""
from __future__ import annotations

import argparse
import logging
import re
import urllib.request
from datetime import datetime, timezone

from config import get_settings
from supabase_rest import SupabaseRestClient


# Feeds iCal publicos por cliente (no son secretos). Se puede sobreescribir por
# variable de entorno ICAL_URL_<SLUG_EN_MAYUSCULAS>.
ICS_URLS = {
    "gbs": "https://calendar.google.com/calendar/ical/sam%40gbs-logistics.cl/public/basic.ics",
    "bambutech": "https://calendar.google.com/calendar/ical/michelle.hernandez%40bambutech-services.com/public/basic.ics",
    "clickie": "https://calendar.google.com/calendar/ical/francis%40clickie.tech/public/basic.ics",
}


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "conprospeccion-sync/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _unfold(raw: str) -> str:
    # RFC 5545: las lineas continuadas empiezan con espacio o tab.
    return re.sub(r"\n[ \t]", "", raw.replace("\r\n", "\n"))


def _field(ev: str, key: str) -> str:
    m = re.search(rf"^{key}[;:]([^\n]*)", ev, re.M)
    return (m.group(1) if m else "").strip()


def _parse_dt(value: str) -> datetime | None:
    """Parsea DTSTART. Soporta '...Z' (UTC) y 'YYYYMMDDThhmmss' (naive->UTC)."""
    value = value.strip()
    m = re.search(r"(\d{8}T\d{6})Z?", value)
    if not m:
        return None
    try:
        dt = datetime.strptime(m.group(1), "%Y%m%dT%H%M%S")
    except ValueError:
        return None
    return dt.replace(tzinfo=timezone.utc)


def _empresa_de(summary: str) -> str:
    # Formato habitual "EMPRESA - <Cliente>". Toma lo previo al ultimo " - ".
    s = summary.strip()
    if " - " in s:
        return s.rsplit(" - ", 1)[0].strip()
    return s


def parse_events(raw: str, cliente_slug: str) -> list[dict]:
    rows = []
    for ev in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", _unfold(raw), re.S):
        desc = _field(ev, "DESCRIPTION")
        m_id = re.search(r"event_id=([A-Za-z0-9]+)", desc)
        if not m_id:
            # Sin event_id (p.ej. calendario en modo "Busy"): no se puede
            # enlazar con GHL ni usar de respaldo confiable. Se ignora.
            continue
        dt = _parse_dt(_field(ev, "DTSTART"))
        if dt is None:
            continue
        summary = _field(ev, "SUMMARY")
        email = (re.search(r"Email:-\s*([^\s\\]+@[^\s\\]+)", desc) or [None, ""])[1]
        phone = (re.search(r"Phone:-\s*([^\n\\]+)", desc) or [None, ""])[1].strip()
        cal_id = (re.search(r"/widget/booking/([A-Za-z0-9]+)", desc) or [None, None])[1]
        rows.append(
            {
                "ghl_appointment_id": m_id.group(1),
                "cliente_slug": cliente_slug,
                "empresa": _empresa_de(summary) or None,
                "titulo": summary or None,
                "email": email or None,
                "telefono": phone or None,
                "appointment_at": dt.isoformat(),
                "starts_at": dt.isoformat(),
                "fecha_agendada": dt.date().isoformat(),
                "ghl_calendar_id": cal_id,
                "origen_reunion": "calendario_ical",
                "synced_at": iso_now(),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Respaldo de reuniones desde iCal publico de Google.")
    parser.add_argument("--client-slug", help="Solo un cliente.")
    parser.add_argument("--dry-run", action="store_true", help="No escribe en Supabase; solo reporta.")
    args = parser.parse_args()

    setup_logging()
    import os

    slugs = [args.client_slug] if args.client_slug else list(ICS_URLS)
    supabase = None
    if not args.dry_run:
        settings = get_settings()
        supabase = SupabaseRestClient(settings.supabase_url, settings.supabase_secret_key)

    total_nuevos = 0
    for slug in slugs:
        url = os.getenv(f"ICAL_URL_{slug.upper()}") or ICS_URLS.get(slug)
        if not url:
            logging.info("Sin URL iCal para %s, se omite.", slug)
            continue
        try:
            raw = _fetch(url)
        except Exception as exc:  # noqa: BLE001
            logging.warning("No se pudo leer el iCal de %s: %s", slug, exc)
            continue
        eventos = parse_events(raw, slug)
        logging.info("%s: %s eventos con event_id en el calendario.", slug, len(eventos))
        if args.dry_run:
            for r in eventos[:5]:
                logging.info("  %s | %s | %s", r["appointment_at"][:16], r["ghl_appointment_id"], r["empresa"])
            continue

        existentes = {
            r["ghl_appointment_id"]
            for r in supabase.select_all("reuniones", "ghl_appointment_id", cliente_slug=f"eq.{slug}")
            if r.get("ghl_appointment_id")
        }
        nuevos = [r for r in eventos if r["ghl_appointment_id"] not in existentes]
        if nuevos:
            for i in range(0, len(nuevos), 100):
                supabase.upsert("reuniones", nuevos[i : i + 100], "ghl_appointment_id")
        total_nuevos += len(nuevos)
        logging.info("%s: %s reuniones nuevas agregadas desde el calendario.", slug, len(nuevos))

    if not args.dry_run and supabase is not None:
        supabase.insert(
            "sync_runs",
            {
                "source": "ical",
                "entity": "reuniones",
                "status": "success",
                "stats": {"nuevas": total_nuevos},
                "errors": [],
            },
        )


if __name__ == "__main__":
    main()
