from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFont

from .config import BACKGROUND_COLOR, CLIENTS, TEXT_COLOR


ORDER = ("bambutech", "gbs", "balia")
TOTAL_KEY = "total"
TOTAL_COLOR = "#D1D5DB"
HEADER_COLOR = "#CBD5E1"
GRID_COLOR = "#111827"
WORK_COLOR = "#86EFAC"
IDLE_COLOR = "#FDE047"


def _number(value: Any) -> int:
    return max(0, int(value or 0))


def _sum_rows(rows: Iterable[dict[str, int]], keys: Iterable[str]) -> dict[str, int]:
    rows = list(rows)
    return {key: sum(_number(row.get(key)) for row in rows) for key in keys}


def _task_row(data: dict) -> dict[str, int]:
    overdue = _number(data.get("tasks_overdue", data.get("overdue_pending")))
    today = _number(data.get("tasks_today", data.get("tasks_total")))
    total = overdue + today
    completed = min(total, _number(data.get("tasks_completed", data.get("tasks_done"))))
    return {
        "overdue": overdue,
        "today": today,
        "total": total,
        "completed": completed,
        "pending": max(0, total - completed),
        "percent": round(100 * completed / total) if total else 0,
    }


def _communication_rows(clients: dict, channel: str) -> dict[str, dict | None]:
    output: dict[str, dict | None] = {}
    known = []
    for slug in ORDER:
        source = clients[slug].get(channel)
        if source is None:
            output[slug] = None
            continue
        row = {
            "pending": _number(source.get("pending_previous")),
            "today": _number(source.get("today", source.get("received"))),
            "total": _number(source.get("total")),
            "responded": _number(source.get("responded")),
            "unanswered": _number(source.get("unanswered", source.get("pending"))),
        }
        if not row["total"]:
            row["total"] = row["pending"] + row["today"]
        row["responded"] = min(row["total"], row["responded"])
        row["unanswered"] = max(0, row["total"] - row["responded"])
        output[slug] = row
        known.append(row)
    total = _sum_rows(known, ("pending", "today", "total", "responded", "unanswered"))
    total["partial"] = len(known) != len(ORDER)
    output[TOTAL_KEY] = total
    return output


