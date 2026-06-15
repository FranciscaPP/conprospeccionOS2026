# Diagnóstico técnico — Portal Cliente v2 (paralelo, sin tocar lo actual)

> **Para el agente que construye v2 (Codex u otro).** Documento auto-contenido.
> Última actualización: 2026-06-05. Repo `FranciscaPP/conprospeccion-os`, rama `master`.
> Supabase proyecto `gdlncvbvhbfjonbnmxfl`. Stack actual: Streamlit + Supabase (PostgREST) + GHL.
>
> **Objetivo v2:** portal nuevo paralelo (nuevo login, nuevo link, nueva navegación y estética)
> reutilizando los **mismos datos reales** y la **misma lógica de negocio**. Primero GBS, luego
> Tiresias, Clickie y otros. **No modificar el portal actual.**
>
> **Reglas duras del proyecto (heredadas):** responder/UI en español; sin emojis en la UI;
> gráficos en HTML/CSS (Plotly/Altair NO funcionan en Streamlit Cloud); el cliente **nunca** ve
> el SDR ni responsables internos; **nunca** exponer nombres de plataformas (GHL/GoHighLevel/
> Snov/Apollo/Supabase/GitHub) al cliente; un solo `.env` en la raíz.

---

## ⚠️ DIRECTRICES DEL PROYECTO PARA v2 (leer antes que nada)

1. **Hacer SOLO GBS primero, y que quede perfecto.** El foco es el **frontend**: hermoso,
   entendible, optimizado, consistente. NO trabajar en otros clientes todavía.
2. **Los datos de GBS se mantienen DEMO / inventados, tal cual están hoy.** NO realizar datos,
   NO conectar a fuentes reales nuevas, NO inicializar tablas. Reutilizar `shared/gbs_data.cargar_dataset()`
   y las funciones de carga actuales **sin cambiarlas**. El objetivo de v2 es la **estética y UX**,
   no el origen de los datos.
3. **Recién cuando los 5 dashboards de GBS estén aprobados**, se replica a Tiresias/Clickie/otros,
   y SOLO ahí se actualizan/realizan los datos de cada cliente. No antes.
4. **No tocar el portal actual** (`dashboard/`). v2 es paralelo, app/deploy/link aparte.

> En resumen: v2 = **front-end nuevo y hermoso para GBS con los mismos datos demo de hoy.**
> Todo lo que en este documento mencione "datos reales", "capa de datos real" o "intelligence_source:
> supabase" es para la **fase posterior de replicación**, NO para el v2 inicial de GBS.

---

## 1. Mapa de archivos

### Dashboards GBS (rutas exactas)
| # | Dashboard | Archivo | Líneas | Tipo de datos |
|---|---|---|---|---|
| 1 | Onboarding | `dashboard/pages/14_GBS_Onboarding.py` | 387 | Form → escribe DB |
| 2 | Validación Reuniones | `dashboard/pages/12_GBS_Validacion_Reuniones.py` | 404 | **Datos reales** + escribe |
| 3 | Reporte Mensual | `dashboard/pages/15_GBS_Reporte_Mensual.py` | 135 | Demo + 1 real + PDF |
| 4 | Intelligence Insight | `dashboard/pages/11_GBS.py` | 1249 | Mayormente demo |
| 5 | Playbook SDR | `dashboard/pages/13_GBS_Playbook_SDR.py` | 725 | **100% estático** |

### Archivos compartidos (`shared/`)
- `shared/config.py` — credenciales (Supabase, GHL, Telegram), `portal_passwords()`, `ghl_tokens()`, `master_passwords()`
- `shared/seguimiento.py` — acceso a `seguimiento_reuniones` (3 capas) + recálculo + historial + `COLUMNAS_CLIENTE`
- `shared/validacion.py` — motor de reglas puro (sin I/O)
- `shared/validacion_ui.py` — componentes HTML del bloque de validación (banner, resumen, chips, barra avance)
- `shared/planes.py` — tier base/premium por cliente (`plan_de`)
- `shared/metas.py` — metas contractuales por cliente (`meta_de`)
- `shared/kpis.py` — catálogo de 15 KPIs + `compute_kpis`
- `shared/gbs_data.py` — **dataset demo** (seed 42) — NO es real
- `shared/pdf_report.py` — generación de PDF con fpdf2 (`construir_pdf`)
- `shared/gbs_brand.py` — paleta + tokens semánticos + top-5 cargos/industrias de GBS
- `dashboard/portal_auth.py` — **auth del portal cliente** (login + token de sesión + nav)
- `dashboard/master_auth.py` — auth interna del equipo (Francisca/Yanina)

