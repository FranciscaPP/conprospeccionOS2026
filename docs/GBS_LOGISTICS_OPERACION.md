# GBS Logistics - Operacion de reuniones

## Regla de calendario maestro

Todas las reuniones de GBS Logistics deben agendarse siempre en el calendario maestro:

`sam@gbs-logistics.cl`

Para sincronizacion automatica, este calendario es la fuente primaria de agenda. Si una reunion tambien aparece en otro calendario o subcalendario, se considera duplicada/secundaria; la version del calendario maestro es la referencia.

## Flujo esperado

1. La reunion se agenda en el calendario maestro de Sam.
2. La grabadora se une desde esa invitacion.
3. La evidencia se cruza por fecha, contacto, empresa y link de Google Meet.
4. El dashboard del cliente muestra grabacion, transcripcion, resumen IA y decision de validacion.

## Solicitudes de cotizacion sin reunion

Para GBS, una solicitud directa de cotizacion puede contar para la meta aunque no exista una videollamada.

Flujo recomendado en GHL:

1. Campo personalizado: `Tipo de gestion GBS`.
2. Valores:
   - `Reunion`
   - `Cotizacion`
   - `Cotizacion + reunion`
3. Workflow:
   - Trigger: contacto actualizado y `Tipo de gestion GBS = Cotizacion`.
   - Acciones:
     - agregar tag `gbs cotizacion`
     - mover oportunidad a etapa `Cotizacion solicitada`
     - crear tarea para llamar y levantar requerimiento
     - enviar webhook al portal con empresa, contacto, telefono, email, pais, tipo y proximo paso
4. El dashboard lo muestra como `Solo cotizacion`, pendiente de validacion del cliente y con seguimiento comercial.

## Webhook cotizacion GBS

Endpoint Vercel:

`POST /api/meetings/quote-request`

Uso esperado desde GHL cuando el campo del contacto indique `Cotizacion` o `Cotizacion + reunion`.

Payload minimo:

```json
{
  "clientSlug": "gbs",
  "externalId": "ghl-contact-or-workflow-id",
  "contactId": "ghl-contact-id",
  "company": "DYSMAR",
  "contactName": "Jorge Manrique",
  "jobTitle": "General Manager",
  "email": "jorgemanrique@dysmar.com",
  "phone": "+51 968 088 181",
  "industry": "information technology & services",
  "country": "Peru",
  "meetingInfo": "Texto del campo INFORMACION PARA REUNION",
  "requestedAt": "2026-06-16T16:00:00-04:00"
}
```

Campos opcionales utiles:

`website`, `companyLinkedin`, `contactLinkedin`, `companySize`, `quoteNotes`, `source`, `raw`.

Mapa completo de campos GHL estandar:

`docs/GHL_CAMPOS_ESTANDAR.md`

El endpoint crea o actualiza una fila en `public.reuniones` como:

- `estado_reunion`: `solicita_cotizacion`
- `estado_validacion`: `pendiente_validacion`
- `notas`: `Solo cotizacion`
- `cliente_slug`: `gbs` por defecto

Si existe `GHL_WEBHOOK_SECRET` o `WEBHOOK_SECRET`, GHL debe enviar el header `x-webhook-secret`.

Si despues se agenda reunion, el tipo cambia a `Cotizacion + reunion` y se sigue el flujo normal del calendario maestro.
