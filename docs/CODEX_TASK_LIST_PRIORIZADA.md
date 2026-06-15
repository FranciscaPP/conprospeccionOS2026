# Task List Priorizada — MVP Setup
**Fecha:** 2026-05-29
**Para:** Codex
**Contexto:** Tareas ordenadas por prioridad real de impacto operativo

---

## Resumen de prioridades

| Nivel | Descripción | Tareas |
|-------|-------------|--------|
| P0 — Crítico | Impide que el MVP funcione correctamente | 4 tareas |
| P1 — Importante | Necesario para flujo usable en producción | 8 tareas |
| P2 — Mejora | Optimización, UX, reportería | 7 tareas |

---

## P0 — CRÍTICO (impide funcionamiento correcto)

---

### P0-01: Bug en `_icp_a_apollo_filtros()` — industrias incorrectas

**Descripción:**
La función que mapea el ICP a filtros de Apollo tiene un bug: detecta `"import"` y `"export"` en el texto del ICP y los convierte en la industria `"Import and Export"` como **objetivo**, cuando para clientes de logística (como GBS) esa industria debería ser **excluida** (es competencia directa, no cliente).

**Archivos involucrados:**
- `mvp_setup/app.py` — función `_icp_a_apollo_filtros()`, línea ~2862

**Qué debe cambiarse:**
```python
# ACTUAL (buggy):
ind_kw = {
    "import": "Import and Export",   # Bug: detecta "importador" como "Import and Export"
    "export": "Import and Export",   # Bug: idem
    ...
}

# CORRECTO:
ind_kw = {
    "logis": "Logistics and Supply Chain",
    "supply chain": "Logistics and Supply Chain",
    "transport": "Transportation/Trucking/Railroad",
    # ... NO incluir "import"/"export" como industrias objetivo
    # Si el ICP menciona "importadores" como clientes, eso mapea a:
    # Retail, Manufacturing, Consumer Goods — las empresas que CONTRATAN logística
}
```

También, la función debe contrastar con `icp_criterios_descarte` para generar `ind_excluidas`, y el campo `competidores` del estado debe alimentar `ind_excluidas` adicionalmente.

**Resultado esperado:**
Para GBS Logistics, `_icp_a_apollo_filtros()` devuelve industrias objetivo como `["Logistics and Supply Chain", "Manufacturing", "Retail"]` y excluidas como `["Import and Export", "Government Administration"]`.

**Criterio de aceptación:**
Al presionar "Cargar desde ICP" en el pool search de GBS, las industrias sugeridas son los clientes de GBS (quienes contratan logística), no las empresas del mismo rubro.

**Riesgo si no se hace:**
Los filtros auto-generados son inútiles o contraproducentes. El usuario termina con bases llenas de competidores.

---

### P0-02: Apollo API no filtra industrias — falta post-filtro en sección API

**Descripción:**
La sección "Buscar prospectos directamente" de la API Apollo llama a `_apollo_buscar()` y devuelve resultados, pero `q_organization_keyword_tags` no es un filtro duro de industria. Las empresas de industrias incorrectas (competencia, gobierno) siguen apareciendo. El pool search ya tiene post-filtro de industrias, pero la sección API no lo tiene.

**Archivos involucrados:**
- `mvp_setup/app.py` — función `tab_bases_apollo()`, sección "Buscar en API Apollo" (~línea 3288-3320)

**Qué debe cambiarse:**
Después de convertir el resultado de Apollo a DataFrame con `_apollo_a_df()`, aplicar el mismo post-filtro de industrias que existe en el pool search:

```python
# Después de _apollo_a_df(people):
if ind_incluir:
    _ind_lower = [i.lower() for i in ind_incluir]
    _ind_col = next((c for c in df_result.columns if c.lower() == 'industry'), None)
    if _ind_col:
        df_result = df_result[df_result[_ind_col].fillna('').str.lower().apply(
            lambda v: any(ind in v for ind in _ind_lower) if v.strip() else True
        )]

if ind_excluir:
    _excl_lower = [i.lower() for i in ind_excluir]
    if _ind_col:
        df_result = df_result[~df_result[_ind_col].fillna('').str.lower().apply(
            lambda v: any(ex in v for ex in _excl_lower)
        )]
```

