# Handoff para Codex — Conprospección OS
**Fecha:** 2026-05-29
**Preparado por:** Claude (auditoría del estado actual)
**Propósito:** Permitir que Codex entienda, audite y continúe este proyecto sin perder contexto.

---

## 1. Resumen ejecutivo

**Conprospección OS** es el sistema operativo interno de la agencia ConProspección. Es una plataforma Streamlit/Python que automatiza el ciclo completo de prospección B2B para sus clientes: desde el onboarding hasta la generación de bases, mensajería y seguimiento.

El sistema tiene tres módulos activos en producción más uno en desarrollo activo:

| Módulo | Puerto | Estado |
|--------|--------|--------|
| `mvp_setup/app.py` | 8501 | **Desarrollo activo** — el foco de este handoff |
| `dashboard/app.py` | 8502 | Producción estable |
| `alicia/bot.py` | Telegram | Producción estable |
| `sync/scripts/` | cron / manual | Estable |

El cliente de referencia actual para pruebas es **GBS Logistics**, pero el MVP Setup está diseñado para todos los clientes de la agencia.

---

## 2. Qué es cada módulo

### MVP Setup (`mvp_setup/app.py`)
Onboarding operativo de clientes B2B. Permite crear la carpeta del cliente, analizar su web con IA, construir su ICP, buscar/filtrar bases de contactos desde Apollo.io y Snov.io, calificarlos con el ICP y generar mensajería por segmento. Es el módulo donde se concentra el trabajo actual.

### Dashboard (`dashboard/`)
Panel de seguimiento operativo. Muestra reuniones del día, permite validarlas, ver métricas por SDR y por cliente. Conectado a Supabase en tiempo real.

### Alicia (`alicia/bot.py`)
Bot Telegram. Permite a los SDRs y a Francisca interactuar con el CRM (GHL), validar reuniones, consultar rankings y crear/actualizar contactos — todo desde Telegram.

### Sync (`sync/scripts/`)
Scripts de sincronización GHL ↔ Supabase. Corren manualmente o en cron. Sincronizan contactos, reuniones, oportunidades, pipelines y usuarios.

---

## 3. Arquitectura actual

```
ConprospeccionOS/
├── .env                          ← ÚNICO .env del proyecto (no crear otros)
├── shared/
│   └── config.py                 ← Centraliza lectura de variables de entorno
├── mvp_setup/
│   ├── app.py                    ← ~5,530 líneas — UI completa Streamlit
│   ├── config.py                 ← CLIENTES_DIR, ETAPAS, extensiones válidas
│   └── modules/
│       ├── estructura.py         ← Define y crea 35 carpetas por cliente
│       ├── estado.py             ← Lee/escribe estado_cliente.json
│       ├── archivos.py           ← Upload y clasificación de archivos
│       ├── firma.py              ← Genera firma HTML/texto para email
│       └── templates.py         ← Plantillas Markdown base por carpeta
├── dashboard/
│   ├── app.py                    ← Header, auth, navegación
│   ├── master_auth.py            ← Login interno (Francisca, equipo)
│   ├── portal_auth.py            ← Login para portales de clientes
│   └── pages/
│       ├── 1_Seguimiento_Reuniones.py
│       ├── 2_Clientes.py
│       ├── 3_Tiresias.py         ← Dashboard específico Tiresias
│       ├── 4_Tiresias_Validacion_Reuniones.py
│       ├── 5_Tiresias_Playbook_SDR.py
│       ├── 6_Clickie.py
│       ├── 7_Clickie_Validacion_Reuniones.py
│       ├── 8_Clickie_Playbook_SDR.py
│       ├── 9_SDRs.py
│       └── 10_Tiresias_Interno.py
├── alicia/
│   └── bot.py                   ← ~1,164 líneas — Telegram + GHL API
├── sync/
│   └── scripts/
│       ├── run_sync.py           ← Master: ejecuta sync en orden
│       ├── sync_meetings.py      ← GHL calendarios → Supabase
│       ├── sync_opportunities.py ← Wrapper → sync_ghl.py
│       ├── sync_contacts.py      ← Wrapper → sync_ghl.py
│       ├── sync_ghl.py           ← Lógica real de sync GHL→Supabase
│       ├── sync_pipelines.py
│       ├── sync_users.py
│       ├── sync_snov.py
│       ├── config.py
│       ├── ghl_client.py
│       ├── supabase_rest.py
│       └── snov_client.py
├── BASES_APOLLO/                 ← Gitignoreado — bases acumuladas por cliente
│   └── {nombre_cliente}/
│       └── apollo_all.csv
├── BASES_SNOV/                   ← Gitignoreado
│   └── {nombre_cliente}/
│       └── snov_all.csv
└── docs/                         ← Este handoff
```

