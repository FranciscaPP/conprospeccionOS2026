# Snov reply -> contacto GHL + bot Telegram por cliente — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cuando un prospecto responde a una campaña de Snov (Balia, GBS o BambuTech), crear/actualizar automáticamente su contacto en GoHighLevel con los datos de Snov, avisar por un bot de Telegram propio de cada cliente, y permitir desde ahí mover el estatus del prospecto (`STATUS PROSPECTO`) o crearle una tarea en GHL.

**Architecture:** Dos scripts nuevos e independientes en `sync/scripts/`: `sync_snov_replies_to_ghl.py` (job periódico por Task Scheduler: detecta respuestas vía `SnovClient.replies()`, enriquece con `SnovClient.prospect_by_id()`, crea/actualiza el contacto en GHL, avisa por Telegram) y `telegram_ghl_bot.py` (proceso de larga duración, long-polling, uno por cliente en threads separados: maneja "mover estatus" con botones y "crear tarea" por texto, disparado al responder la tarjeta). La lógica de negocio pura (matching, mapeo de campos, armado de tarjetas) vive en dos módulos sin red (`snov_ghl_matching.py`, `telegram_ghl_cards.py`) para poder testearla sin llamadas reales. `ghl_client.py` (hoy 100% lectura) se amplía con métodos de escritura. Nada de esto toca Alicia ni los `sync_*.py` existentes.

**Tech Stack:** Python 3.14, httpx, pytest, Supabase (Postgres vía REST), API de Snov.io, API de GoHighLevel v2 (leadconnectorhq), API de Telegram Bot (long-polling).

**Contexto verificado en la sesión de diseño (no asumido):**
- `replies()` devuelve, entre otros campos: `prospectId`, `prospectEmail`, `prospectFirstName`, `prospectLastName`, `prospectName`, `campaignId`, `campaign`.
- `prospect_by_id(prospectId)` devuelve `{"success": true, "data": {"firstName", "lastName", "name", "country", "locality", "industry", "phones": [...], "social": [{"link","type"}], "currentJob": [{"companyName","position","site","size","industry","country","city","socialLink"}], ...}}`.
- `GET /contacts/` (GHL) devuelve `{"contacts": [...], "meta": {...}}`; cada contacto tiene `customFields: [{"id","value"}]` (sin nombre).
- `GET /contacts/{id}` devuelve `{"contact": {...}, "traceId": ...}`.
- El custom field `STATUS PROSPECTO` en GBS (`id 73CZcGKJJr8hsSun2sV6`) tiene las opciones: `No Contesta, No Interesado, Información Adicional, Coordinando Reunión, Reunión Agendada, Reagendar Reunión, Teléfono / Whatsapp no existen, Deriva Refiere Directo, Deriva Refiere Seguimiento, No Califica`.
- `snov_campaign_map` HOY no tiene ninguna fila con `cliente_slug = 'balia'` (confirmado, 0 filas). Ver Task 17.
- Credenciales ya cargadas en `.env.local`: `GHL_TOKEN_GBS_LOGISTICS`, `GHL_TOKEN_BAMBUTECH`, `GHL_TOKEN_BALIA`, `TELEGRAM_BOT_BAMBUTECH_TOKEN` + `TELEGRAM_BOT_BAMBUTECH_CHAT_IDS`. Faltan `TELEGRAM_BOT_GBS_TOKEN`/`_CHAT_IDS` y `TELEGRAM_BOT_BALIA_TOKEN`/`_CHAT_IDS`.
- Fila `balia` ya existe en `clientes` (Supabase), con `ghl_location_id = eJnh0qIKSxz0C2CHbT2O` (compartida con `conprospeccion`).

---

### Task 1: Migración — tabla `telegram_ghl_cards`

Guarda qué contacto de GHL corresponde a cada tarjeta mandada por Telegram, para poder identificar el contacto cuando la SDR responde (reply) a esa tarjeta.

**Files:**
- Create: `sync/supabase/migrations/014_telegram_ghl_cards.sql`

- [ ] **Step 1: Escribir la migración**

```sql
create table if not exists public.telegram_ghl_cards (
  id bigint generated always as identity primary key,
  cliente_slug text not null references public.clientes(slug) on update cascade,
  chat_id bigint not null,
  telegram_message_id bigint not null,
  ghl_contact_id text not null,
  ghl_location_id text not null,
  prospect_name text,
  prospect_email text,
  created_at timestamptz not null default now(),
  unique (chat_id, telegram_message_id)
);

create index if not exists telegram_ghl_cards_contact_idx
  on public.telegram_ghl_cards(ghl_contact_id);
```

- [ ] **Step 2: Aplicar la migración contra Supabase**

Run (desde la raíz del repo):
```bash
cd sync/scripts
python3 - <<'EOF'
from config import get_settings
from supabase_rest import SupabaseRestClient
import httpx

s = get_settings()
sql = open("../supabase/migrations/014_telegram_ghl_cards.sql", encoding="utf-8").read()
# Ejecutar via Supabase REST no soporta DDL crudo; usar el MCP de Supabase
# (apply_migration) o psql/Supabase Studio con este archivo, segun como se
# aplican las demas migraciones numeradas en este repo.
print("Revisar como se aplican las migraciones 001-013 en este repo y aplicar la misma via")
EOF
```
Expected: seguir el mismo mecanismo ya usado para aplicar `sync/supabase/migrations/013_snov_ghl_contact_enrichment.sql` u otras migraciones numeradas de este repo (Supabase Studio, `supabase db push`, o el MCP de Supabase con `apply_migration`) — no hay un script propio en este repo para aplicar migraciones .sql sueltas.

- [ ] **Step 3: Confirmar que la tabla existe**

Run:
```bash
cd sync/scripts
python3 -c "
from config import get_settings
from supabase_rest import SupabaseRestClient
s = get_settings()
sb = SupabaseRestClient(s.supabase_url, s.supabase_secret_key)
print(sb.select('telegram_ghl_cards', '*', limit='1'))
"
```
Expected: `[]` (tabla vacía pero existe, sin error 404/42P01).

- [ ] **Step 4: Commit**

