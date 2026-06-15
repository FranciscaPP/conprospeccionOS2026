create or replace view public.vw_performance_sdr_cliente as
with asignaciones as (
  select
    sc.cliente_slug,
    c.nombre as cliente,
    c.estado_contrato,
    c.pais_prospeccion,
    sc.sdr_slug,
    s.nombre as sdr,
    sc.ghl_user_id,
    sc.location_id,
    sc.estado_asignacion,
    sc.activo as asignacion_activa
  from public.sdr_cliente sc
  join public.clientes c on c.slug = sc.cliente_slug
  join public.sdrs s on s.slug = sc.sdr_slug
  where coalesce(sc.activo, true) is true
),
base_ghl as (
  select
    cliente_slug,
    sdr_slug,
    count(*) as contactos_ghl_asignados,
    count(distinct lower(nullif(trim(email), ''))) filter (where email is not null) as emails_ghl_unicos,
    count(*) filter (where telefono is not null) as contactos_con_telefono,
    count(*) filter (where cargo is not null) as contactos_con_cargo,
    count(*) filter (where industria is not null) as contactos_con_industria,
    count(*) filter (where pais is not null) as contactos_con_pais,
    count(*) filter (where ghl_created_at::date = current_date) as contactos_ghl_cargados_hoy,
    count(*) filter (where ghl_created_at::date >= date_trunc('week', current_date)::date) as contactos_ghl_cargados_semana
  from public.contactos
  group by cliente_slug, sdr_slug
),
llamadas as (
  select
    cliente_slug,
    sdr_slug,
    count(*) as llamadas_totales,
    count(*) filter (where fecha = current_date) as llamadas_hoy,
    count(*) filter (where fecha >= date_trunc('week', current_date)::date) as llamadas_semana,
    coalesce(round(sum(duracion_minutos), 2), 0) as minutos_totales,
    coalesce(round(sum(duracion_minutos) filter (where fecha = current_date), 2), 0) as minutos_hoy,
    coalesce(round(sum(duracion_minutos) filter (where fecha >= date_trunc('week', current_date)::date), 2), 0) as minutos_semana,
    count(distinct coalesce(nullif(ghl_contact_id, ''), nullif(regexp_replace(coalesce(telefono, ''), '\D', '', 'g'), ''))) as contactos_llamados,
    count(distinct coalesce(nullif(ghl_contact_id, ''), nullif(regexp_replace(coalesce(telefono, ''), '\D', '', 'g'), ''))) filter (where fecha >= date_trunc('week', current_date)::date) as contactos_llamados_semana
  from public.llamadas
  where sdr_slug is not null
  group by cliente_slug, sdr_slug
),
reuniones as (
  select
    cliente_slug,
    sdr_slug,
    count(*) as reuniones_agendadas,
    count(*) filter (where fecha_reunion = current_date) as reuniones_hoy,
    count(*) filter (where fecha_reunion >= date_trunc('week', current_date)::date) as reuniones_semana,
    count(*) filter (where es_valida is true) as reuniones_validas,
    count(*) filter (where es_valida is true and fecha_reunion >= date_trunc('week', current_date)::date) as reuniones_validas_semana,
    count(*) filter (where es_valida is false) as reuniones_no_validas,
    count(*) filter (where es_valida is null) as reuniones_pendientes_validacion
  from public.reuniones
  where sdr_slug is not null
  group by cliente_slug, sdr_slug
),
oportunidades as (
  select
    cliente_slug,
    sdr_slug,
    count(*) as oportunidades_totales,
    count(*) filter (where ghl_created_at::date >= date_trunc('week', current_date)::date) as oportunidades_semana,
    count(*) filter (where is_meeting_stage is true) as oportunidades_en_stage_reunion,
    count(*) filter (where is_valid_meeting is true) as oportunidades_reunion_valida
  from public.oportunidades
  where sdr_slug is not null
  group by cliente_slug, sdr_slug
),
metas as (
  select
    cliente_slug,
    max(reuniones_validas_meta) filter (where periodo = 'contrato') as meta_reuniones_validas_contrato,
    max(reuniones_validas_actuales) filter (where periodo = 'contrato') as reuniones_validas_iniciales
  from public.cliente_metas
  group by cliente_slug
),
snov_cliente as (
  select
    cliente_slug,
    prospectos_snov,
    tambien_en_ghl as prospectos_snov_tambien_en_ghl,
    solo_snov as prospectos_solo_snov
  from public.vw_cliente_contactos_por_canal
)
select
  a.cliente_slug,
  a.cliente,
  a.estado_contrato,
  a.pais_prospeccion,
  a.sdr_slug,
  a.sdr,
  a.ghl_user_id,
  a.location_id,
  a.estado_asignacion,
  coalesce(b.contactos_ghl_asignados, 0) as contactos_ghl_asignados,
  coalesce(b.emails_ghl_unicos, 0) as emails_ghl_unicos,
  coalesce(b.contactos_con_telefono, 0) as contactos_con_telefono,
  coalesce(b.contactos_con_cargo, 0) as contactos_con_cargo,
  coalesce(b.contactos_con_industria, 0) as contactos_con_industria,
  coalesce(b.contactos_con_pais, 0) as contactos_con_pais,
  coalesce(b.contactos_ghl_cargados_hoy, 0) as contactos_ghl_cargados_hoy,
  coalesce(b.contactos_ghl_cargados_semana, 0) as contactos_ghl_cargados_semana,
  coalesce(l.contactos_llamados, 0) as contactos_llamados,
  greatest(coalesce(b.contactos_ghl_asignados, 0) - coalesce(l.contactos_llamados, 0), 0) as contactos_no_llamados,
  case
    when coalesce(b.contactos_ghl_asignados, 0) = 0 then 0
    else round(coalesce(l.contactos_llamados, 0)::numeric / nullif(b.contactos_ghl_asignados, 0), 4)
  end as porcentaje_base_llamada,
  coalesce(l.llamadas_totales, 0) as llamadas_totales,
  coalesce(l.llamadas_hoy, 0) as llamadas_hoy,
  coalesce(l.llamadas_semana, 0) as llamadas_semana,
  coalesce(l.minutos_totales, 0) as minutos_totales,
  coalesce(l.minutos_hoy, 0) as minutos_hoy,
  coalesce(l.minutos_semana, 0) as minutos_semana,
  case
    when coalesce(l.contactos_llamados, 0) = 0 then 0
    else round(coalesce(l.llamadas_totales, 0)::numeric / nullif(l.contactos_llamados, 0), 2)
  end as llamadas_por_contacto_llamado,
  coalesce(r.reuniones_agendadas, 0) as reuniones_agendadas,
  coalesce(r.reuniones_hoy, 0) as reuniones_hoy,
  coalesce(r.reuniones_semana, 0) as reuniones_semana,
  coalesce(r.reuniones_validas, 0) as reuniones_validas,
  coalesce(r.reuniones_validas_semana, 0) as reuniones_validas_semana,
  coalesce(r.reuniones_no_validas, 0) as reuniones_no_validas,
  coalesce(r.reuniones_pendientes_validacion, 0) as reuniones_pendientes_validacion,
  coalesce(o.oportunidades_totales, 0) as oportunidades_totales,
  coalesce(o.oportunidades_semana, 0) as oportunidades_semana,
  coalesce(o.oportunidades_en_stage_reunion, 0) as oportunidades_en_stage_reunion,
  coalesce(o.oportunidades_reunion_valida, 0) as oportunidades_reunion_valida,
  case
    when coalesce(b.contactos_ghl_asignados, 0) = 0 then 0
    else round(coalesce(r.reuniones_agendadas, 0)::numeric / nullif(b.contactos_ghl_asignados, 0), 4)
  end as conversion_contacto_reunion,
  case
    when coalesce(b.contactos_ghl_asignados, 0) = 0 then 0
    else round(coalesce(r.reuniones_validas, 0)::numeric / nullif(b.contactos_ghl_asignados, 0), 4)
  end as conversion_contacto_reunion_valida,
  case
    when coalesce(l.llamadas_totales, 0) = 0 then 0
    else round(coalesce(r.reuniones_agendadas, 0)::numeric / nullif(l.llamadas_totales, 0), 4)
  end as conversion_llamada_reunion,
  case
    when coalesce(l.llamadas_totales, 0) = 0 then 0
    else round(coalesce(r.reuniones_validas, 0)::numeric / nullif(l.llamadas_totales, 0), 4)
  end as conversion_llamada_reunion_valida,
  case
    when coalesce(r.reuniones_agendadas, 0) = 0 then 0
    else round(coalesce(r.reuniones_validas, 0)::numeric / nullif(r.reuniones_agendadas, 0), 4)
  end as tasa_validacion_reuniones,
  coalesce(m.meta_reuniones_validas_contrato, 0) as meta_reuniones_validas_contrato,
  coalesce(m.reuniones_validas_iniciales, 0) as reuniones_validas_iniciales_cliente,
  coalesce(vr.avance_meta, 0) as avance_meta_cliente,
  coalesce(vr.riesgo, 'sin_datos') as riesgo_cliente,
  coalesce(sn.prospectos_snov, 0) as prospectos_snov_cliente,
  coalesce(sn.prospectos_snov_tambien_en_ghl, 0) as prospectos_snov_tambien_en_ghl,
  coalesce(sn.prospectos_solo_snov, 0) as prospectos_solo_snov,
  case
    when a.estado_contrato in ('setup', 'pausado', 'finalizado', 'terminado') then 'cliente_no_evaluable_operacion_activa'
    when coalesce(b.contactos_ghl_asignados, 0) = 0 and coalesce(sn.prospectos_snov, 0) > 0 then 'falta_traspasar_base_snov_a_ghl_o_asignar_owner'
    when coalesce(b.contactos_ghl_asignados, 0) = 0 then 'sin_base_ghl_asignada'
    when coalesce(l.llamadas_semana, 0) = 0 then 'baja_actividad_sin_llamadas_semana'
    when coalesce(l.llamadas_totales, 0) >= 100 and coalesce(r.reuniones_agendadas, 0) = 0 then 'llama_mucho_y_no_agenda'
    when coalesce(r.reuniones_agendadas, 0) >= 3 and coalesce(r.reuniones_validas, 0) = 0 then 'agenda_pero_no_valida'
    when coalesce(vr.riesgo, 'sin_datos') = 'rojo' and coalesce(l.llamadas_semana, 0) < 50 then 'cliente_en_riesgo_y_baja_actividad'
    when coalesce(l.llamadas_totales, 0) > 0 and coalesce(r.reuniones_validas, 0) > 0 then 'con_resultado'
    else 'monitorear'
  end as diagnostico_operacional
