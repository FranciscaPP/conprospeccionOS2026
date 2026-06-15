-- KPIs superiores del dia
select * from public.vw_operacional_hoy;

-- Tabla reuniones del dia
select * from public.vw_reuniones_del_dia;

-- Pipeline general por estado
select
  estado,
  count(*) as oportunidades
from public.oportunidades
group by estado
order by oportunidades desc;

-- Contactos cargados por cliente/pais/industria/cargo
select
  cliente_slug,
  pais,
  industria,
  cargo,
  count(*) as contactos
from public.contactos
group by cliente_slug, pais, industria, cargo
order by contactos desc;
