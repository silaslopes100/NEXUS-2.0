BEGIN;

ALTER TABLE alunos
    ADD COLUMN IF NOT EXISTS revalidado_em TIMESTAMPTZ;

ALTER TABLE alunos_desistentes
    ADD COLUMN IF NOT EXISTS reingresso_em TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS matricula_anterior VARCHAR(32);

CREATE TABLE IF NOT EXISTS conteudo_progresso (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id UUID NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    conteudo_id UUID NOT NULL REFERENCES disciplina_conteudos(id) ON DELETE CASCADE,
    concluido_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (aluno_id, conteudo_id)
);

COMMIT;
