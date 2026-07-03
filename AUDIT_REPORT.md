# AUDIT_REPORT — ConprospecciónOS 2026

Fecha de auditoría: 2026-07-03
Alcance: solo lectura. Rama auditada: `main` (HEAD `acdad39`). Historia del repo: 50 commits desde 2026-06-27 (import inicial `465f6ce`), por lo que "fecha de último commit" no sirve como evidencia de abandono anterior a esa fecha.

---

## 1. DIAGNÓSTICO EJECUTIVO

**Nivel de desorden: MEDIO-ALTO.**

Justificación: la documentación vigente (2026-06-27) es coherente con la intención de negocio y el núcleo de reglas (`shared/validacion.py`) implementa exactamente los 7 estados esperados. Pero ese núcleo **no es la única implementación**: hay tres modelos de estados conviviendo en producción (núcleo compartido, panel maestro en JS embebido, portal Tiresias legacy), el esquema de Supabase crítico no está versionado en el repo, y la suite de tests está roja en `main` (6 de 46 fallan), incluyendo justamente el test que vigilaba que panel y portal usaran la misma derivación de estados.

### 5 riesgos principales

| # | Riesgo | Evidencia |
|---|--------|-----------|
| 1 | **El portal cliente Tiresias permite al cliente marcar "Reunión válida / No válida" directamente** sobre `reuniones.estado_validacion`, violando la regla de que solo Conprospección cierra validez. La página está desplegada y protegida solo por password (`PORTAL_PASSWORD_TIRESIAS`). | `dashboard/pages/4_Tiresias_Validacion_Reuniones.py:27-29,125-148`; `shared/config.py` (password tiresias) |
| 2 | **El panel maestro no usa la derivación canónica de estados.** `1_Seguimiento_Reuniones.py` es un componente HTML/JS embebido con su propio modelo de 4 ejes + "Estado del Caso", con opciones que no existen en el modelo de 7 estados ("Reagendar reunión" como Estado Final, "No válida" como evaluación cliente). La regla de negocio vive duplicada en JavaScript. | `dashboard/pages/1_Seguimiento_Reuniones.py:823-827` (statuses/cps/clientVals/finalOptions/caseStatusOptions); no importa `derivar_estado_flujo` |
| 3 | **Tablas críticas de Supabase sin migración versionada**: `seguimiento_reuniones`, `meeting_status_history`, `contactos`, `reporte_config` y la vista `vw_reuniones_semana` no tienen `CREATE` en ningún `.sql` del repo (solo `ALTER` incrementales). La única fuente de verdad del esquema es la base viva. | `grep CREATE TABLE` sobre `supabase/migrations/`, `sync/supabase/migrations/`, `sync/migrations/` — sin resultados para esas tablas |
| 4 | **Tres implementaciones paralelas de portal cliente**: Clickie y BambuTech son copias de ~55 KB cada una que sí usan el núcleo (`derivar_estado_flujo`); GBS usa un componente HTML distinto (`client_meeting_portal/index.html`) con proyección propia de estados en `meeting_shared.py`. Cualquier corrección de regla contractual debe hacerse 3 veces. | `dashboard/pages/7_Clickie_Validacion_Reuniones.py:1038`, `18_BambuTech_Validacion_Reuniones.py:1007`, `12_GBS_Validacion_Reuniones.py` → `dashboard/client_meeting_portal.py` |
| 5 | **Tests rojos en `main` (6/46)**, incluido `test_portal_y_seguimiento_dependen_de_la_misma_derivacion_de_estado`, que falla porque el portal GBS y el panel interno ya no usan `derivar_estado_flujo`. La red de seguridad existe pero nadie la mantiene ni la corre en CI (no hay workflow de tests). | `tests/test_validacion.py:225`; `pytest -q` → 6 failed / 40 passed; `.github/workflows/` solo contiene sync de datos |

### Qué está activo

- **Streamlit Cloud** desde `dashboard/app.py`, rama `main` (verificado en docs al 2026-06-27; `vercel.json` desactiva todo deploy Git; commit `55a4760` "desactivar todos los deploys Vercel").
- Panel maestro `dashboard/pages/1_Seguimiento_Reuniones.py`; portales Clickie (7), GBS (12), BambuTech (18); páginas de soporte GBS/BambuTech (11, 13-15, 17, 19-20).
- Núcleo compartido `shared/` (validación, seguimiento, config, metas).
- Sync GHL→Supabase: `sync/scripts/` vía GitHub Actions cada día a las 8/13/20 hora Chile (`.github/workflows/sync-commercial-data.yml`), solo BambuTech y GBS.
- Edge functions Supabase: `ghl-webhook` (sync inmediato al agendar) y `meeting-evidence` (ingesta genérica de evidencia).

