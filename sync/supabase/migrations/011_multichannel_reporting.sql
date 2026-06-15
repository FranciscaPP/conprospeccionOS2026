create or replace view public.vw_contactos_multifuente as
select
  'ghl' as fuente,
  c.cliente_slug,
  cl.nombre as cliente,
  c.sdr_slug,
  c.ghl_contact_id as source_contact_id,
  lower(nullif(trim(c.email), '')) as email_normalizado,
  regexp_replace(coalesce(c.telefono, ''), '\D', '', 'g') as telefono_normalizado,
  coalesce(c.nombre_contacto, c.nombre) as contacto,
  c.nombre_empresa as empresa,
  c.cargo,
  c.industria,
  c.pais,
  c.ghl_created_at as created_at_source
from public.contactos c
left join public.clientes cl on cl.slug = c.cliente_slug

union all

select
  'snov' as fuente,
  e.cliente_slug,
  cl.nombre as cliente,
  e.sdr_slug,
  e.prospect_id as source_contact_id,
  lower(nullif(trim(e.prospect_email), '')) as email_normalizado,
  null as telefono_normalizado,
  e.prospect_name as contacto,
  e.company as empresa,
  e.cargo,
  e.industria,
  e.pais,
  e.occurred_at as created_at_source
from public.snov_email_events e
left join public.clientes cl on cl.slug = e.cliente_slug
where e.prospect_email is not null;

create or replace view public.vw_contactos_overlap_ghl_snov as
select
  g.cliente_slug,
  g.cliente,
  g.email_normalizado,
  max(g.contacto) filter (where g.fuente = 'ghl') as contacto_ghl,
  max(g.contacto) filter (where g.fuente = 'snov') as contacto_snov,
  count(*) filter (where g.fuente = 'ghl') as apariciones_ghl,
  count(*) filter (where g.fuente = 'snov') as apariciones_snov,
  min(g.created_at_source) as primera_aparicion,
  max(g.created_at_source) as ultima_aparicion
from public.vw_contactos_multifuente g
where g.email_normalizado is not null
group by g.cliente_slug, g.cliente, g.email_normalizado
having count(*) filter (where g.fuente = 'ghl') > 0
   and count(*) filter (where g.fuente = 'snov') > 0;

create or replace view public.vw_actividad_multicanal_diaria as
select
  l.fecha,
  l.cliente_slug,
  cl.nombre as cliente,
  l.sdr_slug,
  'llamada' as canal,
  count(*) as actividades,
  coalesce(sum(l.duracion_minutos), 0)::numeric as minutos,
  0::numeric as respuestas,
  0::numeric as reuniones
from public.llamadas l
left join public.clientes cl on cl.slug = l.cliente_slug
where l.fecha is not null
group by l.fecha, l.cliente_slug, cl.nombre, l.sdr_slug

union all

select
  r.fecha_reunion as fecha,
  r.cliente_slug,
  cl.nombre as cliente,
  r.sdr_slug,
  'reunion' as canal,
  count(*) as actividades,
  0::numeric as minutos,
  0::numeric as respuestas,
  count(*) filter (where r.es_valida is true)::numeric as reuniones
from public.reuniones r
left join public.clientes cl on cl.slug = r.cliente_slug
where r.fecha_reunion is not null
group by r.fecha_reunion, r.cliente_slug, cl.nombre, r.sdr_slug

union all

select
  e.occurred_at::date as fecha,
  e.cliente_slug,
  cl.nombre as cliente,
  e.sdr_slug,
  'correo' as canal,
  count(*) filter (where e.event_type in ('sent', 'open', 'click', 'reply')) as actividades,
  0::numeric as minutos,
  count(*) filter (where e.event_type = 'reply')::numeric as respuestas,
  0::numeric as reuniones
from public.snov_email_events e
left join public.clientes cl on cl.slug = e.cliente_slug
where e.occurred_at is not null
group by e.occurred_at::date, e.cliente_slug, cl.nombre, e.sdr_slug;

create or replace view public.vw_cliente_multicanal_resumen as
select
  cliente_slug,
  cliente,
  fecha,
  sum(actividades) filter (where canal = 'llamada') as llamadas,
  sum(minutos) filter (where canal = 'llamada') as minutos_llamada,
  sum(actividades) filter (where canal = 'correo') as eventos_correo,
  sum(respuestas) filter (where canal = 'correo') as respuestas_correo,
  sum(reuniones) filter (where canal = 'reunion') as reuniones_validas
from public.vw_actividad_multicanal_diaria
group by cliente_slug, cliente, fecha;