### Carpeta por cliente (se crea automáticamente)

```
CLIENTES/{CLIENTE_ID}/
├── estado_cliente.json           ← Estado + ICP + progreso (fuente de verdad)
├── 00_INPUT_CLIENTE/
│   ├── documentos/               ← PDF, DOCX, TXT, MD subidos por el cliente
│   ├── logos/
│   ├── bases/                    ← CSV/XLSX del cliente
│   ├── imagenes/
│   ├── minutas/
│   └── otros/
├── 01_ADMIN_CLIENTE/
├── 02_BRANDING_Y_ACTIVOS/
├── 03_ANALISIS_CLIENTE/
│   ├── resumen_servicio.md
│   ├── propuesta_valor.md
│   ├── problema_que_resuelve.md
│   └── analisis_web.md
├── 04_ICP_ESTRATEGIA/
│   ├── icp_borrador.md           ← ICP en elaboración (con historial de chat)
│   ├── icp_master.md             ← ICP aprobado (solo Francisca lo edita)
│   ├── macro_cargos.md
│   ├── cargos_apollo_por_coma.md
│   ├── industrias_apollo_por_coma.md
│   ├── criterios_prioridad.md
│   ├── criterios_descarte.md
│   └── exclusiones_apollo.md
├── 05_MENSAJERIA_COMERCIAL/
├── 06_PLAYBOOK_SDR/
├── 07_APOLLO_Y_BUSQUEDAS/
├── 07_BASE_DATOS/
│   └── comercial.json            ← Datos del contrato
├── 08_BASES_Y_CALIFICACION/      ← Bases calificadas (output del Paso 5)
│   ├── 01_originales/
│   ├── 02_calificadas/
│   ├── 03_para_ghl/
│   ├── 04_para_snov/
│   ├── 05_para_whatsapp/
│   ├── 06_por_sdr/
│   └── 99_descartados/
├── 09_CAMPAÑAS_EMAIL/
├── 10_CAMPAÑAS_WHATSAPP/
├── 11_SCRIPTS_Y_AUTOMATIZACIONES/
├── 12_REPORTERIA/
├── 13_BRIEF_CLIENTE_INTERACTIVO/
├── 14_SUPABASE_METABASE/
└── 99_HISTORICO/
```

---

## 4. Cómo ejecutar localmente

```bash
# Instalar dependencias
pip install streamlit anthropic supabase python-dotenv requests pandas openpyxl pypdf python-docx

# MVP Setup (este módulo)
streamlit run mvp_setup/app.py --server.port 8501

# Dashboard
streamlit run dashboard/app.py --server.port 8502

# Alicia
python alicia/bot.py

# Sync manual
python sync/scripts/run_sync.py
```

**Python correcto en Windows:** `C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe`

---

## 5. Tecnologías

| Capa | Tecnología |
|------|-----------|
| Frontend | Streamlit (Python) |
| Base de datos | Supabase (PostgreSQL) — proyecto `gdlncvbvhbfjonbnmxfl` |
| CRM | GoHighLevel (GHL) |
| IA | Claude API (Anthropic) — modelo `claude-sonnet-4-6` |
| Bot | Telegram (python-telegram-bot) |
| Prospección | Apollo.io API, Snov.io API |
| Storage local | Sistema de archivos Windows — OneDrive sincroniza automáticamente |

---

## 6. Variables de entorno requeridas

Todas en **`.env` en la raíz** del proyecto. No hay otros `.env`.

```env
# IA
ANTHROPIC_API_KEY=sk-ant-...

# Base de datos
SUPABASE_URL=https://gdlncvbvhbfjonbnmxfl.supabase.co
SUPABASE_KEY=eyJ...

# Telegram bot
TELEGRAM_TOKEN=...

# Prospección
APOLLO_API_KEY=...
SNOV_CLIENT_ID=...
SNOV_CLIENT_SECRET=...

# GHL — tokens por cliente (subcuenta)
GHL_AGENCY_TOKEN=...
ECOSMART_TOKEN=...
ECOSMART_ID=...
CLICKIE_TOKEN=...
CLICKIE_ID=...
JUST4U_TOKEN=...
JUST4U_ID=...
TIRESIAS_TOKEN=...
TIRESIAS_ID=...
BAMBUTECH_TOKEN=...
BAMBUTECH_ID=...
GBS_TOKEN=...
GBS_ID=...

# Portales (contraseñas)
MASTER_PASSWORD=...
TIRESIAS_PORTAL_PASSWORD=...
CLICKIE_PORTAL_PASSWORD=...
```

