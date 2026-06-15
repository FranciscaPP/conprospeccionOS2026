create table if not exists public.snov_prospects (
  id uuid primary key default gen_random_uuid(),
  snov_prospect_id text not null unique,
  cliente_slug text references public.clientes(slug) on update cascade on delete set null,
  sdr_slug text references public.sdrs(slug) on update cascade on delete set null,
  snov_campaign_id text references public.snov_campaigns(snov_campaign_id) on update cascade on delete set null,
  list_id text,
  list_name text,
  nombre text,
  first_name text,
  last_name text,
  email text,
  email_status text,
  empresa text,
  cargo text,
  industria text,
  pais text,
  localidad text,
  linkedin_url text,
  status text,
  raw_data jsonb not null default '{}'::jsonb,
  synced_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists snov_prospects_email_idx on public.snov_prospects(lower(email));
create index if not exists snov_prospects_cliente_idx on public.snov_prospects(cliente_slug);
create index if not exists snov_prospects_campaign_idx on public.snov_prospects(snov_campaign_id);
create index if not exists snov_prospects_list_idx on public.snov_prospects(list_id);
create index if not exists snov_prospects_industria_idx on public.snov_prospects(industria);
create index if not exists snov_prospects_cargo_idx on public.snov_prospects(cargo);
create index if not exists snov_prospects_pais_idx on public.snov_prospects(pais);

create or replace view public.vw_snov_prospects_enriched as
select
  sp.cliente_slug,
  cl.nombre as cliente,
  sp.sdr_slug,
  s.nombre as sdr,
  sp.snov_campaign_id,
  sc.nombre as campaign_name,
  sp.list_id,
  sp.list_name,
  sp.snov_prospect_id,
  sp.nombre,
  sp.email,
  sp.empresa,
  sp.cargo,
  sp.industria,
  sp.pais,
  sp.localidad,
  sp.linkedin_url,
  sp.status,
  sp.synced_at
from public.snov_prospects sp
left join public.clientes cl on cl.slug = sp.cliente_slug
left join public.sdrs s on s.slug = sp.sdr_slug
left join public.snov_campaigns sc on sc.snov_campaign_id = sp.snov_campaign_id;

create or replace view public.vw_snov_prospect_events_enriched as
select
  e.snov_event_id,
  e.event_type,
  e.occurred_at,
  coalesce(e.cliente_slug, sp.cliente_slug) as cliente_slug,
  cl.nombre as cliente,
  coalesce(e.sdr_slug, sp.sdr_slug) as sdr_slug,
  s.nombre as sdr,
  e.snov_campaign_id,
  sc.nombre as campaign_name,
  coalesce(e.prospect_id, sp.snov_prospect_id) as snov_prospect_id,
  coalesce(e.prospect_email, sp.email) as email,
  coalesce(e.prospect_name, sp.nombre) as contacto,
  coalesce(e.company, sp.empresa) as empresa,
  coalesce(e.cargo, sp.cargo) as cargo,
  coalesce(e.industria, sp.industria) as industria,
  coalesce(e.pais, sp.pais) as pais,
  sp.localidad,
  sp.linkedin_url,
  e.subject
from public.snov_email_events e
left join public.snov_prospects sp
  on sp.snov_prospect_id = e.prospect_id
  or lower(sp.email) = lower(e.prospect_email)
left join public.clientes cl on cl.slug = coalesce(e.cliente_slug, sp.cliente_slug)
left join public.sdrs s on s.slug = coalesce(e.sdr_slug, sp.sdr_slug)
left join public.snov_campaigns sc on sc.snov_campaign_id = e.snov_campaign_id;

drop trigger if exists trg_snov_prospects_updated_at on public.snov_prospects;
create trigger trg_snov_prospects_updated_at
before update on public.snov_prospects
for each row execute function public.set_updated_at();