### Qué es legacy

- `archive/` completo (app Next.js/React, componentes, prototipos).
- Páginas Tiresias (3, 4, 5, 10) — cliente marcado "Legacy/inactive" en `.env.example`, pero las páginas siguen desplegadas.
- Mockups: `mockups/`, `dashboard/mockup_portal.html`, `dashboard/build_mockup.py`, `dashboard/mockup_bambutech_onboarding.html`, `archive/prototypes/`.
- Rastros Next/Vercel en raíz: `next-dev.log`, `next-dev.err.log`, variables `NEXT_PUBLIC_*` en `.env.example`.
- Scripts de transcripción/evidencia que apuntan a rutas inexistentes (`scripts/sync-google-meet-evidence.mjs` → `docs/data/*` no existe).
- Bot Telegram "Alicia" (`bot.py`, `start_alicia.bat`) y `diagnostico.py` — solo ejecución manual local, con clientes inactivos (ecosmart, tiresias).

### Qué requiere verificación manual (no verificable desde el repo)

- Qué migraciones están realmente aplicadas en la base Supabase viva (especialmente `006_client_setup_os_proposed.sql`, que el propio código marca como "Revisar y ejecutar en Fase 2": `dashboard/pages/16_Client_Setup_OS.py:468`).
- Si Metabase sigue conectado a las vistas `vw_*` (`sync/queries/metabase_validation.sql`, migraciones 017/020).
- Si el bot Alicia y los scripts Snov (`sync/scripts/sync_snov*.py`, `scripts/*.js`) se ejecutan aún manualmente.
- Definición real de `vw_reuniones_semana` en la base viva (el panel y páginas Tiresias dependen de ella).
- Si los deploys Vercel quedaron efectivamente desconectados en el dashboard de Vercel (el repo solo puede desactivar su lado).

---

## 2. MAPA DEL REPO

Estados: **activo** / **legacy** / **dudoso** / **archivar-luego** / **revisar**.

### Raíz

| Archivo | Propósito aparente | Estado | Riesgo | Comentario |
|---|---|---|---|---|
| `CLAUDE.md`, `AGENTS.md` | Instrucciones para agentes | activo | medio | Ambos obligan a usar Graphify (`graphify-out/`), que **no existe** en el repo. Instrucción rota. |
| `PROJECT_MASTER_CONTEXT.md`, `ACTIVE_WORKSPACE.md` | Fuente de verdad técnica (2026-06-27) | activo | bajo | Coherentes entre sí y con la intención de negocio. |
| `CONPROSPECCION_OS_RULEBOOK.md` | Reglas de autoridad y 7 estados | activo | bajo | Sección 6 define los 7 estados oficiales; coincide con `shared/validacion.py`. |
| `README.md` | Presentación | activo | bajo | — |
| `bot.py`, `start_alicia.bat` | Bot Telegram "Alicia" (Anthropic + GHL + Supabase) | dudoso | medio | Incluye clientes inactivos (ecosmart, just4u, tiresias). Sin evidencia de ejecución automatizada. |
| `diagnostico.py` | Test manual de conexión GHL ecosmart/tiresias | legacy | bajo | Solo clientes inactivos. |
| `process_gbs_snov.py` | Depuración ICP de base Snov GBS (one-shot) | archivar-luego | bajo | Lee `data/raw/GBS/*.xlsx` local que no está en el repo. |
| `iniciar_dashboard.bat` | Arranque local Windows | activo | bajo | — |
| `vercel.json` | Desactiva deploys Vercel | activo | bajo | **No tocar**: es el freno del bot de Vercel. |
| `next-dev.log`, `next-dev.err.log` | Logs de `next dev` commiteados | legacy | bajo | Basura; candidatos a archivar/ignorar. |
| `.env.example` | Plantilla de variables | activo | medio | Referencia rutas inexistentes (`docs/data/*`) y habla de "Next.js local development". Desactualizado. |
| `requirements.txt` (raíz) | Deps del bot (telegram, anthropic) | dudoso | bajo | No son las deps del dashboard (`dashboard/requirements.txt`). Confuso. |
| `.github/workflows/sync-commercial-data.yml` | Sync GHL 3×/día (bambutech, gbs) | activo | alto | Único automatismo de datos. **No tocar sin cuidado.** |
| `.streamlit/config.toml` | Config Streamlit | activo | bajo | — |

