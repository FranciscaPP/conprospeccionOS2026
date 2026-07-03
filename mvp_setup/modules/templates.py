"""
Genera el contenido de todos los archivos base por cliente.
"""
import json
from datetime import datetime
from pathlib import Path


def _f(datos: dict, clave: str, default: str = "[PENDIENTE]") -> str:
    val = datos.get(clave, "")
    return str(val) if val else default


def _hoy() -> str:
    return datetime.now().strftime("%Y-%m-%d")


# ─────────────────────────────────────────────
# 01_ADMIN_CLIENTE
# ─────────────────────────────────────────────

def tpl_datos_cliente(datos: dict) -> str:
    return f"""# Datos del Cliente: {_f(datos, 'nombre_cliente')}

**Fecha de creación:** {_hoy()}
**Última actualización:** {_hoy()}

---

## Información General

| Campo | Valor |
|-------|-------|
| Nombre cliente | {_f(datos, 'nombre_cliente')} |
| Sitio web | {_f(datos, 'sitio_web')} |
| País objetivo | {_f(datos, 'pais_objetivo')} |
| Fecha inicio setup | {_f(datos, 'fecha_inicio_setup', 'pendiente')} |
| Fecha término setup | {_f(datos, 'fecha_fin_setup', 'pendiente')} |
| Fecha inicio prospección | {_f(datos, 'fecha_inicio_prospeccion', 'pendiente')} |

---

## Descripción del Negocio

{_f(datos, 'descripcion', '[Completar descripción del negocio]')}

---

## Objetivo Comercial

{_f(datos, 'objetivo_comercial', '[Completar objetivo comercial]')}

---

## Datos del Prospector SDR

| Campo | Valor |
|-------|-------|
| Nombre | {_f(datos, 'nombre_prospector', 'pendiente')} |
| Cargo | {_f(datos, 'cargo_prospector', 'pendiente')} |
| Correo | {_f(datos, 'correo', 'pendiente')} |
| Teléfono | {_f(datos, 'telefono', 'pendiente')} |
| LinkedIn | {_f(datos, 'linkedin', 'pendiente')} |
| Web Conprospección | {_f(datos, 'web_conprospeccion', 'conprospeccion.com')} |

---

## Notas Internas

{_f(datos, 'notas_internas', '[Sin notas todavía]')}
"""


def tpl_informacion_original_cliente(datos: dict) -> str:
    return f"""# Información Original del Cliente: {_f(datos, 'nombre_cliente')}

**Fecha de ingreso:** {_hoy()}

> Este archivo guarda exactamente lo que el cliente nos entregó en el onboarding.
> No modificar. Ver analisis_web.md y resumen_servicio.md para la versión procesada.

---

## Descripción entregada por el cliente

{_f(datos, 'descripcion', '[Completar con lo que el cliente dijo textualmente]')}

---

## Objetivo comercial declarado

{_f(datos, 'objetivo_comercial', '[Completar con palabras del cliente]')}

---

## Documentos entregados

_Listar aquí los documentos que el cliente envió (ya ordenados en 00_INPUT_CLIENTE)_

- [ ] Sin documentos aún

---

## Reunión de onboarding

- **Fecha:** [pendiente]
- **Participantes:** [pendiente]
- **Resumen:** [pendiente]
"""


def tpl_informacion_pendiente(datos: dict) -> str:
    campos_comerciales = []
    comerciales = [
        ("fecha_inicio_setup", "Fecha inicio setup"),
        ("fecha_fin_setup", "Fecha término setup"),
        ("fecha_inicio_prospeccion", "Fecha inicio prospección"),
        ("fecha_fin_prospeccion", "Fecha término prospección"),
        ("meta_total_reuniones", "Meta total de reuniones"),
        ("meta_mensual_reuniones", "Meta mensual de reuniones"),
        ("tipo_meta", "Tipo de meta"),
        ("garantia_total", "Garantía total"),
        ("monto_setup", "Monto setup"),
        ("monto_mensual", "Monto mensual"),
        ("monto_variable", "Monto variable por reunión"),
        ("moneda", "Moneda"),
        ("sdr_asignados", "SDR asignados"),
        ("canales_activos", "Canales activos"),
    ]
    for clave, label in comerciales:
        val = datos.get(clave, "")
        if not val:
            campos_comerciales.append(f"- [ ] {label}")

    pendientes_str = "\n".join(campos_comerciales) if campos_comerciales else "- ✅ Sin campos comerciales pendientes"

    return f"""# Información Pendiente: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}

---

## Campos Comerciales Pendientes

{pendientes_str}

---

## Información Estratégica Pendiente

- [ ] Logo oficial confirmado
- [ ] Colores de marca confirmados
- [ ] Casos de éxito para usar en prospección
- [ ] Industrias que NO quieren prospectar
- [ ] Qué consideran una reunión válida
- [ ] Qué tipo de empresa es su mejor cliente
- [ ] Objeciones más frecuentes
- [ ] Diferenciadores clave vs. competencia

---

## Próximas acciones para completar

1. [ ] Enviar brief_cliente_interactivo.html al cliente
2. [ ] Reunión de kickoff si no se ha hecho
3. [ ] Confirmar datos del prospector SDR
4. [ ] Validar descripción del negocio con cliente
"""


def tpl_condiciones_comerciales(datos: dict) -> str:
    return f"""# Condiciones Comerciales: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}

---

## Resumen Económico

| Concepto | Valor |
|----------|-------|
| Moneda | {_f(datos, 'moneda', 'USD')} |
| Monto setup | {_f(datos, 'monto_setup', 'pendiente')} |
| Monto mensual | {_f(datos, 'monto_mensual', 'pendiente')} |
| Monto variable por reunión | {_f(datos, 'monto_variable', 'pendiente')} |
| Garantía total | {_f(datos, 'garantia_total', 'pendiente')} |

---

## Metas

| Concepto | Valor |
|----------|-------|
| Meta total de reuniones | {_f(datos, 'meta_total_reuniones', 'pendiente')} |
| Meta mensual | {_f(datos, 'meta_mensual_reuniones', 'pendiente')} |
| Tipo de meta | {_f(datos, 'tipo_meta', 'pendiente')} |

---

## Equipo y Canales

| Concepto | Valor |
|----------|-------|
| SDR asignados | {_f(datos, 'sdr_asignados', 'pendiente')} |
| Canales activos | {_f(datos, 'canales_activos', 'pendiente')} |

---

## Fechas Clave

| Etapa | Fecha |
|-------|-------|
| Inicio setup | {_f(datos, 'fecha_inicio_setup', 'pendiente')} |
| Término setup | {_f(datos, 'fecha_fin_setup', 'pendiente')} |
| Inicio prospección | {_f(datos, 'fecha_inicio_prospeccion', 'pendiente')} |
| Término prospección | {_f(datos, 'fecha_fin_prospeccion', 'pendiente')} |

---

## Criterios de Reunión Válida

_Completar después de alinear con cliente_

- [ ] Pendiente definir
"""


def tpl_metas_campana(datos: dict) -> str:
    return f"""# Metas de Campaña: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}

---

## Metas Definidas

- **Meta total:** {_f(datos, 'meta_total_reuniones', 'pendiente')} reuniones
- **Meta mensual:** {_f(datos, 'meta_mensual_reuniones', 'pendiente')} reuniones/mes
- **Tipo de meta:** {_f(datos, 'tipo_meta', 'pendiente')}

---

## Criterios de Reunión Válida

> Completar luego de alinear con el cliente.

- [ ] Definir qué cargo debe asistir
- [ ] Definir qué industria debe ser
- [ ] Definir tamaño mínimo de empresa
- [ ] Definir qué cuenta como NO válida
- [ ] Confirmar duración mínima de la reunión

---

## Seguimiento de Progreso

| Mes | Meta | Reuniones agendadas | Reuniones válidas | Tasa |
|-----|------|--------------------|--------------------|------|
| Mes 1 | {_f(datos, 'meta_mensual_reuniones', '-')} | - | - | - |
| Mes 2 | {_f(datos, 'meta_mensual_reuniones', '-')} | - | - | - |
| Mes 3 | {_f(datos, 'meta_mensual_reuniones', '-')} | - | - | - |

---

## Notas

_Agregar notas de seguimiento aquí_
"""


