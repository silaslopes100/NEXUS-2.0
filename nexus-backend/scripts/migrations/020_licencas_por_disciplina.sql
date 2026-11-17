-- =============================================================================
-- 020 - Estoque de licencas por disciplina (Fase 3A)
--
-- - licencas_estoque passa a ter 1 linha por (polo|escola, disciplina).
--   materia_id NULL = balde "Sem disciplina" (saldo anterior a esta migracao).
-- - Consolida linhas duplicadas de estoque. Um bug no backend gravava uma
--   linha nova a cada credito na escola (o filtro usava polo_id IS NOT NULL);
--   as quantidades sao somadas numa unica linha.
-- - FKs de materia_id -> disciplinas (estoque, movimentacoes, licencas de aluno).
-- - Indices unicos: uma linha de estoque por local/disciplina e no maximo uma
--   licenca ATIVA por aluno/disciplina.
--
-- Antes de rodar (diagnostico; nao altera nada):
--   SELECT escola_id, materia_id, count(*) FROM licencas_estoque
--    WHERE polo_id IS NULL GROUP BY 1, 2 HAVING count(*) > 1;
--   SELECT aluno_id, count(*) FROM licencas_alunos
--    WHERE status = 'ativa' GROUP BY 1 HAVING count(*) > 1;
--
-- Idempotente. Se algo falhar, a transacao inteira e revertida.
-- =============================================================================
BEGIN;

-- 1) Consolida duplicadas (polo e escola), somando quantidades na linha mais recente.
WITH ranqueado AS (
    SELECT id,
           COALESCE(escola_id, polo_id) AS local_id,
           (escola_id IS NOT NULL) AS eh_escola,
           materia_id,
           row_number() OVER (
               PARTITION BY COALESCE(escola_id, polo_id), (escola_id IS NOT NULL), materia_id
               ORDER BY atualizado_em DESC NULLS LAST, id
           ) AS rn,
           sum(quantidade_disponivel) OVER (
               PARTITION BY COALESCE(escola_id, polo_id), (escola_id IS NOT NULL), materia_id
           ) AS total_disp,
           sum(quantidade_vendida) OVER (
               PARTITION BY COALESCE(escola_id, polo_id), (escola_id IS NOT NULL), materia_id
           ) AS total_vend,
           count(*) OVER (
               PARTITION BY COALESCE(escola_id, polo_id), (escola_id IS NOT NULL), materia_id
           ) AS qtd
      FROM licencas_estoque
)
UPDATE licencas_estoque le
   SET quantidade_disponivel = r.total_disp,
       quantidade_vendida = r.total_vend,
       atualizado_em = now()
  FROM ranqueado r
 WHERE le.id = r.id AND r.rn = 1 AND r.qtd > 1;

WITH ranqueado AS (
    SELECT id,
           row_number() OVER (
               PARTITION BY COALESCE(escola_id, polo_id), (escola_id IS NOT NULL), materia_id
               ORDER BY atualizado_em DESC NULLS LAST, id
           ) AS rn
      FROM licencas_estoque
)
DELETE FROM licencas_estoque le
 USING ranqueado r
 WHERE le.id = r.id AND r.rn > 1;

-- 2) Licencas ativas duplicadas por aluno nao sao corrigidas automaticamente:
--    a migracao para e informa, para revisao manual.
DO $$
DECLARE
    duplicados INT;
BEGIN
    SELECT count(*) INTO duplicados FROM (
        SELECT aluno_id, materia_id FROM licencas_alunos
         WHERE status = 'ativa' GROUP BY 1, 2 HAVING count(*) > 1
    ) d;
    IF duplicados > 0 THEN
        RAISE EXCEPTION 'Ha % aluno(s) com mais de uma licenca ativa na mesma disciplina. Revise licencas_alunos antes de aplicar a 020.', duplicados;
    END IF;
END $$;

-- 3) Chaves estrangeiras para disciplinas.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_licencas_estoque_disciplina') THEN
        ALTER TABLE licencas_estoque
            ADD CONSTRAINT fk_licencas_estoque_disciplina
            FOREIGN KEY (materia_id) REFERENCES disciplinas(id) ON DELETE RESTRICT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_licencas_mov_disciplina') THEN
        ALTER TABLE licencas_movimentacoes
            ADD CONSTRAINT fk_licencas_mov_disciplina
            FOREIGN KEY (materia_id) REFERENCES disciplinas(id) ON DELETE RESTRICT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_licencas_alunos_disciplina') THEN
        ALTER TABLE licencas_alunos
            ADD CONSTRAINT fk_licencas_alunos_disciplina
            FOREIGN KEY (materia_id) REFERENCES disciplinas(id) ON DELETE RESTRICT;
    END IF;
END $$;

-- 4) Unicidade (NULL = balde "Sem disciplina", tratado como um valor).
CREATE UNIQUE INDEX IF NOT EXISTS uq_licencas_estoque_polo_disciplina
    ON licencas_estoque (polo_id, COALESCE(materia_id, '00000000-0000-0000-0000-000000000000'::uuid))
    WHERE escola_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_licencas_estoque_escola_disciplina
    ON licencas_estoque (escola_id, COALESCE(materia_id, '00000000-0000-0000-0000-000000000000'::uuid))
    WHERE polo_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_licencas_alunos_ativa_disciplina
    ON licencas_alunos (aluno_id, COALESCE(materia_id, '00000000-0000-0000-0000-000000000000'::uuid))
    WHERE status = 'ativa';

CREATE INDEX IF NOT EXISTS idx_licencas_mov_materia ON licencas_movimentacoes (materia_id);

COMMENT ON COLUMN licencas_estoque.materia_id IS 'Disciplina do saldo; NULL = "Sem disciplina"';
COMMENT ON COLUMN licencas_movimentacoes.tipo IS
    'compra_fornecedor, distribuicao_polo_escola, venda_aluno, devolucao_escola_polo, devolucao_aluno_escola, reingresso_churn, reclassificacao';

COMMIT;
