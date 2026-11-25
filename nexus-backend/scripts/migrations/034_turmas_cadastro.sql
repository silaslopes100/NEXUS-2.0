-- 034 — Cadastro de turmas: código, modalidade, turno/horário, vagas, local, responsável,
-- cancelamento e prazos de disciplinas EAD.
--  * A situação da turma é derivada (planejada / em andamento / concluída / cancelada), sem coluna.
--  * Início e fim da turma = vigência do Calendário Acadêmico do curso (backfill abaixo).
--  * disciplinas.ead_prazo_dias: prazo próprio da disciplina na turma EAD (senão, o padrão do calendário).
-- Idempotente: pode ser executada mais de uma vez.

BEGIN;

ALTER TABLE turmas ADD COLUMN IF NOT EXISTS codigo VARCHAR(30);
ALTER TABLE turmas ADD COLUMN IF NOT EXISTS modalidade VARCHAR(12) NOT NULL DEFAULT 'presencial';
ALTER TABLE turmas ADD COLUMN IF NOT EXISTS turno VARCHAR(10);
ALTER TABLE turmas ADD COLUMN IF NOT EXISTS horario_inicio TIME;
ALTER TABLE turmas ADD COLUMN IF NOT EXISTS horario_fim TIME;
ALTER TABLE turmas ADD COLUMN IF NOT EXISTS vagas INT;
ALTER TABLE turmas ADD COLUMN IF NOT EXISTS local_aulas TEXT;
ALTER TABLE turmas ADD COLUMN IF NOT EXISTS responsavel_id UUID REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE turmas ADD COLUMN IF NOT EXISTS cancelada_em TIMESTAMPTZ;
ALTER TABLE turmas ADD COLUMN IF NOT EXISTS cancelada_por UUID REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE turmas ADD COLUMN IF NOT EXISTS motivo_cancelamento TEXT;

ALTER TABLE disciplinas ADD COLUMN IF NOT EXISTS ead_prazo_dias INT;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_turmas_modalidade') THEN
        ALTER TABLE turmas ADD CONSTRAINT ck_turmas_modalidade CHECK (modalidade IN ('presencial', 'ead'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_turmas_turno') THEN
        ALTER TABLE turmas ADD CONSTRAINT ck_turmas_turno
            CHECK (turno IS NULL OR turno IN ('manha', 'tarde', 'noite', 'integral'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_turmas_vagas') THEN
        ALTER TABLE turmas ADD CONSTRAINT ck_turmas_vagas CHECK (vagas IS NULL OR vagas > 0);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_turmas_horario') THEN
        ALTER TABLE turmas ADD CONSTRAINT ck_turmas_horario
            CHECK (horario_inicio IS NULL OR horario_fim IS NULL OR horario_fim > horario_inicio);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_disciplinas_ead_prazo') THEN
        ALTER TABLE disciplinas ADD CONSTRAINT ck_disciplinas_ead_prazo CHECK (ead_prazo_dias IS NULL OR ead_prazo_dias > 0);
    END IF;
END $$;

-- Turmas do "polo EAD" passam a ser modalidade EAD (o vínculo com o polo/escola é mantido).
UPDATE turmas t SET modalidade = 'ead'
  FROM polos p
 WHERE p.id = t.polo_id AND upper(trim(p.nome)) = 'EAD' AND t.modalidade <> 'ead';

-- Início e fim = vigência do calendário do curso (turmas não concluídas e não canceladas).
UPDATE turmas t
   SET data_inicio = ca.data_inicio, data_fim = ca.data_fim, atualizado_em = now()
  FROM cursos c JOIN calendarios_academicos ca ON ca.id = c.calendario_id
 WHERE c.id = t.curso_id
   AND t.concluida_em IS NULL AND t.cancelada_em IS NULL
   AND (t.data_inicio IS DISTINCT FROM ca.data_inicio OR t.data_fim IS DISTINCT FROM ca.data_fim);

-- Código {SIGLA}-{ANO}-{SEQ}: iniciais das palavras do curso (sem de/da/do/e), até 4 letras.
WITH siglas AS (
    SELECT t.id, t.criado_em,
           COALESCE(NULLIF(LEFT(translate(upper((
               SELECT string_agg(LEFT(w.palavra, 1), '' ORDER BY w.ord)
                 FROM regexp_split_to_table(COALESCE(c.nome, ''), '\s+') WITH ORDINALITY AS w(palavra, ord)
                WHERE lower(w.palavra) NOT IN ('de', 'da', 'do', 'das', 'dos', 'e', 'em', 'a', 'o', 'para')
                  AND w.palavra ~ '^[[:alpha:]]'
           )), 'ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ', 'AAAAAEEEEIIIIOOOOOUUUUC'), 4), ''), 'TUR') AS sigla,
           EXTRACT(YEAR FROM COALESCE(t.data_inicio, t.criado_em::date, now()::date))::int AS ano
      FROM turmas t
      LEFT JOIN cursos c ON c.id = t.curso_id
     WHERE t.codigo IS NULL
), numeradas AS (
    SELECT id, sigla, ano,
           ROW_NUMBER() OVER (PARTITION BY sigla, ano ORDER BY criado_em NULLS LAST, id)
           + COALESCE((SELECT MAX(split_part(t2.codigo, '-', 3)::int) FROM turmas t2
                        WHERE t2.codigo LIKE siglas.sigla || '-' || siglas.ano || '-%'
                          AND split_part(t2.codigo, '-', 3) ~ '^\d+$'), 0) AS seq
      FROM siglas
)
UPDATE turmas t SET codigo = n.sigla || '-' || n.ano || '-' || LPAD(n.seq::text, 3, '0')
  FROM numeradas n
 WHERE n.id = t.id;

CREATE UNIQUE INDEX IF NOT EXISTS uq_turmas_codigo ON turmas (codigo);
CREATE INDEX IF NOT EXISTS idx_turmas_responsavel ON turmas (responsavel_id);

COMMIT;