**Resultado esperado:**
Los contactos de Apollo traídos por API ya no incluyen empresas de "Import and Export", "Government Administration", ni otras industrias excluidas.

**Criterio de aceptación:**
Después de buscar con Apollo API + industrias excluidas configuradas, el resultado no contiene empresas de esas industrias.

**Riesgo si no se hace:**
El usuario sigue viendo resultados con competidores/industrias incorrectas, perdiendo confianza en el sistema.

---

### P0-03: `'_df_search' in dir()` — hack que puede crashear

**Descripción:**
En el botón "Descargar TODO el pool (sin filtros)", el código usa:
```python
data=_df_search.to_csv(...) if '_df_search' in dir() else b''
```
Esto es un hack. `dir()` devuelve variables del scope local pero `_df_search` solo existe si el usuario presionó "Filtrar base" en la misma sesión. Si no lo hizo, el botón descarga un archivo vacío sin avisar.

**Archivos involucrados:**
- `mvp_setup/app.py` — línea ~3572

**Qué debe cambiarse:**
```python
# ACTUAL (hack):
data=_df_search.to_csv(...) if '_df_search' in dir() else b''

# CORRECTO: leer el pool directamente desde archivo
def _get_pool_csv(ruta_apollo, ruta_snov, fuente):
    dfs = []
    if fuente in ('Apollo + Snov', 'Solo Apollo') and ruta_apollo.exists():
        dfs.append(pd.read_csv(str(ruta_apollo), dtype=str, encoding='utf-8-sig'))
    if fuente in ('Apollo + Snov', 'Solo Snov') and ruta_snov.exists():
        dfs.append(pd.read_csv(str(ruta_snov), dtype=str, encoding='utf-8-sig'))
    if not dfs:
        return b''
    return pd.concat(dfs, ignore_index=True).to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
```

**Resultado esperado:**
El botón siempre descarga el pool completo actualizado, independientemente de si se filtró antes.

**Criterio de aceptación:**
Descargar todo el pool funciona aunque no se haya ejecutado "Filtrar base" previamente.

**Riesgo si no se hace:**
El usuario descarga un archivo vacío creyendo que tiene todo el pool, pierde datos.

---

### P0-04: Competidores del ICP no se excluyen en la búsqueda del pool

**Descripción:**
El campo `est.get("competidores")` se guarda en `estado_cliente.json` (Paso 1/3) pero no se usa en la búsqueda del pool ni en `_clasificar_base()`. Las empresas competidoras aparecen en los resultados.

**Archivos involucrados:**
- `mvp_setup/app.py` — función `_clasificar_base()` (~línea 3152) y pool search (~línea 3462)

**Qué debe cambiarse:**

En `_clasificar_base()`, agregar:
```python
competidores_excl = _parsear_lista_icp(icp.get("competidores", ""))
excluida_competidor = bool(competidores_excl and _match_keywords(empresa, competidores_excl))

if excluida or excluida_competidor or descarte_match:
    tier = "❌ Excluir"
```

En pool search, al cargar ICP, cargar competidores como exclusión adicional:
```python
_competidores = _plist(est.get("competidores", "") or "")
# Agregar al multiselect de industrias excluidas si hay coincidencias de industria
```

**Resultado esperado:**
Empresas competidoras (definidas en Paso 1) no aparecen en resultados de pool ni en calificación.

**Criterio de aceptación:**
Si GBS tiene "DHL, Fedex" como competidores, esas empresas obtienen `❌ Excluir` en la calificación.

**Riesgo si no se hace:**
Los SDRs contactan a competidores de sus propios clientes — error grave operativo.

---

## P1 — IMPORTANTE (flujo usable en producción)

---

### P1-01: Separar company_score de contact_score en `_clasificar_base()`

**Descripción:**
Actualmente el score mezcla cargo (del contacto) con industria/país (de la empresa). Esto genera situaciones donde un contacto excelente en empresa incorrecta obtiene Tier B, y el usuario no sabe por qué.

**Archivos involucrados:**
- `mvp_setup/app.py` — función `_clasificar_base()` (~línea 3152)

