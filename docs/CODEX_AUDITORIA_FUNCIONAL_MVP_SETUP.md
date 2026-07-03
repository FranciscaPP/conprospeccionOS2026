# Auditoría Funcional — MVP Setup
**Fecha:** 2026-05-29  
**Archivo auditado:** `mvp_setup/app.py` (~5,530 líneas)

---

## Resumen ejecutivo de la auditoría

El MVP Setup tiene una base sólida con los 5 pasos bien estructurados. Los Pasos 1-4 funcionan bien en general. El Paso 5 (Bases y Mensajería) es el más complejo y tiene los problemas más críticos, especialmente en la integración con APIs externas y la calidad de los filtros.

| Paso | Estado | Prioridad de fixes |
|------|--------|--------------------|
| Paso 1: Datos | ✅ Funciona — faltan algunos campos | P2 |
| Paso 2: Archivos | ✅ Funciona básicamente | P2 |
| Paso 3: Análisis web | ✅ Funciona con Claude | P2 |
| Paso 4: ICP | ⚠️ Funciona, bugs en mapping → Apollo | P1 |
| Paso 5: Bases | 🔴 Múltiples problemas críticos | P0/P1 |

---

## Paso 1 — Datos del cliente

### Dónde está en el código
- Función: `tab_datos_cliente(path, est)` — línea ~1568
- Guarda en: `estado_cliente.json` + `07_BASE_DATOS/comercial.json`

### Qué funciona
- Campos de información general: nombre, web, países, objetivo, industria
- Campos del prospector/SDR: nombre, cargo, correo, teléfono, LinkedIn, ciudad
- Sección de contrato: moneda, setup único, fijo/mes, meses, semanas setup, reuniones garantizadas, costo/reunión, notas
- Auto-extracción de datos comerciales desde propuesta PDF/DOCX con Claude
- Sincronización a Supabase (opcional, falla silenciosamente si no hay credenciales)
- Tabla de rentabilidad comparativa en página de inicio

### Qué falta o falla
- **Falta:** Fecha de inicio de contrato y fecha de inicio de prospección activa no aparecen en el formulario visual de forma prominente (están en `comercial.json` pero no en la sección de "Contrato")
- **Falta:** Campo de "correo general del cliente" (distinto del correo del prospector)
- **Falta:** Historial de cambios o versiones del contrato
- **Comportamiento no ideal:** Si se analiza la propuesta con Claude y luego se edita manualmente, los campos se guardan en orden inverso (el manual sobreescribe el de Claude solo al presionar "Guardar cambios")
- **Bug menor:** Si `comercial.json` existe pero tiene JSON malformado, el bloque `except` silencia el error y devuelve `{}`

### Criterio de aceptación del Paso 1
El usuario puede ingresar todos los datos del cliente, SDR y contrato, y quedan guardados en `estado_cliente.json` y `comercial.json` con fechas correctas.

---

## Paso 2 — Archivos del cliente

### Dónde está en el código
- Función: `tab_archivos(path, est)` — buscar "def tab_archivos" en app.py
- Guarda en: `CLIENTES/{ID}/00_INPUT_CLIENTE/{subcarpeta}/`

### Qué funciona
- Upload de múltiples archivos simultáneos
- Clasificación automática por tipo (logo → logos/, PDF/DOCX → documentos/, CSV/XLSX → bases/, etc.)
- Visualización de archivos ya subidos
- Descarga de archivos individuales

### Qué falta o falla
- **Falta:** Vista consolidada de qué hay en CADA carpeta (00, 03, 04, 05, etc.) — solo muestra 00_INPUT_CLIENTE
- **Falta:** Posibilidad de renombrar o eliminar archivos desde la UI
- **Falta:** Preview de documentos subidos (al menos el nombre y tamaño)
- **UX problema:** Si el usuario sube el mismo archivo dos veces, no hay deduplicación — se sobreescribe silenciosamente

---

## Paso 3 — Análisis web

