alter table public.clientes add column if not exists tipo_servicio text default 'outbound';
alter table public.clientes add column if not exists tipo_meta text default 'total_contrato';
alter table public.clientes add column if not exists pago_setup numeric;
alter table public.clientes add column if not exists observaciones text;

alter table public.sdrs add column if not exists email text;
alter table public.sdrs add column if not exists ghl_user_id text;
alter table public.sdrs add column if not exists estado text not null default 'activo';
alter table public.sdrs add column if not exists costo_base numeric;
alter table public.sdrs add column if not exists pago_variable_reunion numeric;
alter table public.sdrs add column if not exists bonos jsonb not null default '[]'::jsonb;
alter table public.sdrs add column if not exists observaciones text;

alter table public.sdr_cliente add column if not exists location_id text;
alter table public.sdr_cliente add column if not exists fecha_inicio_asignacion date;
alter table public.sdr_cliente add column if not exists fecha_fin_asignacion date;
alter table public.sdr_cliente add column if not exists estado_asignacion text not null default 'activo';

update public.sdr_cliente sc
set location_id = c.ghl_location_id
from public.clientes c
where sc.cliente_slug = c.slug
  and sc.location_id is null;

alter table public.llamadas add column if not exists ghl_call_id text;
alter table public.llamadas add column if not exists cliente_slug text references public.clientes(slug) on update cascade on delete set null;
alter table public.llamadas add column if not exists sdr_slug text references public.sdrs(slug) on update cascade on delete set null;
alter table public.llamadas add column if not exists ghl_contact_id text;
alter table public.llamadas add column if not exists ghl_owner_user_id text;
alter table public.llamadas add column if not exists location_id text;
alter table public.llamadas add column if not exists fecha date;
alter table public.llamadas add column if not exists hora time;
alter table public.llamadas add column if not exists started_at timestamptz;
alter table public.llamadas add column if not exists duracion_segundos numeric;
alter table public.llamadas add column if not exists duracion_minutos numeric;
alter table public.llamadas add column if not exists direccion text;
alter table public.llamadas add column if not exists resultado text;
alter table public.llamadas add column if not exists telefono text;
alter table public.llamadas add column if not exists raw_data jsonb not null default '{}'::jsonb;
alter table public.llamadas add column if not exists synced_at timestamptz not null default now();

create unique index if not exists llamadas_ghl_call_id_uidx
  on public.llamadas(ghl_call_id);
create index if not exists llamadas_fecha_idx on public.llamadas(fecha);
create index if not exists llamadas_cliente_slug_idx on public.llamadas(cliente_slug);
create index if not exists llamadas_sdr_slug_idx on public.llamadas(sdr_slug);

alter table public.reuniones add column if not exists ghl_appointment_id text;
alter table public.reuniones add column if not exists cliente_slug text references public.clientes(slug) on update cascade on delete set null;
alter table public.reuniones add column if not exists sdr_slug text references public.sdrs(slug) on update cascade on delete set null;
alter table public.reuniones add column if not exists ghl_contact_id text;
alter table public.reuniones add column if not exists ghl_owner_user_id text;
alter table public.reuniones add column if not exists location_id text;
alter table public.reuniones add column if not exists empresa text;
alter table public.reuniones add column if not exists contacto text;
alter table public.reuniones add column if not exists telefono text;
alter table public.reuniones add column if not exists email text;
alter table public.reuniones add column if not exists cargo text;
alter table public.reuniones add column if not exists industria text;
alter table public.reuniones add column if not exists pais text;
alter table public.reuniones add column if not exists fecha_agendada date;
alter table public.reuniones add column if not exists fecha_reunion date;
alter table public.reuniones add column if not exists hora_reunion time;
alter table public.reuniones add column if not exists starts_at timestamptz;
alter table public.reuniones add column if not exists ends_at timestamptz;
alter table public.reuniones add column if not exists estado_reunion text;
alter table public.reuniones add column if not exists es_valida boolean;
alter table public.reuniones add column if not exists motivo_rechazo text;
alter table public.reuniones add column if not exists observacion text;
alter table public.reuniones add column if not exists raw_data jsonb not null default '{}'::jsonb;
alter table public.reuniones add column if not exists synced_at timestamptz not null default now();

create unique index if not exists reuniones_ghl_appointment_id_uidx
  on public.reuniones(ghl_appointment_id);
