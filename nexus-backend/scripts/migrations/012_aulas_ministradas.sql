-- Aula ministrada: une a ata (conteúdo ministrado), os materiais e a chamada
-- de uma aula (vínculo professor+disciplina+turma, data e número da aula).
-- A tabela `presencas` NÃO muda: a chamada se liga à aula pela mesma chave
-- (professor_disciplina_id, data_aula, numero_aula). Idempotente.
BEGIN;

CREATE TABLE IF NOT EXISTS aulas_ministradas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professor_disciplina_id UUID NOT NULL REFERENCES professor_disciplinas(id) ON DELETE CASCADE,
    data_aula DATE NOT NULL,
    numero_aula INT NOT NULL DEFAULT 1 CHECK (numero_aula >= 1),
    conteudo_ministrado TEXT,
    observacoes TEXT,
    -- Reservado para a Fase 4 (visão do aluno).
    visivel_aluno BOOLEAN NOT NULL DEFAULT true,
    criado_por UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_aulas_ministradas_vinculo_data_numero
        UNIQUE (professor_disciplina_id, data_aula, numero_aula)
);

CREATE INDEX IF NOT EXISTS idx_aulas_ministradas_data ON aulas_ministradas (data_aula DESC);

ALTER TABLE professor_materiais
    ADD COLUMN IF NOT EXISTS aula_id UUID REFERENCES aulas_ministradas(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_professor_materiais_aula ON professor_materiais (aula_id);

-- Backfill 1: toda chamada já lançada vira uma aula (sem ata).
INSERT INTO aulas_ministradas (professor_disciplina_id, data_aula, numero_aula)
SELECT DISTINCT professor_disciplina_id, data_aula, numero_aula
  FROM presencas
 WHERE professor_disciplina_id IS NOT NULL
   AND data_aula IS NOT NULL
   AND numero_aula IS NOT NULL
   AND numero_aula >= 1
ON CONFLICT ON CONSTRAINT uq_aulas_ministradas_vinculo_data_numero DO NOTHING;

-- Backfill 2: material com data de aula vira (ou se junta a) a aula nº 1 daquele dia.
INSERT INTO aulas_ministradas (professor_disciplina_id, data_aula, numero_aula)
SELECT DISTINCT professor_disciplina_id, data_aula, 1
  FROM professor_materiais
 WHERE data_aula IS NOT NULL
   AND aula_id IS NULL
ON CONFLICT ON CONSTRAINT uq_aulas_ministradas_vinculo_data_numero DO NOTHING;

UPDATE professor_materiais material
   SET aula_id = aula.id
  FROM aulas_ministradas aula
 WHERE material.aula_id IS NULL
   AND material.data_aula IS NOT NULL
   AND aula.professor_disciplina_id = material.professor_disciplina_id
   AND aula.data_aula = material.data_aula
   AND aula.numero_aula = 1;

COMMIT;
