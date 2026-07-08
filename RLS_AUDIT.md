# Informe RLS — Proyecto SDR (`gdlncvbvhbfjonbnmxfl`)

**Fecha:** 2026-07-08
**Alcance:** Solo lectura del repositorio. No se modificó código ni la base de datos.
**Motivo:** Supabase reporta `rls_disabled_in_public` (CRÍTICO — "Table publicly
accessible") en múltiples tablas del esquema `public`.

> **Conclusión adelantada:** La app corre 100 % del lado servidor (Streamlit) y
> tanto la app como los scripts de sync acceden a Supabase con la **llave secreta
> (service_role)**. Como `service_role` **ignora RLS**, se puede **activar RLS en
> todas las tablas sin políticas y la app NO se rompe**. Esto cierra la exposición
> pública sin efectos secundarios. Único prerrequisito: confirmar que la llave
> configurada es efectivamente `service_role` (ver §1).

---

## 1. Conexión a Supabase

**Punto único de configuración:** `shared/config.py`

- `supabase_url()` — `shared/config.py:42-43` → `SUPABASE_URL` (default `https://gdlncvbvhbfjonbnmxfl.supabase.co`).
- `supabase_key()` — `shared/config.py:46-47` → devuelve `SUPABASE_KEY`, y si no existe, `SUPABASE_SECRET_KEY`.

Las variables se leen con `_get()` (`shared/config.py:29-39`): primero
`st.secrets` (Streamlit Cloud), luego `.env` local. **La llave vive en secrets/
.env del servidor, nunca en el cliente.**

**Cómo se usa la llave (siempre en headers REST, lado servidor):**

| Archivo | Línea | Uso |
|---|---|---|
| `shared/seguimiento.py` | 23-24 | `_KEY = supabase_key()`, header `apikey` + `Bearer` |
| `shared/planes.py` | 33-36 | idem |
| `dashboard/pages/1_Seguimiento_Reuniones.py` | 31-32 | idem |
| `dashboard/meeting_shared.py` | 26-27 | idem |
| `dashboard/pages/2_Clientes.py` | 22-28 | idem |
| `dashboard/pages/16_Client_Setup_OS.py` | 37-38 | idem |
| `dashboard/pages/19_BambuTech_Intelligence_Insight.py` | 42-43 | idem |
| `dashboard/pages/20_GBS_Intelligence_Insight.py` | 55-56 | idem |
| `sync/scripts/config.py` | 40,49 | `SUPABASE_SECRET_KEY` (service_role) |
| `sync/scripts/supabase_rest.py` | 14-15 | header `apikey` + `Bearer` |
| `supabase/functions/*/index.ts` | — | `SUPABASE_SERVICE_KEY` (edge functions) |

**¿Qué llave es (service_role vs anon)?**

Evidencia de que es **service_role / secret**, no anon:

1. El sync y GitHub Actions usan explícitamente `SUPABASE_SECRET_KEY`
   (`.github/workflows/sync-commercial-data.yml:40,52,70`;
   `sync/scripts/config.py:40`).
2. Las edge functions usan `SUPABASE_SERVICE_KEY`
   (`supabase/functions/meeting-evidence/index.ts:11-12`,
   `ghl-webhook/index.ts:9-10`).
3. El RUNBOOK exige no exponer service_role en el navegador
   (`docs/SEGUIMIENTO_REUNIONES_RUNBOOK.md:111`) — coherente con uso server-side.
4. La app hace escrituras privilegiadas en muchas tablas (ver §2) que con RLS
   activo solo funcionarían con service_role.

**Verificación pendiente (no ejecutada aquí):** el valor real de `SUPABASE_KEY`
en `st.secrets` de Streamlit Cloud no es visible desde el repo. Para confirmarlo
con certeza, decodificar el JWT de la llave configurada y revisar el claim
`role`: debe decir `service_role` (no `anon`). Este es el único dato que
inclina el plan de remediación.

**Exposición de la llave:** La app es **Streamlit puro (server-side)**. El código
Python que contiene la llave se ejecuta en el servidor de Streamlit Cloud; **no
se envía al navegador** ni hay cliente JS de Supabase en el producto actual (los
portales React/Next que sí podían exponer llaves fueron eliminados del repo).
→ **La llave NO está expuesta al cliente a través de la app.**

---

## 2. Uso de las tablas listadas

Clasificación por quién las toca y si la app (Streamlit) las lee/escribe:

| Tabla | App dashboard (Streamlit) | Sync (backend, service_role) | Escritura desde la app |
|---|---|---|---|
| `clientes` | **LEE** `shared/planes.py:35`; **ESCRIBE** `dashboard/pages/2_Clientes.py:27` (PATCH `tier`) | upsert `import_excel_config.py:451`; select en sync_* | **Sí** (tier) |
| `cliente_metas` | **LEE** `dashboard/pages/20_GBS_Intelligence_Insight.py:185` | upsert `import_excel_config.py:454` | No |
| `sdrs` | **LEE** `dashboard/meeting_shared.py:459` (slug,nombre) | upsert `import_excel_config.py:450` | No |
| `cliente_contratos` | — | upsert `import_excel_config.py:455` | No |
| `cliente_costos` | — | upsert `import_excel_config.py:456` | No |
| `sdr_pago_reglas` | — | upsert `import_excel_config.py:458` | No |
| `sdr_cliente` | — | select/upsert `sync_users.py:46,65`, `sync_meetings.py:103` | No |
| `costos_fijos` | — | upsert `import_excel_config.py:457` | No |
| `sync_runs` | — | insert `sync_*.py` (varios) | No |
| `import_runs` | — | insert `import_excel_config.py:461` | No |

**Resumen:**
- La app solo **lee** `cliente_metas`, `sdrs` y `clientes`, y solo **escribe**
  `clientes.tier` (desde `2_Clientes.py`).
- Las 7 tablas restantes las tocan **exclusivamente los scripts de sync**
  (backend, GitHub Actions, `SUPABASE_SECRET_KEY`).
- **Todos** los accesos (app y sync) van con la misma llave secreta/service_role.

---

## 3. Impacto de activar RLS

El comportamiento de RLS depende del rol de la llave:

- **`service_role`** → **ignora RLS por completo.** Activar RLS (con o sin
  políticas) **no afecta** ninguna consulta que use esta llave.
- **`anon` / `authenticated`** → respeta RLS. Activar RLS **sin políticas**
  bloquea todo acceso.

Dado que la evidencia (§1) indica que la app y el sync usan **service_role**:

> **Activar RLS sin políticas NO rompe la app ni el sync.** Todos los flujos
> (panel interno, `2_Clientes` escribir tier, Intelligence Insight leer metas,
> selects de SDR, y todos los jobs de sync) seguirían funcionando, porque
> service_role salta RLS.

**Qué fallaría solo si la llave fuera anon (caso a descartar con la verificación
del §1):** todo lo de la tabla de arriba — lecturas de `clientes/cliente_metas/
sdrs`, el PATCH de `tier`, y cada job de sync que inserta en `sync_runs`,
`import_runs`, etc.

---

## 4. Veredicto de urgencia

**Exposición: ALTA. Facilidad de remediación: ALTA (bajo riesgo de romper).**

Justificación:

- **Por qué la exposición es alta:** con RLS desactivado, la API REST de Supabase
  permite leer/editar/borrar todas las filas a quien tenga la **llave anon** del
  proyecto (que por diseño es "pública") más la URL. Las tablas afectadas
  contienen datos sensibles: `contactos` (~19.443 filas), `clientes`, costos y
  finanzas (`cliente_costos`, `costos_fijos`, `resumen_financiero`), pagos SDR,
  y datos de prospección (`snov_*`). Es exactamente lo que alerta Supabase.
- **Factor mitigante real:** la app es server-side y usa service_role, así que
  **el producto no filtra ninguna llave al navegador**. La explotación requiere
  que un tercero **ya conozca la llave anon** del proyecto. Si esa llave nunca se
  publicó (app 100 % server-side, portales JS eliminados), la probabilidad baja.
  No obstante, la llave anon existe para el proyecto y debe considerarse
  potencialmente conocida.
- **Conclusión:** el hueco es real y crítico según Supabase, pero **cerrarlo es
  barato y sin efectos secundarios** en este proyecto (ver §5), porque la app no
  depende de anon.

---

## 5. Plan de remediación propuesto (NO ejecutado)

**Prerrequisito único:** confirmar que `SUPABASE_KEY` (Streamlit) es
`service_role` decodificando el claim `role` de su JWT. Si lo es, seguir el
Camino A. Si resultara ser `anon`, seguir el Camino B.

### Camino A — La llave es service_role (esperado)

Activar RLS en **todas** las tablas del esquema `public`, **sin políticas**. Como
service_role ignora RLS, la app y el sync siguen funcionando y la exposición
anon queda cerrada de inmediato.

- Orden sugerido: primero las tablas con datos sensibles y de negocio
  (`contactos`, `clientes`, `cliente_contratos`, `cliente_costos`,
  `cliente_metas`, `costos_fijos`, `sdr_pago_reglas`, `pagos_sdr`,
  `resumen_financiero`), luego el resto.
- No se requieren políticas mientras el único consumidor sea service_role.
- Es la remediación que Supabase ofrece con "Enable RLS", aquí segura por el
  modelo de acceso.

### Camino B — La llave es anon (solo si la verificación lo revela)

No activar RLS en seco. Para cada tabla, activar RLS **y** crear la política
mínima según su uso (§2):

| Tabla | Política mínima requerida |
|---|---|
| `clientes` | SELECT para el rol de la app; UPDATE de `tier` (escritura desde `2_Clientes.py`) |
| `cliente_metas` | SELECT |
| `sdrs` | SELECT |
| `cliente_contratos`, `cliente_costos`, `costos_fijos`, `sdr_pago_reglas`, `sdr_cliente` | Sin acceso anon; escritura solo desde sync (service_role) → RLS activo sin política anon |
| `sync_runs`, `import_runs` | Igual: solo service_role, sin política anon |

**Decisión de negocio pendiente:** la app **no tiene modelo de autenticación a
nivel de base de datos** (el login master/portal es de aplicación, no usuarios
Supabase Auth — ver `shared/config.py:90-105`). Por eso, en el Camino B, no
existe un `auth.uid()` sobre el cual construir políticas por usuario; las
políticas serían por rol (todo-o-nada para anon) y la recomendación real seguiría
siendo migrar la app a service_role server-side (Camino A) en vez de exponer anon.

### Recomendación

Migrar mentalmente al **Camino A**: confirmar service_role → activar RLS en todas
las tablas sin políticas. Es la opción más simple, segura y alineada con cómo ya
funciona el proyecto (server-side, sin portales JS). Reevaluar políticas anon
solo el día que se reconstruyan portales cliente que consulten Supabase
directamente desde el navegador (hoy no existen).

---

*Informe generado en modo solo-lectura. No se activó RLS ni se modificó ninguna
tabla o archivo de código; el único archivo creado es este `RLS_AUDIT.md`.*
