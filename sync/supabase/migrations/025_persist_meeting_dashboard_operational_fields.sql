alter table public.seguimiento_reuniones
  add column if not exists estado_caso text,
  add column if not exists evidencia_visibilidad jsonb not null default '{}'::jsonb,
  add column if not exists evidencia_manual jsonb not null default '[]'::jsonb,
  add column if not exists etapa_agenda_metadata jsonb not null default '{}'::jsonb,
  add column if not exists comentario_final_cliente text,
  add column if not exists respuesta_cp_cliente text,
  add column if not exists evidencia_cliente text;

comment on column public.seguimiento_reuniones.estado_caso is
  'Estado operativo interno del caso. No visible en portal cliente.';
comment on column public.seguimiento_reuniones.evidencia_visibilidad is
  'Mapa por tipo de evidencia que indica si el cliente puede verla.';
comment on column public.seguimiento_reuniones.evidencia_manual is
  'Evidencias agregadas manualmente desde el panel interno.';
comment on column public.seguimiento_reuniones.etapa_agenda_metadata is
  'Motivo y detalle operativo de cancelaciones o reagendamientos.';
comment on column public.seguimiento_reuniones.comentario_final_cliente is
  'Mensaje de Estado Final visible para el portal cliente.';
comment on column public.seguimiento_reuniones.respuesta_cp_cliente is
  'Respuesta de Conprospeccion a una evaluacion o revision del cliente.';
comment on column public.seguimiento_reuniones.evidencia_cliente is
  'Evidencia o referencia aportada/indicada en la evaluacion cliente.';
