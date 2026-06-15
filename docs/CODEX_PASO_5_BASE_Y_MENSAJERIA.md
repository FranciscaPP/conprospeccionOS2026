# Diseño del Paso 5 — Bases y Mensajería
**Fecha:** 2026-05-29
**Propósito:** Especificación funcional del Paso 5 del MVP Setup para que Codex pueda implementarlo correctamente.

---

## Contexto

El Paso 5 es el núcleo operativo del MVP Setup. Después de que el ICP está validado (Paso 4), el Paso 5 permite:
1. Conseguir bases de contactos (Apollo, Snov, o subida manual)
2. Filtrar según el ICP
3. Calificar contactos
4. Exportar bases segmentadas
5. Generar mensajería por segmento

Este documento describe el diseño **ideal** de cómo debería funcionar, los problemas actuales y las prioridades de implementación.

---

## 1. Principios fundamentales

### Apollo y Snov son fuentes SEPARADAS

| Aspecto | Apollo.io | Snov.io |
|---------|-----------|---------|
| API | `POST /api/v1/mixed_people/api_search` | `POST /v2/api/search-contacts` |
| Auth | Header `x-api-key` | OAuth2 token temporal |
| Filtros | person_titles, seniorities, locations, employees | positions, industries, countries |
| Columnas clave | Apollo ID, Person LinkedIn Url, # Employees | Snov ID, position, companySize |
| Emails en API | NO (requiere créditos extra) | Parcial |
| Industria como filtro | NO (solo relevance boost) | Sí (campo directo) |
| Dedup key | Apollo ID → Email → LinkedIn URL | Snov ID → Email |
| Pool local | `BASES_APOLLO/{cliente}/apollo_all.csv` | `BASES_SNOV/{cliente}/snov_all.csv` |

**No mezclar la lógica de parseo, filtros ni columnas** entre Apollo y Snov.

### Separar company_score de contact_score

Un contacto excelente en una empresa incorrecta ≠ un contacto mediocre en la empresa perfecta.

```
company_score:
  + industria coincide con ICP         → +4 pts
  + tamaño coincide con ICP            → +2 pts
  + país coincide con ICP              → +2 pts
  - empresa es cliente actual          → Excluir
  - empresa es competidor              → Excluir
  - industria en lista de exclusión    → Excluir

contact_score:
  + macro_cargo coincide con ICP       → +4 pts
  + cargo específico coincide con ICP  → +2 pts
  + keywords del título coinciden      → +1 pt
```

Tier final = combinación de ambos:
- Tier A: company ≥ 6 AND contact ≥ 5
- Tier B: (company ≥ 4 AND contact ≥ 3) OR (company ≥ 6 AND contact ≥ 1)
- Tier C: company ≥ 2 AND contact ≥ 1
- Excluir: cualquier flag de exclusión activo
- Sin match: no se pudo clasificar

---

## 2. Flujo ideal — Apollo.io

### 2.1 Flujo API (búsqueda en tiempo real)

```
1. ICP validado está cargado
   ↓
2. Sistema auto-genera filtros recomendados desde ICP:
   - person_titles: [lista de cargos]
   - person_seniorities: [c_suite, director, manager...]
   - person_locations: [países/ciudades]
   - organization_num_employees_ranges: [rangos]
   - person_departments: [optional, desde ICP]
   ↓
3. Usuario ve filtros en UI y puede EDITAR:
   - Agregar/quitar cargos (text + chips)
   - Agregar/quitar países
   - Seleccionar seniority (multiselect con valores reales de Apollo)
   - Seleccionar tamaños de empresa
   - Agregar/quitar industrias A INCLUIR (post-filtro, no parámetro API)
   - Agregar/quitar industrias A EXCLUIR (post-filtro)
   ↓
4. Botón "Estimar resultados" → hace llamada con per_page=1, lee pagination.total_entries
   Muestra: "Apollo tiene ~X contactos con estos filtros"
   ↓
5. Usuario define cantidad objetivo (100, 500, 1000...)
   ↓
6. Botón "Descargar contactos"
   → Paginación automática (hasta N contactos)
   → Post-filtro de industrias (incluir/excluir) sobre el DataFrame resultante
   → Muestra: "X traídos de Apollo, Y tras filtro industria, Z nuevos al pool"
   ↓
7. Resultado se acumula en BASES_APOLLO/{cliente}/apollo_all.csv (dedup por Apollo ID)
   ↓
8. Contadores visibles:
   - Total encontrado en Apollo
   - Total descargado
   - Total nuevo (deduplicado)
   - Total con email
   - Total industria correcta (post-filtro)
```