---

## 7. APIs conectadas

### Apollo.io
- **Endpoint:** `POST https://api.apollo.io/api/v1/mixed_people/api_search`
- **Auth:** Header `x-api-key: {APOLLO_API_KEY}`
- **Función en código:** `_apollo_buscar()` (línea ~2957 en `mvp_setup/app.py`)
- **Nota crítica:** El parámetro `q_organization_keyword_tags` es un **relevance boost, no un filtro duro**. No filtra industrias con precisión. El filtrado real de industrias debe hacerse en post-procesamiento local.
- **Limitación:** La API pública no devuelve emails (requiere créditos de enriquecimiento adicionales). Las bases descargadas desde el sitio de Apollo tienen todos los campos.

### Snov.io
- **OAuth:** `POST https://api.snov.io/v1/oauth/access_token` → token temporal
- **Búsqueda:** `POST https://api.snov.io/v2/api/search-contacts`
- **Función en código:** `_snov_token()` + `_snov_buscar()` (línea ~3045 en `mvp_setup/app.py`)
- **Estado:** Integración parcial — la función está escrita pero no probada en producción. La estructura de respuesta del endpoint puede diferir de lo esperado.

### Supabase
- **Tablas clave:** `reuniones`, `sdr_cliente`, `ghl_pipeline_stages`, `clientes`
- **Uso en MVP Setup:** Sincroniza datos básicos del cliente con `_sync_supabase_cliente()` (opcional, falla silenciosamente)

### GoHighLevel (GHL)
- **Base URL:** `https://services.leadconnectorhq.com`
- **Uso:** Principalmente en Alicia y en sync. El MVP Setup tiene un tab "GHL Setup" pero está en desarrollo.

### Claude / Anthropic
- **Modelo:** `claude-sonnet-4-6`
- **Usos principales:**
  - Análisis web del cliente (Paso 3)
  - Generación y refinamiento de ICP (Paso 4)
  - Extracción de datos comerciales de propuestas
  - Generación de mensajería por segmento (Paso 5)
- **Función central:** `llamar_claude()` con reintentos exponenciales para rate limits

---

## 8. Flujo funcional actual (MVP Setup)

```
Usuario abre mvp_setup en localhost:8501
  ↓
Sidebar: selecciona cliente o crea nuevo
  ↓
[Nuevo cliente] → Wizard:
  1. Sube archivos del cliente (PDF, logos, bases, docs)
  2. Completa datos base (nombre, web, países, objetivo)
  3. Claude analiza documentos → genera 5 cards de análisis
  4. Confirma → crea estructura de 35 carpetas
  ↓
[Cliente existente] → 12 Tabs:
  Tab 0: Datos del cliente (info general, SDR, contrato)
  Tab 1: Archivos (upload, gestión documentos)
  Tab 2: Análisis web (Claude analiza la web + docs)
  Tab 3: ICP (genera/edita ICP con Claude, chat)
  Tab 4: Bases y Mensajería ← FOCO PRINCIPAL
  Tab 5: Playbook SDR
  Tab 6: Firma de email
  Tab 7: GHL Setup
  Tab 8: Estado y datos (dashboard de progreso)
  Tab 9: Chat (con contexto completo del cliente)
  Tab 10: Archivos generados (descarga todos los MD)
  Tab 11: Roadmap
```

### Tab 4 — Bases y Mensajería (flujo detallado)

```
1. Muestra estado del ICP (si está cargado o no)
2. Sección "Buscar prospectos directamente" [APIs]
   ├── Apollo.io: genera filtros desde ICP → permite editar → ejecuta búsqueda
   └── Snov.io: mismo flujo
3. Sección "Pool de bases" [LOCAL]
   ├── Stats del pool actual (N total, N con email)
   ├── Upload de base Apollo/Snov al pool
   ├── Filtrar base (palabras clave, industrias, países, tamaño)
   └── Descarga resultado filtrado
4. Sección "O sube tu base manualmente"
   ├── Upload de CSV/XLSX
   ├── Calificar con ICP → genera 8 columnas CP_*
   ├── Stats: Tier A/B/C/Excluir/Sin match
   └── Descarga por tier
5. Sección "Archivos para SDRs — CRM"
   └── Bases por prioridad para subir a GHL/Snov
6. Sección "Mensajería por segmento"
   └── Claude genera 3 emails por segmento (macro_cargo × macro_industria)
```

