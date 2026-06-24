# Plan de rescate desde ConprospeccionOS

Fecha: 2026-06-18

## Objetivo

Evaluar e incorporar selectivamente cambios exclusivos de:

```text
C:\Users\Admin\OneDrive\Documents\Con Prospección\ConprospeccionOS
```

al proyecto oficial:

```text
C:\Users\Admin\OneDrive\Documents\Con Prospección\conprospeccionOS2026
```

No se deben copiar carpetas ni archivos completos sin comparación previa. Ambos proyectos divergieron y el repositorio oficial también contiene cambios posteriores.

## Principios

- Streamlit continúa siendo la única implementación oficial.
- Rescatar cambios funcionales pequeños, no código histórico completo.
- Comparar cada cambio contra el estado local actual, no únicamente contra el último commit.
- Mantener juntas las reglas, la UI que las representa y sus pruebas.
- No ejecutar escrituras en Supabase, GHL ni otras integraciones durante la evaluación.
- Crear backup o referencia Git de la carpeta antigua antes de retirarla.

## Incorporar ahora

### 1. Historial completo de reuniones y cabecera fija

Prioridad: máxima  
Origen principal: `dashboard/pages/12_GBS_Validacion_Reuniones.py`  
Commits de referencia: `49f1aae`, `098b6ba`

Rescatar:

- Visualización del historial completo de reuniones GBS.
- Orden cronológico y tratamiento correcto de fechas.
- Cabecera fija de la tabla si no altera el diseño aprobado.
- Simplificación de motivos mostrados al cliente.

No copiar el archivo completo. Extraer exclusivamente los cambios relacionados con historial, fechas, tabla y motivos.

Validación requerida:

- Las reuniones futuras, realizadas y pendientes aparecen en el grupo correcto.
- No desaparecen reuniones históricas.
- Los filtros y KPIs siguen usando el mismo conjunto de datos.
- La tabla no introduce un segundo scroll vertical.

Riesgo: medio.

### 2. Persistencia de sesión administrativa

Prioridad: alta  
Archivos de origen:

- `dashboard/master_auth.py`
- `dashboard/portal_auth.py`

Commits de referencia: `80e57df`, `5b44098`, `52a1a16`

Rescatar:

- Token temporal para restaurar la sesión interna.
- Persistencia del usuario administrador durante recargas de Streamlit.
- Recuperación de `admin_mode` al previsualizar portales cliente.
- Limpieza del token al cerrar sesión.

Revisar antes de incorporar:

- Duración de 12 horas.
- Uso de query parameters.
- Derivación criptográfica del token.
- Posible exposición del modo administrador al compartir una URL.

Validación requerida:

- El administrador conserva sesión al recargar.
- Un cliente no obtiene permisos administrativos.
- Cerrar sesión invalida el acceso restaurado.
- La sesión no persiste indefinidamente.

Riesgo: alto por tratarse de autenticación.

### 3. Correcciones de estados GBS

Prioridad: alta  
Archivos de origen:

- `dashboard/pages/12_GBS_Validacion_Reuniones.py`
- `sync/scripts/sync_meetings.py`

Commit de referencia: `a629efd`

Rescatar solamente:

- Mapeos de estados GBS demostrablemente incorrectos en el proyecto oficial.
- Correcciones de campos de fecha y estado recibidos desde GHL.
- Compatibilidad con filas históricas que tengan datos incompletos.

No incorporar automáticamente el bloqueo temporal del portal GBS del commit `b32f98c`.

Validación requerida:

- Comparación con muestras reales de Supabase sin escribir datos.
- Reuniones canceladas, no realizadas, futuras y realizadas quedan diferenciadas.
- No se altera el comportamiento de Clickie, Tiresias u otros clientes.

Riesgo: alto por afectar datos y sincronización.

### 4. Semántica de validación manual

Prioridad: alta  
Archivos de origen:

- `shared/validacion.py`
- `tests/test_validacion.py`
- `dashboard/pages/12_GBS_Validacion_Reuniones.py`

Commit de referencia: `068f82d`

Decisión que debe confirmarse:

> BANT incompleto o evidencia ausente no invalidan automáticamente una reunión que fue marcada manualmente como válida.

Si esa regla continúa vigente, incorporar conjuntamente:

- Cambio en la derivación final.
- Compatibilidad de la página GBS.
- Tests que expresan la nueva regla.

No mezclar parcialmente pruebas antiguas con reglas nuevas.

Validación requerida:

- Pruebas de válida, no válida, reagendada, no realizada y en revisión.
- Casos con BANT incompleto.
- Casos sin evidencia.
- Casos con decisión manual explícita.

Riesgo: alto por ser una regla contractual.

## Incorporar después

### 5. Backfill de nombres de reuniones GBS

Origen:

```text
sync/scripts/backfill_gbs_meeting_names.py
```

