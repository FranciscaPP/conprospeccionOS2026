"""Tests de los metodos de escritura/resolucion nuevos de ghl_client.py,
con httpx mockeado (sin llamadas reales a GHL)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from ghl_client import DuplicateContactError, GHLClient


def _mock_response(json_data, status=200):
    response = MagicMock()
    response.json.return_value = json_data
    response.status_code = status
    if status >= 400:
        request = httpx.Request("POST", "https://services.leadconnectorhq.com/contacts/")
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=request, response=httpx.Response(status, request=request, json=json_data),
        )
    else:
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


def test_create_contact_400_duplicado_lanza_duplicate_contact_error():
    # Caso real de produccion: GHL rechaza el create porque el email buscado
    # matchea additionalEmails de un contacto existente. GHL nunca devuelve
    # ese contacto en la busqueda previa (query= no indexa additionalEmails),
    # pero el 400 trae el contactId real en meta.contactId.
    client = GHLClient("token")
    error_body = {
        "statusCode": 400,
        "message": "This location does not allow duplicated contacts.",
        "meta": {
            "contactName": "Carleth Torres Villarreal",
            "contactId": "n8RE3BmeUWuurdIflRHK",
            "matchingField": "additionalEmail",
        },
        "traceId": "abc-123",
    }
    client.client.post = MagicMock(return_value=_mock_response(error_body, status=400))

    with pytest.raises(DuplicateContactError) as exc_info:
        client.create_contact("loc1", {"email": "alejandra@conexioncomercial.mx"})

    assert exc_info.value.contact_id == "n8RE3BmeUWuurdIflRHK"
    assert exc_info.value.error_body == error_body


def test_create_contact_400_sin_meta_contact_id_no_es_duplicado():
    # 400 de validacion normal (sin meta.contactId) debe seguir propagando
    # el HTTPStatusError de siempre, no confundirse con un duplicado.
    client = GHLClient("token")
    error_body = {"statusCode": 400, "message": "email must be a valid email", "meta": {}}
    client.client.post = MagicMock(return_value=_mock_response(error_body, status=400))

    with pytest.raises(httpx.HTTPStatusError):
        client.create_contact("loc1", {"email": "no-es-un-email"})


def test_create_contact_400_con_contact_id_pero_sin_mensaje_duplicado_no_es_duplicado():
    # meta.contactId presente pero el mensaje no habla de duplicados: no debe
    # dispararse DuplicateContactError por las dudas (falso positivo).
    client = GHLClient("token")
    error_body = {"statusCode": 400, "message": "otro tipo de error", "meta": {"contactId": "xyz"}}
    client.client.post = MagicMock(return_value=_mock_response(error_body, status=400))

    with pytest.raises(httpx.HTTPStatusError):
        client.create_contact("loc1", {"email": "a@b.cl"})


def test_create_contact_exitoso_no_lanza_duplicate_contact_error():
    client = GHLClient("token")
    client.client.post = MagicMock(return_value=_mock_response({"contact": {"id": "new1"}}, status=200))

    result = client.create_contact("loc1", {"email": "a@b.cl"})

    assert result["contact"]["id"] == "new1"


def test_process_client_recupera_de_contacto_duplicado_como_update(monkeypatch):
    # Reproduce el bug de produccion completo: find_contact_by_email no
    # encuentra nada (GHL no indexa additionalEmails en la busqueda), el
    # create_contact() explota con DuplicateContactError, y process_client()
    # debe recuperarse trayendo el contacto real y actualizandolo, sumando a
    # stats["updated"] en vez de perder el prospecto.
    import sync_snov_replies_to_ghl as sync_mod

    monkeypatch.setenv("GHL_TOKEN_TESTCLIENT", "tok")

    ghl_mock = MagicMock()
    ghl_mock.custom_field_id_map.return_value = {}
    ghl_mock.find_contact_by_email.return_value = None
    ghl_mock.create_contact.side_effect = DuplicateContactError(
        "n8RE3BmeUWuurdIflRHK",
        {
            "message": "This location does not allow duplicated contacts.",
            "meta": {"contactId": "n8RE3BmeUWuurdIflRHK", "matchingField": "additionalEmail"},
        },
    )
    ghl_mock.get_contact.return_value = {
        "contact": {
            "id": "n8RE3BmeUWuurdIflRHK",
            "companyName": None,
            "website": None,
            "phone": None,
            "customFields": [],
        },
    }
    ghl_mock.update_contact.return_value = {"contact": {"id": "n8RE3BmeUWuurdIflRHK"}}
    monkeypatch.setattr(sync_mod, "GHLClient", MagicMock(return_value=ghl_mock))

    snov_mock = MagicMock()
    snov_mock.replies.return_value = [
        {"prospectEmail": "alejandra@conexioncomercial.mx", "prospectId": "p1", "campaign": "camp1"},
    ]
    snov_mock.prospect_by_id.return_value = {
        "data": {
            "firstName": "Alejandra",
            "lastName": "Torres",
            "name": "Alejandra Torres",
            "currentJob": [{"companyName": "Acme"}],
            "social": [],
            "phones": [],
        },
    }

    supabase_mock = MagicMock()
    client = {"slug": "testclient", "ghl_location_id": "loc1", "nombre": "Test Client"}
    stats = {"created": 0, "updated": 0, "mismatch": 0, "skipped": 0}

    sync_mod.process_client(client, ["camp1"], snov_mock, supabase_mock, stats, dry_run=False)

    ghl_mock.create_contact.assert_called_once()
    ghl_mock.get_contact.assert_called_once_with("n8RE3BmeUWuurdIflRHK")
    ghl_mock.update_contact.assert_called_once()
    assert ghl_mock.update_contact.call_args[0][0] == "n8RE3BmeUWuurdIflRHK"
    assert stats["updated"] == 1
    assert stats["created"] == 0


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
