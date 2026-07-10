# Portal Demo — Panel de Seguimiento de Reuniones

Fecha: 2026-07-10
Estado: implementado

## Propósito

Entregar a un prospecto comercial un portal navegable, con datos ficticios, que
muestre exactamente lo que Conprospección opera. El prospecto accede por su
cuenta, recorre el panel de Seguimiento de Reuniones y entiende el diferenciador
del servicio: la trazabilidad y el rigor con que cada reunión se valida o se
descarta.

## Corrección de rumbo

La primera versión de este spec apuntaba al portal *cliente* de validación de
reuniones, recuperado de `18_BambuTech_Validacion_Reuniones.py`. Era la página
equivocada.

La página a replicar es el **panel interno**,
`dashboard/pages/1_Seguimiento_Reuniones.py`, el que vive en
<https://conprospeccion-os2026.streamlit.app/Seguimiento_Reuniones>. Se reconoce
por "Avance por cliente", el KPI "Pendiente CP", el filtro de SDR y el botón
"+ Nueva reunión".

El trabajo de la primera versión quedó fuera del árbol, en el scratchpad de la
sesión. Los módulos `shared/validacion_ui.py` y `shared/icp_summary.py` que se
habían recuperado de git para sostenerlo se eliminaron de nuevo.

## Hallazgo que definió la solución

El panel interno no está construido con widgets de Streamlit. Es una página
HTML+JavaScript completa, guardada como un string (`POC_HTML`) dentro de la
página. Streamlit solo la monta como componente. Los datos entran por una única
sustitución:

```python
real_meetings = cargar_reuniones_reales_poc()
POC_HTML = re.sub(r"let meetings=\[[\s\S]*?\];\nconst storageKey=", ...)
```

Replicar el panel es, por lo tanto, **cambiar ese JSON**. No hay que reimplementar
la interfaz.

## Decisiones tomadas

| Decisión | Elección |
|---|---|
| Página fuente | `1_Seguimiento_Reuniones.py` (panel interno) |
| Interactividad | Navegable; los cambios viven en el navegador |
| Persistencia | Ninguna. Sin Supabase. |
| Cliente | Uno solo, "Cliente Demo" |
| Contactos | "Lead Demo N" / "Empresa Demo N" |
| Meta mensual | 12 reuniones válidas |
| Credenciales | Usuario `DEMO`, contraseña `DEMO2026` |
| Evidencia | Resumen IA sí; grabación y transcripción sin enlace |

## Arquitectura

### Archivos nuevos

- `dashboard/seguimiento_poc_template.py` — la plantilla HTML, extraída de la
  página interna, más `construir_html_demo()`
- `dashboard/pages/21_Demo_Panel_Reuniones.py` — la página demo
- `shared/demo_data.py` — las 11 reuniones ficticias
- `tests/test_demo_data.py`

### Archivos modificados

- `dashboard/pages/1_Seguimiento_Reuniones.py` — ahora importa `POC_HTML` desde
  la plantilla en vez de definirlo. Es un movimiento puro: 300 líneas menos.
- `shared/config.py` — `"demo"` en `portal_passwords()`
- `shared/metas.py` — `"demo": {"validas": 12, "tipo": "mensual"}`
- `dashboard/portal_auth.py` — slug `demo` en `_CLIENTS`, usuario esperado,
  acento dorado

### Por qué una plantilla compartida

El panel interno y el demo montan **el mismo** archivo HTML. Si mañana mejoras la
interfaz del panel, el demo la hereda sin tocarlo. Un demo que se desincroniza
del producto es peor que no tener demo: le promete al prospecto algo que ya no
entregas.

La plantilla no tiene dependencias de red — solo `json` y `re` — para que la
página demo pueda importarla sin arrastrar Supabase.

### Aislamiento

`21_Demo_Panel_Reuniones.py`, `shared/demo_data.py` y
`seguimiento_poc_template.py` **no importan** `requests`, `supabase`,
`shared.config` ni `meeting_shared`.

Esta es la garantía dura: el demo es incapaz de leer o escribir en la base de
producción. Tres tests lo verifican inspeccionando los imports con `ast`.

La página descarta deliberadamente el payload que el componente devuelve al
guardar, crear o eliminar. No hay backend al que escribir.

## Componentes

### `shared/demo_data.py`

`cargar_reuniones_demo()` sustituye a `meeting_shared.cargar_reuniones_reales_poc()`,
que lee cinco tablas de Supabase. Devuelve la misma lista de diccionarios que
consume el JavaScript, con los mismos ~50 campos.

**Vocabulario de estados.** Los valores deben calzar exactamente con los labels
que produce el panel interno, o los filtros del prospecto no encuentran nada:

- `status`: Reunión futura · Reunión realizada · Reunión cancelada · Reagendar reunión
- `cp`: Válida · No válida · Pendiente
- `clientVal`: Válida · No válida · Solicita revisión · Pendiente
- `final`: Reunión válida · Reunión no válida · Reunión cancelada · Reagendar reunión · Pendiente
- `caseStatus`: Cerrado · En revisión · En evaluación CP · Esperando cliente · Abierto

### Las 11 reuniones

Cada una existe para que un estado del panel tenga contenido. Si un filtro o un
KPI queda en cero, el prospecto no ve para qué sirve.