from asignaciones a
left join base_ghl b on b.cliente_slug = a.cliente_slug and b.sdr_slug = a.sdr_slug
left join llamadas l on l.cliente_slug = a.cliente_slug and l.sdr_slug = a.sdr_slug
left join reuniones r on r.cliente_slug = a.cliente_slug and r.sdr_slug = a.sdr_slug
left join oportunidades o on o.cliente_slug = a.cliente_slug and o.sdr_slug = a.sdr_slug
left join metas m on m.cliente_slug = a.cliente_slug
left join public.vw_clientes_riesgo vr on vr.cliente_slug = a.cliente_slug
left join snov_cliente sn on sn.cliente_slug = a.cliente_slug;

create or replace view public.vw_performance_cliente_base_canal as
select
  c.slug as cliente_slug,
  c.nombre as cliente,
  c.estado_contrato,
  coalesce(vr.riesgo, 'sin_datos') as riesgo_cliente,
  coalesce(ghl.contactos_ghl_total, 0) as contactos_ghl_total,
  coalesce(ghl.contactos_ghl_con_owner, 0) as contactos_ghl_con_owner,
  coalesce(ghl.contactos_ghl_sin_owner, 0) as contactos_ghl_sin_owner,
  coalesce(sn.prospectos_snov, 0) as prospectos_snov_total,
  coalesce(sn.tambien_en_ghl, 0) as prospectos_snov_tambien_en_ghl,
  coalesce(sn.solo_snov, 0) as prospectos_solo_snov,
  coalesce(ll.contactos_llamados_total, 0) as contactos_llamados_total,
  coalesce(ll.llamadas_totales, 0) as llamadas_totales,
  coalesce(ll.minutos_totales, 0) as minutos_totales,
  coalesce(rr.reuniones_agendadas, 0) as reuniones_agendadas,
  coalesce(rr.reuniones_validas, 0) as reuniones_validas,
  coalesce(mail.emails_enviados, 0) as emails_enviados,
  coalesce(mail.respuestas_email, 0) as respuestas_email,
  case
    when coalesce(ghl.contactos_ghl_total, 0) = 0 then 0
    else round(coalesce(ll.contactos_llamados_total, 0)::numeric / nullif(ghl.contactos_ghl_total, 0), 4)
  end as cobertura_llamadas_base_ghl,
  case
    when coalesce(ll.llamadas_totales, 0) = 0 then 0
    else round(coalesce(rr.reuniones_agendadas, 0)::numeric / nullif(ll.llamadas_totales, 0), 4)
  end as conversion_llamada_reunion,
  case
    when coalesce(mail.emails_enviados, 0) = 0 then 0
    else round(coalesce(mail.respuestas_email, 0)::numeric / nullif(mail.emails_enviados, 0), 4)
  end as conversion_email_respuesta,
  case
    when coalesce(ghl.contactos_ghl_sin_owner, 0) > 0 then 'hay_contactos_ghl_sin_owner'
    when coalesce(sn.solo_snov, 0) > coalesce(sn.tambien_en_ghl, 0) then 'mucha_base_solo_snov'
    when coalesce(vr.riesgo, 'sin_datos') = 'rojo' and coalesce(ll.llamadas_totales, 0) = 0 then 'riesgo_sin_llamadas'
    when coalesce(vr.riesgo, 'sin_datos') = 'rojo' then 'riesgo_revisar_operacion'
    else 'ok'
  end as alerta_base_canal
