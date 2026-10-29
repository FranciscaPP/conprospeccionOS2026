# Equipo Alicia: envíos cada dos horas y Con Prospección separado

Fecha: 2026-10-28

## Objetivo

Modificar exclusivamente el reporte operativo de `@equipo_alicia_bot` para:

1. enviarlo de lunes a viernes a las 09:00, 11:00, 13:00, 15:00, 17:00,
   19:00 y 21:00, hora de Chile;
2. no enviar reportes los sábados ni domingos;
3. mostrar `CON PROSPECCIÓN` como una unidad separada de `BALIA`, aunque ambas
   operen dentro de la misma subcuenta de GHL;
4. mantener un solo total global de minutos sin trabajar, porque Con Prospección
   no tiene un bloque horario esperado propio.

No se modifican los bots de clientes ni el bot separado de reuniones.

## Identidad y atribución

La fuente de verdad es el usuario GHL de Nora:

- correo verificado en vivo: `nora@conprospeccion.com`;
- `user_id`: `hzPn99MPQYZTj0u4G4Qj`;
- subcuenta: la misma ubicación GHL usada por Balia.

La atribución no dependerá del texto del título ni de palabras como
"prospección". Se usará el campo de propietario/asignado correspondiente:

- tareas: `assignedTo`;
- llamadas y mensajes salientes: `userId`;
- conversaciones entrantes y pendientes: usuario responsable de la
  conversación/contacto;
- reuniones: usuario asignado al evento.

Cuando el identificador sea el de Nora, la gestión se atribuye a
`CON PROSPECCIÓN`. El resto de la subcuenta sigue atribuido a `BALIA`.

## Tablas del reporte

`CON PROSPECCIÓN` usará una fila azul propia y aparecerá separado en:

- reuniones de hoy;
- reuniones agendadas hoy;
- tareas: atrasadas, hoy, total, avance en número y porcentaje, pendientes;
- llamadas en número: total, contestadas y sin contestar;
- llamadas en minutos: total, contestadas y sin contestar;
- correos: pendientes, hoy, total, respondidos y sin responder;
- tiempo trabajado efectivo atribuible a llamadas y correos;
- trabajo fuera de horario: antes de las 11:00, almuerzo y después de las
  20:00, tanto en cantidad como en minutos.

Las tareas y actividades atribuidas a Con Prospección se excluyen de la fila de
Balia antes de construir los totales. De esta forma, el total general conserva
el universo completo sin duplicaciones.

## Tiempo trabajado y sin trabajar

Con Prospección no tiene un bloque horario asignado dentro de la jornada. Por
eso el reporte mostrará sus minutos efectivamente trabajados, pero no calculará
un tiempo ocioso propio para esa fila.

El total de Nora mantiene:

- minutos trabajados por llamadas más el crédito vigente para correos y
  WhatsApp manuales;
- minutos sin trabajar como una sola diferencia global entre la jornada
  transcurrida y el trabajo acreditado de todos los clientes y Con Prospección.

La adherencia a bloques permanece solo para Balia, GBS y BambuTech, que sí
tienen bloques esperados.

## Programación

La guardia horaria usará `America/Santiago` y una lista explícita de horas
permitidas: `{09, 11, 13, 15, 17, 19, 21}`. No se codificará una equivalencia
UTC fija, para respetar los cambios de horario de Chile.

GitHub Actions puede seguir despertando cada 15 minutos para tolerar retrasos
del cron, pero la clave idempotente permitirá un solo envío dentro de cada hora
habilitada. El programador local de respaldo tendrá exactamente los mismos
siete disparadores y la misma exclusión de fines de semana.

## Errores y datos incompletos

- Una actividad sin usuario atribuible no se asignará silenciosamente a Con
  Prospección.
- Si una fuente no permite separar un canal con certeza, se mostrará como no
  disponible y se agregará una alerta; no se inventará la atribución.
- Se conserva la protección contra reportes duplicados y envíos parciales.

## Pruebas y aceptación

La implementación debe demostrar:

1. envío permitido solo en las siete horas acordadas de lunes a viernes;
2. bloqueo completo en sábado y domingo;
3. comportamiento correcto bajo ambos desfases UTC de Chile;
4. partición de tareas por `assignedTo` y de actividad por usuario;
5. filas separadas de Balia y Con Prospección en todas las tablas acordadas;
6. totales sin duplicación;
7. trabajo efectivo de Con Prospección incluido en el total global, sin crear
   minutos ociosos propios;
8. exactamente dos imágenes enviadas por `@equipo_alicia_bot` en una prueba
   real, sin usar ningún otro bot.