def tpl_firma_comercial(datos: dict) -> str:
    return f"""# Firma Comercial: {_f(datos, 'nombre_cliente')}

**Fecha generación:** {_hoy()}

---

## Datos de la Firma

- **Nombre SDR:** {_f(datos, 'nombre_prospector', 'pendiente')}
- **Cargo:** {_f(datos, 'cargo_prospector', 'pendiente')}
- **Correo:** {_f(datos, 'correo', 'pendiente')}
- **Teléfono:** {_f(datos, 'telefono', 'pendiente')}
- **Web:** {_f(datos, 'sitio_web', 'pendiente')}
- **LinkedIn:** {_f(datos, 'linkedin', 'No definido')}

---

## Estado

- [ ] Firma HTML generada → ver firma_email.html
- [ ] Logo seleccionado
- [ ] Firma aprobada
- [ ] Firma instalada en cliente de correo

---

## Archivo HTML

Ver: `01_ADMIN_CLIENTE/firma_email.html`
Copia en: `02_BRANDING_Y_ACTIVOS/firma_email.html`
"""


# ─────────────────────────────────────────────
# 03_ANALISIS_CLIENTE
# ─────────────────────────────────────────────

def tpl_analisis_web(datos: dict) -> str:
    return f"""# Análisis Web: {_f(datos, 'nombre_cliente')}

**URL analizada:** {_f(datos, 'sitio_web')}
**Fecha análisis:** {_hoy()}
**Estado:** PENDIENTE — completar con Claude

---

## Resumen de la Web

_Pedir a Claude: "Analiza la web de {_f(datos, 'sitio_web')} y dame un resumen del servicio, propuesta de valor, mercados que atiende y cargos que toman la decisión."_

[COMPLETAR CON ANÁLISIS]

---

## Servicios/Productos Identificados

1. [servicio 1]
2. [servicio 2]
3. [servicio 3]

---

## Mercados que Atienden (según web)

- [mercado 1]
- [mercado 2]

---

## Propuesta de Valor Visible

[Completar]

---

## Tono de Comunicación

- [ ] Formal
- [ ] Semi-formal
- [ ] Casual
- [ ] Técnico
- [ ] Comercial

---

## Observaciones

[Completar]
"""


def tpl_resumen_servicio(datos: dict) -> str:
    return f"""# Resumen del Servicio: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}
**Estado:** PENDIENTE — completar con Claude

---

## Descripción Base del Cliente

{_f(datos, 'descripcion', '[Completar]')}

---

## Resumen Procesado

_Versión depurada y lista para usar en prospección_

[COMPLETAR CON CLAUDE]

---

## Qué hace en una línea

> [Completar: "{_f(datos, 'nombre_cliente')} ayuda a [QUIÉN] a [QUÉ RESULTADO] mediante [CÓMO]"]

---

## Qué hace en tres líneas

[Completar]

---

## Para usar en pitch

[Completar]
"""


def tpl_propuesta_valor(datos: dict) -> str:
    return f"""# Propuesta de Valor: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}
**Estado:** PENDIENTE — completar con Claude

---

## Propuesta de Valor Principal

[COMPLETAR CON CLAUDE]

---

## Beneficios Clave (para el prospecto)

1. [beneficio 1]
2. [beneficio 2]
3. [beneficio 3]

---

## Resultado Esperado por el Cliente

[Completar]

---

## Diferencia vs. No Contratarlos

[Completar: ¿Qué pasa si el prospecto NO contrata a {_f(datos, 'nombre_cliente')}?]
"""


def tpl_problemas_que_resuelve(datos: dict) -> str:
    return f"""# Problemas que Resuelve: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}
**Estado:** PENDIENTE — completar con Claude

---

## Dolores Principales que Resuelven

| # | Dolor del prospecto | Cómo lo resuelven |
|---|--------------------|--------------------|
| 1 | [dolor] | [solución] |
| 2 | [dolor] | [solución] |
| 3 | [dolor] | [solución] |

---

## Frases de Dolor para Mensajería

_Estas frases van directo a los mensajes de apertura_

- "¿Tienes problemas con...?"
- "Muchas empresas nos contactan cuando..."
- "Sabemos que es difícil cuando..."

[COMPLETAR CON CLAUDE]
"""


def tpl_diferenciadores(datos: dict) -> str:
    return f"""# Diferenciadores: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}
**Estado:** PENDIENTE — completar con cliente y Claude

---

## Diferenciadores vs. Competencia

1. [diferenciador 1]
2. [diferenciador 2]
3. [diferenciador 3]

---

## Por qué elegirnos sobre alternativas

[Completar]

---

## Prueba Social / Credibilidad

- Clientes actuales que podemos mencionar: [pendiente]
- Casos de éxito: [pendiente]
- Métricas: [pendiente]
"""


def tpl_informacion_no_confirmada(datos: dict) -> str:
    return f"""# Información No Confirmada: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}

> Este archivo guarda suposiciones, inferencias y datos que aún no han sido validados
> directamente con el cliente. Nunca usar en campañas sin validar primero.

---

## Suposiciones de Análisis Web

- [ ] [suposición 1 — pendiente validar]
- [ ] [suposición 2 — pendiente validar]

---

## Información Inferida (no declarada)

[Completar a medida que se analiza]

---

## Preguntas para Validar con el Cliente

1. [pregunta]
2. [pregunta]

---

## Validaciones Completadas

_Mover aquí los ítems que el cliente confirme_
"""


# ─────────────────────────────────────────────
# 04_ICP_ESTRATEGIA
# ─────────────────────────────────────────────

def tpl_icp_borrador(datos: dict) -> str:
    return f"""# ICP Borrador: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}
**Estado:** BORRADOR — no usar hasta aprobación
**⚠️ Ver icp_master.md para versión oficial aprobada**

---

## Perfil de Empresa Objetivo

| Atributo | Descripción |
|----------|-------------|
| Industrias objetivo | [COMPLETAR CON CLAUDE] |
| Tamaño empresa | [empleados / facturación] |
| País / región | {_f(datos, 'pais_objetivo')} |
| Tecnología / herramientas | [si aplica] |
| Madurez digital | [si aplica] |

---

## Perfil de Cargo Objetivo

| Atributo | Descripción |
|----------|-------------|
| Cargo principal | [COMPLETAR] |
| Cargos secundarios | [COMPLETAR] |
| Nivel jerárquico | [C-Level / Director / Gerente / Jefe] |
| Área | [Área específica] |

---

## Criterios de Calificación

### ✅ Incluir si...
- [criterio 1]
- [criterio 2]

### ❌ Excluir si...
- [criterio 1]
- [criterio 2]

---

## Fuente

Basado en:
- [ ] Análisis web
- [ ] Descripción del cliente
- [ ] Reunión de onboarding
- [ ] Aprobación cliente

---

> **⚠️ REGLA:** Este ICP no reemplaza a icp_master.md.
> Ninguna herramienta debe redefinir el ICP sin crear nueva versión y pedir aprobación.
"""


def tpl_icp_master(datos: dict) -> str:
    return f"""# ICP Master: {_f(datos, 'nombre_cliente')}

**Fecha de aprobación:** [PENDIENTE APROBACIÓN]
**Estado:** ⏳ PENDIENTE — este archivo es la fuente oficial SOLO después de aprobación

---

> **INSTRUCCIÓN PARA TODAS LAS HERRAMIENTAS:**
> Este archivo es la fuente oficial del ICP de {_f(datos, 'nombre_cliente')}.
> Ningún agente, script o herramienta debe redefinir este ICP sin crear una nueva versión
> en 99_HISTORICO/ y obtener aprobación explícita.

---

## ICP Aprobado

_Este archivo se completa cuando se aprueba icp_borrador.md_

[PENDIENTE APROBACIÓN DE ICP EN LA APP]

---

## Historial de Versiones

| Versión | Fecha | Cambio | Aprobado por |
|---------|-------|--------|--------------|
| v1.0 | [fecha] | Versión inicial | [nombre] |
"""


