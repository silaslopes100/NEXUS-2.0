CREATE INDEX IF NOT EXISTS idx_notas_atualizado_em_desc
    ON notas (atualizado_em DESC NULLS LAST, id DESC);
