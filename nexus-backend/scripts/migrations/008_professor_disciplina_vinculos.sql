-- Relação N:N entre professores e disciplinas do cadastro administrativo.
-- Separada de professor_disciplinas, que contém vínculos acadêmicos com turma
-- e pode ter materiais e atas associados.
BEGIN;

CREATE TABLE IF NOT EXISTS professor_disciplina_vinculos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professor_id UUID NOT NULL REFERENCES professores(id) ON DELETE CASCADE,
    disciplina_id UUID NOT NULL REFERENCES disciplinas(id) ON DELETE CASCADE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (professor_id, disciplina_id)
);

COMMIT;
