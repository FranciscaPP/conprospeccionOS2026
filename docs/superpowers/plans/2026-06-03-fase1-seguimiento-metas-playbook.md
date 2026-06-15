# Fase 1 — Seguimiento (dedup + orden + metas) + fix Playbook — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el dashboard interno de Seguimiento deduplique reuniones (deja la de última fecha), las ordene de la más reciente a la más antigua, y muestre en cada tarjeta el avance real contra la meta por cliente (contado SIEMPRE con la validación final); además recolorear el Playbook GBS al morado de marca y hacer legibles los correos sugeridos.

**Architecture:** Se crea la tabla fundación `seguimiento_reuniones` (una fila por reunión, con `val_estado_final` y los campos por nivel para la Fase 2). El % de avance lee `val_estado_final`. La lógica de dedup se extrae a una función pura testeable. Las metas viven en `shared/metas.py`.

**Tech Stack:** Python · Streamlit · Supabase REST · pandas · `shared/gbs_brand.py` (paleta).

**Nota sobre tests:** el repo no tiene pytest. Para la función pura de dedup se escribe un script de asserts ejecutable con `python`. Para el resto, verificación = `ast.parse` (sintaxis) + query SQL a Supabase + smoke visual.

---

### Task 1: Crear tabla fundación `seguimiento_reuniones`

**Files:**
- Migración Supabase (MCP `apply_migration`, proyecto `gdlncvbvhbfjonbnmxfl`)

- [ ] **Step 1: Aplicar la migración**

Nombre: `crear_seguimiento_reuniones_unificada`

```sql
CREATE TABLE IF NOT EXISTS public.seguimiento_reuniones (
  reunion_id      bigint PRIMARY KEY,
  cliente_slug    text,
  -- Nivel Conprospección (CP)
  val_estado_cp   text,
  etapa_cp        text,
  bant_cp         text,
  status_cp       text,
  -- Nivel Cliente
  val_estado_cli  text,
  etapa_cli       text,
  bant_cli        text,
  status_cli      text,
  interes_cli     text,
  motivo_cli      text,
  -- Validación final (la define CP)
  val_estado_final text,
  etapa_final      text,
  bant_final       text,
  status_final     text,
  updated_at       timestamptz DEFAULT now(),
  updated_by_cp    timestamptz,
  updated_by_cli   timestamptz
);
CREATE INDEX IF NOT EXISTS idx_seg_reuniones_cliente ON public.seguimiento_reuniones (cliente_slug);
CREATE INDEX IF NOT EXISTS idx_seg_reuniones_final   ON public.seguimiento_reuniones (val_estado_final);
```

- [ ] **Step 2: Verificar columnas**

Ejecutar (MCP `execute_sql`):
```sql
SELECT column_name FROM information_schema.columns
WHERE table_schema='public' AND table_name='seguimiento_reuniones' ORDER BY ordinal_position;
```
Esperado: aparecen `reunion_id`, `val_estado_final`, `val_estado_cp`, `val_estado_cli`, etc.

- [ ] **Step 3: Commit (no hay archivos; registrar en mensaje)**

```bash
git commit --allow-empty -m "db: crear tabla unificada seguimiento_reuniones (fundación 3 niveles)"
```

---

### Task 2: Crear `shared/metas.py`

**Files:**
- Create: `shared/metas.py`

- [ ] **Step 1: Escribir el módulo de metas**

```python
"""Metas de reuniones válidas por cliente — fuente única (versionada en git).

tipo "contrato" = meta total del contrato.
tipo "mensual"  = meta por mes (se evalúa sobre el mes en curso).
Las claves son el cliente_slug tal como aparece en Supabase / vw_reuniones_semana.
"""

METAS = {
    "just4u":    {"validas": 40,  "tipo": "contrato"},
    "ecosmart":  {"validas": 30,  "tipo": "contrato"},
    "gbs":       {"validas": 45,  "tipo": "contrato"},
    "bambutech": {"validas": 100, "tipo": "contrato"},
    "clickie":   {"validas": 6,   "tipo": "mensual"},
}

# Mapa nombre visible (mayúsculas) -> slug, para dashboards que agrupan por nombre.
NOMBRE_A_SLUG = {
    "JUST4U": "just4u",
    "ECOSMART": "ecosmart",
    "GBS LOGISTICS": "gbs",
    "BAMBUTECH": "bambutech",
    "CLICKIE": "clickie",
    "TIRESIAS": "tiresias",
}


def meta_de(slug: str) -> dict | None:
    """Devuelve {'validas': int, 'tipo': str} o None si el cliente no tiene meta."""
    return METAS.get((slug or "").lower())
```

