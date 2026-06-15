# Fase 2a — Fundación de sync + camino de escritura del cliente unificado — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que la Validación de Reuniones del cliente escriba en la tabla única `seguimiento_reuniones` usando el campo unificado `tipo_respuesta` (reemplazando Interés del lead + Motivo de rechazo), vía un módulo compartido reutilizable por los 3 dashboards.

**Architecture:** Se agrega `tipo_respuesta_{cp,cli,final}` a `seguimiento_reuniones`. Un módulo `shared/seguimiento.py` centraliza la taxonomía, la normalización BANT y el acceso REST (lectura/escritura por nivel). La Validación (`12_GBS`) deja de usar `gbs_seguimiento` y escribe el nivel `_cli` en la tabla única. Los datos viejos se migran una vez.

**Tech Stack:** Python · Streamlit · Supabase REST · pandas · Supabase MCP (migraciones/SQL).

**Nota sobre tests:** sin pytest en el repo. La lógica pura (`shared/seguimiento.py`) se prueba con asserts ejecutables (`python tests/...`); el resto, `ast.parse` + verificación SQL en Supabase.

**Alcance:** Fase 2a NO toca el dashboard interno (Seguimiento `_cp`/`_final`) ni el snapshot semanal — eso es Fase 2b/2c.

---

### Task 1: Migración — columnas `tipo_respuesta_{cp,cli,final}`

**Files:**
- Migración Supabase (MCP `apply_migration`, proyecto `gdlncvbvhbfjonbnmxfl`)

- [ ] **Step 1: Aplicar la migración**

Nombre: `seguimiento_reuniones_add_tipo_respuesta`
```sql
ALTER TABLE public.seguimiento_reuniones
  ADD COLUMN IF NOT EXISTS tipo_respuesta_cp    text,
  ADD COLUMN IF NOT EXISTS tipo_respuesta_cli   text,
  ADD COLUMN IF NOT EXISTS tipo_respuesta_final text;
```

- [ ] **Step 2: Verificar**

Ejecutar (MCP `execute_sql`):
```sql
SELECT column_name FROM information_schema.columns
WHERE table_schema='public' AND table_name='seguimiento_reuniones'
  AND column_name LIKE 'tipo_respuesta%' ORDER BY column_name;
```
Esperado: `tipo_respuesta_cli`, `tipo_respuesta_cp`, `tipo_respuesta_final`.

- [ ] **Step 3: Commit (registro)**
```bash
git commit --allow-empty -m "db: tipo_respuesta_{cp,cli,final} en seguimiento_reuniones"
```

---

### Task 2: Módulo `shared/seguimiento.py` + test

**Files:**
- Create: `shared/seguimiento.py`
- Create: `tests/test_seguimiento_helpers.py`

- [ ] **Step 1: Escribir el test que falla**

Create `tests/test_seguimiento_helpers.py`:
```python
"""Tests de los helpers puros de shared/seguimiento.py (run: python tests/test_seguimiento_helpers.py)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.seguimiento import (
    TIPO_RESPUESTA_OPTS, bant_to_list, bant_to_str, tipo_valido, payload_nivel,
)

def test_bant_roundtrip():
    assert bant_to_list("B,A,N") == ["B", "A", "N"]
    assert bant_to_list(["b", "x", "T"]) == ["B", "T"]
    assert bant_to_str(["B", "A", "Z"]) == "B,A"

def test_tipo_valido():
    assert tipo_valido("Solicita reunión")
    assert tipo_valido("No es la persona")
    assert not tipo_valido("cualquier cosa")
    assert not tipo_valido(None)

def test_opts_tienen_8():
    assert len(TIPO_RESPUESTA_OPTS) == 8
    assert "Solicita más información" in TIPO_RESPUESTA_OPTS
    assert "Sin respuesta" in TIPO_RESPUESTA_OPTS

def test_payload_nivel_cli():
    p = payload_nivel(
        reunion_id=7, cliente_slug="gbs", nivel="cli",
        val_estado="valida", etapa="envio_propuesta",
        bant=["B", "A"], tipo_respuesta="Solicita reunión", status="ok")
    assert p["reunion_id"] == 7
    assert p["cliente_slug"] == "gbs"
    assert p["val_estado_cli"] == "valida"
    assert p["etapa_cli"] == "envio_propuesta"
    assert p["bant_cli"] == "B,A"
    assert p["tipo_respuesta_cli"] == "Solicita reunión"
    assert p["status_cli"] == "ok"
    assert "updated_at" in p and "updated_by_cli" in p

if __name__ == "__main__":
    test_bant_roundtrip(); test_tipo_valido(); test_opts_tienen_8(); test_payload_nivel_cli()
    print("OK seguimiento helpers")
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `python tests/test_seguimiento_helpers.py`
Esperado: FALLA con `ModuleNotFoundError: No module named 'shared.seguimiento'`.

- [ ] **Step 3: Implementar `shared/seguimiento.py`**

```python
"""Acceso unificado a la tabla `seguimiento_reuniones` (3 niveles: cp / cli / final).

Una sola fila por reunión. El cliente escribe el nivel `cli`, Conprospección el `cp`
y el `final` (la validación final la define CP). Los 3 dashboards leen/escriben aquí.
"""
from __future__ import annotations
from datetime import datetime, timezone