def tpl_macro_industrias(datos: dict) -> str:
    return f"""# Macro Industrias: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}
**Estado:** PENDIENTE — completar con Claude

---

## Instrucción para Claude

"Para {_f(datos, 'nombre_cliente')}, cuyo servicio es: {_f(datos, 'descripcion', '[descripción]')},
y cuyo objetivo es: {_f(datos, 'objetivo_comercial', '[objetivo]')},
¿cuáles son las macro industrias que deberíamos prospectar, ordenadas por prioridad?"

---

## Macro Industrias Definidas

| # | Macro Industria | Prioridad | Razón |
|---|----------------|-----------|-------|
| 1 | [industria] | Alta | [razón] |
| 2 | [industria] | Media | [razón] |
| 3 | [industria] | Baja | [razón] |

---

## Industrias a Excluir

- [industria excluida y por qué]

---

## Validado por cliente: ⏳ Pendiente
"""


def tpl_micro_industrias(datos: dict) -> str:
    return f"""# Micro Industrias: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}
**Estado:** PENDIENTE — completar con Claude

---

## Micro Industrias por Macro

### [Macro Industria 1]
- [micro 1]
- [micro 2]
- [micro 3]

### [Macro Industria 2]
- [micro 1]
- [micro 2]

---

## Para Apollo

Ver: `04_ICP_ESTRATEGIA/industrias_apollo_por_coma.md`
"""


def tpl_macro_cargos(datos: dict) -> str:
    return f"""# Macro Cargos: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}
**Estado:** PENDIENTE — completar con Claude

---

## Cargos Objetivo por Prioridad

| # | Cargo | Prioridad | Área | Nivel |
|---|-------|-----------|------|-------|
| 1 | [cargo] | Alta | [área] | [nivel] |
| 2 | [cargo] | Alta | [área] | [nivel] |
| 3 | [cargo] | Media | [área] | [nivel] |

---

## Cargos a Evitar

- [cargo y razón]

---

## Para Apollo

Ver: `04_ICP_ESTRATEGIA/cargos_apollo_por_coma.md`
"""


def tpl_criterios_prioridad(datos: dict) -> str:
    return f"""# Criterios de Prioridad: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}

---

## Un prospecto es PRIORIDAD 1 si...

- [ ] [criterio]
- [ ] [criterio]
- [ ] [criterio]

## Un prospecto es PRIORIDAD 2 si...

- [ ] [criterio]
- [ ] [criterio]

## Un prospecto es PRIORIDAD 3 si...

- [ ] [criterio]

---

## Señales de Compra a Detectar

- [señal]
- [señal]
"""


def tpl_criterios_descarte(datos: dict) -> str:
    return f"""# Criterios de Descarte: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}

---

## Descartar si...

- [ ] [criterio de descarte]
- [ ] [criterio de descarte]
- [ ] [criterio de descarte]

---

## Industrias a NO prospectar

- [industria — razón]

---

## Cargos que NO sirven

- [cargo — razón]

---

## Señales de No Calificado

- [señal]
"""


def tpl_cargos_apollo(datos: dict) -> str:
    return f"""# Cargos Apollo (separados por coma): {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}
**Usar directamente en Apollo → People Search → Job Title**

---

## Cargos en Español

[cargo 1], [cargo 2], [cargo 3], [cargo 4]

---

## Cargos en Inglés

[cargo 1], [cargo 2], [cargo 3], [cargo 4]

---

## Cargos Combinados (para búsqueda amplia)

[cargo 1], [cargo 2], [cargo 3], [cargo 4], [cargo 5], [cargo 6]
"""


def tpl_industrias_apollo(datos: dict) -> str:
    return f"""# Industrias Apollo (separadas por coma): {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}
**Usar directamente en Apollo → Company → Industry**

---

## Industrias para búsqueda prioritaria

[industria 1], [industria 2], [industria 3]

---

## Industrias para búsqueda amplia

[industria 1], [industria 2], [industria 3], [industria 4]
"""


def tpl_busquedas_apollo(datos: dict) -> str:
    return f"""# Búsquedas Apollo Sugeridas: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}
**Estado:** PENDIENTE — completar con Claude y validar en Apollo

---

## Búsqueda 1 — Prioritaria

**Objetivo:** [descripción]

| Filtro | Valor |
|--------|-------|
| Job Title | [cargos] |
| Industry | [industrias] |
| Country | {_f(datos, 'pais_objetivo')} |
| Company Size | [rango] |
| Keywords | [keywords] |

---

## Búsqueda 2 — Amplia

Ver: `07_APOLLO_Y_BUSQUEDAS/busqueda_2_amplia.md`

---

## Búsqueda 3 — Nicho

Ver: `07_APOLLO_Y_BUSQUEDAS/busqueda_3_nicho.md`
"""


# ─────────────────────────────────────────────
# 05_MENSAJERIA_COMERCIAL
# ─────────────────────────────────────────────

def tpl_pitch_general(datos: dict) -> str:
    return f"""# Pitch General: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}
**Estado:** PENDIENTE — completar con Claude

---

## Pitch de 1 línea

> [COMPLETAR: "{_f(datos, 'nombre_cliente')} ayuda a [QUIÉN] a [QUÉ] sin [DOLOR]"]

---

## Pitch de 3 líneas (para email/LinkedIn)

[COMPLETAR CON CLAUDE]

---

## Pitch completo (para llamadas)

[COMPLETAR CON CLAUDE]

---

## Instrucción para Claude

"Dame un pitch de prospección para {_f(datos, 'nombre_cliente')} que:
- {_f(datos, 'descripcion', '[descripción]')}
- Objetivo: {_f(datos, 'objetivo_comercial', '[objetivo]')}
- País: {_f(datos, 'pais_objetivo')}
- En versión 1 línea, 3 líneas y pitch completo para llamada."
"""


def tpl_pitch_por_segmento(datos: dict) -> str:
    return f"""# Pitch por Segmento: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}
**Estado:** PENDIENTE — completar con Claude tras definir ICP

---

## [Segmento 1: Macro Industria + Cargo]

**Dolor principal:** [dolor]
**Pitch:**
> [pitch específico para este segmento]

---

## [Segmento 2: Macro Industria + Cargo]

**Dolor principal:** [dolor]
**Pitch:**
> [pitch específico]

---

## Referencia

Ver segmentos en: `06_PLAYBOOK_SDR/segmentos_playbook.json`
"""


def tpl_aperturas_sdr(datos: dict) -> str:
    return f"""# Aperturas SDR: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}
**Estado:** PENDIENTE — completar con Claude

---

## Aperturas Email

### Apertura 1 — Directa
Asunto: [asunto]
Cuerpo: [apertura]

### Apertura 2 — Pregunta
Asunto: [asunto]
Cuerpo: [apertura]

### Apertura 3 — Caso de uso
Asunto: [asunto]
Cuerpo: [apertura]

---

## Aperturas LinkedIn

### Apertura 1
[texto]

### Apertura 2
[texto]

---

## Aperturas WhatsApp

### Apertura 1
[texto]
"""


def tpl_preguntas_discovery(datos: dict) -> str:
    return f"""# Preguntas Discovery: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}
**Estado:** PENDIENTE — completar con Claude

---

## Preguntas para calificar al prospecto

1. [pregunta]
2. [pregunta]
3. [pregunta]

---

## Preguntas para entender el dolor

1. [pregunta]
2. [pregunta]

---

## Preguntas para avanzar a reunión

1. [pregunta]
2. [pregunta]

---

## Instrucción para Claude

"Dame 10 preguntas discovery para un SDR que prospecta para {_f(datos, 'nombre_cliente')},
cuyos prospectos son [cargos] en industrias [industrias]."
"""