### 2.2 Flujo Pool local (bases ya descargadas)

```
1. Usuario sube CSV/XLSX exportado desde Apollo
   → Preview automático: N filas, columnas detectadas
   ↓
2. Sistema detecta columna de dedup (Apollo ID → Email → LinkedIn URL)
   → Muestra: "Clave de dedup: {columna}"
   ↓
3. Se acumula en pool (dedup)
   → Muestra: "X nuevos, Y duplicados, pool total: Z"
   ↓
4. [FILTRAR] Usuario define filtros:
   - Palabras clave de cargo (word-level, no phrase)
   - Industrias incluir (multiselect)
   - Industrias excluir (multiselect)
   - Países
   - Empleados mínimos
   ↓
5. [FILTRAR BASE] → resultado con debug counter
   - "Total pool: X | Tras filtro cargo: Y | Tras industrias: Z | Resultado: W"
   ↓
6. Descargar resultado filtrado
```

### 2.3 Filtros Apollo reutilizables

Los filtros usados deben guardarse en `07_APOLLO_Y_BUSQUEDAS/busqueda_1_prioritaria.md` con:
- Cargos usados
- Seniorities
- Países
- Tamaños
- Industrias incluidas/excluidas
- Resultado: N contactos, fecha

---

## 3. Flujo ideal — Snov.io

### 3.1 Diferencias con Apollo que impactan el flujo

- Snov.io SÍ soporta filtro de industria como parámetro directo (no solo boost)
- Snov.io devuelve menos campos por contacto
- La columna de dedup es `Snov ID` o `email`
- No hay `Apollo ID` ni `Person Linkedin Url` necesariamente

### 3.2 Flujo API Snov

```
1. ICP validado cargado
   ↓
2. Sistema genera filtros para Snov:
   - positions: [cargos del ICP, máx 5]
   - industries: [industrias del ICP, máx 5]
   - countries: [países del ICP, máx 5]
   ↓
3. Usuario puede editar filtros
   ↓
4. Botón "Buscar en Snov"
   → Llama OAuth → obtiene token
   → Llama /v2/api/search-contacts
   → Si falla: muestra error específico (no silenciar)
   ↓
5. Resultado se acumula en BASES_SNOV/{cliente}/snov_all.csv
   ↓
6. Contadores idénticos a Apollo
```

### 3.3 Flujo subida manual Snov

```
1. Usuario sube CSV/XLSX exportado desde Snov
   ↓
2. Preview automático + columnas detectadas
   ↓
3. Detecta dedup key (Snov ID → email)
   ↓
4. Acumula en pool Snov
   ↓
5. [FILTRAR] → filtros por cargo (word-level), industrias, país, empleados
   ↓
6. Resultado filtrado + descarga
```

---

## 4. Field mapping recomendado

### Columnas estándar Apollo (exportación CSV del sitio)

| Columna Apollo | Campo interno | Tipo |
|----------------|--------------|------|
| First Name | first_name | str |
| Last Name | last_name | str |
| Title | title | str |
| Company | company | str |
| Company Name for Emails | company_email_name | str |
| Email | email | str |
| Email Status | email_status | str |
| Mobile Phone | mobile_phone | str |
| Work Direct Phone | direct_phone | str |
| Person Linkedin Url | linkedin_person | str |
| Company Linkedin Url | linkedin_company | str |
| Website | website | str |
| Company Address | address | str |
| City | city | str |
| State | state | str |
| Country | country | str |
| # Employees | employees | int |
| Industry | industry | str |
| Keywords | keywords | str |
| Apollo ID | apollo_id | str |

### Columnas estándar Snov (exportación CSV del sitio)