### `dashboard/`

| Archivo | Propósito | Estado | Riesgo | Comentario |
|---|---|---|---|---|
| `app.py` | Entrada + login master | activo | alto | Producción. |
| `master_auth.py` | Login Francisca/Yanina, sin roles | activo | bajo | Cumple la intención: mismas capacidades, sin RBAC. |
| `portal_auth.py` | Auth portales cliente por password | activo | medio | Incluye Tiresias como cliente con portal. |
| `meeting_shared.py` | Carga/normalización de reuniones + proyección para portal | activo | alto | Deriva labels de estado por su cuenta (no usa `derivar_estado_flujo`). Segunda fuente de reglas. |
| `client_meeting_portal.py` + `client_meeting_portal/index.html` | Portal cliente unificado (usado solo por GBS) | activo | medio | Escritura correcta (solo confirmar/solicitar revisión vía `payload_respuesta_cliente`), pero proyección de estados propia. |
| `meeting_component.py` | Wrapper de componente Streamlit | activo | bajo | — |
| `pages/1_Seguimiento_Reuniones.py` | Panel maestro (110 KB, HTML/JS embebido) | activo | alto | Producción. Modelo de estados propio en JS; contiene aún datos demo muertos (líneas 835-841) que ya no se usan (reemplazados en runtime, `:952-955`). |
| `pages/2_Clientes.py`, `9_SDRs.py` | Vistas internas | activo | bajo | — |
| `pages/3,4,5,10` (Tiresias) | Portal + interno Tiresias | legacy | **alto** | Cliente inactivo; el portal 4 permite al cliente cerrar validez (contradicción crítica). |
| `pages/6,7,8` (Clickie) | Portal + playbook Clickie | activo | medio | 7 usa el núcleo canónico. |
| `pages/11,12,13,14,15` (GBS) | Portal, validación, playbook, onboarding, reporte | activo | medio | 12 usa `client_meeting_portal` (ruta distinta a Clickie/Bambu). |
| `pages/16_Client_Setup_OS.py` | Setup OS (fase propuesta) | dudoso | medio | Depende de tablas `client_setup*` cuya migración 006 está marcada "proposed". Lee carpetas locales (`BASES_APOLLO/`) que no existen en el repo. |
| `pages/17,18,19,20` (BambuTech) | Onboarding, validación, insights, playbook | activo | medio | 18 usa el núcleo canónico. |
| `build_mockup.py`, `mockup_portal.html` (148 KB), `mockup_portal_template.html` (1 byte), `mockup_bambutech_onboarding.html` | Generador y salidas de mockups | archivar-luego | bajo | No referenciados por el producto. Cumplen la regla de no estar en `pages/`, pero ensucian `dashboard/`. |
| `data/` | Snapshot JSON BambuTech + script | dudoso | bajo | Datos estáticos embebidos en repo. |
| `assets/` | Logos | activo | bajo | Binarios, no auditados. |

### `shared/`

| Archivo | Propósito | Estado | Riesgo | Comentario |
|---|---|---|---|---|
| `validacion.py` | **Núcleo canónico de estados** (7 estados, reglas cliente, meta) | activo | alto | Fuente de verdad de negocio. Contiene además taxonomías paralelas antiguas (`VAL_FINAL`, `ESTATUS_VALIDACION` de 10 estados, `ETAPAS_AGENDA` con cotización). |
| `seguimiento.py` | Acceso a `seguimiento_reuniones` + recálculo final/flags | activo | alto | Autoderiva `val_estado_final` (contradice al RUNBOOK, ver sección 4). |
| `config.py` | Config central (Supabase, GHL, passwords) | activo | alto | Contiene URL Supabase hardcodeada como default. Incluye tokens de clientes inactivos. |
| `metas.py`, `planes.py`, `kpis.py`, `meeting_scope.py` | Metas/planes/KPIs, alcance activo (clickie, gbs, bambutech) | activo | bajo | `meeting_scope` fija los 3 clientes prioritarios. |
| `*_brand.py`, `gbs_data.py`, `icp_summary.py`, `pdf_report.py`, `validacion_ui.py` | Branding y helpers | activo | bajo | — |

