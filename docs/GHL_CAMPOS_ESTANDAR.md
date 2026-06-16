# GHL - Campos estandar Conprospeccion OS

Este documento guarda el mapa operativo de campos observado en GHL para evitar volver a levantarlo manualmente.

Regla: todas las subcuentas de clientes deben mantener estos mismos campos y claves. Si una subcuenta no los tiene, se debe crear o corregir antes de conectar workflows al portal.

## Contacto - campos base requeridos

| Dato OS | Campo GHL | Clave GHL |
| --- | --- | --- |
| Nombre | Nombre | `{{contact.first_name}}` |
| Apellidos | Apellidos | `{{contact.last_name}}` |
| Nombre completo | Nombre | `{{contact.name}}` |
| Telefono | Telefono | `{{contact.phone}}` |
| Correo | Correo electronico | `{{contact.email}}` |
| Cargo | Cargo | `{{contact.cargo}}` |
| Nombre empresa | Nombre de la empresa | `{{contact.company_name}}` |
| Pais | Pais | `{{contact.country}}` |
| Sitio web | Sitio web | `{{contact.website}}` |
| Industria | Industria | `{{contact.industria}}` |
| Tamano empresa | Tamano Empresa | `{{contact.tamao_empresa}}` |
| LinkedIn personal | Linkedin Personal | `{{contact.linkedin_personal}}` |
| LinkedIn empresa | Linkedin Empresa | `{{contact.linkedin_empresa}}` |
| Informacion para reunion | INFORMACION PARA REUNION | `{{contact.informacin_de_preparacin_para_la_reunin}}` |

## Contacto - campos comerciales utiles

| Campo GHL | Clave GHL |
| --- | --- |
| Validacion cliente BANT | `{{contact.validar_bant}}` |
| Validacion SDR BANT | `{{contact.validacin_sdr_bant}}` |
| BANT llamadas validacion BANT SDR | `{{contact.bant_llamadas_validacin_bant_sdr}}` |
| CANAL DE CONTACTO | `{{contact.canal_de_contacto}}` |
| STATUS INTERES | `{{contact.status_inters}}` |
| Nivel de Prioridad | `{{contact.nivel_de_prioridad}}` |
| STATUS LLAMADA ANTERIOR | `{{contact.status_llamada_anterior}}` |
| Status Reunion | `{{contact.status_reunin}}` |
| Comentario Reunion | `{{contact.comentario_reunin}}` |
| TIPO BBDD | `{{contact.tipo_bbdd}}` |
| STATUS PROSPECTO | `{{contact.status_llamadas}}` |
| SEGMENTO GENERAL | `{{contact.segmento_general}}` |
| Teus Promedio | `{{contact.teus_promedio}}` |
| Numero de llamada | `{{contact.nmero_de_llamada}}` |

## Contacto - direccion y fuente

| Campo GHL | Clave GHL |
| --- | --- |
| Direccion postal | `{{contact.address1}}` |
| Ciudad | `{{contact.city}}` |
| Region/provincia/estado | `{{contact.state}}` |
| Codigo postal | `{{contact.postal_code}}` |
| Zona horaria | `{{contact.timezone}}` |
| Fuente de contacto | `{{contact.source}}` |
| Tipo de contacto | `{{contact.type}}` |
| Fecha de nacimiento | `{{contact.date_of_birth}}` |

## Oportunidad

| Dato OS | Campo GHL | Clave GHL |
| --- | --- | --- |
| Nombre oportunidad | Nombre de la oportunidad | `{{opportunity.name}}` |
| Pipeline | Secuencia | `{{opportunity.pipeline_id}}` |
| Etapa | Fase | `{{opportunity.pipeline_stage_id}}` |
| Estado oportunidad | Estado | `{{opportunity.status}}` |
| Valor oportunidad | Valor del cliente potencial | `{{opportunity.monetary_value}}` |
| Propietario | Propietario | `{{opportunity.assigned_to}}` |
| Fuente oportunidad | Fuente de oportunidad | `{{opportunity.source}}` |
| Razon abandono | Razon del abandono | `{{opportunity.lost_reason}}` |
| Fecha cierre estimada | Fecha de cierre estimada de la prevision | `{{opportunity.forecast_expected_close_date}}` |
| Probabilidad | Probabilidad de la prevision | `{{opportunity.forecast_probability}}` |

## Empresa

| Dato OS | Campo GHL | Clave GHL |
| --- | --- | --- |
| Nombre empresa | Company Name | `{{business.name}}` |
| Telefono empresa | Phone | `{{business.phone}}` |
| Email empresa | Email | `{{business.email}}` |
| Website empresa | Website | `{{business.website}}` |
| Pais empresa | Country | `{{business.country}}` |
| Ciudad empresa | City | `{{business.city}}` |
| Estado empresa | State | `{{business.state}}` |
| Direccion empresa | Address | `{{business.address}}` |
| Codigo postal empresa | Postal Code | `{{business.postalcode}}` |
| Descripcion empresa | Description | `{{business.description}}` |

## Payload recomendado para workflows GHL

Usar un solo webhook universal por tipo de evento y mandar siempre el maximo detalle disponible.

```json
{
  "clientSlug": "gbs",
  "externalId": "{{contact.id}}-cotizacion",
  "contactId": "{{contact.id}}",
  "firstName": "{{contact.first_name}}",
  "lastName": "{{contact.last_name}}",
  "contactName": "{{contact.name}}",
  "email": "{{contact.email}}",
  "phone": "{{contact.phone}}",
  "jobTitle": "{{contact.cargo}}",
  "company": "{{contact.company_name}}",
  "country": "{{contact.country}}",
  "industry": "{{contact.industria}}",
  "companySize": "{{contact.tamao_empresa}}",
  "website": "{{contact.website}}",
  "companyLinkedin": "{{contact.linkedin_empresa}}",
  "contactLinkedin": "{{contact.linkedin_personal}}",
  "meetingInfo": "{{contact.informacin_de_preparacin_para_la_reunin}}",
  "statusInterest": "{{contact.status_inters}}",
  "statusMeeting": "{{contact.status_reunin}}",
  "meetingComment": "{{contact.comentario_reunin}}",
  "source": "ghl-workflow-cotizacion"
}
```

## Nota de sostenibilidad

No se debe crear un endpoint por cliente. Se usa un endpoint universal y el campo `clientSlug` define el cliente:

- GBS Logistics: `gbs`
- Otros clientes: usar su slug operativo.

Si todas las subcuentas conservan los mismos campos, solo cambia `clientSlug`, location/subcuenta y reglas del workflow.
