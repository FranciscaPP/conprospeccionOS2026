create or replace view public.vw_llamadas_sin_sdr_revision as
select
  l.cliente_slug,
  cl.nombre as nombre_cliente,
  l.ghl_owner_user_id,
  gu.nombre as nombre_ghl_user,
  gu.email as email_ghl_user,
  gu.tipo_usuario,
  coalesce(gu.es_sdr, false) as es_sdr,
  coalesce(gu.excluir_metricas_sdr, false) as excluir_metricas_sdr,
  case
    when l.ghl_owner_user_id is null then 'sin_owner_ghl'
    when gu.ghl_user_id is null then 'owner_no_en_ghl_users'
    when coalesce(gu.excluir_metricas_sdr, false) is true then 'operacion_admin_excluido'
    when coalesce(gu.es_sdr, false) is true and gu.sdr_slug is null then 'sdr_sin_slug_mapeado'
    else 'revisar_owner'
  end as categoria_revision,
  count(*) as llamadas,
  min(l.fecha) as primera_llamada,
  max(l.fecha) as ultima_llamada
from public.llamadas l
left join public.clientes cl on cl.slug = l.cliente_slug
left join public.ghl_users gu
  on gu.ghl_user_id = l.ghl_owner_user_id
 and gu.cliente_slug = l.cliente_slug
where l.sdr_id is null
group by
  l.cliente_slug,
  cl.nombre,
  l.ghl_owner_user_id,
  gu.nombre,
  gu.email,
  gu.tipo_usuario,
  gu.es_sdr,
  gu.excluir_metricas_sdr,
  gu.ghl_user_id,
  gu.sdr_slug;

create or replace view public.vw_reuniones_sin_sdr_revision as
select
  r.cliente_slug,
  cl.nombre as nombre_cliente,
  r.ghl_owner_user_id,
  gu.nombre as nombre_ghl_user,
  gu.email as email_ghl_user,
  gu.tipo_usuario,
  coalesce(gu.es_sdr, false) as es_sdr,
  coalesce(gu.excluir_metricas_sdr, false) as excluir_metricas_sdr,
  r.opportunity_id,
  o.pipeline_name,
  o.pipeline_stage_name,
  case
    when r.ghl_owner_user_id is null then 'sin_owner_ghl'
    when gu.ghl_user_id is null then 'owner_no_en_ghl_users'
    when coalesce(gu.excluir_metricas_sdr, false) is true then 'operacion_admin_excluido'
    when coalesce(gu.es_sdr, false) is true and gu.sdr_slug is null then 'sdr_sin_slug_mapeado'
    else 'revisar_owner'
  end as categoria_revision,
  count(*) as reuniones,
  count(*) filter (where r.es_valida is true) as reuniones_validas,
  count(*) filter (where r.es_valida is false) as reuniones_no_validas,
  count(*) filter (where r.es_valida is null) as reuniones_pendientes
from public.reuniones r
left join public.clientes cl on cl.slug = r.cliente_slug
left join public.ghl_users gu
  on gu.ghl_user_id = r.ghl_owner_user_id
 and gu.cliente_slug = r.cliente_slug
left join public.oportunidades o
  on o.ghl_opportunity_id = r.opportunity_id
where r.sdr_id is null
group by
  r.cliente_slug,
  cl.nombre,
  r.ghl_owner_user_id,
  gu.nombre,
  gu.email,
  gu.tipo_usuario,
  gu.es_sdr,
  gu.excluir_metricas_sdr,
  gu.ghl_user_id,
  gu.sdr_slug,
  r.opportunity_id,
  o.pipeline_name,
  o.pipeline_stage_name;

drop view if exists public.vw_alertas_operativas;

create or replace view public.vw_alertas_operativas as
select current_date as fecha_alerta, 'reunion_sin_cliente_id' as tipo_alerta, 'alta' as severidad,
  r.cliente_id::text as cliente_id, cl.nombre as nombre_cliente, r.sdr_id::text as sdr_id, s.nombre as nombre_sdr,
  'reuniones' as registro_origen, r.id::text as id_registro_origen,
  'Reunión sin cliente_id físico' as descripcion,
  'Revisar cliente_slug/location_id y completar relación' as accion_recomendada
from public.reuniones r
left join public.clientes cl on cl.slug = r.cliente_slug
left join public.sdrs s on s.slug = r.sdr_slug
where r.cliente_id is null

union all
select current_date, 'reunion_sin_sdr_id_revisar', 'alta',
  r.cliente_id::text, cl.nombre, r.sdr_id::text, s.nombre,
  'reuniones', r.id::text,
  'Reunión sin sdr_id y owner no marcado como admin/operación excluida',
  'Revisar owner GHL, oportunidad y mapeo con SDR'
from public.reuniones r
left join public.clientes cl on cl.slug = r.cliente_slug
left join public.sdrs s on s.slug = r.sdr_slug
left join public.ghl_users gu on gu.ghl_user_id = r.ghl_owner_user_id and gu.cliente_slug = r.cliente_slug
where r.sdr_id is null
  and coalesce(gu.excluir_metricas_sdr, false) is false

union all
select current_date, 'reunion_sin_contacto_id', 'media',
  r.cliente_id::text, cl.nombre, r.sdr_id::text, s.nombre,
  'reuniones', r.id::text,
  'Reunión sin contacto_id físico',
  'Revisar ghl_contact_id contra contactos'
from public.reuniones r
left join public.clientes cl on cl.slug = r.cliente_slug
left join public.sdrs s on s.slug = r.sdr_slug
where r.contacto_id is null

