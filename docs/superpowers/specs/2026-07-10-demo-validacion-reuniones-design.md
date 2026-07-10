# Portal Demo — Validación de Reuniones

Fecha: 2026-07-10
Estado: aprobado, pendiente de implementación

## Propósito

Entregar a un prospecto comercial un portal navegable, con datos ficticios, que
muestre exactamente lo que Conprospección entrega a sus clientes. El prospecto
accede por su cuenta, recorre el módulo de Validación de Reuniones y entiende el
diferenciador del servicio: la trazabilidad y el rigor con que cada reunión se
valida o se descarta.

Este spec cubre **solo Validación de Reuniones**. Los módulos de Setup
(onboarding del cliente) e Intelligence Insight se abordarán después, cada uno
con su propio ciclo spec → plan → implementación.

## Contexto

Los portales cliente se eliminaron del repo el 2026-07-03 en el commit `0dab1f0`
("Limpieza: solo panel interno"). Las páginas relevantes siguen recuperables:

- `dashboard/pages/18_BambuTech_Validacion_Reuniones.py` (1412 líneas) — la
  versión más evolucionada del módulo. Es la plantilla.
- `dashboard/pages/12_GBS_Validacion_Reuniones.py` — versión anterior.
- `shared/validacion_ui.py` (246 líneas) — helpers de chips, banners y tarjetas.
  **Hoy no existe** en el árbol de trabajo; la página lo necesita.

`shared/validacion.py`, `shared/seguimiento.py` y `shared/metas.py` sí siguen
vivos y no se tocan.

## Decisiones tomadas

| Decisión | Elección |
|---|---|
| Interactividad | Navegable + interacción que no persiste |
| Marca | Conprospección (`shared/cp_design.py`) |
| Ubicación | Página en la app actual, con login propio |
| Datos | 5 reuniones ficticias cubriendo todo el flujo |
| Evidencia | Resumen IA y BANT visibles; grabación y transcripción deshabilitadas |
| Persistencia | Ninguna. Sin Supabase. |
| Meta mensual | 12 reuniones |
| Credenciales | Usuario `DEMO`, contraseña `DEMO2026` |

### Por qué se duplica la página en vez de refactorizar

Se evaluó extraer la página a un renderer parametrizado por fuente de datos, que
el demo y los futuros portales cliente compartirían. Se descartó por ahora: el
demo tiene urgencia comercial y un único consumidor, y hoy no existe ningún
portal cliente vivo contra el cual validar la abstracción. Diseñar la interfaz
compartida con un solo caso concreto produce peores abstracciones que hacerlo
cuando se reconstruya el primer portal cliente real y se sepa qué varía de
verdad entre clientes.

La duplicación es aceptable porque el demo es un artefacto de venta, no código
que evoluciona junto al producto.

## Arquitectura

### Archivos nuevos

- `dashboard/pages/21_Demo_Validacion_Reuniones.py`
- `shared/demo_data.py`
- `shared/validacion_ui.py` (recuperado de `git show 0dab1f0^:shared/validacion_ui.py`)
- `tests/test_demo_data.py`

### Archivos modificados

- `shared/config.py` — agregar `"demo"` a `portal_passwords()`
- `shared/metas.py` — agregar `"demo": {"validas": 12, "tipo": "mensual"}` a `METAS`
- `dashboard/portal_auth.py` — registrar slug `demo` en `_CLIENTS`, su usuario
  esperado en `_check_login`, y su color de acento en `render_client_nav` y
  `require_auth_client`

### Aislamiento

`dashboard/pages/21_Demo_Validacion_Reuniones.py` y `shared/demo_data.py` **no
importan**:

- `requests` ni `supabase`
- `supabase_url` / `supabase_key` de `shared.config`
- **`shared.seguimiento`** — este módulo importa `requests` y las credenciales de
  Supabase, y su `recalcular_final_y_flags()` persiste en la base ("y los
  persiste", dice su propio docstring). La página original lo usa; la demo no
  puede.

Esta es la garantía dura: la página demo es incapaz de leer o escribir en la
base de datos de producción. Un test lo verifica inspeccionando los imports del
módulo.

Sí puede importar `shared.validacion` y `shared.metas`: ambos son puros.
`validacion.py` solo importa `json`, `re` y `datetime.date`; `metas.py` es un
diccionario versionado en git.

## Componentes

### `shared/demo_data.py`

Expone tres funciones con la misma firma y el mismo tipo de retorno que las
funciones de acceso a Supabase que reemplaza en la página original:

- `cargar_reuniones(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame`
- `cargar_seguimiento() -> dict[int, dict]`
- `cargar_historial(reunion_id: int) -> list[dict]`

Además: `guardar_respuesta_cliente(reunion_id, estado, comentario="", motivo=None) -> bool`

Como las firmas coinciden, el resto de la página (KPIs, filtros, chips,
tarjetas, tabla, historial) funciona sin modificación.

La meta no se define aquí. Se agrega `"demo"` a `shared/metas.py` y la página
llama `meta_de("demo")` igual que la original, reusando el mecanismo real.

`cargar_reuniones` ignora el rango de fechas y devuelve siempre las 5 reuniones,
fechadas dentro del mes en curso. Esto evita que el demo aparezca vacío si un
prospecto lo abre meses después.

Las fechas se calculan con `datetime.now(ZoneInfo("America/Santiago"))` dentro
del propio `demo_data`. No se reutiliza `_now_chile()`: esa función es privada y
vive en `dashboard/meeting_shared.py`, y `shared/` no debe depender de
`dashboard/`. Streamlit Cloud corre en UTC, así que usar `datetime.now()` sin
zona produciría fechas corridas — el mismo problema ya documentado para el panel
interno.

### Las 5 reuniones

Empresas y contactos inventados, del rubro logística y manufactura. Ninguno
corresponde a un cliente, prospecto o contacto real.

| # | `_validation_status` | Rol en la demostración |
|---|---|---|
| 1 | `evaluacion_cerrada_valida` | Caso limpio: BANT completo, resumen IA |
| 2 | `cotizacion_valida` | La reunión derivó en cotización |
| 3 | `pendiente_confirmacion_cliente` | El prospecto puede confirmarla |
| 4 | `reagendar` | El proceso maneja el no-show |
| 5 | `evaluacion_cerrada_no_valida` | Rigor: se descartan reuniones fuera de ICP |

Conteo resultante de los KPIs: Total 5, Válidas 2, No válidas 1, Pendiente
cliente 1, En revisión 0, Reagenda 1. La barra de avance muestra 2/12 (17%).

La reunión #3 hace el demo interactivo. La #5 es la de mayor valor comercial:
demuestra que Conprospección descarta reuniones que no cumplen el perfil, en
lugar de inflar resultados.

### Interacción sin persistencia

`guardar_respuesta_cliente()` escribe en
`st.session_state["demo_overrides"][reunion_id]` y devuelve `True`.

`cargar_seguimiento()` fusiona esos overrides sobre los datos base antes de
devolver el diccionario.

Para derivar el estado final, `demo_data` llama directamente a las funciones
puras de `shared/validacion.py` — `derivar_final()`, `flag_disputa()` y
`flag_meta_countable()` — que son exactamente las que
`recalcular_final_y_flags()` usa por dentro antes de persistir. Así las
transiciones de estado que ve el prospecto obedecen las mismas reglas de negocio
del producto real, sin tocar la base.

El historial de la reunión #3 gana una entrada en memoria al confirmarse.

Al recargar la página, `session_state` se limpia y el portal vuelve al estado
inicial. No hay limpieza manual entre demos.

### Evidencia

- Resumen IA y chips BANT: texto ficticio realista, incluido en `demo_data`.
- Botones de Grabación y Transcripción: visibles y deshabilitados, reutilizando
  el estado que la página original ya muestra cuando no hay link
  (`st.button("Grabación no disponible", disabled=True)`).

### Autenticación

`shared/config.py`:

```python
"demo": _get("PORTAL_PASSWORD_DEMO") or "DEMO2026",
```

El fallback en código es deliberado. `DEMO2026` es una credencial pensada para
compartirse por correo con prospectos; no es un secreto. El fallback permite
desplegar sin tocar los secrets de Streamlit Cloud, y la variable de entorno
permite rotarla si hiciera falta.

`dashboard/portal_auth.py`:

- `_CLIENTS["demo"]` con `session_key: "portal_auth_demo"`,
  `logo_file: "conprospeccion_logo.png"`, y `nav` con una sola entrada apuntando
  a la página demo.
- `_check_login`: el mapa `expected_user` gana `"demo": "DEMO"`.
- Acento de marca: `CP_GOLD` / `CP_INK`.

### Visibilidad

El prospecto autenticado en el portal demo **no ve ninguna otra página**:
`render_client_nav` oculta `[data-testid="stSidebarNav"]` y presenta solo los
ítems del slug. Las páginas internas requieren `master_auth` y le negarían el
acceso de todos modos.

El equipo de Conprospección **sí verá** "Demo Validacion Reuniones" en el menú
lateral del panel interno, y podrá entrar sin login gracias a `admin_mode`. Esto
es intencional y aprobado: permite mostrar el demo en vivo durante una reunión.

Ocultar la página también del menú interno exigiría sacarla de
`dashboard/pages/`, lo que rompe el enrutamiento de Streamlit.

Nota sobre `CLAUDE.md`: la regla "no dejar POCs, backups ni experimentos en
`dashboard/pages`" no aplica aquí. El portal demo es un artefacto de producto
mantenido, no un experimento.

### Marca

Se aplican los tokens de `shared/cp_design.py` al cromo de marca:

- Encabezado de página: fondo `CP_INK`, acento `CP_GOLD`
- Acento de navegación y estado activo: `CP_GOLD`
- Barra de avance de meta: `CP_GOLD`
- Tipografía: `FONT_HEAD` (Saira) y `FONT_BODY` (IBM Plex Sans)

**La paleta semántica de estados no cambia.** Verde para válida, rojo para no
válida, ámbar para reagenda, cian para en revisión. Esos colores comunican
significado, no identidad de marca — la misma regla que ya documenta el
docstring de `gbs_brand.py`. Teñirlos de dorado destruiría la legibilidad de los
KPIs.

Ajuste de contraste: el patrón heredado pinta texto blanco sobre el color de
acento. Blanco sobre `#FFD700` no alcanza contraste legible. En el portal demo,
el texto sobre dorado usa `CP_INK`.

## Manejo de errores

La página demo no hace red, así que desaparecen los modos de falla de la
original (timeout de Supabase, respuesta no-`ok`, columnas legacy ausentes). Se
eliminan los bloques de fallback correspondientes en lugar de dejarlos como
código muerto.

Riesgo restante: un `KeyError` si `demo_data` produce un registro al que le
falta una columna que la página espera. Se cubre con un test que construye el
`DataFrame` y verifica que contiene todas las columnas de `base_fields`.

## Testing

`tests/test_demo_data.py`:

1. `cargar_reuniones` devuelve exactamente 5 filas.
2. El `DataFrame` contiene todas las columnas que la página consume.
3. Los `_validation_status` cubren los 5 estados de la tabla, produciendo los
   conteos esperados en los 6 KPIs.
4. Ni `demo_data` ni la página demo importan `requests`, `supabase`,
   `shared.seguimiento`, ni las credenciales de `shared.config`.
5. Un override en `session_state` mueve el conteo de válidas de 2 a 3.
6. Las fechas de las reuniones caen dentro del mes en curso.

Verificación manual: levantar la app, entrar con `DEMO` / `DEMO2026`, recorrer
el flujo completo del prospecto, confirmar la reunión #3, comprobar que el KPI
se mueve y que al recargar vuelve a 2.

## Fuera de alcance

- Módulo de Setup / Onboarding del cliente (`14_GBS_Onboarding.py`)
- Módulo Intelligence Insight
- Refactor de la página de validación a un componente compartido
- Cualquier escritura a Supabase