def tpl_objeciones(datos: dict) -> str:
    return f"""# Objeciones y Respuestas: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}
**Estado:** PENDIENTE — completar con Claude y cliente

---

## Objeciones Comunes

### "No tenemos presupuesto"
**Respuesta:**
[completar]

### "Ya tenemos proveedor"
**Respuesta:**
[completar]

### "No es el momento"
**Respuesta:**
[completar]

### "Mándame información"
**Respuesta:**
[completar]

### "No me interesa"
**Respuesta:**
[completar]

---

## Objeciones Específicas del Rubro

[Completar según industria de {_f(datos, 'nombre_cliente')}]
"""


def tpl_mensajes_whatsapp(datos: dict) -> str:
    return f"""# Mensajes WhatsApp: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}
**Estado:** PENDIENTE — completar con Claude

---

## Mensaje de Apertura 1

Hola [nombre], [apertura corta].

¿Tienes 15 minutos esta semana para conversar?

---

## Mensaje de Apertura 2

[alternativa]

---

## Follow-up 1 (sin respuesta)

[texto]

---

## Follow-up 2

[texto]

---

## Mensaje de Cierre / Descarte

[texto]
"""


def tpl_mensajes_email(datos: dict) -> str:
    return f"""# Mensajes Email: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}
**Estado:** PENDIENTE — completar con Claude

---

## Email 1 — Apertura

**Asunto:** [asunto]

Hola [nombre],

[cuerpo]

¿Tienes 15 minutos para una llamada rápida?

Saludos,
{_f(datos, 'nombre_prospector', '[nombre SDR]')}

---

## Email 2 — Follow-up 1

**Asunto:** Re: [asunto]

[cuerpo]

---

## Email 3 — Follow-up 2

**Asunto:** [asunto]

[cuerpo]

---

## Email 4 — Breakup

**Asunto:** [asunto]

[cuerpo]
"""


def tpl_mensajes_linkedin(datos: dict) -> str:
    return f"""# Mensajes LinkedIn: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}
**Estado:** PENDIENTE — completar con Claude

---

## Nota de conexión (300 chars max)

[texto corto — NO vender, solo conectar]

---

## Mensaje post-conexión 1

[texto]

---

## Mensaje post-conexión 2 (follow-up)

[texto]

---

## InMail (para perfiles cerrados)

**Asunto:** [asunto]
[cuerpo]
"""


# ─────────────────────────────────────────────
# 06_PLAYBOOK_SDR
# ─────────────────────────────────────────────

def tpl_brief_playbook_codex(datos: dict) -> str:
    return f"""# Brief Playbook SDR para Codex: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}
**Estado:** PENDIENTE — completar con Claude antes de enviar a Codex

> Este archivo es la instrucción completa para que Codex construya el archivo
> `playbook_sdr.html`. Claude debe completar todo el contenido antes de usar este brief.

---

## 1. Datos del Cliente

- **Nombre:** {_f(datos, 'nombre_cliente')}
- **Web:** {_f(datos, 'sitio_web')}
- **País objetivo:** {_f(datos, 'pais_objetivo')}

---

## 2. Resumen del Servicio

{_f(datos, 'descripcion', '[Completar con resumen_servicio.md]')}

---

## 3. Propuesta de Valor

[Completar desde 03_ANALISIS_CLIENTE/propuesta_valor.md]

---

## 4. ICP Aprobado

⚠️ Usar solo contenido de `04_ICP_ESTRATEGIA/icp_master.md` (después de aprobación).

[Completar tras aprobación de ICP]

---

## 5. Macro Industrias y Cargos

**Macro industrias:** [desde macro_industrias.md]
**Macro cargos:** [desde macro_cargos.md]

---

## 6. Criterios

**Prioridad:** [desde criterios_prioridad.md]
**Descarte:** [desde criterios_descarte.md]

---

## 7. Pitch

[desde pitch_general.md]

---

## 8. Mensajes por Segmento

Ver: `06_PLAYBOOK_SDR/segmentos_playbook.json`

---

## 9. Objeciones

[desde objeciones_y_respuestas.md]

---

## 10. Preguntas Discovery

[desde preguntas_discovery.md]

---

## 11. Assets de Marca

- **Logo:** [nombre del logo en 02_BRANDING_Y_ACTIVOS/logos_cliente/]
- **Colores:** [desde 02_BRANDING_Y_ACTIVOS/colores_marca.md]

---

## 12. Estructura Esperada del Playbook HTML

El playbook debe tener:
- Barra lateral con filtros por macro industria y macro cargo
- Tarjetas por segmento con pitch, apertura, preguntas, objeciones
- Mensajes de email, WhatsApp y LinkedIn por segmento
- Indicador de prioridad
- Branding del cliente (logo + colores)
- Responsive y fácil de usar en pantalla

---

## 13. Instrucciones para Codex

1. Usar `segmentos_playbook.json` como fuente de datos
2. NO redefinir el ICP — usar solo lo que está en este brief
3. Diseño limpio, moderno, fácil de escanear
4. Incluir buscador por segmento si es posible
5. Exportar como archivo HTML autónomo (sin dependencias externas)

---

## 14. Instrucción CRÍTICA

⛔ Codex NO debe redefinir el ICP, las macro industrias, los macro cargos ni la propuesta
de valor. Solo debe tomar el contenido de este brief y presentarlo visualmente en HTML.
"""


def tpl_segmentos_playbook_json(datos: dict) -> str:
    segmentos = [
        {
            "macro_industria": "[Completar]",
            "micro_industria": "[Completar]",
            "macro_cargo": "[Completar]",
            "prioridad": "Alta",
            "dolor_principal": "[Completar con Claude]",
            "pitch": "[Completar con Claude]",
            "apertura_sdr": "[Completar con Claude]",
            "preguntas": [
                "[pregunta 1]",
                "[pregunta 2]",
                "[pregunta 3]",
            ],
            "objeciones": [
                {"objecion": "[objeción 1]", "respuesta": "[respuesta 1]"},
            ],
            "mensaje_whatsapp": "[Completar con Claude]",
            "mensaje_email": "[Completar con Claude]",
            "mensaje_linkedin": "[Completar con Claude]",
        }
    ]
    return json.dumps(segmentos, ensure_ascii=False, indent=2)


def tpl_reglas_playbook(datos: dict) -> str:
    return f"""# Reglas del Playbook: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}

---

## Reglas Generales del SDR

1. Nunca enviar el mismo mensaje dos veces al mismo contacto.
2. Máximo 4 intentos por contacto antes de marcar como descartado.
3. Siempre personalizar con nombre y cargo del prospecto.
4. No presumir tecnología que usan — preguntar.
5. Nunca enviar precio sin calificar primero.

---

## Reglas de Calificación

- Solo agendar reunión si el cargo es el correcto.
- Solo agendar si la empresa cumple los criterios del ICP.
- Validar tamaño de empresa antes de agendar.

---

## Reglas de Secuencia

- Email 1 → esperar 3 días.
- Email 2 → esperar 4 días.
- LinkedIn → después del Email 2.
- WhatsApp → solo si hay alguna señal de interés.
- Email 4 (breakup) → al día 14 sin respuesta.

---

## Qué NO hacer

- No enviar adjuntos en el primer contacto.
- No mencionar precio en el primer contacto.
- No usar palabras como "solución", "plataforma", "innovador".
- No escribir mensajes de más de 100 palabras en WhatsApp.

---

## ICP Oficial

⚠️ La fuente oficial del ICP es: `04_ICP_ESTRATEGIA/icp_master.md`
Ningún SDR ni herramienta debe redefinir el ICP sin aprobación.
"""


# ─────────────────────────────────────────────
# 07_APOLLO_Y_BUSQUEDAS
# ─────────────────────────────────────────────