### `sync/`

| Ruta | Propósito | Estado | Riesgo | Comentario |
|---|---|---|---|---|
| `scripts/sync_ghl.py`, `sync_meetings.py`, `sync_pipelines.py`, `derive_meetings_from_opportunities.py`, `ghl_client.py`, `supabase_rest.py`, `config.py` | Sync GHL→Supabase usado por CI | activo | alto | Corre 3×/día. |
| `scripts/sync_snov*.py`, `snov_client.py` | Sync Snov | dudoso | medio | No están en el workflow CI. Ejecución manual o abandonados — requiere verificación. |
| `scripts/sync_calls.py`, `sync_users.py`, `sync_contacts.py`, `sync_opportunities.py`, `import_excel_config.py`, `calculate_*.py`, `generate_*.py`, `test_*.py`, `validate_supabase.py` | Sync/reportes auxiliares | dudoso | medio | No referenciados por CI ni dashboard. |
| `supabase/migrations/001-026` | Migraciones históricas (heredadas del repo anterior) | revisar | alto | Fuente parcial del esquema real; numeración choca con `supabase/migrations/`. |
| `migrations/001_tiresias_seguimiento.sql` | Tabla tiresias | legacy | bajo | Tercer árbol de migraciones. |
| `queries/*.sql` | Queries para Metabase/dashboards SQL | dudoso | bajo | Uso externo (Metabase) — requiere verificación. |
| `README.md` | Doc del sync | activo | bajo | — |

### `supabase/`

| Ruta | Propósito | Estado | Riesgo | Comentario |
|---|---|---|---|---|
| `functions/ghl-webhook/index.ts` | Webhook GHL → sync inmediato | activo | alto | Filtra a clickie/gbs/bambutech pero mantiene mapeo de inactivos. |
| `functions/meeting-evidence/index.ts` | Ingesta de evidencia (tl;dv/Meet/Fathom/manual) | activo | medio | Endpoint genérico; solo gbs/bambutech. Origen de los datos requiere verificación. |
| `migrations/001-005` | Tablas core + gbs_onboarding | revisar | alto | No incluyen `seguimiento_reuniones` ni `meeting_status_history`. |
| `migrations/006_client_setup_os_proposed.sql` | Esquema Client Setup OS "propuesto" | dudoso | medio | El código dice ejecutarla "en Fase 2"; aplicación real requiere verificación. |
| `README.md` | Doc | activo | bajo | — |

### `scripts/` (raíz)

| Archivo | Propósito | Estado | Riesgo | Comentario |
|---|---|---|---|---|
| `sync-ghl-meetings.mjs`, `sync-google-meet-evidence.mjs` | Sync Node de reuniones/evidencia Meet | legacy | medio | Leen/escriben `docs/data/*` que **no existe** en el repo. No referenciados por CI ni docs vigentes. |
| `analyze_*.{js,ps1}`, `build_conprospeccion_snov_campaigns.js`, `validate_conprospeccion_snov_ready.js` | Campañas Snov one-shot | archivar-luego | bajo | Scripts puntuales de prospección. |
| `strip_emojis.py` | Utilidad | dudoso | bajo | — |

### `tests/`, `docs/`, `mockups/`, `archive/`

| Ruta | Propósito | Estado | Riesgo | Comentario |
|---|---|---|---|---|
| `tests/` (5 archivos) | Guardas de reglas de negocio | activo | alto | **6 de 46 tests fallan en `main`**; varios son asserts de texto fuente que quedaron obsoletos tras refactors. No hay CI de tests. |
| `docs/SEGUIMIENTO_REUNIONES_RUNBOOK.md` | Runbook del panel | activo | medio | Contradice al código en autoderivación de Estado Final (ver sección 4). |
| `docs/ACCESS_MODEL.md`, `PORTAL_CLIENTE_UX_STANDARD.md`, `GHL_CAMPOS_ESTANDAR.md`, `GBS_CALENDARIO_MAESTRO.md` | Modelo de acceso, UX, campos GHL | activo | bajo | ACCESS_MODEL coincide con la intención (sin roles; RLS pendiente). |
| `mockups/portal-cliente-validacion-reuniones.html` | Mockup HTML | archivar-luego | bajo | Referencia visual; no producto. |
| `archive/` (app, components, lib, prototypes, public) | App Next.js/React anterior + prototipos | legacy | bajo | Correctamente aislado. No auditado en detalle (fuera de alcance por instrucción). |

