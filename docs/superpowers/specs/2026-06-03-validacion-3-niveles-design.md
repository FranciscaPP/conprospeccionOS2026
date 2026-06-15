# Validación de reuniones en 3 niveles + sincronización de dashboards

**Fecha:** 2026-06-03
**Autor:** Francisca Polanco · Conprospección
**Estado:** Diseño aprobado — pendiente de plan de implementación

## 1. Problema

Hoy los tres dashboards que tocan reuniones no comparten datos:

- **Seguimiento Reuniones** (interno, equipo CP): lee `vw_reuniones_semana` de todos los
  clientes; cada reunión tiene un único `estado_validacion` en la tabla `reuniones`. No
  deduplica, no ordena por última fecha, y el "% de avance" de cada tarjeta es
  `reuniones_cliente ÷ total_global` (sin sentido de negocio).
- **Validación de Reuniones** (cliente, p. ej. `12_GBS`): escribe en tablas separadas por
  cliente (`gbs_seguimiento`, `clickie_seguimiento`) con BANT, etapa, status, interés, motivo.
  No comparte fuente con el dashboard interno → no hay sincronización.
- **Indicadores**: usa datos demo sintéticos; no lee la validación real.

Se necesita que **CP, cliente y "validación final" usen los mismos campos**, que los dashboards
se **sincronicen de forma bidireccional**, y que **Indicadores se alimente semanalmente solo de
la validación final**.

## 2. Decisiones tomadas

1. **La "validación final" la define Conprospección (CP)** tras ver lo que cargó el cliente.
2. **Fuente unificada**: una sola fila por reunión con columnas por nivel. Sin copias entre tablas.
3. **Indicadores**: se deja la cañería (estructura + cálculo) lista, pero **se mantiene el demo**
   hasta que haya reuniones reales validadas (GBS no tiene reuniones reales todavía).
4. **Por fases**: Fase 1 entregable inmediato; Fase 2 el modelo 3-niveles completo.
5. **Dedup** en Seguimiento por `opportunity_id` → si falta `email` → si falta `contacto+empresa`,
   dentro de cada cliente; se conserva la reunión de **fecha más reciente**.
6. **Metas por cliente** viven como **constante en `shared/`** (dict versionado en git).
7. **El % de avance se calcula SIEMPRE con la validación final** (`val_estado_final`), en todos
   los dashboards (Seguimiento e Indicadores). Por eso el campo `val_estado_final` se crea como
   fundación desde la Fase 1, aunque permanezca en 0 hasta que CP empiece a validar.

## 3. Modelo de datos unificado (fundación de Fase 2)

Nueva tabla **`seguimiento_reuniones`** (key = `reunion_id`; válida para todos los clientes; la
sync de `reuniones` nunca la pisa). Cada reunión guarda el mismo set de campos en 3 niveles
(`_cp` = Conprospección, `_cli` = cliente, `_final` = validación final que define CP):

| Campo base | Tipo | Niveles |
|---|---|---|
| `val_estado` (valida / no_valida / reagendar / pendiente) | text | `_cp`, `_cli`, `_final` |
| `etapa` (propuesta_enviada / seguimiento_propuesta / sin_respuesta_post / cliente_ganado / cliente_perdido) | text | `_cp`, `_cli`, `_final` |
| `bant` (subset de B,A,N,T como "B,A,N") | text | `_cp`, `_cli`, `_final` |
| `tipo_respuesta` (ver taxonomía única abajo) | text | `_cp`, `_cli`, `_final` |
| `status` (texto libre del estado del lead) | text | `_cp`, `_cli`, `_final` |

Más metadatos: `reunion_id` (PK), `cliente_slug`, `updated_at`, `updated_by_cp`, `updated_by_cli`.

### Taxonomía única: `tipo_respuesta` (reemplaza Interés del lead + Motivo de rechazo)

Un **único campo uniforme** en todos los dashboards (Indicadores, Validación, Seguimiento) y como
guía en el Playbook. Mantiene siempre el mismo formato (positivas con verbo «Solicita…»):

- **Positivas:** `Solicita reunión` · `Solicita cotización` · `Solicita reunión + cotización` ·
  `Solicita más información`
