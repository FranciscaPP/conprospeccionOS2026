-- Estado, avance y riesgo por cliente
select * from public.vw_clientes_riesgo order by riesgo desc, avance_meta asc;

-- Operacion por cliente
select
  c.slug as cliente_slug,
  c.nombre as cliente,
  count(distinct ct.ghl_contact_id) as contactos_cargados,
  count(distinct l.ghl_call_id) as llamadas,
  coalesce(sum(l.duracion_minutos), 0) as minutos,
  count(distinct r.ghl_appointment_id) as reuniones,
  count(distinct r.ghl_appointment_id) filter (where r.es_valida is true) as reuniones_validas,
  case when count(distinct l.ghl_call_id) = 0 then 0 else round(count(distinct r.ghl_appointment_id)::numeric / count(distinct l.ghl_call_id), 4) end as conversion_llamadas_reuniones
from public.clientes c
left join public.contactos ct on ct.cliente_slug = c.slug
left join public.llamadas l on l.cliente_slug = c.slug
left join public.reuniones r on r.cliente_slug = c.slug
group by c.slug, c.nombre
order by reuniones_validas desc;

-- Mejores paises/industrias/cargos por volumen de oportunidades
select cliente_slug, contacto_empresa, jsonb_array_elements_text(tags) as tag, count(*) as oportunidades
from public.oportunidades
group by cliente_slug, contacto_empresa, jsonb_array_elements_text(tags)
order by oportunidades desc;
