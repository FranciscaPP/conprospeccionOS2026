# Equipo Alicia: reporte tabular en dos imágenes

Fecha: 2026-10-01

Estado: aprobado visualmente en `reporte-tablas-v2.html`.

## Objetivo

Reemplazar las tarjetas verticales del reporte horario de `@equipo_alicia_bot`
por dos imágenes PNG con tablas de ancho fijo. El reporte debe permitir entender
de inmediato tareas, llamadas, correos, WhatsApp, tiempo trabajado, adherencia y
actividad fuera de horario sin que los números se desplacen en Telegram.

Las reuniones de hoy y la adherencia conservan su significado. Este diseño
reemplaza únicamente la presentación y las fórmulas centrales de tareas,
llamadas, correos, WhatsApp y tiempo.

## Identidad visual

- BAMBU TECH: verde.
- GBS: morado.
- BALIA: rosado.
- TOTAL: gris.
- TOTAL TRABAJO: verde.
- TOTAL SIN TRABAJAR: amarillo.
- Encabezados: gris neutro.
- Todos los números usan columnas de ancho fijo, alineación centrada y cifras
  tabulares.

No se usan tablas HTML ni bloques monoespaciados de Telegram. El resultado se
renderiza a PNG para conservar el mismo aspecto en teléfono y computador.

## Entrega

Cada corte genera exactamente dos imágenes:

1. Reuniones, tareas, llamadas en cantidad, llamadas en minutos y tiempo de
   llamadas.
2. Correos, WhatsApp, total trabajado/sin trabajar, adherencia a bloques y
   trabajo fuera de horario.

Cada imagen lleva la fecha, hora de corte, SDR Nora e indicador `1 de 2` o
`2 de 2`. El envío textual se limita a una leyenda breve; no repite todas las
tablas.

## Imagen 1

### Reuniones de hoy

Columnas:

- Cliente.
- Contacto / empresa.
- Hora Chile.
- Hora Perú.

Filas: BAMBU TECH, GBS, BALIA y TOTAL. Las reuniones canceladas o `noshow` no
cuentan.

### Tareas

Columnas:

- Cliente.
- Atrasadas.
- Hoy.
- Total.
- Avance.
- Pendiente.

Definiciones:

- `Atrasadas`: tareas abiertas cuya fecha corresponde exclusivamente al día
  anterior.
- `Hoy`: tareas cuya fecha corresponde exclusivamente al día del reporte.
- `Total = Atrasadas + Hoy`.
- `Avance`: cantidad completada del universo Total y porcentaje sobre Total,
  con formato `18 · 60%`.
- `Pendiente = Total - cantidad completada`.

La fila TOTAL vuelve a calcular el porcentaje desde las sumas globales; no
promedia los porcentajes de los clientes.

### Llamadas N°

Columnas:

- Cliente.
- Hoy.
- Contestadas `>20 s`.
- Sin contestar `≤20 s`.

`Hoy = Contestadas + Sin contestar`. Una llamada de exactamente 20 segundos se
clasifica como sin contestar. Las filas son BAMBU TECH, GBS, BALIA y TOTAL.

Esta tabla principal incluye solo llamadas dentro de la jornada oficial y fuera
del almuerzo. Las llamadas antes de las 11:00, durante 16:00–17:00 o después de
las 20:00 aparecen únicamente en la tabla FUERA DE HORARIO.

### Llamadas minutos

Columnas:

- Cliente.
- Hoy.
- Contestadas `>20 s`.
- Sin contestar `≤20 s`.

Definiciones:

- `Contestadas`: suma de duración real de las llamadas mayores a 20 segundos.
- `Sin contestar`: suma del tiempo telefónico de las llamadas de 20 segundos o
  menos.
- `Hoy = Contestadas + Sin contestar`.

Debajo se muestra un único resumen:

- `Trabajados`: total de minutos telefónicos dentro de jornada.
- `Sin trabajar`: minutos laborales transcurridos al corte menos minutos
  telefónicos dentro de jornada.

## Imagen 2

### Correos

Columnas:

- Cliente.
- Pendiente.
- Hoy.
- Total.
- Respondidos.
- Sin responder.

La unidad es conversación que requiere respuesta, no cantidad bruta de mensajes.

- `Pendiente`: conversaciones recibidas el día anterior que seguían abiertas al
  comenzar hoy.
