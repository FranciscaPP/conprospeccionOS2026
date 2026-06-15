-- ═══════════════════════════════════════════════════════════════
-- 001 — Tablas core: SDRs, clientes y relaciones
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS sdrs (
  id                    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nombre                TEXT,
  email                 TEXT,
  ghl_user_id           TEXT,
  slug                  TEXT,
  activo                BOOLEAN      NOT NULL DEFAULT true,
  estado                TEXT         NOT NULL DEFAULT 'activo',
  costo_base            NUMERIC,
  pago_variable_reunion NUMERIC,
  bonos                 JSONB        NOT NULL DEFAULT '[]',
  observaciones         TEXT,
  created_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS clientes (
  id                    BIGINT PRIMARY KEY,
  nombre_cliente        TEXT,
  nombre                TEXT,
  slug                  TEXT,
  ghl_location_id       TEXT,
  env_location_key      TEXT,
  pais_principal        TEXT,
  pais_prospeccion      TEXT,
  meta_mensual_reuniones INTEGER,
  estado_contrato       TEXT         NOT NULL DEFAULT 'activo',
  tipo_servicio         TEXT                  DEFAULT 'outbound',
  tipo_meta             TEXT                  DEFAULT 'total_contrato',
  pago_setup            NUMERIC,
  notas                 TEXT,
  observaciones         TEXT,
  created_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sdr_cliente (
  id                     UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  cliente_slug           TEXT        NOT NULL,
  sdr_slug               TEXT        NOT NULL,
  ghl_user_id            TEXT,
  location_id            TEXT,
  activo                 BOOLEAN     NOT NULL DEFAULT true,
  estado_asignacion      TEXT        NOT NULL DEFAULT 'activo',
  fecha_inicio_asignacion DATE,
  fecha_fin_asignacion    DATE,
  notas                  TEXT,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sdr_pago_reglas (
  id         UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  slug       TEXT        NOT NULL,
  nombre     TEXT        NOT NULL,
  tipo       TEXT        NOT NULL,
  monto      NUMERIC,
  moneda     TEXT        NOT NULL DEFAULT 'CLP',
  condicion  TEXT,
  notas      TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
