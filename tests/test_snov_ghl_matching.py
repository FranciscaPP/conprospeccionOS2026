"""Tests de sync/scripts/snov_ghl_matching.py (logica pura, sin red)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from snov_ghl_matching import extract_snov_enrichment, names_match, normalize_name

SAMPLE_PROSPECT_DATA = {
    "firstName": "Caterina A.",
    "lastName": "Cronoro V.",
    "name": "Caterina A. Cronoro V.",
    "country": "Chile",
    "locality": "Chile",
    "industry": "International Affairs",
    "phones": [],
    "social": [
        {"link": "https://www.linkedin.com/in/caterina-a-cronoro-v-6297a0163", "type": "linkedinProfile"},
        {"link": "https://www.linkedin.com/in/caterina-a-cronoro-v-6297a0163", "type": "linkedIn"},
    ],
    "currentJob": [
        {
            "companyName": "TranSapp",
            "position": "Commercial Manager",
            "socialLink": "https://www.linkedin.com/company/11570222",
            "site": "https://transapp.cl",
            "city": "Santiago",
            "size": "11-50",
            "industry": "Information Technology & Services",
            "country": "Chile",
        },
    ],
}


def test_normalize_name_quita_acentos_y_mayusculas():
    assert normalize_name("José García") == "jose garcia"


def test_normalize_name_none_da_vacio():
    assert normalize_name(None) == ""


def test_names_match_mismo_nombre():
    assert names_match("José García", "Jose", "Garcia") is True


def test_names_match_nombres_distintos():
    assert names_match("José García", "Juan", "Perez") is False


def test_names_match_ghl_sin_nombre_no_hay_choque():
    assert names_match("José García", None, None) is True


def test_names_match_snov_sin_nombre_no_hay_choque():
    assert names_match(None, "Juan", "Perez") is True


def test_extract_snov_enrichment_campos_basicos():
    result = extract_snov_enrichment(SAMPLE_PROSPECT_DATA)
    assert result["first_name"] == "Caterina A."
    assert result["last_name"] == "Cronoro V."
    assert result["name"] == "Caterina A. Cronoro V."
    assert result["company_name"] == "TranSapp"
    assert result["cargo"] == "Commercial Manager"
    assert result["website"] == "https://transapp.cl"
    assert result["tamano_empresa"] == "11-50"
    assert result["linkedin_empresa"] == "https://www.linkedin.com/company/11570222"
    assert result["linkedin_personal"] == "https://www.linkedin.com/in/caterina-a-cronoro-v-6297a0163"
    assert result["country"] == "Chile"
    assert result["city"] == "Santiago"
    assert result["phone"] is None


def test_extract_snov_enrichment_sin_currentjob_no_rompe():
    result = extract_snov_enrichment({"firstName": "Ana", "lastName": "Diaz", "name": "Ana Diaz"})
    assert result["company_name"] is None
    assert result["website"] is None
    assert result["name"] == "Ana Diaz"


def test_extract_snov_enrichment_con_telefono_string():
    data = dict(SAMPLE_PROSPECT_DATA, phones=["+56912345678"])
    assert extract_snov_enrichment(data)["phone"] == "+56912345678"


def test_extract_snov_enrichment_con_telefono_dict():
    data = dict(SAMPLE_PROSPECT_DATA, phones=[{"number": "+56912345678"}])
    assert extract_snov_enrichment(data)["phone"] == "+56912345678"


from snov_ghl_matching import resolve_custom_field_ids

RAW_CUSTOM_FIELDS = [
    {"id": "3x6OFmjHx0TKsa7YZ1hm", "name": "STATUS INTERÉS"},
    {"id": "73CZcGKJJr8hsSun2sV6", "name": "STATUS PROSPECTO"},
    {"id": "cargo-id", "name": "Cargo"},
    {"id": "industria-id", "name": "Industria"},
    {"id": "tamano-id", "name": "Tamaño Empresa"},
    {"id": "li-personal-id", "name": "Linkedin Personal"},
    {"id": "li-empresa-id", "name": "Linkedin Empresa"},
]


def test_resolve_custom_field_ids_mapea_las_claves_esperadas():
    result = resolve_custom_field_ids(RAW_CUSTOM_FIELDS)
    assert result["status_prospecto"] == "73CZcGKJJr8hsSun2sV6"
    assert result["cargo"] == "cargo-id"
    assert result["industria"] == "industria-id"
    assert result["tamano_empresa"] == "tamano-id"
    assert result["linkedin_personal"] == "li-personal-id"
    assert result["linkedin_empresa"] == "li-empresa-id"


def test_resolve_custom_field_ids_ignora_campos_no_mapeados():
    result = resolve_custom_field_ids(RAW_CUSTOM_FIELDS)
    assert "status_interes" not in result


from snov_ghl_matching import build_ghl_contact_payload, build_update_payload

ENRICHMENT = {
    "first_name": "Caterina A.",
    "last_name": "Cronoro V.",
    "name": "Caterina A. Cronoro V.",
    "country": "Chile",
    "city": "Santiago",
    "company_name": "TranSapp",
    "cargo": "Commercial Manager",
    "industria": "Information Technology & Services",
    "website": "https://transapp.cl",
    "tamano_empresa": "11-50",
    "linkedin_empresa": "https://www.linkedin.com/company/11570222",
    "linkedin_personal": "https://www.linkedin.com/in/caterina",
    "phone": None,
}

FIELD_IDS = {
    "cargo": "cargo-id",
    "industria": "industria-id",
    "tamano_empresa": "tamano-id",
    "linkedin_personal": "li-personal-id",
    "linkedin_empresa": "li-empresa-id",
}


def test_build_ghl_contact_payload_campos_estandar():
    payload = build_ghl_contact_payload(ENRICHMENT, "cate@transapp.cl", "gbs", FIELD_IDS)
    assert payload["email"] == "cate@transapp.cl"
    assert payload["firstName"] == "Caterina A."
    assert payload["lastName"] == "Cronoro V."
    assert payload["companyName"] == "TranSapp"
    assert payload["website"] == "https://transapp.cl"
    assert payload["country"] == "Chile"
    assert payload["source"] == "snov-gbs"
    assert payload["tags"] == ["gbs"]
    assert "phone" not in payload  # no se manda si no hay dato


def test_build_ghl_contact_payload_custom_fields():
    payload = build_ghl_contact_payload(ENRICHMENT, "cate@transapp.cl", "gbs", FIELD_IDS)
    custom = {cf["id"]: cf["value"] for cf in payload["customFields"]}
    assert custom["cargo-id"] == "Commercial Manager"
    assert custom["tamano-id"] == "11-50"


def test_build_update_payload_solo_lo_que_falta():
    existing = {"companyName": "TranSapp", "website": None, "customFields": []}
    payload = build_update_payload(existing, ENRICHMENT, FIELD_IDS)
    assert "companyName" not in payload  # ya estaba
    assert payload["website"] == "https://transapp.cl"  # faltaba
    custom = {cf["id"]: cf["value"] for cf in payload["customFields"]}
    assert custom["cargo-id"] == "Commercial Manager"


def test_build_update_payload_no_pisa_custom_field_con_valor():
    existing = {"companyName": "TranSapp", "website": "https://ya-cargado.cl",
                "customFields": [{"id": "cargo-id", "value": "Ya cargado a mano"}]}
    payload = build_update_payload(existing, ENRICHMENT, FIELD_IDS)
    assert "website" not in payload
    custom_ids = {cf["id"] for cf in payload.get("customFields", [])}
    assert "cargo-id" not in custom_ids


from snov_ghl_matching import GhlAction, decide_action


def test_decide_action_no_existe_crea():
    assert decide_action(None, ENRICHMENT, FIELD_IDS) == GhlAction.CREATE


def test_decide_action_existe_completo_no_hace_nada():
    existing = {
        "firstName": "Caterina", "lastName": "Cronoro",
        "companyName": "TranSapp", "website": "https://transapp.cl", "phone": None,
        "customFields": [{"id": "cargo-id", "value": "algo"}],
    }
    enrichment = dict(ENRICHMENT, phone=None)
    result = decide_action(existing, enrichment, {"cargo": "cargo-id"})
    assert result == GhlAction.SKIP_COMPLETE


def test_decide_action_existe_le_falta_algo_actualiza():
    existing = {"firstName": "Caterina", "lastName": "Cronoro", "companyName": None, "customFields": []}
    result = decide_action(existing, ENRICHMENT, FIELD_IDS)
    assert result == GhlAction.UPDATE


def test_decide_action_choque_de_nombre_no_toca():
    existing = {"firstName": "Juan", "lastName": "Perez", "companyName": None, "customFields": []}
    result = decide_action(existing, ENRICHMENT, FIELD_IDS)
    assert result == GhlAction.SKIP_MISMATCH
