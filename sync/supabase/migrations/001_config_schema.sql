create extension if not exists pgcrypto;

create table if not exists public.clientes (
  id uuid primary key default gen_random_uuid(),
  nombre text not null,
  slug text not null unique,
  ghl_location_id text unique,
  env_location_key text,
  pais_prospeccion text,
  estado_contrato text not null default 'activo',
  notas text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.clientes add column if not exists nombre text;
alter table public.clientes add column if not exists slug text;
alter table public.clientes add column if not exists ghl_location_id text;
alter table public.clientes add column if not exists env_location_key text;
alter table public.clientes add column if not exists pais_prospeccion text;
alter table public.clientes add column if not exists estado_contrato text not null default 'activo';
alter table public.clientes add column if not exists notas text;
alter table public.clientes add column if not exists created_at timestamptz not null default now();
alter table public.clientes add column if not exists updated_at timestamptz not null default now();
create unique index if not exists clientes_slug_uidx on public.clientes(slug);
create unique index if not exists clientes_ghl_location_id_uidx on public.clientes(ghl_location_id) where ghl_location_id is not null;

create table if not exists public.sdrs (
  id uuid primary key default gen_random_uuid(),
  nombre text not null,
  slug text not null unique,
  activo boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.sdrs add column if not exists nombre text;
alter table public.sdrs add column if not exists slug text;
alter table public.sdrs add column if not exists activo boolean not null default true;
alter table public.sdrs add column if not exists created_at timestamptz not null default now();
alter table public.sdrs add column if not exists updated_at timestamptz not null default now();
create unique index if not exists sdrs_slug_uidx on public.sdrs(slug);

create table if not exists public.sdr_cliente (
  id uuid primary key default gen_random_uuid(),
  cliente_slug text not null references public.clientes(slug) on update cascade on delete cascade,
  sdr_slug text not null references public.sdrs(slug) on update cascade on delete cascade,
  ghl_user_id text,
  activo boolean not null default true,
  notas text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (cliente_slug, sdr_slug)
);

create table if not exists public.cliente_metas (
  id uuid primary key default gen_random_uuid(),
  cliente_slug text not null references public.clientes(slug) on update cascade on delete cascade,
  periodo text not null default 'contrato',
  reuniones_validas_meta numeric,
  reuniones_validas_actuales numeric,
  notas text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (cliente_slug, periodo)
);

create table if not exists public.cliente_contratos (
  id uuid primary key default gen_random_uuid(),
  cliente_slug text not null references public.clientes(slug) on update cascade on delete cascade,
  fecha_inicio date,
  fecha_termino date,
  tipo_contrato text not null default 'plazo_fijo',
  duracion_meses numeric,
  estado text not null default 'activo',
  notas text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (cliente_slug)
);

create table if not exists public.cliente_costos (
  id uuid primary key default gen_random_uuid(),
  cliente_slug text not null references public.clientes(slug) on update cascade on delete cascade,
  pago_mensual numeric,
  pago_mensual_moneda text default 'CLP',
  pago_variable numeric,
  pago_variable_moneda text default 'CLP',
  notas text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (cliente_slug)
);

create table if not exists public.costos_fijos (
  id uuid primary key default gen_random_uuid(),
  nombre text not null,
  slug text not null unique,
  monto numeric,
  moneda text not null default 'CLP',
  frecuencia text not null default 'mensual',
  notas text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.sdr_pago_reglas (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  nombre text not null,
  tipo text not null,
  monto numeric,
  moneda text not null default 'CLP',
  condicion text,
  notas text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.import_runs (
  id uuid primary key default gen_random_uuid(),
  source_file text not null,
  status text not null,
  stats jsonb not null default '{}'::jsonb,
  errors jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

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
    'clientes',
    'sdrs',
    'sdr_cliente',
    'cliente_metas',
    'cliente_contratos',
    'cliente_costos',
    'costos_fijos',
    'sdr_pago_reglas'
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
