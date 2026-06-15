-- Vista central para tomar decisiones: SDR + cliente + base + llamadas + reuniones + conversion.
select *
from public.vw_performance_sdr_cliente
order by
  riesgo_cliente desc,
  reuniones_validas desc,
  llamadas_semana desc,
  cliente,
  sdr;

-- Casos que requieren accion operativa.
select
  cliente,
  sdr,
  contactos_ghl_asignados,
  contactos_llamados,
  porcentaje_base_llamada,
  llamadas_semana,
  llamadas_totales,
  reuniones_agendadas,
  reuniones_validas,
  conversion_llamada_reunion,
  riesgo_cliente,
  diagnostico_operacional
from public.vw_performance_sdr_cliente
where diagnostico_operacional <> 'con_resultado'
order by cliente, diagnostico_operacional, llamadas_semana desc;

-- Cliente por canal: GHL llamadas/reuniones + Snov correo/base.
select *
from public.vw_performance_cliente_base_canal
order by riesgo_cliente desc, cliente;

-- Ranking de eficiencia SDR por cliente.
select
  cliente,
  sdr,
  llamadas_totales,
  minutos_totales,
  reuniones_agendadas,
  reuniones_validas,
  conversion_llamada_reunion,
  conversion_llamada_reunion_valida,
  tasa_validacion_reuniones,
  diagnostico_operacional
from public.vw_performance_sdr_cliente
order by reuniones_validas desc, conversion_llamada_reunion_valida desc, llamadas_totales desc;

-- Cobertura de base: cuanto de la base GHL asignada fue llamada.
select
  cliente,
  sdr,
  contactos_ghl_asignados,
  contactos_llamados,
  contactos_no_llamados,
  porcentaje_base_llamada,
  llamadas_por_contacto_llamado
from public.vw_performance_sdr_cliente
order by porcentaje_base_llamada asc, contactos_ghl_asignados desc;
