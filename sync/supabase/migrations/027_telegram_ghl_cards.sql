create table if not exists public.telegram_ghl_cards (
  id bigint generated always as identity primary key,
  cliente_slug text not null references public.clientes(slug) on update cascade on delete cascade,
  chat_id bigint not null,
  telegram_message_id bigint not null,
  ghl_contact_id text not null,
  ghl_location_id text not null,
  prospect_name text,
  prospect_email text,
  created_at timestamptz not null default now(),
  unique (chat_id, telegram_message_id)
);

create index if not exists telegram_ghl_cards_contact_idx
  on public.telegram_ghl_cards(ghl_contact_id);
create index if not exists telegram_ghl_cards_cliente_idx
  on public.telegram_ghl_cards(cliente_slug);