### Assets (`dashboard/assets/`)
`gbs_logo.png`, `tiresias_logo.png`, `clickie_logo.png`, `conprospeccion_logo.png`, `cp_b64.txt`, `trs_b64.txt`.
Se cargan vía `img_b64(fname, h)` en `portal_auth.py`.

### Equivalentes Tiresias / Clickie
| Cliente | Indicadores | Validación | Playbook | Interno |
|---|---|---|---|---|
| Tiresias | `dashboard/pages/3_Tiresias.py` | `dashboard/pages/4_Tiresias_Validacion_Reuniones.py` | `dashboard/pages/5_Tiresias_Playbook_SDR.py` | `dashboard/pages/10_Tiresias_Interno.py` |
| Clickie | `dashboard/pages/6_Clickie.py` | `dashboard/pages/7_Clickie_Validacion_Reuniones.py` | `dashboard/pages/8_Clickie_Playbook_SDR.py` | — |

> **HALLAZGO CRÍTICO:** Tiresias y Clickie usan tablas legacy de 2 campos
> (`tiresias_seguimiento`, `clickie_seguimiento` → `status_comercial, etapa_comercial`).
> **Solo GBS** (y el Seguimiento interno `dashboard/pages/1_Seguimiento_Reuniones.py`) usan el
> modelo de 3 capas `seguimiento_reuniones`. Para replicar v2 a Tiresias/Clickie hay que
> **migrar/inicializar** sus filas en `seguimiento_reuniones`.

---

## 2. Datos por dashboard

### Validación Reuniones (12) — DATOS REALES
- **Vista:** `vw_reuniones_semana` (filtrada `cliente_slug=eq.gbs`)
- **Tabla:** `seguimiento_reuniones` (3 capas)
- **Endpoints REST:**
  - `GET /rest/v1/vw_reuniones_semana?select=*&cliente_slug=eq.gbs&fecha=gte.{fi}&fecha=lte.{ff}&order=fecha.asc,hora.asc`
  - `GET /rest/v1/seguimiento_reuniones?select={COLUMNAS_CLIENTE}&cliente_slug=eq.gbs`
  - `PATCH /rest/v1/reuniones?id=eq.{rid}` (body `{"estado_validacion": ...}`)
  - `POST /rest/v1/seguimiento_reuniones` (upsert `Prefer: resolution=merge-duplicates`)
  - `PATCH /rest/v1/seguimiento_reuniones?reunion_id=eq.{rid}`
  - `POST /rest/v1/meeting_status_history`
  - `PUT https://services.leadconnectorhq.com/opportunities/{opp_id}` (GHL — header `Version: 2021-07-28`)
- **Lee:** `val_estado_cp, bant_cp, comentario_cp, val_estado_cli, bant_cli, comentario_cli, val_estado_final, final_override, estado_comercial, motivo_no_validez, status_reunion`
- **Escribe (cliente):** `val_estado_cli, bant_cli, comentario_cli, estado_comercial, motivo_no_validez, validated_by_cli, validated_cli_at` + flags vía `recalcular_final_y_flags`
- **Funciones de carga:** `cargar_reuniones(fi,ff)`, `cargar_seguimiento()`, `cargar_stages()`, `contar_validas_finales()`
- **Funciones de guardado:** `guardar_nivel()`, `recalcular_final_y_flags()`, `registrar_historial()`, `upd_validacion()`, `mover_ghl()`

### Intelligence Insight (11) — MIXTO (poco real, mucho demo)
- **Real:** `cargar_validacion_gbs()`:
  - `GET /rest/v1/reuniones?select=estado_validacion&cliente_slug=eq.gbs`
  - `GET /rest/v1/gbs_seguimiento?select=reunion_id,etapa_comercial` (legacy)
  - `GET /rest/v1/seguimiento_reuniones?cliente_slug=eq.gbs&flag_meta_countable=eq.true&select=reunion_id` (válidas oficiales)
