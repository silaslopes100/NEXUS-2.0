-- Migração 001 (idempotente)
-- 1) Remove a relação circular escolas.secretario_usuario_id <-> usuarios.escola_id,
--    mantendo apenas usuarios.escola_id.
-- 2) Vincula turmas a escolas.
-- 3) Sequence para numero_matricula (NX-AAAA-NNNNNNN).

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'escolas' AND column_name = 'secretario_usuario_id'
    ) THEN
        UPDATE usuarios u
           SET escola_id = e.id, polo_id = COALESCE(u.polo_id, e.polo_id)
          FROM escolas e
         WHERE e.secretario_usuario_id = u.id AND u.escola_id IS NULL;
        ALTER TABLE escolas DROP COLUMN secretario_usuario_id;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_usuarios_escola_id ON usuarios (escola_id);
CREATE INDEX IF NOT EXISTS idx_usuarios_polo_id ON usuarios (polo_id);

ALTER TABLE turmas ADD COLUMN IF NOT EXISTS escola_id UUID REFERENCES escolas(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_turmas_escola_id ON turmas (escola_id);
CREATE INDEX IF NOT EXISTS idx_turmas_polo_id ON turmas (polo_id);

CREATE SEQUENCE IF NOT EXISTS seq_matricula_aluno START 1;
