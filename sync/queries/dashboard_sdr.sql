-- Ranking SDR diario
select * from public.vw_ranking_sdr_hoy;

-- Ranking SDR semanal
select
  s.slug as sdr_slug,
  s.nombre as sdr,
  coalesce(l.llamadas_semana, 0) as llamadas_semana,
  coalesce(l.minutos_semana, 0) as minutos_semana,
  coalesce(r.reuniones_semana, 0) as reuniones_semana,
  coalesce(r.validas_semana, 0) as validas_semana,
  case when coalesce(l.llamadas_semana, 0) = 0 then 0 else round(coalesce(r.reuniones_semana, 0) / l.llamadas_semana, 4) end as conversion_semanal
from public.sdrs s
left join (
  select sdr_slug, count(*)::numeric llamadas_semana, coalesce(sum(duracion_minutos), 0)::numeric minutos_semana
  from public.llamadas
  where fecha >= date_trunc('week', current_date)::date
  group by sdr_slug
) l on l.sdr_slug = s.slug
left join (
  select sdr_slug, count(*)::numeric reuniones_semana, count(*) filter (where es_valida is true)::numeric validas_semana
  from public.reuniones
  where fecha_reunion >= date_trunc('week', current_date)::date
  group by sdr_slug
) r on r.sdr_slug = s.slug
where s.estado = 'activo'
order by validas_semana desc, reuniones_semana desc, llamadas_semana desc;

-- Vista por SDR y cliente asignado
select
  sc.sdr_slug,
  s.nombre as sdr,
  sc.cliente_slug,
  c.nombre as cliente,
  count(distinct l.ghl_call_id) as llamadas,
  coalesce(sum(l.duracion_minutos), 0) as minutos,
  count(distinct r.ghl_appointment_id) as reuniones,
  count(distinct r.ghl_appointment_id) filter (where r.es_valida is true) as validas
from public.sdr_cliente sc
left join public.sdrs s on s.slug = sc.sdr_slug
left join public.clientes c on c.slug = sc.cliente_slug
left join public.llamadas l on l.sdr_slug = sc.sdr_slug and l.cliente_slug = sc.cliente_slug
left join public.reuniones r on r.sdr_slug = sc.sdr_slug and r.cliente_slug = sc.cliente_slug
where sc.activo is true
group by sc.sdr_slug, s.nombre, sc.cliente_slug, c.nombre
order by s.nombre, c.nombre;