- **Demo (seed 42):** todo el resto vía `shared.gbs_data.cargar_dataset(776)` — 784 contactos, 148 empresas, embudo, segmentos, hallazgos, recomendaciones, campañas. **Hardcodeado.**
- **Filtros:** Período, País, Industria, Cargo, Canal (sobre el DataFrame demo).

### Reporte Mensual (15) — DEMO + 1 dato real
- **Demo:** `cargar_dataset()` → `compute_kpis(df, "gbs", validas_final)`
- **Real:** `validas_final` (cuenta `val_estado_final` válida en `seguimiento_reuniones`)
- **Tabla config:** `reporte_config` (`cliente_slug, kpis, updated_at`) — KPIs elegidos
- **Genera:** PDF en memoria (`construir_pdf`), nombre `reporte_gbs_<periodo>.pdf`. No persiste archivo.

### Onboarding (14) — ESCRIBE, defaults GBS
- **Tabla:** `gbs_onboarding` (upsert `on_conflict="cliente"`, vía cliente `supabase-py`: `create_client`)
- **35 campos.** Defaults hardcodeados a GBS (web, ICP, diferenciadores, casos de éxito).
- Notifica a Telegram al guardar (`_notify_telegram`).

### Playbook (13) — 100% estático
Sin requests ni DB. 725 líneas de texto hardcodeado GBS. Solo `require_auth_client("gbs")` + `render_client_nav`.

### `gbs` hardcodeado (lugares exactos)
- `require_auth_client("gbs")` y `render_client_nav(..., "gbs")` en las 5 páginas
- `cliente_slug=eq.gbs` en queries de `11_GBS.py` y `12_GBS_Validacion_Reuniones.py`
- Tablas `gbs_onboarding`, `gbs_seguimiento`; `reporte_config?cliente_slug=eq.gbs`
- `_plan_de("gbs")`, `cargar_seg("gbs")`
- `import shared.gbs_data`, `import shared.gbs_brand`

---

## 3. Autenticación y acceso

- **Archivo:** `dashboard/portal_auth.py`
- **Login:** `require_auth_client(slug)` → si `st.session_state["portal_auth_<slug>"]`, pasa;
  si no, muestra el form y valida `_check_login()` contra `portal_passwords()[slug]`
  (de `.env`/`st.secrets`: `PORTAL_PASSWORD_GBS`, `PORTAL_PASSWORD_TIRESIAS`, `PORTAL_PASSWORD_CLICKIE`).
- **Sesión persistente:** token efímero en query params: `cp_s`=slug, `cp_k`=`sha256(slug:pwd:bucket)[:32]`,
  ventana de 30 min (`_TOKEN_WINDOW=1800`), acepta el bucket actual y el anterior. Sobrevive
  reconexiones del WebSocket de Streamlit Cloud. Nunca expone la contraseña.
- **Variables de sesión:** `portal_auth_<slug>` (bool), `admin_mode` (bypass interno desde el hub).
- **Navegación:** `_CLIENTS[slug]` define `session_key`, `logo_file` y `nav` (lista de tuplas
  `(label, path, tier)`); `render_client_nav` oculta el sidebar nativo y arma uno propio.
- **Links:** mismo dominio Streamlit; navegación con `st.switch_page()`. No hay link único por cliente:
  el cliente entra y loguea con su password de slug.
- **Riesgos de un login v2 paralelo:**
  - **App v2 separada** (otro entrypoint `app_v2.py`): NO comparte `session_state` → aislamiento limpio,
    sin riesgo. Puede reutilizar `portal_passwords()`. **Recomendado.**
  - **Páginas v2 en la misma app:** comparte `session_state` y el multipage nativo → riesgo de
    colisión de `session_key` y nav cruzada. **No recomendado.**
  - Password **compartido por cliente** (uno solo, sin usuarios individuales). Si v2 necesita
    usuarios distintos, hay que otra fuente de credenciales.

---

## 4. Validación Reuniones (detalle)