union all
select current_date, 'llamada_sin_sdr_id_revisar', 'alta',
  l.cliente_id::text, cl.nombre, l.sdr_id::text, s.nombre,
  'llamadas', l.id::text,
  'Llamada sin sdr_id y owner no marcado como admin/operación excluida',
  'Revisar owner GHL y mapeo sdr_cliente'
from public.llamadas l
left join public.clientes cl on cl.slug = l.cliente_slug
left join public.sdrs s on s.slug = l.sdr_slug
left join public.ghl_users gu on gu.ghl_user_id = l.ghl_owner_user_id and gu.cliente_slug = l.cliente_slug
where l.sdr_id is null
  and coalesce(gu.excluir_metricas_sdr, false) is false

union all
select current_date, 'llamada_admin_operacion_sin_sdr', 'baja',
  l.cliente_id::text, cl.nombre, l.sdr_id::text, coalesce(gu.nombre, s.nombre),
  'llamadas', l.id::text,
  'Llamada sin SDR atribuida a usuario admin/operación excluido de métricas SDR',
  'No incluir en ranking SDR; mantener como actividad operativa'
from public.llamadas l
left join public.clientes cl on cl.slug = l.cliente_slug
left join public.sdrs s on s.slug = l.sdr_slug
left join public.ghl_users gu on gu.ghl_user_id = l.ghl_owner_user_id and gu.cliente_slug = l.cliente_slug
where l.sdr_id is null
  and coalesce(gu.excluir_metricas_sdr, false) is true

union all
select current_date, 'llamada_sin_cliente_id', 'alta',
  l.cliente_id::text, cl.nombre, l.sdr_id::text, s.nombre,
  'llamadas', l.id::text,
  'Llamada sin cliente_id físico',
  'Revisar cliente_slug/location_id'
from public.llamadas l
left join public.clientes cl on cl.slug = l.cliente_slug
left join public.sdrs s on s.slug = l.sdr_slug
where l.cliente_id is null

union all
select current_date, 'cliente_sin_meta_definida', 'media',
  c.id::text, c.nombre, null::text, null::text,
  'clientes', c.id::text,
  'Cliente sin meta de reuniones configurada',
  'Completar cliente_metas'
from public.clientes c
left join public.cliente_metas cm on cm.cliente_slug = c.slug and cm.periodo = 'contrato'
where cm.reuniones_validas_meta is null or cm.reuniones_validas_meta = 0

union all
select current_date, 'sdr_sin_cliente_asignado', 'media',
  null::text, null::text, s.id::text, s.nombre,
  'sdrs', s.id::text,
  'SDR activo sin cliente asignado',
  'Completar tabla sdr_cliente o desactivar SDR'
from public.sdrs s
where (s.estado = 'activo' or s.activo is true)
  and not exists (select 1 from public.sdr_cliente sc where sc.sdr_slug = s.slug and coalesce(sc.activo, true) is true)

union all
select current_date, 'cliente_bajo_cumplimiento', 'alta',
  c.id::text, c.nombre, null::text, null::text,
  'vw_clientes_riesgo', c.slug,
  'Cliente clasificado en riesgo rojo',
  'Revisar actividad, base, reuniones válidas y fecha de contrato'
from public.vw_clientes_riesgo vr
join public.clientes c on c.slug = vr.cliente_slug
where vr.riesgo = 'rojo'

union all
select current_date, 'sdr_sin_actividad_diaria', 'media',
  null::text, null::text, s.id::text, s.nombre,
  'llamadas', s.slug,
  'SDR activo sin llamadas hoy',
  'Revisar actividad diaria o ausencias'
from public.sdrs s
where (s.estado = 'activo' or s.activo is true)
  and not exists (select 1 from public.llamadas l where l.sdr_slug = s.slug and l.fecha = current_date)

union all
select current_date, 'reunion_pendiente_validacion', 'media',
  r.cliente_id::text, cl.nombre, r.sdr_id::text, s.nombre,
  'reuniones', r.id::text,
  'Reunión pendiente de validación',
  'Validar si fue válida o no válida'
from public.reuniones r
left join public.clientes cl on cl.id = r.cliente_id
left join public.sdrs s on s.id = r.sdr_id
where r.es_valida is null

union all
select current_date, 'reunion_no_valida_sin_motivo', 'media',
  r.cliente_id::text, cl.nombre, r.sdr_id::text, s.nombre,
  'reuniones', r.id::text,
  'Reunión no válida sin motivo registrado',
  'Completar motivo_no_valida/motivo_rechazo'
from public.reuniones r
left join public.clientes cl on cl.id = r.cliente_id
left join public.sdrs s on s.id = r.sdr_id
where r.es_valida is false
  and coalesce(r.motivo_no_valida, r.motivo_rechazo) is null

union all
select current_date, 'oportunidad_sin_proxima_accion', 'baja',
  cl.id::text, cl.nombre, s.id::text, s.nombre,
  'oportunidades', o.ghl_opportunity_id,
  'Oportunidad abierta sin actividad reciente registrada',
  'Revisar stage y próxima acción en GHL'
from public.oportunidades o
left join public.clientes cl on cl.slug = o.cliente_slug
left join public.sdrs s on s.slug = o.sdr_slug
where lower(coalesce(o.estado, '')) not in ('won', 'lost', 'abandoned')
  and greatest(o.last_status_change_at, o.last_stage_change_at, o.ghl_updated_at) < now() - interval '14 days';