---

## 3. FUENTES DE VERDAD ACTUALES

**Mandan hoy (código):**
1. `shared/validacion.py` — reglas de negocio canónicas: 7 estados (`ESTADOS_FLUJO:53-61`), acciones cliente (`acciones_cliente_permitidas:412-420`), autoridad CP (`derivar_final:423-452`), meta (`flag_meta_countable:459-460`).
2. `shared/seguimiento.py` — contrato de escritura sobre `seguimiento_reuniones` (respuesta cliente restringida a `valida`/`requiere_revision` con comentario obligatorio: `:39,84-87`).
3. `shared/meeting_scope.py` — clientes activos: clickie, gbs, bambutech.
4. `dashboard/app.py` + `dashboard/pages/1_Seguimiento_Reuniones.py` — producto desplegado.
5. `.github/workflows/sync-commercial-data.yml` + `sync/scripts/` — pipeline de datos real.
6. La **base Supabase viva** — única fuente completa del esquema (el repo no la refleja; ver riesgo 3).

**Mandan hoy (docs):** `PROJECT_MASTER_CONTEXT.md`, `ACTIVE_WORKSPACE.md`, `CONPROSPECCION_OS_RULEBOOK.md`, `docs/ACCESS_MODEL.md`, `docs/SEGUIMIENTO_REUNIONES_RUNBOOK.md` (con la salvedad de la sección 4), `CLAUDE.md` (con la salvedad de Graphify).

**NO deberían mandar aunque existan:**
- Todo `archive/` (React/Next/prototipos) — el propio AGENTS.md lo dice.
- `dashboard/mockup_portal.html`, `dashboard/build_mockup.py`, `mockups/` — referencias visuales, no reglas.
- Los datos demo incrustados en `1_Seguimiento_Reuniones.py:835-841` — código muerto que un lector puede confundir con reglas.
- Taxonomías paralelas dentro de `shared/validacion.py` (`ESTATUS_VALIDACION` de 10 estados, `VAL_FINAL` con `en_disputa`/`excluida`/`reagendada`) — conviven con el modelo de 7 estados y confunden cuál es el oficial.
- `.env.example` en su sección Next.js/Vercel y rutas `docs/data/*`.
- Referencias a Graphify en `CLAUDE.md`/`AGENTS.md` mientras `graphify-out/` no exista.
- `scripts/sync-google-meet-evidence.mjs` y `sync-ghl-meetings.mjs` (apuntan a rutas inexistentes).

---

## 4. CONTRADICCIONES DETECTADAS

