# Núcleo de validación de reuniones — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar la validación de reuniones en 3 capas (CP / cliente / final) con propagación automática, flags, historial y permisos, sincronizada entre Seguimiento (interno), Validación (cliente) e Indicadores, sin romper lo existente.

**Architecture:** Motor de reglas puro en `shared/validacion.py` (testeable). La tabla única `seguimiento_reuniones` se extiende con columnas idempotentes + tabla `meeting_status_history`. `shared/seguimiento.py` escribe por nivel aplicando el motor y registrando historial. Las 3 UIs Streamlit consumen los helpers; ninguna duplica lógica de reglas.

**Tech Stack:** Python · Streamlit · Supabase REST + MCP (migraciones) · pandas.

**Spec:** `docs/superpowers/specs/2026-06-04-nucleo-validacion-reuniones-design.md`.

**Tests:** sin pytest → la lógica pura se prueba con asserts ejecutables (`python tests/...`); el resto, `ast.parse` + verificación SQL.

---

### Task 1: Migración — columnas de validación + historial

**Files:** Migración Supabase (MCP `apply_migration`, proyecto `gdlncvbvhbfjonbnmxfl`)

- [ ] **Step 1: Aplicar la migración**

Nombre: `validacion_reuniones_columnas_e_historial`
```sql
ALTER TABLE public.seguimiento_reuniones
  ADD COLUMN IF NOT EXISTS status_reunion      text,
  ADD COLUMN IF NOT EXISTS comentario_cp       text,
  ADD COLUMN IF NOT EXISTS validated_by_cp     text,
  ADD COLUMN IF NOT EXISTS validated_cp_at     timestamptz,
  ADD COLUMN IF NOT EXISTS comentario_cli      text,
  ADD COLUMN IF NOT EXISTS validated_by_cli    text,
  ADD COLUMN IF NOT EXISTS validated_cli_at    timestamptz,
  ADD COLUMN IF NOT EXISTS motivo_no_validez   text,
  ADD COLUMN IF NOT EXISTS estado_comercial    text,
  ADD COLUMN IF NOT EXISTS proximo_paso        text,
  ADD COLUMN IF NOT EXISTS comentario_final    text,
  ADD COLUMN IF NOT EXISTS validated_final_by  text,
  ADD COLUMN IF NOT EXISTS validated_final_at  timestamptz,
  ADD COLUMN IF NOT EXISTS final_override      boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS flag_meta_countable boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS flag_disputa        boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS flag_cliente_pendiente boolean DEFAULT true,
  ADD COLUMN IF NOT EXISTS recording_url       text,
  ADD COLUMN IF NOT EXISTS transcript_url      text,
  ADD COLUMN IF NOT EXISTS ai_summary          text,
  ADD COLUMN IF NOT EXISTS ai_recommendation   text,
  ADD COLUMN IF NOT EXISTS ai_bant_detected    text,
  ADD COLUMN IF NOT EXISTS ai_confidence       numeric,
  ADD COLUMN IF NOT EXISTS ai_evidence         text;

CREATE TABLE IF NOT EXISTS public.meeting_status_history (
  id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  meeting_id    bigint,
  field_changed text,
  old_value     text,
  new_value     text,
  changed_by    text,
  changed_by_role text,
  source_dashboard text,
  changed_at    timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_msh_meeting ON public.meeting_status_history (meeting_id);
```

- [ ] **Step 2: Verificar columnas**

MCP `execute_sql`:
```sql
SELECT count(*) FROM information_schema.columns
WHERE table_schema='public' AND table_name='seguimiento_reuniones'
  AND column_name IN ('status_reunion','estado_comercial','flag_meta_countable','comentario_cli');
```
Esperado: `4`.

- [ ] **Step 3: Commit (registro)**
```bash
git commit --allow-empty -m "db: columnas de validación 3 capas + meeting_status_history"
```

---

### Task 2: Motor de reglas `shared/validacion.py` + test

**Files:** Create `shared/validacion.py` · Create `tests/test_validacion.py`

- [ ] **Step 1: Escribir el test que falla**

