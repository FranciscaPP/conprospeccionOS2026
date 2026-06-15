-- 020 - Backfill seguro + vistas principales para Metabase.
-- No borra datos. Solo completa campos NULL usando joins confiables.

create table if not exists public.backup_reuniones_pre_020 as
select * from public.reuniones;

create table if not exists public.backup_llamadas_pre_020 as
select * from public.llamadas;

create table if not exists public.backup_pagos_sdr_pre_020 as
select * from public.pagos_sdr;

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

alter table public.pagos_sdr add column if not exists periodo_mes date;
alter table public.pagos_sdr add column if not exists reuniones_validas_periodo numeric not null default 0;
alter table public.pagos_sdr add column if not exists monto_base numeric not null default 0;
alter table public.pagos_sdr add column if not exists monto_variable numeric not null default 0;
alter table public.pagos_sdr add column if not exists ajustes numeric not null default 0;
alter table public.pagos_sdr add column if not exists total_pagado numeric not null default 0;
alter table public.pagos_sdr add column if not exists moneda text not null default 'USD';
alter table public.pagos_sdr add column if not exists fecha_pago date;
alter table public.pagos_sdr add column if not exists estado_pago text not null default 'pendiente';
alter table public.pagos_sdr add column if not exists observaciones_pago text;

update public.reuniones r
set opportunity_id = replace(r.ghl_appointment_id, 'opportunity:', '')
where r.opportunity_id is null
  and r.ghl_appointment_id like 'opportunity:%';

update public.reuniones r
set
  cliente_slug = coalesce(r.cliente_slug, o.cliente_slug),
  sdr_slug = coalesce(r.sdr_slug, o.sdr_slug),
  ghl_contact_id = coalesce(r.ghl_contact_id, o.ghl_contact_id),
  ghl_owner_user_id = coalesce(r.ghl_owner_user_id, o.ghl_owner_user_id),
  location_id = coalesce(r.location_id, o.location_id),
  asignacion_fuente = coalesce(r.asignacion_fuente, 'oportunidades')
from public.oportunidades o
where (r.opportunity_id = o.ghl_opportunity_id or replace(r.ghl_appointment_id, 'opportunity:', '') = o.ghl_opportunity_id)
  and (
    r.cliente_slug is null
    or r.sdr_slug is null
    or r.ghl_contact_id is null
    or r.ghl_owner_user_id is null
    or r.location_id is null
  );

update public.reuniones r
set cliente_id = c.id
from public.clientes c
where r.cliente_id is null
  and r.cliente_slug = c.slug;

update public.reuniones r
set sdr_id = s.id
from public.sdrs s
where r.sdr_id is null
  and r.sdr_slug = s.slug;

update public.reuniones r
set contacto_id = c.id
from public.contactos c
where r.contacto_id is null
  and r.ghl_contact_id = c.ghl_contact_id;

update public.reuniones r
set
  estado_validacion = coalesce(
    r.estado_validacion,
    case
      when r.es_valida is true then 'valida'
      when r.es_valida is false then 'no_valida'
      else 'pendiente_validacion'
    end
  ),
  motivo_no_valida = coalesce(r.motivo_no_valida, r.motivo_rechazo),
  reagendada = coalesce(r.reagendada, lower(coalesce(r.estado_reunion, r.estado, '')) like '%reagend%'),
  cancelada = coalesce(r.cancelada, lower(coalesce(r.estado_reunion, r.estado, '')) like '%cancel%'),
  no_show = coalesce(r.no_show, lower(coalesce(r.estado_reunion, r.estado, '')) in ('no_show', 'no show', 'noshow')),
  pendiente_validacion = coalesce(r.pendiente_validacion, r.es_valida is null),
  asignacion_estado = case
    when r.cliente_id is null then 'sin_cliente'
    when r.sdr_id is null then 'sin_sdr'
    when r.contacto_id is null then 'sin_contacto'
    else 'relacionada'
  end;

update public.llamadas l
set sdr_slug = coalesce(l.sdr_slug, gu.sdr_slug),
    asignacion_fuente = coalesce(l.asignacion_fuente, 'ghl_users')