---

## 9. Datos guardados y dónde

| Dato | Archivo |
|------|---------|
| Estado del cliente, ICP, progreso | `CLIENTES/{ID}/estado_cliente.json` |
| Datos del contrato | `CLIENTES/{ID}/07_BASE_DATOS/comercial.json` |
| ICP en elaboración | `CLIENTES/{ID}/04_ICP_ESTRATEGIA/icp_borrador.md` |
| ICP aprobado | `CLIENTES/{ID}/04_ICP_ESTRATEGIA/icp_master.md` |
| Análisis web | `CLIENTES/{ID}/03_ANALISIS_CLIENTE/*.md` |
| Pool Apollo acumulado | `BASES_APOLLO/{nombre_cliente}/apollo_all.csv` |
| Pool Snov acumulado | `BASES_SNOV/{nombre_cliente}/snov_all.csv` |
| Bases calificadas | `CLIENTES/{ID}/08_BASES_Y_CALIFICACION/` |
| Mensajería generada | `CLIENTES/{ID}/05_MENSAJERIA_COMERCIAL/` |

---

## 10. Qué NO está en GitHub (gitignoreado)

```
.env                    ← Credenciales
CLIENTES/               ← Datos de clientes (datos personales)
BASES_APOLLO/           ← Bases Apollo descargadas (datos personales)
BASES_SNOV/             ← Bases Snov (datos personales)
*.csv, *.xlsx           ← Datos
*.log                   ← Logs
.streamlit/secrets.toml
```

---

## 11. Clientes activos

| Cliente | Slug | Estado |
|---------|------|--------|
| Ecosmart | ecosmart | En operación |
| Clickie | clickie | En operación |
| Just4U | just4u | En operación |
| Tiresias | tiresias | En operación |
| Bambutech | bambutech | En operación |
| **GBS Logistics** | gbs | **En setup — caso de prueba actual** |

---

## 12. SDRs del equipo

Florencia Ravizza, Mariana Figueroa, Mariela Tello, Yanina, Zoe Olmedo, Eugenia Marañón, Luciana Acuña

---

## 13. Riesgos que Codex debe conocer

1. **`app.py` es monolítico (5,530 líneas)** — cualquier cambio grande puede romper otras funciones. Leer con cuidado antes de editar.
2. **`estado_cliente.json` es la fuente de verdad del ICP** — no editarlo manualmente. Usar `actualizar_campo()`.
3. **Las bases Apollo/Snov son datos personales de contactos** — no incluir en commits, no logear.
4. **La API de Apollo no filtra industrias con precisión** — `q_organization_keyword_tags` es boost de relevancia, no filtro. El filtrado real es post-procesamiento local.
5. **Snov.io no está probado en producción** — la integración existe pero puede fallar silenciosamente.
6. **Las carpetas de clientes viven en OneDrive** — si OneDrive está sincronizando, puede haber conflictos de archivo.
7. **No refactorizar sin coordinación** — muchas funciones están entrelazadas. Las refactorizaciones grandes deben ser coordinadas.

---

## 14. Qué debe revisar Codex primero

1. `mvp_setup/app.py` — líneas 2786-3320 (constantes Apollo, funciones API, función pool)
2. `mvp_setup/app.py` — líneas 3119-3254 (funciones de clasificación)
3. `mvp_setup/app.py` — líneas 3256-3600 (tab_bases_apollo completo)
4. `mvp_setup/app.py` — líneas 1536-1563 (definición de tabs)
5. `mvp_setup/modules/estado.py` — para entender el ciclo de vida del estado
6. `.env.example` — para entender todas las variables necesarias

---

## 15. Qué NO tocar todavía

- `alicia/bot.py` — en producción, estable, cambios coordinados con Francisca
- `dashboard/pages/` — en producción
- `sync/scripts/` — en producción
- `CLIENTES/` — datos reales de clientes
- `icp_master.md` de cualquier cliente — es el ICP aprobado, no se modifica sin confirmación

---

## 16. Preguntas abiertas para Francisca

Ver archivo `CODEX_HANDOFF_PROYECTO_COMPLETO.md` — sección final.

*(Las preguntas están en `docs/CODEX_TASK_LIST_PRIORIZADA.md` — sección "Preguntas abiertas para Francisca")*

---

*Generado automáticamente mediante auditoría del código — 2026-05-29*