- **Reuniones:** de `vw_reuniones_semana` (vista sobre `reuniones`, alimentada por sync GHL).
- **Seguimiento / 3 capas:** `seguimiento_reuniones` (una fila por `reunion_id`).
- **Validación del cliente:** `val_estado_cli, bant_cli, comentario_cli, estado_comercial, motivo_no_validez`.
- **Evaluación Conprospección (CP):** `val_estado_cp, bant_cp, comentario_cp`.
- **Validez final:** `val_estado_final` (+ `final_override, flag_meta_countable, flag_disputa, flag_cliente_pendiente`).
- **Función que recalcula:** `recalcular_final_y_flags(reunion_id, cliente_slug)` en `shared/seguimiento.py`,
  que invoca `derivar_final()` de `shared/validacion.py`.
- **Campos visibles al cliente:** `shared/seguimiento.COLUMNAS_CLIENTE` =
  `reunion_id, cliente_slug, status_reunion, val_estado_cp, bant_cp, comentario_cp, val_estado_cli,
  bant_cli, comentario_cli, motivo_no_validez, val_estado_final, final_override, estado_comercial`.
- **Campos internos que el cliente NO debe ver:** `notas_internas, proximo_paso, validated_by_cp/cli/final,
  validated_*_at, ai_*, recording_url, transcript_url`, IDs técnicos, y el **SDR**
  (vive en `reuniones.sdr_slug` / `vw_reuniones_semana.sdr`; nunca se trae al portal).
- **Stages GHL:** `mover_ghl(opp_id, pipeline_id, stage_id)` cruza
  `_CLI_VAL_TO_CAT = {"valida":"reunion_valida","no_valida":"reunion_no_valida"}` contra
  `ghl_pipeline_stages` (cargado por `cargar_stages()`).
- **Al presionar Guardar (cliente):**
  1. `upd_validacion(rid, legacy)` → `reuniones.estado_validacion`
  2. `mover_ghl(opp_id, *stages[cat])` (si corresponde)
  3. `guardar_nivel(rid, "gbs", "cli", ...)` → upsert nivel cliente
  4. `PATCH seguimiento_reuniones` (estado_comercial, comentario_cli, motivo, validated_by_cli, validated_cli_at)
  5. `recalcular_final_y_flags(rid, "gbs")` → deriva final + flags
  6. `registrar_historial(...)` → `meeting_status_history`
  7. `st.cache_data.clear()` + `st.rerun()`
- **Reglas implementadas hoy (`derivar_final`):**
  - **El cliente manda:** cliente `valida` → final `valida` y cuenta meta, **sin importar el status**.
  - Cliente `no_valida` + CP `valida` con ≥2 BANT → `en_disputa` (revisión manual de Francisca).
  - Cliente `no_valida` (resto) → `no_valida`.
  - Sin validación de cliente: si status es no realizada (no_asistió/cancelada) → `no_valida`; resto → `pendiente`.
  - `final_override` (CP) manda sobre todo.
  - `flag_meta_countable = (val_estado_final == "valida")`.
- **Tests:** `tests/test_validacion.py` (9 casos), `tests/test_seguimiento_helpers.py`,
  `tests/test_dedup_reuniones.py`. Sin pytest: `python tests/<archivo>.py` → imprime `OK ...`.

---

## 5. Intelligence Insight (detalle)

- **Métricas reales:** válidas finales (`flag_meta_countable`), `estado_validacion` de `reuniones`, avance de meta.
- **Datos demo (`shared.gbs_data.cargar_dataset`, seed 42):** 784 contactos, 148 empresas, 21 respuestas,
  8 positivas (6 info + 2 agendadas), embudo, top industria/cargo/canal, hallazgos, recomendaciones, campañas.
- **Cálculos hardcodeados:** pesos `W_CARGO/W_IND` en `shared/gbs_brand.py`; los 8 registros `POS` y las
  tasas del embudo en `shared/gbs_data.py`.
- **Reutilizable:** estructura del embudo, helper `css_hbar()`, generadores de hallazgos/recomendaciones, tabs.
- **Específico de GBS:** `gbs_data` (dataset completo), `gbs_brand` (paleta, top-5), textos.
- **Para el v2 de GBS (AHORA):** **mantener el dataset demo** — reutilizar `shared.gbs_data.cargar_dataset()`
  y `compute_kpis()` tal cual. NO conectar a Supabase real. Solo rehacer la **presentación** (layout,
  componentes, estética). Los números deben verse exactamente iguales a hoy (784 contactos, etc.).