`tests/test_validacion.py`:
```python
"""Tests del motor de reglas de validación (run: python tests/test_validacion.py)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.validacion import (
    derivar_final, flag_disputa, flag_meta_countable, gate_valida_permitida, bant_list,
    STATUS_REUNION, VAL_ESTADOS, VAL_FINAL,
)

def test_no_realizada_no_cuenta():
    assert derivar_final("no_asistio_lead", "valida", "valida", "B,A,N,T") == "no_valida"
    assert derivar_final("cancelada_cliente", "valida", "valida", "B,A") == "no_valida"

def test_reagenda_pendiente():
    assert derivar_final("reagendada", "valida", "valida", "B,A") == "pendiente"
    assert derivar_final("agendada", "espera", "espera", "") == "pendiente"

def test_cliente_valida_manda():
    assert derivar_final("realizada", "no_valida", "valida", "") == "valida"
    assert derivar_final("realizada", "valida", "valida", "B,A") == "valida"

def test_disputa_engano():
    assert derivar_final("realizada", "valida", "no_valida", "B,A,N") == "en_disputa"
    assert flag_disputa("valida", "no_valida", "B,A,N") is True

def test_ambos_no_valida():
    assert derivar_final("realizada", "no_valida", "no_valida", "") == "no_valida"

def test_cliente_pendiente():
    assert derivar_final("realizada", "valida", "espera", "B,A") == "pendiente"

def test_override_manda():
    assert derivar_final("no_asistio_lead", "no_valida", "no_valida", "", override="valida") == "valida"

def test_gate_y_meta():
    assert gate_valida_permitida("realizada") is True
    assert gate_valida_permitida("no_asistio_lead") is False
    assert gate_valida_permitida("agendada") is False
    assert flag_meta_countable("valida") is True
    assert flag_meta_countable("en_disputa") is False

def test_bant_list():
    assert bant_list("B,A,x,T") == ["B", "A", "T"]

if __name__ == "__main__":
    for fn in [test_no_realizada_no_cuenta, test_reagenda_pendiente, test_cliente_valida_manda,
               test_disputa_engano, test_ambos_no_valida, test_cliente_pendiente,
               test_override_manda, test_gate_y_meta, test_bant_list]:
        fn()
    print("OK validacion")
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python tests/test_validacion.py`
Esperado: `ModuleNotFoundError: No module named 'shared.validacion'`.

- [ ] **Step 3: Implementar `shared/validacion.py`**

```python
"""Reglas del núcleo de validación de reuniones — puro y testeable.

3 capas de validez (cp/cli/final). La final se deriva automáticamente con
`derivar_final`; CP nunca se pisa; nada que no se haya realizado puede ser válido.
"""

STATUS_REUNION = ["agendada", "realizada", "no_asistio_lead", "no_asistio_cliente",
                  "cancelada_lead", "cancelada_cliente", "reagendada",
                  "pendiente_reagendar", "sin_info"]
VAL_ESTADOS = ["espera", "valida", "no_valida", "requiere_revision"]      # CP y cliente
VAL_FINAL   = ["pendiente", "valida", "no_valida", "en_disputa", "reagendada", "excluida"]
BANT_OPTS   = ["B", "A", "N", "T"]
MOTIVO_NO_VALIDEZ = ["no_calza_icp", "sin_necesidad", "sin_autoridad", "sin_presupuesto",
                     "sin_timing", "no_realizada", "otro"]
ESTADO_COMERCIAL = ["pendiente_seguimiento", "proximo_paso", "solicita_propuesta",
                    "propuesta_enviada", "seguimiento_propuesta", "negociacion",
                    "no_responde", "cliente_ganado", "cliente_perdido", "no_califica"]

_NO_REALIZADA = {"no_asistio_lead", "no_asistio_cliente", "cancelada_lead", "cancelada_cliente"}


def bant_list(v) -> list:
    if not v:
        return []
    items = v if isinstance(v, list) else str(v).split(",")
    return [x.strip().upper() for x in items if x and x.strip().upper() in BANT_OPTS]


def gate_valida_permitida(status_reunion) -> bool:
    """Solo una reunión realizada puede ser válida (candado)."""
    return status_reunion == "realizada"


def derivar_final(status_reunion, val_cp, val_cli, bant_cp, override=None):
    """Validez final automática. `override` (validez fijada a mano por CP) manda siempre."""
    if override:
        return override
    if status_reunion in _NO_REALIZADA:
        return "no_valida"            # se excluye del conteo
    if status_reunion != "realizada":  # agendada, reagendada, pendiente_reagendar, sin_info
        return "pendiente"
    if val_cli == "valida":
        return "valida"               # el cliente manda; sin disputa aunque CP sea no_valida
    if val_cli == "no_valida":
        if val_cp == "valida" and len(bant_list(bant_cp)) >= 2:
            return "en_disputa"
        if val_cp == "no_valida":
            return "no_valida"
        return "en_disputa"
    return "pendiente"                 # cliente en espera / requiere revisión


def flag_disputa(val_cp, val_cli, bant_cp) -> bool:
    return val_cp == "valida" and val_cli == "no_valida" and len(bant_list(bant_cp)) >= 2


def flag_meta_countable(val_final) -> bool:
    return val_final == "valida"
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python tests/test_validacion.py`
Esperado: `OK validacion`

