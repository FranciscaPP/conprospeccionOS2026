create table if not exists public.ghl_pipeline_stages (
  id uuid primary key default gen_random_uuid(),
  cliente_slug text references public.clientes(slug) on update cascade on delete set null,
  location_id text,
  pipeline_id text not null,
  pipeline_name text,
  stage_id text not null,
  stage_name text not null,
  stage_position numeric,
  stage_probability numeric,
  stage_category text not null default 'otro',
  is_meeting_stage boolean not null default false,
  is_valid_meeting boolean,
  raw_data jsonb not null default '{}'::jsonb,
  synced_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (cliente_slug, pipeline_id, stage_id)
);

alter table public.oportunidades add column if not exists pipeline_name text;
alter table public.oportunidades add column if not exists pipeline_stage_name text;
alter table public.oportunidades add column if not exists stage_category text;
alter table public.oportunidades add column if not exists is_meeting_stage boolean not null default false;
alter table public.oportunidades add column if not exists is_valid_meeting boolean;

alter table public.reuniones add column if not exists origen_reunion text not null default 'ghl_calendar';
alter table public.reuniones add column if not exists opportunity_id text;
alter table public.reuniones add column if not exists fecha_reunion_estimada boolean not null default false;

create index if not exists ghl_pipeline_stages_cliente_idx on public.ghl_pipeline_stages(cliente_slug);
create index if not exists ghl_pipeline_stages_stage_id_idx on public.ghl_pipeline_stages(stage_id);
create index if not exists oportunidades_stage_category_idx on public.oportunidades(stage_category);
create index if not exists reuniones_origen_reunion_idx on public.reuniones(origen_reunion);

drop trigger if exists trg_ghl_pipeline_stages_updated_at on public.ghl_pipeline_stages;
create trigger trg_ghl_pipeline_stages_updated_at
before update on public.ghl_pipeline_stages
for each row execute function public.set_updated_at();