| Columna Snov | Campo interno | Tipo |
|--------------|--------------|------|
| First Name | first_name | str |
| Last Name | last_name | str |
| Position | title | str |
| Company | company | str |
| Email | email | str |
| Phone | phone | str |
| LinkedIn URL | linkedin_person | str |
| Company Website | website | str |
| Industry | industry | str |
| Company Size | employees | str |
| Country | country | str |
| City | city | str |

### Detección automática de columnas

La función `_detectar_cols_base()` ya detecta muchas variaciones. Debe extenderse para cubrir Snov específicamente:

```python
def _detectar_cols_base(df):
    cols_l = {c.lower().strip(): c for c in df.columns}
    def _c(*ns):
        for n in ns:
            if n in cols_l: return cols_l[n]
        return None
    return {
        "title":    _c("title", "job title", "position", "cargo"),  # Snov usa "position"
        "employees":_c("# employees", "employees", "company size", "companysize"),  # Snov usa "company size"
        "linkedin_p":_c("person linkedin url", "linkedin url", "linkedin"),
        # ... etc
    }
```

---

## 5. Scoring recomendado (company + contact)

### Implementación actual (en `_clasificar_base()`)

```python
score = 0
if macro_cargo != "Sin clasificar": score += 3   # company: industria
if cargo_esp   != "—":             score += 1   # contact: cargo específico
if macro_ind   != "Sin clasificar": score += 3   # company: macro industria
if pais_ok:                         score += 2   # company: país
if kw_match:                        score += 1   # contact: keyword
# Máximo teórico: 10 puntos

Tier A: ≥7, Tier B: ≥4, Tier C: ≥2, Sin match: <2
```

### Scoring recomendado (separado)

```python
# COMPANY SCORE
company_score = 0
if macro_ind != "Sin clasificar":   company_score += 4   # industria match
if pais_ok:                          company_score += 2   # país match
if tamano_ok:                        company_score += 2   # tamaño match
# Flags de exclusión
if empresa_excluida or industria_excluida: tier = "❌ Excluir"
# Máximo: 8 pts

# CONTACT SCORE
contact_score = 0
if macro_cargo != "Sin clasificar": contact_score += 4   # nivel jerárquico match
if cargo_esp   != "—":             contact_score += 2   # cargo específico match
if kw_match:                        contact_score += 1   # keyword match
# Máximo: 7 pts

# TIER COMBINADO
if company_score >= 6 and contact_score >= 5: tier = "🟢 Tier A"
elif (company_score >= 4 and contact_score >= 3) or \
     (company_score >= 6 and contact_score >= 1): tier = "🟡 Tier B"
elif company_score >= 2 and contact_score >= 1: tier = "🟠 Tier C"
else: tier = "⚫ Sin match"
```

---

## 6. Exclusiones

### Exclusiones de competidores

```python
# Fuentes de exclusión:
#   est.get("competidores")          → empresas competidoras
#   est.get("clientes_actuales")     → clientes ya activos (no prospectar)
#   _sb_ind_excl                     → industrias a excluir (en pool search)

# Aplicar en _clasificar_base():
competidores_excl = _parsear_lista_icp(icp.get("competidores", ""))
clientes_actuales_excl = _parsear_lista_icp(icp.get("clientes_actuales", ""))

excluida_competidor = bool(competidores_excl and _match_keywords(empresa, competidores_excl))
excluida_cliente = bool(clientes_actuales_excl and _match_keywords(empresa, clientes_actuales_excl))

if excluida_competidor or excluida_cliente:
    tier = "❌ Excluir"
    resultado["CP_Motivo_Exclusion"] = "Competidor" if excluida_competidor else "Cliente actual"
```

### Exclusiones de industria en pool search

Ya implementadas en el pool search. Pendiente: propagar estas exclusiones también a la sección de calificación manual.

---

## 7. Cómo generar filtros Apollo editables

### Estado actual

El botón "Cargar desde ICP" en el pool search ya rellena los filtros. La sección de API Apollo también tiene un botón similar.

### Diseño recomendado

