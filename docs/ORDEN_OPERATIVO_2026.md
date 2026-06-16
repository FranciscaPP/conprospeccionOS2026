# Orden operativo Conprospeccion OS2026

## Carpeta y repo oficiales

La carpeta que se debe usar para el producto actual es:

```txt
C:\Users\Admin\OneDrive\Documents\Con Prospección\conprospeccionOS2026
```

Repo remoto:

```txt
https://github.com/FranciscaPP/conprospeccionOS2026.git
```

Este repo es el stack Vercel/Next.js. La carpeta historica `ConprospeccionOS` queda como referencia legacy de Streamlit y scripts antiguos, no como destino de producto.

## Estado de Graphify

Graphify esta generado en este repo:

```txt
graphify-out/
```

Comandos locales en esta maquina:

```bash
python -m graphify query "pregunta"
python -m graphify explain "concepto"
python -m graphify path "A" "B"
python -m graphify update .
```

Nota Windows: el comando `graphify` existe en el paquete Python, pero en esta maquina no esta en PATH. Usar `python -m graphify`.

## Prioridad de producto

Antes de construir "Recuperacion de oportunidades", conviene cerrar el nucleo operativo:

1. Dashboard cliente: dejar estable la vista que el cliente usa para revisar performance, reuniones y validacion.
2. Dashboard SDR lider: dejar estable la vista interna para controlar SDR, clientes, actividad, riesgo y foco semanal.
3. Calidad de datos: asegurar sync confiable desde GHL, Snov y Supabase.
4. Recuperacion de oportunidades: construir despues como modulo interno conectado al historico.

La razon operativa es simple: recuperacion historica va a depender de los mismos conceptos de cliente, SDR, reuniones, oportunidades, estados y actividad. Si esos dashboards no estan cerrados, el modulo historico hereda deuda y duplicidad.

## Fuentes confirmadas

### GHL

Subcuenta Conprospeccion:

- `GHL_LOCATION_CONPROSPECCION`
- `GHL_TOKEN_CONPROSPECCION`

La subcuenta interna debe tratarse distinto a las subcuentas de clientes. Puede contener oportunidades propias de Conprospeccion, pero segun contexto operativo estan desordenadas y no deben asumirse como fuente limpia.

### Snov

Credenciales locales:

- `SNOV_CLIENT_ID`
- `SNOV_CLIENT_SECRET`

Snov es clave para recuperar respuestas porque ahi existe un mini CRM de Conprospeccion. Debe usarse para identificar:

- prospectos que respondieron
- respuestas positivas
- solicitudes de informacion
- interesados que no agendaron
- campanas y listas origen
- ultimo contacto conocido

### Supabase

Supabase sigue siendo la fuente de verdad normalizada del producto. GHL y Snov alimentan Supabase; la app Next.js debe leer desde APIs internas o Supabase normalizado, no directamente desde archivos locales.

## Recuperacion de oportunidades

El modulo debe construirse como capa interna, no como automatizacion de envio.

Entidad recomendada:

- `recovery_opportunities`: oportunidad consolidada
- `opportunity_events`: eventos normalizados por fuente
- `opportunity_identities`: emails, dominios, contactos y empresas vinculadas
- `recovery_actions`: decisiones humanas, borradores, descartes y proximos pasos

Estados iniciales:

- reunion realizada + propuesta enviada + sin respuesta
- reunion realizada + info enviada + sin respuesta
- respondio interesado pero no agendo
- coordinando reunion
- pidio informacion
- oportunidad antigua sin seguimiento

Prioridad inicial:

- Alta: propuesta enviada o reunion realizada
- Media: respondio o pidio informacion
- Baja: interaccion menor

## Regla de seguridad comercial

No enviar correos automaticamente en la primera version.

Permitido en MVP:

- ver historial
- clasificar oportunidad
- generar borrador
- editar borrador
- copiar correo

Permitido en fase posterior:

- crear borrador en Gmail con API

No permitido sin aprobacion humana:

- enviar correo
- secuenciar contactos automaticamente
- reactivar bases grandes sin revision de entregabilidad

## Orden tecnico recomendado

1. Usar Graphify para navegar el repo antes de cambios grandes.
2. Cerrar dashboard cliente y SDR lider.
3. Auditar tablas/vistas actuales de reuniones, clientes, SDR, Snov y GHL.
4. Validar credenciales Snov y GHL Conprospeccion localmente.
5. Crear modelo Supabase de recuperacion.
6. Crear API interna Next.js.
7. Crear UI interna de revision.
8. Agregar generador de borradores.
9. Agregar Gmail drafts solo cuando el flujo humano este aprobado.

## Deliverability

La recuperacion debe ejecutarse en lotes chicos y con contexto real:

- priorizar conversaciones con respuesta previa
- responder desde la misma cuenta que tuvo la conversacion cuando sea posible
- no usar tracking al inicio
- evitar enlaces innecesarios
- excluir rebotes, bajas y no interesados
- limitar volumen diario por cuenta
- revisar manualmente antes de crear cualquier borrador