### Dónde está en el código
- Función: `tab_analisis(path, est)` — buscar "def tab_analisis" en app.py
- Guarda en: `estado_cliente.json` + `03_ANALISIS_CLIENTE/*.md`

### Qué funciona
- Claude lee los documentos subidos del cliente (hasta 8 docs, 4,000 chars cada uno)
- Genera 5 cards de análisis: resumen, propuesta de valor, problema, diferenciación, tipo de cliente
- Chat continuo para refinar el análisis
- Guarda automáticamente en archivos MD

### Qué falta o falla
- **Limitación importante:** El "análisis web" no hace scraping de la web — lee documentos subidos + el campo "web" del estado. Si el cliente no subió documentos, el análisis es débil.
- **Falta:** Botón "Analizar URL directamente" que haga fetch de la web del cliente
- **Falta:** El análisis no incluye "segmentos potenciales" ni "oportunidades comerciales" mencionados en el diseño
- **UX problema:** Si Claude está sobrecargado (rate limit), el spinner se queda girando hasta 4 reintentos (~2 minutos). No hay feedback de cuánto puede tardar.

---

## Paso 4 — ICP / Buyer Persona

### Dónde está en el código
- Función: `tab_icp(path, est)` — línea ~2100 (aproximado)
- Función clave: `_icp_a_apollo_filtros(est)` — línea ~2862
- Guarda en: `estado_cliente.json` + `04_ICP_ESTRATEGIA/icp_borrador.md` + `04_ICP_ESTRATEGIA/icp_master.md`

### Qué funciona
- Generación automática de ICP con Claude usando documentos + análisis previo
- Chat continuo con contexto del cliente
- Campos estructurados: macro_cargos, cargos, industrias, micro_industrias, tamano, paises_foco, keywords, criterios_prioridad, criterios_descarte, empresas_foco
- Acciones rápidas preconfiguradas
- Vista del icp_borrador.md completo editable
- Vista del icp_master.md (read-only)
- La función `_icp_a_apollo_filtros()` mapea el ICP a filtros de Apollo

### Qué falta o falla

**Bug crítico en `_icp_a_apollo_filtros()`:**
```python
ind_kw = {
    ...
    "import": "Import and Export",  # Bug: "import" aparece en "importador" o "importaciones"
    "export": "Import and Export",  # Bug: un cliente de logística QUIERE importadores como clientes,
    ...                              #      pero NO quiere "Import and Export" como industria del prospecto
}
```
Si el ICP de GBS Logistics dice "importadores, exportadores" como clientes objetivo, `_icp_a_apollo_filtros()` detecta "import" y "export" y **agrega "Import and Export" como industria objetivo** — cuando en realidad debería ser una industria a **excluir** (es competencia directa de GBS).

**Falta:**
- Campo de "competidores" no se mapea a exclusiones del pool search (solo `icp_criterios_descarte` se usa, no el campo `competidores` del estado)
- No hay flujo explícito de "Borrador → Revisar → Aprobar → Master". El botón guarda en borrador pero no promueve a master automáticamente. Hay que hacerlo manualmente.
- Falta campo "Buyer Persona" como persona específica (no solo cargo) — la UI tiene cargos pero no "María, 38 años, Gerenta de Logística"
- Falta campo "TIR" (tasa interna de retorno / prioridades) explícito
- El campo `icp_criterios_descarte` no diferencia entre "industria a excluir" vs "cargo a excluir" vs "tamaño a excluir"

**UX problema:**
- El prompt de generación del ICP hace dos llamadas a `docs_content` (líneas 352 y 360 del prompt) — está duplicado en `build_icp_system_prompt()`
- No hay indicador visual claro de si el ICP está "aprobado" o "en borrador"

---

## Paso 5 — Bases y Mensajería

### Dónde está en el código
- Función: `tab_bases_apollo(path, est)` — línea ~3256
- Funciones auxiliares: `_clasificar_base()`, `_apollo_buscar()`, `_snov_buscar()`, `_apollo_a_df()`, `_snov_a_df()`, `_acumular_base()`, `_detectar_id_col()`
- Pool de bases: líneas ~3320-3575