| # | Contradicción | Archivos involucrados | Impacto | Recomendación |
|---|---|---|---|---|
| C1 (Q1) | **El modelo canónico de 7 estados existe y coincide 1:1 con la intención**, pero solo lo usan los portales Clickie y BambuTech. El panel maestro y el portal GBS derivan estados por caminos propios. | `shared/validacion.py:53-61,107-115,270-310` (canónico); `dashboard/pages/7_...:1038`, `18_...:1007` (lo usan); `dashboard/meeting_shared.py:96-190` y `dashboard/pages/1_Seguimiento_Reuniones.py:823-827` (no lo usan) | Alto: una misma reunión puede mostrarse con estados distintos según pantalla | Unificar toda derivación en `shared/validacion.py`. REQUIERE DECISIÓN DE FRANCISCA sobre cuál pantalla manda mientras tanto |
| C2 (Q1) | **Portal Tiresias permite al cliente marcar válida/no válida** directamente, en contra de "solo Conprospección cierra". | `dashboard/pages/4_Tiresias_Validacion_Reuniones.py:27-29,125-148` escribe `reuniones.estado_validacion` | Alto (contractual), mitigado por cliente inactivo | Retirar/archivar las páginas Tiresias. REQUIERE DECISIÓN DE FRANCISCA |
| C3 (Q1) | El panel maestro ofrece opciones fuera del modelo: Estado Final "Reagendar reunión"/"Pendiente", Evaluación Cliente "No válida", eje extra "Estado del Caso". La intención dice que no existen acciones cliente de rechazar/reagendar/no válida. | `1_Seguimiento_Reuniones.py:823-827`; `meeting_shared.py:140-151,160-171` | Medio: permite registrar internamente estados que el modelo no contempla | REQUIERE DECISIÓN DE FRANCISCA: ¿"No válida" como registro interno de lo que dijo el cliente es aceptable, o se elimina la opción? |
| C4 (Q1) | **Cotización se cierra automáticamente como válida y suma a meta**, estado que no existe en los 7 oficiales. | `shared/validacion.py:442-443` (`derivar_final`: cotización → `valida`); `:327-328,354-355,87,100` | Medio: afecta directamente el conteo de meta | REQUIERE DECISIÓN DE FRANCISCA |
| C5 (Q1) | El RUNBOOK dice "Ninguno debe calcular automáticamente al otro" y que Estado Final "siempre se define manualmente", pero el código autoderiva `val_estado_final` en cada guardado (confirmación del cliente cierra como válida sola). El RULEBOOK, en cambio, respalda al código ("confirmar cierra la evaluación como válida"). | `docs/SEGUIMIENTO_REUNIONES_RUNBOOK.md:24-31,51`; `shared/seguimiento.py:177-236` (`recalcular_final_y_flags`); `CONPROSPECCION_OS_RULEBOOK.md:91` | Medio: dos docs oficiales se contradicen entre sí y uno contradice al código | Corregir el RUNBOOK o el código. REQUIERE DECISIÓN DE FRANCISCA sobre si la confirmación del cliente cierra sola la evaluación |
| C6 (Q2) | Producción confirmada Streamlit; sin embargo quedan rastros React/Next/Vercel activos en raíz: logs de `next dev` commiteados, sección Next.js en `.env.example`, y `vercel.json` (este último es intencional: apaga deploys). | `next-dev.log`, `next-dev.err.log`, `.env.example:2-3,10`, `vercel.json`; legacy aislado en `archive/` | Bajo: confusión | Archivar logs, limpiar `.env.example`. Mantener `vercel.json` |
| C7 (Q3) | El código asume herramientas de evidencia/transcripción (tl;dv, Google Meet, Fathom) vía endpoint genérico, pero los scripts que la alimentaban apuntan a `docs/data/*` que no existe en el repo. | `supabase/functions/meeting-evidence/index.ts:1-3`; `scripts/sync-google-meet-evidence.mjs:5-9`; `.env.example` (GOOGLE_MEET_*) | Medio: no se puede saber desde el repo si la evidencia llega hoy | Requiere verificación: ¿qué alimenta `recording_url`/`transcript_url`/`ai_*` hoy? |
| C8 (Q3) | Snov/Apollo: tablas, scripts y vistas Snov existen, pero el CI no los ejecuta; Apollo aparece como "Preparado, sin API". | `sync/scripts/sync_snov*.py`; `sync/supabase/migrations/010-013`; `dashboard/pages/16_Client_Setup_OS.py:817`; workflow CI (solo GHL) | Medio: pipeline de prospección aparentemente detenido en el repo | Requiere verificación de ejecución manual |
| C9 (Q4) | **Tablas núcleo sin `CREATE` versionado** (`seguimiento_reuniones`, `meeting_status_history`, `contactos`, `reporte_config`, vista `vw_reuniones_semana`), y tres árboles de migraciones con numeración en conflicto. | Uso: `shared/seguimiento.py:135,146,166,221`; `dashboard/meeting_shared.py:411-439`. Definición: inexistente; solo ALTERs en `sync/supabase/migrations/022,024,025,026` | Alto: imposible reconstruir o ramificar la base desde el repo | Volcar esquema vivo a migraciones consolidadas (tarea futura, no ejecutada en esta auditoría) |
| C10 (Q4) | Decenas de tablas/vistas definidas que el dashboard no usa (`llamadas`, `pagos_sdr`, `snov_*`, `resumen_*`, `costos_*`, `cliente_contratos`, ~34 vistas `vw_*`), usadas solo por scripts sync no calendarizados o por Metabase. | `sync/supabase/migrations/005,011,014,016,017,020`; consumo dashboard: solo 12 recursos (ver Q4 abajo) | Medio: esquema inflado, difícil saber qué borrar | Inventario contra la base viva antes de archivar nada |
| C11 | `CLAUDE.md` y `AGENTS.md` obligan a usar Graphify (`graphify-out/graph.json`) que no existe en el repo. | `CLAUDE.md` (sección Graphify); `AGENTS.md:1-12` | Bajo: instrucciones de agente inoperantes | Actualizar docs o regenerar el grafo |
| C12 | Tests que vigilaban la coherencia del sistema están rotos y sin CI. | `tests/test_validacion.py:225` (falla), `tests/test_dedup_reuniones.py:12`, `tests/test_bambutech_portal.py:26`; `.github/workflows/` sin job de tests | Alto: deriva silenciosa ya ocurrió (C1) | Reparar tests y agregar CI. REQUIERE DECISIÓN DE FRANCISCA solo si implica cambiar reglas, no para el CI |