import requests

from shared.config import supabase_url, supabase_key

_URL = supabase_url()
_KEY = supabase_key()
_H   = {"apikey": _KEY, "Authorization": f"Bearer {_KEY}"}
_HW  = {**_H, "Content-Type": "application/json"}

# ── Taxonomía única de tipo de respuesta (formato "Solicita..." en positivas) ──
TIPO_RESPUESTA_POS = [
    "Solicita reunión", "Solicita cotización",
    "Solicita reunión + cotización", "Solicita más información",
]
TIPO_RESPUESTA_NEG = [
    "No interesado", "Ya tiene proveedor", "No es la persona", "Sin respuesta",
]
TIPO_RESPUESTA_OPTS = TIPO_RESPUESTA_POS + TIPO_RESPUESTA_NEG

BANT_OPTS  = ["B", "A", "N", "T"]
NIVELES    = ("cp", "cli", "final")


def bant_to_list(v) -> list[str]:
    if not v:
        return []
    items = v if isinstance(v, list) else str(v).split(",")
    return [x.strip().upper() for x in items if x and x.strip().upper() in BANT_OPTS]


def bant_to_str(lst) -> str:
    return ",".join(x for x in (lst or []) if x in BANT_OPTS)


def tipo_valido(t) -> bool:
    return t in TIPO_RESPUESTA_OPTS


def payload_nivel(reunion_id: int, cliente_slug: str, nivel: str, *,
                  val_estado=None, etapa=None, bant=None,
                  tipo_respuesta=None, status=None) -> dict:
    """Arma el payload para upsert de un nivel (cp/cli/final). Solo toca columnas del nivel."""
    assert nivel in NIVELES, f"nivel inválido: {nivel}"
    p = {
        "reunion_id": reunion_id, "cliente_slug": cliente_slug,
        f"val_estado_{nivel}": val_estado,
        f"etapa_{nivel}": etapa,
        f"bant_{nivel}": bant_to_str(bant),
        f"tipo_respuesta_{nivel}": tipo_respuesta if tipo_valido(tipo_respuesta) else None,
        f"status_{nivel}": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        f"updated_by_{nivel}": datetime.now(timezone.utc).isoformat() if nivel in ("cp", "cli") else None,
    }
    return {k: v for k, v in p.items() if v is not None}


def cargar(cliente_slug: str) -> dict:
    """Devuelve {reunion_id: fila} de seguimiento_reuniones para un cliente."""
    r = requests.get(
        f"{_URL}/rest/v1/seguimiento_reuniones?select=*&cliente_slug=eq.{cliente_slug}",
        headers=_H, timeout=15)
    if not r.ok:
        return {}
    return {int(x["reunion_id"]): x for x in r.json() if x.get("reunion_id")}


def guardar_nivel(reunion_id: int, cliente_slug: str, nivel: str, **campos) -> bool:
    """Upsert (merge) del nivel indicado en seguimiento_reuniones."""
    p = payload_nivel(reunion_id, cliente_slug, nivel, **campos)
    r = requests.post(
        f"{_URL}/rest/v1/seguimiento_reuniones",
        json=p,
        headers={**_HW, "Prefer": "resolution=merge-duplicates,return=minimal"},
        timeout=10)
    return r.ok
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `python tests/test_seguimiento_helpers.py`
Esperado: `OK seguimiento helpers`

- [ ] **Step 5: Commit**
```bash
git add shared/seguimiento.py tests/test_seguimiento_helpers.py
git commit -m "feat(shared): módulo seguimiento_reuniones (taxonomía + BANT + acceso REST) + test"
```

---

### Task 3: Migración de datos viejos → `seguimiento_reuniones` (nivel cli)

**Files:**
- Migración Supabase (MCP `apply_migration`)

- [ ] **Step 1: Migrar `gbs_seguimiento` y `clickie_seguimiento` al nivel cli**

