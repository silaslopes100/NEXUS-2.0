-- Os totais docentes sao derivados apenas dos vinculos administrativos.
-- O backfill substitui os valores manuais existentes.
BEGIN;

LOCK TABLE professores, disciplinas, professor_disciplina_vinculos IN SHARE ROW EXCLUSIVE MODE;

CREATE OR REPLACE FUNCTION calcular_totais_professor()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    SELECT COALESCE(SUM(d.carga_horaria), 0),
           COALESCE(SUM(d.qtd_aulas_prevista), 0)
      INTO NEW.horas_totais, NEW.quantidade_aulas
      FROM professor_disciplina_vinculos v
      JOIN disciplinas d ON d.id = v.disciplina_id
     WHERE v.professor_id = NEW.id;
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
    IF TG_OP = 'UPDATE' AND OLD.professor_id IS DISTINCT FROM NEW.professor_id THEN
        UPDATE professores SET horas_totais = 0 WHERE id = OLD.professor_id;
    END IF;
    IF TG_OP = 'DELETE' THEN
        UPDATE professores SET horas_totais = 0 WHERE id = OLD.professor_id;
        RETURN OLD;
    END IF;
    UPDATE professores SET horas_totais = 0 WHERE id = NEW.professor_id;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS vinculos_atualizam_totais ON professor_disciplina_vinculos;
CREATE TRIGGER vinculos_atualizam_totais
AFTER INSERT OR UPDATE OR DELETE ON professor_disciplina_vinculos
FOR EACH ROW EXECUTE FUNCTION atualizar_totais_por_vinculo();

CREATE OR REPLACE FUNCTION atualizar_totais_por_disciplina()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.carga_horaria IS DISTINCT FROM NEW.carga_horaria
       OR OLD.qtd_aulas_prevista IS DISTINCT FROM NEW.qtd_aulas_prevista THEN
        UPDATE professores SET horas_totais = 0
         WHERE id IN (
             SELECT professor_id FROM professor_disciplina_vinculos
             WHERE disciplina_id = NEW.id
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

COMMIT;
