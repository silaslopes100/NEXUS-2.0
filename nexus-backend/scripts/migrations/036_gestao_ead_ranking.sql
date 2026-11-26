-- 036 — Gestão de Matrículas EAD (admin) + pesos do índice do ranking de Polos.
--  * matriculas_ead: tipo (regular | bolsista), origem (site | manual | legado), status (ativa | cancelada),
--    turma, observação e trilha de cancelamento. Bolsista recebe as disciplinas sem custo, pelo calendário.
--  * compras_disciplina_ead: origem (loja | manual | bolsa | legado), quem liberou, motivo e cancelamento.
--    Liberação manual = status_pagamento 'liberado', valor 0.
--  * config_ranking_polos: pesos (notas, frequência, compras) do índice de desempenho dos Polos.
-- Idempotente: pode ser executada mais de uma vez.

BEGIN;

-- Matrículas EAD
ALTER TABLE matriculas_ead ADD COLUMN IF NOT EXISTS tipo VARCHAR(12) NOT NULL DEFAULT 'regular';
ALTER TABLE matriculas_ead ADD COLUMN IF NOT EXISTS origem VARCHAR(12) NOT NULL DEFAULT 'legado';
ALTER TABLE matriculas_ead ADD COLUMN IF NOT EXISTS status VARCHAR(12) NOT NULL DEFAULT 'ativa';
ALTER TABLE matriculas_ead ADD COLUMN IF NOT EXISTS turma_id UUID REFERENCES turmas(id) ON DELETE SET NULL;
ALTER TABLE matriculas_ead ADD COLUMN IF NOT EXISTS observacao TEXT;
ALTER TABLE matriculas_ead ADD COLUMN IF NOT EXISTS criado_por UUID REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE matriculas_ead ADD COLUMN IF NOT EXISTS cancelada_em TIMESTAMPTZ;
ALTER TABLE matriculas_ead ADD COLUMN IF NOT EXISTS cancelada_por UUID REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE matriculas_ead ADD COLUMN IF NOT EXISTS motivo_cancelamento TEXT;
ALTER TABLE matriculas_ead DROP CONSTRAINT IF EXISTS ck_matriculas_ead_tipo;
ALTER TABLE matriculas_ead ADD CONSTRAINT ck_matriculas_ead_tipo CHECK (tipo IN ('regular', 'bolsista'));
ALTER TABLE matriculas_ead DROP CONSTRAINT IF EXISTS ck_matriculas_ead_origem;
ALTER TABLE matriculas_ead ADD CONSTRAINT ck_matriculas_ead_origem CHECK (origem IN ('site', 'manual', 'legado'));
ALTER TABLE matriculas_ead DROP CONSTRAINT IF EXISTS ck_matriculas_ead_status;
ALTER TABLE matriculas_ead ADD CONSTRAINT ck_matriculas_ead_status CHECK (status IN ('ativa', 'cancelada'));
CREATE INDEX IF NOT EXISTS idx_matriculas_ead_aluno ON matriculas_ead (aluno_id, curso_id);
CREATE INDEX IF NOT EXISTS idx_matriculas_ead_turma ON matriculas_ead (turma_id) WHERE turma_id IS NOT NULL;

-- Inscrições feitas pela vitrine (035) antes desta migração: origem 'site' e a turma.
UPDATE matriculas_ead m
   SET origem = 'site',
       turma_id = (SELECT ta.turma_id FROM turma_alunos ta JOIN turmas t ON t.id = ta.turma_id
                    WHERE ta.aluno_id = m.aluno_id AND t.curso_id = m.curso_id AND t.modalidade = 'ead'
                    ORDER BY ta.data_matricula DESC NULLS LAST LIMIT 1)
 WHERE m.origem = 'legado' AND m.legacy_id IS NULL AND m.ativa_automaticamente;

-- Compras / liberações EAD
ALTER TABLE compras_disciplina_ead ADD COLUMN IF NOT EXISTS origem VARCHAR(12) NOT NULL DEFAULT 'legado';
ALTER TABLE compras_disciplina_ead ADD COLUMN IF NOT EXISTS liberada_por UUID REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE compras_disciplina_ead ADD COLUMN IF NOT EXISTS motivo VARCHAR(32);
ALTER TABLE compras_disciplina_ead ADD COLUMN IF NOT EXISTS motivo_texto TEXT;
ALTER TABLE compras_disciplina_ead ADD COLUMN IF NOT EXISTS cancelada_em TIMESTAMPTZ;
ALTER TABLE compras_disciplina_ead ADD COLUMN IF NOT EXISTS cancelada_por UUID REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE compras_disciplina_ead DROP CONSTRAINT IF EXISTS ck_compras_ead_origem;
ALTER TABLE compras_disciplina_ead ADD CONSTRAINT ck_compras_ead_origem CHECK (origem IN ('loja', 'manual', 'bolsa', 'legado'));
UPDATE compras_disciplina_ead SET origem = 'loja' WHERE origem = 'legado' AND pedido_id IS NOT NULL;

-- Pesos do índice de desempenho do ranking de Polos (uma linha só)
CREATE TABLE IF NOT EXISTS config_ranking_polos (
    id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    peso_notas NUMERIC(6,2) NOT NULL DEFAULT 40,
    peso_frequencia NUMERIC(6,2) NOT NULL DEFAULT 30,
    peso_compras NUMERIC(6,2) NOT NULL DEFAULT 30,
    atualizado_por UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    atualizado_em TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT ck_config_ranking_pesos CHECK (peso_notas >= 0 AND peso_frequencia >= 0 AND peso_compras >= 0
                                              AND peso_notas + peso_frequencia + peso_compras > 0)
);
INSERT INTO config_ranking_polos (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

COMMIT;