- [ ] **Step 5: Commit**
```bash
git add shared/validacion.py tests/test_validacion.py
git commit -m "feat(validacion): motor de reglas 3 capas (derivación final, flags, candado) + test"
```

---

### Task 3: Escritura por nivel + historial en `shared/seguimiento.py`

**Files:** Modify `shared/seguimiento.py`

- [ ] **Step 1: Agregar el log de historial y el recalculo de final/flags**

Al final de `shared/seguimiento.py`, agregar:
```python
from shared.validacion import derivar_final, flag_disputa, flag_meta_countable


def registrar_historial(meeting_id, field, old, new, by, role, dashboard):
    if str(old) == str(new):
        return
    requests.post(
        f"{_URL}/rest/v1/meeting_status_history",
        json={"meeting_id": meeting_id, "field_changed": field,
              "old_value": str(old) if old is not None else None,
              "new_value": str(new) if new is not None else None,
              "changed_by": by, "changed_by_role": role, "source_dashboard": dashboard},
        headers={**_HW, "Prefer": "return=minimal"}, timeout=10)


def recalcular_final_y_flags(reunion_id: int, cliente_slug: str) -> dict:
    """Lee la fila, deriva la validez final automática y los flags, y los persiste.
    Respeta el override manual (final_override=true)."""
    filas = cargar(cliente_slug)
    r = filas.get(int(reunion_id), {})
    override = r.get("val_estado_final") if r.get("final_override") else None
    final = derivar_final(r.get("status_reunion"), r.get("val_estado_cp"),
                          r.get("val_estado_cli"), r.get("bant_cp"), override=override)
    disp = flag_disputa(r.get("val_estado_cp"), r.get("val_estado_cli"), r.get("bant_cp"))
    countable = flag_meta_countable(final)
    pend_cli = (r.get("val_estado_cli") in (None, "", "espera"))
    payload = {"reunion_id": reunion_id, "cliente_slug": cliente_slug,
               "val_estado_final": final, "flag_disputa": disp,
               "flag_meta_countable": countable, "flag_cliente_pendiente": pend_cli,
               "updated_at": datetime.now(timezone.utc).isoformat()}
    requests.post(f"{_URL}/rest/v1/seguimiento_reuniones", json=payload,
                  headers={**_HW, "Prefer": "resolution=merge-duplicates,return=minimal"}, timeout=10)
    return {"final": final, "disputa": disp, "countable": countable, "pendiente_cli": pend_cli}
```

- [ ] **Step 2: Verificar sintaxis + tests previos**

Run:
```bash
python -c "import ast; ast.parse(open('shared/seguimiento.py',encoding='utf-8').read()); print('OK')"
python tests/test_seguimiento_helpers.py
python tests/test_validacion.py
```
Esperado: OK en los tres.

- [ ] **Step 3: Commit**
```bash
git add shared/seguimiento.py
git commit -m "feat(seguimiento): recalculo de validez final + flags + log de historial"
```

---

### Task 4: UI cliente — Validación de Reuniones (`12_GBS`)

**Files:** Modify `dashboard/pages/12_GBS_Validacion_Reuniones.py`

- [ ] **Step 1: Importar opciones y helpers**

Tras los imports de `shared.seguimiento`, agregar:
```python
from shared.validacion import (
    VAL_ESTADOS, MOTIVO_NO_VALIDEZ, ESTADO_COMERCIAL, bant_list as _bant_list,
)
from shared.seguimiento import recalcular_final_y_flags, registrar_historial, guardar_nivel as _gn
```

