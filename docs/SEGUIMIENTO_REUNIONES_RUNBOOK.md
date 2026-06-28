# Runbook - Seguimiento de reuniones

Fecha de referencia: 2026-06-27

Este documento es la guia operativa del panel maestro interno y de su relacion con los portales de validacion de clientes.

## Ruta oficial

Panel interno oficial:

```text
dashboard/pages/1_Seguimiento_Reuniones.py
```

Ruta publica:

```text
https://conprospeccion-os2026.streamlit.app/Seguimiento_Reuniones
```

No usar rutas POC como fuente de verdad.

## Principio de negocio

El flujo funcional tiene cuatro campos independientes:

1. Etapa Agenda
2. Evaluacion CP
3. Evaluacion Cliente
4. Estado Final

Ninguno debe calcular automaticamente al otro.

Etapa Agenda solo describe que ocurrio operacionalmente:

- futura;
- realizada;
- cancelada;
- reagendada;
- u otra etapa operativa definida por Conprospeccion.

Evaluacion CP es independiente de Etapa Agenda. Una reunion cancelada o reagendada puede evaluarse como valida o no valida si existe informacion contractual suficiente.

Evaluacion Cliente solo informa lo que hizo el cliente en su portal:

- pendiente;
- confirmada;
- solicita revision.

Estado Final representa el cierre administrativo y contractual de Conprospeccion. Siempre se define manualmente desde el panel interno. No debe cerrarse automaticamente porque CP evaluo, porque el cliente confirmo o porque existe evidencia.

## Estado del caso

`Estado del Caso` es un campo interno de seguimiento operativo.

Ejemplos:

- Abierto
- En evaluacion CP
- Esperando cliente
- En revision
- Cerrado

No reemplaza Etapa Agenda, Evaluacion CP, Evaluacion Cliente ni Estado Final. No es visible para el cliente.

## Acceso

Panel interno:

- Francisca y Yanina ven todas las reuniones.
- Francisca y Yanina tienen las mismas capacidades.
- No implementar roles internos, RBAC, perfiles de supervisor ni permisos diferenciados.

Portales cliente:

- Cada portal filtra por su cliente.
- El cliente solo ve su proyeccion permitida del registro canonico.
- El cliente no decide Estado Final.

Hoy la separacion esta implementada en la aplicacion con autenticacion interna y autenticacion por cliente. Como mejora futura, Supabase debe reforzar esta separacion con politicas RLS.

## Datos y persistencia

Tablas principales:

- `reuniones`: registro canonico base de reunion, contacto, empresa, agenda, datos GHL, links y evidencia sincronizada.
- `seguimiento_reuniones`: estado operativo interno, evaluaciones, correcciones manuales, visibilidad, textos y overrides de Conprospeccion.
- `meeting_status_history`: auditoria de cambios relevantes.

Regla:

- Los cambios de la tabla y del panel lateral deben guardarse en Supabase.
- Al volver a abrir una reunion, los cambios deben reflejarse desde base de datos.
- El historial registra lo ocurrido, pero no reemplaza los campos operativos principales.
- Una nota manual en historial no debe modificar automaticamente Etapa Agenda, Evaluacion CP, Evaluacion Cliente ni Estado Final.

## SDR asignada

La interfaz usa un solo campo operativo: `SDR asignada`.

Valor inicial:

- usuario asignado al contacto en GoHighLevel, cuando exista;
- vacio si GHL no trae asignacion confiable.

Francisca o Yanina pueden corregirlo desde el panel interno. Si cambia, debe quedar en historial:

- valor anterior;
- valor nuevo;
- usuario que hizo el cambio;
- fecha y hora.

No crear campos separados como SDR que agendo, SDR responsable o SDR operativa hasta que exista una fuente confiable y una necesidad real.

## UI/UX vigente del panel maestro

La estructura general del panel debe mantenerse:

1. Filtros globales
2. Avance por cliente
3. KPIs
4. Tabla principal
5. Panel lateral contextual

Filtros basicos:

- Cliente
- SDR
- Etapa Agenda
- Evaluacion CP
- Evaluacion Cliente
- Estado Final
- Estado del Caso
- Mes
- Ano
- Fecha desde/hasta
- Busqueda por empresa o contacto

La tabla debe mantener encabezado fijo y usar los mismos nombres de estados que el panel lateral.

Columnas funcionales esperadas:

- Fecha y hora
- Cliente
- SDR asignada
- Empresa
- Contacto
- Cargo
- Etapa Agenda
- Evaluacion CP
- Evaluacion Cliente
- Estado Final
- Acciones