- **Negativas (identifican el porqué):** `No interesado` · `Ya tiene proveedor` ·
  `No es la persona` · `Sin respuesta`

Migración: los actuales `interes_lead` (Reunión/Cotización/Reunión + Cotización) y `motivo_rechazo`
(Ya tienen proveedor/Sin respuesta/No interesado) se consolidan en `tipo_respuesta` con el mapeo
correspondiente; el Playbook ya expone esta taxonomía como guía por tipo (sección «Manejo de
respuestas»).

- **Sync bidireccional automática**: es una sola fila. El cliente escribe `*_cli`, CP escribe
  `*_cp` y `*_final`. Ambos dashboards leen la misma fila → siempre la misma información.
- **SDR**: queda solo en el dashboard interno (campo + filtro); el cliente nunca lo ve.
- La columna `reuniones.estado_validacion` se mantiene por retrocompatibilidad y se espeja desde
  `val_estado_final` (o `val_estado_cp` mientras no haya final).

## 4. Fase 1 — entregable inmediato

Incluye una fundación mínima del modelo: la tabla `seguimiento_reuniones` con (al menos) la
columna `val_estado_final`, para que el % de avance lea SIEMPRE la validación final.

### 4.1 Seguimiento Reuniones (interno)
- **Dedup**: agrupar por `cliente_slug` + clave (opp → email → contacto+empresa); conservar la
  fila con `fecha` máxima.
- **Orden**: por `fecha` descendente (última agendada primero) en todas las secciones.
- **Tarjetas con meta real por cliente** (reemplaza el % actual sin sentido):
  - Metas por contrato: Just4U **40**, Ecosmart **30**, GBS **45**, BambuTech **100** válidas.
  - Clickie: **6 válidas/mes** (avance mensual; se calcula sobre el mes en curso).
  - **Avance = válidas_final ÷ meta** (con barra y `n/meta`), donde válidas_final cuenta
    `val_estado_final == "valida"`. Hasta que CP empiece a validar finalmente, el avance es 0/meta
    en todos lados — es el comportamiento pedido ("siempre con la validación final").
- Orden de reuniones de cliente (12_GBS y pares) también estable: fecha descendente.

### 4.2 Playbook GBS (`13_GBS_Playbook_SDR.py`)
- Recolorear del azul viejo (`#1a56db`, `#eff6ff`, `#bfdbfe`, `#1e3a5f`, `#1e40af`) al morado de
  marca importando `shared/gbs_brand`.
- Mejorar la legibilidad de la letra de los correos sugeridos (tamaño/contraste/fuente del cuerpo).

### 4.3 Link canónico del portal
Las URLs de cada página las deriva Streamlit del nombre del archivo (`11_GBS.py` → `/GBS`,
`13_GBS_Playbook_SDR.py` → `/GBS_Playbook_SDR`). El link de acceso a repartir es siempre
`https://conprospeccion-os.streamlit.app/GBS` (Indicadores con login). No requiere cambio de
código; opcionalmente, agregar en `/GBS` un aviso "compartí este link" para evitar copiar URLs
de subpáginas.

### 4.4 Constante de metas
`shared/metas.py` (o dentro de `shared/gbs_brand.py` no — es cross-cliente, va aparte):
```python
METAS = {
    "just4u":    {"validas": 40,  "tipo": "contrato"},
    "ecosmart":  {"validas": 30,  "tipo": "contrato"},
    "gbs":       {"validas": 45,  "tipo": "contrato"},
    "bambutech": {"validas": 100, "tipo": "contrato"},
    "clickie":   {"validas": 6,   "tipo": "mensual"},
}
```

## 5. Fase 2 — modelo 3-niveles + sync + Indicadores semanal

1. **Migración**: crear `seguimiento_reuniones`; migrar datos de `gbs_seguimiento` /
   `clickie_seguimiento` a las columnas `*_cli` correspondientes.
2. **Validación de Reuniones (cliente)**: carga sus campos `*_cli` (BANT cliente con 1+
   variables, estado, etapa, status). Reuniones siempre ordenadas (fecha desc).
3. **Seguimiento (interno)**: agrega los campos `*_cp` y la **validación final `*_final`**
   (CP decide), más el SDR. Muestra los tres niveles lado a lado para comparar.
