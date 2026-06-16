-- 022 — Columnas de evidencia IA (tl;dv / Google Meet) en reuniones
-- Alimentadas por el webhook app/api/meetings/evidence/tldv.
-- Aditivo e idempotente: no afecta filas ni columnas existentes.

alter table public.reuniones add column if not exists recording_url      text;
alter table public.reuniones add column if not exists transcript_url     text;
alter table public.reuniones add column if not exists ai_summary         text;
alter table public.reuniones add column if not exists ai_evidence        text;
alter table public.reuniones add column if not exists ai_bant_detected   jsonb not null default '[]'::jsonb;
alter table public.reuniones add column if not exists ai_recommendation  text;
alter table public.reuniones add column if not exists ai_confidence      numeric;
alter table public.reuniones add column if not exists ai_dispute_flag    boolean not null default false;
