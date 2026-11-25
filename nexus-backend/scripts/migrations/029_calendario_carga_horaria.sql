-- 029 — Calendário Acadêmico, carga horária, cronograma de aulas previstas e tipos de ata
-- Regras de Negócio "Carga Horária, Progresso e Frequência" (RN01–RN07).
--  * calendarios_academicos: datas letivas + regras (pontos em aberto parametrizados).
--  * cursos.calendario_id: o curso segue obrigatoriamente o calendário (a API exige).
--  * cursos.carga_horaria_total / aulas_previstas_total: soma das disciplinas (trigger, RN02).
--  * aulas_previstas: cronograma da turma (status derivado da ata que aponta para a aula).
--  * aulas_ministradas: tipo da aula, aula prevista de referência, horas e justificativa.
-- Idempotente: pode ser executada mais de uma vez.

BEGIN;

CREATE TABLE IF NOT EXISTS calendarios_academicos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome            VARCHAR(255) NOT NULL,
    descricao       TEXT,
    data_inicio     DATE NOT NULL,
    data_fim        DATE NOT NULL,
    dias_semana     INT[] NOT NULL,                      -- 0=domingo .. 6=sábado
    meses_recesso   INT[] NOT NULL DEFAULT '{7,12}',
    feriados        JSONB NOT NULL DEFAULT '[]'::jsonb,  -- [{"data": "AAAA-MM-DD", "descricao": "..."}]
    datas_excluidas DATE[] NOT NULL DEFAULT '{}',
    datas_extras    DATE[] NOT NULL DEFAULT '{}',
    regras          JSONB NOT NULL DEFAULT '{}'::jsonb,
    ativo           BOOLEAN NOT NULL DEFAULT true,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_calendario_periodo CHECK (data_fim >= data_inicio),
    CONSTRAINT ck_calendario_dias CHECK (cardinality(dias_semana) > 0)
);

ALTER TABLE cursos ADD COLUMN IF NOT EXISTS calendario_id UUID REFERENCES calendarios_academicos(id) ON DELETE RESTRICT;
ALTER TABLE cursos ADD COLUMN IF NOT EXISTS aulas_previstas_total INT NOT NULL DEFAULT 0;
CREATE INDEX IF NOT EXISTS idx_cursos_calendario ON cursos (calendario_id);

ALTER TABLE turmas ADD COLUMN IF NOT EXISTS concluida_em TIMESTAMPTZ;
ALTER TABLE turmas ADD COLUMN IF NOT EXISTS concluida_por UUID REFERENCES usuarios(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS aulas_previstas (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    turma_id        UUID NOT NULL REFERENCES turmas(id) ON DELETE CASCADE,
    disciplina_id   UUID NOT NULL REFERENCES disciplinas(id) ON DELETE CASCADE,
    numero          INT NOT NULL CHECK (numero >= 1),
    data_prevista   DATE NOT NULL,
    horas_previstas NUMERIC(6,2) NOT NULL CHECK (horas_previstas > 0),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_aula_prevista UNIQUE (turma_id, disciplina_id, numero)
);
CREATE INDEX IF NOT EXISTS idx_aulas_previstas_turma_data ON aulas_previstas (turma_id, data_prevista);

ALTER TABLE aulas_ministradas ADD COLUMN IF NOT EXISTS tipo VARCHAR(16) NOT NULL DEFAULT 'prevista';
ALTER TABLE aulas_ministradas ADD COLUMN IF NOT EXISTS aula_prevista_id UUID REFERENCES aulas_previstas(id) ON DELETE SET NULL;
ALTER TABLE aulas_ministradas ADD COLUMN IF NOT EXISTS horas NUMERIC(6,2);
ALTER TABLE aulas_ministradas ADD COLUMN IF NOT EXISTS justificativa TEXT;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_aulas_ministradas_tipo') THEN
        ALTER TABLE aulas_ministradas ADD CONSTRAINT ck_aulas_ministradas_tipo
            CHECK (tipo IN ('prevista', 'reposicao', 'extra', 'reforco', 'complemento', 'revisao'));
    END IF;
END
$$;
-- Cada aula prevista é cumprida por uma única ata (prevista OU reposição).
CREATE UNIQUE INDEX IF NOT EXISTS uq_aulas_ministradas_cumpre_prevista
    ON aulas_ministradas (aula_prevista_id)
    WHERE aula_prevista_id IS NOT NULL AND tipo IN ('prevista', 'reposicao');
CREATE INDEX IF NOT EXISTS idx_aulas_ministradas_prevista ON aulas_ministradas (aula_prevista_id);

-- RN02: carga e aulas previstas do curso = soma das disciplinas ativas (nunca editadas à mão).
CREATE OR REPLACE FUNCTION fn_recalcular_carga_curso(p_curso_id UUID) RETURNS void AS $$
BEGIN
    IF p_curso_id IS NULL THEN
        RETURN;
    END IF;
    UPDATE cursos c
       SET carga_horaria_total = COALESCE(s.carga, 0),
           aulas_previstas_total = COALESCE(s.aulas, 0)
      FROM (SELECT SUM(COALESCE(carga_horaria, 0)) AS carga, SUM(COALESCE(qtd_aulas_prevista, 0)) AS aulas
              FROM disciplinas WHERE curso_id = p_curso_id AND COALESCE(ativo, true)) s
     WHERE c.id = p_curso_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION tg_disciplinas_recalcular_curso() RETURNS trigger AS $$
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        PERFORM fn_recalcular_carga_curso(OLD.curso_id);
    END IF;
    IF TG_OP IN ('INSERT', 'UPDATE') AND (TG_OP = 'INSERT' OR NEW.curso_id IS DISTINCT FROM OLD.curso_id
                                           OR NEW.carga_horaria IS DISTINCT FROM OLD.carga_horaria
                                           OR NEW.qtd_aulas_prevista IS DISTINCT FROM OLD.qtd_aulas_prevista
                                           OR NEW.ativo IS DISTINCT FROM OLD.ativo) THEN
        PERFORM fn_recalcular_carga_curso(NEW.curso_id);
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_disciplinas_recalcular_curso ON disciplinas;
CREATE TRIGGER trg_disciplinas_recalcular_curso
    AFTER INSERT OR UPDATE OR DELETE ON disciplinas
    FOR EACH ROW EXECUTE FUNCTION tg_disciplinas_recalcular_curso();

-- RN01: disciplinas sem quantidade de aulas recebem o padrão do calendário (2 aulas por mês).
UPDATE disciplinas SET qtd_aulas_prevista = 2 WHERE COALESCE(qtd_aulas_prevista, 0) <= 0;
UPDATE disciplinas SET carga_horaria = 40 WHERE COALESCE(carga_horaria, 0) <= 0;

-- Calendário padrão para os cursos já existentes (regras = padrões do sistema).
INSERT INTO calendarios_academicos (id, nome, descricao, data_inicio, data_fim, dias_semana)
SELECT gen_random_uuid(), 'Calendário Padrão',
       'Criado na migração 029. Ajuste dias de aula, recessos, feriados e regras antes de gerar cronogramas.',
       make_date(EXTRACT(YEAR FROM now())::int, 1, 1), make_date(EXTRACT(YEAR FROM now())::int + 1, 12, 31),
       '{6}'
WHERE NOT EXISTS (SELECT 1 FROM calendarios_academicos);

UPDATE cursos SET calendario_id = (SELECT id FROM calendarios_academicos ORDER BY criado_em LIMIT 1)
 WHERE calendario_id IS NULL;

SELECT fn_recalcular_carga_curso(id) FROM cursos;

COMMIT;
