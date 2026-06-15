alter table public.cliente_contratos
  add column if not exists tipo_contrato text not null default 'plazo_fijo';

alter table public.cliente_contratos
  add column if not exists duracion_meses numeric;

update public.cliente_contratos
set
  tipo_contrato = 'plazo_fijo',
  duracion_meses = 5,
  notas = trim(both from concat_ws(E'\n', notas, 'Contrato por 5 meses.'))
where cliente_slug in ('bambutech', 'gbs_logistics');

update public.cliente_contratos
set
  tipo_contrato = 'indefinido',
  duracion_meses = null,
  fecha_inicio = null,
  fecha_termino = null,
  notas = trim(both from concat_ws(E'\n', notas, 'Contrato indefinido.'))
where cliente_slug = 'clickie';
