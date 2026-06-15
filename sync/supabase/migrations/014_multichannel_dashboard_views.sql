create or replace view public.vw_dashboard_general_multicanal_hoy as
select
  current_date as fecha,
  (select count(*) from public.reuniones where fecha_reunion = current_date) as reuniones_dia,
  (select count(*) from public.reuniones where date_trunc('week', fecha_reunion)::date = date_trunc('week', current_date)::date) as reuniones_semana,
  (select count(*) from public.reuniones where fecha_reunion = current_date and es_valida is true) as reuniones_validas_dia,
  (select count(*) from public.reuniones where fecha_reunion = current_date and es_valida is null) as reuniones_pendientes_validacion,
  (select count(*) from public.llamadas where fecha = current_date) as llamadas_dia,
  (select coalesce(round(sum(duracion_minutos), 2), 0) from public.llamadas where fecha = current_date) as minutos_hablados_dia,
  (select count(*) from public.contactos where ghl_created_at::date = current_date) as contactos_ghl_cargados_dia,
  (select count(*) from public.snov_email_events where occurred_at::date = current_date and event_type = 'sent') as emails_enviados_dia,
  (select count(*) from public.snov_email_events where occurred_at::date = current_date and event_type = 'open') as aperturas_email_dia,
  (select count(*) from public.snov_email_events where occurred_at::date = current_date and event_type = 'reply') as respuestas_email_dia,
  (select count(*) from public.snov_email_events where occurred_at::date >= date_trunc('week', current_date)::date and event_type = 'sent') as emails_enviados_semana,
  (select count(*) from public.snov_email_events where occurred_at::date >= date_trunc('week', current_date)::date and event_type = 'reply') as respuestas_email_semana,
  (select count(*) from public.vw_clientes_riesgo where riesgo = 'rojo') as clientes_en_riesgo,
  (select count(*) from public.sdrs s where s.estado = 'activo' and not exists (
    select 1 from public.llamadas l where l.sdr_slug = s.slug and l.fecha = current_date
  )) as sdrs_sin_llamadas_hoy,
  (select count(*) from public.snov_campaigns where status in ('active', 'paused')) as campanas_snov_monitoreadas,
  (select coalesce(sum(prospectos_snov), 0) from public.vw_cliente_contactos_por_canal) as prospectos_snov_total,
  (select coalesce(sum(tambien_en_ghl), 0) from public.vw_cliente_contactos_por_canal) as prospectos_snov_tambien_en_ghl,
  (select coalesce(sum(solo_snov), 0) from public.vw_cliente_contactos_por_canal) as prospectos_solo_snov;

create or replace view public.vw_dashboard_cliente_multicanal_hoy as
select
  c.slug as cliente_slug,
  c.nombre as cliente,
  c.estado_contrato,
  coalesce(riesgo.riesgo, 'sin_datos') as riesgo_contrato,
  coalesce(llamadas.llamadas_dia, 0) as llamadas_dia,
  coalesce(llamadas.minutos_dia, 0) as minutos_hablados_dia,
  coalesce(reuniones.reuniones_dia, 0) as reuniones_dia,
  coalesce(reuniones.reuniones_validas_dia, 0) as reuniones_validas_dia,
  coalesce(reuniones.reuniones_pendientes_dia, 0) as reuniones_pendientes_dia,
  coalesce(correos.emails_enviados_dia, 0) as emails_enviados_dia,
  coalesce(correos.aperturas_dia, 0) as aperturas_email_dia,
  coalesce(correos.respuestas_dia, 0) as respuestas_email_dia,
  coalesce(correos.emails_enviados_semana, 0) as emails_enviados_semana,
  coalesce(correos.respuestas_semana, 0) as respuestas_email_semana,
  coalesce(contactos.contactos_ghl_total, 0) as contactos_ghl_total,
  coalesce(snov.prospectos_snov, 0) as prospectos_snov,
  coalesce(snov.tambien_en_ghl, 0) as prospectos_snov_tambien_en_ghl,
  coalesce(snov.solo_snov, 0) as prospectos_solo_snov,
  case
    when coalesce(correos.emails_enviados_semana, 0) = 0 then 0
    else round(correos.respuestas_semana::numeric / nullif(correos.emails_enviados_semana, 0), 4)
  end as conversion_email_respuesta_semana,
  case
    when coalesce(llamadas.llamadas_dia, 0) = 0 then 0
    else round(reuniones.reuniones_dia::numeric / nullif(llamadas.llamadas_dia, 0), 4)
  end as conversion_llamadas_reuniones_dia
