create table if not exists public.sdr_activity_events (
  id uuid primary key default gen_random_uuid(),
  source text not null,
  source_id text not null,
  cliente_slug text not null,
  contact_id text,
  event_type text not null,
  occurred_at timestamptz not null,
  duration_seconds integer,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (source, source_id, cliente_slug)
);

create table if not exists public.sdr_daily_baselines (
  baseline_date date not null,
  cliente_slug text not null,
  captured_at timestamptz not null,
  payload jsonb not null,
  primary key (baseline_date, cliente_slug)
);

create table if not exists public.sdr_hourly_snapshots (
  snapshot_date date not null,
  cut_at time not null,
  scope text not null,
  schema_version integer not null default 1,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  primary key (snapshot_date, cut_at, scope)
);

create table if not exists public.sdr_alert_state (
  alert_key text primary key,
  fingerprint text not null,
  severity text not null,
  last_sent_at timestamptz not null,
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists sdr_activity_events_occurred_idx
  on public.sdr_activity_events (occurred_at desc);
create index if not exists sdr_activity_events_client_idx
  on public.sdr_activity_events (cliente_slug, occurred_at desc);
create index if not exists sdr_hourly_snapshots_date_idx
  on public.sdr_hourly_snapshots (snapshot_date desc, cut_at desc);

alter table public.sdr_activity_events enable row level security;
alter table public.sdr_daily_baselines enable row level security;
alter table public.sdr_hourly_snapshots enable row level security;
alter table public.sdr_alert_state enable row level security;

revoke all on public.sdr_activity_events from anon, authenticated;
revoke all on public.sdr_daily_baselines from anon, authenticated;
revoke all on public.sdr_hourly_snapshots from anon, authenticated;
revoke all on public.sdr_alert_state from anon, authenticated;

grant select, insert, update, delete on public.sdr_activity_events to service_role;
grant select, insert, update, delete on public.sdr_daily_baselines to service_role;
grant select, insert, update, delete on public.sdr_hourly_snapshots to service_role;
grant select, insert, update, delete on public.sdr_alert_state to service_role;

