-- ═══════════════════════════════════════════════════════════════
-- 004 — Tablas de seguimiento por cliente
-- Patrón: {cliente}_seguimiento → una fila por reunión
-- reunion_id referencia reuniones.id
-- ═══════════════════════════════════════════════════════════════

-- Tiresias (creada ~2026-05)
CREATE TABLE IF NOT EXISTS tiresias_seguimiento (
  reunion_id       BIGINT      NOT NULL PRIMARY KEY,
  status_comercial TEXT,
  etapa_comercial  TEXT,
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Clickie (creada ~2026-05)
CREATE TABLE IF NOT EXISTS clickie_seguimiento (
  reunion_id       BIGINT      NOT NULL PRIMARY KEY,
  status_comercial TEXT,
  etapa_comercial  TEXT,
  updated_at       TIMESTAMPTZ          DEFAULT now()
);

-- GBS Logistics (creada 2026-06-02)
CREATE TABLE IF NOT EXISTS gbs_seguimiento (
  reunion_id       BIGINT      NOT NULL PRIMARY KEY,
  status_comercial TEXT,
  etapa_comercial  TEXT,
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