**Qué debe cambiarse:**
Ver diseño completo en `docs/CODEX_PASO_5_BASE_Y_MENSAJERIA.md` — sección 5.

**Resultado esperado:**
Cada contacto tiene `CP_Company_Score`, `CP_Contact_Score` y `CP_Tier` separados. La tabla muestra ambos scores. Hay dos columnas adicionales: `CP_Motivo_Empresa` y `CP_Motivo_Contacto`.

**Criterio de aceptación:**
Un contacto con cargo perfecto en empresa de industria incorrecta muestra: company_score=0, contact_score=7, tier=Tier C (con nota "industria no match"). El usuario puede decidir contactarlo igual.

**Riesgo si no se hace:**
Pérdida de contactos valiosos (buen cargo + empresa incorrecta) y confusión sobre por qué las empresas buenas quedan en Tier B.

---

### P1-02: Verificar y documentar Snov.io API en producción

**Descripción:**
La integración con Snov.io existe en código pero no está probada. El endpoint `/v2/api/search-contacts` puede no existir o tener estructura diferente. Los errores se silencian.

**Archivos involucrados:**
- `mvp_setup/app.py` — funciones `_snov_token()`, `_snov_buscar()`, `_snov_a_df()` (~línea 3045-3100)

**Qué debe cambiarse:**
1. Probar `_snov_token()` con credenciales reales y verificar que devuelve token
2. Probar `_snov_buscar()` con una búsqueda simple (1 cargo, 1 país, per_page=5)
3. Imprimir la respuesta real para entender la estructura
4. Actualizar `_snov_a_df()` con los paths correctos
5. Agregar error handling visible (no silenciar): `st.error(f"Snov error: {r.status_code} — {r.text[:300]}")`

**Resultado esperado:**
`_snov_buscar()` funciona, `_snov_a_df()` parsea correctamente, los errores se muestran al usuario.

**Criterio de aceptación:**
Con credenciales de Snov configuradas, una búsqueda simple devuelve al menos 1 contacto con nombre, cargo y empresa correctos.

**Riesgo si no se hace:**
Snov.io silenciosamente falla en producción y el usuario no sabe por qué no trae datos.

---

### P1-03: Agregar paginación real en búsqueda Apollo API

**Descripción:**
La función `_apollo_buscar()` solo trae `per_page` resultados (máx 100 por llamada). No hay paginación activa. El usuario no puede descargar 500 o 1000 contactos de una sola búsqueda.

**Archivos involucrados:**
- `mvp_setup/app.py` — función `_apollo_buscar()` (~línea 2957) y su llamada en `tab_bases_apollo`

**Qué debe cambiarse:**
```python
def _apollo_buscar_paginado(cargos, paises, n_objetivo=500, **kwargs) -> list:
    todos = []
    pagina = 1
    while len(todos) < n_objetivo:
        resultado = _apollo_buscar(cargos, paises, pagina=pagina, por_pagina=100, **kwargs)
        if "error" in resultado:
            break
        people = resultado.get("people", resultado.get("contacts", []))
        if not people:
            break
        todos.extend(people)
        pagina += 1
        total_disponible = resultado.get("pagination", {}).get("total_entries", 0)
        if len(todos) >= total_disponible:
            break
    return todos[:n_objetivo]
```

También agregar botón "Estimar" que trae `per_page=1` y muestra `pagination.total_entries`.

**Resultado esperado:**
Usuario puede definir "quiero 500 contactos" y el sistema pagina automáticamente haciendo múltiples llamadas.

**Criterio de aceptación:**
Al pedir 500 contactos con Apollo API, el sistema hace 5 llamadas y acumula 500 contactos (menos duplicados).

**Riesgo si no se hace:**
El usuario solo puede traer 100 contactos por búsqueda, haciendo el flujo ineficiente.

---

### P1-04: Auto-guardar resultado de calificación en carpeta del cliente

**Descripción:**
Actualmente, después de calificar una base, el resultado solo existe en `st.session_state`. Si el usuario recarga la página, pierde el trabajo. Tampoco se guarda automáticamente en `08_BASES_Y_CALIFICACION/`.

