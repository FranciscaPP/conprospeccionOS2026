# SDR Dashboard - Reporterias

Infraestructura base para cargar configuracion SDR desde `Asignacion SDR.xlsx` hacia Supabase.

## Estado actual

- Excel importado a Supabase.
- Contactos y oportunidades sincronizados desde GHL.
- Pipelines/stages sincronizados y reuniones derivadas desde oportunidades.
- Usuarios GHL sincronizados.
- Llamadas sincronizadas desde Conversations `TYPE_CALL` con paginacion.
- Resumenes diario, cliente y financiero generados.
- GBS queda pendiente hasta que exista su subcuenta/location.
- Calendarios GHL responden, pero no estan devolviendo eventos; por ahora las reuniones se derivan desde pipeline.

## 1. Preparar entorno

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

El proyecto lee variables desde `.env` o `.env.txt`.

## 2. Crear tablas de configuracion

Ejecuta el SQL de `supabase/migrations/001_config_schema.sql` en el SQL Editor de Supabase.

La migracion crea/asegura:

- `clientes`
- `sdrs`
- `sdr_cliente`
- `cliente_metas`
- `cliente_contratos`
- `cliente_costos`
- `costos_fijos`
- `sdr_pago_reglas`
- `import_runs`

## 3. Validar el Excel sin escribir en Supabase

```powershell
python scripts/import_excel_config.py --dry-run
```

## 4. Cargar datos en Supabase

```powershell
python scripts/import_excel_config.py
```

El importador usa `upsert`, por lo que puedes correrlo mas de una vez sin duplicar registros.

## 5. Validar Supabase

```powershell
python scripts/validate_supabase.py
```

## Siguiente fase

## 6. Validar conexion Go High Level

```powershell
python scripts/test_ghl_connection.py
```

Para probar tambien permisos minimos de lectura de contactos y oportunidades:

```powershell
python scripts/test_ghl_connection.py --include-samples
```

Si `--include-samples` responde `The token is not authorized for this scope`, crea un Private Integration Token por subcuenta con scopes de lectura y agregalo al `.env`/`.env.txt` usando el slug del cliente:

```env
GHL_TOKEN_BAMBUTECH=
GHL_TOKEN_CLICKIE=
GHL_TOKEN_ECOSMART=
GHL_TOKEN_JUST4U=
GHL_TOKEN_TIRESIAS=
```

Scopes minimos recomendados para reporterias:

- `contacts.readonly`
- `opportunities.readonly`
- `calendars/events.readonly`
- `conversations.readonly`
- `locations.readonly`

GBS puede quedar sin `ghl_location_id` hasta que la subcuenta exista en Go High Level.

## Siguiente fase

## 7. Preparar tablas para sincronizacion GHL

Ejecuta en Supabase SQL Editor:

```text
supabase/migrations/003_ghl_sync_schema.sql
```

## 8. Probar sincronizacion sin escribir

```powershell
python scripts/sync_ghl.py --dry-run --max-pages 1
```

## 9. Sincronizar contactos y oportunidades

```powershell
python scripts/sync_ghl.py
```

Para sincronizar solo un cliente o una entidad:

```powershell
python scripts/sync_ghl.py --client-slug clickie --entity contactos
python scripts/sync_ghl.py --client-slug clickie --entity oportunidades
```

El sync usa `ghl_contact_id` y `ghl_opportunity_id` para evitar duplicados.

## 10. Preparar capa de reporterias

Ejecuta en Supabase SQL Editor:

```text
supabase/migrations/005_reporting_model.sql
```

Esto crea/asegura:

- columnas operacionales en `llamadas` y `reuniones`
- `costos_herramientas`
- `pagos_sdr`
- `resumen_diario_sdr`
- `resumen_cliente`
- `resumen_financiero`
- vistas base para dashboard operacional, SDR, cliente y financiero

## 11. Generar resumenes calculados

```powershell
python scripts/generate_daily_summary.py --days 7
python scripts/calculate_client_forecast.py
python scripts/calculate_financial_metrics.py --periodo actual
```

## Queries listas

Las consultas base quedan en:

- `queries/dashboard_general_operacional.sql`
- `queries/dashboard_sdr.sql`
- `queries/dashboard_cliente.sql`
- `queries/dashboard_horarios.sql`
- `queries/dashboard_financiero.sql`
- `queries/openclaw_questions.sql`

## Scripts disponibles

- `scripts/import_excel_config.py`
- `scripts/test_ghl_connection.py`
- `scripts/sync_ghl.py`
- `scripts/sync_contacts.py`
- `scripts/sync_opportunities.py`
- `scripts/sync_calls.py`
- `scripts/sync_meetings.py`
- `scripts/generate_daily_summary.py`
- `scripts/generate_weekly_summary.py`
- `scripts/calculate_client_forecast.py`
- `scripts/calculate_financial_metrics.py`

## 12. Sincronizar calendarios/reuniones

Ejecuta primero:

```text
supabase/migrations/006_calendars_meetings_sync.sql
```

Prueba sin escribir:

```powershell
python scripts/sync_meetings.py --dry-run
```

Sincroniza:

```powershell
python scripts/sync_meetings.py
```

## 13. Mapear stages y derivar reuniones desde pipeline

Ejecuta en Supabase SQL Editor:

```text
supabase/migrations/007_pipeline_stage_mapping.sql
```

Luego:

```powershell
python scripts/sync_pipelines.py
python scripts/derive_meetings_from_opportunities.py
```

## 14. Sincronizar usuarios y llamadas

Ejecuta en Supabase SQL Editor:

```text
supabase/migrations/008_users_and_conversation_calls.sql
```

Luego:

```powershell
python scripts/sync_users.py
python scripts/sync_calls.py --dry-run --client-slug clickie --max-conversations 20
python scripts/sync_calls.py --client-slug clickie --max-conversations 20
```

Para una carga controlada por paginas de conversaciones:

```powershell
python scripts/sync_calls.py --client-slug clickie --max-conversation-pages 2
python scripts/sync_calls.py --max-conversation-pages 1
```

Despues de sincronizar llamadas, recalcula:

```powershell
python scripts/generate_daily_summary.py --days 120
python scripts/calculate_client_forecast.py
python scripts/calculate_financial_metrics.py --periodo actual
```

## 15. Revisar owners GHL sin SDR

Si aparecen llamadas, contactos, oportunidades o reuniones sin `sdr_slug`, usa:

```text
queries/unmapped_ghl_users.sql
```

Esa consulta muestra `ghl_user_id`, nombre/email de GHL y cantidad de eventos sin SDR para decidir si se debe mapear a un SDR o excluir como usuario administrativo/cliente.

## 16. Excluir usuarios GHL no SDR

Ejecuta en Supabase SQL Editor:

```text
supabase/migrations/009_ghl_user_metric_exclusions.sql
```

Esto marca usuarios GHL confirmados como no SDR operativo con `excluir_metricas_sdr = true` y crea:

- `vw_actividad_ghl_no_sdr`

La actividad no se borra; queda auditable, pero fuera de rankings SDR.

## 17. Integrar Snov.io

Agrega credenciales Snov al `.env` o `.env.txt`:

```env
SNOV_CLIENT_ID=
SNOV_CLIENT_SECRET=
```

Ejecuta en Supabase SQL Editor:

```text
supabase/migrations/010_snov_email_campaigns.sql
```

Prueba conexion y lista campanas:

```powershell
python scripts/test_snov_connection.py --show-campaigns
```

Sincroniza campanas y metricas generales:

```powershell
python scripts/sync_snov.py --date-from 2026-05-01 --date-to 2026-05-31
```

Sincroniza tambien eventos detallados por campana, como enviados, aperturas, clicks, replies y finalizados:

```powershell
python scripts/sync_snov.py --date-from 2026-05-01 --date-to 2026-05-31 --include-events
```

Si quieres probar solo una campana:

```powershell
python scripts/sync_snov.py --campaign-id 123456 --include-events --dry-run
```

Tablas/vistas creadas:

- `snov_campaigns`
- `snov_campaign_metrics`
- `snov_email_events`
- `snov_campaign_map`
- `vw_snov_campaign_performance`
- `vw_snov_daily_activity`

Usa `snov_campaign_map` para asociar cada campana a `cliente_slug` y `sdr_slug`. Asi Snov queda unido al mismo modelo de reporterias que GHL.

Nota operativa actual: si Snov lo opera Francisca y no un SDR asignado, deja `sdr_slug` en blanco. El reporte de Snov queda por cliente/campana/canal correo, no en ranking SDR.

## 18. Reporterias multicanal GHL + Snov

Ejecuta en Supabase SQL Editor:

```text
supabase/migrations/011_multichannel_reporting.sql
```

Esto crea vistas para:

- contactos multifuente GHL/Snov por email normalizado
- contactos que existen en ambas fuentes
- actividad diaria multicanal por cliente
- resumen cliente con llamadas, minutos, eventos de correo, respuestas y reuniones validas

Queries listas:

- `queries/dashboard_multicanal.sql`

Por ahora el modelo recomendado es:

- GHL = llamadas, reuniones, pipeline, owner SDR
- Snov = correo, campana, CRM email, replies
- Matching futuro = por email/telefono cuando los contactos esten mejor normalizados

## 19. Enriquecer Snov con prospectos/listas

Ejecuta en Supabase SQL Editor:

```text
supabase/migrations/012_snov_prospects_enrichment.sql
```

Luego sincroniza prospectos desde las listas asociadas a campanas Snov:

```powershell
python scripts/sync_snov_prospects.py --dry-run --max-pages 1
python scripts/sync_snov_prospects.py --max-pages 1
```

Esto crea/usa:

- `snov_prospects`
- `vw_snov_prospects_enriched`
- `vw_snov_prospect_events_enriched`

Aqui se guarda cargo, industria, pais/localidad, empresa, email, LinkedIn y lista/campana cuando Snov los entregue. Despues estos datos enriquecen los eventos de correo y el cruce con GHL.

## 20. Enriquecer Snov con datos de GHL por email

Ejecuta en Supabase SQL Editor:

```text
supabase/migrations/013_snov_ghl_contact_enrichment.sql
```

Esto crea:

- `vw_snov_contacts_enriched_with_ghl`
- `vw_cliente_contactos_por_canal`

Sirve porque Snov a veces solo entrega nombre/email en listas, mientras GHL puede tener telefono, cargo, industria, pais y owner SDR para el mismo email.