```bash
git add sync/supabase/migrations/014_telegram_ghl_cards.sql
git commit -m "Agregar tabla telegram_ghl_cards para mapear tarjetas de Telegram a contactos GHL

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: `snov_ghl_matching.py` — normalización y choque de nombre

**Files:**
- Create: `sync/scripts/snov_ghl_matching.py`
- Test: `tests/test_snov_ghl_matching.py`

- [ ] **Step 1: Escribir el test que falla**

```python
"""Tests de sync/scripts/snov_ghl_matching.py (logica pura, sin red)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from snov_ghl_matching import names_match, normalize_name


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
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `pytest tests/test_snov_ghl_matching.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'snov_ghl_matching'`

- [ ] **Step 3: Implementar `normalize_name` y `names_match`**

```python
from __future__ import annotations

import unicodedata
from typing import Any


def normalize_name(name: str | None) -> str:
    if not name:
        return ""
    stripped = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return " ".join(stripped.lower().split())


def names_match(snov_name: str | None, ghl_first_name: str | None, ghl_last_name: str | None) -> bool:
    """True si no hay choque de identidad: no hay suficiente informacion para
    comparar, o los nombres comparten al menos un token (nombre o apellido)."""
    ghl_name = " ".join(part for part in [ghl_first_name, ghl_last_name] if part)
    ghl_norm = normalize_name(ghl_name)
    snov_norm = normalize_name(snov_name)
    if not ghl_norm or not snov_norm:
        return True
    return bool(set(snov_norm.split()) & set(ghl_norm.split()))
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `pytest tests/test_snov_ghl_matching.py -v`
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add sync/scripts/snov_ghl_matching.py tests/test_snov_ghl_matching.py
git commit -m "Agregar chequeo de choque de identidad (nombre Snov vs GHL)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: `snov_ghl_matching.py` — enriquecimiento desde `prospect_by_id`

**Files:**
- Modify: `sync/scripts/snov_ghl_matching.py`
- Test: `tests/test_snov_ghl_matching.py`

- [ ] **Step 1: Agregar el test (con la forma real verificada de `prospect_by_id`)**

```python
from snov_ghl_matching import extract_snov_enrichment

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
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `pytest tests/test_snov_ghl_matching.py -v -k extract_snov_enrichment`
Expected: FAIL con `ImportError: cannot import name 'extract_snov_enrichment'`

- [ ] **Step 3: Implementar `extract_snov_enrichment`**

Agregar al final de `sync/scripts/snov_ghl_matching.py`:

```python
def extract_snov_enrichment(prospect_data: dict[str, Any]) -> dict[str, Any]:
    """prospect_data es el dict 'data' de SnovClient.prospect_by_id()."""
    current_job = (prospect_data.get("currentJob") or [{}])[0]

    linkedin_personal = None
    for entry in prospect_data.get("social") or []:
        if entry.get("type") in ("linkedinProfile", "linkedIn") and entry.get("link"):
            linkedin_personal = entry["link"]
            break

    phones = prospect_data.get("phones") or []
    phone = None
    if phones:
        first_phone = phones[0]
        phone = first_phone if isinstance(first_phone, str) else (first_phone or {}).get("number")

    return {
        "first_name": prospect_data.get("firstName"),
        "last_name": prospect_data.get("lastName"),
        "name": prospect_data.get("name"),
        "country": current_job.get("country") or prospect_data.get("country"),
        "city": current_job.get("city") or prospect_data.get("locality"),
        "company_name": current_job.get("companyName"),
        "cargo": current_job.get("position"),
        "industria": current_job.get("industry") or prospect_data.get("industry"),
        "website": current_job.get("site"),
        "tamano_empresa": current_job.get("size"),
        "linkedin_empresa": current_job.get("socialLink"),
        "linkedin_personal": linkedin_personal,
        "phone": phone,
    }
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `pytest tests/test_snov_ghl_matching.py -v`
Expected: 9 tests PASS (5 de Task 2 + 4 nuevos)

- [ ] **Step 5: Commit**

```bash
git add sync/scripts/snov_ghl_matching.py tests/test_snov_ghl_matching.py
git commit -m "Agregar extraccion de datos de enriquecimiento desde prospect_by_id

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: `snov_ghl_matching.py` — resolver IDs de custom fields por nombre

**Files:**
- Modify: `sync/scripts/snov_ghl_matching.py`
- Test: `tests/test_snov_ghl_matching.py`

- [ ] **Step 1: Agregar el test**

```python
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
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `pytest tests/test_snov_ghl_matching.py -v -k resolve_custom_field_ids`
Expected: FAIL con `ImportError`

- [ ] **Step 3: Implementar**

```python
CUSTOM_FIELD_ALIASES: dict[str, list[str]] = {
    "cargo": ["cargo"],
    "industria": ["industria"],
    "tamano_empresa": ["tamano empresa", "tamano de la empresa"],
    "linkedin_personal": ["linkedin personal"],
    "linkedin_empresa": ["linkedin empresa"],
    "status_prospecto": ["status prospecto"],
}


def resolve_custom_field_ids(raw_fields: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for field in raw_fields:
        normalized = normalize_name(field.get("name"))
        for key, aliases in CUSTOM_FIELD_ALIASES.items():
            if key in result:
                continue
            if normalized in aliases:
                result[key] = field.get("id")
    return result
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `pytest tests/test_snov_ghl_matching.py -v`
Expected: 11 tests PASS

- [ ] **Step 5: Commit**

```bash
git add sync/scripts/snov_ghl_matching.py tests/test_snov_ghl_matching.py
git commit -m "Agregar resolucion de custom field IDs por nombre normalizado

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: `snov_ghl_matching.py` — armar el payload de GHL (crear / actualizar)

**Files:**
- Modify: `sync/scripts/snov_ghl_matching.py`
- Test: `tests/test_snov_ghl_matching.py`

- [ ] **Step 1: Agregar el test**

```python
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
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `pytest tests/test_snov_ghl_matching.py -v -k "build_ghl_contact_payload or build_update_payload"`
Expected: FAIL con `ImportError`

- [ ] **Step 3: Implementar**

```python
CUSTOM_FIELD_KEYS = ("cargo", "industria", "tamano_empresa", "linkedin_personal", "linkedin_empresa")


def build_ghl_contact_payload(
    enrichment: dict[str, Any],
    email: str,
    cliente_slug: str,
    custom_field_ids: dict[str, str],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "email": email,
        "source": f"snov-{cliente_slug}",
        "tags": [cliente_slug],
    }
    if enrichment.get("first_name"):
        payload["firstName"] = enrichment["first_name"]
    if enrichment.get("last_name"):
        payload["lastName"] = enrichment["last_name"]
    if enrichment.get("company_name"):
        payload["companyName"] = enrichment["company_name"]
    if enrichment.get("website"):
        payload["website"] = enrichment["website"]
    if enrichment.get("country"):
        payload["country"] = enrichment["country"]
    if enrichment.get("phone"):
        payload["phone"] = enrichment["phone"]

    custom_fields = [
        {"id": custom_field_ids[key], "value": enrichment[key]}
        for key in CUSTOM_FIELD_KEYS
        if custom_field_ids.get(key) and enrichment.get(key)
    ]
    if custom_fields:
        payload["customFields"] = custom_fields
    return payload


def build_update_payload(
    existing_contact: dict[str, Any],
    enrichment: dict[str, Any],
    custom_field_ids: dict[str, str],
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if not existing_contact.get("companyName") and enrichment.get("company_name"):
        payload["companyName"] = enrichment["company_name"]
    if not existing_contact.get("website") and enrichment.get("website"):
        payload["website"] = enrichment["website"]
    if not existing_contact.get("phone") and enrichment.get("phone"):
        payload["phone"] = enrichment["phone"]

    existing_with_value = {
        cf.get("id") for cf in (existing_contact.get("customFields") or [])
        if cf.get("value") not in (None, "")
    }
    custom_fields = [
        {"id": custom_field_ids[key], "value": enrichment[key]}
        for key in CUSTOM_FIELD_KEYS
        if custom_field_ids.get(key) and enrichment.get(key)
        and custom_field_ids[key] not in existing_with_value
    ]
    if custom_fields:
        payload["customFields"] = custom_fields
    return payload
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `pytest tests/test_snov_ghl_matching.py -v`
Expected: 15 tests PASS

- [ ] **Step 5: Commit**

```bash
git add sync/scripts/snov_ghl_matching.py tests/test_snov_ghl_matching.py
git commit -m "Agregar armado de payload GHL para crear/actualizar contacto

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: `snov_ghl_matching.py` — decidir la acción (create/update/skip)

**Files:**
- Modify: `sync/scripts/snov_ghl_matching.py`
- Test: `tests/test_snov_ghl_matching.py`

- [ ] **Step 1: Agregar el test**

```python
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
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `pytest tests/test_snov_ghl_matching.py -v -k decide_action`
Expected: FAIL con `ImportError`

- [ ] **Step 3: Implementar**

```python
from enum import Enum


class GhlAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    SKIP_MISMATCH = "skip_mismatch"
    SKIP_COMPLETE = "skip_complete"


def decide_action(
    existing_contact: dict[str, Any] | None,
    enrichment: dict[str, Any],
    custom_field_ids: dict[str, str],
) -> GhlAction:
    if existing_contact is None:
        return GhlAction.CREATE

    if not names_match(enrichment.get("name"), existing_contact.get("firstName"), existing_contact.get("lastName")):
        return GhlAction.SKIP_MISMATCH

    update_payload = build_update_payload(existing_contact, enrichment, custom_field_ids)
    return GhlAction.UPDATE if update_payload else GhlAction.SKIP_COMPLETE
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `pytest tests/test_snov_ghl_matching.py -v`
Expected: 19 tests PASS

- [ ] **Step 5: Commit**

```bash
git add sync/scripts/snov_ghl_matching.py tests/test_snov_ghl_matching.py
git commit -m "Agregar decide_action: create/update/skip segun estado real en GHL

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: `telegram_ghl_cards.py` — orden de estatus y botones

**Files:**
- Create: `sync/scripts/telegram_ghl_cards.py`
- Test: `tests/test_telegram_ghl_cards.py`

- [ ] **Step 1: Escribir el test**

```python
"""Tests de sync/scripts/telegram_ghl_cards.py (logica pura, sin red)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from telegram_ghl_cards import build_status_keyboard, order_status_options

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
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `pytest tests/test_telegram_ghl_cards.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'telegram_ghl_cards'`

- [ ] **Step 3: Implementar**

```python
from __future__ import annotations

import unicodedata
from typing import Any

STATUS_PROSPECTO_ORDER = [
    "No Contesta",
    "Informacion Adicional",
    "Coordinando Reunion",
    "Reunion Agendada",
    "Reagendar Reunion",
    "No Interesado",
    "No Califica",
    "Deriva Refiere Directo",
    "Deriva Refiere Seguimiento",
    "Telefono / Whatsapp no existen",
]

CLIENT_ACCENTS = {"bambutech": "🟢", "gbs": "🔵", "balia": "🟠"}


def _strip_accents(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()


def order_status_options(real_options: list[str]) -> list[str]:
    """Ordena las opciones reales de GHL segun STATUS_PROSPECTO_ORDER.
    Cualquier opcion que no matchee ninguna palabra clave queda al final,
    en el orden en que vino de GHL."""

    def sort_key(option: str) -> tuple[int, int]:
        normalized = _strip_accents(option)
        for index, wanted in enumerate(STATUS_PROSPECTO_ORDER):
            if _strip_accents(wanted) == normalized:
                return (index, 0)
        return (len(STATUS_PROSPECTO_ORDER), real_options.index(option))

    return sorted(real_options, key=sort_key)


def build_status_keyboard(ordered_options: list[str], contact_id: str) -> dict[str, Any]:
    rows = [ordered_options[i:i + 2] for i in range(0, len(ordered_options), 2)]
    inline_keyboard: list[list[dict[str, str]]] = []
    idx = 0
    for row in rows:
        keyboard_row = []
        for label in row:
            keyboard_row.append({"text": label, "callback_data": f"status:{contact_id}:{idx}"})
            idx += 1
        inline_keyboard.append(keyboard_row)
    return {"inline_keyboard": inline_keyboard}
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `pytest tests/test_telegram_ghl_cards.py -v`
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add sync/scripts/telegram_ghl_cards.py tests/test_telegram_ghl_cards.py
git commit -m "Agregar orden de embudo y armado de botones de estatus para Telegram

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 8: `telegram_ghl_cards.py` — textos de las tarjetas

**Files:**
- Modify: `sync/scripts/telegram_ghl_cards.py`
- Test: `tests/test_telegram_ghl_cards.py`

- [ ] **Step 1: Agregar el test**

```python
from telegram_ghl_cards import (
    build_already_status_text,
    build_mismatch_alert,
    build_new_contact_card,
    build_status_changed_text,
    build_updated_contact_card,
)

ENRICHMENT = {
    "first_name": "Caterina", "last_name": "Cronoro", "name": "Caterina Cronoro",
    "cargo": "Commercial Manager", "company_name": "TranSapp", "tamano_empresa": "11-50",
    "website": "https://transapp.cl", "country": "Chile", "linkedin_personal": "https://linkedin.com/in/cate",
}


def test_build_new_contact_card_incluye_los_datos_clave():
    text = build_new_contact_card("bambutech", "BAMBUTECH", "BambuTech 21 Julio", ENRICHMENT, "cate@transapp.cl")
    assert "🟢" in text
    assert "Caterina Cronoro" in text
    assert "Commercial Manager" in text
    assert "TranSapp" in text
    assert "cate@transapp.cl" in text
    assert "Respondé este mensaje" in text


def test_build_new_contact_card_sin_nombre_no_rompe():
    text = build_new_contact_card("gbs", "GBS LOGISTICS", "GBS 20 julio", {}, "x@y.cl")
    assert "(sin nombre)" in text


def test_build_updated_contact_card():
    text = build_updated_contact_card("gbs", "GBS LOGISTICS", "Caterina Cronoro", "cate@transapp.cl")
    assert "actualizado" in text.lower()
    assert "Caterina Cronoro" in text


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
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `pytest tests/test_telegram_ghl_cards.py -v -k "card or alert or status_text or changed"`
Expected: FAIL con `ImportError`

- [ ] **Step 3: Implementar**

Agregar al final de `sync/scripts/telegram_ghl_cards.py`:

```python
def build_new_contact_card(
    cliente_slug: str, cliente_nombre: str, campaign_name: str,
    enrichment: dict[str, Any], email: str,
) -> str:
    accent = CLIENT_ACCENTS.get(cliente_slug, "🆕")
    nombre = enrichment.get("name") or "(sin nombre)"
    lines = [
        f"{accent} *Nuevo contacto creado en GHL*",
        "",
        f"*Cliente:* {cliente_nombre}",
        f"*Campaña:* {campaign_name}",
        "",
        f"*Prospecto:* {nombre}",
    ]
    if enrichment.get("cargo"):
        lines.append(f"*Cargo:* {enrichment['cargo']}")
    if enrichment.get("company_name"):
        lines.append(f"*Empresa:* {enrichment['company_name']}")
    if enrichment.get("tamano_empresa"):
        lines.append(f"*Tamaño empresa:* {enrichment['tamano_empresa']}")
    if enrichment.get("website"):
        lines.append(f"*Web:* {enrichment['website']}")
    if enrichment.get("country"):
        lines.append(f"*País:* {enrichment['country']}")
    lines.append(f"*Correo:* {email}")
    if enrichment.get("linkedin_personal"):
        lines.append(f"*LinkedIn:* {enrichment['linkedin_personal']}")
    lines += [
        "",
        "_Respondió la campaña — no existía en GHL, se creó con estos datos._",
        "",
        "Respondé este mensaje para mover el estatus o crear una tarea.",
    ]
    return "\n".join(lines)


def build_updated_contact_card(cliente_slug: str, cliente_nombre: str, nombre: str, email: str) -> str:
    accent = CLIENT_ACCENTS.get(cliente_slug, "🔄")
    return (
        f"{accent} *Contacto actualizado en GHL*\n\n"
        f"*Cliente:* {cliente_nombre}\n"
        f"*Prospecto:* {nombre} ({email})\n\n"
        "_Respondió de nuevo la campaña — se completaron datos que faltaban._\n\n"
        "Respondé este mensaje para mover el estatus o crear una tarea."
    )


def build_mismatch_alert(cliente_nombre: str, email: str, ghl_name: str, snov_name: str) -> str:
    return (
        f"⚠️ *Revisar a mano* — {cliente_nombre}\n\n"
        f"El correo `{email}` ya existe en GHL a nombre de *{ghl_name}*, "
        f"pero en Snov respondió *{snov_name}*.\n\n"
        "No se modificó el contacto ni el estatus — puede ser una casilla "
        "compartida o datos cruzados."
    )


def build_already_status_text(nombre: str, status: str) -> str:
    return f"ℹ️ *{nombre}* ya está en *{status}* en GHL — no hay cambios."


def build_status_changed_text(nombre: str, status: str) -> str:
    return f"✅ *{nombre}* ahora está en *{status}* en GHL."
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `pytest tests/test_telegram_ghl_cards.py -v`
Expected: 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add sync/scripts/telegram_ghl_cards.py tests/test_telegram_ghl_cards.py
git commit -m "Agregar textos de tarjetas de Telegram (nuevo/actualizado/choque/estatus)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 9: `telegram_ghl_cards.py` — parsear el comando de tarea

**Files:**
- Modify: `sync/scripts/telegram_ghl_cards.py`
- Test: `tests/test_telegram_ghl_cards.py`

- [ ] **Step 1: Agregar el test**

```python
from telegram_ghl_cards import parse_task_command


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
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `pytest tests/test_telegram_ghl_cards.py -v -k parse_task_command`
Expected: FAIL con `ImportError`

- [ ] **Step 3: Implementar**

```python
def parse_task_command(text: str) -> str | None:
    """Devuelve el texto de la tarea si el mensaje empieza con 'tarea' (con
    o sin ':'), sino None."""
    stripped = text.strip()
    lowered = stripped.lower()
    if lowered.startswith("tarea:"):
        rest = stripped[len("tarea:"):].strip()
    elif lowered.startswith("tarea "):
        rest = stripped[len("tarea "):].strip()
    else:
        return None
    return rest or None
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `pytest tests/test_telegram_ghl_cards.py -v`
Expected: 15 tests PASS

- [ ] **Step 5: Commit**

```bash
git add sync/scripts/telegram_ghl_cards.py tests/test_telegram_ghl_cards.py
git commit -m "Agregar parseo del comando 'tarea:' desde Telegram

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 10: `telegram_client.py` — cliente delgado de la API de Telegram

**Files:**
- Create: `sync/scripts/telegram_client.py`
- Test: `tests/test_telegram_client.py`

- [ ] **Step 1: Escribir el test (mockeando `httpx.Client`, sin red real)**

```python
"""Tests de sync/scripts/telegram_client.py con httpx mockeado (sin red real)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync" / "scripts"))

from telegram_client import TelegramClient


def _mock_response(json_data):
    response = MagicMock()
    response.json.return_value = json_data
    response.raise_for_status.return_value = None
    return response


def test_send_message_llama_al_endpoint_correcto():
    client = TelegramClient("FAKE_TOKEN")
    client.client.post = MagicMock(return_value=_mock_response({"ok": True, "result": {"message_id": 42}}))

    result = client.send_message("123", "hola")

    client.client.post.assert_called_once()
    args, kwargs = client.client.post.call_args
    assert args[0] == "https://api.telegram.org/botFAKE_TOKEN/sendMessage"
    assert kwargs["json"]["chat_id"] == "123"
    assert kwargs["json"]["text"] == "hola"
    assert result["message_id"] == 42


def test_send_message_incluye_reply_markup_si_se_pasa():
    client = TelegramClient("FAKE_TOKEN")
    client.client.post = MagicMock(return_value=_mock_response({"ok": True, "result": {"message_id": 1}}))

    keyboard = {"inline_keyboard": [[{"text": "A", "callback_data": "a"}]]}
    client.send_message("123", "hola", reply_markup=keyboard)

    _, kwargs = client.client.post.call_args
    assert kwargs["json"]["reply_markup"] == keyboard


def test_get_updates_pasa_el_offset():
    client = TelegramClient("FAKE_TOKEN")
    client.client.get = MagicMock(return_value=_mock_response({"ok": True, "result": [{"update_id": 5}]}))

    result = client.get_updates(offset=5, timeout=1)

    args, kwargs = client.client.get.call_args
    assert kwargs["params"]["offset"] == 5
    assert result == [{"update_id": 5}]
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `pytest tests/test_telegram_client.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'telegram_client'`

- [ ] **Step 3: Implementar**

```python
from __future__ import annotations

from typing import Any

import httpx