El script es único de la carpeta antigua y completa contacto, empresa, email y teléfono consultando GHL.

Antes de incorporarlo:

- Adaptarlo a las versiones actuales de `config.py`, `ghl_client.py` y `supabase_rest.py`.
- Añadir `--dry-run`.
- Añadir límite, cliente explícito y resumen de cambios.
- Verificar qué campos puede sobrescribir.
- Evitar incluir credenciales o datos temporales.

No ejecutarlo durante el rescate.

Riesgo: alto por escribir en Supabase.

### 6. Mejoras del sincronizador de reuniones

Origen:

```text
sync/scripts/sync_meetings.py
```

La versión antigua contiene correcciones GBS, pero la oficial contiene mejoras posteriores para enriquecer contactos y normalizar datos.

Incorporar mediante comparación por funciones:

- Selección de fechas.
- Estado de reunión.
- Campos GBS ausentes.
- Campos históricos compatibles.

No reemplazar el sincronizador oficial completo.

Validación requerida:

- Ejecución `--dry-run`.
- Comparación de payloads para los mismos eventos.
- Deduplificación por `ghl_appointment_id`.
- Comprobación multicliente.

Riesgo: alto.

### 7. Recuperación de onboarding previamente guardado

Origen:

```text
dashboard/pages/14_GBS_Onboarding.py
```

Rescatar:

- Lectura del registro más reciente.
- Precarga segura de inputs, selectores y listas.
- Manejo de valores vacíos o formatos antiguos.

Separar esta mejora de la generación DOCX.

Validación requerida:

- Formulario vacío para un cliente sin datos.
- Formulario precargado para un cliente existente.
- Guardar conserva campos no editados.
- No se mezclan datos de clientes.

Riesgo: medio/alto.

### 8. Exportación DOCX del onboarding

Origen:

- `dashboard/pages/14_GBS_Onboarding.py`
- `dashboard/requirements.txt`

Dependencia nueva:

```text
python-docx>=1.1
```

Incorporar solo después de estabilizar la carga y guardado del onboarding.

Requisitos:

- Definir el propósito y destinatario del documento.
- Verificar estructura, nombre y datos sensibles.
- Evitar escribir archivos temporales permanentes.
- Probar el download directamente en Streamlit.

Riesgo: medio.

## No incorporar

### Bloqueo temporal del portal GBS

Commit: `b32f98c`

Fue una medida temporal. Solo debe recuperarse si el usuario solicita explícitamente desactivar el portal.

### Sustitución completa de la página de validación GBS

No copiar completa la versión antigua de:

```text
dashboard/pages/12_GBS_Validacion_Reuniones.py
```

La página oficial ya contiene una implementación posterior y cambios locales. Solo se deben portar funciones o fragmentos claramente identificados.

### Sustitución completa del motor de validación

No reemplazar íntegramente:

- `shared/validacion.py`
- `shared/validacion_ui.py`
- `tests/test_validacion.py`

El proyecto oficial incorporó estados de flujo y reglas adicionales que la versión antigua elimina.

### Sustitución completa de sincronización o webhook

No reemplazar íntegramente:

- `sync/scripts/config.py`
- `sync/scripts/ghl_client.py`
- `sync/scripts/sync_meetings.py`
- `supabase/functions/ghl-webhook/index.ts`

El proyecto oficial contiene cambios posteriores y migraciones adicionales.

### Proyectos y datos históricos

No incorporar al workspace activo:

- `mvp_setup/`
- `portal_v2/`
- `portal_v2_web/`
- `whatsapp_check/`
- `apollo_export/`
- `data/`
- `BASES_APOLLO&SNOV/`
- logs, archivos temporales y credenciales.

### Alicia

No mezclar `alicia/` con Streamlit. Si sigue siendo necesaria, evaluarla como proyecto independiente.

## Orden recomendado de ejecución

1. Crear backup o etiqueta recuperable de `ConprospeccionOS`.
2. Portar historial de reuniones y cabecera fija.
3. Portar persistencia de sesión con revisión de seguridad.
4. Definir formalmente la semántica de validación manual.
5. Incorporar juntas las reglas confirmadas y sus tests.
6. Revisar correcciones GBS con muestras reales en modo lectura.
7. Comparar y adaptar sincronización usando `--dry-run`.
8. Adaptar el backfill sin ejecutarlo.
9. Incorporar precarga del onboarding.
10. Evaluar DOCX como mejora independiente.
11. Verificar Streamlit completo antes de archivar la carpeta antigua.

## Criterio de cierre

La carpeta `ConprospeccionOS` podrá archivarse fuera del workspace cuando:

- los cambios seleccionados estén incorporados o descartados explícitamente;
- las pruebas de validación pasen;
- la sesión administrativa y los portales funcionen;
- GBS muestre historial y estados correctos;
- la sincronización haya sido verificada en modo `--dry-run`;
- exista un backup recuperable de archivos y commits antiguos.