- [ ] **Step 2: Mostrar CP en solo-lectura y editar el nivel cliente**

En el loop de cada reunión, debajo de la cabecera de la tarjeta, reemplazar el bloque de validación
del cliente por:
```python
            seg = seguimiento.get(rid, {})
            # Solo-lectura: lo que puso el equipo (CP)
            _cp_val = seg.get("val_estado_cp") or "espera"
            _cp_bant = " · ".join(_bant_list(seg.get("bant_cp"))) or "—"
            st.markdown(
                f'<div style="font-size:12px;color:#475569;margin:4px 0 8px">'
                f'Validez del equipo (CP): <b>{_cp_val}</b> · BANT CP: <b>{_cp_bant}</b></div>',
                unsafe_allow_html=True)

            cE1, cE2 = st.columns(2)
            with cE1:
                v_cli = st.selectbox("Tu validación", VAL_ESTADOS,
                    index=VAL_ESTADOS.index(seg.get("val_estado_cli")) if seg.get("val_estado_cli") in VAL_ESTADOS else 0,
                    key=f"vcli_{rid}_{i}")
                b_cli = st.multiselect("BANT (cliente)", ["B", "A", "N", "T"],
                    default=_bant_list(seg.get("bant_cli")),
                    placeholder="Seleccionar opciones", key=f"bcli_{rid}_{i}")
            with cE2:
                ec = st.selectbox("Estado comercial", ["—"] + ESTADO_COMERCIAL,
                    index=(ESTADO_COMERCIAL.index(seg.get("estado_comercial")) + 1) if seg.get("estado_comercial") in ESTADO_COMERCIAL else 0,
                    key=f"ec_{rid}_{i}")
                pp = st.text_input("Próximo paso acordado", value=seg.get("proximo_paso") or "",
                    key=f"pp_{rid}_{i}")
            motivo = None
            coment = st.text_input("Comentario", value=seg.get("comentario_cli") or "", key=f"ccli_{rid}_{i}")
            if v_cli == "no_valida":
                motivo = st.selectbox("Motivo de no validez (obligatorio)", MOTIVO_NO_VALIDEZ,
                    key=f"mot_{rid}_{i}")
            # Validez final (solo lectura)
            st.markdown(
                f'<div style="font-size:12px;color:#475569;margin-top:6px">'
                f'Validez final: <b>{seg.get("val_estado_final") or "pendiente"}</b></div>',
                unsafe_allow_html=True)

            if st.button("Guardar", key=f"save_{rid}_{i}", type="primary"):
                if v_cli == "no_valida" and not (coment.strip()):
                    st.warning("Si la reunión es No válida, el comentario es obligatorio.")
                else:
                    _gn(rid, "gbs", "cli", val_estado=v_cli, bant=b_cli,
                        etapa=(ec if ec != "—" else None), status=coment)
                    requests.patch(
                        f"{SUPABASE_URL}/rest/v1/seguimiento_reuniones?reunion_id=eq.{rid}",
                        json={"estado_comercial": (ec if ec != "—" else None),
                              "proximo_paso": pp, "comentario_cli": coment,
                              "motivo_no_validez": motivo, "validated_by_cli": "cliente",
                              "validated_cli_at": datetime.now(timezone.utc).isoformat()},
                        headers=_HW, timeout=10)
                    recalcular_final_y_flags(rid, "gbs")
                    registrar_historial(rid, "val_estado_cli", seg.get("val_estado_cli"), v_cli,
                                        "cliente", "cliente", "validacion")
                    st.toast("Guardado")
                    st.cache_data.clear(); st.rerun()
```

- [ ] **Step 3: Verificar sintaxis**

Run: `python -c "import ast; ast.parse(open('dashboard/pages/12_GBS_Validacion_Reuniones.py',encoding='utf-8').read()); print('OK')"`
Esperado: `OK`

- [ ] **Step 4: Commit**
```bash
git add dashboard/pages/12_GBS_Validacion_Reuniones.py
git commit -m "feat(validacion cliente): validez+BANT cliente, estado comercial, próximo paso, motivo obligatorio"
```

---

