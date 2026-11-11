-- Mantem os dados dependentes quando um professor deixa de atender uma turma.
BEGIN;

ALTER TABLE professor_disciplinas
    ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT true;

CREATE INDEX IF NOT EXISTS idx_professor_disciplinas_turma_ativo
    ON professor_disciplinas (turma_id, ativo);

COMMIT;