class TelegramClient:
    def __init__(self, token: str):
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.client = httpx.Client(timeout=30)

    def send_message(self, chat_id: int | str, text: str, reply_markup: dict[str, Any] | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        if reply_markup:
            body["reply_markup"] = reply_markup
        response = self.client.post(f"{self.base_url}/sendMessage", json=body)
        response.raise_for_status()
        return response.json()["result"]

    def answer_callback_query(self, callback_query_id: str, text: str = "") -> None:
        response = self.client.post(
            f"{self.base_url}/answerCallbackQuery",
            json={"callback_query_id": callback_query_id, "text": text},
        )
        response.raise_for_status()

    def get_updates(self, offset: int | None = None, timeout: int = 30) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        response = self.client.get(f"{self.base_url}/getUpdates", params=params, timeout=timeout + 10)
        response.raise_for_status()
        return response.json().get("result", [])
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `pytest tests/test_telegram_client.py -v`
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add sync/scripts/telegram_client.py tests/test_telegram_client.py
git commit -m "Agregar cliente delgado de la API de Telegram (send/get_updates/callback)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 11: `ghl_client.py` — búsqueda de contacto y resolución de custom fields

**Files:**
- Modify: `sync/scripts/ghl_client.py`
- Test: `tests/test_ghl_client_writes.py`

- [ ] **Step 1: Escribir el test (mockeando `httpx.Client`)**

```python
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
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `pytest tests/test_ghl_client_writes.py -v`
Expected: FAIL — `AttributeError: 'GHLClient' object has no attribute 'find_contact_by_email'`

- [ ] **Step 3: Implementar**

Modificar `sync/scripts/ghl_client.py`. En `__init__`, agregar el cache:

```python
    def __init__(self, token: str, version: str = "2021-07-28"):
        self.client = httpx.Client(
            base_url="https://services.leadconnectorhq.com",
            headers={
                "Authorization": f"Bearer {token}",
                "Version": version,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=60,
        )
        self._custom_fields_cache: dict[str, list[dict[str, Any]]] = {}
```

Agregar al final de la clase `GHLClient`:

```python
    def find_contact_by_email(self, location_id: str, email: str) -> dict[str, Any] | None:
        response = self.client.get("/contacts/", params={"locationId": location_id, "query": email, "limit": 5})
        response.raise_for_status()
        contacts = response.json().get("contacts") or []
        email_norm = email.strip().lower()
        for contact in contacts:
            if (contact.get("email") or "").strip().lower() == email_norm:
                return contact
        return None

    def _raw_custom_fields(self, location_id: str) -> list[dict[str, Any]]:
        if location_id not in self._custom_fields_cache:
            payload = self.list_custom_fields(location_id)
            fields = payload.get("customFields", payload) if isinstance(payload, dict) else payload
            self._custom_fields_cache[location_id] = fields
        return self._custom_fields_cache[location_id]

    def custom_field_id_map(self, location_id: str) -> dict[str, str]:
        from snov_ghl_matching import resolve_custom_field_ids
        return resolve_custom_field_ids(self._raw_custom_fields(location_id))

    def custom_field_options(self, location_id: str, field_id: str) -> list[str]:
        for field in self._raw_custom_fields(location_id):
            if field.get("id") == field_id:
                return field.get("picklistOptions") or []
        return []
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `pytest tests/test_ghl_client_writes.py -v`
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add sync/scripts/ghl_client.py tests/test_ghl_client_writes.py
git commit -m "Agregar busqueda de contacto por email y resolucion de custom fields a GHLClient

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 12: `ghl_client.py` — crear/actualizar contacto, mover estatus, crear tarea

**Files:**
- Modify: `sync/scripts/ghl_client.py`
- Test: `tests/test_ghl_client_writes.py`

- [ ] **Step 1: Agregar el test**

```python
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
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `pytest tests/test_ghl_client_writes.py -v -k "create_contact or update_contact or update_custom_field or create_task"`
Expected: FAIL — métodos no existen

- [ ] **Step 3: Implementar**

Agregar al final de la clase `GHLClient` en `sync/scripts/ghl_client.py`:

```python
    def create_contact(self, location_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = {"locationId": location_id, **payload}
        response = self.client.post("/contacts/", json=body)
        response.raise_for_status()
        return response.json()

    def update_contact(self, contact_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.client.put(f"/contacts/{contact_id}", json=payload)
        response.raise_for_status()
        return response.json()

    def update_custom_field(self, contact_id: str, field_id: str, value: Any) -> dict[str, Any]:
        return self.update_contact(contact_id, {"customFields": [{"id": field_id, "value": value}]})

    def create_task(self, contact_id: str, title: str, due_date_iso: str, body: str = "") -> dict[str, Any]:
        payload = {"title": title, "body": body, "dueDate": due_date_iso, "completed": False}
        response = self.client.post(f"/contacts/{contact_id}/tasks", json=payload)
        response.raise_for_status()
        return response.json()
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `pytest tests/test_ghl_client_writes.py -v`
Expected: 8 tests PASS

- [ ] **Step 5: Verificar contra la API real, UNA vez, con un contacto de prueba**

Esto no se puede cubrir con mocks porque `create_task` nunca se probó contra la
API real de GHL en esta sesión (todo lo demás sí). Antes de dar por buena la
Fase 1, correr manualmente:

```bash
cd sync/scripts
python3 - <<'EOF'
from config import get_optional_env
from ghl_client import GHLClient

token = get_optional_env("GHL_TOKEN_GBS_LOGISTICS")
client = GHLClient(token)
# Reemplazar por un contactId real de prueba en la location de GBS.
result = client.create_task(
    "CONTACT_ID_DE_PRUEBA",
    title="[TEST] borrar esta tarea",
    due_date_iso="2026-09-25T13:00:00+00:00",
    body="Tarea de prueba del plan de implementacion, se puede borrar.",
)
print(result)
EOF
```
Expected: 200 y un objeto de tarea con `id`. Si la forma real de la respuesta o
el endpoint difieren, ajustar `create_task` y sus tests antes de seguir. Borrar
la tarea de prueba desde la UI de GHL después.

- [ ] **Step 6: Commit**

```bash
git add sync/scripts/ghl_client.py tests/test_ghl_client_writes.py
git commit -m "Agregar create/update de contacto, mover custom field y crear tarea a GHLClient

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 13: `sync_snov_replies_to_ghl.py` — job periódico (Fase 1)

**Files:**
- Create: `sync/scripts/sync_snov_replies_to_ghl.py`

- [ ] **Step 1: Implementar el script**

```python
from __future__ import annotations

import argparse
import logging
from typing import Any

from config import get_optional_env, get_settings
from ghl_client import GHLClient
from snov_client import SnovClient
from snov_ghl_matching import (
    GhlAction,
    build_ghl_contact_payload,
    build_update_payload,
    decide_action,
    extract_snov_enrichment,
)
from supabase_rest import SupabaseRestClient
from telegram_client import TelegramClient
from telegram_ghl_cards import build_mismatch_alert, build_new_contact_card, build_updated_contact_card


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)


def token_for_client(slug: str) -> str:
    env_key = {"gbs": "GHL_TOKEN_GBS_LOGISTICS"}.get(slug, f"GHL_TOKEN_{slug.upper()}")
    token = get_optional_env(env_key)
    if not token:
        raise RuntimeError(f"Falta {env_key} en .env/.env.txt")
    return token


def telegram_for_client(slug: str) -> tuple[TelegramClient, list[str]] | None:
    token = get_optional_env(f"TELEGRAM_BOT_{slug.upper()}_TOKEN")
    chat_ids_raw = get_optional_env(f"TELEGRAM_BOT_{slug.upper()}_CHAT_IDS")
    if not token or not chat_ids_raw:
        return None
    chat_ids = [c.strip() for c in chat_ids_raw.split(",") if c.strip()]
    return (TelegramClient(token), chat_ids) if chat_ids else None


def active_clients(supabase: SupabaseRestClient) -> list[dict[str, Any]]:
    rows = supabase.select("clientes", "nombre,slug,ghl_location_id", order="nombre.asc")
    return [row for row in rows if row.get("ghl_location_id")]


def campaigns_by_client(supabase: SupabaseRestClient) -> dict[str, list[str]]:
    rows = supabase.select_all("snov_campaign_map", "snov_campaign_id,cliente_slug")
    result: dict[str, list[str]] = {}
    for row in rows:
        if row.get("cliente_slug") and row.get("snov_campaign_id"):
            result.setdefault(row["cliente_slug"], []).append(row["snov_campaign_id"])
    return result


def notify(
    telegram: tuple[TelegramClient, list[str]] | None,
    supabase: SupabaseRestClient,
    text: str,
    *,
    cliente_slug: str,
    ghl_contact_id: str | None,
    ghl_location_id: str,
    prospect_name: str | None,
    prospect_email: str | None,
    dry_run: bool,
) -> None:
    if not telegram or dry_run:
        return
    client_bot, chat_ids = telegram
    for chat_id in chat_ids:
        sent = client_bot.send_message(chat_id, text)
        if ghl_contact_id:
            supabase.insert("telegram_ghl_cards", {
                "cliente_slug": cliente_slug,
                "chat_id": int(chat_id),
                "telegram_message_id": sent["message_id"],
                "ghl_contact_id": ghl_contact_id,
                "ghl_location_id": ghl_location_id,
                "prospect_name": prospect_name,
                "prospect_email": prospect_email,
            })


def process_client(
    client: dict[str, Any],
    campaign_ids: list[str],
    snov: SnovClient,
    supabase: SupabaseRestClient,
    stats: dict[str, int],
    dry_run: bool,
) -> None:
    slug = client["slug"]
    location_id = client["ghl_location_id"]
    ghl = GHLClient(token_for_client(slug))
    custom_field_ids = ghl.custom_field_id_map(location_id)
    telegram = telegram_for_client(slug)

    for campaign_id in campaign_ids:
        for reply in snov.replies(campaign_id):
            email = reply.get("prospectEmail")
            prospect_id = reply.get("prospectId")
            if not email or not prospect_id:
                continue

            detail = snov.prospect_by_id(prospect_id)
            enrichment = extract_snov_enrichment(detail.get("data") or {})
            if not enrichment.get("name"):
                enrichment["name"] = reply.get("prospectName")

            existing = ghl.find_contact_by_email(location_id, email)
            action = decide_action(existing, enrichment, custom_field_ids)
            nombre = enrichment.get("name") or email
            campaign_name = reply.get("campaign") or campaign_id

            if action == GhlAction.CREATE:
                payload = build_ghl_contact_payload(enrichment, email, slug, custom_field_ids)
                contact_id = None
                if not dry_run:
                    created = ghl.create_contact(location_id, payload)
                    contact_id = created["contact"]["id"]
                stats["created"] += 1
                notify(
                    telegram, supabase, build_new_contact_card(slug, client["nombre"], campaign_name, enrichment, email),
                    cliente_slug=slug, ghl_contact_id=contact_id, ghl_location_id=location_id,
                    prospect_name=nombre, prospect_email=email, dry_run=dry_run,
                )

            elif action == GhlAction.UPDATE:
                payload = build_update_payload(existing, enrichment, custom_field_ids)
                if payload and not dry_run:
                    ghl.update_contact(existing["id"], payload)
                stats["updated"] += 1
                notify(
                    telegram, supabase, build_updated_contact_card(slug, client["nombre"], nombre, email),
                    cliente_slug=slug, ghl_contact_id=existing["id"], ghl_location_id=location_id,
                    prospect_name=nombre, prospect_email=email, dry_run=dry_run,
                )

            elif action == GhlAction.SKIP_MISMATCH:
                stats["mismatch"] += 1
                ghl_name = f"{existing.get('firstName') or ''} {existing.get('lastName') or ''}".strip() or "(sin nombre)"
                notify(
                    telegram, supabase, build_mismatch_alert(client["nombre"], email, ghl_name, nombre),
                    cliente_slug=slug, ghl_contact_id=None, ghl_location_id=location_id,
                    prospect_name=nombre, prospect_email=email, dry_run=dry_run,
                )
            else:
                stats["skipped"] += 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Detecta respuestas de Snov y crea/actualiza el contacto en GHL.")
    parser.add_argument("--client", action="append", help="Limitar a estos cliente_slug")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    setup_logging()

    snov_client_id = get_optional_env("SNOV_CLIENT_ID")
    snov_client_secret = get_optional_env("SNOV_CLIENT_SECRET")
    if not snov_client_id or not snov_client_secret:
        raise RuntimeError("Faltan SNOV_CLIENT_ID y/o SNOV_CLIENT_SECRET en .env/.env.txt")
    snov = SnovClient(snov_client_id, snov_client_secret)

    settings = get_settings()
    supabase = SupabaseRestClient(settings.supabase_url, settings.supabase_secret_key)

    clients = active_clients(supabase)
    if args.client:
        wanted = set(args.client)
        clients = [c for c in clients if c["slug"] in wanted]
    by_client = campaigns_by_client(supabase)

    stats: dict[str, int] = {"created": 0, "updated": 0, "mismatch": 0, "skipped": 0}
    for client in clients:
        campaign_ids = by_client.get(client["slug"], [])
        if not campaign_ids:
            logging.info("%s: sin campanas mapeadas en snov_campaign_map, se omite", client["slug"])
            continue
        process_client(client, campaign_ids, snov, supabase, stats, args.dry_run)

    logging.info("Resumen: %s", stats)
    if not args.dry_run:
        supabase.insert("sync_runs", {"source": "snov_replies_ghl", "entity": "contacts", "status": "success", "stats": stats, "errors": []})


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Correr en dry-run contra datos reales de GBS**

Run:
```bash
cd sync/scripts
python3 sync_snov_replies_to_ghl.py --client gbs --dry-run
```
Expected: log `Resumen: {'created': N, 'updated': M, 'mismatch': K, 'skipped': J}`
sin errores. Revisar que `N+M+K+J` sea razonable comparado con la cantidad de
respuestas reales que tiene GBS en Snov ahora mismo.

- [ ] **Step 3: Correr una vez sin `--dry-run` para un solo cliente y confirmar en GHL**

Run: `python3 sync_snov_replies_to_ghl.py --client gbs`
Expected: sin errores; entrar a GHL (location GBS) y confirmar que al menos un
contacto nuevo aparece con el tag `gbs`, `source = snov-gbs` y los custom
fields esperados. Si hay bot de Telegram de GBS configurado, confirmar que
llegó la tarjeta.

- [ ] **Step 4: Commit**

```bash
git add sync/scripts/sync_snov_replies_to_ghl.py
git commit -m "Agregar job Fase 1: Snov replies -> contacto en GHL + aviso Telegram

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 14: `telegram_ghl_bot.py` — bot interactivo (mover estatus / crear tarea)

**Files:**
- Create: `sync/scripts/telegram_ghl_bot.py`

- [ ] **Step 1: Implementar el script**

```python
from __future__ import annotations

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any

from config import get_optional_env, get_settings
from ghl_client import GHLClient
from supabase_rest import SupabaseRestClient
from telegram_client import TelegramClient
from telegram_ghl_cards import (
    build_already_status_text,
    build_status_changed_text,
    build_status_keyboard,
    order_status_options,
    parse_task_command,
)

CLIENTS = ["bambutech", "gbs", "balia"]


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)


def token_for_client(slug: str) -> str:
    env_key = {"gbs": "GHL_TOKEN_GBS_LOGISTICS"}.get(slug, f"GHL_TOKEN_{slug.upper()}")
    token = get_optional_env(env_key)
    if not token:
        raise RuntimeError(f"Falta {env_key} en .env/.env.txt")
    return token


def location_for_client(supabase: SupabaseRestClient, slug: str) -> str:
    rows = supabase.select("clientes", "ghl_location_id", slug=f"eq.{slug}")
    if not rows or not rows[0].get("ghl_location_id"):
        raise RuntimeError(f"Cliente {slug} sin ghl_location_id en Supabase")
    return rows[0]["ghl_location_id"]


def find_card(supabase: SupabaseRestClient, chat_id: int, message_id: int) -> dict[str, Any] | None:
    rows = supabase.select(
        "telegram_ghl_cards", "*",
        chat_id=f"eq.{chat_id}", telegram_message_id=f"eq.{message_id}",
    )
    return rows[0] if rows else None


def default_due_date() -> str:
    due = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=13, minute=0, second=0, microsecond=0)
    return due.isoformat()


def handle_task_command(
    task_text: str, chat_id: str, card: dict[str, Any], ghl: GHLClient, telegram: TelegramClient,
) -> None:
    ghl.create_task(card["ghl_contact_id"], title=task_text[:100], due_date_iso=default_due_date(), body=task_text)
    nombre = card.get("prospect_name") or card.get("prospect_email")
    telegram.send_message(chat_id, f"✅ Tarea creada para *{nombre}*: {task_text}")


def handle_status_prompt(
    chat_id: str, card: dict[str, Any], location_id: str, ghl: GHLClient, telegram: TelegramClient,
) -> None:
    custom_field_ids = ghl.custom_field_id_map(location_id)
    field_id = custom_field_ids.get("status_prospecto")
    if not field_id:
        telegram.send_message(chat_id, "⚠️ No encontré el campo STATUS PROSPECTO en esta location.")
        return
    ordered = order_status_options(ghl.custom_field_options(location_id, field_id))
    keyboard = build_status_keyboard(ordered, card["ghl_contact_id"])
    nombre = card.get("prospect_name") or card.get("prospect_email")
    telegram.send_message(chat_id, f"¿A qué estatus movemos a *{nombre}*?", reply_markup=keyboard)


def handle_message(
    message: dict[str, Any], slug: str, telegram: TelegramClient, ghl: GHLClient,
    supabase: SupabaseRestClient, location_id: str,
) -> None:
    if "reply_to_message" not in message:
        return
    chat_id = message["chat"]["id"]
    reply_to_id = message["reply_to_message"]["message_id"]
    card = find_card(supabase, chat_id, reply_to_id)
    if not card:
        return

    text = (message.get("text") or "").strip()
    task_text = parse_task_command(text)
    if task_text:
        handle_task_command(task_text, chat_id, card, ghl, telegram)
        return

    handle_status_prompt(chat_id, card, location_id, ghl, telegram)


def handle_callback(callback: dict[str, Any], ghl: GHLClient, telegram: TelegramClient) -> None:
    data = callback.get("data") or ""
    parts = data.split(":", 2)
    if len(parts) != 3 or parts[0] != "status":
        return
    _, contact_id, idx_raw = parts
    chat_id = callback["message"]["chat"]["id"]
    telegram.answer_callback_query(callback["id"])

    contact = ghl.get_contact(contact_id)["contact"]
    location_id = contact["locationId"]
    custom_field_ids = ghl.custom_field_id_map(location_id)
    field_id = custom_field_ids.get("status_prospecto")
    if not field_id:
        return
    ordered = order_status_options(ghl.custom_field_options(location_id, field_id))
    idx = int(idx_raw)
    if idx >= len(ordered):
        return
    new_status = ordered[idx]

    nombre = f"{contact.get('firstName') or ''} {contact.get('lastName') or ''}".strip() or "(contacto)"
    current_value = next(
        (cf.get("value") for cf in contact.get("customFields") or [] if cf.get("id") == field_id), None,
    )
    if current_value == new_status:
        telegram.send_message(chat_id, build_already_status_text(nombre, new_status))
        return

    ghl.update_custom_field(contact_id, field_id, new_status)
    telegram.send_message(chat_id, build_status_changed_text(nombre, new_status))


def run_client_bot(slug: str) -> None:
    settings = get_settings()
    supabase = SupabaseRestClient(settings.supabase_url, settings.supabase_secret_key)
    token = get_optional_env(f"TELEGRAM_BOT_{slug.upper()}_TOKEN")
    if not token:
        logging.warning("%s: sin TELEGRAM_BOT_%s_TOKEN, no arranca", slug, slug.upper())
        return

    telegram = TelegramClient(token)
    ghl = GHLClient(token_for_client(slug))
    location_id = location_for_client(supabase, slug)

    offset = None
    logging.info("%s: bot escuchando", slug)
    while True:
        for update in telegram.get_updates(offset=offset, timeout=30):
            offset = update["update_id"] + 1
            try:
                if "callback_query" in update:
                    handle_callback(update["callback_query"], ghl, telegram)
                elif "message" in update:
                    handle_message(update["message"], slug, telegram, ghl, supabase, location_id)
            except Exception:
                logging.exception("%s: error procesando update %s", slug, update.get("update_id"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Bot interactivo por cliente: mover estatus y crear tareas en GHL.")
    parser.add_argument("--client", choices=CLIENTS, help="Correr un solo cliente")
    args = parser.parse_args()
    setup_logging()

    targets = [args.client] if args.client else CLIENTS
    with ThreadPoolExecutor(max_workers=len(targets)) as pool:
        list(pool.map(run_client_bot, targets))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Correr solo para BambuTech (el único bot con token hoy) y probar en vivo**

Run: `cd sync/scripts && python3 telegram_ghl_bot.py --client bambutech`

Mientras corre, en otra terminal correr una vez el job de Fase 1 para
bambutech (`python3 sync_snov_replies_to_ghl.py --client bambutech`) para que
llegue una tarjeta real al chat de @bambutech_bot. Responder esa tarjeta con
`tarea: probar` y confirmar que llega "✅ Tarea creada...". Responder otra
tarjeta con cualquier texto (sin "tarea") y confirmar que aparecen los botones
de estatus; tocar uno y confirmar el mensaje de confirmación, y que el custom
field `STATUS PROSPECTO` cambió en GHL.

Expected: ambos flujos (tarea y estatus) funcionan de punta a punta contra
BambuTech real. `Ctrl+C` para parar.

- [ ] **Step 3: Commit**

```bash
git add sync/scripts/telegram_ghl_bot.py
git commit -m "Agregar bot interactivo de Telegram: mover estatus y crear tareas en GHL

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 15: Documentar el mapeo de campos en `GHL_CAMPOS_ESTANDAR.md`

**Files:**
- Modify: `docs/GHL_CAMPOS_ESTANDAR.md`

- [ ] **Step 1: Agregar la sección**

Agregar al final de `docs/GHL_CAMPOS_ESTANDAR.md`:

```markdown
## Automatización: respuesta de Snov -> contacto en GHL

`sync/scripts/sync_snov_replies_to_ghl.py` crea/actualiza el contacto cuando
un prospecto responde una campaña de Snov (Balia, GBS, BambuTech). Fuente de
datos: `SnovClient.prospect_by_id(prospectId)` (no `snov_prospects`/
`prospects_in_list`, que casi no trae estos campos en la práctica).

| Dato Snov (`prospect_by_id`) | Campo GHL |
| --- | --- |
| `firstName` / `lastName` | `firstName` / `lastName` (estándar) |
| `currentJob[0].companyName` | `companyName` (estándar) |
| `currentJob[0].site` | `website` (estándar) |
| `country` / `currentJob[0].country` | `country` (estándar) |
| `currentJob[0].position` | Cargo (custom field) |
| `currentJob[0].industry` / `industry` | Industria (custom field) |
| `currentJob[0].size` | Tamaño Empresa (custom field) |
| `social[].link` (linkedinProfile/linkedIn) | Linkedin Personal (custom field) |
| `currentJob[0].socialLink` | Linkedin Empresa (custom field) |

Todo contacto creado/actualizado por este job lleva tag `{cliente_slug}` y
`source = snov-{cliente_slug}` (útil especialmente para Balia, que comparte
`locationId` con la cuenta privada de Conprospección).

El bot interactivo (`sync/scripts/telegram_ghl_bot.py`, uno por cliente) deja
mover el custom field `STATUS PROSPECTO` con botones (respondiendo la tarjeta
del contacto) y crear tareas (`tarea: <texto>`, respondiendo la misma
tarjeta).
```

- [ ] **Step 2: Commit**

```bash
git add docs/GHL_CAMPOS_ESTANDAR.md
git commit -m "Documentar mapeo de campos de la automatizacion Snov -> GHL

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 16: Task Scheduler — programar el job de Fase 1

**Files:** ninguno (configuración del sistema operativo, no del repo)

- [ ] **Step 1: Crear la tarea programada**

En Windows Task Scheduler, crear una tarea nueva:
- Nombre: `Snov replies -> GHL`
- Disparador: repetir cada 1 hora, de 8:00 a 20:00, todos los días.
- Acción: ejecutar
  `python "C:\Users\Admin\OneDrive\Documents\Con Prospección\conprospeccionOS2026\sync\scripts\sync_snov_replies_to_ghl.py"`
  con directorio de inicio
  `C:\Users\Admin\OneDrive\Documents\Con Prospección\conprospeccionOS2026\sync\scripts`
  (mismo patrón que las demás tareas de reportes ya configuradas — revisar una
  tarea existente en el Task Scheduler para copiar el mismo usuario/cuenta y
  las mismas opciones).

- [ ] **Step 2: Verificar una corrida manual desde el Task Scheduler**

Click derecho -> Run. Revisar en "Historial" que terminó con éxito, y que
`sync_runs` en Supabase tiene una fila nueva con `source = snov_replies_ghl`.

- [ ] **Step 3: Dejar `telegram_ghl_bot.py` corriendo de forma persistente**

No es una tarea programada (es un proceso de larga duración). Crear un
`.bat` como el que ya existe para `report_sdr_bot.py`
(`sync/scripts/run_sdr_bot.bat`), copiando su patrón, apuntando a
`telegram_ghl_bot.py`, y dejarlo corriendo (o programarlo para arrancar al
iniciar sesión de Windows, igual que el bot de reportes).

---

### Task 17: Prerrequisito de producción — completar lo que falta de datos/credenciales

Este task no se puede automatizar: necesita respuestas de la usuaria. El resto
del plan (Tasks 1-16) no depende de esto y se puede implementar y testear
igual (BambuTech ya tiene todo lo necesario para probar de punta a punta).

- [ ] **Step 1: Confirmar las campañas de Snov de Balia**

`snov_campaign_map` no tiene ninguna fila con `cliente_slug = 'balia'`. Hay
campañas activas candidatas por nombre (a confirmar con la usuaria, no
asumir): `CP CHILE - CONSULTORAS MINERAS` (3085485), `CP MEXICO - Serv Financieros`
(3095494), `CP COLOMBIA - Serv Financieros` (3095491), `CP PERÚ - CONSULTORAS
MINERAS` (3095487), `CP PERÚ - SERV. FINANCIEROS` (3094383). Preguntar:
"¿cuáles de estas (u otras) campañas de Snov son de Balia?".

Una vez confirmado, cargar el mapeo:

```python
from supabase_rest import SupabaseRestClient
from config import get_settings

s = get_settings()
sb = SupabaseRestClient(s.supabase_url, s.supabase_secret_key)
sb.upsert("snov_campaign_map", [
    {"snov_campaign_id": "REEMPLAZAR", "cliente_slug": "balia", "sdr_slug": None},
    # una fila por cada snov_campaign_id confirmado
], "snov_campaign_id")
```

- [ ] **Step 2: Crear los bots de Telegram de GBS y Balia**

Mismos pasos que ya se usaron para BambuTech (@BotFather -> `/newbot`).
Guardar `TELEGRAM_BOT_GBS_TOKEN` / `TELEGRAM_BOT_GBS_CHAT_IDS` y
`TELEGRAM_BOT_BALIA_TOKEN` / `TELEGRAM_BOT_BALIA_CHAT_IDS` en `.env.local`
(mismo formato que `TELEGRAM_BOT_BAMBUTECH_*`, chat_ids separados por coma
para Francisca + Nora).

- [ ] **Step 3: Primera corrida real para los 3 clientes**

```bash
cd sync/scripts
python3 sync_snov_replies_to_ghl.py --dry-run
```
Revisar el resumen por consola. Si se ve razonable, correr sin `--dry-run` y
confirmar en GHL y en los 3 bots de Telegram.

---

## Parte 2: UX v2 (los 3 clientes) + Fase 2 para BambuTech (Responder correo / Agendar)

Agregado tras revisar un demo real con la usuaria (24-sept-2026). Ver
[[tono-textos-usuario-conprospeccion]] en memoria: sin voseo, nunca nombrar
"GHL"/"GoHighLevel" en texto de cara al usuario — decir "CRM".

**Contexto adicional verificado en esta sesión:**
- El array `emails` de `SnovClient.replies()` mezcla la respuesta real del
  prospecto con lo que parecen ser borradores de respuesta ya redactados
  (sin campo que distinga uno de otro), y no dice a qué casilla llegó. Por
  eso "Responder correo" NO puede confiar en los datos de Snov — hay que leer
  las casillas reales de BambuTech por IMAP.
- BambuTech: 2 casillas con credenciales verificadas por login IMAP real
  (`SMTP_BAMBUTECH01_EMAIL/PASSWORD` = michelle@bambutech-services.com,
  `SMTP_BAMBUTECH02_EMAIL/PASSWORD` = michelle.hernandez@bambutech-services.com).
- La identidad "Michelle Hernández N" (usuario GHL `VtRhXhRCd8e7CMSKHbTq`,
  email `michelle.hernandez@bambutech-services.com`) es la misma que
  `report_sdr_bot.py` ya identifica internamente como **"Norma"**
  (`USER_NAMES["VtRhXhRCd8e7CMSKHbTq"] = "Norma"`). Es la persona real detrás
  de la casilla de agenda.
- Calendario a usar para agendar: `uB5sjspYMHvb42qeYVrj` ("Agenda BambuTech
  Services Michelle N", tipo `personal`) en la location de BambuTech
  (`FJ1YCwi4UVvwcBb8qlOb`) — NO el calendario "Ravizza" (round robin
  Norma+Francisca), que es el que aparece primero en `list_calendars` pero es
  para otra cosa. Confirmado por nombre e id de usuario, no asumido a ciegas —
  si al implementar algo no calza, volver a confirmar con la usuaria antes de
  agendar nada real.
- Agendar SIEMPRE en hora México (`America/Mexico_City`), sin importar en qué
  huso esté quien usa el bot.
- GBS y Balia: sin casillas de correo verificadas todavía (las de GBS fallan
  con la contraseña que se dio — hace falta App Password; Balia no tiene
  ninguna casilla identificada aún). Los botones "Responder correo" y
  "Agendar" se muestran en los 3 clientes por consistencia de diseño, pero en
  GBS/Balia contestan "⚠️ Todavía no está configurado el correo de este
  cliente para responder/agendar" en vez de ejecutar la acción.

---

### Task 18: Reescribir los textos de las tarjetas — sin "GHL", sin voseo, con teléfono y con lo que respondió

**Files:**
- Modify: `sync/scripts/telegram_ghl_cards.py`
- Modify: `tests/test_telegram_ghl_cards.py`

- [ ] **Step 1: Actualizar los tests existentes de las tarjetas**

Reemplazar en `tests/test_telegram_ghl_cards.py` las funciones que revisan
texto literal (ajustar a los textos nuevos, agregando los casos de teléfono y
de qué respondió):

```python
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
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `pytest tests/test_telegram_ghl_cards.py -v -k "new_contact_card or updated_contact_card"`
Expected: FAIL (los textos actuales todavía dicen "GHL" y usan voseo)

- [ ] **Step 3: Reescribir las funciones**

Reemplazar en `sync/scripts/telegram_ghl_cards.py`:

```python
def build_new_contact_card(
    cliente_slug: str, cliente_nombre: str, campaign_name: str,
    enrichment: dict[str, Any], email: str, reply_snippet: str | None = None,
) -> str:
    accent = CLIENT_ACCENTS.get(cliente_slug, "🆕")
    nombre = enrichment.get("name") or "(sin nombre)"
    lines = [
        f"{accent} *Nuevo contacto en el CRM*",
        "",
        f"*Cliente:* {cliente_nombre}",
        f"*Campaña:* {campaign_name}",
        "",
        f"*Prospecto:* {nombre}",
    ]
    if enrichment.get("cargo"):
        lines.append(f"*Cargo:* {enrichment['cargo']}")
    if enrichment.get("company_name"):
        lines.append(f"*Empresa:* {enrichment['company_name']}")
    if enrichment.get("tamano_empresa"):
        lines.append(f"*Tamaño empresa:* {enrichment['tamano_empresa']}")
    if enrichment.get("website"):
        lines.append(f"*Web:* {enrichment['website']}")
    if enrichment.get("country"):
        lines.append(f"*País:* {enrichment['country']}")
    lines.append(f"*Correo:* {email}")
    if enrichment.get("phone"):
        lines.append(f"*Teléfono:* {enrichment['phone']}")
    if enrichment.get("linkedin_personal"):
        lines.append(f"*LinkedIn:* {enrichment['linkedin_personal']}")
    if reply_snippet:
        preview = reply_snippet.strip().replace("\r\n", " ").replace("\n", " ")
        if len(preview) > 300:
            preview = preview[:300].rstrip() + "…"
        lines += ["", f"*Respondió:* _{preview}_"]
    lines += ["", "Esta tarjeta se creó porque respondió la campaña y no existía en el CRM."]
    return "\n".join(lines)


def build_updated_contact_card(cliente_slug: str, cliente_nombre: str, nombre: str, email: str) -> str:
    accent = CLIENT_ACCENTS.get(cliente_slug, "🔄")
    return (
        f"{accent} *Contacto actualizado en el CRM*\n\n"
        f"*Cliente:* {cliente_nombre}\n"
        f"*Prospecto:* {nombre} ({email})\n\n"
        "Respondió de nuevo la campaña — se completaron datos que faltaban."
    )
```

También reemplazar, en `build_mismatch_alert`, `build_already_status_text` y
`build_status_changed_text`, cualquier mención de "GHL" por "el CRM" (no hay
voseo en esas tres, no hace falta tocar la conjugación).

- [ ] **Step 4: Correr y verificar que pasa**

Run: `pytest tests/test_telegram_ghl_cards.py -v`
Expected: todos los tests PASS

- [ ] **Step 5: Commit**

```bash
git add sync/scripts/telegram_ghl_cards.py tests/test_telegram_ghl_cards.py
git commit -m "Reescribir tarjetas: decir CRM en vez de GHL, sin voseo, con telefono y respuesta

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 19: Separar estatus / agendar / tarea en 3 mensajes con botón propio

**Files:**
- Modify: `sync/scripts/telegram_ghl_cards.py`
- Modify: `sync/scripts/telegram_ghl_bot.py`
- Modify: `sync/scripts/sync_snov_replies_to_ghl.py`
- Modify: `tests/test_telegram_ghl_cards.py`

Hoy, al responder la tarjeta, el bot manda un solo mensaje con los botones de
estatus. Pasa a mandar 3 mensajes separados (con salto de línea entre uno y
otro, disparados en secuencia): 🔵 estatus, 🟢 agendar, ⚪ tarea.

- [ ] **Step 1: Agregar el test de los 3 builders de pregunta**

```python
from telegram_ghl_cards import build_agendar_prompt, build_status_prompt, build_tarea_prompt


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
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `pytest tests/test_telegram_ghl_cards.py -v -k "prompt"`
Expected: FAIL con `ImportError`

- [ ] **Step 3: Implementar los 3 builders + los botones de agendar/tarea**

Agregar a `sync/scripts/telegram_ghl_cards.py`:

```python
def build_status_prompt(nombre: str) -> str:
    return f"🔵 *¿A qué estatus movemos a {nombre}?*"


def build_agendar_prompt(nombre: str) -> str:
    return f"🟢 *Agendar con {nombre}*"


def build_tarea_prompt(nombre: str) -> str:
    return f"⚪ *Generar tarea para {nombre}*"


def build_agendar_keyboard(contact_id: str) -> dict[str, Any]:
    return {"inline_keyboard": [[{"text": "📅 Ver horarios disponibles", "callback_data": f"agendar:{contact_id}:0"}]]}


def build_tarea_keyboard(contact_id: str) -> dict[str, Any]:
    return {"inline_keyboard": [[
        {"text": "✍️ Generar manual", "callback_data": f"tarea:{contact_id}:manual"},
        {"text": "⚙️ Generar automática", "callback_data": f"tarea:{contact_id}:auto"},
    ]]}
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `pytest tests/test_telegram_ghl_cards.py -v`
Expected: todos los tests PASS

- [ ] **Step 5: Wire en `telegram_ghl_bot.py` — mandar los 3 mensajes en vez de uno**

Reemplazar `handle_message` (la parte que hoy solo llama a
`handle_status_prompt`) por:

```python
def handle_message(
    message: dict[str, Any], slug: str, telegram: TelegramClient, ghl: GHLClient,
    supabase: SupabaseRestClient, location_id: str,
) -> None:
    if "reply_to_message" not in message:
        return
    chat_id = message["chat"]["id"]
    reply_to_id = message["reply_to_message"]["message_id"]
    card = find_card(supabase, chat_id, reply_to_id)
    if not card:
        return

    nombre = card.get("prospect_name") or card.get("prospect_email")
    contact_id = card["ghl_contact_id"]

    send_status_options(chat_id, nombre, contact_id, location_id, ghl, telegram)
    telegram.send_message(chat_id, build_agendar_prompt(nombre), reply_markup=build_agendar_keyboard(contact_id))
    telegram.send_message(chat_id, build_tarea_prompt(nombre), reply_markup=build_tarea_keyboard(contact_id))


def send_status_options(
    chat_id: str, nombre: str, contact_id: str, location_id: str, ghl: GHLClient, telegram: TelegramClient,
) -> None:
    custom_field_ids = ghl.custom_field_id_map(location_id)
    field_id = custom_field_ids.get("status_prospecto")
    if not field_id:
        telegram.send_message(chat_id, "⚠️ No encontré el campo STATUS PROSPECTO en esta location.")
        return
    ordered = order_status_options(ghl.custom_field_options(location_id, field_id))
    keyboard = build_status_keyboard(ordered, contact_id)
    telegram.send_message(chat_id, build_status_prompt(nombre), reply_markup=keyboard)
```

(Elimina la función vieja `handle_status_prompt`; `send_status_options` la
reemplaza.) Actualizar el `import` de `telegram_ghl_cards` para incluir
`build_agendar_prompt, build_agendar_keyboard, build_tarea_prompt,
build_tarea_keyboard, build_status_prompt`.

En `sync_snov_replies_to_ghl.py`, pasar `reply_snippet` a
`build_new_contact_card` usando `reply.get("emails", [{}])[0].get("emailBody")`
(la primera entrada del array — es la que se observó como respuesta real del
prospecto en los datos verificados; es una heurística, no una garantía, por
eso el bot NO la usa para nada operativo, solo como preview en la tarjeta).

- [ ] **Step 6: Probar en vivo contra BambuTech**

Responder una tarjeta real (cualquier texto que no empiece con "tarea").
Expected: llegan 3 mensajes separados, en este orden: 🔵 estatus (con
botones), 🟢 agendar (con botón), ⚪ tarea (con 2 botones).

- [ ] **Step 7: Commit**

```bash
git add sync/scripts/telegram_ghl_cards.py sync/scripts/telegram_ghl_bot.py sync/scripts/sync_snov_replies_to_ghl.py tests/test_telegram_ghl_cards.py
git commit -m "Separar estatus/agendar/tarea en 3 mensajes con botones propios

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 20: Botón de tarea — "Generar manual" (pide fecha/hora + texto) vs "Generar automática" (no hace nada más)

**Files:**
- Modify: `sync/scripts/telegram_ghl_bot.py`

Reemplaza el parseo libre de `tarea: ...` por los 2 botones agregados en la
Task 19. `parse_task_command` (Task 9) queda como fallback por si alguien
igual escribe `tarea: ...` a mano.

- [ ] **Step 1: Manejar el callback `tarea:{contact_id}:manual|auto`**

Agregar a `sync/scripts/telegram_ghl_bot.py`, y sumar el ruteo en
`handle_callback` (agregar un `elif parts[0] == "tarea":` antes del `return`
final):

```python
PENDING_MANUAL_TASK: dict[int, str] = {}  # chat_id -> contact_id, en memoria del proceso


def handle_tarea_callback(parts: list[str], chat_id: int, telegram: TelegramClient) -> None:
    _, contact_id, modo = parts
    telegram.answer_callback_query_ok = True
    if modo == "auto":
        telegram.send_message(chat_id, "⚙️ Listo, no se crea una tarea manual — queda a cargo de la automatización del estatus que le pongas.")
        return
    PENDING_MANUAL_TASK[chat_id] = contact_id
    telegram.send_message(chat_id, "✍️ Escribime la tarea: fecha/hora y descripción en un solo mensaje (ej. \"mañana 11am llamar para coordinar reunión\").")
```

En `handle_callback`, después del bloque que maneja `status`:

```python
    if parts[0] == "tarea":
        handle_tarea_callback(parts, chat_id, telegram)
        return
```

- [ ] **Step 2: Capturar el siguiente mensaje como la tarea manual**

En `handle_message`, antes de todo lo demás (incluso si no es un reply),
agregar al principio:

```python
    chat_id = message["chat"]["id"]
    if chat_id in PENDING_MANUAL_TASK and message.get("text"):
        contact_id = PENDING_MANUAL_TASK.pop(chat_id)
        texto = message["text"].strip()
        ghl.create_task(contact_id, title=texto[:100], due_date_iso=default_due_date(), body=texto)
        telegram.send_message(chat_id, f"✅ Tarea creada: {texto}")
        return
```

(`default_due_date()` ya existe de la Task 14; para la versión manual sigue
siendo un valor por defecto razonable ya que el texto libre no se parsea a
fecha real — anotar como mejora futura si hace falta fecha exacta en el
campo `dueDate`, no en la Fase actual.)

- [ ] **Step 3: Probar en vivo**

Responder una tarjeta -> tocar "⚙️ Generar automática" en el mensaje de
tarea -> confirmar el mensaje de "no se crea nada". Responder otra tarjeta ->
tocar "✍️ Generar manual" -> escribir un texto libre -> confirmar que se creó
la tarea en GHL (revisar en la UI).

- [ ] **Step 4: Commit**

```bash
git add sync/scripts/telegram_ghl_bot.py
git commit -m "Agregar flujo de tarea manual/automatica desde los botones

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 21: `bambutech_mailboxes.py` — encontrar el hilo real por IMAP

**Files:**
- Create: `sync/scripts/bambutech_mailboxes.py`

Busca, en las 2 casillas conocidas de BambuTech, el hilo real de correo con
un prospecto (por asunto y remitente), para no depender de los datos de Snov.

- [ ] **Step 1: Implementar**

```python
from __future__ import annotations

import email
import imaplib
from email.header import decode_header
from typing import Any

from config import get_optional_env

BAMBUTECH_ACCOUNTS = ["BAMBUTECH01", "BAMBUTECH02"]  # michelle@ y michelle.hernandez@


def _decode(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    return "".join(
        part.decode(enc or "utf-8", errors="replace") if isinstance(part, bytes) else part
        for part, enc in parts
    )


def _account_credentials(account_key: str) -> tuple[str, str] | None:
    email_addr = get_optional_env(f"SMTP_{account_key}_EMAIL")
    password = get_optional_env(f"SMTP_{account_key}_PASSWORD")
    if not email_addr or not password:
        return None
    return email_addr, password


def find_reply_thread(prospect_email: str) -> dict[str, Any] | None:
    """Busca en las casillas de BambuTech el ultimo correo REAL recibido de
    prospect_email. Devuelve {account_email, message_id, subject, body,
    references} o None si no se encuentra en ninguna."""
    for account_key in BAMBUTECH_ACCOUNTS:
        creds = _account_credentials(account_key)
        if not creds:
            continue
        account_email, password = creds
        result = _search_mailbox(account_email, password, prospect_email)
        if result:
            return {**result, "account_email": account_email}
    return None


def _search_mailbox(account_email: str, password: str, prospect_email: str) -> dict[str, Any] | None:
    conn = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    try:
        conn.login(account_email, password)
        conn.select("INBOX")
        status, data = conn.search(None, f'(FROM "{prospect_email}")')
        if status != "OK" or not data or not data[0]:
            return None
        message_ids = data[0].split()
        latest_id = message_ids[-1]
        status, msg_data = conn.fetch(latest_id, "(RFC822)")
        if status != "OK" or not msg_data or not msg_data[0]:
            return None
        raw = msg_data[0][1]
        message = email.message_from_bytes(raw)
        body = _extract_plain_text(message)
        return {
            "message_id": message.get("Message-ID"),
            "references": message.get("References") or message.get("Message-ID"),
            "subject": _decode(message.get("Subject")),
            "body": body,
        }
    finally:
        conn.logout()


def _extract_plain_text(message: email.message.Message) -> str:
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                charset = part.get_content_charset() or "utf-8"
                return part.get_payload(decode=True).decode(charset, errors="replace")
        return ""
    charset = message.get_content_charset() or "utf-8"
    payload = message.get_payload(decode=True)
    return payload.decode(charset, errors="replace") if payload else ""
```

- [ ] **Step 2: Probar contra un prospecto real que sí respondió**

```bash
cd sync/scripts
python3 -c "
from bambutech_mailboxes import find_reply_thread
result = find_reply_thread('alexander@orkline.com')
print(result)
"
```
Expected: un dict con `account_email` (michelle@ o michelle.hernandez@),
`subject`, y `body` con el texto real que escribió Guillermo (el mismo que
ya vimos en `replies()`, pero esta vez la fuente es el correo real, no Snov).
Si da `None`, confirmar que el email de prueba efectivamente escribió a una
de las 2 casillas configuradas (puede estar en otra casilla de BambuTech que
todavía no está en `.env.local`).

- [ ] **Step 3: Commit**

```bash
git add sync/scripts/bambutech_mailboxes.py
git commit -m "Agregar busqueda de hilo real por IMAP en las casillas de BambuTech

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 22: `bambutech_mailboxes.py` — mandar la respuesta por SMTP en el mismo hilo

**Files:**
- Modify: `sync/scripts/bambutech_mailboxes.py`

- [ ] **Step 1: Implementar `send_reply`**

Agregar al final de `sync/scripts/bambutech_mailboxes.py`:

```python
import smtplib
from email.mime.text import MIMEText
from email.utils import make_msgid


def send_reply(account_email: str, to_email: str, subject: str, body: str, references: str | None) -> None:
    account_key = next(
        (key for key in BAMBUTECH_ACCOUNTS if (get_optional_env(f"SMTP_{key}_EMAIL") or "").lower() == account_email.lower()),
        None,
    )
    if not account_key:
        raise RuntimeError(f"No hay credenciales SMTP guardadas para {account_email}")
    _, password = _account_credentials(account_key)

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
    msg["From"] = account_email
    msg["To"] = to_email
    msg["Message-ID"] = make_msgid()
    if references:
        msg["In-Reply-To"] = references
        msg["References"] = references

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(account_email, password)
        server.send_message(msg)
```

- [ ] **Step 2: Verificar UNA vez contra una casilla real de prueba (no contra un prospecto real)**

```bash
cd sync/scripts
python3 -c "
from bambutech_mailboxes import send_reply
send_reply(
    'michelle.hernandez@bambutech-services.com',
    'TU_PROPIO_CORREO_DE_PRUEBA@gmail.com',
    'Prueba plan de implementacion',
    'Esto es una prueba, se puede ignorar.',
    None,
)
"
```
Expected: llega el correo a la casilla de prueba, desde
`michelle.hernandez@bambutech-services.com`. Recién después de confirmar esto
se usa `send_reply` contra un prospecto real.

- [ ] **Step 3: Commit**

```bash
git add sync/scripts/bambutech_mailboxes.py
git commit -m "Agregar envio de respuesta por SMTP en el mismo hilo (BambuTech)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 23: Botón "Responder correo" en el bot de BambuTech

**Files:**
- Modify: `sync/scripts/telegram_ghl_cards.py`
- Modify: `sync/scripts/telegram_ghl_bot.py`

- [ ] **Step 1: Agregar el botón "Responder correo" a la tarjeta de contacto nuevo/actualizado**

En `telegram_ghl_cards.py`, agregar una función:

```python
def build_reply_email_keyboard(contact_id: str) -> dict[str, Any]:
    return {"inline_keyboard": [[{"text": "✉️ Responder correo", "callback_data": f"email:{contact_id}"}]]}
```

En `sync_snov_replies_to_ghl.py`, después de mandar la tarjeta de contacto
nuevo/actualizado (Task 13/19), si `slug == "bambutech"`, mandar un mensaje
extra con este teclado; para `gbs`/`balia`, omitirlo por ahora (no hay
casillas configuradas — se agrega cuando se resuelvan sus credenciales, no
antes, para no ofrecer un botón que siempre falla).

- [ ] **Step 2: Manejar el callback `email:{contact_id}`**

En `telegram_ghl_bot.py`, agregar el ruteo en `handle_callback`:

```python
    if parts[0] == "email" and len(parts) >= 2:
        handle_email_callback(parts[1], chat_id, ghl, telegram)
        return
```

```python
PENDING_EMAIL_REPLY: dict[int, dict[str, str]] = {}  # chat_id -> {contact_id, account_email, to, subject, references}


def handle_email_callback(contact_id: str, chat_id: int, ghl: GHLClient, telegram: TelegramClient) -> None:
    from bambutech_mailboxes import find_reply_thread

    contact = ghl.get_contact(contact_id)["contact"]
    prospect_email = contact.get("email")
    if not prospect_email:
        telegram.send_message(chat_id, "⚠️ Este contacto no tiene correo cargado.")
        return

    thread = find_reply_thread(prospect_email)
    if not thread:
        telegram.send_message(chat_id, "⚠️ No encontré el correo real de este prospecto en las casillas de BambuTech.")
        return

    PENDING_EMAIL_REPLY[chat_id] = {
        "contact_id": contact_id,
        "account_email": thread["account_email"],
        "to": prospect_email,
        "subject": thread["subject"],
        "references": thread["references"] or "",
    }
    preview = thread["body"].strip().replace("\r\n", " ").replace("\n", " ")[:500]
    telegram.send_message(
        chat_id,
        f"📨 Esto escribió el prospecto (desde `{thread['account_email']}`):\n\n_{preview}_\n\n"
        "Escribime la respuesta que quieras mandar.",
    )
```

- [ ] **Step 3: Capturar el siguiente mensaje como la respuesta a enviar**

En `handle_message`, junto al chequeo de `PENDING_MANUAL_TASK` (Task 20),
agregar:

```python
    if chat_id in PENDING_EMAIL_REPLY and message.get("text"):
        from bambutech_mailboxes import send_reply
        pending = PENDING_EMAIL_REPLY.pop(chat_id)
        send_reply(
            pending["account_email"], pending["to"], pending["subject"],
            message["text"].strip(), pending["references"] or None,
        )
        telegram.send_message(chat_id, f"✅ Correo enviado desde `{pending['account_email']}`.")
        return
```

- [ ] **Step 4: Probar en vivo con un prospecto real de BambuTech que haya respondido**

Tocar "✉️ Responder correo" en una tarjeta real -> confirmar que muestra el
texto real que escribió el prospecto (comparar con lo que se ve directamente
en Gmail) -> escribir una respuesta de prueba corta -> confirmar que llega al
prospecto (o, si se quiere probar sin arriesgar mandarle algo a un prospecto
real, repetir primero el Step 2 de la Task 22 con una casilla propia).

- [ ] **Step 5: Commit**

```bash
git add sync/scripts/telegram_ghl_cards.py sync/scripts/telegram_ghl_bot.py sync/scripts/sync_snov_replies_to_ghl.py
git commit -m "Agregar boton Responder correo (BambuTech, via IMAP/SMTP real)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 24: Botón "Agendar" en el bot de BambuTech

**Files:**
- Modify: `sync/scripts/telegram_ghl_bot.py`

Usa el calendario `uB5sjspYMHvb42qeYVrj` ("Agenda BambuTech Services
Michelle N") en la location de BambuTech, siempre en hora México
(`America/Mexico_City`), y la API de GHL para leer horarios libres y crear la
cita — que al vivir en GHL queda automáticamente reflejada ahí, sin paso
aparte.

**Nota:** el endpoint exacto para traer horarios libres y crear la cita no se
verificó en vivo en esta sesión (a diferencia de casi todo lo demás en este
plan) porque hacerlo hubiera creado una cita de prueba real en el calendario
de trabajo de Norma. Verificar contra la documentación de GHL
(`GET /calendars/{calendarId}/free-slots`, `POST /calendars/events/appointments`
son los nombres esperados en la API v2 — confirmar antes de dar por buena
esta tarea) en el Step 1, y ajustar `ghl_client.py` si el nombre real difiere.

- [ ] **Step 1: Agregar a `ghl_client.py` y confirmar contra la API real**

```python
    def free_slots(self, calendar_id: str, start_ms: int, end_ms: int, timezone: str) -> dict[str, Any]:
        response = self.client.get(
            f"/calendars/{calendar_id}/free-slots",
            params={"startDate": start_ms, "endDate": end_ms, "timezone": timezone},
        )
        response.raise_for_status()
        return response.json()

    def create_appointment(self, calendar_id: str, location_id: str, contact_id: str, start_iso: str) -> dict[str, Any]:
        body = {
            "calendarId": calendar_id,
            "locationId": location_id,
            "contactId": contact_id,
            "startTime": start_iso,
        }
        response = self.client.post("/calendars/events/appointments", json=body)
        response.raise_for_status()
        return response.json()
```

Correr una vez, solo lectura, para confirmar la forma real de `free_slots`:
```bash
cd sync/scripts
python3 -c "
from config import get_optional_env
from ghl_client import GHLClient
import time
token = get_optional_env('GHL_TOKEN_BAMBUTECH')
client = GHLClient(token)
now_ms = int(time.time() * 1000)
week_ms = now_ms + 7 * 24 * 3600 * 1000
print(client.free_slots('uB5sjspYMHvb42qeYVrj', now_ms, week_ms, 'America/Mexico_City'))
"
```
Expected: una lista de horarios libres. Si el endpoint da 404, buscar el
endpoint correcto en la documentación de GHL v2 (`services.leadconnectorhq.com`)
antes de seguir.

- [ ] **Step 2: Botón "Ver horarios disponibles" -> lista de horarios -> confirmar**

En `telegram_ghl_bot.py`, manejar el callback `agendar:{contact_id}:0` (ya
armado en la Task 19) mostrando los primeros 6 horarios libres como botones,
cada uno con `callback_data = f"agendar_slot:{contact_id}:{slot_iso}"`
(cuidando el límite de 64 bytes de `callback_data` — si `slot_iso` es muy
largo, guardar los slots ofrecidos en un dict en memoria por `chat_id` e usar
un índice corto, mismo patrón que `STATUS_PROSPECTO_ORDER`). Al tocar un
horario, llamar `ghl.create_appointment(...)` y confirmar por Telegram.
Para `gbs`/`balia`, el callback `agendar:` contesta directamente
"⚠️ Todavía no está configurado el calendario de este cliente" sin llamar a
la API.

- [ ] **Step 3: Probar en vivo, con una cita de prueba real (avisando a Norma antes)**

Esto sí crea una cita real en el calendario de trabajo de BambuTech — avisar
antes de probarlo y borrar la cita de prueba después desde GHL.

- [ ] **Step 4: Commit**

```bash
git add sync/scripts/ghl_client.py sync/scripts/telegram_ghl_bot.py
git commit -m "Agregar boton Agendar (BambuTech): horarios libres y crear cita en GHL

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```
