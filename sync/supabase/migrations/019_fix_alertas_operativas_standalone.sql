alter table public.reuniones add column if not exists estado_validacion text;
alter table public.reuniones add column if not exists motivo_no_valida text;
alter table public.reuniones add column if not exists fecha_validacion date;
alter table public.reuniones add column if not exists reagendada boolean;
alter table public.reuniones add column if not exists cancelada boolean;
alter table public.reuniones add column if not exists no_show boolean;
alter table public.reuniones add column if not exists pendiente_validacion boolean;
alter table public.reuniones add column if not exists asignacion_estado text;
alter table public.reuniones add column if not exists asignacion_fuente text;

alter table public.llamadas add column if not exists asignacion_estado text;
alter table public.llamadas add column if not exists asignacion_fuente text;

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
select current_date, 'reunion_sin_sdr_id', 'alta',
  r.cliente_id::text, cl.nombre, r.sdr_id::text, s.nombre,
  'reuniones', r.id::text,
  'Reunión sin sdr_id físico',
  'Revisar sdr_slug, owner GHL o stage de oportunidad'
from public.reuniones r
left join public.clientes cl on cl.slug = r.cliente_slug
left join public.sdrs s on s.slug = r.sdr_slug
where r.sdr_id is null

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
select current_date, 'llamada_sin_sdr_id', 'alta',
  l.cliente_id::text, cl.nombre, l.sdr_id::text, s.nombre,
  'llamadas', l.id::text,
  'Llamada sin sdr_id físico',
  'Revisar owner GHL y mapeo sdr_cliente'
from public.llamadas l
left join public.clientes cl on cl.slug = l.cliente_slug
left join public.sdrs s on s.slug = l.sdr_slug
where l.sdr_id is null

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
