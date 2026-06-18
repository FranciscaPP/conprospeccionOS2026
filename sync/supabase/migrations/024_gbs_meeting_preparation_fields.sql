-- 024 — Preparación de reuniones GBS y respaldo manual interno.
-- Aditivo e idempotente. Conserva raw_data/custom_fields originales.

alter table public.contactos
  add column if not exists informacion_reunion text,
  add column if not exists bant_sdr text;

alter table public.reuniones
  add column if not exists informacion_reunion text,
  add column if not exists bant_sdr text;

alter table public.seguimiento_reuniones
  add column if not exists informacion_reunion_manual text,
  add column if not exists icp_cumple boolean;

comment on column public.contactos.informacion_reunion is
  'Valor normalizado desde contact.informacin_de_preparacin_para_la_reunin.';
comment on column public.contactos.bant_sdr is
  'Valor normalizado desde contact.validacin_sdr_bant.';
comment on column public.reuniones.informacion_reunion is
  'Información de preparación sincronizada desde el contacto GHL.';
comment on column public.reuniones.bant_sdr is
  'BANT informado por SDR y sincronizado desde el contacto GHL.';
comment on column public.seguimiento_reuniones.informacion_reunion_manual is
  'Corrección o complemento manual interno visible en el portal cliente.';
comment on column public.seguimiento_reuniones.icp_cumple is
  'Antecedente ICP separado de la resolución contractual.';