def build_table_document(report: dict) -> dict:
    clients = report["clients"]
    tasks = {slug: _task_row(clients[slug]) for slug in ORDER}
    task_total = _sum_rows(
        tasks.values(), ("overdue", "today", "total", "completed", "pending")
    )
    task_total["percent"] = (
        round(100 * task_total["completed"] / task_total["total"])
        if task_total["total"] else 0
    )
    tasks[TOTAL_KEY] = task_total

    calls_count = {}
    calls_minutes = {}
    outside = {}
    for slug in ORDER:
        data = clients[slug]
        calls_count[slug] = {
            "today": _number(data.get("calls")),
            "answered": _number(data.get("answered")),
            "unanswered": _number(data.get("unanswered")),
        }
        calls_minutes[slug] = {
            "today": _number(data.get("phone_seconds")),
            "answered": _number(data.get("answered_seconds", data.get("conversation_seconds"))),
            "unanswered": _number(data.get("unanswered_phone_seconds")),
        }
        source_outside = data.get("outside_hours") or {}
        outside[slug] = {
            period: {
                "count": _number((source_outside.get(period) or {}).get("count")),
                "phone_seconds": _number((source_outside.get(period) or {}).get("phone_seconds")),
            }
            for period in ("before", "lunch", "after", "total")
        }
    calls_count[TOTAL_KEY] = _sum_rows(
        calls_count.values(), ("today", "answered", "unanswered")
    )
    calls_minutes[TOTAL_KEY] = _sum_rows(
        calls_minutes.values(), ("today", "answered", "unanswered")
    )
    outside[TOTAL_KEY] = {
        period: _sum_rows(
            (outside[slug][period] for slug in ORDER), ("count", "phone_seconds")
        )
        for period in ("before", "lunch", "after", "total")
    }

    meetings = []
    meeting_count = 0
    for slug in ORDER:
        client_meetings = clients[slug].get("meetings") or []
        if isinstance(client_meetings, int):
            meeting_count += client_meetings
            meetings.append({"client": slug, "title": f"{client_meetings} reunión(es)", "chile": "N/D", "peru": "N/D"})
        elif client_meetings:
            meeting_count += len(client_meetings)
            for meeting in client_meetings:
                meetings.append({
                    "client": slug,
                    "title": str(meeting.get("title") or meeting.get("contact_name") or "Reunión"),
                    "chile": str(meeting.get("chile") or "N/D"),
                    "peru": str(meeting.get("peru") or "N/D"),
                })
        else:
            meetings.append({"client": slug, "title": "Sin reuniones", "chile": "—", "peru": "—"})

    adherence = []
    for block in report.get("block_adherence") or []:
        correct = _number(block.get("correct_calls"))
        other = _number(block.get("other_calls"))
        total_calls = correct + other
        result = "Sin actividad registrada" if total_calls == 0 else f"{round(100 * correct / total_calls)}% cliente"
        adherence.append({
            "block": f"{block.get('start', '')}–{block.get('end', '')}",
            "client": block.get("client"),
            "calls": correct,
            "other": other,
            "result": result,
        })

    work = report.get("work_time") or {}
    elapsed_seconds = _number(work.get("elapsed_seconds"))
    phone_seconds = calls_minutes[TOTAL_KEY]["today"]
    return {
        "day": report["day"],
        "cut": report["cut"],
        "sdr": str(report.get("sdr") or "Nora"),
        "meetings": meetings,
        "meeting_count": meeting_count,
        "tasks": tasks,
        "calls_count": calls_count,
        "calls_minutes": calls_minutes,
        "phone_time": {
            "worked_seconds": phone_seconds,
            "unregistered_seconds": max(0, elapsed_seconds - phone_seconds),
        },
        "email": _communication_rows(clients, "email"),
        "whatsapp": _communication_rows(clients, "whatsapp"),
        "work_time": {
            "worked_seconds": _number(work.get("worked_seconds")),
            "unregistered_seconds": _number(work.get("unregistered_seconds")),
        },
        "adherence": adherence,
        "outside": outside,
    }


def _font(size: int, bold: bool = False):
    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default(size=size)


def _duration(seconds: int) -> str:
    minutes = round(_number(seconds) / 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes:02d} min" if hours else f"{minutes} min"


def _fit_text(draw: ImageDraw.ImageDraw, text: str, width: int, bold: bool = False, maximum: int = 24):
    text = str(text)
    for size in range(maximum, 13, -1):
        font = _font(size, bold)
        if draw.textbbox((0, 0), text, font=font)[2] <= width - 12:
            return text, font
    font = _font(14, bold)
    while text and draw.textbbox((0, 0), text + "…", font=font)[2] > width - 12:
        text = text[:-1]
    return text + "…", font


def _cell(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    *,
    fill: str = "#FFFFFF",
    bold: bool = False,
    align: str = "center",
    color: str = TEXT_COLOR,
) -> None:
    draw.rectangle(box, fill=fill, outline=GRID_COLOR, width=1)
    x0, y0, x1, y1 = box
    fitted, font = _fit_text(draw, text, x1 - x0, bold)
    bounds = draw.textbbox((0, 0), fitted, font=font)
    text_width, text_height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    x = x0 + 8 if align == "left" else x0 + (x1 - x0 - text_width) / 2
    y = y0 + (y1 - y0 - text_height) / 2 - bounds[1]
    draw.text((x, y), fitted, fill=color, font=font)