**Archivos involucrados:**
- `mvp_setup/app.py` — sección de calificación en `tab_bases_apollo` (~línea 3619-3625)

**Qué debe cambiarse:**
```python
# Después de clasificar:
df_cal = _clasificar_base(df_raw, est)
st.session_state[f"base_cal_{path.name}"] = df_cal

# Auto-guardar en carpeta del cliente
fecha_str = datetime.now().strftime("%Y%m%d_%H%M")
carpeta_cal = path / "08_BASES_Y_CALIFICACION" / "02_calificadas"
carpeta_cal.mkdir(parents=True, exist_ok=True)
nombre_base = archivo.name.rsplit(".", 1)[0]
ruta_guardado = carpeta_cal / f"{nombre_base}_calificada_{fecha_str}.csv"
df_cal.to_csv(str(ruta_guardado), index=False, encoding='utf-8-sig')
st.success(f"✅ Guardado automáticamente en 08_BASES_Y_CALIFICACION/02_calificadas/")
```

**Resultado esperado:**
Cada calificación se guarda automáticamente con timestamp en la carpeta correcta del cliente.

**Criterio de aceptación:**
Después de calificar, el archivo aparece en `08_BASES_Y_CALIFICACION/02_calificadas/` y en la lista de "Bases clasificadas anteriores".

---

### P1-05: Separar Tab 4 en subtabs (Apollo / Snov / Calificar / Mensajería)

**Descripción:**
El Tab 4 actual tiene demasiadas secciones en una sola vista. Pool de Apollo, Pool de Snov, API Apollo, API Snov, upload manual, calificación, mensajería — todo en scroll vertical. Es confuso.

**Archivos involucrados:**
- `mvp_setup/app.py` — función `tab_bases_apollo()` (~línea 3256)

**Qué debe cambiarse:**
```python
def tab_bases_apollo(path: Path, est: dict):
    # ... ICP status header (siempre visible) ...

    subtabs = st.tabs(["📊 Apollo.io", "📬 Snov.io", "⚡ Calificar", "✉️ Mensajería"])

    with subtabs[0]:  # Apollo.io
        _subtab_apollo(path, est)
    with subtabs[1]:  # Snov.io
        _subtab_snov(path, est)
    with subtabs[2]:  # Calificar
        _subtab_calificar(path, est)
    with subtabs[3]:  # Mensajería
        _subtab_mensajeria(path, est)
```

**Resultado esperado:**
El usuario navega entre Apollo, Snov, Calificación y Mensajería sin perder contexto. Cada subtab es una unidad coherente.

**Criterio de aceptación:**
Cambiar entre subtabs no reinicia el estado de la calificación ni de los filtros. Los datos persisten en `st.session_state`.

---

### P1-06: Agregar fechas de contrato en Tab "Datos del cliente"

**Descripción:**
El Tab de datos del cliente tiene la sección de contrato pero le faltan campos visuales para: fecha de inicio del contrato, fecha de inicio de prospección activa, y fecha de fin del contrato (calculada automáticamente).

**Archivos involucrados:**
- `mvp_setup/app.py` — función `tab_datos_cliente()` (~línea 1568)

**Qué debe cambiarse:**
Agregar en la sección de contrato:
```python
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    v_fecha_inicio = st.date_input("Fecha inicio contrato", ...)
with col_f2:
    v_fecha_prosp = st.date_input("Fecha inicio prospección activa", ...)
with col_f3:
    # Auto-calculada = fecha_inicio + meses_contrato
    fin = fecha_inicio + timedelta(days=meses * 30.4)
    st.metric("Fecha fin contrato", fin.strftime('%d/%m/%Y'))
```

**Resultado esperado:**
Las fechas se guardan en `comercial.json` y son visibles en el tab.

---

### P1-07: Hacer visible el ICP resumen antes de filtrar en el pool

**Descripción:**
Al entrar al Tab 4, el ICP summary está oculto en un `st.expander` colapsado. El usuario no ve qué criterios se están usando. Debería mostrarse siempre una versión compacta.

**Archivos involucrados:**
- `mvp_setup/app.py` — función `tab_bases_apollo()` (~línea 3266-3285)