from public.clientes c
left join public.vw_clientes_riesgo vr on vr.cliente_slug = c.slug
left join (
  select
    cliente_slug,
    count(*) as contactos_ghl_total,
    count(*) filter (where sdr_slug is not null) as contactos_ghl_con_owner,
    count(*) filter (where sdr_slug is null) as contactos_ghl_sin_owner
  from public.contactos
  group by cliente_slug
) ghl on ghl.cliente_slug = c.slug
left join public.vw_cliente_contactos_por_canal sn on sn.cliente_slug = c.slug
left join (
  select
    cliente_slug,
    count(distinct coalesce(nullif(ghl_contact_id, ''), nullif(regexp_replace(coalesce(telefono, ''), '\D', '', 'g'), ''))) as contactos_llamados_total,
    count(*) as llamadas_totales,
    coalesce(round(sum(duracion_minutos), 2), 0) as minutos_totales
  from public.llamadas
  group by cliente_slug
) ll on ll.cliente_slug = c.slug
left join (
  select
    cliente_slug,
    count(*) as reuniones_agendadas,
    count(*) filter (where es_valida is true) as reuniones_validas
  from public.reuniones
  group by cliente_slug
) rr on rr.cliente_slug = c.slug
left join (
  select
    cliente_slug,
    count(*) filter (where event_type = 'sent') as emails_enviados,
    count(*) filter (where event_type = 'reply') as respuestas_email
  from public.snov_email_events
  group by cliente_slug
) mail on mail.cliente_slug = c.slug;
