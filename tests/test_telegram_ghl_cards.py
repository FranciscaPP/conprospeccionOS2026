"""Tests de sync/scripts/telegram_ghl_cards.py (logica pura, sin red)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from telegram_ghl_cards import build_status_keyboard, order_status_options
from telegram_ghl_cards import (
    build_already_status_text,
    build_mismatch_alert,
    build_new_contact_card,
    build_status_changed_text,
    build_updated_contact_card,
)
from telegram_ghl_cards import parse_task_command
from telegram_ghl_cards import build_agendar_prompt, build_status_prompt, build_tarea_prompt

ENRICHMENT = {
    "first_name": "Caterina", "last_name": "Cronoro", "name": "Caterina Cronoro",
    "cargo": "Commercial Manager", "company_name": "TranSapp", "tamano_empresa": "11-50",
    "website": "https://transapp.cl", "country": "Chile", "linkedin_personal": "https://linkedin.com/in/cate",
}

REAL_GHL_OPTIONS = [
    "No Contesta", "No Interesado", "Información Adicional", "Coordinando Reunión",
    "Reunión Agendada", "Reagendar Reunión", "Teléfono / Whatsapp no existen",
    "Deriva Refiere Directo", "Deriva Refiere Seguimiento", "No Califica",
]


def test_order_status_options_sigue_el_orden_de_embudo():
    ordered = order_status_options(REAL_GHL_OPTIONS)
    assert ordered[0] == "No Contesta"
    assert ordered[1] == "Información Adicional"
    assert ordered[2] == "Coordinando Reunión"
    assert ordered.index("No Interesado") > ordered.index("Reunión Agendada")


def test_order_status_options_no_pierde_ni_agrega_opciones():
    ordered = order_status_options(REAL_GHL_OPTIONS)
    assert sorted(ordered) == sorted(REAL_GHL_OPTIONS)


def test_build_status_keyboard_dos_por_fila():
    ordered = order_status_options(REAL_GHL_OPTIONS)
    keyboard = build_status_keyboard(ordered, "contact123")
    rows = keyboard["inline_keyboard"]
    assert all(len(row) <= 2 for row in rows)
    assert sum(len(row) for row in rows) == len(REAL_GHL_OPTIONS)


def test_build_status_keyboard_callback_data_tiene_indice_no_texto():
    ordered = order_status_options(REAL_GHL_OPTIONS)
    keyboard = build_status_keyboard(ordered, "contact123")
    first_button = keyboard["inline_keyboard"][0][0]
    assert first_button["callback_data"] == "status:contact123:0"
    assert first_button["text"] == ordered[0]
    for row in keyboard["inline_keyboard"]:
        for button in row:
            assert len(button["callback_data"].encode("utf-8")) <= 64


def test_build_new_contact_card_incluye_los_datos_clave():
    enrichment = dict(ENRICHMENT, phone="+52 55 1234 5678")
    text = build_new_contact_card(
        "bambutech", "BAMBUTECH", "BambuTech 21 Julio", enrichment, "cate@transapp.cl",
        reply_snippet="Hola, gracias por tu correo, me interesa saber más.",
    )
    assert "🟢" in text
    assert "CRM" in text
    assert "GHL" not in text
    assert "GoHighLevel" not in text
    assert "Respondé" not in text  # sin voseo
    assert "+52 55 1234 5678" in text
    assert "gracias por tu correo" in text


def test_build_new_contact_card_sin_telefono_ni_respuesta_no_rompe():
    text = build_new_contact_card("gbs", "GBS LOGISTICS", "GBS 20 julio", {}, "x@y.cl")
    assert "(sin nombre)" in text


def test_build_updated_contact_card_dice_crm_no_ghl():
    text = build_updated_contact_card("gbs", "GBS LOGISTICS", "Caterina Cronoro", "cate@transapp.cl")
    assert "actualizado" in text.lower()
    assert "CRM" in text
    assert "GHL" not in text


def test_build_mismatch_alert():
    text = build_mismatch_alert("GBS LOGISTICS", "compartido@empresa.cl", "Juan Perez", "Jose Garcia")
    assert "compartido@empresa.cl" in text
    assert "Juan Perez" in text
    assert "Jose Garcia" in text
    assert "No se modificó" in text


def test_build_already_status_text():
    text = build_already_status_text("Caterina Cronoro", "Coordinando Reunión")
    assert "Caterina Cronoro" in text
    assert "Coordinando Reunión" in text
    assert "ya está" in text


def test_build_status_changed_text():
    text = build_status_changed_text("Caterina Cronoro", "Coordinando Reunión")
    assert "Caterina Cronoro" in text
    assert "Coordinando Reunión" in text


def test_parse_task_command_con_dos_puntos():
    assert parse_task_command("tarea: llamar mañana 10am") == "llamar mañana 10am"


def test_parse_task_command_sin_dos_puntos():
    assert parse_task_command("tarea llamar mañana 10am") == "llamar mañana 10am"


def test_parse_task_command_mayusculas():
    assert parse_task_command("TAREA: Llamar mañana") == "Llamar mañana"


def test_parse_task_command_no_es_tarea():
    assert parse_task_command("mover a coordinando reunion") is None


def test_parse_task_command_vacio_da_none():
    assert parse_task_command("tarea:") is None


def test_build_status_prompt():
    text = build_status_prompt("Caterina Cronoro")
    assert text.startswith("🔵")
    assert "Caterina Cronoro" in text


def test_build_agendar_prompt():
    text = build_agendar_prompt("Caterina Cronoro")
    assert text.startswith("🟢")
    assert "Caterina Cronoro" in text


def test_build_tarea_prompt():
    text = build_tarea_prompt("Caterina Cronoro")
    assert text.startswith("⚪")
    assert "Caterina Cronoro" in text
