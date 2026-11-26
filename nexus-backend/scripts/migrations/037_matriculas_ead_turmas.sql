-- 037 — Alunos colocados em Turma EAD pela tela de Turmas antes da 036 não tinham matrícula EAD
-- (matriculas_ead): não apareciam na Gestão de Matrículas EAD nem viam as disciplinas do curso no AVA.
-- Cria a matrícula (Regular, origem manual) para cada vaga ativa em Turma EAD sem matrícula no curso.
-- Idempotente.

BEGIN;

INSERT INTO matriculas_ead (id, aluno_id, curso_id, ativa_automaticamente, data_matricula, tipo, origem, status,
                            turma_id, criado_em, atualizado_em)
SELECT gen_random_uuid(), x.aluno_id, x.curso_id, true, x.data_matricula, 'regular', 'manual', 'ativa',
       x.turma_id, now(), now()
  FROM (
      SELECT DISTINCT ON (ta.aluno_id, t.curso_id)
             ta.aluno_id, t.curso_id, t.id AS turma_id, COALESCE(ta.data_matricula, ta.criado_em, now()) AS data_matricula
        FROM turma_alunos ta
        JOIN turmas t ON t.id = ta.turma_id
       WHERE t.modalidade = 'ead' AND t.curso_id IS NOT NULL
         AND COALESCE(ta.status, 'ativo') = 'ativo'
         AND t.cancelada_em IS NULL
       ORDER BY ta.aluno_id, t.curso_id, ta.data_matricula DESC NULLS LAST
  ) x
 WHERE NOT EXISTS (SELECT 1 FROM matriculas_ead m WHERE m.aluno_id = x.aluno_id AND m.curso_id = x.curso_id);

COMMIT;