### Estado actual (post-fixes de 2026-05-29)

Los siguientes bugs fueron **corregidos** en el commit `5982508`:
- ✅ Upload al pool ya no crashea con "Apollo ID KeyError" (usa `_detectar_id_col()`)
- ✅ Búsqueda por cargo usa palabras individuales, no frases exactas
- ✅ Existe multiselect de "Industrias a EXCLUIR"
- ✅ Hay debug counter (Total base | Tras filtro cargo | Resultado final)

### Qué funciona

**Sección Pool (local):**
- Upload de bases Apollo/Snov al pool acumulado con deduplicación automática
- Preview del pool con columnas detectadas
- Filtros: cargo por palabras, industrias incluir/excluir, países, empleados mínimos
- Descarga del resultado filtrado + descarga del pool completo
- Botón "Cargar filtros desde ICP"

**Sección Calificación manual:**
- Upload de CSV/XLSX
- Clasificación en 5 tiers con 8 columnas `CP_*`
- Stats visuales por tier
- Filtro por tier en la tabla
- Descarga Excel con colores por tier
- Generación de mensajería por segmento con Claude

### Qué falta o falla (problemas actuales)

#### Críticos

**1. Apollo API no filtra industrias (limitación de la API)**
- `q_organization_keyword_tags` es boost de relevancia, no filtro
- Apollo no expone `organization_industry_tag_ids` en la API pública
- **Consecuencia:** Se siguen viendo empresas de industrias incorrectas en resultados de la API
- **Fix pendiente:** El filtrado real de industria debe hacerse post-descarga, sobre el DataFrame

**2. La sección de búsqueda API (Apollo/Snov) y la sección Pool son confusas**
- La UI tiene 3 subsecciones diferentes para "conseguir contactos" y no está claro cuándo usar cada una
- El usuario no sabe si la API busca en Apollo directamente, si guarda al pool, o si son flujos separados
- **Consecuencia:** Confusión operativa → el usuario termina duplicando trabajo

**3. No hay separación company_score vs contact_score**
- `_clasificar_base()` mezcla el score del contacto (cargo) con el de la empresa (industria, empleados)
- Un contacto con cargo perfecto en empresa incorrecta obtiene Tier B — pero debería separarse
- Un contacto con cargo incorrecto en empresa perfecta también obtiene score bajo — cuando la empresa podría ser valiosa con otro contacto

**4. Snov.io no probado en producción**
- `_snov_buscar()` usa endpoint `/v2/api/search-contacts` cuya estructura de respuesta es especulativa
- `_snov_a_df()` usa rutas de datos como `c.get("firstName", c.get("first_name", ""))` sin validar que el endpoint existe
- No hay manejo de error visible para el usuario si Snov falla

**5. La sección API Apollo solo descarga ~100 contactos**
- La paginación existe pero el código actual no usa múltiples páginas activamente en el flujo UI
- No hay contador de "total disponible en Apollo" antes de descargar
- El usuario no puede saber cuántos resultados hay antes de ejecutar

#### Importantes

**6. Filtro de competidores no llega al pool search**
- `est.get("competidores")` no se usa en la búsqueda del pool
- Solo `icp_criterios_descarte` e `ind_excluidas` se usan
- Consecuencia: empresas competidoras pueden aparecer en resultados del pool

**7. `_df_search in dir()` es un hack**
```python
data=_df_search.to_csv(...) if '_df_search' in dir() else b''
```
Esto falla si `_df_search` no está en scope — lo correcto es usar `st.session_state`

**8. El pool se guarda en `BASES_APOLLO/{nombre_cliente}/` en la raíz del proyecto**
- No está dentro de `CLIENTES/{ID}/` — esto es intencional (bases pesadas fuera de la carpeta del cliente)
- Pero `_base_dir = path.parent.parent` (sube dos niveles desde CLIENTES/{ID}/) — si la estructura cambia, esto rompe

