from __future__ import annotations

import html

from .config import CLIENTS


ORDER = ("bambutech", "gbs", "balia")
WEEKDAYS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")


def _minutes(seconds: int) -> str:
    return f"{round(max(0, int(seconds or 0)) / 60)} min"


def _percent(done: int, total: int) -> int:
    return round(100 * int(done or 0) / int(total or 0)) if total else 0


def _client_header(slug: str) -> str:
    cfg = CLIENTS[slug]
    return f"{cfg.emoji} <b>{cfg.name}</b>"


def _meeting_lines(slug: str, data: dict) -> list[str]:
    meetings = data.get("meetings") or []
    if isinstance(meetings, int):
        return [f"{_client_header(slug)} · {meetings} reunión(es)"]
    if not meetings:
        return [f"{_client_header(slug)} · Sin reuniones"]
    lines = [_client_header(slug)]
    for meeting in meetings:
        title = html.escape(str(meeting.get("title") or meeting.get("contact_name") or "Reunión"))
        chile = html.escape(str(meeting.get("chile") or "N/D"))
        peru = html.escape(str(meeting.get("peru") or "N/D"))
        lines.append(f"• {title} · Chile {chile} · Perú {peru}")
    return lines


def _task_card(slug: str, data: dict) -> str:
    done = int(data.get("tasks_done") or 0)
    total = int(data.get("tasks_total") or 0)
    pending = int(data.get("pending_today", max(0, total - done)) or 0)
    overdue = int(data.get("overdue_pending") or 0)
    last_hour = int(data.get("tasks_done_last_hour") or 0)
    return (
        f"{_client_header(slug)}\n"
        f"Hoy: {done}/{total} · {_percent(done, total)}% · +{last_hour} última hora\n"
        f"Pendientes de hoy: {pending}\n"
        f"Atrasadas de ayer: {overdue}\n"
        f"Total pendiente: {pending + overdue}"
    )


def _email_line(data: dict) -> str:
    email = data.get("email")
    if email is None:
        return "Correo: N/D"
    return (
        f"Correos: {int(email.get('received') or 0)} recibidos · "
        f"{int(email.get('responded') or 0)} respondidos · "
        f"{int(email.get('pending') or 0)} pendientes"
    )


def _activity_card(slug: str, data: dict) -> str:
    work = data.get("work_time") or {}
    return (
        f"{_client_header(slug)}\n"
        f"Llamadas: {int(data.get('calls') or 0)} · Contactos: {int(data.get('contacts') or 0)}\n"
        f"Remarcaciones: {int(data.get('repeated_contacts') or 0)}\n"
        f"Contestadas (&gt;20 s): {int(data.get('answered') or 0)}\n"
        f"Sin contestar (≤20 s): {int(data.get('unanswered') or 0)}\n"
        f"Hablando: {_minutes(data.get('answered_seconds', data.get('conversation_seconds', 0)))}\n"
        f"Sin contestar/sonando: {_minutes(data.get('unanswered_phone_seconds', 0))}\n"
        f"Total teléfono: {_minutes(data.get('phone_seconds', 0))}\n"
        f"{_email_line(data)}\n"
        f"Trabajado: {_minutes(work.get('worked_seconds', 0))}\n"
        f"Sin trabajar: {_minutes(work.get('unregistered_seconds', 0))}"
    )


def _total_task_card(clients: dict) -> str:
    done = sum(int(clients[s].get("tasks_done") or 0) for s in ORDER)
    total = sum(int(clients[s].get("tasks_total") or 0) for s in ORDER)
    pending = sum(int(clients[s].get("pending_today", max(0, int(clients[s].get("tasks_total") or 0) - int(clients[s].get("tasks_done") or 0))) or 0) for s in ORDER)
    overdue = sum(int(clients[s].get("overdue_pending") or 0) for s in ORDER)
    last_hour = sum(int(clients[s].get("tasks_done_last_hour") or 0) for s in ORDER)
    return (
        f"⬛ <b>TOTAL</b>\nHoy: {done}/{total} · {_percent(done, total)}% · +{last_hour} última hora\n"
        f"Pendientes de hoy: {pending}\nAtrasadas de ayer: {overdue}\nTotal pendiente: {pending + overdue}"
    )


def _total_activity_card(report: dict) -> str:
    clients = report["clients"]
    calls = sum(int(clients[s].get("calls") or 0) for s in ORDER)
    contacts = sum(int(clients[s].get("contacts") or 0) for s in ORDER)
    retries = sum(int(clients[s].get("repeated_contacts") or 0) for s in ORDER)
    answered = sum(int(clients[s].get("answered") or 0) for s in ORDER)
    unanswered = sum(int(clients[s].get("unanswered") or 0) for s in ORDER)
    answered_seconds = sum(int(clients[s].get("answered_seconds", clients[s].get("conversation_seconds", 0)) or 0) for s in ORDER)
    unanswered_seconds = sum(int(clients[s].get("unanswered_phone_seconds") or 0) for s in ORDER)
    phone_seconds = sum(int(clients[s].get("phone_seconds") or 0) for s in ORDER)
    received = responded = pending = 0
    known = 0
    for slug in ORDER:
        email = clients[slug].get("email")
        if email is not None:
            known += 1
            received += int(email.get("received") or 0)
            responded += int(email.get("responded") or 0)
            pending += int(email.get("pending") or 0)
    email_line = (
        f"Correos verificados: {received} recibidos · {responded} respondidos · {pending} pendientes"
        if known else "Correo: N/D"
    )
    work = report.get("work_time") or {}
    return (
        f"⬛ <b>TOTAL</b>\n"
        f"Llamadas: {calls} · Contactos: {contacts}\nRemarcaciones: {retries}\n"
        f"Contestadas (&gt;20 s): {answered}\nSin contestar (≤20 s): {unanswered}\n"
        f"Hablando: {_minutes(answered_seconds)}\nSin contestar/sonando: {_minutes(unanswered_seconds)}\n"
        f"Total teléfono: {_minutes(phone_seconds)}\n{email_line}\n"
        f"<b>TOTAL TRABAJADO: {_minutes(work.get('worked_seconds', 0))}</b>\n"
        f"<b>SIN TRABAJAR: {_minutes(work.get('unregistered_seconds', 0))}</b>"
    )