- [ ] **Step 2: Verificar import**

Run: `python -c "from shared.metas import METAS, meta_de, NOMBRE_A_SLUG; print(meta_de('gbs'), NOMBRE_A_SLUG['GBS LOGISTICS'])"`
Esperado: `{'validas': 45, 'tipo': 'contrato'} gbs`

- [ ] **Step 3: Commit**

```bash
git add shared/metas.py
git commit -m "feat(shared): metas de reuniones válidas por cliente"
```

---

### Task 3: Función pura de dedup + test ejecutable

**Files:**
- Modify: `dashboard/pages/1_Seguimiento_Reuniones.py` (agregar funciones puras cerca de los helpers, ~línea 108)
- Create: `tests/test_dedup_reuniones.py` (script de asserts, sin pytest)

- [ ] **Step 1: Escribir el test que falla**

Create `tests/test_dedup_reuniones.py`:
```python
"""Test de la función pura de dedup (se corre con `python tests/test_dedup_reuniones.py`)."""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dashboard" / "pages"))
# Import por archivo con prefijo numérico:
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "seg", Path(__file__).resolve().parent.parent / "dashboard" / "pages" / "1_Seguimiento_Reuniones.py")

def _load():
    # cargar solo las funciones puras sin ejecutar la app: leemos y exec en un namespace acotado
    src = (Path(__file__).resolve().parent.parent / "dashboard" / "pages" / "1_Seguimiento_Reuniones.py").read_text(encoding="utf-8")
    import re
    # extraer el bloque de funciones puras delimitado por marcadores
    ini = src.index("# <<DEDUP-PURO>>")
    fin = src.index("# <<DEDUP-PURO-FIN>>")
    ns = {"pd": pd}
    exec(src[ini:fin], ns)
    return ns

def test_dedup_mantiene_ultima_fecha():
    ns = _load()
    df = pd.DataFrame([
        {"id": 1, "cliente_slug": "gbs", "opportunity_id": "A", "email": "x@e.cl", "contacto": "Ana", "empresa": "E", "fecha": pd.Timestamp("2026-05-01")},
        {"id": 2, "cliente_slug": "gbs", "opportunity_id": "A", "email": "x@e.cl", "contacto": "Ana", "empresa": "E", "fecha": pd.Timestamp("2026-06-10")},
        {"id": 3, "cliente_slug": "gbs", "opportunity_id": "",  "email": "y@e.cl", "contacto": "Bob", "empresa": "E", "fecha": pd.Timestamp("2026-05-20")},
    ])
    out = ns["deduplicar_reuniones"](df)
    ids = set(out["id"])
    assert ids == {2, 3}, f"esperaba quedarme con 2 y 3, obtuve {ids}"

def test_dedup_separa_por_cliente():
    ns = _load()
    df = pd.DataFrame([
        {"id": 1, "cliente_slug": "gbs",     "opportunity_id": "", "email": "z@e.cl", "contacto": "C", "empresa": "E", "fecha": pd.Timestamp("2026-05-01")},
        {"id": 2, "cliente_slug": "clickie", "opportunity_id": "", "email": "z@e.cl", "contacto": "C", "empresa": "E", "fecha": pd.Timestamp("2026-05-01")},
    ])
    out = ns["deduplicar_reuniones"](df)
    assert set(out["id"]) == {1, 2}, "no debe deduplicar entre clientes distintos"

if __name__ == "__main__":
    test_dedup_mantiene_ultima_fecha()
    test_dedup_separa_por_cliente()
    print("OK dedup")
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `python tests/test_dedup_reuniones.py`
Esperado: FALLA con `ValueError: substring not found` (todavía no existen los marcadores `# <<DEDUP-PURO>>`).

- [ ] **Step 3: Implementar las funciones puras**

