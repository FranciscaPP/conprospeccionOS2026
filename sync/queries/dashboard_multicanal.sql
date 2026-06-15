-- Resumen diario por cliente combinando GHL llamadas/reuniones y Snov correo.
select *
from public.vw_cliente_multicanal_resumen
order by fecha desc, cliente;

-- Contactos que aparecen tanto en GHL como en Snov por email normalizado.
select *
from public.vw_contactos_overlap_ghl_snov
order by ultima_aparicion desc;

-- Actividad multicanal cruda para filtros por cliente/canal/fecha.
select *
from public.vw_actividad_multicanal_diaria
order by fecha desc, cliente, canal;

-- Performance Snov sin atribuir a SDR, recomendado por ahora.
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

-- Cobertura de datos por cliente combinando Snov + GHL.
select *
from public.vw_cliente_contactos_por_canal
order by prospectos_snov desc;

-- Contactos Snov enriquecidos con datos GHL, utiles para revisar telefono/empresa/pais.
select
  cliente,
  campaign_name,
  nombre_snov,
  email,
  empresa,
  cargo,
  industria,
  pais,
  telefono,
  existe_en_ghl,
  ghl_sdr_slug
from public.vw_snov_contacts_enriched_with_ghl
order by cliente, campaign_name, nombre_snov;

-- Gaps de calidad de datos para completar cargo/industria/pais.
select
  cliente,
  count(*) as contactos,
  count(*) filter (where empresa is null) as sin_empresa,
  count(*) filter (where cargo is null) as sin_cargo,
  count(*) filter (where industria is null) as sin_industria,
  count(*) filter (where pais is null) as sin_pais,
  count(*) filter (where telefono is null) as sin_telefono
from public.vw_snov_contacts_enriched_with_ghl
group by cliente
order by contactos desc;

-- Resumen de respuestas de correo por cliente.
select
  cliente,
  count(*) filter (where event_type = 'sent') as emails_enviados,
  count(*) filter (where event_type = 'open') as aperturas,
  count(*) filter (where event_type = 'reply') as respuestas,
  count(*) filter (where event_type = 'finished') as finalizados
from public.vw_snov_prospect_events_enriched
group by cliente
order by respuestas desc, emails_enviados desc;