**Qué debe cambiarse:**
Mostrar un summary always-visible en 3 columnas compactas:
```
Cargos: Director de Operaciones, Gerente... | Industrias: Logistics, Manufacturing... | Países: Chile, Perú...
Excluir empresas: DHL, Fedex... | Excluir industrias: Import and Export...
```

---

### P1-08: Guardar filtros de búsqueda en `07_APOLLO_Y_BUSQUEDAS/`

**Descripción:**
Cuando el usuario ejecuta una búsqueda (pool filter o API), los filtros usados deben guardarse en `07_APOLLO_Y_BUSQUEDAS/busqueda_{n}_prioritaria.md` para trazabilidad y reutilización.

**Archivos involucrados:**
- `mvp_setup/app.py` — sección de filtros del pool (~línea 3462)

**Qué debe cambiarse:**
Al presionar "Filtrar base" o "Descargar desde Apollo", guardar:
```markdown
# Búsqueda Apollo — GBS Logistics — 2026-05-29

**Cargos:** Director de Operaciones, Gerente de Logística...
**Industrias incluidas:** Logistics and Supply Chain, Manufacturing...
**Industrias excluidas:** Import and Export...
**Países:** Chile, Perú
**Empleados mínimos:** 50
**Resultado:** 1,234 contactos totales | 892 tras filtros | 341 nuevos al pool
```

---

## P2 — MEJORAS (optimización y UX)

---

### P2-01: Vectorizar `_clasificar_base()` para performance

**Descripción:**
La función usa `iterrows()` que es O(n). En bases de 30k+ contactos tarda varios segundos. Debe reescribirse con operaciones vectorizadas de pandas (`.str.contains()`, `.apply()` vectorizado).

**Archivos involucrados:**
- `mvp_setup/app.py` — función `_clasificar_base()` (~línea 3152)

**Criterio de aceptación:**
Calificar 30k contactos tarda menos de 5 segundos.

---

### P2-02: Fetch automático de la URL del cliente en Paso 3

**Descripción:**
El análisis web actualmente requiere que el cliente suba documentos. Si no hay documentos, el análisis se basa solo en el nombre y la URL que el usuario escribió. Agregar fetch básico de la homepage del cliente.

**Archivos involucrados:**
- `mvp_setup/app.py` — función `tab_analisis()`

**Qué debe cambiarse:**
Botón "Analizar web directamente":
```python
import httpx
resp = httpx.get(web_url, timeout=10, follow_redirects=True)
# Extraer texto de HTML, pasar a Claude
```

---

### P2-03: Preview de archivos antes de subir en Paso 2

**Descripción:**
Al subir archivos, el usuario solo ve el nombre. Sería útil ver: tipo de archivo, tamaño, primeras líneas si es CSV/Excel.

---

### P2-04: Historial de versiones del ICP

**Descripción:**
Cuando se actualiza el ICP, se sobreescribe `icp_borrador.md`. No hay historial de cambios. Agregar versiones automáticas con timestamp.

**Archivos involucrados:**
- `mvp_setup/app.py` — `tab_icp()` — sección de guardado (~línea 2697)

---

### P2-05: Exportación XLSX con colores en pool search

**Descripción:**
El resultado del pool search se descarga como CSV. Sería útil poder descargarlo también como Excel con colores por tier (como ya existe en calificación manual).

---

### P2-06: Indicador de progreso en calificación

**Descripción:**
Al calificar 30k contactos, el spinner no muestra progreso. Agregar `st.progress()` con porcentaje.

---

### P2-07: Refactorizar módulos Apollo y Snov

**Descripción:**
Mover las funciones de API (`_apollo_buscar`, `_apollo_a_df`, `_snov_token`, `_snov_buscar`, `_snov_a_df`, `_icp_a_apollo_filtros`, `_clasificar_base`) a módulos separados:
- `mvp_setup/modules/apollo.py`
- `mvp_setup/modules/snov.py`
- `mvp_setup/modules/scoring.py`

**Beneficio:**
Testeable, mantenible, permite importar desde otros módulos.

**Nota:** No hacer esto hasta que P0 y P1 estén resueltos. No reescribir funcionalidad, solo mover.