Nombre: `migrar_seguimiento_por_cliente_a_unificada`
```sql
-- GBS: vuelca interés/motivo a tipo_respuesta_cli, BANT cliente/sdr a bant_cli/bant_cp.
INSERT INTO public.seguimiento_reuniones
  (reunion_id, cliente_slug, val_estado_cli, etapa_cli, bant_cli, bant_cp,
   tipo_respuesta_cli, status_cli, updated_at, updated_by_cli)
SELECT
  g.reunion_id, 'gbs', g.status_comercial, g.etapa_comercial, g.bant_cliente, g.bant_sdr,
  COALESCE(
    CASE g.interes_lead
      WHEN 'Reunión' THEN 'Solicita reunión'
      WHEN 'Cotización' THEN 'Solicita cotización'
      WHEN 'Reunión + Cotización' THEN 'Solicita reunión + cotización' END,
    CASE g.motivo_rechazo
      WHEN 'Ya tienen proveedor' THEN 'Ya tiene proveedor'
      WHEN 'Sin respuesta' THEN 'Sin respuesta'
      WHEN 'No interesado' THEN 'No interesado' END),
  g.status_comercial, now(), g.updated_at
FROM public.gbs_seguimiento g
ON CONFLICT (reunion_id) DO UPDATE SET
  bant_cli = EXCLUDED.bant_cli, bant_cp = EXCLUDED.bant_cp,
  etapa_cli = EXCLUDED.etapa_cli, status_cli = EXCLUDED.status_cli,
  tipo_respuesta_cli = EXCLUDED.tipo_respuesta_cli, updated_at = now();

-- Clickie: solo tiene status/etapa (sin BANT ni interés/motivo).
INSERT INTO public.seguimiento_reuniones
  (reunion_id, cliente_slug, val_estado_cli, etapa_cli, status_cli, updated_at, updated_by_cli)
SELECT c.reunion_id, 'clickie', c.status_comercial, c.etapa_comercial, c.status_comercial, now(), c.updated_at
FROM public.clickie_seguimiento c
ON CONFLICT (reunion_id) DO UPDATE SET
  etapa_cli = EXCLUDED.etapa_cli, status_cli = EXCLUDED.status_cli, updated_at = now();
```

- [ ] **Step 2: Verificar conteos**

Ejecutar (MCP `execute_sql`):
```sql
SELECT cliente_slug, count(*) FROM public.seguimiento_reuniones GROUP BY cliente_slug;
```
Esperado: filas para `gbs` y/o `clickie` según haya datos previos (puede ser 0 si las tablas estaban vacías — no es error).

- [ ] **Step 3: Commit (registro)**
```bash
git commit --allow-empty -m "db: migrar gbs/clickie_seguimiento a seguimiento_reuniones (nivel cli)"
```

---

### Task 4: Validación (`12_GBS`) — `tipo_respuesta` unificado + escritura a tabla única

**Files:**
- Modify: `dashboard/pages/12_GBS_Validacion_Reuniones.py`

- [ ] **Step 1: Importar el módulo compartido**

Tras `from shared.gbs_brand import (...)` agregar:
```python
from shared.seguimiento import (
    TIPO_RESPUESTA_OPTS, cargar as cargar_seg_unif, guardar_nivel, bant_to_list,
)
```

- [ ] **Step 2: Reemplazar las opciones Interés/Motivo por una sola de tipo de respuesta**

Sustituir el bloque de constantes `INTERES_OPTS` / `MOTIVO_OPTS` (y sus `_LABEL`) por:
```python
# Tipo de respuesta — taxonomía única (shared/seguimiento.py). "— Sin definir —" = sin registrar.
TIPO_RESP_UI = ["— Sin definir —"] + TIPO_RESPUESTA_OPTS
def _tipo_index(v):
    return TIPO_RESP_UI.index(v) if v in TIPO_RESP_UI else 0
```

- [ ] **Step 3: Leer el seguimiento desde la tabla única**

Reemplazar la función `cargar_seguimiento` por:
```python
@st.cache_data(ttl=60)
def cargar_seguimiento():
    return cargar_seg_unif("gbs")  # {reunion_id: fila de seguimiento_reuniones}
```

- [ ] **Step 4: Leer los valores previos del nivel cli en el loop de reuniones**

Donde hoy se leen `interes_prev` / `motivo_prev` / `bant_*_prev`, reemplazar por:
```python
        seg               = seguimiento.get(rid, {})
        status_prev       = seg.get("status_cli") or ""
        etapa_prev        = seg.get("etapa_cli")
        bant_cliente_prev = bant_to_list(seg.get("bant_cli"))
        bant_sdr_prev     = bant_to_list(seg.get("bant_cp"))
        tipo_prev         = seg.get("tipo_respuesta_cli")
```

- [ ] **Step 5: Reemplazar los selectores Interés + Motivo por un único selector Tipo de respuesta**

