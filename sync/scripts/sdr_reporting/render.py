from __future__ import annotations

import html
from collections import defaultdict

from .config import CLIENTS


ORDER = ("bambutech", "gbs", "balia")
WEEKDAYS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")


def _hm(seconds: int) -> str:
    minutes = round(max(0, seconds) / 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}" if hours else f"{minutes}m"


def _pct(done: int, total: int) -> int:
    return round(100 * done / total) if total else 0


def _totals(clients: dict) -> dict:
    keys = (
        "tasks_done", "tasks_total", "overdue_pending", "calls", "contacts",
        "answered", "unanswered", "conversation_seconds", "phone_seconds", "meetings",
    )
    return {key: sum(int(clients[slug].get(key) or 0) for slug in ORDER) for key in keys}


def _task_table(clients: dict) -> str:
    labels: dict[str, dict[str, tuple[int, int]]] = defaultdict(dict)
    for slug in ORDER:
        for label, values in clients[slug].get("task_types", {}).items():
            labels[label][slug] = values
    lines = [f"{'TAREA':<16}{'BAM':>7}{'GBS':>7}{'BAL':>7}{'TOTAL':>8}"]
    for label in list(labels)[:8]:
        pairs = [labels[label].get(slug, (0, 0)) for slug in ORDER]
        total = (sum(pair[0] for pair in pairs), sum(pair[1] for pair in pairs))
        values = [f"{a}/{b}" for a, b in [*pairs, total]]
        lines.append(f"{label[:15]:<16}" + "".join(f"{value:>7}" for value in values[:3]) + f"{values[3]:>8}")
    return "<pre>" + html.escape("\n".join(lines)) + "</pre>"


def _call_table(clients: dict, totals: dict) -> str:
    rows = [
        ("Contactos", "contacts", str), ("Llamadas", "calls", str),
        ("Contestadas", "answered", str), ("No contesta", "unanswered", str),
        ("Conversación", "conversation_seconds", _hm),
        ("Teléfono", "phone_seconds", _hm),
    ]
    lines = [f"{'':<14}{'BAM':>7}{'GBS':>7}{'BAL':>7}{'TOTAL':>8}"]
    for label, key, formatter in rows:
        values = [formatter(clients[slug].get(key, 0)) for slug in ORDER]
        values.append(formatter(totals[key]))
        lines.append(f"{label:<14}" + "".join(f"{value:>7}" for value in values[:3]) + f"{values[3]:>8}")
    return "<pre>" + html.escape("\n".join(lines)) + "</pre>"


def _email_table(clients: dict) -> str:
    rows = (
        ("Recibidos", "received"), ("Respondidos", "responded"),
        ("Pendientes", "pending"), ("Nuevos manual", "new_manual"),
    )
    lines = [f"{'':<14}{'BAM':>7}{'GBS':>7}{'BAL':>7}{'TOTAL':>8}"]
    for label, key in rows:
        values = [int((clients[slug].get("email") or {}).get(key) or 0) for slug in ORDER]
        lines.append(f"{label:<14}" + "".join(f"{value:>7}" for value in values) + f"{sum(values):>8}")
    return "<pre>" + html.escape("\n".join(lines)) + "</pre>"


def _movement_table(clients: dict) -> str:
    labels = []
    for slug in ORDER:
        for label in clients[slug].get("movements", {}):
            if label not in labels:
                labels.append(label)
    if not labels:
        return "Sin movimientos de etapa registrados en este corte."
    lines = [f"{'MOVIMIENTO':<17}{'BAM':>6}{'GBS':>6}{'BAL':>6}{'TOTAL':>7}"]
    for label in labels[:8]:
        values = [int(clients[slug].get("movements", {}).get(label) or 0) for slug in ORDER]
        lines.append(f"{'-> ' + label[:14]:<17}" + "".join(f"{value:>6}" for value in values) + f"{sum(values):>7}")
    return "<pre>" + html.escape("\n".join(lines)) + "</pre>"


