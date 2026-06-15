create table if not exists public.snov_campaigns (
  id uuid primary key default gen_random_uuid(),
  snov_campaign_id text not null unique,
  cliente_slug text references public.clientes(slug) on update cascade on delete set null,
  sdr_slug text references public.sdrs(slug) on update cascade on delete set null,
  nombre text,
  list_id text,
  status text,
  hash text,
  created_at_snov timestamptz,
  updated_at_snov timestamptz,
  started_at_snov timestamptz,
  raw_data jsonb not null default '{}'::jsonb,
  synced_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.snov_campaign_metrics (
  id uuid primary key default gen_random_uuid(),
  snov_campaign_id text not null references public.snov_campaigns(snov_campaign_id) on update cascade on delete cascade,
  cliente_slug text references public.clientes(slug) on update cascade on delete set null,
  sdr_slug text references public.sdrs(slug) on update cascade on delete set null,
  periodo_desde date,
  periodo_hasta date,
  recipients_contacted integer not null default 0,
  emails_sent integer not null default 0,
  email_opens integer not null default 0,
  link_clicks integer not null default 0,
  email_replies integer not null default 0,
  unsubscribed integer not null default 0,
  auto_replied integer not null default 0,
  bounced integer not null default 0,
  email_opens_rate numeric not null default 0,
  link_clicks_rate numeric not null default 0,
  email_replies_rate numeric not null default 0,
  unsubscribed_rate numeric not null default 0,
  progress text,
  progress_status text,
  unfinished integer not null default 0,
  raw_analytics jsonb not null default '{}'::jsonb,
  raw_progress jsonb not null default '{}'::jsonb,
  synced_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (snov_campaign_id, periodo_desde, periodo_hasta)
);

create table if not exists public.snov_email_events (
  id uuid primary key default gen_random_uuid(),
  snov_event_id text not null unique,
  snov_campaign_id text references public.snov_campaigns(snov_campaign_id) on update cascade on delete set null,
  cliente_slug text references public.clientes(slug) on update cascade on delete set null,
  sdr_slug text references public.sdrs(slug) on update cascade on delete set null,
  event_type text not null,
  prospect_id text,
  prospect_name text,
  prospect_email text,
  company text,
  cargo text,
  industria text,
  pais text,
  subject text,
  occurred_at timestamptz,
  raw_data jsonb not null default '{}'::jsonb,
  synced_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.snov_campaign_map (
  id uuid primary key default gen_random_uuid(),
  snov_campaign_id text not null unique,
  cliente_slug text references public.clientes(slug) on update cascade on delete set null,
  sdr_slug text references public.sdrs(slug) on update cascade on delete set null,
  notas text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists snov_campaigns_cliente_idx on public.snov_campaigns(cliente_slug);
create index if not exists snov_campaigns_sdr_idx on public.snov_campaigns(sdr_slug);
create index if not exists snov_campaign_metrics_campaign_idx on public.snov_campaign_metrics(snov_campaign_id);
create index if not exists snov_email_events_campaign_idx on public.snov_email_events(snov_campaign_id);
create index if not exists snov_email_events_email_idx on public.snov_email_events(prospect_email);
create index if not exists snov_email_events_type_idx on public.snov_email_events(event_type);
create index if not exists snov_email_events_occurred_idx on public.snov_email_events(occurred_at);

create or replace view public.vw_snov_campaign_performance as
select
  c.snov_campaign_id,
  c.nombre as campaign_name,
  c.status as campaign_status,
  c.cliente_slug,
  cl.nombre as cliente,
  c.sdr_slug,
  s.nombre as sdr,
  m.periodo_desde,
  m.periodo_hasta,
  m.recipients_contacted,
  m.emails_sent,
  m.email_opens,
  m.email_opens_rate,
  m.link_clicks,
  m.link_clicks_rate,
  m.email_replies,
  m.email_replies_rate,
  m.unsubscribed,
  m.unsubscribed_rate,
  m.auto_replied,
  m.bounced,
  m.progress,
  m.progress_status,
  m.unfinished,
  case when m.emails_sent > 0 then round(m.email_replies::numeric / m.emails_sent, 4) else 0 end as replies_por_email_enviado,
  case when m.recipients_contacted > 0 then round(m.email_replies::numeric / m.recipients_contacted, 4) else 0 end as replies_por_contacto
from public.snov_campaigns c
left join public.snov_campaign_metrics m on m.snov_campaign_id = c.snov_campaign_id
left join public.clientes cl on cl.slug = c.cliente_slug
left join public.sdrs s on s.slug = c.sdr_slug;

create or replace view public.vw_snov_daily_activity as
select
  occurred_at::date as fecha,
  cliente_slug,
  sdr_slug,
  snov_campaign_id,
  count(*) filter (where event_type = 'sent') as emails_enviados,
  count(*) filter (where event_type = 'open') as aperturas,
  count(*) filter (where event_type = 'click') as clicks,
  count(*) filter (where event_type = 'reply') as respuestas,
  count(*) filter (where event_type = 'finished') as prospects_finalizados
from public.snov_email_events
where occurred_at is not null
group by occurred_at::date, cliente_slug, sdr_slug, snov_campaign_id;

drop trigger if exists trg_snov_campaigns_updated_at on public.snov_campaigns;
create trigger trg_snov_campaigns_updated_at
before update on public.snov_campaigns
for each row execute function public.set_updated_at();

drop trigger if exists trg_snov_campaign_metrics_updated_at on public.snov_campaign_metrics;
create trigger trg_snov_campaign_metrics_updated_at
before update on public.snov_campaign_metrics
for each row execute function public.set_updated_at();

drop trigger if exists trg_snov_email_events_updated_at on public.snov_email_events;
create trigger trg_snov_email_events_updated_at
before update on public.snov_email_events
for each row execute function public.set_updated_at();

drop trigger if exists trg_snov_campaign_map_updated_at on public.snov_campaign_map;
create trigger trg_snov_campaign_map_updated_at
before update on public.snov_campaign_map
for each row execute function public.set_updated_at();
