# Núcleo de validación de reuniones (3 capas) — Design

**Fecha:** 2026-06-04 · **Autor:** Francisca Polanco · Conprospección
**Estado:** Diseño — pendiente de revisión y plan de implementación
**Reconcilia:** decisiones de brainstorming + propuesta externa (ChatGPT) + correcciones de arquitectura.

## 1. Objetivo

Sistema de **validación operativa, validación cliente y validación final** sobre las reuniones
(que vienen de GHL → Supabase), para medir correctamente el **avance de meta contractual** por
cliente. Una sola fuente de datos sincronizada en 3 dashboards: Seguimiento (interno), Validación
(cliente) y Ejecutivo/Indicadores.

## 2. Principios de diseño (correcciones clave)

1. **Separar "qué pasó" de "si cuenta".** `status_reunion` (operativo) ≠ `validez` (CP/cliente/final).
2. **BANT puro = B · A · N · T.** Es el piso del contrato (≥2 = alerta/guía, NO validez automática).
   Las señales (interés, solicita propuesta, próximo paso) viven en otros campos, no en BANT.
3. **Reusar `seguimiento_reuniones`** (ya existe con columnas por nivel). Extender con columnas
   idempotentes; NO crear esquema paralelo. Sin borrar datos. Compatibilidad hacia atrás.
4. **Validez requiere Realizada.** Solo una reunión `status_reunion = realizada` puede ser Válida.
5. **IA solo recomienda** (Válida/No válida/Revisar). Nunca marca válida final. Es Proyecto 2.
6. **El cliente NO ve el SDR.** El SDR solo aparece en el dashboard interno.

## 3. Modelo de datos (extender `seguimiento_reuniones`)

Una fila por reunión (`reunion_id` PK, `cliente_slug`). Columnas (las que ya existen se reusan):

**Operativo (lo pone el equipo CP):**
- `status_reunion` — agendada · realizada · no_asistio_lead · no_asistio_cliente · cancelada_lead ·
  cancelada_cliente · reagendada · pendiente_reagendar · sin_info.

**Validez CP (equipo / SDR líder):**
- `val_estado_cp` — espera · valida · no_valida · requiere_revision
- `bant_cp` — subset de B,A,N,T (puro)
- `comentario_cp` (texto) · `validated_by_cp` · `validated_cp_at`

**Validez Cliente (la hace el cliente):**
- `val_estado_cli` — espera · valida · no_valida · requiere_revision
- `bant_cli` — subset de B,A,N,T (puro)
- `comentario_cli` (texto) · `validated_by_cli` · `validated_cli_at`
- `tipo_respuesta_cli` — taxonomía única ya existente (Solicita reunión/cotización/… · No interesado…)
- `motivo_no_validez` — no_calza_icp · sin_necesidad · sin_autoridad · sin_presupuesto · sin_timing ·
  no_realizada · otro  (solo si val = no_valida)
- `estado_comercial` — pendiente_seguimiento · proximo_paso · solicita_propuesta · propuesta_enviada ·
  seguimiento_propuesta · negociacion · no_responde · cliente_ganado · cliente_perdido · no_califica
  **(100 % del cliente)**
- `proximo_paso` (texto/bool) — señal de calidad sin IA

**Validez Final (la define CP / Francisca):**
- `val_estado_final` — pendiente · valida · no_valida · en_disputa · reagendada · excluida
- `comentario_final` · `validated_final_by` · `validated_final_at`

**Flags (computados o materializados):**
- `flag_meta_countable` (bool) — true solo si `val_estado_final = valida`
- `flag_disputa` (bool) — CP=valida (≥2 BANT) y cliente=no_valida (o contradicción)
- `flag_cliente_pendiente` (bool) — cliente aún no validó

**IA / grabaciones (Proyecto 2 — crear ahora, vacías):**
- `recording_url` · `transcript_url` · `ai_summary` · `ai_recommendation` (valida/no_valida/revisar) ·
  `ai_bant_detected` · `ai_confidence` · `ai_evidence` · `ai_dispute_flag`

**Tabla nueva `meeting_status_history`** (auditoría):
- `meeting_id` · `field_changed` · `old_value` · `new_value` · `changed_by` · `changed_by_role` ·
  `changed_at` · `source_dashboard`

## 4. Reglas automáticas

1. **Alta (reunión nueva de GHL):** status_reunion=agendada · val_estado_cp=espera ·
   val_estado_cli=espera · val_estado_final=pendiente · flag_cliente_pendiente=true ·
   flag_disputa=false · flag_meta_countable=false.