def render_hourly(report: dict) -> list[str]:
    clients = report["clients"]
    total = _totals(clients)
    cut = report["cut"]
    title = f"📊 <b>REPORTE OPERATIVO · {cut.strftime('%H:%M')}</b>"
    header = f"{title}\n\n📅 {WEEKDAYS[cut.weekday()]} {cut.strftime('%d/%m')}\n👤 SDR: {html.escape(report.get('sdr', 'Nora'))}"
    total_pct = _pct(total["tasks_done"], total["tasks_total"])
    client_lines = []
    for slug in ORDER:
        cfg, data = CLIENTS[slug], clients[slug]
        client_lines.append(
            f"{cfg.emoji} {cfg.name} · {data.get('tasks_done', 0)}/{data.get('tasks_total', 0)} · "
            f"{_pct(data.get('tasks_done', 0), data.get('tasks_total', 0))}%"
        )
    baseline_note = "" if report.get("baseline_available") else "\nℹ️ Baseline inicial no disponible para este primer corte."
    overdue_detail = []
    for slug in ORDER:
        cfg = CLIENTS[slug]
        for contact in clients[slug].get("overdue_contacts", []):
            overdue_detail.append(
                f"{cfg.emoji} {html.escape(contact['name'])} · "
                f"{html.escape(contact['type'])} · {contact['days']} días vencida"
            )
    msg1 = (
        f"{header}\n\n🎯 <b>01 · META OPERATIVA</b>\n\n"
        f"<b>TOTAL: {total['tasks_done']} / {total['tasks_total']} · {total_pct}%</b>\n"
        + "\n".join(client_lines)
        + f"\n\nPendientes: {total['tasks_total'] - total['tasks_done']}\n"
          f"Arrastre vencido pendiente: {total['overdue_pending']}"
        + baseline_note
        + "\n\n<b>02 · AVANCE POR TIPO DE TAREA</b>\n\n"
        + _task_table(clients)
        + "\n<i>Completadas/meta de tareas GHL; no representan llamadas. "
          "“Otro” agrupa títulos que GHL no permite clasificar con certeza.</i>\n"
        + f"\n🔴 <b>03 · ARRASTRE VENCIDO</b>\n\nSiguen vencidas: <b>{total['overdue_pending']}</b>"
        + ("\n\n<b>Contactos prioritarios</b>\n" + "\n".join(overdue_detail) if overdue_detail else "")
    )

    adherence_lines = []
    true_gap_lines = []
    for block in report.get("block_adherence", []):
        cfg = CLIENTS[block["client"]]
        adherence_lines.append(
            f"{cfg.emoji} <b>{cfg.name}</b> · {block['start']}–{block['end']}\n"
            f"Cliente correcto: {block['correct_calls']} · Otros clientes: {block['other_calls']}"
        )
        true_gap_lines.extend(
            f"{cfg.name} · {gap} sin actividad registrada"
            for gap in block.get("no_activity_gaps", [])
        )
    adherence_text = "\n\n".join(adherence_lines) or "Sin bloques transcurridos."
    gaps_text = "\n".join(true_gap_lines) if true_gap_lines else "Sin huecos generales de 20 min dentro de bloques."
    msg2 = (
        f"☎️ <b>04 · LLAMADAS</b>\n\n{_call_table(clients, total)}\n"
        f"Contactos llamados más de una vez: "
        f"{sum(int(clients[s].get('repeated_contacts') or 0) for s in ORDER)}\n\n"
        f"⏱️ <b>05 · TIEMPO DE ACTIVIDAD</b>\n\n"
        f"Teléfono total: <b>{_hm(total['phone_seconds'])}</b>\n"
        "Actividad registrada: solo intervalos confirmados por la fuente.\n\n"
        f"🕐 <b>06 · ADHERENCIA A BLOQUES</b>\n\n{adherence_text}\n\n"
        f"⚠️ <b>HUECOS SIN ACTIVIDAD REGISTRADA</b>\n{gaps_text}\n\n"
        "🔥 <b>CUMPLIMIENTO VENTANA CRÍTICA</b>\n"
        "Se calcula con actividad telefónica dentro del bloque asignado."
    )

    meetings = "\n".join(
        f"{CLIENTS[s].emoji} {CLIENTS[s].name} · {clients[s].get('meetings', 0)}" for s in ORDER
    )
    email = "Sin fuente manual confiable" if not report.get("email_available") else _email_table(clients)
    comparison = "Sin snapshot comparable de ayer a esta hora." if report.get("comparison") is None else report["comparison"]
    alerts = report.get("alerts") or []
    alert_text = "\n".join(f"{i}. {html.escape(text)}" for i, text in enumerate(alerts[:3], 1)) or "Sin alertas accionables nuevas."
    msg3 = (
        "🔄 <b>07 · MOVIMIENTO DEL FUNNEL</b>\n\n"
        + _movement_table(clients)
        + f"\n\n✉️ <b>08 · EMAIL MANUAL</b>\n\n{email}"
        + f"\n\n🚀 <b>09 · REUNIONES AGENDADAS HOY</b>\n\n{meetings}\n\n<b>TOTAL · {total['meetings']}</b>"
        + f"\n\n📈 <b>10 · VS AYER · MISMA HORA</b>\n\n{html.escape(str(comparison))}"
        + f"\n\n⚠️ <b>ATENCIÓN</b>\n\n{alert_text}"
    )
    return [msg1, msg2, msg3]
