-- ═══════════════════════════════════════════════════════════════
-- 003 — Finanzas SDR + tablas de control de sync
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS pagos_sdr (
  id                        UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  sdr_slug                  TEXT,
  cliente_slug              TEXT,
  periodo_mes               DATE,
  base_mensual              NUMERIC,
  variable_reunion_valida   NUMERIC,
  bono_semanal              NUMERIC,
  bono_mensual              NUMERIC,
  condicion_bono            TEXT,
  fecha_vigencia            DATE        DEFAULT CURRENT_DATE,
  activo                    BOOLEAN     NOT NULL DEFAULT true,
  reuniones_validas_periodo NUMERIC     NOT NULL DEFAULT 0,
  monto_base                NUMERIC     NOT NULL DEFAULT 0,
  monto_variable            NUMERIC     NOT NULL DEFAULT 0,
  ajustes                   NUMERIC     NOT NULL DEFAULT 0,
  total_pagado              NUMERIC     NOT NULL DEFAULT 0,
  moneda                    TEXT        NOT NULL DEFAULT 'USD',
  fecha_pago                DATE,
  estado_pago               TEXT        NOT NULL DEFAULT 'pendiente',
  observacion               TEXT,
  observaciones_pago        TEXT,
  created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Registro de cada ejecución de sync GHL → Supabase
CREATE TABLE IF NOT EXISTS sync_runs (
  id         UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  source     TEXT        NOT NULL,
  entity     TEXT        NOT NULL,
  status     TEXT        NOT NULL,
  stats      JSONB       NOT NULL DEFAULT '{}',
  errors     JSONB       NOT NULL DEFAULT '[]',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Registro de imports manuales (CSV/XLSX)
CREATE TABLE IF NOT EXISTS import_runs (
  id          UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  source_file TEXT        NOT NULL,
  status      TEXT        NOT NULL,
  stats       JSONB       NOT NULL DEFAULT '{}',
  errors      JSONB       NOT NULL DEFAULT '[]',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
