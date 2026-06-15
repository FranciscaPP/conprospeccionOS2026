-- 006 - Client Setup OS proposed schema
-- Scope: internal operations setup model. Do not run automatically until reviewed.

create extension if not exists pgcrypto;

create table if not exists public.client_setup (
  id uuid primary key default gen_random_uuid(),
  cliente_slug text not null unique,
  canonical_slug text not null,
  cliente_nombre text not null,
  intake_source text default 'portal',
  intake_table text,
  intake_received_at timestamptz,
  review_status text not null default 'pending_review',
  setup_status text not null default 'draft',
  responsable text,
  launch_status text not null default 'not_ready',
  learning_notes text,
  risk_notes text,
  source_refs jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.client_setup_steps (
  id uuid primary key default gen_random_uuid(),
  client_setup_id uuid not null references public.client_setup(id) on delete cascade,
  step_key text not null,
  step_name text not null,
  status text not null default 'pending',
  owner text,
  due_date date,
  completed_at timestamptz,
  notes text,
  sort_order integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (client_setup_id, step_key)
);

create table if not exists public.client_icp_profiles (
  id uuid primary key default gen_random_uuid(),
  client_setup_id uuid not null references public.client_setup(id) on delete cascade,
  profile_name text not null default 'Target Market Profile Principal',
  status text not null default 'draft',
  countries jsonb not null default '[]'::jsonb,
  industries jsonb not null default '[]'::jsonb,
  cargos jsonb not null default '[]'::jsonb,
  company_sizes jsonb not null default '[]'::jsonb,
  keywords jsonb not null default '[]'::jsonb,
  exclusions jsonb not null default '[]'::jsonb,
  source text default 'onboarding',
  approved_at timestamptz,
  approved_by text,
  learning_notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.client_icp_segments (
  id uuid primary key default gen_random_uuid(),
  client_setup_id uuid not null references public.client_setup(id) on delete cascade,
  icp_profile_id uuid references public.client_icp_profiles(id) on delete set null,
  segment_name text not null,
  country text,
  region text,
  industry text,
  cargo_area text,
  company_size text,
  keywords jsonb not null default '[]'::jsonb,
  status text not null default 'active',
  priority text not null default 'medium',
  assigned_sdr_slug text,
  database_status text default 'pending',
  campaign_status text default 'pending',
  result_status text default 'no_data',
  learning_notes text,
  performance_summary jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.client_target_accounts (
  id uuid primary key default gen_random_uuid(),
  client_setup_id uuid not null references public.client_setup(id) on delete cascade,
  icp_segment_id uuid references public.client_icp_segments(id) on delete set null,
  company_name text not null,
  domain text,
  status text not null default 'target',
  source text,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.client_excluded_accounts (
  id uuid primary key default gen_random_uuid(),
  client_setup_id uuid not null references public.client_setup(id) on delete cascade,
  company_name text not null,
  domain text,
  exclusion_type text not null default 'other',
  source text,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.client_domains (
  id uuid primary key default gen_random_uuid(),
  client_setup_id uuid not null references public.client_setup(id) on delete cascade,
  domain text not null,
  provider text,
  status text not null default 'pending',
  created_on date,
  expires_on date,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (client_setup_id, domain)
);

create table if not exists public.client_mailboxes (
  id uuid primary key default gen_random_uuid(),
  client_setup_id uuid not null references public.client_setup(id) on delete cascade,
  domain_id uuid references public.client_domains(id) on delete set null,
  mailbox text not null,
  provider text,
  status text not null default 'pending',
  owner_name text,
  owner_role text,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (client_setup_id, mailbox)
);

create table if not exists public.client_email_signatures (
  id uuid primary key default gen_random_uuid(),
  client_setup_id uuid not null references public.client_setup(id) on delete cascade,
  mailbox_id uuid references public.client_mailboxes(id) on delete set null,
  signature_name text not null,
  implementation_status text not null default 'pending',
  asset_path text,
  html_path text,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.client_warmup (
  id uuid primary key default gen_random_uuid(),
  client_setup_id uuid not null references public.client_setup(id) on delete cascade,
  mailbox_id uuid references public.client_mailboxes(id) on delete cascade,
  warmup_status text not null default 'pending',
  provider text default 'Snov.io',
  started_at date,
  ended_at date,
  target_daily_volume integer,
  current_daily_volume integer,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.client_databases (
  id uuid primary key default gen_random_uuid(),
  client_setup_id uuid not null references public.client_setup(id) on delete cascade,
  icp_segment_id uuid references public.client_icp_segments(id) on delete set null,
  database_name text not null,
  source text,
  country text,
  industry text,
  cargo text,
  segment text,
  status text not null default 'pending_review',
  prospect_count integer,
  quality_estimated text,
  file_path text,
  duplicate_group text,
  observations text,
  alerts jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.client_campaigns (
  id uuid primary key default gen_random_uuid(),
  client_setup_id uuid not null references public.client_setup(id) on delete cascade,
  icp_segment_id uuid references public.client_icp_segments(id) on delete set null,
  campaign_name text not null,
  platform text,
  source text,
  country text,
  segment text,
  status text not null default 'pending_review',
  prospect_count integer,
  quality_estimated text,
  snov_campaign_id text,
  ghl_campaign_id text,
  file_path text,
  observations text,
  alerts jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.client_sdr_assignments (
  id uuid primary key default gen_random_uuid(),
  client_setup_id uuid not null references public.client_setup(id) on delete cascade,
  icp_segment_id uuid references public.client_icp_segments(id) on delete set null,
  sdr_slug text not null,
  sdr_name text,
  ghl_user_id text,
  status text not null default 'pending',
  starts_on date,
  ends_on date,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.client_setup_history (
  id uuid primary key default gen_random_uuid(),
  client_setup_id uuid not null references public.client_setup(id) on delete cascade,
  action_at timestamptz not null default now(),
  action text not null,
  actor text,
  entity_type text,
  entity_id text,
  previous_value jsonb,
  new_value jsonb,
  observations text,
  created_at timestamptz not null default now()
);

create index if not exists client_setup_canonical_slug_idx on public.client_setup(canonical_slug);
create index if not exists client_icp_segments_setup_idx on public.client_icp_segments(client_setup_id);
create index if not exists client_databases_setup_idx on public.client_databases(client_setup_id);
create index if not exists client_campaigns_setup_idx on public.client_campaigns(client_setup_id);
create index if not exists client_setup_history_setup_idx on public.client_setup_history(client_setup_id, action_at desc);

create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'client_setup',
    'client_setup_steps',
    'client_icp_profiles',
    'client_icp_segments',
    'client_target_accounts',
    'client_excluded_accounts',
    'client_domains',
    'client_mailboxes',
    'client_email_signatures',
    'client_warmup',
    'client_databases',
    'client_campaigns',
    'client_sdr_assignments'
  ]
  loop
    execute format('drop trigger if exists trg_%I_updated_at on public.%I', table_name, table_name);
    execute format(
      'create trigger trg_%I_updated_at before update on public.%I for each row execute function public.set_updated_at()',
      table_name,
      table_name
    );
  end loop;
end $$;
