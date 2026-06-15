-- GHL owners/users that still need an SDR mapping.
-- Use this after syncing users/calls/opportunities to decide which ghl_user_id belongs to which SDR.

with owner_events as (
  select
    cliente_slug,
    ghl_owner_user_id as ghl_user_id,
    count(*) as llamadas,
    0::bigint as contactos,
    0::bigint as oportunidades,
    0::bigint as reuniones
  from public.llamadas
  where sdr_slug is null
    and ghl_owner_user_id is not null
  group by cliente_slug, ghl_owner_user_id

  union all

  select
    cliente_slug,
    ghl_owner_user_id as ghl_user_id,
    0::bigint,
    count(*),
    0::bigint,
    0::bigint
  from public.contactos
  where sdr_slug is null
    and ghl_owner_user_id is not null
  group by cliente_slug, ghl_owner_user_id

  union all

  select
    cliente_slug,
    ghl_owner_user_id as ghl_user_id,
    0::bigint,
    0::bigint,
    count(*),
    0::bigint
  from public.oportunidades
  where sdr_slug is null
    and ghl_owner_user_id is not null
  group by cliente_slug, ghl_owner_user_id

  union all

  select
    cliente_slug,
    ghl_owner_user_id as ghl_user_id,
    0::bigint,
    0::bigint,
    0::bigint,
    count(*)
  from public.reuniones
  where sdr_slug is null
    and ghl_owner_user_id is not null
  group by cliente_slug, ghl_owner_user_id
),
rollup as (
  select
    cliente_slug,
    ghl_user_id,
    sum(llamadas) as llamadas_sin_sdr,
    sum(contactos) as contactos_sin_sdr,
    sum(oportunidades) as oportunidades_sin_sdr,
    sum(reuniones) as reuniones_sin_sdr
  from owner_events
  group by cliente_slug, ghl_user_id
)
select
  r.cliente_slug,
  c.nombre as cliente,
  r.ghl_user_id,
  gu.nombre as ghl_user_nombre,
  gu.email as ghl_user_email,
  r.llamadas_sin_sdr,
  r.contactos_sin_sdr,
  r.oportunidades_sin_sdr,
  r.reuniones_sin_sdr,
  r.llamadas_sin_sdr + r.contactos_sin_sdr + r.oportunidades_sin_sdr + r.reuniones_sin_sdr as eventos_sin_sdr
from rollup r
left join public.clientes c on c.slug = r.cliente_slug
left join public.ghl_users gu
  on gu.cliente_slug = r.cliente_slug
 and gu.ghl_user_id = r.ghl_user_id
where coalesce(gu.excluir_metricas_sdr, false) is false
order by eventos_sin_sdr desc, r.cliente_slug, gu.nombre;