def tpl_busqueda_apollo(numero: int, tipo: str, datos: dict) -> str:
    return f"""# Búsqueda Apollo {numero} — {tipo}: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}
**Estado:** PENDIENTE — definir con Claude y validar en Apollo

---

## Objetivo de esta búsqueda

[Describir qué tipo de prospecto busca esta búsqueda y por qué]

---

## Filtros Apollo

| Filtro | Valor |
|--------|-------|
| Job Title (contiene) | [cargos] |
| Job Title (excluye) | [cargos a excluir] |
| Industry | [industrias] |
| Company Size | [rango de empleados] |
| Country | {_f(datos, 'pais_objetivo')} |
| Keywords | [palabras clave] |
| Company Domain | [dominios si aplica] |

---

## Resultado Esperado

- Cantidad estimada: [número]
- Calidad esperada: [descripción]

---

## Notas

[Notas de la búsqueda, observaciones, ajustes]
"""


def tpl_keywords_apollo(datos: dict) -> str:
    return f"""# Keywords Apollo: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}

---

## Keywords para Company Search

[keyword 1], [keyword 2], [keyword 3]

---

## Keywords para People Search

[keyword 1], [keyword 2]

---

## Instrucción para Claude

"Dame keywords de Apollo para buscar prospectos de {_f(datos, 'nombre_cliente')}.
Servicio: {_f(datos, 'descripcion', '[descripción]')}.
País: {_f(datos, 'pais_objetivo')}."
"""


def tpl_exclusiones_apollo(datos: dict) -> str:
    return f"""# Exclusiones Apollo: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}

---

## Industrias a Excluir

[industria 1], [industria 2]

---

## Cargos a Excluir

[cargo 1], [cargo 2]

---

## Dominios a Excluir (competencia, proveedores)

[dominio1.com], [dominio2.com]

---

## Empresas a Excluir (clientes actuales)

[empresa 1], [empresa 2]
"""


# ─────────────────────────────────────────────
# 13_BRIEF_CLIENTE_INTERACTIVO
# ─────────────────────────────────────────────

