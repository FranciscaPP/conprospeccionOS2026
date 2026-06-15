-- Rentabilidad estimada por cliente
select * from public.vw_financiero_cliente order by margen_estimado desc;

-- Costo herramientas
select
  coalesce(cliente_slug, 'general') as cliente_slug,
  herramienta,
  costo_mensual,
  moneda,
  tipo_costo
from public.costos_herramientas
order by cliente_slug, herramienta;

-- Pagos SDR configurados
select
  p.sdr_slug,
  s.nombre as sdr,
  p.cliente_slug,
  c.nombre as cliente,
  p.base_mensual,
  p.variable_reunion_valida,
  p.bono_semanal,
  p.bono_mensual,
  p.condicion_bono
from public.pagos_sdr p
left join public.sdrs s on s.slug = p.sdr_slug
left join public.clientes c on c.slug = p.cliente_slug
where p.activo is true;