```python
# 1. Auto-generar desde ICP al abrir el tab (no esperar botón)
if not st.session_state.get(f"apollo_filtros_init_{path.name}"):
    filtros = _icp_a_apollo_filtros(est)
    st.session_state[f"apollo_cargos_{path.name}"] = _cargos_icp[:10]
    st.session_state[f"apollo_seniority_{path.name}"] = filtros["seniority"]
    st.session_state[f"apollo_tamano_{path.name}"] = filtros["tamano"]
    st.session_state[f"apollo_industrias_{path.name}"] = filtros["industrias"]
    st.session_state[f"apollo_excluir_{path.name}"] = filtros["ind_excluidas"]
    st.session_state[f"apollo_filtros_init_{path.name}"] = True

# 2. Mostrar filtros editables (siempre, no en expander oculto)
col_f1, col_f2 = st.columns(2)
with col_f1:
    cargos_edit = st.text_area("Cargos (uno por línea)", ...)
    seniority_edit = st.multiselect("Seniority", options=list(APOLLO_SENIORITY.keys()), ...)
with col_f2:
    industrias_incl = st.multiselect("Industrias a INCLUIR (post-filtro)", APOLLO_INDUSTRIAS, ...)
    industrias_excl = st.multiselect("Industrias a EXCLUIR (post-filtro)", APOLLO_INDUSTRIAS, ...)

tamano_edit = st.multiselect("Tamaño empresa", options=list(APOLLO_TAMANOS.keys()), ...)
paises_edit = st.text_input("Países", ...)

# 3. Botón ESTIMAR antes de DESCARGAR
if st.button("🔍 Estimar resultados"):
    result_est = _apollo_buscar(cargos, paises, por_pagina=1)
    total = result_est.get("pagination", {}).get("total_entries", "?")
    st.info(f"Apollo tiene ~{total:,} contactos con estos filtros")

# 4. Botón DESCARGAR con N objetivo
n_objetivo = st.number_input("¿Cuántos contactos descargar?", 100, 5000, 500)
if st.button("⬇️ Descargar contactos"):
    # Paginación hasta n_objetivo
    # Post-filtro industrias
    # Acumular en pool
```

---

## 8. Exportaciones requeridas

### Por cliente, en `CLIENTES/{ID}/08_BASES_Y_CALIFICACION/`

```
08_BASES_Y_CALIFICACION/
├── 01_originales/
│   └── base_apollo_raw_{fecha}.csv           ← Sin calificar
├── 02_calificadas/
│   └── base_calificada_{fecha}.xlsx          ← Con columnas CP_* y colores
├── 03_para_ghl/
│   ├── prioridad_1_TierA_{fecha}.csv         ← Solo Tier A
│   ├── prioridad_2_TierB_{fecha}.csv         ← Solo Tier B
│   └── prioridad_3_TierC_{fecha}.csv         ← Solo Tier C
├── 04_para_snov/
│   └── campana_snov_{fecha}.csv              ← Campos normalizados para Snov
├── 05_para_whatsapp/
│   └── base_whatsapp_{fecha}.csv             ← Con mobile_phone
├── 06_por_sdr/
│   ├── sdr_florencia_{fecha}.csv
│   └── sdr_mariana_{fecha}.csv
└── 99_descartados/
    └── descartados_{fecha}.csv               ← Tier Excluir
```

### Exportaciones adicionales

| Archivo | Contenido |
|---------|-----------|
| `base_tier_A.xlsx` | Solo Tier A, colores, todas las columnas |
| `base_tier_B.xlsx` | Solo Tier B |
| `campana_{fecha}.csv` | Solo contactos del resultado filtrado (para campañas) |
| `pool_completo_{cliente}.csv` | Todo el pool sin filtros |
| `mensajeria_{segmento}_{fecha}.txt` | Mensajes generados por Claude |

### Contadores que deben mostrarse siempre

```
Pool: {N} contactos totales | {N} con email
Filtro: Total base: {N} | Tras cargo: {N} | Tras industria: {N} | Final: {N}
Calificación: Tier A: {N} | Tier B: {N} | Tier C: {N} | Excluir: {N} | Sin match: {N}
```

---

