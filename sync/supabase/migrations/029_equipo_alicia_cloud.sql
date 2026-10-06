-- Estado cloud e idempotencia para @equipo_alicia_bot.
-- Las tablas y RPC quedan disponibles exclusivamente para service_role.

create table if not exists public.sdr_report_deliveries (
    delivery_key text primary key,
    status text not null default 'processing'
        check (status in ('processing', 'sent', 'failed')),
    attempt_count integer not null default 1 check (attempt_count between 1 and 2),
    part1_sent_at timestamptz,
    part2_sent_at timestamptz,
    sent_at timestamptz,
    error_summary text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.sdr_bot_queries (
    update_id bigint primary key,
    chat_id bigint not null,
    text text not null,
    status text not null default 'queued'
        check (status in ('queued', 'processing', 'answered', 'failed')),
    attempt_count integer not null default 0 check (attempt_count between 0 and 2),
    answered_at timestamptz,
    error_summary text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table public.sdr_report_deliveries enable row level security;
alter table public.sdr_bot_queries enable row level security;

revoke all on table public.sdr_report_deliveries from public;
revoke all on table public.sdr_report_deliveries from anon;
revoke all on table public.sdr_report_deliveries from authenticated;
revoke all on table public.sdr_bot_queries from public;
revoke all on table public.sdr_bot_queries from anon;
revoke all on table public.sdr_bot_queries from authenticated;
grant select, insert, update, delete on table public.sdr_report_deliveries to service_role;
grant select, insert, update, delete on table public.sdr_bot_queries to service_role;

create or replace function public.claim_sdr_report_delivery(p_delivery_key text)
returns setof public.sdr_report_deliveries
language plpgsql
set search_path = public
as $$
declare
    claimed public.sdr_report_deliveries%rowtype;
begin
    insert into public.sdr_report_deliveries (delivery_key)
    values (p_delivery_key)
    on conflict (delivery_key) do nothing
    returning * into claimed;

    if found then
        return next claimed;
        return;
    end if;

    update public.sdr_report_deliveries
       set status = 'processing',
           attempt_count = attempt_count + 1,
           updated_at = now(),
           error_summary = null
     where delivery_key = p_delivery_key
       and attempt_count < 2
       and (
           status = 'failed'
           or (status = 'processing' and updated_at < now() - interval '30 minutes')
       )
    returning * into claimed;

    if found then
        return next claimed;
    end if;
end;
$$;

create or replace function public.claim_sdr_bot_query(p_update_id bigint)
returns setof public.sdr_bot_queries
language plpgsql
set search_path = public
as $$
declare
    claimed public.sdr_bot_queries%rowtype;
begin
    update public.sdr_bot_queries
       set status = 'processing',
           attempt_count = attempt_count + 1,
           updated_at = now(),
           error_summary = null
     where update_id = p_update_id
       and attempt_count < 2
       and (
           status in ('queued', 'failed')
           or (status = 'processing' and updated_at < now() - interval '30 minutes')
       )
    returning * into claimed;

    if found then
        return next claimed;
    end if;
end;
$$;

revoke all on function public.claim_sdr_report_delivery(text) from public;
revoke all on function public.claim_sdr_report_delivery(text) from anon;
revoke all on function public.claim_sdr_report_delivery(text) from authenticated;
revoke all on function public.claim_sdr_bot_query(bigint) from public;
revoke all on function public.claim_sdr_bot_query(bigint) from anon;
revoke all on function public.claim_sdr_bot_query(bigint) from authenticated;
grant execute on function public.claim_sdr_report_delivery(text) to service_role;
grant execute on function public.claim_sdr_bot_query(bigint) to service_role;
