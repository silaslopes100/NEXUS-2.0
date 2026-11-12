-- Executar somente durante manutencao, apos backup e verificacao dos dados.
BEGIN;

LOCK TABLE professores, disciplinas, professor_disciplina_vinculos, professor_disciplinas
    IN SHARE ROW EXCLUSIVE MODE;

CREATE TABLE IF NOT EXISTS migracao_professor_disciplinas (
    id boolean PRIMARY KEY DEFAULT true CHECK (id),
    concluida_em timestamptz NOT NULL DEFAULT now()
);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid IN ('professor_disciplinas'::regclass, 'professor_disciplina_vinculos'::regclass)
          AND relrowsecurity
    ) THEN
        RAISE EXCEPTION 'Seguranca por linha exige revisao antes da migracao';
    END IF;
    IF EXISTS (
        SELECT 1 FROM professor_disciplinas
        WHERE turma_id IS NULL AND (professor_id IS NULL OR disciplina_id IS NULL)
    ) THEN
        RAISE EXCEPTION 'Existem vinculos sem turma com professor ou disciplina ausente';
    END IF;
    IF EXISTS (
        SELECT 1 FROM professor_disciplinas pd
        LEFT JOIN professores p ON p.id = pd.professor_id
        LEFT JOIN disciplinas d ON d.id = pd.disciplina_id
        WHERE pd.turma_id IS NULL AND (p.id IS NULL OR d.id IS NULL)
    ) THEN
        RAISE EXCEPTION 'Existem vinculos no destino com referencias invalidas';
    END IF;
    IF EXISTS (
        SELECT 1 FROM professor_disciplinas
        WHERE turma_id IS NULL
        GROUP BY professor_id, disciplina_id HAVING count(*) > 1
    ) THEN
        RAISE EXCEPTION 'Existem vinculos administrativos duplicados no destino';
    END IF;
    IF EXISTS (
        SELECT 1 FROM professor_disciplina_vinculos v
        LEFT JOIN professores p ON p.id = v.professor_id
        LEFT JOIN disciplinas d ON d.id = v.disciplina_id
        WHERE p.id IS NULL OR d.id IS NULL
    ) THEN
        RAISE EXCEPTION 'Existem vinculos de origem com referencias invalidas';
    END IF;
END;
$$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_professor_disciplinas_cadastro
    ON professor_disciplinas (professor_id, disciplina_id) WHERE turma_id IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_index i
        JOIN pg_class idx ON idx.oid = i.indexrelid
        WHERE i.indrelid = 'professor_disciplinas'::regclass
          AND idx.relname = 'uq_professor_disciplinas_cadastro'
          AND i.indisunique AND i.indisvalid
          AND i.indnkeyatts = 2 AND i.indnatts = 2
          AND i.indkey[0] = (SELECT attnum FROM pg_attribute
                              WHERE attrelid = i.indrelid AND attname = 'professor_id')
          AND i.indkey[1] = (SELECT attnum FROM pg_attribute
                              WHERE attrelid = i.indrelid AND attname = 'disciplina_id')
          AND pg_get_expr(i.indpred, i.indrelid) = '(turma_id IS NULL)'
    ) THEN
        RAISE EXCEPTION 'Indice administrativo existente nao corresponde ao esperado';
    END IF;
END;
$$;

INSERT INTO professor_disciplinas
    (professor_id, disciplina_id, turma_id, ativo, criado_em, atualizado_em)
SELECT v.professor_id, v.disciplina_id, NULL, true, v.criado_em, v.atualizado_em
FROM professor_disciplina_vinculos v
WHERE NOT EXISTS (SELECT 1 FROM migracao_professor_disciplinas WHERE id = true)
  AND NOT EXISTS (
    SELECT 1 FROM professor_disciplinas pd
    WHERE pd.professor_id = v.professor_id
      AND pd.disciplina_id = v.disciplina_id AND pd.turma_id IS NULL
);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM professor_disciplina_vinculos v
        WHERE NOT EXISTS (
            SELECT 1 FROM professor_disciplinas pd
            WHERE pd.professor_id = v.professor_id
              AND pd.disciplina_id = v.disciplina_id AND pd.turma_id IS NULL
        )
    ) AND NOT EXISTS (SELECT 1 FROM migracao_professor_disciplinas WHERE id = true) THEN
        RAISE EXCEPTION 'Nem todos os vinculos de origem foram migrados';
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION calcular_totais_professor()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    SELECT COALESCE(SUM(d.carga_horaria), 0),
           COALESCE(SUM(d.qtd_aulas_prevista), 0)
      INTO NEW.horas_totais, NEW.quantidade_aulas
      FROM professor_disciplinas v
      JOIN disciplinas d ON d.id = v.disciplina_id
     WHERE v.professor_id = NEW.id AND v.turma_id IS NULL;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS professores_totais_calculados ON professores;
CREATE TRIGGER professores_totais_calculados
BEFORE INSERT OR UPDATE OF horas_totais, quantidade_aulas ON professores
FOR EACH ROW EXECUTE FUNCTION calcular_totais_professor();

CREATE OR REPLACE FUNCTION atualizar_totais_por_vinculo()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' OR TG_OP = 'UPDATE' THEN
        IF OLD.turma_id IS NULL THEN
            UPDATE professores SET horas_totais = 0 WHERE id = OLD.professor_id;
        END IF;
    END IF;
    IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
        IF NEW.turma_id IS NULL
           AND (TG_OP = 'INSERT' OR OLD.turma_id IS NOT NULL
                OR OLD.professor_id IS DISTINCT FROM NEW.professor_id) THEN
            UPDATE professores SET horas_totais = 0 WHERE id = NEW.professor_id;
        END IF;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS vinculos_atualizam_totais ON professor_disciplina_vinculos;
DROP TRIGGER IF EXISTS vinculos_atualizam_totais ON professor_disciplinas;
CREATE TRIGGER vinculos_atualizam_totais
AFTER INSERT OR UPDATE OR DELETE ON professor_disciplinas
FOR EACH ROW EXECUTE FUNCTION atualizar_totais_por_vinculo();

CREATE OR REPLACE FUNCTION atualizar_totais_por_disciplina()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.carga_horaria IS DISTINCT FROM NEW.carga_horaria
       OR OLD.qtd_aulas_prevista IS DISTINCT FROM NEW.qtd_aulas_prevista THEN
        UPDATE professores SET horas_totais = 0
         WHERE id IN (
             SELECT professor_id FROM professor_disciplinas
             WHERE disciplina_id = NEW.id AND turma_id IS NULL
         );
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS disciplinas_atualizam_totais ON disciplinas;
CREATE TRIGGER disciplinas_atualizam_totais
AFTER UPDATE OF carga_horaria, qtd_aulas_prevista ON disciplinas
FOR EACH ROW EXECUTE FUNCTION atualizar_totais_por_disciplina();

UPDATE professores SET horas_totais = 0;

INSERT INTO migracao_professor_disciplinas (id) VALUES (true)
ON CONFLICT (id) DO NOTHING;

COMMIT;
