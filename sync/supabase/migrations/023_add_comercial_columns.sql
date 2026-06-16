-- 023 — Avance comercial editable desde el portal cliente (Avance reuniones).
-- comercial_estado: etiqueta del estado comercial (Propuesta, Reunión agendada, ...).
-- comercial_proximo_paso: texto libre del próximo paso comercial.
-- Aditivo e idempotente.

alter table public.reuniones add column if not exists comercial_estado       text;
alter table public.reuniones add column if not exists comercial_proximo_paso text;
