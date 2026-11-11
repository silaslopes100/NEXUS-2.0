-- Impede duplicar a presenca de um aluno na mesma aula docente.
-- Acrescenta o contrato do diario a esquemas legados sem remover historico.
BEGIN;

ALTER TABLE presencas
    ADD COLUMN IF NOT EXISTS professor_disciplina_id UUID,
    ADD COLUMN IF NOT EXISTS numero_aula INTEGER,
    ADD COLUMN IF NOT EXISTS data_aula DATE,
    ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ DEFAULT now();

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'presencas'::regclass
          AND conname = 'presencas_professor_disciplina_id_fkey'
    ) THEN
        ALTER TABLE presencas
            ADD CONSTRAINT presencas_professor_disciplina_id_fkey
            FOREIGN KEY (professor_disciplina_id)
            REFERENCES professor_disciplinas(id)
            ON DELETE SET NULL;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'presencas'
          AND column_name = 'aula_id'
    ) THEN
        ALTER TABLE presencas ALTER COLUMN aula_id DROP NOT NULL;
    END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_presencas_vinculo_aluno_aula
    ON presencas (professor_disciplina_id, aluno_id, data_aula, numero_aula)
    WHERE professor_disciplina_id IS NOT NULL
      AND data_aula IS NOT NULL
      AND numero_aula IS NOT NULL;

COMMIT;
