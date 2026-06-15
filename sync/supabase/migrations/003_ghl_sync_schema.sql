alter table public.contactos add column if not exists ghl_contact_id text;
alter table public.contactos add column if not exists cliente_slug text references public.clientes(slug) on update cascade on delete set null;
alter table public.contactos add column if not exists location_id text;
alter table public.contactos add column if not exists sdr_slug text references public.sdrs(slug) on update cascade on delete set null;
alter table public.contactos add column if not exists ghl_owner_user_id text;
alter table public.contactos add column if not exists nombre text;
alter table public.contactos add column if not exists nombre_contacto text;
alter table public.contactos add column if not exists nombre_empresa text;
alter table public.contactos add column if not exists email text;
alter table public.contactos add column if not exists telefono text;
alter table public.contactos add column if not exists tipo text;
alter table public.contactos add column if not exists fuente text;
alter table public.contactos add column if not exists pais text;
alter table public.contactos add column if not exists ciudad text;
alter table public.contactos add column if not exists estado_region text;
alter table public.contactos add column if not exists industria text;
alter table public.contactos add column if not exists cargo text;
alter table public.contactos add column if not exists tags jsonb not null default '[]'::jsonb;
alter table public.contactos add column if not exists custom_fields jsonb not null default '[]'::jsonb;
alter table public.contactos add column if not exists raw_data jsonb not null default '{}'::jsonb;
alter table public.contactos add column if not exists ghl_created_at timestamptz;
alter table public.contactos add column if not exists ghl_updated_at timestamptz;
alter table public.contactos add column if not exists synced_at timestamptz not null default now();

create unique index if not exists contactos_ghl_contact_id_uidx
  on public.contactos(ghl_contact_id);

create index if not exists contactos_cliente_slug_idx on public.contactos(cliente_slug);
create index if not exists contactos_sdr_slug_idx on public.contactos(sdr_slug);
create index if not exists contactos_location_id_idx on public.contactos(location_id);

create table if not exists public.oportunidades (
  id uuid primary key default gen_random_uuid(),
  ghl_opportunity_id text not null unique,
  ghl_contact_id text,
  cliente_slug text references public.clientes(slug) on update cascade on delete set null,
  location_id text,
  sdr_slug text references public.sdrs(slug) on update cascade on delete set null,
  ghl_owner_user_id text,
  nombre text,
  valor_monetario numeric,
  pipeline_id text,
  pipeline_stage_id text,
  pipeline_stage_uid text,
  estado text,
  fuente text,
  probabilidad_forecast numeric,
  probabilidad_efectiva numeric,
  contacto_nombre text,
  contacto_empresa text,
  contacto_email text,
  contacto_telefono text,
  tags jsonb not null default '[]'::jsonb,
  custom_fields jsonb not null default '[]'::jsonb,
  raw_data jsonb not null default '{}'::jsonb,
  ghl_created_at timestamptz,
  ghl_updated_at timestamptz,
  last_status_change_at timestamptz,
  last_stage_change_at timestamptz,
  synced_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists oportunidades_cliente_slug_idx on public.oportunidades(cliente_slug);
create index if not exists oportunidades_sdr_slug_idx on public.oportunidades(sdr_slug);
create index if not exists oportunidades_ghl_contact_id_idx on public.oportunidades(ghl_contact_id);
create index if not exists oportunidades_pipeline_stage_id_idx on public.oportunidades(pipeline_stage_id);

create table if not exists public.sync_runs (
  id uuid primary key default gen_random_uuid(),
  source text not null,
  entity text not null,
  status text not null,
  stats jsonb not null default '{}'::jsonb,
  errors jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

drop trigger if exists trg_oportunidades_updated_at on public.oportunidades;
create trigger trg_oportunidades_updated_at
before update on public.oportunidades
for each row execute function public.set_updated_at();
