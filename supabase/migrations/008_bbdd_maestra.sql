-- 008 - BBDD maestra: pool único de prospectos + ICP por cliente + ledger de reutilización
--
-- Objetivo: consolidar el universo de prospectos (contactos GHL + snov_prospects)
-- en una sola vista deduplicable, guardar el ICP normalizado por cliente y trazar
-- qué prospecto se reutiliza/envía a qué cliente (Snov / GHL).
--
-- La dedup fina (elegir el registro más completo por email) se hace en Python
-- (shared/bbdd_maestra.py). Aquí solo se expone la unión normalizada.

create extension if not exists pgcrypto;

-- ── Pool maestro unificado (vista) ───────────────────────────────────────────
-- Une contactos (fuente GHL) y snov_prospects (fuente Snov) al mismo esquema.
-- email_norm = clave canónica para deduplicar entre fuentes y clientes.
create or replace view public.vw_prospectos_maestros as
select
    'ghl'::text                                         as fuente,
    c.ghl_contact_id                                    as ref_id,
    lower(trim(c.email))                                as email_norm,
    c.email                                             as email,
    coalesce(nullif(trim(c.nombre), ''), c.nombre_contacto) as nombre,
    coalesce(nullif(trim(c.empresa), ''), c.nombre_empresa) as empresa,
    c.cargo                                             as cargo,
    c.industria                                         as industria,
    c.pais                                              as pais,
    c.ciudad                                            as localidad,
    c.telefono                                          as telefono,
    null::text                                          as email_status,
    null::text                                          as linkedin_url,
    c.cliente_slug                                      as cliente_slug_origen,
    c.fecha_creacion::timestamptz                       as origen_creado_at
from public.contactos c
where c.email is not null and trim(c.email) <> ''

union all

select
    'snov'::text                                        as fuente,
    p.snov_prospect_id                                  as ref_id,
    lower(trim(p.email))                                as email_norm,
    p.email                                             as email,
    coalesce(
        nullif(trim(p.nombre), ''),
        nullif(trim(concat_ws(' ', p.first_name, p.last_name)), '')
    )                                                   as nombre,
    p.empresa                                           as empresa,
    p.cargo                                             as cargo,
    p.industria                                         as industria,
    p.pais                                              as pais,
    p.localidad                                         as localidad,
    null::text                                          as telefono,
    p.linkedin_url                                      as linkedin_url,
    p.cliente_slug                                      as cliente_slug_origen,
    p.created_at                                        as origen_creado_at
from public.snov_prospects p
where p.email is not null and trim(p.email) <> '';

comment on view public.vw_prospectos_maestros is
    'Pool maestro unificado GHL+Snov. Dedup fina por email_norm en shared/bbdd_maestra.py.';

-- ── ICP normalizado por cliente ──────────────────────────────────────────────
-- Generaliza el ICP más allá de gbs_onboarding. Cada cliente edita el suyo desde
-- la página BBDD Maestras. Los arrays viven como jsonb de strings.
create table if not exists public.icp_clientes (
    cliente_slug text primary key,
    paises       jsonb not null default '[]'::jsonb,
    industrias   jsonb not null default '[]'::jsonb,
    cargos       jsonb not null default '[]'::jsonb,
    tamanos      jsonb not null default '[]'::jsonb,
    keywords     jsonb not null default '[]'::jsonb,
    exclusiones  jsonb not null default '[]'::jsonb,
    umbral_score numeric not null default 2,
    notas        text,
    updated_at   timestamptz not null default now(),
    updated_by   text
);

comment on table public.icp_clientes is
    'ICP normalizado por cliente para filtrar el pool maestro (BBDD Maestras).';

-- ── Ledger de reutilización / envío ──────────────────────────────────────────
-- Memoria de qué prospecto (email_norm) se asignó/envió a qué cliente. Evita
-- reenviar y permite trazar el destino en Snov/GHL. Idempotente por par.
create table if not exists public.bbdd_maestra_asignaciones (
    id                uuid primary key default gen_random_uuid(),
    email_norm        text not null,
    cliente_slug      text not null,
    estado            text not null default 'candidato'
        check (estado in ('candidato','asignado','enviado_snov','enviado_ghl','descartado')),
    score_icp         numeric,
    motivo            text,
    origen            jsonb not null default '{}'::jsonb,
    snov_campaign_id  text,
    ghl_contact_id    text,
    created_by        text,
    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now(),
    unique (email_norm, cliente_slug)
);

comment on table public.bbdd_maestra_asignaciones is
    'Ledger de reutilización del pool maestro por cliente (destino Snov/GHL).';

create index if not exists bbdd_maestra_asignaciones_cliente_idx
    on public.bbdd_maestra_asignaciones (cliente_slug);
create index if not exists bbdd_maestra_asignaciones_email_idx
    on public.bbdd_maestra_asignaciones (email_norm);

-- ── RLS ──────────────────────────────────────────────────────────────────────
-- Nota de seguridad: el resto del esquema tiene RLS deshabilitado (decisión
-- pendiente de Francisca, ver advisory de Supabase). Aquí habilitamos RLS con
-- política permisiva para NO romper la app (que usa una sola key) y dejar el
-- punto de ajuste listo: para restringir, se edita la policy en vez de activar RLS.
alter table public.icp_clientes enable row level security;
alter table public.bbdd_maestra_asignaciones enable row level security;

drop policy if exists icp_clientes_all on public.icp_clientes;
create policy icp_clientes_all on public.icp_clientes
    for all using (true) with check (true);

drop policy if exists bbdd_maestra_asignaciones_all on public.bbdd_maestra_asignaciones;
create policy bbdd_maestra_asignaciones_all on public.bbdd_maestra_asignaciones
    for all using (true) with check (true);