def tpl_brief_interactivo_html(datos: dict) -> str:
    nombre = _f(datos, 'nombre_cliente')
    descripcion = _f(datos, 'descripcion', '')
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Brief Interactivo — {nombre}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f5f7fa; color: #1a1a2e; }}
  header {{ background: linear-gradient(135deg, #1a56db 0%, #0e3a8a 100%); color: white; padding: 32px 40px; }}
  header h1 {{ font-size: 26px; font-weight: 700; margin-bottom: 6px; }}
  header p {{ font-size: 14px; opacity: 0.85; }}
  .container {{ max-width: 780px; margin: 40px auto; padding: 0 24px 60px; }}
  .intro {{ background: white; border-radius: 12px; padding: 24px; margin-bottom: 28px; border-left: 4px solid #1a56db; }}
  .intro h2 {{ font-size: 16px; font-weight: 600; margin-bottom: 8px; color: #1a56db; }}
  .intro p {{ font-size: 14px; color: #555; line-height: 1.6; }}
  .seccion {{ background: white; border-radius: 12px; padding: 28px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
  .seccion h3 {{ font-size: 16px; font-weight: 700; color: #1a1a2e; margin-bottom: 18px; padding-bottom: 10px; border-bottom: 2px solid #e8ecf0; }}
  .pregunta {{ margin-bottom: 20px; }}
  .pregunta label {{ display: block; font-size: 13px; font-weight: 600; color: #333; margin-bottom: 8px; }}
  .pregunta textarea {{ width: 100%; padding: 12px; border: 1.5px solid #d0d7e2; border-radius: 8px; font-size: 14px; font-family: inherit; resize: vertical; min-height: 80px; transition: border-color 0.2s; }}
  .pregunta textarea:focus {{ outline: none; border-color: #1a56db; }}
  .pregunta .hint {{ font-size: 12px; color: #888; margin-top: 4px; }}
  .btn-group {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 32px; }}
  .btn {{ padding: 12px 24px; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s; }}
  .btn-primary {{ background: #1a56db; color: white; }}
  .btn-primary:hover {{ background: #1345b8; }}
  .btn-secondary {{ background: #e8ecf0; color: #333; }}
  .btn-secondary:hover {{ background: #d0d7e2; }}
  .badge {{ display: inline-block; background: #e8f0fe; color: #1a56db; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 12px; margin-bottom: 6px; }}
  #confirmacion {{ display: none; background: #e8f7ef; border: 1.5px solid #27ae60; border-radius: 8px; padding: 16px; margin-top: 16px; color: #1a6e38; font-size: 14px; }}
</style>
</head>
<body>

<header>
  <h1>📋 Brief de Prospección</h1>
  <p>Conprospección · {nombre} · Generado el {_hoy()}</p>
</header>

<div class="container">

  <div class="intro">
    <h2>¿Para qué es este formulario?</h2>
    <p>Necesitamos tu ayuda para definir exactamente a quién prospectar y cómo hacerlo bien.
    Tus respuestas guiarán toda la estrategia de la campaña. No hay respuestas incorrectas —
    entre más específico, mejor.</p>
  </div>

  <form id="briefForm">

    <div class="seccion">
      <h3>1. Tu Empresa y Servicio</h3>

      <div class="pregunta">
        <label>¿Esta descripción refleja correctamente lo que hace tu empresa?</label>
        <div class="hint">Puedes corregir, agregar o simplificar.</div>
        <textarea name="descripcion_validada" placeholder="{descripcion}">{descripcion}</textarea>
      </div>

      <div class="pregunta">
        <label>¿Cuáles son tus principales diferenciadores vs. la competencia?</label>
        <div class="hint">¿Qué tienen ustedes que los demás no ofrecen?</div>
        <textarea name="diferenciadores" placeholder="Ej: tiempos de respuesta más rápidos, precios transparentes, servicio personalizado..."></textarea>
      </div>

      <div class="pregunta">
        <label>¿Qué clientes actuales podemos mencionar en los mensajes (como referencia de credibilidad)?</label>
        <div class="hint">Solo si tienes permiso para usarlos.</div>
        <textarea name="clientes_referencia" placeholder="Ej: Empresa ABC, Empresa XYZ..."></textarea>
      </div>

      <div class="pregunta">
        <label>¿Tienen casos de éxito o métricas que podamos usar en la prospección?</label>
        <div class="hint">Ej: "reducimos costos un 20%", "gestionamos 500 embarques al mes"</div>
        <textarea name="casos_exito" placeholder="Describe resultados concretos si los tienes..."></textarea>
      </div>
    </div>

    <div class="seccion">
      <h3>2. A Quién Prospectar</h3>

      <div class="pregunta">
        <label>¿Qué industrias quieren priorizar?</label>
        <div class="hint">Lista las más importantes primero.</div>
        <textarea name="industrias_prioritarias" placeholder="Ej: manufactura, retail, agricultura, tecnología..."></textarea>
      </div>

      <div class="pregunta">
        <label>¿Qué industrias NO quieren prospectar?</label>
        <div class="hint">Sectores que no son su mercado o que prefieren evitar.</div>
        <textarea name="industrias_excluir" placeholder="Ej: gobierno, organizaciones sin fines de lucro..."></textarea>
      </div>

      <div class="pregunta">
        <label>¿Qué tipo de empresa es su mejor cliente actual?</label>
        <div class="hint">Tamaño, industria, país, facturación, características.</div>
        <textarea name="mejor_cliente" placeholder="Ej: empresa mediana del sector manufactura, con equipo de logística interno, que importa desde Asia..."></textarea>
      </div>

      <div class="pregunta">
        <label>¿Qué cargos toman la decisión de contratarlos?</label>
        <div class="hint">¿Quién firma? ¿Quién influye? ¿Quién necesitan que asista a la reunión?</div>
        <textarea name="cargos_decision" placeholder="Ej: Gerente de Logística, Director de Operaciones, Gerente General..."></textarea>
      </div>

      <div class="pregunta">
        <label>¿Hay cargos que NO sirven para prospectar?</label>
        <div class="hint">Cargos que no tienen poder de decisión o que no son relevantes.</div>
        <textarea name="cargos_excluir" placeholder="Ej: asistentes, analistas júnior, pasantes..."></textarea>
      </div>
    </div>

    <div class="seccion">
      <h3>3. Reuniones y Calificación</h3>

      <div class="pregunta">
        <label>¿Qué consideran una reunión válida?</label>
        <div class="hint">¿Qué condiciones debe cumplir un prospecto para que la reunión cuente?</div>
        <textarea name="reunion_valida" placeholder="Ej: debe ser el Gerente de Logística o quien tome la decisión, la empresa debe importar o exportar, debe tener al menos 50 empleados..."></textarea>
      </div>

      <div class="pregunta">
        <label>¿Qué prospectos definitivamente NO deberían agendarse?</label>
        <div class="hint">Tipos de empresas o personas que no califican aunque respondan.</div>
        <textarea name="no_agendar" placeholder="Ej: empresas que solo operan localmente, personas sin poder de decisión..."></textarea>
      </div>
    </div>

    <div class="seccion">
      <h3>4. Mensajería y Comunicación</h3>

      <div class="pregunta">
        <label>¿Qué objeciones reciben normalmente cuando prospectan?</label>
        <div class="hint">¿Qué dice la gente cuando no quiere reunirse?</div>
        <textarea name="objeciones" placeholder="Ej: ya tenemos proveedor, no es el momento, mándame información..."></textarea>
      </div>

      <div class="pregunta">
        <label>¿Qué diferenciales deberíamos destacar en los mensajes?</label>
        <div class="hint">¿Qué hace que los clientes los elijan sobre la competencia?</div>
        <textarea name="diferenciales_mensajes" placeholder="Ej: respuesta en 24 horas, precio fijo sin sorpresas, equipo dedicado..."></textarea>
      </div>

      <div class="pregunta">
        <label>¿Hay algún mensaje, tono o estilo que NO quieran usar?</label>
        <div class="hint">Palabras, frases o estilos que prefieren evitar.</div>
        <textarea name="no_usar" placeholder="Ej: no queremos sonar muy agresivos, no queremos mencionar precios, no queremos compararnos con X competidor..."></textarea>
      </div>
    </div>

    <div class="seccion">
      <h3>5. Información Adicional</h3>
      <div class="pregunta">
        <label>¿Hay algo más que deberíamos saber para hacer bien la prospección?</label>
        <textarea name="adicional" placeholder="Cualquier cosa importante que no hayamos preguntado..."></textarea>
      </div>
    </div>

    <div class="btn-group">
      <button type="button" class="btn btn-primary" onclick="descargarJSON()">⬇️ Descargar respuestas (JSON)</button>
      <button type="button" class="btn btn-secondary" onclick="descargarMD()">📄 Descargar respuestas (Markdown)</button>
    </div>

    <div id="confirmacion">✅ Respuestas descargadas correctamente. Enviar el archivo a tu equipo de Conprospección.</div>

  </form>
</div>

<script>
function obtenerRespuestas() {{
  const form = document.getElementById('briefForm');
  const data = {{}};
  const inputs = form.querySelectorAll('textarea, input');
  inputs.forEach(el => {{
    data[el.name] = el.value.trim();
  }});
  return data;
}}

function descargarJSON() {{
  const data = obtenerRespuestas();
  const obj = {{
    cliente: "{nombre}",
    fecha: "{_hoy()}",
    respuestas: data
  }};
  const blob = new Blob([JSON.stringify(obj, null, 2)], {{type: 'application/json'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'brief_{nombre.lower().replace(" ", "_")}_{_hoy()}.json';
  a.click();
  document.getElementById('confirmacion').style.display = 'block';
}}

function descargarMD() {{
  const data = obtenerRespuestas();
  let md = `# Brief Completado por Cliente: {nombre}\\n\\nFecha: {_hoy()}\\n\\n---\\n\\n`;
  for (const [key, val] of Object.entries(data)) {{
    md += `## ${{key.replace(/_/g, ' ')}}\\n\\n${{val || '(sin respuesta)'}}\\n\\n---\\n\\n`;
  }}
  const blob = new Blob([md], {{type: 'text/markdown'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'brief_{nombre.lower().replace(" ", "_")}_{_hoy()}.md';
  a.click();
  document.getElementById('confirmacion').style.display = 'block';
}}
</script>

</body>
</html>"""


def tpl_preguntas_pendientes_cliente(datos: dict) -> str:
    return f"""# Preguntas Pendientes para el Cliente: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}

---

## Preguntas Críticas (sin responder)

- [ ] ¿Esta descripción refleja correctamente lo que hace la empresa?
- [ ] ¿Qué industrias quieren priorizar?
- [ ] ¿Qué industrias NO quieren prospectar?
- [ ] ¿Qué tipo de empresa es su mejor cliente actual?
- [ ] ¿Qué cargos toman la decisión?
- [ ] ¿Qué consideran una reunión válida?

---

## Preguntas Complementarias

- [ ] ¿Qué clientes podemos mencionar como referencia?
- [ ] ¿Tienen casos de éxito con métricas?
- [ ] ¿Qué objeciones reciben normalmente?
- [ ] ¿Qué diferenciales destacar?
- [ ] ¿Hay mensajes o tonos que NO quieren usar?

---

## Cómo enviar al cliente

Usar: `13_BRIEF_CLIENTE_INTERACTIVO/brief_cliente_interactivo.html`
Abrir en navegador → completar → descargar JSON o MD → enviar de vuelta.

---

## Respuestas recibidas

_Guardar archivos del cliente en: `13_BRIEF_CLIENTE_INTERACTIVO/respuestas_cliente/`_
"""


# ─────────────────────────────────────────────
# 14_SUPABASE_METABASE
# ─────────────────────────────────────────────

def tpl_datos_supabase_json(datos: dict) -> dict:
    return {
        "meta": {
            "version": "1.0",
            "generado": _hoy(),
            "app": "ConprospeccionOS",
        },
        "cliente": {
            "nombre": _f(datos, "nombre_cliente", ""),
            "sitio_web": _f(datos, "sitio_web", ""),
            "pais_objetivo": _f(datos, "pais_objetivo", ""),
            "descripcion": _f(datos, "descripcion", ""),
            "objetivo_comercial": _f(datos, "objetivo_comercial", ""),
            "nombre_prospector": _f(datos, "nombre_prospector", ""),
            "cargo_prospector": _f(datos, "cargo_prospector", ""),
            "correo": _f(datos, "correo", ""),
            "telefono": _f(datos, "telefono", ""),
            "linkedin": _f(datos, "linkedin", ""),
            "notas_internas": _f(datos, "notas_internas", ""),
            "fecha_creacion": _hoy(),
        },
        "campana": {
            "fecha_inicio_setup": datos.get("fecha_inicio_setup", None),
            "fecha_fin_setup": datos.get("fecha_fin_setup", None),
            "fecha_inicio_prospeccion": datos.get("fecha_inicio_prospeccion", None),
            "fecha_fin_prospeccion": datos.get("fecha_fin_prospeccion", None),
            "monto_setup": datos.get("monto_setup", None),
            "monto_mensual": datos.get("monto_mensual", None),
            "monto_variable": datos.get("monto_variable", None),
            "moneda": datos.get("moneda", None),
            "meta_total_reuniones": datos.get("meta_total_reuniones", None),
            "meta_mensual_reuniones": datos.get("meta_mensual_reuniones", None),
            "tipo_meta": datos.get("tipo_meta", None),
            "garantia_total": datos.get("garantia_total", None),
            "sdr_asignados": datos.get("sdr_asignados", None),
            "canales_activos": datos.get("canales_activos", None),
        },
        "icp": {
            "estado": "pendiente",
            "macro_industrias": [],
            "micro_industrias": [],
            "macro_cargos": [],
            "criterios_prioridad": [],
            "criterios_descarte": [],
            "paises": [_f(datos, "pais_objetivo", "")],
        },
        "apollo": {
            "busquedas": [],
            "cargos_por_coma": "",
            "industrias_por_coma": "",
            "keywords": [],
            "exclusiones": [],
        },
        "playbook": {
            "estado": "pendiente",
            "segmentos": [],
            "version": "v1",
        },
        "reporteria": {
            "reuniones_agendadas": 0,
            "reuniones_validas": 0,
            "contactos_enviados": 0,
            "tasa_respuesta": 0,
            "tasa_conversion": 0,
        },
    }


def tpl_supabase_sync_plan(datos: dict) -> str:
    return f"""# Plan de Sincronización Supabase: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}
**Estado:** PLACEHOLDER — integración futura

---

## Objetivo

Sincronizar datos de {_f(datos, 'nombre_cliente')} desde ConprospeccionOS hacia Supabase
para alimentar dashboards en Metabase.

---

## Tablas a Crear (ver supabase_schema_sugerido.sql)

1. `clientes` — datos del cliente
2. `campanas` — datos de campaña y metas
3. `icps` — perfil de cliente ideal
4. `segmentos` — segmentos del playbook
5. `contactos` — base de prospectos
6. `reuniones` — reuniones agendadas y válidas
7. `secuencias` — secuencias de email/WA/LinkedIn

---

## Frecuencia de Sync

- `estado_cliente.json` → sync diario
- `datos_para_supabase.json` → sync al actualizar
- Reuniones → sync en tiempo real (futuro)

---

## Pasos para Integrar

1. [ ] Crear proyecto en Supabase
2. [ ] Ejecutar supabase_schema_sugerido.sql
3. [ ] Obtener API Key de Supabase
4. [ ] Agregar `SUPABASE_URL` y `SUPABASE_KEY` a .env de ConprospeccionOS
5. [ ] Activar módulo de sync en la app
6. [ ] Verificar datos en Metabase
"""


def tpl_supabase_schema(datos: dict) -> str:
    return f"""-- Schema Supabase: Conprospección OS
-- Cliente: {_f(datos, 'nombre_cliente')}
-- Generado: {_hoy()}

-- ─────────────────────────────────────────
-- CLIENTES
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS clientes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nombre TEXT NOT NULL,
  sitio_web TEXT,
  pais_objetivo TEXT,
  descripcion TEXT,
  objetivo_comercial TEXT,
  nombre_prospector TEXT,
  cargo_prospector TEXT,
  correo TEXT,
  telefono TEXT,
  linkedin TEXT,
  notas_internas TEXT,
  estado_general TEXT DEFAULT 'creado',
  fecha_creacion DATE DEFAULT CURRENT_DATE,
  fecha_actualizacion DATE DEFAULT CURRENT_DATE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- CAMPAÑAS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS campanas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cliente_id UUID REFERENCES clientes(id),
  monto_setup NUMERIC,
  monto_mensual NUMERIC,
  monto_variable NUMERIC,
  moneda TEXT DEFAULT 'USD',
  meta_total_reuniones INTEGER,
  meta_mensual_reuniones INTEGER,
  tipo_meta TEXT,
  garantia_total TEXT,
  sdr_asignados TEXT,
  canales_activos TEXT,
  fecha_inicio_setup DATE,
  fecha_fin_setup DATE,
  fecha_inicio_prospeccion DATE,
  fecha_fin_prospeccion DATE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- ICP
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS icps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cliente_id UUID REFERENCES clientes(id),
  estado TEXT DEFAULT 'pendiente',
  macro_industrias JSONB DEFAULT '[]',
  micro_industrias JSONB DEFAULT '[]',
  macro_cargos JSONB DEFAULT '[]',
  criterios_prioridad JSONB DEFAULT '[]',
  criterios_descarte JSONB DEFAULT '[]',
  paises JSONB DEFAULT '[]',
  version INTEGER DEFAULT 1,
  aprobado_por TEXT,
  fecha_aprobacion DATE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- SEGMENTOS PLAYBOOK
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS segmentos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cliente_id UUID REFERENCES clientes(id),
  macro_industria TEXT,
  micro_industria TEXT,
  macro_cargo TEXT,
  prioridad TEXT,
  dolor_principal TEXT,
  pitch TEXT,
  apertura_sdr TEXT,
  preguntas JSONB DEFAULT '[]',
  objeciones JSONB DEFAULT '[]',
  mensaje_whatsapp TEXT,
  mensaje_email TEXT,
  mensaje_linkedin TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- REUNIONES
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reuniones (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cliente_id UUID REFERENCES clientes(id),
  prospecto_nombre TEXT,
  prospecto_cargo TEXT,
  prospecto_empresa TEXT,
  prospecto_industria TEXT,
  fecha_agendada DATE,
  fecha_reunion DATE,
  estado TEXT DEFAULT 'agendada',
  es_valida BOOLEAN,
  razon_invalida TEXT,
  sdr TEXT,
  canal TEXT,
  notas TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
"""


def tpl_metabase_plan(datos: dict) -> str:
    return f"""# Plan Dashboard Metabase: {_f(datos, 'nombre_cliente')}

**Fecha:** {_hoy()}
**Estado:** PLACEHOLDER — integración futura

---

## Dashboards Planificados

### 1. Dashboard Cliente
- Reuniones agendadas vs. meta
- Reuniones válidas vs. agendadas
- Progreso de campaña
- Tasa de respuesta por canal
- Funnel prospección

### 2. Dashboard SDR
- Reuniones por SDR
- Contactos enviados por SDR
- Tasa de conversión por SDR
- Actividad diaria/semanal

### 3. Dashboard Operativo
- Estado por etapa
- Pendientes por cliente
- Clientes activos vs. en setup

---

## Preguntas de Alicia (queries naturales)

- ¿Cuántas reuniones tiene {_f(datos, 'nombre_cliente')} este mes?
- ¿Cuántos contactos faltan para llegar a la meta?
- ¿Cuál es la tasa de respuesta por canal?
- ¿Qué segmento está funcionando mejor?
- ¿Cuántas reuniones van en total?
"""


# ─────────────────────────────────────────────
# ESTADO CLIENTE
# ─────────────────────────────────────────────

def tpl_estado_cliente(datos: dict) -> dict:
    tiene_analisis = any(datos.get(k, "").strip() for k in [
        "resumen_servicio", "propuesta_valor", "problema_que_resuelve",
        "icp_tipo_cliente", "diferenciacion"
    ])
    return {
        # Datos básicos
        "nombre_cliente": _f(datos, "nombre_cliente", ""),
        "nombre_normalizado": datos.get("nombre_normalizado", ""),
        "sitio_web": _f(datos, "sitio_web", ""),
        "pais_objetivo": _f(datos, "pais_objetivo", ""),
        "objetivo_comercial": _f(datos, "objetivo_comercial", ""),
        # Análisis del cliente (5 cards)
        "resumen_servicio": datos.get("resumen_servicio", ""),
        "propuesta_valor": datos.get("propuesta_valor", ""),
        "problema_que_resuelve": datos.get("problema_que_resuelve", ""),
        "icp_tipo_cliente": datos.get("icp_tipo_cliente", ""),
        "diferenciacion": datos.get("diferenciacion", ""),
        # Info importante
        "industrias_no_prospectar": datos.get("industrias_no_prospectar", ""),
        "clientes_actuales": datos.get("clientes_actuales", ""),
        "competidores": datos.get("competidores", ""),
        "ticket_promedio": datos.get("ticket_promedio", ""),
        "canales_actuales": datos.get("canales_actuales", ""),
        # Fechas y estado
        "fecha_creacion": _hoy(),
        "fecha_actualizacion": _hoy(),
        "estado_general": "creado",
        "estado_estructura": "lista",
        "estado_archivos": "pendiente",
        "estado_branding": "pendiente",
        "estado_firma": "pendiente",
        "estado_analisis": "analisis_listo" if tiene_analisis else "pendiente",
        "estado_icp": "icp_pendiente_revision" if datos.get("icp_tipo_cliente", "").strip() else "pendiente",
        "estado_playbook": "pendiente",
        "estado_apollo": "pendiente",
        "estado_mensajeria": "pendiente",
        "estado_supabase_metabase": "pendiente",
        "etapa_actual": 2,
        "etapa_nombre": "Archivos e Input",
        "pendientes": [
            "Subir archivos y logos del cliente",
            "Completar brief interactivo con cliente",
            "Definir ICP con Claude",
            "Generar o subir logo para firma",
        ],
        "proximos_pasos": [
            "Subir archivos disponibles del cliente",
            "Enviar brief_cliente_interactivo.html al cliente",
            "Pedir a Claude que analice la web",
        ],
    }


# ─────────────────────────────────────────────
# GENERADOR PRINCIPAL
# ─────────────────────────────────────────────

def generar_todos_los_archivos(cliente_dir: Path, datos: dict) -> list:
    """Crea todos los archivos base. Retorna lista de archivos creados."""
    creados = []

    archivos_md = {
        "01_ADMIN_CLIENTE/datos_cliente.md": tpl_datos_cliente(datos),
        "01_ADMIN_CLIENTE/informacion_original_cliente.md": tpl_informacion_original_cliente(datos),
        "01_ADMIN_CLIENTE/informacion_pendiente.md": tpl_informacion_pendiente(datos),
        "01_ADMIN_CLIENTE/condiciones_comerciales.md": tpl_condiciones_comerciales(datos),
        "01_ADMIN_CLIENTE/metas_campaña.md": tpl_metas_campana(datos),
        "01_ADMIN_CLIENTE/firma_comercial.md": tpl_firma_comercial(datos),
        "03_ANALISIS_CLIENTE/analisis_web.md": tpl_analisis_web(datos),
        "03_ANALISIS_CLIENTE/resumen_servicio.md": tpl_resumen_servicio(datos),
        "03_ANALISIS_CLIENTE/propuesta_valor.md": tpl_propuesta_valor(datos),
        "03_ANALISIS_CLIENTE/problemas_que_resuelve.md": tpl_problemas_que_resuelve(datos),
        "03_ANALISIS_CLIENTE/diferenciadores.md": tpl_diferenciadores(datos),
        "03_ANALISIS_CLIENTE/informacion_no_confirmada.md": tpl_informacion_no_confirmada(datos),
        "04_ICP_ESTRATEGIA/icp_borrador.md": tpl_icp_borrador(datos),
        "04_ICP_ESTRATEGIA/icp_master.md": tpl_icp_master(datos),
        "04_ICP_ESTRATEGIA/macro_industrias.md": tpl_macro_industrias(datos),
        "04_ICP_ESTRATEGIA/micro_industrias.md": tpl_micro_industrias(datos),
        "04_ICP_ESTRATEGIA/macro_cargos.md": tpl_macro_cargos(datos),
        "04_ICP_ESTRATEGIA/criterios_prioridad.md": tpl_criterios_prioridad(datos),
        "04_ICP_ESTRATEGIA/criterios_descarte.md": tpl_criterios_descarte(datos),
        "04_ICP_ESTRATEGIA/cargos_apollo_por_coma.md": tpl_cargos_apollo(datos),
        "04_ICP_ESTRATEGIA/industrias_apollo_por_coma.md": tpl_industrias_apollo(datos),
        "04_ICP_ESTRATEGIA/busquedas_apollo_sugeridas.md": tpl_busquedas_apollo(datos),
        "05_MENSAJERIA_COMERCIAL/pitch_general.md": tpl_pitch_general(datos),
        "05_MENSAJERIA_COMERCIAL/pitch_por_segmento.md": tpl_pitch_por_segmento(datos),
        "05_MENSAJERIA_COMERCIAL/aperturas_sdr.md": tpl_aperturas_sdr(datos),
        "05_MENSAJERIA_COMERCIAL/preguntas_discovery.md": tpl_preguntas_discovery(datos),
        "05_MENSAJERIA_COMERCIAL/objeciones_y_respuestas.md": tpl_objeciones(datos),
        "05_MENSAJERIA_COMERCIAL/mensajes_whatsapp.md": tpl_mensajes_whatsapp(datos),
        "05_MENSAJERIA_COMERCIAL/mensajes_email.md": tpl_mensajes_email(datos),
        "05_MENSAJERIA_COMERCIAL/mensajes_linkedin.md": tpl_mensajes_linkedin(datos),
        "06_PLAYBOOK_SDR/brief_playbook_para_codex.md": tpl_brief_playbook_codex(datos),
        "06_PLAYBOOK_SDR/reglas_playbook.md": tpl_reglas_playbook(datos),
        "07_APOLLO_Y_BUSQUEDAS/busqueda_1_prioritaria.md": tpl_busqueda_apollo(1, "Prioritaria", datos),
        "07_APOLLO_Y_BUSQUEDAS/busqueda_2_amplia.md": tpl_busqueda_apollo(2, "Amplia", datos),
        "07_APOLLO_Y_BUSQUEDAS/busqueda_3_nicho.md": tpl_busqueda_apollo(3, "Nicho", datos),
        "07_APOLLO_Y_BUSQUEDAS/cargos_por_coma.md": tpl_cargos_apollo(datos),
        "07_APOLLO_Y_BUSQUEDAS/industrias_por_coma.md": tpl_industrias_apollo(datos),
        "07_APOLLO_Y_BUSQUEDAS/keywords_apollo.md": tpl_keywords_apollo(datos),
        "07_APOLLO_Y_BUSQUEDAS/exclusiones_apollo.md": tpl_exclusiones_apollo(datos),
        "13_BRIEF_CLIENTE_INTERACTIVO/preguntas_pendientes_cliente.md": tpl_preguntas_pendientes_cliente(datos),
        "14_SUPABASE_METABASE/supabase_sync_plan.md": tpl_supabase_sync_plan(datos),
        "14_SUPABASE_METABASE/supabase_schema_sugerido.sql": tpl_supabase_schema(datos),
        "14_SUPABASE_METABASE/metabase_dashboard_plan.md": tpl_metabase_plan(datos),
    }

    for ruta_rel, contenido in archivos_md.items():
        ruta = cliente_dir / ruta_rel
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(contenido, encoding="utf-8")
        creados.append(ruta_rel)

    # Archivos HTML
    html_brief = tpl_brief_interactivo_html(datos)
    ruta_html = cliente_dir / "13_BRIEF_CLIENTE_INTERACTIVO/brief_cliente_interactivo.html"
    ruta_html.parent.mkdir(parents=True, exist_ok=True)
    ruta_html.write_text(html_brief, encoding="utf-8")
    creados.append("13_BRIEF_CLIENTE_INTERACTIVO/brief_cliente_interactivo.html")

    # JSON segmentos playbook
    segmentos = tpl_segmentos_playbook_json(datos)
    ruta_seg = cliente_dir / "06_PLAYBOOK_SDR/segmentos_playbook.json"
    ruta_seg.write_text(segmentos, encoding="utf-8")
    creados.append("06_PLAYBOOK_SDR/segmentos_playbook.json")

    # datos_para_supabase.json
    supabase_data = tpl_datos_supabase_json(datos)
    ruta_supa = cliente_dir / "14_SUPABASE_METABASE/datos_para_supabase.json"
    ruta_supa.write_text(json.dumps(supabase_data, ensure_ascii=False, indent=2), encoding="utf-8")
    creados.append("14_SUPABASE_METABASE/datos_para_supabase.json")

    # estado_cliente.json
    estado = tpl_estado_cliente(datos)
    ruta_estado = cliente_dir / "estado_cliente.json"
    ruta_estado.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    creados.append("estado_cliente.json")

    return creados