from public.ghl_users gu
where l.sdr_slug is null
  and l.ghl_owner_user_id = gu.ghl_user_id
  and gu.sdr_slug is not null
  and coalesce(gu.excluir_metricas_sdr, false) is false;

update public.llamadas l
set sdr_slug = coalesce(l.sdr_slug, sc.sdr_slug),
    asignacion_fuente = coalesce(l.asignacion_fuente, 'sdr_cliente')
from public.sdr_cliente sc
where l.sdr_slug is null
  and l.cliente_slug = sc.cliente_slug
  and l.ghl_owner_user_id = sc.ghl_user_id
  and coalesce(sc.activo, true) is true;

update public.llamadas l
set cliente_id = c.id
from public.clientes c
where l.cliente_id is null
  and l.cliente_slug = c.slug;

update public.llamadas l
set sdr_id = s.id
from public.sdrs s
where l.sdr_id is null
  and l.sdr_slug = s.slug;

update public.llamadas l
set contacto_id = c.id
from public.contactos c
where l.contacto_id is null
  and l.ghl_contact_id = c.ghl_contact_id;

update public.llamadas l
set asignacion_estado = case
    when l.cliente_id is null then 'sin_cliente'
    when l.sdr_id is null then 'sin_sdr'
    when l.contacto_id is null then 'sin_contacto'
    else 'relacionada'
  end;

create or replace view public.vw_sdrs_normalizados as
select
  s.id as sdr_id,
  s.slug as sdr_slug,
  s.nombre as nombre_sdr,
  coalesce(s.email, max(gu.email)) as email_sdr,
  coalesce(s.ghl_user_id, max(sc.ghl_user_id), max(gu.ghl_user_id)) as ghl_user_id,
  coalesce(s.estado, case when s.activo then 'activo' else 'inactivo' end) as estado_activo,
  count(distinct sc.cliente_slug) filter (where coalesce(sc.activo, true) is true) as clientes_asignados,
  string_agg(distinct c.nombre, ', ' order by c.nombre) filter (where coalesce(sc.activo, true) is true) as nombres_clientes_asignados
from public.sdrs s
left join public.sdr_cliente sc on sc.sdr_slug = s.slug
left join public.clientes c on c.slug = sc.cliente_slug
left join public.ghl_users gu on gu.sdr_slug = s.slug
group by s.id, s.slug, s.nombre, s.email, s.ghl_user_id, s.estado, s.activo;

create or replace view public.vw_clientes_normalizados as
select
  c.id as cliente_id,
  c.slug as cliente_slug,
  c.nombre as nombre_cliente,
  c.estado_contrato as estado_cliente,
  c.pais_prospeccion,
  c.ghl_location_id,
  cm.reuniones_validas_meta as meta_reuniones_total,
  c.meta_mensual_reuniones as meta_reuniones_mensual,
  cc.fecha_inicio as fecha_inicio_servicio,
  cc.fecha_termino as fecha_fin_servicio,
  cc.duracion_meses as cantidad_meses_contrato,
  cm.reuniones_validas_meta as reuniones_garantizadas,
  coalesce(ccos.pago_mensual, 0) as monto_fijo_mensual,
  coalesce(ccos.pago_variable, 0) as monto_variable_por_reunion,
  coalesce(ccos.pago_mensual_moneda, ccos.pago_variable_moneda, 'USD') as moneda,
  (c.estado_contrato in ('activo', 'extension', 'extensión')) as estado_activo
from public.clientes c
left join public.cliente_metas cm on cm.cliente_slug = c.slug and cm.periodo = 'contrato'
left join public.cliente_contratos cc on cc.cliente_slug = c.slug
left join public.cliente_costos ccos on ccos.cliente_slug = c.slug;

