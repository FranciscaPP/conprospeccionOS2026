create table if not exists public.ghl_users (
  id uuid primary key default gen_random_uuid(),
  ghl_user_id text not null,
  cliente_slug text references public.clientes(slug) on update cascade on delete set null,
  location_id text,
  sdr_slug text references public.sdrs(slug) on update cascade on delete set null,
  nombre text,
  first_name text,
  last_name text,
  email text,
  phone text,
  deleted boolean not null default false,
  raw_data jsonb not null default '{}'::jsonb,
  synced_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (cliente_slug, ghl_user_id)
);

alter table public.llamadas add column if not exists conversation_id text;
alter table public.llamadas add column if not exists mensaje_tipo text;
alter table public.llamadas add column if not exists source text;

create index if not exists ghl_users_ghl_user_id_idx on public.ghl_users(ghl_user_id);
create index if not exists ghl_users_cliente_slug_idx on public.ghl_users(cliente_slug);
create index if not exists llamadas_conversation_id_idx on public.llamadas(conversation_id);

drop trigger if exists trg_ghl_users_updated_at on public.ghl_users;
create trigger trg_ghl_users_updated_at
before update on public.ghl_users
for each row execute function public.set_updated_at();