### Task 5: UI interna — Seguimiento (`1_Seguimiento_Reuniones`)

**Files:** Modify `dashboard/pages/1_Seguimiento_Reuniones.py`

- [ ] **Step 1: Importar opciones y helpers**

Tras los imports de `shared.metas`, agregar:
```python
from shared.validacion import STATUS_REUNION, VAL_ESTADOS, gate_valida_permitida
from shared.seguimiento import (
    cargar as cargar_seg_cli, guardar_nivel as _gn_cp, recalcular_final_y_flags,
    registrar_historial,
)
```

- [ ] **Step 2: Controles por reunión (status_reunion + validez CP + BANT CP + final)**

En `render_tabla`, dentro del loop de cada reunión, en `col_estado`, reemplazar el `selectbox` único de
estado por:
```python
        with col_estado:
            seg = cargar_seg_cli(cliente_slug).get(reunion_id, {})
            sr = st.selectbox("Estado reunión", STATUS_REUNION,
                index=STATUS_REUNION.index(seg.get("status_reunion")) if seg.get("status_reunion") in STATUS_REUNION else 0,
                key=f"{prefix}_sr_{reunion_id}_{i}")
            vcp = st.selectbox("Validez CP", VAL_ESTADOS,
                index=VAL_ESTADOS.index(seg.get("val_estado_cp")) if seg.get("val_estado_cp") in VAL_ESTADOS else 0,
                key=f"{prefix}_vcp_{reunion_id}_{i}")
            bcp = st.multiselect("BANT CP", ["B", "A", "N", "T"],
                default=[x for x in (seg.get("bant_cp") or "").split(",") if x],
                placeholder="Seleccionar opciones", key=f"{prefix}_bcp_{reunion_id}_{i}")
            vf_opts = ["(automática)", "valida", "no_valida", "en_disputa", "excluida"]
            vf = st.selectbox("Validez FINAL", vf_opts, index=0, key=f"{prefix}_vf_{reunion_id}_{i}",
                help="Dejar en automática salvo que quieras fijarla a mano.")
            if vcp == "valida" and not gate_valida_permitida(sr):
                st.caption("Solo una reunión Realizada puede ser válida.")
            if st.button("Guardar", key=f"{prefix}_save_{reunion_id}_{i}", type="primary"):
                _gn_cp(reunion_id, cliente_slug, "cp", val_estado=vcp, bant=bcp)
                patch = {"status_reunion": sr, "validated_by_cp": "cp",
                         "validated_cp_at": datetime.datetime.now().isoformat()}
                if vf != "(automática)":
                    patch.update({"val_estado_final": vf, "final_override": True,
                                  "validated_final_by": "CP", "validated_final_at": datetime.datetime.now().isoformat()})
                else:
                    patch.update({"final_override": False})
                requests.patch(
                    f"{SUPABASE_URL}/rest/v1/seguimiento_reuniones?reunion_id=eq.{reunion_id}",
                    json=patch, headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json", "Prefer": "return=minimal"}, timeout=10)
                recalcular_final_y_flags(reunion_id, cliente_slug)
                registrar_historial(reunion_id, "status_reunion", seg.get("status_reunion"), sr,
                                    "cp", "cp", "seguimiento")
                st.cache_data.clear(); st.rerun()
```
(El SDR ya se muestra en `col_info`; se mantiene. La fila debe seguir devolviendo `cambios` o ajustarse
para no romper el guardado masivo: si el guardado pasa a ser por reunión, eliminar el bloque de "Guardar
cambios" masivo de `run`.)

- [ ] **Step 3: Widgets de validación + avance/proyección**

En `run`, después de los KPIs actuales, agregar widgets que leen `seguimiento_reuniones` (vía
`cargar_validacion_final` extendido a traer también flags). Mínimo: válidas finales (flag_meta_countable),
en disputa (flag_disputa), pendientes cliente (flag_cliente_pendiente). El avance de meta usa
`válidas_finales / meta` (ya implementado en las tarjetas) leyendo `val_estado_final`.

- [ ] **Step 4: Verificar sintaxis**

Run: `python -c "import ast; ast.parse(open('dashboard/pages/1_Seguimiento_Reuniones.py',encoding='utf-8').read()); print('OK')"`
Esperado: `OK`

- [ ] **Step 5: Commit**
```bash
git add dashboard/pages/1_Seguimiento_Reuniones.py
git commit -m "feat(seguimiento): status_reunion + validez/BANT CP + final + widgets de validación"
```

---

### Task 6: Indicadores — avance oficial con `flag_meta_countable`

**Files:** Modify `dashboard/pages/11_GBS.py` (bloque de avance de meta, `cargar_validacion_gbs`)

- [ ] **Step 1: Contar válidas finales por flag**

En `cargar_validacion_gbs` (o donde se cuenta `validas`), contar las filas de `seguimiento_reuniones`
con `flag_meta_countable = true` para GBS:
```python
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/seguimiento_reuniones"
        f"?cliente_slug=eq.gbs&flag_meta_countable=eq.true&select=reunion_id",
        headers=_SB_H, timeout=15)
    validas = len(r.json()) if r.ok else 0
```

- [ ] **Step 2: Verificar sintaxis**

Run: `python -c "import ast; ast.parse(open('dashboard/pages/11_GBS.py',encoding='utf-8').read()); print('OK')"`
Esperado: `OK`

- [ ] **Step 3: Commit**
```bash
git add dashboard/pages/11_GBS.py
git commit -m "feat(indicadores): avance oficial cuenta solo flag_meta_countable"
```

---

### Task 7: Inicializar las 2 reuniones reales + validación final, push y pruebas

**Files:** Migración Supabase + verificación

- [ ] **Step 1: Inicializar status/flags de las reuniones existentes (5354, 5355)**

MCP `apply_migration` `init_status_reuniones_gbs`:
```sql
INSERT INTO public.seguimiento_reuniones (reunion_id, cliente_slug, status_reunion,
   val_estado_cp, val_estado_cli, val_estado_final, flag_cliente_pendiente,
   flag_disputa, flag_meta_countable)
VALUES (5354,'gbs','agendada','espera','espera','pendiente',true,false,false),
       (5355,'gbs','agendada','espera','espera','pendiente',true,false,false)
ON CONFLICT (reunion_id) DO UPDATE SET status_reunion=COALESCE(seguimiento_reuniones.status_reunion,'agendada');
```

- [ ] **Step 2: Sintaxis + tests + push**
```bash
for f in shared/validacion.py shared/seguimiento.py dashboard/pages/12_GBS_Validacion_Reuniones.py dashboard/pages/1_Seguimiento_Reuniones.py dashboard/pages/11_GBS.py; do python -c "import ast,sys; ast.parse(open(sys.argv[1],encoding='utf-8').read()); print('OK',sys.argv[1])" "$f"; done
python tests/test_validacion.py
python tests/test_seguimiento_helpers.py
git push origin master
```
Esperado: todo OK; push exitoso.

- [ ] **Step 3: Smoke manual (flujo completo)**

1. Seguimiento: marcar una reunión Realizada + Validez CP=valida + BANT≥2 → guardar.
2. Validación (cliente): marcar Válida → final pasa a `valida`, flag_meta_countable=true.
3. Validación: marcar No válida (con comentario) → final pasa a `en_disputa`, flag_disputa=true.
4. Indicadores: el avance refleja solo las válidas finales.
5. Verificar `meeting_status_history` registró los cambios.

---

## Cobertura del spec (self-review)

- Status operativo + 3 capas de validez → Task 1 + 2 + 4 + 5. ✅
- Propagación automática + candado realizada + cliente=válida manda → Task 2 (motor) + 3 (recalculo). ✅
- BANT puro CP y cliente → Task 2 + 4 + 5. ✅
- Estado comercial 100% cliente → Task 4. ✅
- Motivo obligatorio si no válida → Task 4. ✅
- Flags (meta_countable/disputa/pendiente) → Task 3. ✅
- Historial de cambios → Task 1 + 3. ✅
- Avance oficial por flag → Task 6. ✅
- SDR visible solo interno → ya en `1_Seguimiento` (col_info); el cliente no lo muestra. ✅
- IA/grabaciones (campos vacíos) → Task 1 (columnas creadas). Integración real = Proyecto 2 (fuera de alcance). ✅
- Avance probable / proyección detallada y auditoría GHL completa → quedan como refinamiento posterior (Task 5 deja la base de widgets); no bloquean el núcleo.