create or replace view public.vw_reuniones_dashboard as
select
  r.id as reunion_id,
  r.ghl_appointment_id,
  coalesce(r.opportunity_id, replace(r.ghl_appointment_id, 'opportunity:', '')) as opportunity_id,
  r.fecha_reunion,
  r.fecha_agendada,
  r.cliente_id,
  cl.nombre as nombre_cliente,
  r.sdr_id,
  s.nombre as nombre_sdr,
  r.contacto_id,
  coalesce(r.contacto, ct.nombre_contacto, ct.nombre) as nombre_contacto,
  coalesce(r.empresa, ct.nombre_empresa, ct.empresa, o.contacto_empresa) as empresa,
  coalesce(r.cargo, ct.cargo) as cargo,
  coalesce(r.pais, ct.pais) as pais,
  coalesce(r.industria, ct.industria) as industria,
  case
    when coalesce(r.cancelada, false) then 'cancelada'
    when coalesce(r.no_show, false) then 'no_show'
    when coalesce(r.reagendada, false) then 'reagendada'
    when r.es_valida is true then 'valida'
    when r.es_valida is false then 'no_valida'
    when coalesce(r.pendiente_validacion, false) then 'pendiente_validacion'
    else coalesce(r.estado_reunion, r.estado, 'agendada')
  end as estado_reunion,
  coalesce(r.estado_validacion, case when r.es_valida is true then 'valida' when r.es_valida is false then 'no_valida' else 'pendiente_validacion' end) as estado_validacion,
  r.es_valida,
  coalesce(r.motivo_no_valida, r.motivo_rechazo) as motivo_no_valida,
  coalesce(r.origen_reunion, 'ghl') as origen,
  o.pipeline_name as pipeline,
  coalesce(o.pipeline_stage_name, gps.stage_name) as pipeline_stage,
  coalesce(r.starts_at, r.synced_at) as created_at,
  r.synced_at as updated_at
from public.reuniones r
left join public.clientes cl on cl.id = r.cliente_id or cl.slug = r.cliente_slug
left join public.sdrs s on s.id = r.sdr_id or s.slug = r.sdr_slug
left join public.contactos ct on ct.id = r.contacto_id or ct.ghl_contact_id = r.ghl_contact_id
left join public.oportunidades o on o.ghl_opportunity_id = coalesce(r.opportunity_id, replace(r.ghl_appointment_id, 'opportunity:', ''))
left join public.ghl_pipeline_stages gps on gps.cliente_slug = o.cliente_slug and gps.stage_id = o.pipeline_stage_id;

create or replace view public.vw_llamadas_dashboard as
select
  l.id as llamada_id,
  l.fecha as fecha_llamada,
  l.cliente_id,
  cl.nombre as nombre_cliente,
  l.sdr_id,
  s.nombre as nombre_sdr,
  l.contacto_id,
  coalesce(ct.nombre_contacto, ct.nombre) as nombre_contacto,
  coalesce(ct.nombre_empresa, ct.empresa) as empresa,
  coalesce(l.telefono, ct.telefono) as telefono,
  ct.pais,
  ct.industria,
  ct.cargo,
  coalesce(l.resultado, l.status) as resultado_llamada,
  coalesce(l.duracion_minutos, round(l.duracion_segundos / 60.0, 2), 0) as duracion,
  (coalesce(l.duracion_segundos, 0) > 0 or lower(coalesce(l.resultado, l.status, '')) in ('completed', 'connected')) as conectada,
  exists (
    select 1
    from public.reuniones r
    where r.ghl_contact_id = l.ghl_contact_id
      and r.cliente_slug = l.cliente_slug
      and (r.sdr_slug = l.sdr_slug or r.sdr_slug is null or l.sdr_slug is null)
      and r.fecha_reunion >= l.fecha
  ) as genero_reunion,
  (
    select o.ghl_opportunity_id
    from public.oportunidades o
    where o.ghl_contact_id = l.ghl_contact_id
      and o.cliente_slug = l.cliente_slug
    order by o.ghl_created_at desc nulls last
    limit 1
  ) as opportunity_id,
  coalesce(l.started_at, l.synced_at) as created_at
from public.llamadas l
left join public.clientes cl on cl.id = l.cliente_id or cl.slug = l.cliente_slug
left join public.sdrs s on s.id = l.sdr_id or s.slug = l.sdr_slug
left join public.contactos ct on ct.id = l.contacto_id or ct.ghl_contact_id = l.ghl_contact_id;