2. **Candado de validez:** `val_estado_* = valida` solo si `status_reunion = realizada`. Si no asistió /
   cancelada / reagendada → no puede ser válida (bloqueo en UI + check).
3. **CP actualiza:** se ve al instante en el cliente. Si CP=valida y cliente=no_valida → flag_disputa=true
   y val_estado_final=en_disputa.
4. **Cliente actualiza:** se ve al instante en interno. Si cliente=no_valida → `comentario_cli` obligatorio.
   Si contradice a CP → flag_disputa=true.
5. **La final manda:** val_estado_final=valida → flag_meta_countable=true; si no, false. El avance oficial
   cuenta solo flag_meta_countable=true.
6. **BANT ≥2 = guía/alerta:** si cliente=no_valida pero CP tiene ≥2 BANT → disputa. Si CP=valida con
   <2 BANT → aviso. Nunca automático.
7. **Próximo paso acordado:** si val=valida sin `proximo_paso` → pasa a `requiere_revision` (señal de
   calidad). La grabación IA (Proyecto 2) lo confirma.
8. **SDR:** prioridad assigned_to(contacto) → assigned_to(opportunity) → booked_by(appointment) →
   "Sin SDR asignado". **Visible solo en Seguimiento (interno), nunca en el cliente.**
9. **Historial:** todo cambio de un campo de validez/estado escribe una fila en `meeting_status_history`.

## 4b. Integridad de la validación (anti-"engaño") — sin grabación obligatoria

El cliente puede no decir la verdad sobre si la reunión avanzó. Como **no hay grabación gratis
escalable** y Conprospección **no tiene visibilidad del CRM del cliente** (la propuesta/seguimiento
ocurren del lado del cliente), la validez **no depende de la grabación**. Se respalda en lo que sí se
captura, barato y sin trabajo manual extra:

1. **BANT pre-calificado:** el SDR califica al lead *antes* de agendar → evidencia de que entró
   cumpliendo criterio (queda en `bant_cp`).
2. **Asistencia (los 5 min que el SDR ya controla):** el SDR marca `status_reunion`
   (realizada / no_asistio / reagendar). **Optimización clave:** ese paso que hoy el SDR hace manual
   (llamar al lead para que se conecte y avisarle al cliente si se conecta o hay que reagendar) deja de
   ser un mensaje manual → se vuelve un **cambio de estado que el cliente ve al instante** (auto-sync).
3. **Carga de la prueba al cliente:** si el cliente marca `no_valida`, **`comentario_cli` y
   `motivo_no_validez` son obligatorios**. Sin justificación documentada, **manda el contrato**
   (Realizada + ≥2 BANT) y se marca `flag_disputa` para que Francisca resuelva la final.
4. **La final la define Francisca**, con todo a la vista (CP, cliente, motivos, BANT).
5. **Grabación = slot opcional:** los campos `recording_url`/`ai_*` quedan listos; cuando exista una
   grabación (de la herramienta que sea), la IA la lee y **zanja la disputa**. No es requisito.

**Descartado:** artefactos de CRM post-reunión (no hay acceso) y llamado/encuesta manual al lead
(genera trabajo manual; el correo/WhatsApp automático puede no responderse → como mucho, señal extra
opcional, nunca la base).

## 4c. Cruces de estado — propagación automática de la validez FINAL

La validez **final** se deriva automáticamente de los otros estados (y vos la podés sobrescribir
siempre que haga falta). El **CP nunca se pisa**: queda como registro de lo que pensó tu equipo.

**A) El estado operativo manda primero (candado):**
| `status_reunion` | `val_estado_final` automática |
|---|---|
| no_asistio_* / cancelada_* | **no_valida** (excluida) — no cuenta |
| reagendada / pendiente_reagendar | **pendiente** (se valida la reunión nueva) |
| realizada | sigue la lógica de validez (tabla B) |

**B) Validez (solo si `status_reunion = realizada`):**
| Cliente | CP | Final automática |
|---|---|---|
| valida | (cualquiera) | **valida** (cuenta; sin disputa, aunque CP sea no_valida) |
| no_valida | no_valida | **no_valida** |
| no_valida | valida (≥2 BANT) | **en_disputa** → la resuelve Francisca |
| espera (sin validar) | (cualquiera) | **pendiente** |