## Panel lateral

El panel lateral debe abrirse en la pestana Informacion al seleccionar una reunion.

Pestanas:

- Informacion
- Evaluacion CP
- Evaluacion Cliente
- Estado Final
- Historial

El resumen superior debe mostrar los cuatro estados con nombres consistentes:

- Etapa Agenda
- Evaluacion CP
- Evaluacion Cliente
- Estado Final

Los bloques deben ser compactos. Evitar tarjetas grandes para cada dato.

### Informacion

Organizar en bloques:

- Empresa
- Contacto
- Reunion

Campos vacios no deben ocupar espacios grandes.

### Evaluacion CP

Debe permitir editar:

- resultado CP;
- ICP;
- BANT;
- justificacion visible al cliente;
- nota interna CP;
- evidencia y archivos.

Cada evidencia sincronizada debe permitir decidir si sera visible para el cliente.

### Evaluacion Cliente

Debe mostrar seguimiento del cliente:

- estado actual;
- fecha y hora de ultima accion;
- contacto que realizo la accion, si existe;
- motivo seleccionado, si solicito revision;
- comentario escrito por el cliente;
- historial de cambios de esa evaluacion.

Tambien debe permitir que Conprospeccion registre respuesta o cierre operativo, sin que eso calcule automaticamente Estado Final.

### Estado Final

Debe permitir cierre manual por Conprospeccion.

Diferencia de campos:

- `Motivo final`: razon interna administrativa/contractual del cierre.
- `Texto visible al cliente`: explicacion publicable al cliente cuando corresponde.

### Historial

Mostrar solo eventos utiles para operacion:

- fecha de agenda;
- fecha de reunion realizada;
- cambios de Etapa Agenda;
- cambios de Evaluacion CP;
- cambios de Evaluacion Cliente;
- cambios de Estado Final;
- notas manuales relevantes.

El historial debe permitir agregar, editar o eliminar notas manuales. Los eventos automaticos no deben editarse ni eliminarse.

## Evidencia

Evidencia esperada:

- link de grabacion;
- link de transcripcion;
- resumen IA;
- archivos relevantes;
- comentarios o notas.

El panel interno puede mostrar campos vacios para completarlos. El portal cliente no debe mostrar bloques vacios como "sin grabacion" o "sin transcripcion".

## Proyeccion al portal cliente

El portal cliente debe consumir el mismo registro canonico que el panel interno.

No copiar secciones visuales entre paneles. La proyeccion debe construirse con reglas compartidas equivalentes a:

```text
build_client_meeting_view(meeting, client_id)
```

Debe devolver solo:

- informacion visible;
- campos con contenido;
- evaluacion CP publicable;
- ICP y BANT existentes;
- justificacion visible;
- evidencia marcada como visible;
- validacion cliente;
- estado final;
- historial permitido.

El cliente no puede editar historial, evidencia, BANT, ICP, Evaluacion CP ni Estado Final.

## Reglas pendientes de base de datos

Las politicas RLS futuras deben reforzar:

- Francisca/Yanina: lectura y escritura de todas las reuniones.
- Cliente GBS: lectura solo `cliente_slug = 'gbs'`.
- Cliente Clickie: lectura solo `cliente_slug = 'clickie'`.
- Cliente BambuTech: lectura solo `cliente_slug = 'bambutech'`.
- Clientes: escritura solo de campos permitidos de Evaluacion Cliente, cuando aplique.
- Servicio de sincronizacion: escritura tecnica de datos sincronizados.
- Historial: mostrar al cliente solo eventos marcados como visibles.

Esto no cambia el comportamiento actual de portales; solo lo endurece a nivel base de datos.

## Deploy

Desarrollar en `main`.

Publicar codigo fuente:

```powershell
git push origin main
```

Estado verificado de Streamlit Cloud al 2026-06-27:

```text
App URL: https://conprospeccion-os2026.streamlit.app
Repository: franciscapp/conprospeccionOS2026
Branch: main
Main file path: dashboard/app.py
```

No usar el repo historico `FranciscaPP/conprospeccion-os` para nuevos cambios.

No desarrollar en `master`.

## Archivos obsoletos

No deben existir POCs, backups ni experimentos dentro de `dashboard/pages`, porque Streamlit los puede convertir en paginas visibles.

Si se necesita conservar una referencia historica, ubicarla fuera del arbol activo y documentar claramente que no es producto.