4. **Indicadores**: KPIs alimentados **solo por `*_final`**, vía snapshot semanal
   (`indicadores_semanal`, sello "actualizado: lunes dd/mm"). Para GBS: cañería lista, datos
   en demo hasta tener reuniones reales validadas.
5. Roll-out: pilotar en GBS + Seguimiento interno, luego extender a Clickie/Tiresias.

## 6. Componentes y límites

- `shared/metas.py` — metas por cliente (una responsabilidad: configuración de metas).
- `shared/seguimiento.py` (Fase 2) — helpers de lectura/escritura de `seguimiento_reuniones`
  (CRUD + normalización BANT) reutilizados por los 3 dashboards.
- `shared/gbs_brand.py` — ya existe; Playbook lo adopta.
- Dashboards consumen los helpers; no duplican lógica de acceso a datos.

## 7. Riesgos

- La sync de GHL podría sobrescribir `reuniones`; por eso la validación vive en
  `seguimiento_reuniones` aparte.
- Dedup por clave débil (sin opp/email) puede unir/keepar mal; se mitiga con el orden opp→email→nombre.
- "Snapshot semanal" requiere un job programado; en Fase 2 se define (cron o función edge).

## 8. Fuera de alcance (YAGNI)

- No se reescriben los dashboards de otros clientes en Fase 1.
- No se conecta Indicadores GBS a datos reales (se mantiene demo).
- No se construye el job semanal real hasta que haya datos reales que justifiquen el snapshot.

## 9. Insights de Indicadores — cliente vs. interno

Tras el repaso "nivel CEO", los insights se reparten así:

**Ya en el dashboard del CLIENTE (`11_GBS`):**
- Resumen ejecutivo (embudo, dónde traccciona, qué priorizar, estado de meta, aviso de confianza). ✅
- ICP real vs. teórico (qué cargo/industria del ICP convierte de verdad). ✅
- **#2** Efectividad por segmento (tasa de positivas por cargo/industria/país/canal + semáforo Priorizar/Observar/Cortar). ✅
- **#3** Motivos de rechazo agregados + acción sugerida por motivo. ✅

**Panel INTERNO de Conprospección (a construir; NO visible al cliente):**
- **#1** Ritmo vs. garantía: válidas/semana necesarias vs. ritmo actual, por cliente, con alerta temprana.
- **#4** Calidad BANT de las positivas: qué tan calificadas/listas para cerrar (promedio de variables BANT).
- **#5** Valor potencial del pipeline ($): estimación en plata jalando el ticket promedio del Onboarding.

Ubicación sugerida del panel interno: dentro de **Seguimiento Reuniones** (master auth) o una página de
analítica interna nueva. Usa `METAS` (shared/metas.py) y, para #5, el ticket de `gbs_onboarding`.

### Backlog — features del portal cliente (idea de Francisca, 2026-06-03)

- **Evaluación de mercado al final del ICP:** tras armar el ICP, un bloque breve que justifique
  **por qué avanzar con los segmentos elegidos** (ej: si el cliente elige 10 industrias, explicar
  por qué se prioriza un subconjunto). Candidato a generarse con IA (Claude / `ANTHROPIC_API_KEY`).
- **Botón "Generar PDF" en Indicadores:** reporte mensual descargable con los **5 KPIs principales**
  del dashboard, **respetando los filtros** que aplique el cliente. Estrategia comercial: data de
  alto valor, entrega mensual (no semanal) → producto vendible. Requiere lib de PDF (p. ej. fpdf2).

## 10. Recordatorio — qué es la Fase 2 (en una frase)

**Unificar la validación de reuniones en 3 niveles y sincronizarla en todos los dashboards.** Cada reunión
tiene los mismos campos/filtros (estado, etapa, BANT, `tipo_respuesta`, status) en tres miradas:
**(a) lo que valida Conprospección (`_cp`)**, **(b) lo que valida el cliente (`_cli`)** y **(c) la validación
final (`_final`, la define CP)**. Como es una sola fila en `seguimiento_reuniones`, los 3 dashboards
(Indicadores · Validación · Seguimiento) leen y escriben lo mismo → **siempre la misma información**. Los
% de avance y el Indicadores semanal se calculan con la **validación final**.
