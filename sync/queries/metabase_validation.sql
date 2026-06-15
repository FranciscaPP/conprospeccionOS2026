-- Validaciones post migracion 017.

select 'reuniones_sin_cliente_id' as metrica, count(*) as cantidad from public.reuniones where cliente_id is null
union all
select 'reuniones_sin_sdr_id', count(*) from public.reuniones where sdr_id is null
union all
select 'reuniones_sin_contacto_id', count(*) from public.reuniones where contacto_id is null
union all
select 'llamadas_sin_cliente_id', count(*) from public.llamadas where cliente_id is null
union all
select 'llamadas_sin_sdr_id', count(*) from public.llamadas where sdr_id is null
union all
select 'llamadas_sin_contacto_id', count(*) from public.llamadas where contacto_id is null;

select
  date_trunc('month', fecha_reunion)::date as mes,
  nombre_cliente,
  count(*) filter (where es_valida is true) as reuniones_validas
from public.vw_reuniones_dashboard
group by date_trunc('month', fecha_reunion)::date, nombre_cliente
order by mes desc, reuniones_validas desc;

select
  date_trunc('month', fecha_reunion)::date as mes,
  nombre_sdr,
  count(*) filter (where es_valida is true) as reuniones_validas
from public.vw_reuniones_dashboard
group by date_trunc('month', fecha_reunion)::date, nombre_sdr
order by mes desc, reuniones_validas desc;

select
  fecha_llamada,
  nombre_sdr,
  count(*) as llamadas
from public.vw_llamadas_dashboard
group by fecha_llamada, nombre_sdr
order by fecha_llamada desc, llamadas desc;

select *
from public.vw_clientes_riesgo
where riesgo in ('rojo', 'amarillo')
order by riesgo, cliente;

select
  nombre_sdr,
  nombre_cliente,
  total_llamadas,
  reuniones_agendadas,
  reuniones_validas,
  tasa_llamada_a_reunion,
  tasa_reunion_valida
from public.vw_performance_sdr_diario
where fecha = current_date
order by total_llamadas asc, reuniones_validas asc;

select tipo_alerta, severidad, count(*) as cantidad
from public.vw_alertas_operativas
group by tipo_alerta, severidad
order by severidad, cantidad desc;
