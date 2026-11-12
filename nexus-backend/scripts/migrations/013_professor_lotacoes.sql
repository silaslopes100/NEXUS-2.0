-- Lotações do professor: um professor pode atender N polos e N escolas.
-- Cada linha é um polo (obrigatório) com escola opcional. As colunas
-- professores.polo_id/escola_id continuam existindo como a lotação "principal"
-- (compatibilidade com telas e consultas antigas).
-- Idempotente: pode ser executada mais de uma vez.
BEGIN;

CREATE TABLE IF NOT EXISTS professor_lotacoes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professor_id UUID NOT NULL REFERENCES professores(id) ON DELETE CASCADE,
    polo_id UUID NOT NULL REFERENCES polos(id) ON DELETE CASCADE,
    escola_id UUID REFERENCES escolas(id) ON DELETE CASCADE,
    criado_por UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Uma mesma combinação polo/escola só uma vez por professor (escola nula conta como valor).
CREATE UNIQUE INDEX IF NOT EXISTS uq_professor_lotacoes_unidade
    ON professor_lotacoes (
        professor_id,
        polo_id,
        COALESCE(escola_id, '00000000-0000-0000-0000-000000000000'::uuid)
    );
CREATE INDEX IF NOT EXISTS ix_professor_lotacoes_polo ON professor_lotacoes (polo_id);
CREATE INDEX IF NOT EXISTS ix_professor_lotacoes_escola ON professor_lotacoes (escola_id)
    WHERE escola_id IS NOT NULL;

-- 1) Lotação atual de cada professor (polo próprio ou o polo da escola).
INSERT INTO professor_lotacoes (professor_id, polo_id, escola_id)
SELECT prof.id, COALESCE(prof.polo_id, esc.polo_id), prof.escola_id
FROM professores prof
LEFT JOIN escolas esc ON esc.id = prof.escola_id
WHERE COALESCE(prof.polo_id, esc.polo_id) IS NOT NULL
ON CONFLICT DO NOTHING;

-- 2) Polos/escolas das turmas em que o professor já leciona.
INSERT INTO professor_lotacoes (professor_id, polo_id, escola_id)
SELECT DISTINCT pd.professor_id, COALESCE(t.polo_id, esc.polo_id), t.escola_id
FROM professor_disciplinas pd
JOIN turmas t ON t.id = pd.turma_id
LEFT JOIN escolas esc ON esc.id = t.escola_id
WHERE pd.ativo = true
  AND COALESCE(t.polo_id, esc.polo_id) IS NOT NULL
ON CONFLICT DO NOTHING;

COMMIT;