| Lead | Estado | Rol en la demostración |
|---|---|---|
| 1, 2, 3 | Reunión válida | El caso limpio, con BANT y resumen IA |
| 4 | Esperando cliente | Válida para CP, pendiente de confirmación |
| 5 | En revisión | El cliente disputa la evaluación |
| 6 | Reunión no válida | Rigor: se descarta lo que no cumple ICP |
| 7 | En evaluación CP | Todavía sin resolver internamente |
| 8 | Reagendar | El no-show se recupera |
| 9 | Cancelada | El proceso registra la cancelación |
| 10, 11 | Reunión futura | Hay agenda por delante |

KPIs resultantes: Total 11, Válidas 3, No válidas 1. Avance de meta: 3/12 (25%),
etiquetado "A MEDIAS".

La reunión 6 es la de mayor valor comercial: demuestra que Conprospección
descarta reuniones fuera de perfil en lugar de inflar resultados.

### Fechas ancladas al mes en curso

El panel filtra por mes en curso por defecto. Si las reuniones cayeran en el mes
anterior, el prospecto abriría el demo y lo vería vacío. Por eso las fechas se
reparten dentro del mes actual — las pasadas entre el día 1 y hoy, las futuras
entre mañana y fin de mes — en vez de usar un desplazamiento fijo desde hoy.

Casos borde asumidos: el día 1 no hay pasado dentro del mes y todas quedan en
hoy; el último día del mes las futuras se van al mes siguiente. Ambos son
preferibles a un panel vacío.

Las fechas se calculan con `ZoneInfo("America/Santiago")` dentro de `demo_data`.
No se reutiliza `_now_chile()`: es privada, vive en `dashboard/meeting_shared.py`,
y `shared/` no debe depender de `dashboard/`. Streamlit Cloud corre en UTC.

### Anonimización

La plantilla trae la identidad del equipo interno escrita en el HTML: el
encabezado dice "Francisca / Yanina — Panel interno", y ese mismo nombre queda
como autor de cada evento del historial que el usuario crea.

`construir_html_demo()` los reemplaza por "Usuario Demo" y "Vista de
demostración". El panel interno no se toca.

Tres tests cubren esto: que el HTML generado no contenga esos nombres, que no
aparezca ningún cliente real (`gbs`, `bambutech`, `clickie`, `tiresias`,
`ecosmart`, `just4u`) en los datos, y que todos los contactos sean "Lead Demo N".

### Estado del navegador

El demo usa `storageKey = "cp_meetings_demo_v1"`, distinta de la del panel
interno. No comparten estado.

A diferencia del panel interno —que bloquea la restauración desde `localStorage`
porque su verdad está en Supabase— el demo la conserva. Eso es justamente lo que
permite al prospecto ver sus propios cambios sin que nada se escriba en el
servidor.

### Autenticación

`shared/config.py`:

```python
"demo": _get("PORTAL_PASSWORD_DEMO") or "DEMO2026",
```

El fallback en código es deliberado. `DEMO2026` es una credencial pensada para
compartirse con prospectos; no es un secreto. La variable de entorno permite
rotarla sin tocar el código.

### Visibilidad

El prospecto autenticado no ve ninguna otra página: `render_client_nav` oculta la
navegación y las páginas internas exigen `master_auth`.

El equipo de Conprospección sí verá "Demo Panel Reuniones" en su menú lateral, y
podrá entrar sin login gracias a `admin_mode`. Es intencional: permite mostrar el
demo en vivo durante una reunión.

## Manejo de errores

El demo no hace red, así que desaparecen los modos de falla de la página real.

Riesgo restante: que alguien edite la plantilla y elimine el bloque
`let meetings=[...]`. En ese caso el demo mostraría, en silencio, las reuniones
de ejemplo que trae el HTML. `construir_html_demo()` levanta
`PlantillaDesincronizada` en vez de fallar callando, y la página lo reporta.

## Testing

`tests/test_demo_data.py`, 22 tests:

- Aislamiento: ni la página, ni `demo_data`, ni la plantilla importan red.
- Anonimato: sin nombres del equipo ni de clientes reales.
- Forma: claves que el JavaScript consume, BANT con sus cuatro variables, ids únicos.
- Vocabulario: todos los estados dentro de los conjuntos válidos.
- Historia: los cuatro estados de agenda tienen al menos una reunión; 3 válidas,
  1 no válida, 1 cancelada, 1 reagendada; la no válida explica por qué.
- Fechas: las futuras en el futuro, el resto en el pasado.
- Evidencia: sin grabaciones ni transcripciones.
- Plantilla: falla ruidosamente si pierde el punto de inyección.

Verificación manual: se levantó la app, se entró con `DEMO` / `DEMO2026` y se
recorrió el panel. 11 filas, KPIs 11/3/1, "Cliente Demo 25% · 3/12 · A MEDIAS",
el cajón de detalle abre con "Grabación: Sin enlace".

## Fuera de alcance

- Módulo de Setup / Onboarding del cliente (`14_GBS_Onboarding.py`, eliminado en `0dab1f0`)
- Módulo Intelligence Insight
- Portal cliente de validación de reuniones
- Cualquier escritura a Supabase

## Deuda conocida

- `tests/test_dedup_reuniones.py` falla desde el commit `bc1bccf`, que eliminó
  los marcadores `# <<DEDUP-PURO>>` que ese test busca. No tiene relación con
  este trabajo.
- La tarjeta de "Cliente Demo" en "Avance por cliente" sale en gris: el
  JavaScript asigna color por slug y `demo` no tiene uno. Cosmético.
