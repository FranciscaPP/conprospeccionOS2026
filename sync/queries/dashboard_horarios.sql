-- Conversion por hora general
select
  extract(hour from l.hora)::int as hora,
  count(*) as llamadas,
  count(r.*) as reuniones,
  coalesce(sum(l.duracion_minutos), 0) as minutos,
  case when count(*) = 0 then 0 else round(count(r.*)::numeric / count(*), 4) end as conversion_hora
from public.llamadas l
left join public.reuniones r
  on r.sdr_slug = l.sdr_slug
 and r.cliente_slug = l.cliente_slug
 and r.fecha_agendada = l.fecha
where l.hora is not null
group by extract(hour from l.hora)
order by hora;

-- Mejor horario por SDR
select
  l.sdr_slug,
  extract(hour from l.hora)::int as hora,
  count(*) as llamadas,
  count(r.*) as reuniones,
  case when count(*) = 0 then 0 else round(count(r.*)::numeric / count(*), 4) end as conversion_hora
from public.llamadas l
left join public.reuniones r
  on r.sdr_slug = l.sdr_slug
 and r.cliente_slug = l.cliente_slug
 and r.fecha_agendada = l.fecha
where l.hora is not null
group by l.sdr_slug, extract(hour from l.hora)
order by l.sdr_slug, conversion_hora desc;