Sustituir el bloque `ci1, ci2 = st.columns(2)` (interés + motivo) por:
```python
            nuevo_tipo_lbl = st.selectbox(
                "Tipo de respuesta del lead", TIPO_RESP_UI, index=_tipo_index(tipo_prev),
                key=f"ctipo_{rid}_{i}", placeholder="Seleccionar opciones",
                help="Qué respondió el lead. Mismo campo en Indicadores y Seguimiento.")
            nuevo_tipo = None if nuevo_tipo_lbl == "— Sin definir —" else nuevo_tipo_lbl
```

- [ ] **Step 6: Guardar el nivel cli en la tabla única**

Reemplazar el cuerpo del botón Guardar (la llamada a `guardar_reunion(...)`) por:
```python
                if st.button("💾 Guardar", key=f"csave_{rid}_{i}", type="primary"):
                    if nuevo_estado != "pendiente_validacion" and nuevo_estado != estado_db:
                        upd_validacion(rid, nuevo_estado)
                        cat = VAL_A_CAT.get(nuevo_estado)
                        if cat and cat in stages:
                            mover_ghl(opp_id, *stages[cat])
                    ok = guardar_nivel(
                        rid, "gbs", "cli",
                        val_estado=(nuevo_estado if nuevo_estado != "pendiente_validacion" else None),
                        etapa=nueva_etapa, bant=nuevo_bant_cliente,
                        tipo_respuesta=nuevo_tipo, status=nuevo_status)
                    st.toast("✅ Guardado correctamente" if ok else "⚠️ Hubo un problema al guardar")
                    st.cache_data.clear(); st.rerun()
```
(Eliminar la función `guardar_reunion`, `upd_seguimiento`, `_bant_to_str`, `_bant_to_list` locales y los antiguos `interes_*`/`motivo_*` ya no usados. Mantener `upd_validacion`, `mover_ghl`, `cargar_stages`, `VAL_A_CAT`, `BANT_OPTS`, `BANT_LABEL`.)

- [ ] **Step 7: Verificar sintaxis**

Run: `python -c "import ast; ast.parse(open('dashboard/pages/12_GBS_Validacion_Reuniones.py',encoding='utf-8').read()); print('OK')"`
Esperado: `OK`

- [ ] **Step 8: Verificar escritura (smoke SQL)**

Tras guardar una reunión en la app, ejecutar (MCP `execute_sql`):
```sql
SELECT reunion_id, val_estado_cli, tipo_respuesta_cli, bant_cli
FROM public.seguimiento_reuniones WHERE cliente_slug='gbs' ORDER BY updated_at DESC LIMIT 5;
```
Esperado: aparece la fila con el `tipo_respuesta_cli` elegido. (En demo sin reuniones reales, este paso se valida cuando haya filas.)

- [ ] **Step 9: Commit**
```bash
git add dashboard/pages/12_GBS_Validacion_Reuniones.py
git commit -m "feat(validacion): tipo_respuesta unificado + escritura a seguimiento_reuniones (nivel cli)"
```

---

### Task 5: Validación final, push y verificación

- [ ] **Step 1: Sintaxis + tests**
```bash
python -c "import ast; ast.parse(open('shared/seguimiento.py',encoding='utf-8').read()); print('OK shared')"
python -c "import ast; ast.parse(open('dashboard/pages/12_GBS_Validacion_Reuniones.py',encoding='utf-8').read()); print('OK 12')"
python tests/test_seguimiento_helpers.py
python tests/test_dedup_reuniones.py
```
Esperado: todos OK.

- [ ] **Step 2: Push**
```bash
git push origin master
```

- [ ] **Step 3: Smoke visual**

Abrir Validación GBS → el selector dice **"Tipo de respuesta del lead"** (8 opciones + "— Sin definir —"), placeholder en español; al guardar persiste en `seguimiento_reuniones`.

---

## Cobertura del spec (self-review)

- Tabla única con `tipo_respuesta_{cp,cli,final}` → Task 1. ✅
- Acceso compartido (helpers + REST) → Task 2 (+ test). ✅
- Migración de datos viejos → Task 3. ✅
- Validación cliente escribe `_cli` unificado en la tabla única → Task 4. ✅
- `tipo_respuesta` reemplaza Interés + Motivo (formato "Solicita…") → Task 2 + 4. ✅
- Filtros/campos uniformes: este plan unifica el campo en el lado cliente; **Indicadores** y **Seguimiento** adoptan el mismo `tipo_respuesta` en Fase 2b. (Gap consciente, fuera de alcance 2a.)
- CP `_cp` + final `_final` en Seguimiento → **Fase 2b** (fuera de alcance).
- Snapshot semanal de Indicadores → **Fase 2c** (fuera de alcance).