En `dashboard/pages/1_Seguimiento_Reuniones.py`, después de la función `formato_dia` (~línea 114), insertar:
```python
# <<DEDUP-PURO>>
def _dedup_key(row):
    opp = str(row.get("opportunity_id") or "").strip()
    if opp:
        return ("opp", opp)
    email = str(row.get("email") or "").strip().lower()
    if email:
        return ("email", email)
    contacto = str(row.get("contacto") or "").strip().lower()
    empresa  = str(row.get("empresa") or "").strip().lower()
    return ("cont", contacto, empresa)


def deduplicar_reuniones(df):
    """Una reunión por prospecto y cliente: conserva la de fecha más reciente.
    Clave: opportunity_id -> email -> contacto+empresa, dentro de cada cliente_slug."""
    if df is None or df.empty:
        return df
    d = df.copy()
    d["_dk"] = d.apply(_dedup_key, axis=1)
    d = d.sort_values("fecha", na_position="first")          # asc: la última fecha queda al final
    d = d.groupby(["cliente_slug", "_dk"], as_index=False, sort=False).tail(1)
    return d.drop(columns=["_dk"])
# <<DEDUP-PURO-FIN>>
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `python tests/test_dedup_reuniones.py`
Esperado: `OK dedup`

- [ ] **Step 5: Commit**

```bash
git add dashboard/pages/1_Seguimiento_Reuniones.py tests/test_dedup_reuniones.py
git commit -m "feat(seguimiento): función pura de dedup por prospecto (deja última fecha) + test"
```

---

### Task 4: Aplicar dedup + orden descendente en Seguimiento

**Files:**
- Modify: `dashboard/pages/1_Seguimiento_Reuniones.py` (`cargar_reuniones`, ~líneas 125-145, y `run`)

- [ ] **Step 1: Deduplicar y ordenar al cargar**

En `cargar_reuniones`, antes del `return df` final (después de las conversiones de fecha y los fillna), agregar:
```python
    df = deduplicar_reuniones(df)
    df = df.sort_values("fecha", ascending=False, na_position="last").reset_index(drop=True)
```

- [ ] **Step 2: Garantizar orden tras filtrar**

En `aplicar_filtros` (`dashboard/pages/1_Seguimiento_Reuniones.py`), antes del `return dff`, agregar:
```python
    dff = dff.sort_values("fecha", ascending=False, na_position="last")
```

- [ ] **Step 3: Verificar sintaxis**

Run: `python -c "import ast; ast.parse(open('dashboard/pages/1_Seguimiento_Reuniones.py',encoding='utf-8').read()); print('OK')"`
Esperado: `OK`

- [ ] **Step 4: Re-correr el test de dedup (no debe romperse)**

Run: `python tests/test_dedup_reuniones.py`
Esperado: `OK dedup`

- [ ] **Step 5: Commit**

```bash
git add dashboard/pages/1_Seguimiento_Reuniones.py
git commit -m "feat(seguimiento): aplicar dedup y orden descendente (última agendada primero)"
```

---

### Task 5: Tarjetas con avance real por meta (validación final)

**Files:**
- Modify: `dashboard/pages/1_Seguimiento_Reuniones.py` (imports, nueva loader, `resumen_clientes_html`)

- [ ] **Step 1: Importar metas y cargar la validación final**

Tras los imports existentes (~línea 13) agregar:
```python
from shared.metas import meta_de, NOMBRE_A_SLUG
```
Después de `cargar_clientes` (~línea 169) agregar:
```python
@st.cache_data(ttl=30)
def cargar_validacion_final() -> dict:
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/seguimiento_reuniones?select=reunion_id,val_estado_final",
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
        timeout=15)
    if not r.ok:
        return {}
    return {int(x["reunion_id"]): (x.get("val_estado_final") or "")
            for x in r.json() if x.get("reunion_id")}
