BEGIN;

ALTER TABLE cursos
    DROP CONSTRAINT IF EXISTS ck_cursos_nivel_academico;

ALTER TABLE cursos
    ADD CONSTRAINT ck_cursos_nivel_academico
    CHECK (
        nivel_academico IS NULL
        OR nivel_academico IN (
            'bacharelado',
            'licenciatura',
            'tecnologo',
            'pos_graduacao',
            'mestrado',
            'curso_livre'
        )
    );

COMMIT;
