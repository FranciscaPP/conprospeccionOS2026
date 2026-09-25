from __future__ import annotations

import html
from datetime import date, datetime, time, timedelta
from pathlib import Path

from report_calls_live import GHLClient, LOCATION, token_for, to_chile

from .config import BACKGROUND_COLOR, CHILE, CLIENTS, TEXT_COLOR, TOTAL_COLOR

ORDER = ("bambutech", "gbs", "balia")
SUM_KEYS = ("tasks_done", "tasks_total", "overdue_pending", "calls", "contacts",
            "answered", "unanswered", "conversation_seconds", "phone_seconds", "meetings")


def _totals(report: dict) -> dict:
    return {key: sum(int(report["clients"][slug].get(key) or 0) for slug in ORDER) for key in SUM_KEYS}


def render_daily_close(report: dict) -> str:
    total = _totals(report)
    pending = max(0, total["tasks_total"] - total["tasks_done"])
    lines = [
        f"🏁 <b>CIERRE OPERATIVO · {report['day'].strftime('%d/%m/%Y')}</b>",
        "👤 Nora", "",
        f"<b>Tareas GHL:</b> {total['tasks_done']}/{total['tasks_total']}",
        f"<b>Llamadas:</b> {total['calls']} a {total['contacts']} contactos",
        f"<b>Reuniones agendadas:</b> {total['meetings']}", "",
    ]
    for slug in ORDER:
        cfg, data = CLIENTS[slug], report["clients"][slug]
        email = data.get("email") or {}
        lines.append(
            f"{cfg.emoji} <b>{cfg.name}</b> · tareas {data.get('tasks_done', 0)}/{data.get('tasks_total', 0)}"
            f" · llamadas {data.get('calls', 0)} · correos manuales {email.get('new_manual', 0)}"
        )
    lines.extend([
        "", "⚠️ <b>BRECHA DEL DÍA</b>",
        f"Pendientes de la meta GHL: {pending}",
        f"Arrastre vencido pendiente: {total['overdue_pending']}",
        "La brecha telefónica se informa por actividad observada; no se inventa una meta de llamadas.",
    ])
    return "\n".join(lines)


def aggregate_week(reports: list[dict]) -> dict:
    result = {"days": len(reports), "clients": {slug: {key: 0 for key in SUM_KEYS} for slug in ORDER},
              "industries": {}, "roles": {}, "negative_states": {}}
    for report in reports:
        for slug in ORDER:
            for key in SUM_KEYS:
                result["clients"][slug][key] += int(report.get("clients", {}).get(slug, {}).get(key) or 0)
        for dimension in ("industries", "roles", "negative_states"):
            for label, count in (report.get("weekly_dimensions", {}).get(dimension, {}) or {}).items():
                result[dimension][label] = result[dimension].get(label, 0) + int(count or 0)
    return result


def render_weekly(summary: dict, start: date, end: date) -> str:
    lines = [f"📊 <b>RESUMEN SEMANAL · {start.strftime('%d/%m')}–{end.strftime('%d/%m')}</b>",
             f"👤 Nora · {summary['days']} cierres disponibles", ""]
    for slug in ORDER:
        cfg, data = CLIENTS[slug], summary["clients"][slug]
        lines.append(f"{cfg.emoji} <b>{cfg.name}</b> · tareas {data['tasks_done']}/{data['tasks_total']} · llamadas {data['calls']} · reuniones {data['meetings']}")
    if summary["days"] < 5:
        lines.extend(["", "ℹ️ Semana parcial: el análisis completo se consolida cuando existan los 5 cierres diarios."])
    labels = (("Industrias", "industries"), ("Cargos", "roles"), ("Estados negativos", "negative_states"))
    for title, key in labels:
        values = sorted(summary.get(key, {}).items(), key=lambda item: item[1], reverse=True)[:5]
        detail = ", ".join(f"{name} ({count})" for name, count in values) if values else "sin dato estructurado confiable"
        lines.append(f"<b>{title}:</b> {html.escape(detail)}")
    return "\n".join(lines)


def new_meeting_alert(slug: str, event: dict) -> str:
    cfg = CLIENTS[slug]
    raw_start = event.get("startTime") or event.get("start") or event.get("startAt")
    start = to_chile(raw_start)
    name = event.get("contactName") or event.get("name") or event.get("title") or "Contacto sin nombre"
    fields = [f"🚀 <b>NUEVA REUNIÓN · {cfg.name}</b>", f"👤 {html.escape(str(name))}"]
    if start:
        fields.append(f"📅 {start.strftime('%d/%m/%Y %H:%M')} Chile")
    optional = (("Cargo", "jobTitle"), ("Industria", "industry"), ("Teléfono", "phone"),
                ("Email", "email"), ("Origen", "source"), ("Estado anterior", "previousStage"))
    for label, key in optional:
        if event.get(key):
            fields.append(f"<b>{label}:</b> {html.escape(str(event[key]))}")
    fields.append("<b>SDR:</b> Nora")
    return "\n".join(fields)


