alter table public.ghl_users add column if not exists es_sdr boolean not null default false;
alter table public.ghl_users add column if not exists excluir_metricas_sdr boolean not null default false;
alter table public.ghl_users add column if not exists tipo_usuario text;
alter table public.ghl_users add column if not exists notas text;

update public.ghl_users gu
set
  es_sdr = true,
  excluir_metricas_sdr = false,
  tipo_usuario = coalesce(tipo_usuario, 'sdr')
where gu.sdr_slug is not null;

update public.ghl_users gu
set
  es_sdr = false,
  excluir_metricas_sdr = true,
  tipo_usuario = coalesce(tipo_usuario, 'cliente_admin'),
  notas = trim(both from concat_ws(E'\n', gu.notas, 'Usuario GHL confirmado como no SDR operativo; excluir de rankings SDR.'))
where (gu.cliente_slug, gu.ghl_user_id) in (
  ('tiresias', 't9oNZAjcxYUEQyHbvO4F'),
  ('clickie', 'uBgTz8nvKahVxmlhhnkN'),
  ('clickie', 'WqRac9hJvjw4Ldn5gZhL'),
  ('tiresias', 'utcoTwq4sWvbaEEuCAl1'),
  ('tiresias', 'uBgTz8nvKahVxmlhhnkN'),
  ('ecosmart', 'uBgTz8nvKahVxmlhhnkN'),
  ('just4u', 'uBgTz8nvKahVxmlhhnkN'),
  ('clickie', '84ZbfdtuDMxHJPk1RmNr'),
  ('just4u', 'yxvQveqBTQgZb25OrxMz'),
  ('ecosmart', 'a9xqz1FRYjG4H9p7Ee0R'),
  ('tiresias', 'bo4X0u6SlO14hSgzAKDi'),
  ('ecosmart', 'tkNwsMUn2swe96T35zM3'),
  ('clickie', 'e2elwBuj6rxUtSsZQeL1'),
  ('just4u', 'AY8YeyOgilsxEzUegbiF'),
  ('clickie', 'utcoTwq4sWvbaEEuCAl1')
);

create or replace view public.vw_actividad_ghl_no_sdr as
with eventos as (
  select
    'llamada' as tipo_evento,
    cliente_slug,
    ghl_owner_user_id as ghl_user_id,
    fecha as fecha_evento,
    sdr_slug
  from public.llamadas
  where ghl_owner_user_id is not null

  union all

  select
    'contacto',
    cliente_slug,
    ghl_owner_user_id,
    ghl_created_at::date,
    sdr_slug
  from public.contactos
  where ghl_owner_user_id is not null

  union all

  select
    'oportunidad',
    cliente_slug,
    ghl_owner_user_id,
    ghl_created_at::date,
    sdr_slug
  from public.oportunidades
  where ghl_owner_user_id is not null

  union all

  select
    'reunion',
    cliente_slug,
    ghl_owner_user_id,
    fecha_reunion,
    sdr_slug
  from public.reuniones
  where ghl_owner_user_id is not null
)
select
  e.cliente_slug,
  c.nombre as cliente,
  e.ghl_user_id,
  gu.nombre as ghl_user_nombre,
  gu.email as ghl_user_email,
  gu.tipo_usuario,
  gu.excluir_metricas_sdr,
  e.tipo_evento,
  count(*) as eventos
from eventos e
left join public.clientes c on c.slug = e.cliente_slug
left join public.ghl_users gu
  on gu.cliente_slug = e.cliente_slug
 and gu.ghl_user_id = e.ghl_user_id
where e.sdr_slug is null
group by
  e.cliente_slug,
  c.nombre,
  e.ghl_user_id,
  gu.nombre,
  gu.email,
  gu.tipo_usuario,
  gu.excluir_metricas_sdr,
  e.tipo_evento;