---

## Criterios de aceptación globales

Para considerar el Paso 5 "listo para producción":

- [ ] El usuario puede subir una base Apollo de 30k contactos y filtrarla sin crashes
- [ ] Los filtros auto-generados desde ICP no incluyen competidores como objetivos
- [ ] Las industrias excluidas funcionan tanto en API Apollo como en pool search
- [ ] Los competidores del cliente están excluidos automáticamente en la calificación
- [ ] El resultado de calificación se guarda automáticamente en la carpeta del cliente
- [ ] Tier A/B/C son clasificaciones útiles (al menos 20% Tier A en una base bien filtrada)
- [ ] Snov.io funciona o falla con mensaje de error claro
- [ ] Los filtros usados quedan guardados para trazabilidad

---

## Preguntas abiertas para Francisca

Estas preguntas bloquean o condicionan decisiones de implementación. Necesito respuestas antes de avanzar en las tareas marcadas.

---

### Q1 — ICP de GBS Logistics (bloquea P0-01)
**Pregunta:** Para GBS Logistics, ¿cuál es exactamente la lista de industrias que deberían ser **objetivo** vs **excluidas**?

Por ejemplo:
- ¿Los importadores/exportadores (empresas que usan logística) van como objetivo o excluidas?
- ¿Las empresas de "Import and Export" son competencia de GBS o son sus clientes?
- ¿Qué industrias son claramente competencia de GBS?

---

### Q2 — Snov.io en producción (bloquea P1-02)
**Pregunta:** ¿Están configuradas las credenciales de Snov.io en el `.env`? ¿Se puede hacer una prueba real para verificar que el endpoint funciona?

---

### Q3 — Separación Apollo Pool vs API (diseño)
**Pregunta:** ¿Cuál es el flujo preferido para conseguir contactos?

Opciones:
- A) Exportar bases desde el sitio de Apollo y subir al pool (flujo actual ya funcionando)
- B) Buscar directamente en Apollo API desde la app (requiere créditos adicionales)
- C) Ambos, separados claramente

---

### Q4 — company_score vs contact_score (bloquea P1-01)
**Pregunta:** Si una empresa es perfecta (industria + tamaño match) pero el contacto tiene un cargo incorrecto, ¿qué tier debería recibir?

Opciones:
- A) Tier C (contacto no ideal pero empresa buena — vale buscar otro contacto)
- B) Tier B (empresa buena tiene prioridad media)
- C) Crear un tier separado "Empresa OK / Contacto incorrecto"

---

### Q5 — ICP aprobado vs borrador (diseño UX)
**Pregunta:** ¿Cuándo un ICP pasa de "borrador" a "aprobado" (icp_master.md)?

Opciones:
- A) Solo Francisca puede aprobar manualmente con un botón "Aprobar ICP"
- B) Cualquier cambio en el ICP estructurado (al presionar "Guardar ICP") lo promueve automáticamente
- C) El ICP se aprueba al terminar el Paso 4 (tab ICP) con un botón explícito

---

### Q6 — Mensajería por segmento (prioridad)
**Pregunta:** ¿La generación de mensajería por segmento (emails 1-2-3) es usable hoy, o tiene problemas que no detecté en la auditoría?

¿Se usan los mensajes generados directamente, o son solo borrador para que los SDRs editen?

---

### Q7 — GBS Logistics — estado actual del setup
**Pregunta:** ¿Qué pasos del setup de GBS están completados actualmente?

- ¿Tiene ICP aprobado?
- ¿Tiene base en el pool (BASES_APOLLO/GBS LOGISTICS/)?
- ¿Se ha probado la calificación de bases con GBS?

---

### Q8 — Campos del contrato faltantes (Paso 1)
**Pregunta:** ¿Hay algún campo del contrato que falte en el Tab "Datos del cliente" que sea crítico para la operación?

Por ejemplo:
- Correo general del cliente (¿necesario para la firma de email?)
- Contacto directo del cliente (nombre + cargo del interlocutor en el cliente)
- Número de SDRs asignados

---

*Task list generada mediante auditoría de código — 2026-05-29*
