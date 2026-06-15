-- Quien llamo mas hoy?
select sdr, llamadas_realizadas from public.vw_ranking_sdr_hoy order by llamadas_realizadas desc;

-- Quien agendo mas hoy?
select sdr, reuniones_agendadas from public.vw_ranking_sdr_hoy order by reuniones_agendadas desc;

-- Que clientes estan en riesgo?
select cliente, riesgo, avance_meta from public.vw_clientes_riesgo where riesgo in ('amarillo', 'rojo') order by riesgo desc, avance_meta asc;

-- Que cliente deja mas utilidad estimada?
select cliente, margen_estimado, rentabilidad_estimada from public.vw_financiero_cliente order by margen_estimado desc;

-- Cuantos contactos se cargaron por pais?
select pais, count(*) as contactos from public.contactos group by pais order by contactos desc;

-- Que cliente tuvo mas actividad multicanal hoy?
select
  cliente,
  coalesce(llamadas, 0) as llamadas,
  coalesce(minutos_llamada, 0) as minutos_llamada,
  coalesce(eventos_correo, 0) as eventos_correo,
  coalesce(respuestas_correo, 0) as respuestas_correo,
  coalesce(reuniones_validas, 0) as reuniones_validas
from public.vw_cliente_multicanal_resumen
where fecha = current_date
order by coalesce(llamadas, 0) + coalesce(eventos_correo, 0) desc;

-- Cuantos replies de Snov hay por cliente?
select
  cliente,
  count(*) as replies
from public.vw_snov_prospect_events_enriched
where event_type = 'reply'
group by cliente
order by replies desc;

-- Que contactos existen en GHL y Snov?
select *
from public.vw_contactos_overlap_ghl_snov
order by ultima_aparicion desc;

-- Que clientes tienen mas contactos Snov sin estar en GHL?
select
  cliente,
  prospectos_snov,
  tambien_en_ghl,
  solo_snov,
  emails_unicos
from public.vw_cliente_contactos_por_canal
order by solo_snov desc;

-- Donde faltan cargo o industria?
select
  cliente,
  count(*) as contactos,
  count(*) filter (where cargo is null) as sin_cargo,
  count(*) filter (where industria is null) as sin_industria,
  count(*) filter (where pais is null) as sin_pais
from public.vw_snov_contacts_enriched_with_ghl
group by cliente
order by sin_cargo desc, sin_industria desc;
