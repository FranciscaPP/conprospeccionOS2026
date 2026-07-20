-- 007 - Internal weekly task board
-- Scope: simple internal operations board for Francisca and Yanina.

create extension if not exists pgcrypto;

create table if not exists public.internal_tasks (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  description text not null default '',
  reference_url text not null default '',
  client text not null default 'Interno',
  owner text not null default 'Yanina',
  status text not null default 'Pendiente',
  priority text not null default 'Media',
  due_date date,
  week_start date not null,
  created_by text,
  completed_at timestamptz,
  is_archived boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint internal_tasks_client_check check (client in ('Interno', 'GBS', 'BambuTech')),
  constraint internal_tasks_owner_check check (owner in ('Yanina', 'Francisca')),
  constraint internal_tasks_status_check check (status in ('Pendiente', 'En proceso', 'Revisión', 'Terminado')),
  constraint internal_tasks_priority_check check (priority in ('Alta', 'Media', 'Baja'))
);

create index if not exists internal_tasks_week_status_idx
  on public.internal_tasks(week_start, status, owner, client, priority);

create index if not exists internal_tasks_due_date_idx
  on public.internal_tasks(due_date)
  where is_archived = false;

create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_internal_tasks_updated_at on public.internal_tasks;
create trigger trg_internal_tasks_updated_at
  before update on public.internal_tasks
  for each row execute function public.set_updated_at();
