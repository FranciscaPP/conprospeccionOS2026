"""Tests de los metodos de escritura/resolucion nuevos de ghl_client.py,
con httpx mockeado (sin llamadas reales a GHL)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from ghl_client import GHLClient


def _mock_response(json_data, status=200):
    response = MagicMock()
    response.json.return_value = json_data
    response.status_code = status
    response.raise_for_status.return_value = None
    return response


def test_find_contact_by_email_encuentra_match_exacto():
    client = GHLClient("token")
    client.client.get = MagicMock(return_value=_mock_response({
        "contacts": [
            {"id": "abc", "email": "otro@x.cl"},
            {"id": "xyz", "email": "cate@transapp.cl"},
        ],
    }))

    result = client.find_contact_by_email("loc1", "cate@transapp.cl")

    assert result["id"] == "xyz"


def test_find_contact_by_email_sin_match_da_none():
    client = GHLClient("token")
    client.client.get = MagicMock(return_value=_mock_response({"contacts": []}))

    assert client.find_contact_by_email("loc1", "nadie@x.cl") is None


def test_find_contact_by_email_encuentra_match_en_additional_emails():
    # GHL tambien deduplica por additionalEmails (no solo el email principal).
    # Shape real confirmado en vivo: lista de dicts [{"email": "..."}].
    client = GHLClient("token")
    client.client.get = MagicMock(return_value=_mock_response({
        "contacts": [
            {
                "id": "n8RE3BmeUWuurdIflRHK",
                "email": "carleth.torres@genommalab.com",
                "additionalEmails": [{"email": "alejandra@conexioncomercial.mx"}],
            },
        ],
    }))

    result = client.find_contact_by_email("loc1", "Alejandra@ConexionComercial.mx")

    assert result["id"] == "n8RE3BmeUWuurdIflRHK"


def test_custom_field_id_map_usa_cache_por_location():
    client = GHLClient("token")
    client.client.get = MagicMock(return_value=_mock_response({
        "customFields": [{"id": "cargo-id", "name": "Cargo"}],
    }))

    first = client.custom_field_id_map("loc1")
    second = client.custom_field_id_map("loc1")

    assert first["cargo"] == "cargo-id"
    assert second == first
    client.client.get.assert_called_once()  # cacheado, no llama dos veces


def test_custom_field_options_busca_por_id():
    client = GHLClient("token")
    client.client.get = MagicMock(return_value=_mock_response({
        "customFields": [
            {"id": "status-id", "name": "STATUS PROSPECTO", "picklistOptions": ["No Contesta", "No Interesado"]},
        ],
    }))

    options = client.custom_field_options("loc1", "status-id")

    assert options == ["No Contesta", "No Interesado"]


def test_create_contact_manda_location_id_en_el_body():
    client = GHLClient("token")
    client.client.post = MagicMock(return_value=_mock_response({"contact": {"id": "new1"}}))

    result = client.create_contact("loc1", {"email": "a@b.cl"})

    args, kwargs = client.client.post.call_args
    assert args[0] == "/contacts/"
    assert kwargs["json"]["locationId"] == "loc1"
    assert kwargs["json"]["email"] == "a@b.cl"
    assert result["contact"]["id"] == "new1"


def test_update_contact_llama_put_con_el_id():
    client = GHLClient("token")
    client.client.put = MagicMock(return_value=_mock_response({"contact": {"id": "c1"}}))

    client.update_contact("c1", {"website": "https://x.cl"})

    args, kwargs = client.client.put.call_args
    assert args[0] == "/contacts/c1"
    assert kwargs["json"] == {"website": "https://x.cl"}


def test_update_custom_field_arma_el_payload_correcto():
    client = GHLClient("token")
    client.update_contact = MagicMock(return_value={"contact": {"id": "c1"}})

    client.update_custom_field("c1", "field-id", "Coordinando Reunión")

    client.update_contact.assert_called_once_with(
        "c1", {"customFields": [{"id": "field-id", "value": "Coordinando Reunión"}]},
    )


def test_create_task_manda_titulo_y_fecha():
    client = GHLClient("token")
    client.client.post = MagicMock(return_value=_mock_response({"id": "task1"}))

    client.create_task("c1", title="Llamar", due_date_iso="2026-09-25T13:00:00+00:00", body="Llamar mañana")

    args, kwargs = client.client.post.call_args
    assert args[0] == "/contacts/c1/tasks"
    assert kwargs["json"]["title"] == "Llamar"
    assert kwargs["json"]["dueDate"] == "2026-09-25T13:00:00+00:00"
    assert kwargs["json"]["body"] == "Llamar mañana"