def _table(
    draw: ImageDraw.ImageDraw,
    y: int,
    title: str,
    headers: list[str],
    rows: list[list[str]],
    widths: list[int],
    row_keys: list[str] | None = None,
) -> int:
    margin = 35
    draw.text((margin, y), title, fill=TEXT_COLOR, font=_font(28, True))
    y += 42
    x = margin
    for header, width in zip(headers, widths):
        _cell(draw, (x, y, x + width, y + 44), header, fill=HEADER_COLOR, bold=True)
        x += width
    y += 44
    for index, row in enumerate(rows):
        key = row_keys[index] if row_keys else ""
        x = margin
        for column, (value, width) in enumerate(zip(row, widths)):
            fill = "#FFFFFF"
            bold = key == TOTAL_KEY
            align = "center"
            if column == 0:
                align = "left"
                if key in CLIENTS:
                    fill = CLIENTS[key].color
                elif key == TOTAL_KEY:
                    fill = TOTAL_COLOR
            elif key == TOTAL_KEY:
                fill = "#F3F4F6"
            _cell(draw, (x, y, x + width, y + 44), value, fill=fill, bold=bold, align=align)
            x += width
        y += 44
    return y + 30


def _header(draw: ImageDraw.ImageDraw, document: dict, page: int) -> int:
    draw.text((35, 28), "REPORTE OPERATIVO · EQUIPO ALICIA", fill=TEXT_COLOR, font=_font(34, True))
    subtitle = (
        f"{document['day'].strftime('%d/%m/%Y')} · corte {document['cut'].strftime('%H:%M')} Chile"
        f" · SDR {document['sdr']} · {page} de 2"
    )
    draw.text((35, 76), subtitle, fill="#475569", font=_font(23))
    return 125


def _client_name(slug: str) -> str:
    return CLIENTS[slug].name if slug in CLIENTS else "TOTAL"


def _render_image_one(document: dict) -> Image.Image:
    image = Image.new("RGB", (1200, 2600), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)
    y = _header(draw, document, 1)

    meeting_rows = [[_client_name(row["client"]), row["title"], row["chile"], row["peru"]] for row in document["meetings"]]
    meeting_keys = [row["client"] for row in document["meetings"]]
    meeting_rows.append(["TOTAL", f"{document['meeting_count']} reunión(es)", "", ""])
    meeting_keys.append(TOTAL_KEY)
    y = _table(draw, y, "REUNIONES DE HOY", ["Cliente", "Contacto / empresa", "Hora Chile", "Hora Perú"], meeting_rows, [220, 510, 200, 200], meeting_keys)

    task_rows, task_keys = [], []
    for slug in (*ORDER, TOTAL_KEY):
        row = document["tasks"][slug]
        task_rows.append([_client_name(slug), str(row["overdue"]), str(row["today"]), str(row["total"]), f"{row['completed']} · {row['percent']}%", str(row["pending"])])
        task_keys.append(slug)
    y = _table(draw, y, "TAREAS", ["Cliente", "Atrasadas", "Hoy", "Total", "Avance", "Pendiente"], task_rows, [230, 150, 150, 150, 250, 200], task_keys)

    count_rows, minute_rows, keys = [], [], []
    for slug in (*ORDER, TOTAL_KEY):
        count = document["calls_count"][slug]
        minutes = document["calls_minutes"][slug]
        count_rows.append([_client_name(slug), str(count["today"]), str(count["answered"]), str(count["unanswered"])])
        minute_rows.append([_client_name(slug), _duration(minutes["today"]), _duration(minutes["answered"]), _duration(minutes["unanswered"])])
        keys.append(slug)
    y = _table(draw, y, "LLAMADAS N°", ["Cliente", "Hoy", "Contestadas >20 s", "Sin contestar ≤20 s"], count_rows, [230, 250, 325, 325], keys)
    y = _table(draw, y, "LLAMADAS MINUTOS", ["Cliente", "Hoy", "Contestadas >20 s", "Sin contestar ≤20 s"], minute_rows, [230, 250, 325, 325], keys)

    phone = document["phone_time"]
    y = _table(draw, y, "TOTAL HORA / MINUTOS DE LLAMADAS", ["Trabajados", "Sin trabajar"], [[_duration(phone["worked_seconds"]), _duration(phone["unregistered_seconds"])]], [565, 565])
    return image.crop((0, 0, 1200, min(2600, y + 10)))