## 9. Mensajería por segmento

### Flujo actual

1. Calificar base → genera columnas `CP_Macro_Cargo` y `CP_Macro_Industria`
2. Para cada combinación única (macro_cargo × macro_industria), botón "Generar mensajes"
3. Claude genera 3 emails con subject
4. Descarga como TXT + Excel

### Mejoras recomendadas

- Guardar mensajes generados en `05_MENSAJERIA_COMERCIAL/mensajes_{segmento}_{fecha}.md`
- Permitir editar los mensajes antes de descargar
- Mostrar preview de los 3 mensajes en la UI
- Agregar "estilo de mensaje" editable (formal, conversacional, directo)
- Agregar campo de personalización (variable `{{nombre}}`, `{{empresa}}`, etc.)
- Conectar a campañas en Snov directamente (si API Snov está configurada)

---

## 10. Pantallas y componentes que deben existir

### Estructura recomendada del Tab 4

```
Tab 4: Bases y Mensajería
├── [ICP Status] — barra de estado del ICP
│
├── Subtab A: Apollo.io
│   ├── Sección 1: Pool acumulado (stats + upload)
│   ├── Sección 2: Filtrar pool
│   └── Sección 3: Buscar en API Apollo (si API key configurada)
│
├── Subtab B: Snov.io
│   ├── Sección 1: Pool acumulado Snov
│   ├── Sección 2: Filtrar pool Snov
│   └── Sección 3: Buscar en API Snov (si credenciales configuradas)
│
├── Subtab C: Calificar base
│   ├── Upload manual de CSV/XLSX
│   ├── Botón "Calificar con ICP"
│   ├── Stats de tier
│   └── Tabla filtrada por tier
│
└── Subtab D: Mensajería
    ├── Segmentos detectados (macro_cargo × macro_industria)
    ├── Para cada segmento: botón "Generar mensajes"
    └── Vista y descarga de mensajes
```

---

## 11. Qué debe quedar guardado por cliente

```
CLIENTES/{ID}/
├── 04_ICP_ESTRATEGIA/
│   ├── icp_master.md                    ← ICP aprobado (no editar sin confirmación)
│   ├── criterios_prioridad.md
│   ├── criterios_descarte.md
│   └── exclusiones_apollo.md           ← Industrias y empresas a excluir
│
├── 07_APOLLO_Y_BUSQUEDAS/
│   ├── busqueda_1_prioritaria.md       ← Filtros guardados de búsqueda 1
│   ├── busqueda_2_amplia.md
│   └── keywords_apollo.md
│
├── 08_BASES_Y_CALIFICACION/
│   ├── 01_originales/
│   ├── 02_calificadas/                 ← Bases calificadas con CP_*
│   ├── 03_para_ghl/                    ← Por tier/prioridad
│   ├── 04_para_snov/
│   └── 06_por_sdr/
│
└── 05_MENSAJERIA_COMERCIAL/
    ├── mensajes_{segmento}_v1.md
    └── mensajes_aprobados_{segmento}.md
```

### Qué NO debe subirse a GitHub

- Todo el contenido de `BASES_APOLLO/` y `BASES_SNOV/` (ya en .gitignore)
- Todo `CLIENTES/` (ya en .gitignore)
- Los archivos `.csv`, `.xlsx` generados (ya en .gitignore)
- Las claves de API del `.env`

---

## 12. Estados de la interfaz que deben mostrarse

| Estado | Indicador visual |
|--------|-----------------|
| ICP no definido | Warning naranja + enlace al tab ICP |
| ICP cargado | Success verde con resumen de campos |
| Pool vacío | Info azul: "Sin contactos en el pool. Sube archivos." |
| Pool con datos | Métricas: total, con email, sin email |
| Cargando base | Spinner con "Leyendo {N} filas..." |
| Calificando | Spinner con "Clasificando {N} contactos..." |
| Error de API | Error rojo con código HTTP y mensaje específico |
| API no configurada | Info gris: "APOLLO_API_KEY no configurada" |
| Descarga lista | Success con contadores (total, nuevo, duplicado) |

---

*Documento de diseño — 2026-05-29*
