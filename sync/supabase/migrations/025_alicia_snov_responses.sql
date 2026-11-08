-- Alicia · Gestión de respuestas de campañas Snov.io desde Telegram
--
-- Estado y trazabilidad del flujo determinístico (sin IA):
--   detección Gmail → filtro por código → correlación Snov → alerta agrupada
--   a Telegram → (opcional) borrador/aprobación → envío en hilo → acciones GHL.
--
-- Ninguna de estas tablas guarda secretos. Los refresh tokens de Gmail viven
-- SOLO en Secrets (GitHub Actions / Supabase). `alicia_accounts.token_env`
-- guarda el NOMBRE de la variable de entorno, nunca el valor.

-- Registro de cuentas de correo monitoreadas (escala a 25+ sin código por cuenta).
create table if not exists public.alicia_accounts (
  account_id   text primary key,                 -- identificador corto y estable, p.ej. "cuenta01"
  email        text not null unique,             -- dirección de correo receptora
  enabled      boolean not null default false,   -- habilitar una cuenta es solo configuración
  token_env    text not null,                    -- NOMBRE del env var con el refresh token (no el valor)
  cliente_slug text references public.clientes(slug) on update cascade on delete set null,
  notas        text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

-- Idempotencia de detección: un mensaje de Gmail se procesa una sola vez.
create table if not exists public.alicia_processed_messages (
  gmail_message_id text primary key,
  thread_id        text,
  account_id       text references public.alicia_accounts(account_id) on update cascade on delete set null,
  classification   text not null,                -- genuine | bounce | auto_reply | out_of_office | spam | unrelated
  processed_at     timestamptz not null default now()
);

-- Estado por hilo de conversación. `internal_ref` es el "identificador interno"
-- que se muestra en la notificación (derivado del thread_id, estable).
create table if not exists public.alicia_email_threads (
  thread_id            text primary key,         -- Gmail threadId
  internal_ref         text not null unique,     -- p.ej. AL-3F9A2C7B
  account_id           text references public.alicia_accounts(account_id) on update cascade on delete set null,
  account_email        text,
  prospect_email       text,
  prospect_name        text,
  empresa              text,
  snov_campaign_id     text,
  cliente_slug         text,
  subject              text,
  last_message_snippet text,
  last_gmail_message_id text,
  ghl_contact_id       text,
  classification       text,
  estado               text not null default 'nueva',  -- nueva|alertada|borrador|aprobada|enviada|no_responder|error
  dry_run              boolean not null default true,
  first_seen_at        timestamptz not null default now(),
  last_seen_at         timestamptz not null default now(),
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now()
);

-- Relación mensaje de Telegram ↔ hilo ↔ cuenta ↔ contacto GHL.
create table if not exists public.alicia_telegram_links (
  id                 uuid primary key default gen_random_uuid(),
  telegram_message_id bigint,
  telegram_chat_id    bigint,
  thread_id          text references public.alicia_email_threads(thread_id) on update cascade on delete cascade,
  account_id         text,
  ghl_contact_id     text,
  kind               text not null default 'alert',   -- alert|draft|approval|confirmation
  created_at         timestamptz not null default now()
);

-- Auditoría de acciones (envíos de correo, notas GHL, cambios de etapa, errores).
create table if not exists public.alicia_actions_log (
  id         uuid primary key default gen_random_uuid(),
  thread_id  text,
  action     text not null,                       -- alert_sent|draft_created|email_sent|ghl_upserted|ghl_note|ghl_stage|error
  status     text not null default 'ok',          -- ok|error|skipped_dry_run
  detail     jsonb not null default '{}'::jsonb,
  dry_run    boolean not null default true,
  created_at timestamptz not null default now()
);

-- Registro de cada ejecución del poller (una notificación agrupada por corrida).
create table if not exists public.alicia_runs (
  id                uuid primary key default gen_random_uuid(),
  started_at        timestamptz not null default now(),
  finished_at       timestamptz,
  accounts_checked  integer not null default 0,
  messages_scanned  integer not null default 0,
  replies_detected  integer not null default 0,
  filtered_out      jsonb not null default '{}'::jsonb,  -- {bounce: n, auto_reply: n, ...}
  status            text not null default 'running',      -- running|success|error
  dry_run           boolean not null default true,
  created_at        timestamptz not null default now()
);

create index if not exists alicia_threads_account_idx on public.alicia_email_threads(account_id);
create index if not exists alicia_threads_estado_idx on public.alicia_email_threads(estado);
create index if not exists alicia_threads_prospect_idx on public.alicia_email_threads(prospect_email);
create index if not exists alicia_processed_thread_idx on public.alicia_processed_messages(thread_id);
create index if not exists alicia_tg_links_thread_idx on public.alicia_telegram_links(thread_id);
create index if not exists alicia_tg_links_msg_idx on public.alicia_telegram_links(telegram_message_id);
create index if not exists alicia_actions_thread_idx on public.alicia_actions_log(thread_id);

drop trigger if exists trg_alicia_accounts_updated_at on public.alicia_accounts;
create trigger trg_alicia_accounts_updated_at
before update on public.alicia_accounts
for each row execute function public.set_updated_at();

drop trigger if exists trg_alicia_threads_updated_at on public.alicia_email_threads;
create trigger trg_alicia_threads_updated_at
before update on public.alicia_email_threads
for each row execute function public.set_updated_at();