def _communication_table(draw, y, title, rows_document):
    rows, keys = [], []
    for slug in (*ORDER, TOTAL_KEY):
        row = rows_document[slug]
        if row is None:
            values = ["N/D"] * 5
        else:
            values = [str(row[key]) for key in ("pending", "today", "total", "responded", "unanswered")]
            if slug == TOTAL_KEY and row.get("partial"):
                values[2] += " (parcial)"
        rows.append([_client_name(slug), *values])
        keys.append(slug)
    return _table(draw, y, title, ["Cliente", "Pendiente", "Hoy", "Total", "Respondidos", "Sin responder"], rows, [230, 170, 150, 190, 190, 200], keys)


def _render_image_two(document: dict) -> Image.Image:
    image = Image.new("RGB", (1200, 2800), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)
    y = _header(draw, document, 2)
    y = _communication_table(draw, y, "CORREOS", document["email"])
    y = _communication_table(draw, y, "WHATSAPP", document["whatsapp"])

    work = document["work_time"]
    draw.text((35, y), "RESUMEN FINAL", fill=TEXT_COLOR, font=_font(28, True))
    y += 42
    _cell(draw, (35, y, 600, y + 58), "TOTAL TRABAJO", fill=WORK_COLOR, bold=True, align="left")
    _cell(draw, (600, y, 1165, y + 58), _duration(work["worked_seconds"]), fill="#FFFFFF", bold=True)
    y += 58
    _cell(draw, (35, y, 600, y + 58), "TOTAL SIN TRABAJAR", fill=IDLE_COLOR, bold=True, align="left")
    _cell(draw, (600, y, 1165, y + 58), _duration(work["unregistered_seconds"]), fill="#FFFFFF", bold=True)
    y += 90

    adherence_rows, adherence_keys = [], []
    for row in document["adherence"]:
        slug = row["client"]
        adherence_rows.append([row["block"], _client_name(slug), str(row["calls"]), str(row["other"]), row["result"]])
        adherence_keys.append(slug)
    if not adherence_rows:
        adherence_rows = [["—", "Sin bloques finalizados", "0", "0", "Sin actividad registrada"]]
        adherence_keys = [""]
    y = _table(draw, y, "ADHERENCIA A BLOQUES", ["Bloque Chile", "Cliente", "Llamadas", "Otros clientes", "Resultado"], adherence_rows, [190, 230, 160, 200, 350], adherence_keys)

    outside_rows, outside_keys = [], []
    for slug in (*ORDER, TOTAL_KEY):
        row = document["outside"][slug]
        values = []
        for period in ("before", "lunch", "after", "total"):
            values.extend([str(row[period]["count"]), _duration(row[period]["phone_seconds"])])
        outside_rows.append([_client_name(slug), *values])
        outside_keys.append(slug)
    y = _table(draw, y, "TRABAJO FUERA DE HORARIO", ["Cliente", "Antes N°", "Antes min", "Almuerzo N°", "Almuerzo min", "Después N°", "Después min", "Total N°", "Total min"], outside_rows, [170, 100, 125, 110, 135, 110, 135, 100, 145], outside_keys)
    return image.crop((0, 0, 1200, min(2800, y + 10)))


def render_tabular_report(report: dict, directory: str | Path) -> list[Path]:
    document = build_table_document(report)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    stem = f"reporte_nora_{document['day'].isoformat()}_{document['cut'].strftime('%H%M')}"
    paths = [directory / f"{stem}_1.png", directory / f"{stem}_2.png"]
    for image, path in zip((_render_image_one(document), _render_image_two(document)), paths):
        image.save(path, format="PNG", optimize=True)
    return paths
