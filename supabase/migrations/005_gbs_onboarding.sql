-- ═══════════════════════════════════════════════════════════════
-- 005 — Formulario de onboarding GBS Logistics
-- Creada 2026-06-02. Una fila por cliente (upsert por cliente).
-- El formulario en 14_GBS_Onboarding.py hace upsert con on_conflict='cliente'.
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS gbs_onboarding (
  id                   BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  cliente              TEXT        NOT NULL DEFAULT 'gbs' UNIQUE,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at           TIMESTAMPTZ          DEFAULT now(),

  -- Bloque 1: ICP
  icp_pais             TEXT,
  icp_cargos           TEXT,
  icp_industrias       TEXT,
  icp_tamano           TEXT,
  icp_adicional        TEXT,
  icp_descarte         TEXT,

  -- Bloque 2: Empresa y marca
  web                  TEXT,
  linkedin_empresa     TEXT,
  propuesta_valor      TEXT,
  diferenciadores      TEXT,
  presentacion_servicio TEXT,
  casos_exito          TEXT,

  -- Bloque 3: Mensajería
  tono_lenguaje        TEXT,
  mensajes_funcionan   TEXT,
  mensajes_no_decir    TEXT,
  objeciones           TEXT,

  -- Bloque 4: Proceso comercial
  nombre_ejecutivo     TEXT,
  cargo_ejecutivo      TEXT,
  email_ejecutivo      TEXT,
  proceso_comercial    TEXT,
  duracion_reunion     TEXT,
  intervalo_reunion    TEXT,
  anticipacion_agenda  TEXT,
  notificaciones       TEXT,
  tiempo_cierre        INTEGER,
  ticket_promedio      TEXT,
  plan_contratado      TEXT,

  -- Bloque 5: Inteligencia comercial
  preguntas_discovery  TEXT,
  dolores_clientes     TEXT,
  gatillos_compra      TEXT,
  keywords_prospecto   TEXT,
  notas_adicionales    TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS gbs_onboarding_cliente_unique ON gbs_onboarding (cliente);