- **Para la fase posterior (replicación, NO ahora):** se puede crear `data/intelligence.py` que devuelva
  el DataFrame desde fuentes reales por cliente, manteniendo la misma interfaz que `cargar_dataset()`.

---

## 6. Reporte Mensual (detalle)

- **Generación:** `compute_kpis(df, "gbs", validas_final)` → `construir_pdf(nombre, periodo, seleccion, comp)`
  → `st.download_button` (PDF bytes en memoria).
- **KPIs:** catálogo de 15 en `KPI_CATALOGO` (`shared/kpis.py`); el cliente elige hasta 5 (`MAX_KPIS=5`).
- **Origen:** demo (`gbs_data`) salvo `validas` (real, `seguimiento_reuniones`).
- **Parametrizable por cliente:** `cliente_nombre`, `periodo`, selección persistida en `reporte_config`
  (ya tiene `cliente_slug`). Falta: dataset real por cliente; meta ya está en `shared/metas.py`.

---

## 7. Onboarding (detalle)

- **Campos:** 35 (ICP país/cargos/industrias/tamaño/descarte/adicional; marca; mensajería; proceso comercial;
  inteligencia comercial).
- **Guarda:** sí — `gbs_onboarding` (upsert `on_conflict="cliente"`).
- **Dinámico** (form persistente) con **defaults hardcodeados a GBS**.
- **Hardcode GBS:** nombre de tabla `gbs_onboarding`, valores default, textos con "GBS".
- Para v2 multicliente: tabla genérica `onboarding(cliente_slug, ...)` o `gbs_onboarding` renombrada/abstracta.

---

## 8. Playbook SDR (detalle)

- **Fijo:** todo (725 líneas de texto estático: objeciones, scripts, secuencias).
- **Depende del cliente:** nada dinámico hoy; contenido GBS escrito a mano.
- **Datos:** ninguno.
- **Reutilizable:** la estructura/acordeón; el contenido NO (por cliente).
- Para v2: contenido por cliente en `clients/<slug>/playbook.py` o tabla `playbook(cliente_slug, seccion, contenido)`.

---

## 9. Supabase — mapa

### Tablas relevantes
| Tabla | Uso | Clave cliente |
|---|---|---|
| `reuniones` | reuniones reales (sync GHL) | `cliente_slug` |
| `seguimiento_reuniones` | **validación 3 capas (modelo nuevo)** | `cliente_slug` |
| `meeting_status_history` | historial de cambios | `meeting_id` |
| `clientes` | maestro de clientes + `tier` | `slug` |
| `ghl_pipeline_stages` | mapeo de stages GHL | `cliente_slug` |
| `gbs_onboarding` | onboarding (solo GBS) | `cliente` |
| `reporte_config` | KPIs elegidos del PDF | `cliente_slug` |
| `gbs_seguimiento` / `tiresias_seguimiento` / `clickie_seguimiento` | **legacy 2 campos** | `reunion_id` |
| `snov_*` (7 tablas) | datos de campañas email | varios |

### Vistas relevantes
`vw_reuniones_semana` (la que consumen los portales), `vw_reuniones_del_dia`, `vw_reuniones_dashboard`,
+ ~30 vistas operativas/financieras/snov.

### Columnas `seguimiento_reuniones` (todas)
`reunion_id, cliente_slug, val_estado_cp, etapa_cp, bant_cp, status_cp, val_estado_cli, etapa_cli,
bant_cli, status_cli, interes_cli, motivo_cli, val_estado_final, etapa_final, bant_final, status_final,
updated_at, updated_by_cp, updated_by_cli, tipo_respuesta_cp, tipo_respuesta_cli, tipo_respuesta_final,
status_reunion, comentario_cp, validated_by_cp, validated_cp_at, comentario_cli, validated_by_cli,
validated_cli_at, motivo_no_validez, estado_comercial, proximo_paso, comentario_final, validated_final_by,
validated_final_at, final_override, flag_meta_countable, flag_disputa, flag_cliente_pendiente,
recording_url, transcript_url, ai_summary, ai_recommendation, ai_bant_detected, ai_confidence,
ai_evidence, notas_internas`

### Columnas `vw_reuniones_semana`
`id, opportunity_id, ghl_contact_id, cliente_slug, location_id, cliente, fecha, hora, sdr, contacto,
cargo, empresa, industria, pais, email, telefono, estado_reunion, estado_validacion, es_valida`

