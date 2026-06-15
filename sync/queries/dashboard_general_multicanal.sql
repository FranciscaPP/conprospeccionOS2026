-- KPI superior del dashboard general operacional multicanal.
select *
from public.vw_dashboard_general_multicanal_hoy;

-- Vista por cliente para revisar llamadas, reuniones, correo, cobertura Snov/GHL y riesgo.
select *
from public.vw_dashboard_cliente_multicanal_hoy
order by cliente;

-- Ranking SDR operativo. Snov queda excluido de ranking porque corre bajo Francisca/cuenta central.
select *
from public.vw_dashboard_sdr_operacional_hoy;

-- Calidad de datos para saber donde faltan cargo, industria, pais, telefono o empresa.
select *
from public.vw_calidad_datos_contactos_multicanal
order by contactos_snov_enriquecidos desc;

-- Reuniones de hoy con datos del contacto.
select *
from public.vw_reuniones_del_dia;

-- Campanas Snov monitoreadas.
select
  cliente,
  campaign_name,
  campaign_status,
  emails_sent,
  email_opens,
  email_opens_rate,
  link_clicks,
  email_replies,
  email_replies_rate,
  progress,
  unfinished
from public.vw_snov_campaign_performance
order by cliente, campaign_name;