from public.clientes c
left join public.vw_clientes_riesgo riesgo on riesgo.cliente_slug = c.slug
left join (
  select
    cliente_slug,
    count(*) as llamadas_dia,
    coalesce(round(sum(duracion_minutos), 2), 0) as minutos_dia
  from public.llamadas
  where fecha = current_date
  group by cliente_slug
) llamadas on llamadas.cliente_slug = c.slug
left join (
  select
    cliente_slug,
    count(*) as reuniones_dia,
    count(*) filter (where es_valida is true) as reuniones_validas_dia,
    count(*) filter (where es_valida is null) as reuniones_pendientes_dia
  from public.reuniones
  where fecha_reunion = current_date
  group by cliente_slug
) reuniones on reuniones.cliente_slug = c.slug
left join (
  select
    cliente_slug,
    count(*) filter (where occurred_at::date = current_date and event_type = 'sent') as emails_enviados_dia,
    count(*) filter (where occurred_at::date = current_date and event_type = 'open') as aperturas_dia,
    count(*) filter (where occurred_at::date = current_date and event_type = 'reply') as respuestas_dia,
    count(*) filter (where occurred_at::date >= date_trunc('week', current_date)::date and event_type = 'sent') as emails_enviados_semana,
    count(*) filter (where occurred_at::date >= date_trunc('week', current_date)::date and event_type = 'reply') as respuestas_semana
  from public.snov_email_events
  where occurred_at is not null
  group by cliente_slug
) correos on correos.cliente_slug = c.slug
left join (
  select cliente_slug, count(*) as contactos_ghl_total
  from public.contactos
  group by cliente_slug
) contactos on contactos.cliente_slug = c.slug
left join public.vw_cliente_contactos_por_canal snov on snov.cliente_slug = c.slug
where c.estado_contrato not in ('finalizado')
order by c.nombre;

create or replace view public.vw_dashboard_sdr_operacional_hoy as
select
  s.slug as sdr_slug,
  s.nombre as sdr,
  coalesce(l.llamadas_dia, 0) as llamadas_dia,
  coalesce(l.minutos_dia, 0) as minutos_hablados_dia,
  coalesce(r.reuniones_dia, 0) as reuniones_dia,
  coalesce(r.reuniones_validas_dia, 0) as reuniones_validas_dia,
  coalesce(r.reuniones_no_validas_dia, 0) as reuniones_no_validas_dia,
  coalesce(ct.contactos_ghl_dia, 0) as contactos_ghl_cargados_dia,
  case
    when coalesce(l.llamadas_dia, 0) = 0 then 0
    else round(r.reuniones_dia::numeric / nullif(l.llamadas_dia, 0), 4)
  end as conversion_llamadas_reuniones_dia,
  case
    when coalesce(r.reuniones_dia, 0) = 0 then 0
    else round(r.reuniones_validas_dia::numeric / nullif(r.reuniones_dia, 0), 4)
  end as tasa_validacion_dia,
  'Snov se excluye de ranking SDR porque opera bajo Francisca/cuenta central' as nota_snov
from public.sdrs s
left join (
  select sdr_slug, count(*) as llamadas_dia, coalesce(round(sum(duracion_minutos), 2), 0) as minutos_dia
  from public.llamadas
  where fecha = current_date
  group by sdr_slug
) l on l.sdr_slug = s.slug
left join (
  select
    sdr_slug,
    count(*) as reuniones_dia,
    count(*) filter (where es_valida is true) as reuniones_validas_dia,
    count(*) filter (where es_valida is false) as reuniones_no_validas_dia
  from public.reuniones
  where fecha_reunion = current_date
  group by sdr_slug
) r on r.sdr_slug = s.slug
left join (
  select sdr_slug, count(*) as contactos_ghl_dia
  from public.contactos
  where ghl_created_at::date = current_date
  group by sdr_slug
) ct on ct.sdr_slug = s.slug
where s.estado = 'activo'
order by reuniones_validas_dia desc, reuniones_dia desc, llamadas_dia desc;

create or replace view public.vw_calidad_datos_contactos_multicanal as
select
  cliente_slug,
  cliente,
  count(*) as contactos_snov_enriquecidos,
  count(*) filter (where existe_en_ghl is true) as tambien_en_ghl,
  count(*) filter (where empresa is not null) as con_empresa,
  count(*) filter (where cargo is not null) as con_cargo,
  count(*) filter (where industria is not null) as con_industria,
  count(*) filter (where pais is not null) as con_pais,
  count(*) filter (where telefono is not null) as con_telefono,
  count(*) filter (where empresa is null) as sin_empresa,
  count(*) filter (where cargo is null) as sin_cargo,
  count(*) filter (where industria is null) as sin_industria,
  count(*) filter (where pais is null) as sin_pais,
  count(*) filter (where telefono is null) as sin_telefono
from public.vw_snov_contacts_enriched_with_ghl
group by cliente_slug, cliente;