create or replace view public.vw_oportunidades_dashboard as
select
  o.ghl_opportunity_id as opportunity_id,
  o.ghl_created_at as fecha_creacion,
  o.ghl_updated_at as fecha_actualizacion,
  cl.id as cliente_id,
  cl.nombre as nombre_cliente,
  s.id as sdr_id,
  s.nombre as nombre_sdr,
  ct.id as contacto_id,
  coalesce(o.contacto_nombre, ct.nombre_contacto, ct.nombre) as nombre_contacto,
  coalesce(o.contacto_empresa, ct.nombre_empresa, ct.empresa) as empresa,
  ct.cargo,
  ct.pais,
  ct.industria,
  o.pipeline_name as pipeline,
  coalesce(o.pipeline_stage_name, gps.stage_name) as stage,
  o.estado as estado_oportunidad,
  o.valor_monetario as valor_oportunidad,
  o.fuente as origen,
  greatest(o.last_status_change_at, o.last_stage_change_at, o.ghl_updated_at) as fecha_ultima_actividad
from public.oportunidades o
left join public.clientes cl on cl.slug = o.cliente_slug
left join public.sdrs s on s.slug = o.sdr_slug
left join public.contactos ct on ct.ghl_contact_id = o.ghl_contact_id
left join public.ghl_pipeline_stages gps on gps.cliente_slug = o.cliente_slug and gps.stage_id = o.pipeline_stage_id;

create or replace view public.vw_performance_sdr_diario as
with fechas as (
  select fecha from public.llamadas where fecha is not null
  union
  select fecha_reunion from public.reuniones where fecha_reunion is not null
  union
  select ghl_created_at::date from public.oportunidades where ghl_created_at is not null
),
dim as (
  select distinct f.fecha, sc.sdr_slug, sc.cliente_slug
  from fechas f
  cross join public.sdr_cliente sc
  where coalesce(sc.activo, true) is true
)
select
  d.fecha,
  s.id as sdr_id,
  s.nombre as nombre_sdr,
  c.id as cliente_id,
  c.nombre as nombre_cliente,
  coalesce(l.total_llamadas, 0) as total_llamadas,
  coalesce(l.llamadas_conectadas, 0) as llamadas_conectadas,
  coalesce(r.reuniones_agendadas, 0) as reuniones_agendadas,
  coalesce(r.reuniones_validas, 0) as reuniones_validas,
  coalesce(r.reuniones_no_validas, 0) as reuniones_no_validas,
  coalesce(r.reuniones_reagendadas, 0) as reuniones_reagendadas,
  coalesce(o.oportunidades_creadas, 0) as oportunidades_creadas,
  case when coalesce(l.total_llamadas, 0) = 0 then 0 else round(coalesce(r.reuniones_agendadas, 0)::numeric / nullif(l.total_llamadas, 0), 4) end as tasa_llamada_a_reunion,
  case when coalesce(r.reuniones_agendadas, 0) = 0 then 0 else round(coalesce(r.reuniones_validas, 0)::numeric / nullif(r.reuniones_agendadas, 0), 4) end as tasa_reunion_valida,
  0::numeric as cumplimiento_meta_diaria
from dim d
join public.sdrs s on s.slug = d.sdr_slug
join public.clientes c on c.slug = d.cliente_slug
left join (
  select fecha, sdr_slug, cliente_slug,
    count(*) as total_llamadas,
    count(*) filter (where coalesce(duracion_segundos, 0) > 0) as llamadas_conectadas
  from public.llamadas
  group by fecha, sdr_slug, cliente_slug
) l on l.fecha = d.fecha and l.sdr_slug = d.sdr_slug and l.cliente_slug = d.cliente_slug
left join (
  select fecha_reunion as fecha, sdr_slug, cliente_slug,
    count(*) as reuniones_agendadas,
    count(*) filter (where es_valida is true) as reuniones_validas,
    count(*) filter (where es_valida is false) as reuniones_no_validas,
    count(*) filter (where coalesce(reagendada, false) is true or lower(coalesce(estado_reunion, '')) like '%reagend%') as reuniones_reagendadas
  from public.reuniones
  group by fecha_reunion, sdr_slug, cliente_slug
) r on r.fecha = d.fecha and r.sdr_slug = d.sdr_slug and r.cliente_slug = d.cliente_slug
left join (
  select ghl_created_at::date as fecha, sdr_slug, cliente_slug, count(*) as oportunidades_creadas
  from public.oportunidades
  where ghl_created_at is not null
  group by ghl_created_at::date, sdr_slug, cliente_slug
) o on o.fecha = d.fecha and o.sdr_slug = d.sdr_slug and o.cliente_slug = d.cliente_slug;