**Respuestas directas:**

- **Q1**: El código implementa HOY los 7 estados esperados, con nombres y semántica exactos, en `shared/validacion.py` (`ESTADOS_FLUJO`, `derivar_estado_flujo`, `LABEL_ESTADO_FLUJO`). Acciones cliente limitadas a Confirmar/Solicitar revisión con motivo obligatorio (`shared/seguimiento.py:84-87`), BANT no invalida (`derivar_final` no lo usa para invalidar), solo `valida` suma a meta (`flag_meta_countable`). **Cercanía: 7/7 en el núcleo**, pero solo 2 de 4 superficies de UI lo consumen (C1); Tiresias lo viola (C2); cotización agrega un octavo estado de facto (C4).
- **Q2**: Producción es Streamlit (`dashboard/app.py`, Streamlit Cloud, `main`). Candidatos a legacy React/Vercel/Next/Lovable: `archive/` completo, `next-dev.log`/`next-dev.err.log`, sección Next/Vercel de `.env.example`, `mockups/`, `dashboard/mockup_*` y `dashboard/build_mockup.py`, `archive/prototypes/docs/*.html`. `vercel.json` se conserva porque apaga los deploys.
- **Q3**: Activas: GHL (sync CI + webhook), Supabase, Streamlit Cloud. Manuales/dudosas: Snov, Telegram/Anthropic (Alicia), Metabase, Apollo ("sin API"). Aparentemente abandonadas: pipeline de evidencia Google Meet vía `scripts/*.mjs` y `docs/data/*` (rutas inexistentes); no hay integración de Fireflies/Fathom/Granola en el código pese a mencionarse tl;dv/Fathom como orígenes posibles del endpoint `meeting-evidence`.
- **Q4**: El código activo usa 12 recursos: `reuniones`, `seguimiento_reuniones`, `meeting_status_history`, `vw_reuniones_semana`, `contactos`, `sdrs`, `clientes`, `ghl_pipeline_stages`, `gbs_onboarding`, `reporte_config`, `tiresias_seguimiento` (solo páginas legacy), `gbs_seguimiento`. Huérfanas aparentes (definidas, sin consumo en dashboard ni CI): `clickie_seguimiento`, `llamadas`, `pagos_sdr`, `sdr_pago_reglas`, `oportunidades` (solo `derive_meetings_from_opportunities.py`), `import_runs`, `sync_runs`, `snov_*` (5), `ghl_calendars`, `ghl_users`, `cliente_contratos/costos/metas`, `costos_*`, `resumen_*`, `backup_*`, y ~34 vistas `vw_*` (uso Metabase requiere verificación).

---

## 5. CANDIDATOS A ARCHIVAR (no borrar)