```

- [ ] **Step 2: Reescribir `resumen_clientes_html` para mostrar avance vs meta**

Reemplazar la función `resumen_clientes_html` completa por:
```python
def resumen_clientes_html(dff: pd.DataFrame, final_map: dict) -> str:
    import datetime as _dt
    mes_actual = _dt.date.today().month
    anio_actual = _dt.date.today().year
    cards = ""
    for nombre in [c for c in COLORES_CLIENTE if c in dff["cliente"].str.upper().unique()]:
        sub = dff[dff["cliente"].str.upper() == nombre]
        if sub.empty:
            continue
        c    = COLORES_CLIENTE[nombre]
        slug = NOMBRE_A_SLUG.get(nombre, "")
        meta = meta_de(slug)

        # válidas según VALIDACIÓN FINAL
        def _es_final_valida(rid):
            return str(final_map.get(int(rid), "")).lower() in ("valida", "reunion_valida")

        if meta and meta["tipo"] == "mensual":
            sub_meta = sub[(sub["fecha"].dt.month == mes_actual) & (sub["fecha"].dt.year == anio_actual)]
            validas_final = int(sub_meta["id"].apply(_es_final_valida).sum()) if not sub_meta.empty else 0
            meta_n = meta["validas"]
            sufijo = "/mes"
        elif meta:
            validas_final = int(sub["id"].apply(_es_final_valida).sum())
            meta_n = meta["validas"]
            sufijo = ""
        else:
            validas_final, meta_n, sufijo = 0, 0, ""

        pct = round(validas_final / meta_n * 100) if meta_n else 0
        pct_barra = min(pct, 100)
        meta_txt = f"{validas_final}/{meta_n}{sufijo}" if meta_n else "—"
        cards += f"""
        <div style="background:{c['bg']};color:{c['color']};border:2px solid {c['border']};
                    border-radius:12px;padding:14px 18px;min-width:175px;flex:1">
          <div style="display:flex;justify-content:space-between;margin-bottom:6px">
            <span style="font-size:11px;font-weight:800;letter-spacing:.5px;text-transform:uppercase;opacity:.8">{sub['cliente'].iloc[0]}</span>
            <span style="font-size:13px;font-weight:700;opacity:.75">{pct}%</span>
          </div>
          <div style="font-size:22px;font-weight:700;margin-bottom:2px">{meta_txt}</div>
          <div style="font-size:10px;opacity:.7;margin-bottom:6px">reuniones válidas (validación final)</div>
          <div style="background:rgba(0,0,0,0.08);border-radius:4px;height:5px;margin-bottom:9px">
            <div style="background:{c['border']};width:{pct_barra}%;height:100%;border-radius:4px"></div>
          </div>
          <div style="font-size:11px;display:flex;flex-direction:column;gap:3px">
            <div style="display:flex;justify-content:space-between"><span>✅ Válidas</span><b>{_count(sub, es_valida)}</b></div>
            <div style="display:flex;justify-content:space-between"><span>❌ No válidas</span><b>{_count(sub, es_no_valida)}</b></div>
            <div style="display:flex;justify-content:space-between"><span>🔄 Reagendar</span><b>{_count(sub, es_reagendar)}</b></div>
            <div style="display:flex;justify-content:space-between"><span>⏳ Pendientes</span><b>{_count(sub, es_pendiente)}</b></div>
          </div>
        </div>"""
    return f'<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:22px">{cards}</div>'
```

- [ ] **Step 3: Pasar `final_map` en la llamada dentro de `run`**

En `run`, donde dice `df = cargar_reuniones()` agregar debajo:
```python
    final_map = cargar_validacion_final()
```
Y cambiar `st.markdown(resumen_clientes_html(dff), unsafe_allow_html=True)` por:
```python
    st.markdown(resumen_clientes_html(dff, final_map), unsafe_allow_html=True)
```

- [ ] **Step 4: Verificar sintaxis**

Run: `python -c "import ast; ast.parse(open('dashboard/pages/1_Seguimiento_Reuniones.py',encoding='utf-8').read()); print('OK')"`
Esperado: `OK`

- [ ] **Step 5: Verificar que la tabla responde (avance 0/meta esperado)**

Run (MCP `execute_sql`): `SELECT count(*) FROM public.seguimiento_reuniones;`
Esperado: `0` (aún sin validaciones finales → todas las tarjetas mostrarán `0/meta`, que es lo pedido).

- [ ] **Step 6: Commit**

```bash
git add dashboard/pages/1_Seguimiento_Reuniones.py
git commit -m "feat(seguimiento): tarjetas con avance real por meta usando validación final"
```

---

### Task 6: Recolorear Playbook GBS al morado de marca

**Files:**
- Modify: `dashboard/pages/13_GBS_Playbook_SDR.py` (constantes de color, ~líneas 22-25, y hex hardcodeados ~líneas 374, 421-422)

- [ ] **Step 1: Importar la paleta compartida y reapuntar las constantes**

Reemplazar (líneas ~22-25):
```python
BLUE   = "#1a56db"
...
LIGHT  = "#eff6ff"
BORDER = "#bfdbfe"
```
por:
```python
from shared.gbs_brand import GBS_PURPLE, GBS_DARK, GBS_PURPLE_BG, GBS_BORDER_2
BLUE   = GBS_PURPLE       # morado de marca
LIGHT  = GBS_PURPLE_BG    # #f5f3ff
BORDER = GBS_BORDER_2     # #ddd6fe
```
(Mantener el resto de constantes intactas; ajustar el import al inicio del archivo si hace falta para que `from shared...` quede junto a los otros imports.)

- [ ] **Step 2: Reemplazar hex azules hardcodeados restantes**

- Línea ~374: `color:#bfdbfe` → `color:#ddd6fe`.
- Líneas ~421-422: `background:#1e3a5f;border:1px solid #1e40af; ... color:#bfdbfe` → `background:#4c1d95;border:1px solid #7c3aed; ... color:#ede9fe`.

- [ ] **Step 3: Verificar que no quedan azules viejos**