create index if not exists reuniones_fecha_reunion_idx on public.reuniones(fecha_reunion);
create index if not exists reuniones_cliente_slug_idx on public.reuniones(cliente_slug);
create index if not exists reuniones_sdr_slug_idx on public.reuniones(sdr_slug);

create table if not exists public.costos_herramientas (
  id uuid primary key default gen_random_uuid(),
  herramienta text not null,
  slug text not null unique,
  costo_mensual numeric,
  moneda text not null default 'CLP',
  cliente_slug text references public.clientes(slug) on update cascade on delete set null,
  tipo_costo text not null default 'herramienta',
  observacion text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

insert into public.costos_herramientas (herramienta, slug, costo_mensual, moneda, tipo_costo, observacion)
select nombre, slug, monto, moneda, 'herramienta', notas
from public.costos_fijos
on conflict (slug) do update set
  herramienta = excluded.herramienta,
  costo_mensual = excluded.costo_mensual,
  moneda = excluded.moneda,
  tipo_costo = excluded.tipo_costo,
  observacion = excluded.observacion,
  updated_at = now();

create table if not exists public.pagos_sdr (
  id uuid primary key default gen_random_uuid(),
  sdr_slug text references public.sdrs(slug) on update cascade on delete cascade,
  cliente_slug text references public.clientes(slug) on update cascade on delete cascade,
  base_mensual numeric,
  variable_reunion_valida numeric,
  bono_semanal numeric,
  bono_mensual numeric,
  condicion_bono text,
  fecha_vigencia date default current_date,
  activo boolean not null default true,
  observacion text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists pagos_sdr_active_uidx
  on public.pagos_sdr(sdr_slug, cliente_slug, fecha_vigencia);

create table if not exists public.resumen_diario_sdr (
  fecha date not null,
  sdr_slug text references public.sdrs(slug) on update cascade on delete cascade,
  cliente_slug text references public.clientes(slug) on update cascade on delete cascade,
  llamadas_totales numeric not null default 0,
  minutos_totales numeric not null default 0,
  reuniones_agendadas numeric not null default 0,
  reuniones_validas numeric not null default 0,
  reuniones_no_validas numeric not null default 0,
  contactos_cargados numeric not null default 0,
  oportunidades_creadas numeric not null default 0,
  conversion_llamadas_reuniones numeric not null default 0,
  conversion_llamadas_reuniones_validas numeric not null default 0,
  updated_at timestamptz not null default now(),
  primary key (fecha, sdr_slug, cliente_slug)
);

create table if not exists public.resumen_cliente (
  fecha date not null,
  cliente_slug text references public.clientes(slug) on update cascade on delete cascade,
  contactos_totales numeric not null default 0,
  llamadas_totales numeric not null default 0,
  minutos_totales numeric not null default 0,
  reuniones_agendadas numeric not null default 0,
  reuniones_validas numeric not null default 0,
  reuniones_no_validas numeric not null default 0,
  avance_meta numeric not null default 0,
  forecast numeric not null default 0,
  riesgo text not null default 'sin_datos',
  updated_at timestamptz not null default now(),
  primary key (fecha, cliente_slug)
);

create table if not exists public.resumen_financiero (
  cliente_slug text references public.clientes(slug) on update cascade on delete cascade,
  periodo text not null,
  ingresos_fijos numeric not null default 0,
  ingresos_variables numeric not null default 0,
  ingresos_totales numeric not null default 0,
  costos_sdr numeric not null default 0,
  costos_herramientas numeric not null default 0,
  costos_totales numeric not null default 0,
  margen numeric not null default 0,
  rentabilidad numeric not null default 0,
  costo_por_reunion_valida numeric not null default 0,
  updated_at timestamptz not null default now(),
  primary key (cliente_slug, periodo)
);

create or replace view public.vw_reuniones_del_dia as
select
  r.fecha_reunion,
  r.hora_reunion,
  s.nombre as sdr,
  c.nombre as cliente,
  r.empresa,
  r.contacto,
  r.cargo,
  r.industria,
  r.pais,
  r.email,
  r.telefono,
  r.estado_reunion,
  r.es_valida,
  r.motivo_rechazo,
  r.observacion
from public.reuniones r
left join public.sdrs s on s.slug = r.sdr_slug
left join public.clientes c on c.slug = r.cliente_slug
where r.fecha_reunion = current_date
order by r.hora_reunion nulls last, r.starts_at nulls last;

create or replace view public.vw_ranking_sdr_hoy as
select
  s.slug as sdr_slug,
  s.nombre as sdr,
  coalesce(l.llamadas_totales, 0) as llamadas_realizadas,
  coalesce(l.minutos_totales, 0) as minutos_hablados,
  coalesce(r.reuniones_agendadas, 0) as reuniones_agendadas,
  coalesce(r.reuniones_validas, 0) as reuniones_validas,
  coalesce(r.reuniones_no_validas, 0) as reuniones_no_validas,
  coalesce(ct.contactos_cargados, 0) as contactos_cargados,
  case when coalesce(l.llamadas_totales, 0) = 0 then 0 else round(coalesce(r.reuniones_agendadas, 0) / l.llamadas_totales, 4) end as conversion_llamadas_reuniones,
  case when coalesce(l.llamadas_totales, 0) = 0 then 0 else round(coalesce(r.reuniones_validas, 0) / l.llamadas_totales, 4) end as conversion_llamadas_reuniones_validas,
  case when coalesce(r.reuniones_agendadas, 0) = 0 then 0 else round(coalesce(r.reuniones_validas, 0) / r.reuniones_agendadas, 4) end as tasa_validacion
from public.sdrs s
left join (
  select sdr_slug, count(*)::numeric llamadas_totales, coalesce(sum(duracion_minutos), 0)::numeric minutos_totales
  from public.llamadas
  where fecha = current_date
  group by sdr_slug
) l on l.sdr_slug = s.slug
left join (
  select
    sdr_slug,
    count(*)::numeric reuniones_agendadas,
    count(*) filter (where es_valida is true)::numeric reuniones_validas,
    count(*) filter (where es_valida is false)::numeric reuniones_no_validas
  from public.reuniones
  where fecha_reunion = current_date
  group by sdr_slug
) r on r.sdr_slug = s.slug
left join (
  select sdr_slug, count(*)::numeric contactos_cargados
  from public.contactos
  where ghl_created_at::date = current_date
  group by sdr_slug
) ct on ct.sdr_slug = s.slug
where s.estado = 'activo'
order by reuniones_validas desc, reuniones_agendadas desc, llamadas_realizadas desc;

create or replace view public.vw_clientes_riesgo as
select
  c.slug as cliente_slug,
  c.nombre as cliente,
  c.estado_contrato,
  cc.tipo_contrato,
  cc.fecha_inicio,
  cc.fecha_termino,
  cm.reuniones_validas_meta,
  coalesce(cm.reuniones_validas_actuales, 0) as reuniones_validas_iniciales,
  coalesce(rv.reuniones_validas_sync, 0) as reuniones_validas_sync,
  coalesce(cm.reuniones_validas_actuales, 0) + coalesce(rv.reuniones_validas_sync, 0) as reuniones_validas_total,
  case
    when cm.reuniones_validas_meta is null or cm.reuniones_validas_meta = 0 then 0
    else round((coalesce(cm.reuniones_validas_actuales, 0) + coalesce(rv.reuniones_validas_sync, 0)) / cm.reuniones_validas_meta, 4)
  end as avance_meta,
  case
    when c.estado_contrato in ('setup', 'pausado', 'finalizado') then 'no_evaluable'
    when cc.fecha_inicio is null or cc.fecha_termino is null or cm.reuniones_validas_meta is null then 'sin_datos'
    when current_date < cc.fecha_inicio then 'setup'
    else
      case
        when (
          case when cm.reuniones_validas_meta = 0 then 1
          else (coalesce(cm.reuniones_validas_actuales, 0) + coalesce(rv.reuniones_validas_sync, 0)) / cm.reuniones_validas_meta end
        ) >= (
          greatest(0, least(1, (current_date - cc.fecha_inicio)::numeric / nullif((cc.fecha_termino - cc.fecha_inicio)::numeric, 0)))
        ) then 'verde'
        when (
          case when cm.reuniones_validas_meta = 0 then 1
          else (coalesce(cm.reuniones_validas_actuales, 0) + coalesce(rv.reuniones_validas_sync, 0)) / cm.reuniones_validas_meta end
        ) >= (
          greatest(0, least(1, (current_date - cc.fecha_inicio)::numeric / nullif((cc.fecha_termino - cc.fecha_inicio)::numeric, 0))) - 0.15
        ) then 'amarillo'
        else 'rojo'
      end
  end as riesgo
from public.clientes c
left join public.cliente_contratos cc on cc.cliente_slug = c.slug
left join public.cliente_metas cm on cm.cliente_slug = c.slug and cm.periodo = 'contrato'
left join (
  select cliente_slug, count(*)::numeric reuniones_validas_sync
  from public.reuniones
  where es_valida is true
  group by cliente_slug
) rv on rv.cliente_slug = c.slug;

create or replace view public.vw_financiero_cliente as
select
  c.slug as cliente_slug,
  c.nombre as cliente,
  coalesce(ccos.pago_mensual, 0) as ingreso_mensual,
  coalesce(ccos.pago_variable, 0) as ingreso_variable_por_reunion,
  coalesce(rv.reuniones_validas, 0) as reuniones_validas,
  coalesce(ccos.pago_mensual, 0) + (coalesce(ccos.pago_variable, 0) * coalesce(rv.reuniones_validas, 0)) as ingresos_totales_estimados,
  coalesce(h.costos_herramientas, 0) as costos_herramientas,
  coalesce(ps.costos_sdr, 0) as costos_sdr,
  coalesce(h.costos_herramientas, 0) + coalesce(ps.costos_sdr, 0) as costos_totales_estimados,
  (coalesce(ccos.pago_mensual, 0) + (coalesce(ccos.pago_variable, 0) * coalesce(rv.reuniones_validas, 0)))
    - (coalesce(h.costos_herramientas, 0) + coalesce(ps.costos_sdr, 0)) as margen_estimado,
  case
    when coalesce(ccos.pago_mensual, 0) + (coalesce(ccos.pago_variable, 0) * coalesce(rv.reuniones_validas, 0)) = 0 then 0
    else round(
      ((coalesce(ccos.pago_mensual, 0) + (coalesce(ccos.pago_variable, 0) * coalesce(rv.reuniones_validas, 0)))
      - (coalesce(h.costos_herramientas, 0) + coalesce(ps.costos_sdr, 0)))
      / (coalesce(ccos.pago_mensual, 0) + (coalesce(ccos.pago_variable, 0) * coalesce(rv.reuniones_validas, 0))),
      4
    )
  end as rentabilidad_estimada,
  case when coalesce(rv.reuniones_validas, 0) = 0 then 0 else round((coalesce(h.costos_herramientas, 0) + coalesce(ps.costos_sdr, 0)) / rv.reuniones_validas, 2) end as costo_por_reunion_valida
from public.clientes c
left join public.cliente_costos ccos on ccos.cliente_slug = c.slug
left join (
  select cliente_slug, count(*)::numeric reuniones_validas
  from public.reuniones
  where es_valida is true
  group by cliente_slug
) rv on rv.cliente_slug = c.slug
left join (
  select cliente_slug, sum(costo_mensual)::numeric costos_herramientas
  from public.costos_herramientas
  group by cliente_slug
) h on h.cliente_slug = c.slug
left join (
  select cliente_slug, sum(coalesce(base_mensual, 0) + coalesce(variable_reunion_valida, 0))::numeric costos_sdr
  from public.pagos_sdr
  where activo is true
  group by cliente_slug
) ps on ps.cliente_slug = c.slug;

create or replace view public.vw_operacional_hoy as
select
  current_date as fecha,
  (select count(*) from public.reuniones where fecha_reunion = current_date) as reuniones_dia,
  (select count(*) from public.reuniones where date_trunc('week', fecha_reunion)::date = date_trunc('week', current_date)::date) as reuniones_semana,
  (select count(*) from public.reuniones where fecha_reunion = current_date and es_valida is true) as reuniones_validas_dia,
  (select count(*) from public.reuniones where fecha_reunion = current_date and es_valida is null) as reuniones_pendientes_validacion,
  (select count(*) from public.llamadas where fecha = current_date) as llamadas_dia,
  (select coalesce(sum(duracion_minutos), 0) from public.llamadas where fecha = current_date) as minutos_hablados_dia,
  (select count(*) from public.contactos where ghl_created_at::date = current_date) as contactos_cargados_dia,
  (select count(*) from public.vw_clientes_riesgo where riesgo = 'rojo') as clientes_en_riesgo,
  (select count(*) from public.sdrs s where s.estado = 'activo' and not exists (
    select 1 from public.llamadas l where l.sdr_slug = s.slug and l.fecha = current_date
  )) as sdrs_sin_actividad_hoy;
