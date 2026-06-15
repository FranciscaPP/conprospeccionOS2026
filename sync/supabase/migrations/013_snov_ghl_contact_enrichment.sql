create or replace view public.vw_snov_contacts_enriched_with_ghl as
select
  sp.cliente_slug,
  cl.nombre as cliente,
  sp.snov_campaign_id,
  sc.nombre as campaign_name,
  sp.list_id,
  sp.list_name,
  sp.snov_prospect_id,
  sp.nombre as nombre_snov,
  sp.email,
  c.ghl_contact_id,
  coalesce(sp.empresa, c.nombre_empresa) as empresa,
  coalesce(sp.cargo, c.cargo) as cargo,
  coalesce(sp.industria, c.industria) as industria,
  coalesce(sp.pais, c.pais) as pais,
  coalesce(sp.localidad, c.ciudad) as localidad,
  c.telefono,
  c.sdr_slug as ghl_sdr_slug,
  sp.sdr_slug as snov_sdr_slug,
  case when c.ghl_contact_id is not null then true else false end as existe_en_ghl,
  sp.linkedin_url,
  sp.synced_at as snov_synced_at,
  c.synced_at as ghl_synced_at
from public.snov_prospects sp
left join public.clientes cl on cl.slug = sp.cliente_slug
left join public.snov_campaigns sc on sc.snov_campaign_id = sp.snov_campaign_id
left join public.contactos c
  on c.cliente_slug = sp.cliente_slug
 and lower(nullif(trim(c.email), '')) = lower(nullif(trim(sp.email), ''));

create or replace view public.vw_cliente_contactos_por_canal as
select
  sp.cliente_slug,
  cl.nombre as cliente,
  count(*) as prospectos_snov,
  count(*) filter (
    where exists (
      select 1
      from public.contactos c
      where c.cliente_slug = sp.cliente_slug
        and lower(nullif(trim(c.email), '')) = lower(nullif(trim(sp.email), ''))
    )
  ) as tambien_en_ghl,
  count(*) filter (
    where not exists (
      select 1
      from public.contactos c
      where c.cliente_slug = sp.cliente_slug
        and lower(nullif(trim(c.email), '')) = lower(nullif(trim(sp.email), ''))
    )
  ) as solo_snov,
  count(*) filter (where sp.cargo is not null) as con_cargo_snov,
  count(*) filter (where sp.industria is not null) as con_industria_snov,
  count(*) filter (where sp.pais is not null) as con_pais_snov,
  count(distinct lower(sp.email)) as emails_unicos
from public.snov_prospects sp
left join public.clientes cl on cl.slug = sp.cliente_slug
group by sp.cliente_slug, cl.nombre;