Run: `python -c "import re,io; s=open('dashboard/pages/13_GBS_Playbook_SDR.py',encoding='utf-8').read(); print([h for h in ['#1a56db','#eff6ff','#bfdbfe','#1e3a5f','#1e40af'] if h in s])"`
Esperado: `[]`

- [ ] **Step 4: Verificar sintaxis**

Run: `python -c "import ast; ast.parse(open('dashboard/pages/13_GBS_Playbook_SDR.py',encoding='utf-8').read()); print('OK')"`
Esperado: `OK`

- [ ] **Step 5: Commit**

```bash
git add dashboard/pages/13_GBS_Playbook_SDR.py
git commit -m "fix(playbook): recolorear al morado de marca GBS"
```

---

### Task 7: Legibilidad de los correos sugeridos en Playbook

**Files:**
- Modify: `dashboard/pages/13_GBS_Playbook_SDR.py` (bloque donde se renderiza el cuerpo del correo "Asunto: ...")

- [ ] **Step 1: Localizar el render del correo**

Run: `python -c "import re; s=open('dashboard/pages/13_GBS_Playbook_SDR.py',encoding='utf-8').read(); [print(i+1, l) for i,l in enumerate(s.splitlines()) if 'Asunto' in l or 'white-space' in l or 'monospace' in l or 'correo' in l.lower()]"`
Esperado: muestra las líneas del bloque del correo (texto largo con `Asunto:`).

- [ ] **Step 2: Mejorar el estilo del cuerpo del correo**

En el `st.markdown`/contenedor que muestra el texto del correo, asegurar estas propiedades en el `style` del `<div>` del cuerpo (agregar/ajustar, no duplicar):
```
font-size:13.5px; line-height:1.7; color:#1e293b; white-space:pre-wrap;
font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; background:#ffffff;
border:1px solid #ddd6fe; border-radius:10px; padding:14px 16px;
```
Si el cuerpo se muestra dentro de fondo morado oscuro, cambiar el color del texto a `#f8fafc` y el fondo a `transparent`. El objetivo: texto oscuro sobre fondo claro (contraste AA), tamaño ≥13px, `pre-wrap` para respetar los saltos de línea del correo.

- [ ] **Step 3: Verificar sintaxis**

Run: `python -c "import ast; ast.parse(open('dashboard/pages/13_GBS_Playbook_SDR.py',encoding='utf-8').read()); print('OK')"`
Esperado: `OK`

- [ ] **Step 4: Commit**

```bash
git add dashboard/pages/13_GBS_Playbook_SDR.py
git commit -m "fix(playbook): legibilidad de los correos sugeridos (tamaño, contraste, pre-wrap)"
```

---

### Task 8: Validación final, push y verificación

**Files:** (ninguno nuevo)

- [ ] **Step 1: Sintaxis de todos los archivos tocados**

Run:
```bash
for f in shared/metas.py dashboard/pages/1_Seguimiento_Reuniones.py dashboard/pages/13_GBS_Playbook_SDR.py; do python -c "import ast,sys; ast.parse(open(sys.argv[1],encoding='utf-8').read()); print('OK',sys.argv[1])" "$f"; done
```
Esperado: `OK` en los 3.

- [ ] **Step 2: Test de dedup**

Run: `python tests/test_dedup_reuniones.py`
Esperado: `OK dedup`

- [ ] **Step 3: Push**

```bash
git push origin master
```
Esperado: push exitoso a `FranciscaPP/conprospeccion-os`.

- [ ] **Step 4: Smoke visual (manual)**

En Streamlit Cloud: abrir Seguimiento → tarjetas muestran `0/meta` (Just4U /40, Ecosmart /30, GBS /45, BambuTech /100, Clickie /6 mes), reuniones ordenadas de la más reciente a la más antigua y sin duplicados del mismo prospecto. Abrir Playbook GBS → morado de marca y correos legibles.

---

## Cobertura del spec (self-review)

- Dedup (opp→email→nombre, última fecha) → Task 3 + 4. ✅
- Orden descendente → Task 4. ✅
- Metas por cliente (40/30/45/100, Clickie 6/mes) → Task 2 + 5. ✅
- % avance SIEMPRE con validación final → Task 1 (`val_estado_final`) + Task 5. ✅
- Fix Playbook colores → Task 6. ✅
- Fix legibilidad correos → Task 7. ✅
- Link canónico del portal → ya resuelto fuera de este plan (guía + fix de header del login). ✅
- Fundación modelo 3 niveles → Task 1 (tabla completa creada; campos `_cp`/`_cli`/`_final` listos para Fase 2). ✅