### Columnas `clientes`
`id, nombre_cliente, ghl_location_id, pais_principal, meta_mensual_reuniones, nombre, slug,
env_location_key, pais_prospeccion, estado_contrato, notas, created_at, updated_at, tipo_servicio,
tipo_meta, pago_setup, observaciones, tier`

### Relaciones por `cliente_slug`
`reuniones.cliente_slug` ↔ `clientes.slug` ↔ `seguimiento_reuniones.cliente_slug` ↔ `ghl_pipeline_stages.cliente_slug`.
`seguimiento_reuniones.reunion_id` → `reuniones.id`.

### Datos reales por cliente (al 2026-06-05)
| cliente | reuniones | seguimiento_reuniones (3 capas) |
|---|---|---|
| gbs | 2 | **2** |
| tiresias | 110 | **0** (usa `tiresias_seguimiento`) |
| clickie | 77 | 9 |
| ecosmart | 59 | 0 |
| just4u | 59 | 0 |
| bambutech | 11 | 1 |

> **Incompatibilidad:** los clientes NO están homogéneos en `seguimiento_reuniones`. Para replicar v2 a
> Tiresias/Ecosmart/Just4U hay que **inicializar `seguimiento_reuniones`** desde sus `reuniones`
> (igual que se hizo con GBS: INSERT con `status_reunion='agendada'`, capas en `espera/pendiente`).

### Migraciones relevantes ya aplicadas
`validacion_reuniones_columnas_e_historial`, `recalcular_validez_final_cliente_manda`,
`add_notas_internas_seguimiento`, `clientes_add_tier`, `crear_reporte_config`,
`unificar_slug_gbs_logistics_a_gbs`, `migrar_seguimiento_por_cliente_a_unificada`,
`crear_seguimiento_reuniones_unificada`, `seguimiento_reuniones_add_tipo_respuesta`.

### Riesgos de schema
- Dos modelos conviviendo (`seguimiento_reuniones` nuevo vs `*_seguimiento` legacy).
- `gbs_onboarding` usa `cliente` (no `cliente_slug`) y es GBS-específica (no genérica).
- `clientes` tiene nombres redundantes (`nombre`, `nombre_cliente`); la clave es `slug`.

---

## 10. `CLIENT_CONFIG` propuesto

```python
# portal_v2/clients/config.py
CLIENTS = {
  "gbs": {
    "slug": "gbs",
    "nombre": "GBS Logistics",
    "logo": "gbs_logo.png",
    "color_primary": "#7c3aed", "color_accent": "#db2777", "color_dark": "#1e293b",
    "meta": {"validas": 45, "tipo": "contrato"},   # fuente real: shared.metas.meta_de(slug)
    "plan": None,                                   # NO fijar: leer de clientes.tier (plan_de)
    "dashboards": ["onboarding", "validacion", "reporte", "intelligence", "playbook"],
    "seguimiento_table": "seguimiento_reuniones",   # GBS = 3 capas
    "onboarding_table": "gbs_onboarding",
    "intelligence_source": "demo",                  # "demo" | "supabase"
    "playbook_module": "clients/gbs/playbook.py",
    "ghl_token_key": "gbs",
    "assets": {"web": "https://www.gbslogistics.cl"},
  },
  # "tiresias": { ... seguimiento_table legacy hasta migrar ... },
  # "clickie":  { ... },
}
```
Campos: `slug, nombre, logo, colores, meta, plan(base/premium), dashboards habilitados,
tablas/vistas, intelligence_source, playbook, ghl_token_key, assets/links`.

---

## 11. Arquitectura v2 recomendada

**App Streamlit nueva e independiente** (entrypoint propio = deploy y link separados, rollback trivial):
```
portal_v2/
├── app_v2.py                 # entrypoint (app Streamlit nueva, otro deploy/link)
├── auth_v2.py                # login v2 (reusa portal_passwords o credenciales nuevas)
├── clients/
│   ├── config.py             # CLIENT_CONFIG (sección 10)
│   └── gbs/playbook.py       # contenido por cliente
├── data/                     # CAPA DE DATOS (fachada fina sobre shared/)
│   ├── reuniones.py          # wrappers de vw_reuniones_semana
│   ├── validacion.py         # reusa shared/seguimiento.py + shared/validacion.py
│   ├── intelligence.py       # real desde Supabase (reemplaza el demo gbs_data)
│   └── kpis.py               # reusa shared/kpis.py
├── components/               # UI nueva (banner, tabla, side-panel, chips, kpi cards)
├── pages/                    # 5 dashboards v2
└── styles/                   # CSS/tema
```

