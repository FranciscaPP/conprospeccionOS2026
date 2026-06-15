-- Performance general de campanas Snov.io por cliente y SDR.
select *
from public.vw_snov_campaign_performance
order by periodo_hasta desc nulls last, email_replies desc, emails_sent desc;

-- Actividad diaria de email.
select *
from public.vw_snov_daily_activity
order by fecha desc, cliente_slug, sdr_slug;

-- Ranking SDR por replies de email.
select
  sdr_slug,
  sum(emails_enviados) as emails_enviados,
  sum(aperturas) as aperturas,
  sum(clicks) as clicks,
  sum(respuestas) as respuestas,
  case when sum(emails_enviados) > 0 then round(sum(respuestas)::numeric / sum(emails_enviados), 4) else 0 end as reply_rate_sobre_enviados
from public.vw_snov_daily_activity
where fecha >= current_date - interval '7 days'
group by sdr_slug
order by respuestas desc, reply_rate_sobre_enviados desc;

-- Campanas con baja respuesta o posible problema de deliverability.
select
  snov_campaign_id,
  campaign_name,
  cliente,
  sdr,
  emails_sent,
  email_opens,
  email_opens_rate,
  email_replies,
  email_replies_rate,
  unsubscribed,
  bounced,
  case
    when emails_sent >= 100 and email_opens_rate < 20 then 'riesgo_apertura'
    when emails_sent >= 100 and email_replies_rate < 1 then 'riesgo_respuesta'
    when unsubscribed_rate >= 3 then 'riesgo_unsubscribe'
    else 'ok'
  end as alerta_email
from public.vw_snov_campaign_performance
order by
  case
    when emails_sent >= 100 and email_opens_rate < 20 then 1
    when emails_sent >= 100 and email_replies_rate < 1 then 2
    when unsubscribed_rate >= 3 then 3
    else 4
  end,
  emails_sent desc;

-- Prospectos Snov enriquecidos por GHL.
select
  cliente,
  campaign_name,
  list_name,
  nombre_snov,
  email,
  empresa,
  cargo,
  industria,
  pais,
  telefono,
  existe_en_ghl
from public.vw_snov_contacts_enriched_with_ghl
order by cliente, campaign_name, nombre_snov;

-- Replies de Snov con datos enriquecidos.
select
  occurred_at,
  cliente,
  campaign_name,
  contacto,
  email,
  empresa,
  cargo,
  industria,
  pais,
  subject
from public.vw_snov_prospect_events_enriched
where event_type = 'reply'
order by occurred_at desc;
