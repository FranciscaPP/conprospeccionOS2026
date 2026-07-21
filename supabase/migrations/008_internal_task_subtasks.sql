-- 008 - Subtasks for internal task board
-- Scope: checklist items inside each Work and Project Management task.

alter table public.internal_tasks
  add column if not exists subtasks jsonb not null default '[]'::jsonb;

comment on column public.internal_tasks.subtasks is
  'Checklist interno de subtareas: [{id, title, done, created_at, completed_at}].';