**9. Calificación manual no guarda resultado en la carpeta del cliente**
- El usuario califica, ve los resultados, pero para que queden guardados tiene que descargar el Excel/CSV manualmente
- No hay "auto-guardar resultado de calificación en 08_BASES_Y_CALIFICACION/"

**10. Mensajería por segmento requiere calificación previa**
- Si el usuario no calificó con ICP, los segmentos están vacíos y no se pueden generar mensajes
- No hay fallback para generar mensajes sin calificación

---

## Errores de experiencia de usuario (UX)

1. **El tab "Bases y Mensajería" hace demasiado** — debería dividirse en al menos 2 subtabs: "Bases" y "Mensajería"
2. **Los filtros del pool no se pre-llenan del ICP automáticamente al cargar el tab** — hay que presionar el botón "Cargar filtros desde ICP" explícitamente
3. **No hay indicador de qué tiene el pool actualmente** hasta que bajes al expander (que está collapsed por default)
4. **El botón "Filtrar base" cambia a "Buscar en base" sin consistencia** — los textos varían entre versiones
5. **La tabla de resultados solo muestra 500 filas** — en bases de 30k contactos, no sabes qué hay más abajo
6. **Después de descargar no hay feedback** de si el archivo se guardó correctamente en la carpeta del cliente
7. **No hay botón de "Guardar configuración de filtros"** — si cierras y vuelves, los filtros del pool se resetean

---

## Errores de arquitectura

1. **`app.py` monolítico (5,530 líneas)** — las funciones de Apollo, Snov, clasificación, mensajería y UI están todas en el mismo archivo. Dificulta el mantenimiento y el testing.
2. **`_icp_a_apollo_filtros()` tiene lógica de negocio mezclada con UI** — debería estar en un módulo separado `modules/apollo.py`
3. **Las funciones de API (`_apollo_buscar`, `_snov_buscar`) están anidadas en el flujo UI** — deberían ser funciones independientes testeables
4. **No hay tests** — ninguna función tiene tests unitarios. Los bugs se descubren en producción.
5. **La función `_clasificar_base()` itera fila por fila con `iterrows()`** — para bases de 30k+ contactos, esto es lento (O(n)). Debería vectorizarse con pandas.
6. **La función `grabar_y_transcribir()` usa sounddevice** — requiere hardware de audio en el servidor, que no es el caso en despliegue.

---

## Riesgos de datos

1. **Las bases Apollo/Snov son datos personales** de contactos — nunca deben subirse a GitHub, logs o screenshots. Están gitignoreadas.
2. **`estado_cliente.json` es la fuente de verdad del ICP** — si se corrompe, se pierde toda la configuración del cliente. No hay backup automático.
3. **El ICP aprobado (`icp_master.md`)** no debe modificarse sin confirmación de Francisca — es el documento de referencia para todos los SDRs.
4. **Los archivos de mensajería generados** (`05_MENSAJERIA_COMERCIAL/`) deben ser revisados antes de enviar — son borradores generados por IA.

---

## Recomendaciones prioritarias

1. **Corto plazo (P0):** Arreglar `_icp_a_apollo_filtros()` — el bug del "import/export" puede estar filtrando mal industrias para clientes de logística.
2. **Corto plazo (P0):** Implementar filtro post-descarga de industrias en la sección API Apollo (el pool search ya lo tiene).
3. **Mediano plazo (P1):** Separar `company_score` de `contact_score` en `_clasificar_base()`.
4. **Mediano plazo (P1):** Probar y documentar Snov.io API en producción con credenciales reales.
5. **Largo plazo (P2):** Refactorizar `app.py` — mover funciones de API a `modules/apollo.py` y `modules/snov.py`.
6. **Largo plazo (P2):** Vectorizar `_clasificar_base()` con pandas para escalar a 100k+ contactos.

---

*Auditoría realizada mediante lectura del código fuente — 2026-05-29*