def fetch_calendar_meetings(now: datetime | None = None) -> list[dict]:
    now = (now or datetime.now(CHILE)).astimezone(CHILE)
    start = datetime.combine(now.date() - timedelta(days=1), time.min, tzinfo=CHILE)
    end = start + timedelta(days=181)
    output, seen = [], set()
    for slug in ORDER:
        ghl, location_id = GHLClient(token_for(slug)), LOCATION[slug]
        for calendar in ghl.list_calendars(location_id).get("calendars") or []:
            payload = ghl.list_calendar_events(location_id, str(int(start.timestamp()*1000)),
                                                str(int(end.timestamp()*1000)), calendar_id=calendar.get("id"))
            for event in payload.get("events") or payload.get("appointments") or []:
                event_id = str(event.get("id") or event.get("appointmentId") or "")
                status = str(event.get("appointmentStatus") or event.get("status") or "").lower()
                if not event_id or (slug, event_id) in seen or status in {"cancelled", "canceled", "noshow"}:
                    continue
                seen.add((slug, event_id))
                contact_id = event.get("contactId")
                if contact_id:
                    try:
                        contact = (ghl.get_contact(contact_id) or {}).get("contact") or {}
                        event = dict(event)
                        event.setdefault("contactName", " ".join(
                            str(contact.get(key) or "").strip() for key in ("firstName", "lastName")
                        ).strip())
                        for target, source in (("email", "email"), ("phone", "phone"),
                                               ("jobTitle", "jobTitle"), ("source", "source")):
                            if contact.get(source):
                                event.setdefault(target, contact[source])
                    except Exception:
                        pass
                output.append({"slug": slug, "id": event_id, "event": event})
    return output


def render_chart(report: dict, destination: Path, title: str = "Cierre operativo") -> Path:
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new("RGB", (1200, 700), BACKGROUND_COLOR)
    draw, font = ImageDraw.Draw(image), ImageFont.load_default(size=30)
    draw.text((60, 45), title, fill=TEXT_COLOR, font=font)
    for col, slug in enumerate(ORDER):
        draw.text((300 + col * 285, 105), CLIENTS[slug].short, fill=CLIENTS[slug].color, font=font)
    metrics = (("Tareas", "tasks_done"), ("Llamadas", "calls"), ("Reuniones", "meetings"))
    max_value = max(1, *(int(report["clients"][s].get(k) or 0) for s in ORDER for _, k in metrics))
    for row, (label, key) in enumerate(metrics):
        y = 160 + row * 160
        draw.text((60, y), label, fill=TOTAL_COLOR, font=font)
        for col, slug in enumerate(ORDER):
            value = int(report["clients"][slug].get(key) or 0)
            x = 300 + col * 285
            height = max(3, int(105 * value / max_value))
            draw.rectangle((x, y + 115 - height, x + 120, y + 115), fill=CLIENTS[slug].color)
            draw.text((x + 130, y + 75), str(value), fill=TEXT_COLOR, font=font)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)
    return destination


def render_weekly_charts(summary: dict, directory: Path) -> list[Path]:
    from PIL import Image, ImageDraw, ImageFont
    directory.mkdir(parents=True, exist_ok=True)
    output = []
    for label, key in (("Tareas completadas", "tasks_done"), ("Llamadas", "calls"), ("Reuniones", "meetings")):
        values = [summary["clients"][slug][key] for slug in ORDER]
        image = Image.new("RGB", (1000, 600), BACKGROUND_COLOR)
        draw, font = ImageDraw.Draw(image), ImageFont.load_default(size=30)
        draw.text((50, 35), f"Semana · {label}", fill=TEXT_COLOR, font=font)
        maximum = max(1, *values)
        for index, slug in enumerate(ORDER):
            value, x = values[index], 120 + index * 290
            height = max(3, int(350 * value / maximum))
            draw.rectangle((x, 470-height, x+150, 470), fill=CLIENTS[slug].color)
            draw.text((x, 490), f"{CLIENTS[slug].short} {value}", fill=TEXT_COLOR, font=font)
        path = directory / f"semanal_{key}.png"
        image.save(path)
        output.append(path)
    return output