- **Qué crear:** `auth_v2`, capa `data/` (envoltura sobre `shared/`), componentes UI nuevos, `CLIENT_CONFIG`.
- **Qué reutilizar como capa de datos:** `shared/seguimiento.py`, `shared/validacion.py`, `shared/metas.py`,
  `shared/kpis.py`, `shared/config.py`. **No reimplementar reglas de negocio.**
- **Qué NO tocar:** todo `dashboard/pages/*`, `shared/seguimiento.py`, `shared/validacion.py`,
  `shared/validacion_ui.py`, `dashboard/portal_auth.py`, y las tablas/vistas Supabase.
- **Rollback seguro:** v2 es app aparte; si falla, el portal actual sigue intacto. Trabajar en branch `portal-v2`.
- **Deploy con link nuevo:** nueva app en Streamlit Cloud apuntando a `portal_v2/app_v2.py` → URL distinta.
  (El look master-detail idéntico al mockup = React/Next sobre el mismo Supabase, no Streamlit.)
- **Replicar a otro cliente:** agregar entrada en `CLIENT_CONFIG` + inicializar `seguimiento_reuniones` de
  ese cliente + assets/logo. Si su validación está en tabla legacy, migrar primero.

---

## 12. Riesgos y advertencias

- **Datos faltantes:** Tiresias/Ecosmart/Just4U sin filas en `seguimiento_reuniones`; GBS solo 2 reuniones
  reales; Intelligence Insight es **demo** (no hay datos reales de embudo/segmentos).
- **Diferencias entre clientes:** validación de Tiresias/Clickie en tablas legacy; onboarding solo para GBS.
- **Acciones que escriben datos:** `guardar_nivel`, `recalcular_final_y_flags`, `registrar_historial`,
  `upd_validacion`, upsert `gbs_onboarding`, `mover_ghl` (escribe en **GHL real**). v2 debe reusarlas.
- **Dependencia GHL:** `mover_ghl` pega a `services.leadconnectorhq.com` con token real; en demo conviene
  poder desactivarlo (feature flag).
- **Hardcodes:** `gbs` en queries/auth/nav; defaults GBS en onboarding; dataset demo.
- **Auth:** password único por cliente; token en query params (no es auth fuerte).
- **Performance:** Streamlit recarga toda la página por interacción → usar `@st.cache_data(ttl=30/60)`.
- **Streamlit limitations:** no hace master-detail con side-panel editable nativo (el mockup de Codex).
  En Streamlit sería **aproximación**; idéntico = React.

---

## 13. Quick win para demo (camino más seguro, sin tocar lo actual)

1. **App nueva** `portal_v2/app_v2.py` (otro entrypoint, otro deploy, otro link).
2. **Login v2** reutilizando `portal_passwords()["gbs"]` (cero credenciales nuevas).
3. **Validación Reuniones v2 con datos reales GBS:** reusar `cargar` (con `COLUMNAS_CLIENTE`),
   `recalcular_final_y_flags`, `registrar_historial`, `vw_reuniones_semana`. UI nueva encima.
4. **Intelligence Insight v2:** reusar `gbs_data.cargar_dataset()` + `compute_kpis` (mismos números demo;
   se ve completo para la demo).
5. **Navegación** lista para los 5 dashboards (Onboarding/Reporte/Playbook pueden ser versiones mínimas).
6. **Sin romper nada:** no se toca `dashboard/`. Branch `portal-v2`.

> Realista: en una noche, en **Streamlit**, tenés un v2 funcional con datos reales pero **no idéntico**
> al mockup. El mockup idéntico (master-detail React) no entra en "mañana".

---

## Checklist para el agente que construirá v2