| Candidato | Motivo |
|---|---|
| `dashboard/pages/3_Tiresias.py`, `4_Tiresias_Validacion_Reuniones.py`, `5_Tiresias_Playbook_SDR.py`, `10_Tiresias_Interno.py` | Cliente inactivo; el portal viola el modelo de validación vigente; siguen siendo páginas visibles en producción. |
| `next-dev.log`, `next-dev.err.log` | Logs de desarrollo Next commiteados por accidente. |
| `dashboard/mockup_portal.html`, `dashboard/mockup_portal_template.html`, `dashboard/mockup_bambutech_onboarding.html`, `dashboard/build_mockup.py` | Mockups y su generador dentro del árbol del producto. |
| `mockups/portal-cliente-validacion-reuniones.html` | Prototipo visual ya implementado. |
| `scripts/sync-google-meet-evidence.mjs`, `scripts/sync-ghl-meetings.mjs` | Apuntan a `docs/data/*` inexistente; sin invocación en CI ni docs. |
| `scripts/analyze_conprospeccion_campaigns.{js,ps1}`, `build_conprospeccion_snov_campaigns.js`, `validate_conprospeccion_snov_ready.js` | Scripts one-shot de campañas Snov. |
| `process_gbs_snov.py`, `diagnostico.py` | One-shot con insumos locales inexistentes / clientes inactivos. |
| `bot.py`, `start_alicia.bat`, `requirements.txt` raíz | Bot Alicia: sin automatización, con clientes inactivos. Confirmar uso manual antes de archivar. |
| Datos demo incrustados en `1_Seguimiento_Reuniones.py:835-841` | Código muerto (se reemplaza en runtime); extraer en refactor futuro, no en esta sesión. |
| `sync/scripts/` no usados por CI (`sync_snov*`, `sync_calls`, `sync_users`, `import_excel_config`, `calculate_*`, `generate_*`) | Confirmar primero si se ejecutan manualmente. |

---

## 6. ARCHIVOS QUE NO SE DEBEN TOCAR

| Archivo/Ruta | Razón |
|---|---|
| `dashboard/app.py`, `dashboard/pages/1_Seguimiento_Reuniones.py`, `pages/7`, `12`, `18` | Producción en uso por Francisca, Yanina y clientes. |
| `shared/validacion.py`, `shared/seguimiento.py`, `shared/config.py` | Núcleo de reglas contractuales y acceso a datos; todo el producto depende de ellos. |
| `.github/workflows/sync-commercial-data.yml` y `sync/scripts/{sync_ghl,sync_meetings,sync_pipelines,derive_meetings_from_opportunities,ghl_client,supabase_rest,config}.py` | Pipeline de datos automatizado (3×/día). |
| `supabase/functions/ghl-webhook/index.ts`, `meeting-evidence/index.ts` | Endpoints vivos que alimentan la base de producción. |
| `vercel.json` | Es el interruptor que mantiene apagados los deploys Vercel. Quitarlo puede reactivar el bot. |
| `.env.example` (sin borrar claves) y cualquier `.env`/`secrets` locales | Plantilla de credenciales; los secretos reales viven en Streamlit Cloud y GitHub Secrets. |
| `.streamlit/config.toml` | Config de despliegue. |
| Migraciones SQL existentes (`supabase/migrations/`, `sync/supabase/migrations/`, `sync/migrations/`) | Aunque incompletas, son el único registro histórico del esquema; no renumerar ni editar en caliente. |
| `dashboard/assets/` y logos | Binarios usados por login y portales. |

---

## 7. DECISIONES QUE FRANCISCA DEBE APROBAR

1. **Tiresias**: ¿se archivan las 4 páginas Tiresias (3, 4, 5, 10) y se retira su password de portal? Hoy el portal permite al cliente cerrar validez, contra la regla vigente.
2. **Unificación de estados**: autorizar el plan para que panel maestro y portal GBS consuman `shared/validacion.py` (hoy solo Clickie y BambuTech lo hacen). Mientras tanto, definir qué pantalla manda si muestran estados distintos.
3. **Cotización**: ¿"Solicita cotización" debe seguir cerrándose automáticamente como válida y sumar a meta, siendo que no es uno de los 7 estados oficiales?
4. **Cierre automático por confirmación**: cuando el cliente confirma, ¿la evaluación se cierra sola como válida (código y RULEBOOK actuales) o el cierre es siempre manual (RUNBOOK actual)? Hay que corregir uno de los dos.
5. **Evaluación Cliente "No válida" en panel interno**: ¿se mantiene como registro interno de lo que expresó el cliente, o se elimina la opción para dejar solo Pendiente/Confirmar/Solicita revisión/No necesaria?
6. **Esquema Supabase**: autorizar (en una sesión futura, no en esta) el volcado del esquema vivo a migraciones consolidadas para que el repo vuelva a ser fuente de verdad.
7. **Herramientas dudosas**: confirmar si Alicia (Telegram), los scripts Snov y Metabase siguen usándose manualmente, para decidir archivo o mantenimiento.
8. **Tests y CI**: aprobar reparar los 6 tests rotos y agregar un workflow de tests (no cambia reglas de negocio, pero toca archivos existentes, prohibido en esta sesión).