def _adherence(report: dict) -> str:
    cards = []
    for block in report.get("block_adherence", []):
        cfg = CLIENTS[block["client"]]
        cards.append(
            f"{cfg.emoji} <b>{cfg.name}</b> · {block['start']}–{block['end']}\n"
            f"Cliente correcto: {int(block.get('correct_calls') or 0)} · "
            f"Otros clientes: {int(block.get('other_calls') or 0)}"
        )
    return "\n\n".join(cards) or "Todavía no termina ningún bloque laboral."


def render_hourly(report: dict) -> list[str]:
    clients = report["clients"]
    cut = report["cut"]
    header = (
        f"📊 <b>REPORTE OPERATIVO · {cut.strftime('%H:%M')}</b>\n"
        f"📅 {WEEKDAYS[cut.weekday()]} {cut.strftime('%d/%m')} · 👤 {html.escape(report.get('sdr', 'Nora'))}"
    )
    meetings = []
    for slug in ORDER:
        meetings.extend(_meeting_lines(slug, clients[slug]))
    meeting_total = sum(
        value if isinstance(value := clients[s].get("meetings"), int) else len(value or [])
        for s in ORDER
    )
    msg1 = (
        f"{header}\n\n📅 <b>01 · REUNIONES DE HOY</b>\n\n"
        + "\n".join(meetings)
        + f"\n⬛ <b>TOTAL · {meeting_total}</b>\n\n"
        + "✅ <b>02 · TAREAS</b>\n\n"
        + "\n\n".join([*(_task_card(s, clients[s]) for s in ORDER), _total_task_card(clients)])
    )
    msg2 = (
        "☎️ <b>03 · LLAMADAS, CORREOS Y TIEMPO</b>\n\n"
        + "\n\n".join([*(_activity_card(s, clients[s]) for s in ORDER), _total_activity_card(report)])
        + "\n\n<i>Trabajado = tiempo de teléfono + 5 min por cada correo recibido y respondido. "
          "Sin trabajar = tiempo laboral transcurrido − trabajado.</i>"
    )
    msg3 = "🕐 <b>04 · ADHERENCIA A BLOQUES</b>\n\n" + _adherence(report)
    return [msg1, msg2, msg3]


def render_query(report: dict, request) -> list[str]:
    """Renderiza solo las secciones pedidas, usando el mismo documento del reporte."""
    if "summary" in request.intents:
        return render_hourly(report)
    slugs = (request.client,) if request.client else ORDER
    messages: list[str] = []
    if any(intent in request.intents for intent in ("call_counts", "call_minutes", "time_usage", "email_summary", "email_pending")):
        body = "\n\n".join(_activity_card(slug, report["clients"][slug]) for slug in slugs)
        if request.client is None:
            body += "\n\n" + _total_activity_card(report)
        if "email_pending" in request.intents:
            body += "\n\n<i>El conteo pendiente está verificado. Los nombres de cada correo pendiente se muestran solo cuando la fuente entrega ese detalle.</i>"
        messages.append("☎️ <b>ACTIVIDAD CONSULTADA</b>\n\n" + body)
    if "tasks" in request.intents:
        body = "\n\n".join(_task_card(slug, report["clients"][slug]) for slug in slugs)
        if request.client is None:
            body += "\n\n" + _total_task_card(report["clients"])
        messages.append("✅ <b>TAREAS CONSULTADAS</b>\n\n" + body)
    if "meetings" in request.intents:
        lines = []
        for slug in slugs:
            lines.extend(_meeting_lines(slug, report["clients"][slug]))
        messages.append("📅 <b>REUNIONES CONSULTADAS</b>\n\n" + "\n".join(lines))
    if "adherence" in request.intents:
        messages.append("🕐 <b>ADHERENCIA A BLOQUES</b>\n\n" + _adherence(report))
    if "funnel" in request.intents:
        lines = []
        for slug in slugs:
            movements = report["clients"][slug].get("movements") or {}
            detail = " · ".join(f"{html.escape(str(k))}: {int(v)}" for k, v in movements.items())
            lines.append(f"{_client_header(slug)} · {detail or 'Sin movimientos registrados'}")
        messages.append("🔄 <b>MOVIMIENTO DEL FUNNEL</b>\n\n" + "\n".join(lines))
    if "chart" in request.intents:
        messages.append("📈 El gráfico se genera con el cierre diario usando estas mismas métricas.")
    if "menu" in request.intents or not messages:
        messages.append(
            "Puedo responder por <b>llamadas y minutos</b>, <b>tiempo trabajado</b>, "
            "<b>tareas</b>, <b>correos</b>, <b>reuniones</b>, <b>funnel</b> o <b>adherencia</b>. "
            "También puedes indicar BAMBU TECH, GBS o BALIA."
        )
    return messages