**Leer primero (en orden):**
1. `shared/seguimiento.py` — acceso a datos + `COLUMNAS_CLIENTE`
2. `shared/validacion.py` — reglas (`derivar_final`)
3. `dashboard/pages/12_GBS_Validacion_Reuniones.py` — flujo de guardado de referencia
4. `dashboard/portal_auth.py` — auth y token de sesión
5. `shared/kpis.py` + `shared/gbs_data.py` — KPIs e Intelligence
6. `shared/config.py` + `shared/metas.py` + `shared/planes.py`

**Reutilizar (NO reimplementar):**
`cargar`, `guardar_nivel`, `payload_nivel`, `recalcular_final_y_flags`, `registrar_historial`,
`bant_to_list/str`, `COLUMNAS_CLIENTE` · `derivar_final`, `flag_disputa`, `flag_meta_countable`,
`gate_valida_permitida` · `compute_kpis`, `cargar_dataset`, `construir_pdf` · `plan_de`, `meta_de` ·
`supabase_url/key`, `ghl_tokens`, `portal_passwords`.

**NO tocar:**
Todo `dashboard/pages/*`, `shared/seguimiento.py`, `shared/validacion.py`, `shared/validacion_ui.py`,
`dashboard/portal_auth.py`, y las tablas/vistas Supabase.

**Leer (DB):** `vw_reuniones_semana`, `seguimiento_reuniones`, `clientes`, `ghl_pipeline_stages`,
`reporte_config`, `gbs_onboarding`, `snov_*`.

**Escribir (DB):** `seguimiento_reuniones`, `meeting_status_history`, `reporte_config`, `gbs_onboarding`,
y `reuniones.estado_validacion`. **Nunca** escribir vistas (`vw_*`).

**Ocultar al cliente (SIEMPRE):** SDR / responsable interno · `notas_internas` · `proximo_paso` ·
`validated_by_*` · `validated_*_at` · `ai_*` · `recording_url` / `transcript_url` · IDs técnicos
(`opportunity_id`, `ghl_*`). Traer solo `COLUMNAS_CLIENTE`.

**Componentes sugeridos:** `BannerValidezFinal`, `TablaReuniones (master)`, `PanelDetalle (tabs)`,
`ChipsEstado/Validez/BANT`, `BarraAvanceMeta`, `KPICards`, `Filtros (período/estado/cliente)`.

**Orden recomendado de implementación (SOLO GBS hasta aprobación):**
1. `CLIENT_CONFIG` (solo GBS) + `auth_v2` + shell de navegación + estética/tema
2. Capa `data/` (fachada fina sobre `shared/`, **sin cambiar las funciones existentes**)
3. Validación Reuniones v2 — usa los datos reales de GBS que YA existen (2 reuniones) vía las funciones
   actuales; **verificar sincronización con el panel interno**
4. Intelligence Insight v2 — **dataset demo intacto** (`gbs_data.cargar_dataset` + `compute_kpis`),
   solo nueva presentación
5. Reporte Mensual v2, Onboarding v2, Playbook v2 (mismos datos/contenido de hoy)
6. **Pausa: aprobación de Francisca de los 5 dashboards de GBS.**
7. **(Fase posterior, solo tras aprobar)** Replicar a Tiresias/Clickie: agregar al `CLIENT_CONFIG`,
   inicializar/actualizar sus datos, ajustar tablas legacy. NO antes.

> **Regla de oro para el agente:** v2 es un **rediseño de front-end de GBS con los datos demo de hoy.**
> No realizar datos, no tocar otros clientes, no tocar `dashboard/` ni `shared/seguimiento|validacion`.

---

## Contrato de la regla de validez final (resumen para no romper sincronización)

`derivar_final(status_reunion, val_cp, val_cli, bant_cp, override=None)` →
- `override` (CP) manda sobre todo.
- `val_cli == "valida"` → `"valida"` (cuenta meta), sin importar status.
- `val_cli == "no_valida"` → `"en_disputa"` si `val_cp=="valida"` y ≥2 BANT en `bant_cp`; si no, `"no_valida"`.
- Sin validación de cliente (`espera`/`requiere_revision`): status en {no_asistio_lead, no_asistio_cliente,
  cancelada_lead, cancelada_cliente} → `"no_valida"`; resto → `"pendiente"`.

`flag_meta_countable = (val_estado_final == "valida")`. El avance de meta cuenta SOLO estas filas.
Cualquier UI v2 que muestre "válida" debe basarse en `val_estado_final`, no en `reuniones.estado_validacion`.
