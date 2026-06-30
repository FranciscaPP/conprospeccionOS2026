alter table public.seguimiento_reuniones
  add column if not exists historial_visibilidad jsonb not null default '{}'::jsonb,
  add column if not exists historial_manual jsonb not null default '[]'::jsonb;

comment on column public.seguimiento_reuniones.historial_visibilidad is
  'Mapa de visibilidad de hitos del historial para el portal cliente.';
comment on column public.seguimiento_reuniones.historial_manual is
  'Notas manuales del historial con visibilidad cliente/interno.';