- `Hoy`: conversaciones recibidas hoy que requieren respuesta.
- `Total = Pendiente + Hoy`.
- `Respondidos`: conversaciones del universo Total que recibieron una respuesta
  manual hoy.
- `Sin responder = Total - Respondidos`.

Una salida `workflow` no cuenta como respuesta manual. La fila TOTAL suma los
tres clientes. Se elimina la tabla inferior de tiempo exclusivo de correos.

### WhatsApp

Columnas y fórmulas idénticas a Correos:

- Cliente.
- Pendiente.
- Hoy.
- Total.
- Respondidos.
- Sin responder.

Para BAMBU TECH los datos se obtienen de `TYPE_WHATSAPP` en GHL. Para GBS y
BALIA se usan cifras manuales suministradas por Francisca; cuando no existan,
se muestra `N/D` y la fila TOTAL identifica que es parcial. Se elimina la tabla
inferior de tiempo exclusivo de WhatsApp.

## Tiempo total

La jornada oficial es 11:00–20:00 Chile, excluyendo almuerzo 16:00–17:00. El
máximo diario transcurrido es ocho horas.

Los minutos laborales transcurridos se calculan siempre en hora Chile:

- antes de las 11:00: 0 minutos;
- entre 11:00 y 16:00: minutos transcurridos desde las 11:00;
- entre 16:00 y 17:00: 300 minutos;
- entre 17:00 y 20:00: 300 minutos más los transcurridos desde las 17:00;
- desde las 20:00: 480 minutos.

`TOTAL TRABAJO` se expresa en horas y minutos y suma únicamente:

- minutos telefónicos dentro de jornada;
- cinco minutos por conversación de correo respondida;
- cinco minutos por conversación WhatsApp respondida.

`TOTAL SIN TRABAJAR = minutos laborales transcurridos - TOTAL TRABAJO`, con
mínimo cero. También se expresa en horas y minutos.

Los minutos de llamadas fuera de horario se muestran aparte y no reducen TOTAL
SIN TRABAJAR.

## Adherencia a bloques

Columnas:

- Bloque Chile.
- Cliente.
- Llamadas.
- Otros clientes.
- Resultado.

Se mantienen los bloques aprobados por día y cliente. `Resultado` muestra el
porcentaje de llamadas del cliente correcto sobre todas las llamadas dentro del
bloque. Un bloque sin llamadas muestra `Sin actividad registrada` y no inventa
un porcentaje.

## Trabajo fuera de horario

Filas: BAMBU TECH, GBS, BALIA y TOTAL.

Grupos de columnas:

- Antes de 11:00: N° y minutos.
- Almuerzo 16:00–17:00: N° y minutos.
- Después de 20:00: N° y minutos.
- Total fuera: N° y minutos.

Estas llamadas no aparecen en las tablas principales de llamadas y no reducen
los minutos sin trabajar de la jornada oficial.

## Datos y faltantes

- Nunca se inventan datos ausentes.
- `N/D` significa que la fuente no está disponible o no es verificable.
- Los totales parciales deben identificarse como parciales cuando falte un
  cliente.
- Los datos ficticios de la maqueta no se incorporan al reporte real.

## Relación con otras funciones aprobadas

Este diseño no elimina las funciones descritas en
`2026-09-29-equipo-alicia-live-queries-meeting-alerts-design.md`:

- consultas específicas en vivo;
- alerta de reuniones cada tres horas, 24/7;
- protección contra reportes duplicados.

Las consultas conversacionales usan las mismas definiciones que estas tablas.

## Pruebas de aceptación

- Las dos imágenes mantienen columnas alineadas y miden 1200 px de ancho.
- Cada tabla contiene BAMBU TECH, GBS, BALIA y TOTAL.
- `Atrasadas + Hoy = Total` y `cantidad completada indicada en Avance +
  Pendiente = Total` en tareas.
- `Contestadas + Sin contestar = Hoy` en cantidad y minutos de llamadas.
- `Pendiente + Hoy = Total` y `Respondidos + Sin responder = Total` en correos
  y WhatsApp.
- Una llamada de 20 segundos cuenta como sin contestar.
- El total trabajado aplica las ponderaciones aprobadas de cinco minutos.
- Fuera de horario no modifica el total sin trabajar.
- Los colores y rótulos coinciden con la maqueta V2 aprobada.
- Ningún texto o cifra invade otra celda en la imagen final.
