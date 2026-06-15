-- Tabla de seguimiento comercial para el portal Tiresias.
-- Ejecutar UNA VEZ en Supabase → SQL Editor.

CREATE TABLE IF NOT EXISTS tiresias_seguimiento (
    reunion_id       BIGINT PRIMARY KEY,   -- FK a reuniones.id
    status_comercial TEXT,                 -- notas libres del cliente
    etapa_comercial  TEXT,                 -- slug: envio_propuesta | seguimiento_propuesta | sin_respuesta_post | avanzando_post
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Trigger para updated_at automático
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_tiresias_seguimiento_updated_at ON tiresias_seguimiento;
CREATE TRIGGER trg_tiresias_seguimiento_updated_at
    BEFORE UPDATE ON tiresias_seguimiento
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- RLS: acceso con service-role key (misma key que usa el dashboard)
ALTER TABLE tiresias_seguimiento ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all" ON tiresias_seguimiento
    USING (true) WITH CHECK (true);