create or replace view public.vw_performance_cliente_diario as
with fechas as (
  select fecha from public.llamadas where fecha is not null
  union
  select fecha_reunion from public.reuniones where fecha_reunion is not null
  union
  select ghl_created_at::date from public.oportunidades where ghl_created_at is not null
),
dim as (
  select f.fecha, c.slug as cliente_slug
  from fechas f
  cross join public.clientes c
)
select
  d.fecha,
  c.id as cliente_id,
  c.nombre as nombre_cliente,
  coalesce(l.total_llamadas, 0) as total_llamadas,
  coalesce(r.reuniones_agendadas, 0) as reuniones_agendadas,
  coalesce(r.reuniones_validas, 0) as reuniones_validas,
  coalesce(r.reuniones_no_validas, 0) as reuniones_no_validas,
  coalesce(o.oportunidades_creadas, 0) as oportunidades_creadas,
  case when coalesce(c.meta_mensual_reuniones, 0) = 0 then 0 else round(coalesce(rm.reuniones_validas_mes, 0)::numeric / nullif(c.meta_mensual_reuniones, 0), 4) end as avance_meta_mensual,
  case when coalesce(cm.reuniones_validas_meta, 0) = 0 then 0 else round(coalesce(rt.reuniones_validas_total, 0)::numeric / nullif(cm.reuniones_validas_meta, 0), 4) end as avance_meta_total,
  greatest(coalesce(cm.reuniones_validas_meta, 0) - coalesce(rt.reuniones_validas_total, 0), 0) as reuniones_faltantes_meta,
  round(coalesce(rm.reuniones_validas_mes, 0)::numeric / greatest(extract(day from d.fecha), 1) * extract(day from (date_trunc('month', d.fecha) + interval '1 month - 1 day')), 2) as proyeccion_cierre_mes
from dim d
join public.clientes c on c.slug = d.cliente_slug
left join public.cliente_metas cm on cm.cliente_slug = c.slug and cm.periodo = 'contrato'
left join (
  select fecha, cliente_slug, count(*) as total_llamadas
  from public.llamadas
  group by fecha, cliente_slug
) l on l.fecha = d.fecha and l.cliente_slug = d.cliente_slug
left join (
  select fecha_reunion as fecha, cliente_slug,
    count(*) as reuniones_agendadas,
    count(*) filter (where es_valida is true) as reuniones_validas,
    count(*) filter (where es_valida is false) as reuniones_no_validas
  from public.reuniones
  group by fecha_reunion, cliente_slug
) r on r.fecha = d.fecha and r.cliente_slug = d.cliente_slug
left join (
  select ghl_created_at::date as fecha, cliente_slug, count(*) as oportunidades_creadas
  from public.oportunidades
  where ghl_created_at is not null
  group by ghl_created_at::date, cliente_slug
) o on o.fecha = d.fecha and o.cliente_slug = d.cliente_slug
left join (
  select date_trunc('month', fecha_reunion)::date as mes, cliente_slug, count(*) as reuniones_validas_mes
  from public.reuniones
  where es_valida is true
  group by date_trunc('month', fecha_reunion)::date, cliente_slug
) rm on rm.mes = date_trunc('month', d.fecha)::date and rm.cliente_slug = d.cliente_slug
left join (
  select cliente_slug, count(*) as reuniones_validas_total
  from public.reuniones
  where es_valida is true
  group by cliente_slug
) rt on rt.cliente_slug = d.cliente_slug;