**Reglas asociadas:**
- **Cliente=valida → final=valida** es automático y **vale para todos** (es el oficial en los 3 dashboards).
- Si Cliente=valida pero CP=no_valida → **el CP se conserva** (registro/auditoría); solo la final pasa a
  valida. No hay disputa (si el cliente dice que sí, cuenta).
- **No realizada nunca es válida** (candado): no_asistio/cancelada → no cuenta, automático.
- Francisca puede **sobrescribir la final** manualmente en cualquier caso (queda en historial con su autor).

## 5. Permisos de edición

| Campo | Seguimiento (equipo) | Validación (cliente) |
|---|---|---|
| status_reunion | **edita** | ve |
| Validez CP + BANT CP + comentario CP | **edita** | ve ("Validez CP") |
| Validez Cliente + BANT Cliente + comentario | ve (Pendiente hasta que cargue) | **edita** |
| Estado comercial + próximo paso | ve | **edita (100 % cliente)** |
| Validez FINAL + comentario final | **la define CP/Francisca** | ve |
| SDR | **ve** | no aplica (oculto) |

## 6. Dashboards

**Seguimiento (interno):**
- Filtros: cliente · SDR · fecha/semana/mes · status_reunion · validez CP · validez cliente · validez
  final · pendientes cliente · en disputa · canal · campaña · país · industria · cargo · ICP.
- Widgets: agendadas · realizadas · pend. validación CP · pend. validación cliente · válidas CP ·
  válidas cliente · válidas finales · en disputa · avance meta oficial · proyección.
- Dedup + orden última fecha (ya hecho). SDR siempre visible.

**Validación (cliente):** fecha · empresa · contacto · cargo · estado reunión · Validez CP (solo lectura) ·
BANT CP (solo lectura) · comentario CP (solo lectura) · **edita:** validez cliente · BANT cliente ·
comentario · estado comercial · próximo paso. Validez final (solo lectura). Link grabación/resumen IA si
existe (Proyecto 2). **Sin SDR.**

**Ejecutivo / Indicadores:**
- Meta mensual · válidas finales · **avance oficial** = válidas finales / meta (flag_meta_countable).
- **Avance probable** = finales + válidas CP pendientes de cliente. *(IA y disputas con evidencia → Proyecto 2.)*
- **Proyección** = avance probable + reuniones futuras × tasa histórica de conversión.
- En disputa · pendientes validación cliente · conversión agendada→válida final · realizada→válida final.
- Suma **estado comercial** como métrica.

## 7. Integración GHL (auditar antes de migrar)

Guardar/enriquecer por reunión: appointment_id · contact_id · opportunity_id · location_id ·
calendar_id · assigned_sdr_id · assigned_sdr_name · meeting_date · lead_name · email · phone ·
company · job_title · campaign/channel. Auditar qué ya leemos (appointments/contacts/opportunities)
y completar lo que falte. Mapeo de SDR según la prioridad de la regla 8.

## 8. Plan de migración (idempotente, sin pérdida)

1. `ALTER TABLE seguimiento_reuniones ADD COLUMN IF NOT EXISTS …` para los campos nuevos
   (status_reunion, comentario_*, validated_*_by/at, motivo_no_validez, estado_comercial→reusar etapa_cli,
   proximo_paso, flags, campos IA).
2. Crear `meeting_status_history`.
3. Mapear datos actuales: `val_estado_*`/`bant_*`/`tipo_respuesta_cli` ya existen → conservar. Setear flags
   a partir de los valores actuales (flag_meta_countable = (val_estado_final='valida')).
4. Implementar reglas automáticas (en los helpers de escritura `shared/seguimiento.py` + checks).
5. Actualizar UI de los 3 dashboards (campos, permisos, candado de validez, alertas).
6. Recalcular métricas (avance oficial/probable/proyección, conversiones).
7. Pruebas: alta de reunión, transición de status, disputa CP↔cliente, candado realizada,
   comentario obligatorio, cálculo de meta con flag, historial registra cambios.

## 9. Fases

- **Proyecto 1 (este spec):** núcleo de validación 3 capas + reglas + flags + historial + SDR + auditoría
  GHL + avance/proyección. Campos IA creados pero vacíos.
- **Proyecto 2 (después):** grabaciones + transcripción + IA que recomienda (no decide) y ayuda a zanjar
  disputas. Llena los campos `ai_*`.

## 10. Fuera de alcance (YAGNI por ahora)

- Traer BANT desde GHL (hasta validar que los clientes lo tengan). Por ahora BANT manual.
- Integración real de grabaciones/IA (Proyecto 2).