create or replace view public.vw_dashboard_general as
select
  current_date as fecha,
  (select count(*) from public.clientes where estado_contrato in ('activo', 'extension', 'extensión')) as total_clientes_activos,
  (select count(*) from public.sdrs where estado = 'activo' or activo is true) as total_sdr_activos,
  (select count(*) from public.llamadas) as total_llamadas,
  (select count(*) from public.reuniones) as total_reuniones_agendadas,
  (select count(*) from public.reuniones where es_valida is true) as total_reuniones_validas,
  (select count(*) from public.reuniones where es_valida is false) as total_reuniones_no_validas,
  (select count(*) from public.oportunidades) as total_oportunidades,
  case when (select count(*) from public.llamadas) = 0 then 0 else round((select count(*) from public.reuniones)::numeric / nullif((select count(*) from public.llamadas), 0), 4) end as tasa_conversion_llamada_reunion,
  case when (select count(*) from public.reuniones) = 0 then 0 else round((select count(*) from public.reuniones where es_valida is true)::numeric / nullif((select count(*) from public.reuniones), 0), 4) end as tasa_conversion_reunion_valida,
  case when (select coalesce(sum(reuniones_validas_meta), 0) from public.cliente_metas where periodo = 'contrato') = 0 then 0
    else round((select count(*) from public.reuniones where es_valida is true)::numeric / nullif((select sum(reuniones_validas_meta) from public.cliente_metas where periodo = 'contrato'), 0), 4)
  end as cumplimiento_global_meta,
  (select count(*) from public.vw_clientes_riesgo where riesgo = 'rojo') as clientes_en_riesgo,
  (select count(*) from public.vw_performance_sdr_cliente where diagnostico_operacional in ('baja_actividad_sin_llamadas_semana', 'llama_mucho_y_no_agenda', 'agenda_pero_no_valida', 'cliente_en_riesgo_y_baja_actividad')) as sdrs_bajo_rendimiento;

create or replace view public.vw_pagos_sdr_estimados as
with mensual as (
  select
    date_trunc('month', fecha_reunion)::date as mes,
    sdr_id,
    sdr_slug,
    cliente_id,
    cliente_slug,
    count(*) filter (where es_valida is true) as reuniones_validas
  from public.reuniones
  where fecha_reunion is not null
  group by date_trunc('month', fecha_reunion)::date, sdr_id, sdr_slug, cliente_id, cliente_slug
),
semanal as (
  select
    date_trunc('month', fecha_reunion)::date as mes,
    date_trunc('week', fecha_reunion)::date as semana,
    sdr_id,
    sdr_slug,
    cliente_id,
    cliente_slug,
    count(*) filter (where es_valida is true) as reuniones_validas_semana
  from public.reuniones
  where fecha_reunion is not null
  group by date_trunc('month', fecha_reunion)::date, date_trunc('week', fecha_reunion)::date, sdr_id, sdr_slug, cliente_id, cliente_slug
),
bonos_semana as (
  select
    mes,
    sdr_id,
    sdr_slug,
    cliente_id,
    cliente_slug,
    count(*) filter (where reuniones_validas_semana >= 3) * 15::numeric as bono_semanal
  from semanal
  group by mes, sdr_id, sdr_slug, cliente_id, cliente_slug
)
select
  m.mes,
  null::date as semana,
  m.sdr_id,
  s.nombre as nombre_sdr,
  m.cliente_id,
  c.nombre as nombre_cliente,
  m.reuniones_validas,
  (m.reuniones_validas >= 4) as cumple_base,
  case when m.reuniones_validas >= 4 then 100 else 0 end::numeric as monto_base,
  (m.reuniones_validas * 10)::numeric as monto_variable,
  coalesce(bs.bono_semanal, 0) as bono_semanal,
  case when m.reuniones_validas >= 8 then 50 else 0 end::numeric as bono_mensual,
  (
    case when m.reuniones_validas >= 4 then 100 else 0 end
    + (m.reuniones_validas * 10)
    + coalesce(bs.bono_semanal, 0)
    + case when m.reuniones_validas >= 8 then 50 else 0 end
  )::numeric as total_estimado_a_pagar
from mensual m
left join bonos_semana bs on bs.mes = m.mes and bs.sdr_slug = m.sdr_slug and bs.cliente_slug = m.cliente_slug
left join public.sdrs s on s.id = m.sdr_id or s.slug = m.sdr_slug
left join public.clientes c on c.id = m.cliente_id or c.slug = m.cliente_slug;
